#!/usr/bin/env python3
"""Runner: python main.py --data <dir> --out <dir>

<dir> có cấu trúc như train/ hoặc public_test/: questions.jsonl, data/<business_id>/, rulebook.md, calendar.csv.
Ghi <out>/submission.jsonl TỪNG DÒNG (flush) và <out>/run.log (JSONL: id, spec, đáp án, lý do abstain, thời gian).
Chạy lại cùng --out thì bỏ qua câu đã có trong submission. /data chỉ đọc; cache ghi vào <out>/cache (hoặc --cache).
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load_shop(shop_dir: str, rulebook: str, train_dir: str, cache_dir: str) -> tuple[str, str | None]:
    """Nạp một tiệm về schema chuẩn và ghi cache (chạy trong tiến trình con)."""
    warnings.simplefilter("ignore")
    sys.path.insert(0, str(ROOT))
    from load_all import json_value, to_parquet
    from loader import load_business
    out = Path(cache_dir)
    try:
        res = load_business(shop_dir, rulebook, train_dir=train_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name in ("don_hang", "dong_hang", "mat_hang", "quy_doi_don_vi", "khach_hang"):
            to_parquet(res[name], out / f"{name}.parquet")
        (out / "cua_hang.json").write_text(json.dumps(res["cua_hang"], ensure_ascii=False, default=json_value),
                                          encoding="utf-8")
        return Path(shop_dir).name, None
    except Exception as e:  # noqa: BLE001
        return Path(shop_dir).name, f"{type(e).__name__}: {e}"


def prepare_cache(data: Path, cache: Path, train_dir: Path, shops: list[str], workers: int) -> dict[str, str]:
    todo = [b for b in shops if not (cache / b / "cua_hang.json").exists()]
    errors = {}
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(load_shop, str(data / "data" / b), str(data / "rulebook.md"), str(train_dir), str(cache / b))
                    for b in todo]
            for f in as_completed(futs):
                bid, err = f.result()
                print(f"[nạp] {bid}: {'OK' if err is None else err}", flush=True)
                if err:
                    errors[bid] = err
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--train-dir", type=Path, default=ROOT / "train", help="README train để dựng từ điển cột")
    ap.add_argument("--bank", type=Path, default=ROOT / "artifacts" / "fewshot_all.jsonl")
    ap.add_argument("--workers", type=int, default=16, help="số câu chạy song song (request LLM đồng thời)")
    ap.add_argument("--load-workers", type=int, default=4)
    ap.add_argument("--self-consistency", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)

    from agent.llm import load_config
    from agent.pipeline import ABSTAIN, Agent

    args.out.mkdir(parents=True, exist_ok=True)
    cache = args.cache or args.out / "cache"
    questions = [json.loads(l) for l in (args.data / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        questions = questions[:args.limit]
    sub_path, log_path = args.out / "submission.jsonl", args.out / "run.log"
    done = set()
    if sub_path.exists():
        for line in sub_path.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                pass
    todo = [q for q in questions if q["id"] not in done]
    print(f"{len(questions)} câu, đã có {len(done)}, còn {len(todo)}", flush=True)

    load_errors = prepare_cache(args.data, cache, args.train_dir, sorted({q["business_id"] for q in todo}),
                                args.load_workers)
    agent = Agent(load_config(), args.data, cache, args.bank)
    lock = threading.Lock()
    sub_f = sub_path.open("a", encoding="utf-8")
    log_f = log_path.open("a", encoding="utf-8")

    def write(q, submission, record):
        with lock:
            sub_f.write(json.dumps({"id": q["id"], **submission}, ensure_ascii=False) + "\n")
            sub_f.flush()
            log_f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            log_f.flush()

    def one(q):
        if q["business_id"] in load_errors:
            return q, ABSTAIN, {"id": q["id"], "reason": "load_error", "detail": load_errors[q["business_id"]]}
        try:
            rec = agent.answer(q, self_consistency=args.self_consistency)
            return q, (rec["final_b"] if args.self_consistency else rec["final_a"]), rec
        except Exception as e:  # noqa: BLE001  câu lỗi -> abstain, không dừng cả lượt
            return q, ABSTAIN, {"id": q["id"], "reason": "runtime_error", "detail": f"{type(e).__name__}: {e}"}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, f in enumerate(as_completed([ex.submit(one, q) for q in todo]), 1):
            q, submission, record = f.result()
            write(q, submission, record)
            if i % 50 == 0 or i == len(todo):
                print(f"[{time.time() - t0:7.1f}s] {i}/{len(todo)}", flush=True)
    sub_f.close()
    log_f.close()


if __name__ == "__main__":
    main()
