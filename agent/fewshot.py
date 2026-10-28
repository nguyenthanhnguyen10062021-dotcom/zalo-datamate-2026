"""Kho few-shot (câu train -> spec đúng) và tìm ví dụ giống nhất bằng BM25 (thuần code, không model).

Spec đúng lấy từ các câu verifier đã khớp gold: bộ chọn cũ (check_with_gold) + bộ chọn mở rộng (verify_business),
chạy lại qua dispatcher và CHỈ giữ spec cho ra đáp án khớp gold. Thêm ví dụ `unsupported` / `unanswerable` gán
nhãn bằng từ khoá (chỉ dùng lúc dựng kho từ train, không dùng lúc trả lời).
Kho chứa câu hỏi train (dữ liệu BTC) -> ghi ra artifacts/ (git ignore), không đẩy lên repo.

Dựng kho:  python -m agent.fewshot --shops dev --out artifacts/fewshot_dev.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UNSUPPORTED_RE = re.compile(
    r"\bno\b|cong no|tra no|thu no|mua chiu|thieu tien|ton kho|trong kho|con lai may|con ton|het hang|nhap hang|"
    r"nhap vao|phieu nhap|gia nhap|nha cung cap|het han|han dung|\blo\b|dot giao|dot hang|lai rong|"
    r"chi phi|bao hanh|tra gop|may cu|ton theo|gia tri hang")
UNANSWERABLE_RE = re.compile(r"tay nghe|tan tam|lanh nghe|\bkhen\b|nen uong|moi lan may|khach nu|khach nam\b|"
                             r"thoi tiet|dep nhat|ngon nhat|hai long")


def tokens(text: str) -> list[str]:
    """Từ đã chuẩn hoá (bỏ dấu, sửa Telex) + bigram; số thay bằng '#' để khớp theo mẫu câu."""
    from check_with_gold import norm_question
    words = re.sub(r"\d+", "#", norm_question(text)).split()
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.2, b: float = 0.75):
        self.docs, self.k1, self.b = [Counter(d) for d in docs], k1, b
        self.len = [len(d) for d in docs]
        self.avg = sum(self.len) / max(len(docs), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def top(self, query: list[str], k: int, skip=lambda i: False) -> list[int]:
        q = Counter(query)
        scores = []
        for i, d in enumerate(self.docs):
            if skip(i):
                continue
            s = 0.0
            for t in q:
                f = d.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            if s > 0:
                scores.append((s, i))
        return [i for _, i in sorted(scores, key=lambda x: (-x[0], x[1]))[:k]]


class FewShot:
    """Ví dụ few-shot; `exclude_shop` để khi chấm trên DEV không lấy ví dụ của chính tiệm đó."""

    def __init__(self, bank_path: str | Path):
        self.items = [json.loads(l) for l in Path(bank_path).read_text(encoding="utf-8").splitlines() if l.strip()]
        self.index = BM25([tokens(x["question"]) for x in self.items])

    def examples(self, question: str, k: int = 5, exclude_shop: str | None = None, exclude_id: str | None = None):
        skip = lambda i: self.items[i]["business_id"] == exclude_shop or self.items[i]["id"] == exclude_id  # noqa: E731
        return [self.items[i] for i in self.index.top(tokens(question), k, skip)]


# ---- dựng kho từ train -----------------------------------------------------------------------------

def _legacy_spec(q: dict, tables: dict, display: dict) -> dict | None:
    """Câu bộ chọn cũ (check_with_gold) -> spec."""
    import check_with_gold as legacy
    from verify_business import quantity_request
    c = legacy.classify_question(q["question"])
    if c is None:
        return None
    kind, month, year = c[0], c[1], c[2]
    period = {"kind": "month", "month": month, "year": year}
    if kind == "doanh_thu":
        return {"op": "revenue", "answer_type": "number", "period": period}
    if kind == "so_don_huy":
        return {"op": "cancelled_orders", "answer_type": "number", "period": period}
    if kind.startswith("doanh_thu_ca_"):
        return {"op": "revenue", "answer_type": "number", "period": period, "shift": kind.rsplit("_", 1)[1]}
    if kind == "so_luong":
        req = quantity_request(tables, c[3] if len(c) > 3 else "")
        if req is None:
            return None
        unit, filters = req
        spec = {"op": "quantity", "answer_type": "number", "period": period, "unit": unit}
        if filters.product_ids:
            spec["product"] = display[filters.product_ids[0]]
        return spec
    return None


def build_bank(train_dir: Path, cache_dir: Path, shops: list[str], out: Path) -> Counter:
    import check_with_gold as legacy
    import verify_business as vb
    from business import DataError, Periods, Rulebook, SalesMetrics, UnsupportedRule

    from .dispatch import execute
    from .spec import parse_spec
    rules = Rulebook.from_path(train_dir / "rulebook.md")
    questions = [json.loads(l) for l in (train_dir / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    golds = {g["id"]: g for g in map(json.loads, (train_dir / "answers.jsonl").read_text(encoding="utf-8").splitlines())}
    keep, stats, shops_cache = [], Counter(), {}
    for q in questions:
        bid = q["business_id"]
        if bid not in shops:
            continue
        if bid not in shops_cache:
            tables = vb._full_tables(cache_dir / bid)
            shops_cache[bid] = (SalesMetrics(tables, rules, q["as_of_date"]), vb._Ctx(tables), tables)
        engine, ctx, tables = shops_cache[bid]
        t = legacy.norm_question(q["question"])
        spec, source = _legacy_spec(q, tables, ctx.display), "legacy"
        if spec is None:
            source, spec = vb.select_spec(t, ctx)
        if spec is not None:
            parsed, _ = parse_spec(spec)
            try:
                engine.as_of = date.fromisoformat(q["as_of_date"])
                ctx.periods = Periods(rules, q["as_of_date"], train_dir / "calendar.csv")
                answer = execute(parsed, engine, ctx.periods, ctx.catalog)
                ok = vb.SCORER.score_one(golds[q["id"]], answer.to_submission(q["id"]))[0] == vb.SCORER.CORRECT
            except (DataError, UnsupportedRule, ValueError, KeyError):
                ok = False
            if not ok:
                stats["spec_sai_bo"] += 1
                continue
        elif UNANSWERABLE_RE.search(t) and golds[q["id"]]["type"] == "unanswerable":
            source, spec = "unanswerable", {"op": "unanswerable", "answer_type": "unanswerable"}
        elif UNSUPPORTED_RE.search(t):
            source, spec = "unsupported", {"op": "unsupported"}
        else:
            stats["khong_nhan"] += 1
            continue
        stats[source] += 1
        keep.append({"id": q["id"], "business_id": bid, "question": q["question"], "spec": spec, "source": source})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in keep) + "\n", encoding="utf-8")
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", type=Path, default=Path("train"))
    ap.add_argument("--cache", type=Path, default=Path("cache"))
    ap.add_argument("--split", type=Path, default=Path("config/split.json"))
    ap.add_argument("--shops", choices=["dev", "all"], default="dev")
    ap.add_argument("--out", type=Path, default=Path("artifacts/fewshot_dev.jsonl"))
    args = ap.parse_args(argv)
    split = json.loads(args.split.read_text(encoding="utf-8"))
    shops = split["dev"] if args.shops == "dev" else split["dev"] + split["holdout"]
    stats = build_bank(args.train, args.cache, shops, args.out)
    print(f"{args.out}: {sum(v for k, v in stats.items() if k not in ('spec_sai_bo', 'khong_nhan'))} ví dụ", dict(stats))


if __name__ == "__main__":
    main()
