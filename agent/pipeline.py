"""Một câu hỏi: prompt -> LLM (spec JSON) -> kiểm tra -> business API -> đáp án hoặc abstain.

Chính sách abstain (sai -1, bỏ trống 0): spec lỗi sau 1 lần sửa; op unsupported; UnsupportedRule; DataError;
khớp tên mơ hồ; Answer.confidence == 'low'; lỗi LLM/runtime. Self-consistency (tuỳ chọn): 3 spec lấy mẫu
(temperature 0.7, seed 1..3) phải cho cùng đáp án với spec greedy, nếu không thì abstain.
"""
from __future__ import annotations

import copy
import json
import time
from datetime import date
from pathlib import Path

from business import DataError, Periods, Rulebook, SalesMetrics, UnsupportedRule

from .dispatch import Unsupported, execute
from .fewshot import FewShot
from .llm import LLM
from .prompt import messages
from .resolve import Ambiguous, Catalog
from .spec import json_schema, parse_spec

ABSTAIN = {"type": "abstain"}
RANKING_OPS = {"top_products", "top_customers", "top_staff", "loyal_customers", "big_spender_customers",
               "fickle_customers", "favorite_products", "hardworking_staff"}
LABEL_FIELDS = ("product_group", "channel", "payment", "customer_group", "staff", "active_ingredient")


def post_check(spec, question: str):
    """Kiểm tra hậu kỳ, tổng quát (v0.1). Trả (spec đã chỉnh, lý do abstain hoặc None).
    - xếp hạng: k=1 -> string, k>1 -> list (§9: câu hỏi một đối tượng lấy phần tử đầu);
    - revenue_series: >= 2 kỳ, không trùng nhau (hỏi một kỳ là op khác, hai bộ lọc khác nhau chưa có API);
    - nhãn lọc (nhóm, kênh, thanh toán, nhóm khách, nhân viên) phải có mặt trong câu hỏi: LLM không được tự thêm."""
    from check_with_gold import norm_question
    if spec.op in RANKING_OPS and spec.k is not None:
        spec = spec.model_copy(update={"answer_type": "string" if spec.k == 1 else "list"})
    if spec.op == "revenue_series":
        keys = [p.model_dump_json() for p in spec.periods or []]
        if len(keys) < 2 or len(set(keys)) < len(keys):
            return spec, "series_invalid"
    text = f" {norm_question(question)} "
    for field in LABEL_FIELDS:
        value = getattr(spec, field)
        if value:
            words = norm_question(str(value).replace("_", " ")).split()
            if not words or not all(f" {w} " in text for w in words):
                return spec, "ungrounded_filter"
    return spec, None


class Shop:
    """Bảng chuẩn + engine + danh mục của một tiệm (nạp một lần, dùng chung giữa các luồng)."""

    def __init__(self, cache_dir: Path, rules: Rulebook):
        import pandas as pd
        tables = {n: pd.read_parquet(cache_dir / f"{n}.parquet") for n in ("don_hang", "dong_hang", "mat_hang")}
        for n in ("thuoc", "bang_gia"):
            if (cache_dir / f"{n}.parquet").exists():
                tables[n] = pd.read_parquet(cache_dir / f"{n}.parquet")
        tables["cua_hang"] = json.loads((cache_dir / "cua_hang.json").read_text(encoding="utf-8"))
        self.meta = tables["cua_hang"]
        self.catalog = Catalog(tables)
        self.card = self.catalog.card(self.meta)
        try:
            self.engine, self.error = SalesMetrics(tables, rules, self.meta.get("ngay_ket_thuc_du_lieu") or "2100-01-01"), None
        except DataError as e:          # bảng chuẩn hỏng: mọi câu của tiệm abstain
            self.engine, self.error = None, f"DataError: {e}"

    def engine_at(self, as_of: str) -> SalesMetrics:
        e = copy.copy(self.engine)      # dùng chung DataFrame (chỉ đọc), as_of riêng cho từng câu
        e.as_of = date.fromisoformat(as_of)
        return e


def _key(sub: dict | None) -> str | None:
    if not sub or sub.get("type") == "abstain":
        return None
    return json.dumps([sub["type"], sub.get("answer")], ensure_ascii=False, sort_keys=True)


