#!/usr/bin/env python3
"""Đánh giá agent trên train, chia theo TIỆM (config/split.json). Điểm thật bằng luật chấm của evaluate.py.

  python eval_agent.py --split holdout --sc --out runs/holdout_v0      # con số chính
  python eval_agent.py --split dev --out runs/dev_v0                   # tham khảo (few-shot bỏ ví dụ cùng tiệm)
  python eval_agent.py --split holdout --oracle --out runs/oracle      # LLM giả = spec đúng của kho (không GPU)

Few-shot luôn lấy từ kho DEV (artifacts/fewshot_dev.jsonl). Log từng câu: <out>/records.jsonl (chạy lại thì tiếp tục).
Báo cáo: <out>/report.md. Phương án (a) không self-consistency, (b) có (cần --sc).
"""
from __future__ import annotations

import argparse
import json
import statistics
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import verify_business as vb
from agent.llm import Completion, load_config
from agent.pipeline import ABSTAIN, Agent, consistent, post_check
from agent.spec import parse_spec

SCORER = vb.SCORER


class OracleLLM:
    """LLM giả: trả spec của kho cho câu có trong kho, còn lại 'unsupported'. Chỉ để kiểm thử đường ống."""

    def __init__(self, bank: Path):
        self.specs = {}
        for line in bank.read_text(encoding="utf-8").splitlines():
            if line.strip():
                x = json.loads(line)
                self.specs[x["question"]] = x["spec"]

    def complete(self, messages, schema=None, temperature=None, seed=None):
        q = messages[-1]["content"].split("Câu hỏi: ", 1)[1].rsplit("\nTrả về spec JSON.", 1)[0]
        return Completion(json.dumps(self.specs.get(q, {"op": "unsupported"}), ensure_ascii=False), 0, 0, 0.0)


def rescore(agent: Agent, rec: dict, sc: bool) -> dict:
    """Tính lại đáp án từ spec LLM đã lưu (không gọi model): áp hậu kỳ + business/ hiện tại."""
    q = {k: rec[k] for k in ("id", "business_id", "question", "as_of_date")}

    def redo(att):
        if att.get("spec") is None:
            return att
        spec, _ = parse_spec(att["spec"])
        spec, problem = post_check(spec, q["question"])
        keep = {k: att[k] for k in ("prompt_tokens", "completion_tokens", "llm_seconds", "fixed", "raw", "spec") if k in att}
        if problem:
            return {**keep, "submission": ABSTAIN, "reason": problem}
        return {**keep, **agent.run_spec(q, spec)}
    rec = {**rec, "greedy": redo(rec["greedy"]), "samples": [redo(x) for x in rec["samples"]]}
    rec["final_a"] = rec["greedy"]["submission"]
    rec["final_b"] = consistent(rec["greedy"], rec["samples"]) if sc else rec["final_a"]
    return rec


def category(q: dict, ctx_cache: dict, cache_dir: Path) -> str:
    """Loại câu (chỉ để báo cáo): bộ chọn cũ / C1..C9 của verifier / ngoài API (từ khoá) / khác."""
    import check_with_gold as legacy
    from agent.fewshot import UNSUPPORTED_RE
    c = legacy.classify_question(q["question"])
    if c is not None:
        return c[0]
    bid = q["business_id"]
    if bid not in ctx_cache:
        ctx_cache[bid] = vb._Ctx(vb._full_tables(cache_dir / bid))
    t = legacy.norm_question(q["question"])
    kind, _ = vb.select_spec(t, ctx_cache[bid])
    if kind:
        return kind
    return "ngoai_api(tu_khoa)" if UNSUPPORTED_RE.search(t) else "khac"


def score_rows(records, golds, key):
    rows = []
    for r in records:
        sub = {"id": r["id"], **r[key]}
        status, why = SCORER.score_one(golds[r["id"]], sub)
        rows.append((r, status, why))
    return rows


def table(rows, group, title):
    agg = defaultdict(Counter)
    for r, status, _ in rows:
        agg[group(r)][status] += 1
    lines = [f"| {title} | n | đúng | sai | bỏ trống | điểm | điểm/câu |", "|---|---|---|---|---|---|---|"]
    for g in sorted(agg, key=lambda g: -sum(agg[g].values())):
        c = agg[g]
        n, s = sum(c.values()), c[SCORER.CORRECT] - c[SCORER.WRONG]
        lines.append(f"| {g} | {n} | {c[SCORER.CORRECT]} | {c[SCORER.WRONG]} | {c[SCORER.ABSTAIN]} | {s} | {s / n:.3f} |")
    return lines