class Agent:
    def __init__(self, cfg: dict, data_dir: Path, cache_root: Path, bank: Path, llm: LLM | None = None,
                 submit_llm_unanswerable: bool = False):
        self.cfg, self.data_dir, self.cache_root = cfg, Path(data_dir), Path(cache_root)
        self.rules = Rulebook.from_path(self.data_dir / "rulebook.md")
        self.calendar = self.data_dir / "calendar.csv"
        self.fewshot = FewShot(bank)
        self.llm = llm or LLM(cfg)
        self.schema = json_schema()
        self.shops: dict[str, Shop] = {}
        self.submit_llm_unanswerable = submit_llm_unanswerable

    def shop(self, bid: str) -> Shop:
        if bid not in self.shops:
            self.shops[bid] = Shop(self.cache_root / bid, self.rules)
        return self.shops[bid]

    # ---- một lần sinh spec + thực thi ----
    def attempt(self, q: dict, msgs: list[dict], temperature=None, seed=None) -> dict:
        out = {"prompt_tokens": 0, "completion_tokens": 0, "llm_seconds": 0.0, "fixed": False}
        spec, problem = None, None
        for turn in range(2):                   # lần đầu + 1 lần sửa spec lỗi
            c = self.llm.complete(msgs, self.schema, temperature, seed)
            out["prompt_tokens"] += c.prompt_tokens
            out["completion_tokens"] += c.completion_tokens
            out["llm_seconds"] += c.seconds
            if c.text is None:
                return {**out, "submission": ABSTAIN, "reason": "llm_error", "detail": c.error}
            out["raw"] = c.text
            spec, problem = parse_spec(c.text)
            if spec is not None:
                break
            out["fixed"] = True
            msgs = msgs + [{"role": "assistant", "content": c.text},
                           {"role": "user", "content": f"Spec lỗi: {problem}. Trả lại spec JSON đúng."}]
        if spec is None:
            return {**out, "submission": ABSTAIN, "reason": "spec_invalid", "detail": problem}
        out["spec"] = spec.model_dump(exclude_none=True)
        spec, problem = post_check(spec, q["question"])
        if problem:
            return {**out, "submission": ABSTAIN, "reason": problem}
        return {**out, **self.run_spec(q, spec)}

    def run_spec(self, q: dict, spec) -> dict:
        shop = self.shop(q["business_id"])
        if shop.engine is None:
            return {"submission": ABSTAIN, "reason": "data_error", "detail": shop.error}
        try:
            periods = Periods(self.rules, q["as_of_date"], self.calendar)
            answer = execute(spec, shop.engine_at(q["as_of_date"]), periods, shop.catalog)
        except Unsupported as e:
            return {"submission": ABSTAIN, "reason": "op_unsupported" if spec.op == "unsupported" else "exec_unsupported",
                    "detail": str(e)}
        except UnsupportedRule as e:
            return {"submission": ABSTAIN, "reason": "unsupported_rule", "detail": str(e)}
        except DataError as e:
            return {"submission": ABSTAIN, "reason": "data_error", "detail": str(e)}
        except Ambiguous as e:
            return {"submission": ABSTAIN, "reason": "ambiguous_name", "detail": str(e)}
        except Exception as e:  # noqa: BLE001
            return {"submission": ABSTAIN, "reason": "runtime_error", "detail": f"{type(e).__name__}: {e}"[:300]}
        sub = answer.to_submission(q["id"])
        sub.pop("id", None)
        if answer.confidence == "low":
            return {"submission": ABSTAIN, "reason": "low_confidence", "would_be": sub}
        if spec.op == "unanswerable" and not self.submit_llm_unanswerable:
            return {"submission": ABSTAIN, "reason": "llm_unanswerable", "would_be": sub}
        return {"submission": sub, "reason": None}

    # ---- một câu hỏi ----
    def answer(self, q: dict, self_consistency: bool = False, exclude_shop: str | None = None) -> dict:
        t0 = time.time()
        shop = self.shop(q["business_id"])
        shots = self.fewshot.examples(q["question"], k=5, exclude_shop=exclude_shop, exclude_id=q["id"])
        msgs = messages(q["question"], q["as_of_date"], shop.card, shots)
        greedy = self.attempt(q, msgs)
        rec = {"id": q["id"], "business_id": q["business_id"], "question": q["question"], "as_of_date": q["as_of_date"],
               "shots": [s["id"] for s in shots], "greedy": greedy, "samples": []}
        if self_consistency:
            sc = self.cfg["self_consistency"]
            rec["samples"] = [self.attempt(q, msgs, sc["temperature"], seed) for seed in sc["seeds"]]
        rec["final_a"] = greedy["submission"]
        rec["final_b"] = consistent(greedy, rec["samples"]) if self_consistency else greedy["submission"]
        rec["seconds"] = round(time.time() - t0, 3)
        return rec


def consistent(greedy: dict, samples: list[dict]) -> dict:
    """(b): giữ đáp án greedy chỉ khi cả 3 mẫu cho cùng đáp án đó."""
    key = _key(greedy["submission"])
    if key is None or any(_key(s["submission"]) != key for s in samples):
        return ABSTAIN
    return greedy["submission"]