def report(records, golds, cats, out: Path, sc: bool, wall: float | None):
    lines = [f"# Đánh giá agent — {out.name}", "", f"{len(records)} câu.", ""]
    variants = [("final_a", "(a) không self-consistency")] + ([("final_b", "(b) có self-consistency")] if sc else [])
    summary = {}
    for key, name in variants:
        rows = score_rows(records, golds, key)
        c = Counter(s for _, s, _ in rows)
        total = c[SCORER.CORRECT] - c[SCORER.WRONG]
        summary[key] = {"diem": total, "dung": c[SCORER.CORRECT], "sai": c[SCORER.WRONG], "bo_trong": c[SCORER.ABSTAIN],
                        "diem_tren_cau": round(total / max(len(rows), 1), 4)}
        lines += [f"## {name}: điểm {total} / {len(rows)} câu ({total / max(len(rows), 1):.3f}/câu) — "
                  f"đúng {c[SCORER.CORRECT]}, sai {c[SCORER.WRONG]}, bỏ trống {c[SCORER.ABSTAIN]}", ""]
        lines += table(rows, lambda r: golds[r["id"]]["type"], "type (gold)") + [""]
        lines += table(rows, lambda r: cats[r["id"]], "loại câu") + [""]
        lines += table(rows, lambda r: (r["greedy"].get("spec") or {}).get("op", "(không có spec)"), "op (spec greedy)") + [""]
    g = [r["greedy"] for r in records]
    valid = sum(1 for x in g if x.get("spec") is not None)
    reasons = Counter(x["reason"] for x in g if x["submission"].get("type") == "abstain")
    calls = [x for r in records for x in [r["greedy"], *r["samples"]]]
    pt = [x["prompt_tokens"] for x in calls if x.get("prompt_tokens")]
    ct = [x["completion_tokens"] for x in calls if x.get("completion_tokens")]
    secs = [r["seconds"] for r in records]
    lines += ["## Thống kê (spec greedy)", "",
              f"- Spec hợp lệ: {valid}/{len(g)} = {100 * valid / max(len(g), 1):.1f}% "
              f"(phải sửa 1 lần: {sum(1 for x in g if x.get('fixed'))})",
              f"- Abstain (a): {sum(reasons.values())}/{len(g)} = {100 * sum(reasons.values()) / max(len(g), 1):.1f}%",
              f"- Lý do abstain (a): {dict(reasons.most_common())}",
              f"- Giây/câu (một luồng, gồm cả mẫu SC): TB {statistics.mean(secs):.2f}, trung vị {statistics.median(secs):.2f}"
              if secs else "- Giây/câu: -",
              f"- Thời gian thực cả lượt: {wall:.0f}s -> {wall / max(len(records), 1):.2f} s/câu (song song)" if wall else "",
              f"- Token/lời gọi LLM: prompt TB {statistics.mean(pt):.0f} (max {max(pt)}), "
              f"completion TB {statistics.mean(ct):.0f}; số lời gọi {len(calls)}" if pt else "- Token: -", ""]
    wrong = [(r, why) for r, s, why in score_rows(records, golds, "final_b" if sc else "final_a") if s == SCORER.WRONG]
    lines += [f"## Câu sai ({len(wrong)}), 25 câu đầu", ""]
    for r, why in wrong[:25]:
        gold = golds[r["id"]]
        lines.append(f"- `{r['id']}` [{cats[r['id']]}] {r['question']}\n  - spec: `{json.dumps(r['greedy'].get('spec'), ensure_ascii=False)}`"
                     f"\n  - đáp án: `{json.dumps(r['final_a'], ensure_ascii=False)}` | gold: "
                     f"`{json.dumps({'type': gold['type'], 'answer': gold.get('answer')}, ensure_ascii=False)}` | {why}")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps({"n": len(records), **summary, "abstain_reasons": dict(reasons),
                                                  "spec_valid": valid}, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", choices=["holdout", "dev"], default="holdout")
    ap.add_argument("--train", type=Path, default=Path("train"))
    ap.add_argument("--cache", type=Path, default=Path("cache"))
    ap.add_argument("--bank", type=Path, default=Path("artifacts/fewshot_dev.jsonl"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sc", action="store_true", help="chạy thêm 3 mẫu self-consistency")
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--rescore-from", type=Path, default=None,
                    help="tính lại từ records.jsonl của lượt khác (không gọi LLM)")
    args = ap.parse_args(argv)

    split = json.loads(Path("config/split.json").read_text(encoding="utf-8"))
    shops = set(split[args.split])
    questions = [q for q in map(json.loads, (args.train / "questions.jsonl").read_text(encoding="utf-8").splitlines())
                 if q["business_id"] in shops]
    if args.limit:
        questions = questions[:args.limit]
    golds = {g["id"]: g for g in map(json.loads, (args.train / "answers.jsonl").read_text(encoding="utf-8").splitlines())}
    args.out.mkdir(parents=True, exist_ok=True)
    rec_path = args.out / "records.jsonl"
    records = {}
    if rec_path.exists():
        for line in rec_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                records[r["id"]] = r
    if args.rescore_from is not None:
        old = [json.loads(l) for l in (args.rescore_from / "records.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        agent = Agent(load_config(), args.train, args.cache, args.bank, llm=OracleLLM(args.bank))
        with rec_path.open("w", encoding="utf-8") as f:
            for r in old:
                r = rescore(agent, r, args.sc)
                records[r["id"]] = r
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    todo = [q for q in questions if q["id"] not in records]
    wall = None
    if todo and not args.report_only:
        cfg = load_config()
        llm = OracleLLM(Path("artifacts/fewshot_all.jsonl")) if args.oracle else None
        agent = Agent(cfg, args.train, args.cache, args.bank, llm=llm)
        lock = threading.Lock()
        print(f"{len(questions)} câu ({args.split}), đã có {len(records)}, chạy {len(todo)}", flush=True)
        t0 = time.time()
        exclude = (lambda q: q["business_id"]) if args.split == "dev" else (lambda q: None)
        with rec_path.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(agent.answer, q, args.sc, exclude(q)) for q in todo]
            for i, fut in enumerate(as_completed(futs), 1):
                r = fut.result()
                with lock:
                    f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                    f.flush()
                records[r["id"]] = r
                if i % 50 == 0 or i == len(todo):
                    print(f"[{time.time() - t0:7.1f}s] {i}/{len(todo)}", flush=True)
        wall = time.time() - t0
    recs = [records[q["id"]] for q in questions if q["id"] in records]
    ctx_cache = {}
    cats = {q["id"]: category(q, ctx_cache, args.cache) for q in questions}
    summary = report(recs, golds, cats, args.out, args.sc, wall)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
