#!/usr/bin/env python3
"""Chấm điểm submission DataMate (Zalo AI Challenge 2026) theo luật chấm của BTC.

Cách chạy:
    python evaluate.py --pred submission.jsonl --gold train/answers.jsonl \
        [--questions train/questions.jsonl] [--errors errors.jsonl]

Mỗi câu: đúng +1, sai -1, bỏ trống 0. ĐIỂM = (đúng - sai) / tổng số câu.
Chỉ dùng thư viện chuẩn (Python 3.10+).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict

# Kết quả chấm một câu
CORRECT = "correct"
WRONG = "wrong"
ABSTAIN = "abstain"

# Nhóm lý do sai (ghi vào errors.jsonl)
WRONG_TYPE = "sai type"
WRONG_FORMAT = "sai format"
WRONG_VALUE = "sai giá trị"

FLOAT_TOL = 1e-6  # chỉ bỏ qua sai số dấu phẩy động

# re.ASCII để \d chỉ khớp 0-9 (không khớp chữ số Unicode khác)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}-\d{2}", re.ASCII)

_MISSING = object()  # đánh dấu dòng dự đoán không có khóa "answer"


# ---------------------------------------------------------------------------
# Đọc file
# ---------------------------------------------------------------------------

def load_jsonl(path: str) -> tuple[list[dict], int]:
    """Đọc file JSONL, trả về (danh sách object, số dòng không parse được).

    Dòng trống bị bỏ qua. Dòng không phải JSON hợp lệ, hoặc không phải object
    có khóa "id", bị đếm là lỗi (với submission: coi như bỏ trống câu đó).
    Dùng utf-8-sig để chịu được BOM ở đầu file.
    """
    records: list[dict] = []
    n_bad = 0
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            if not isinstance(obj, dict) or "id" not in obj:
                n_bad += 1
                continue
            records.append(obj)
    return records, n_bad


# ---------------------------------------------------------------------------
# Kiểm tra format
# ---------------------------------------------------------------------------

def is_number(x) -> bool:
    """JSON number hữu hạn: int/float nhưng KHÔNG phải bool (bool là lớp con của int)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return False
    return isinstance(x, int) or math.isfinite(x)


def is_valid_format(qtype: str, answer) -> bool:
    """Kiểm tra answer có đúng format của type hay không (chưa so giá trị)."""
    if qtype in ("number", "percent"):
        return is_number(answer)
    if qtype == "date":
        return isinstance(answer, str) and DATE_RE.fullmatch(answer) is not None
    if qtype == "boolean":
        return isinstance(answer, bool)
    if qtype == "string":
        return isinstance(answer, str)
    if qtype == "list":
        return isinstance(answer, list)
    if qtype == "table":
        return (
            isinstance(answer, dict)
            and isinstance(answer.get("columns"), list)
            and isinstance(answer.get("rows"), list)
            and all(isinstance(r, list) for r in answer["rows"])
        )
    if qtype == "unanswerable":
        return True
    return False


# ---------------------------------------------------------------------------
# So giá trị
# ---------------------------------------------------------------------------

def normalize_str(s: str) -> str:
    """Chuẩn hóa chuỗi để so: NFC, lowercase, bỏ khoảng trắng và dấu câu.

    Chỉ giữ ký tự chữ (L*), số (N*) và dấu kết hợp (M*) nên dấu tiếng Việt
    được giữ nguyên: "Sting dầu" != "Sting dâu".
    """
    s = unicodedata.normalize("NFC", s).lower()
    s = unicodedata.normalize("NFC", s)
    return "".join(ch for ch in s if unicodedata.category(ch)[0] in "LNM")


def match_number(gold, pred) -> bool:
    return is_number(pred) and abs(gold - pred) <= FLOAT_TOL


def match_string(gold: str, pred, aliases=()) -> bool:
    """Đúng nếu pred khớp gold hoặc bất kỳ alias nào (sau chuẩn hóa)."""
    if not isinstance(pred, str):
        return False
    p = normalize_str(pred)
    return any(p == normalize_str(c) for c in (gold, *aliases) if isinstance(c, str))


def match_scalar(gold, pred, aliases=()) -> bool:
    """So một giá trị đơn (phần tử list / ô bảng) theo kiểu của gold."""
    if isinstance(gold, bool):
        return isinstance(pred, bool) and gold == pred
    if is_number(gold):
        return match_number(gold, pred)
    if isinstance(gold, str):
        return match_string(gold, pred, aliases)
    return gold == pred


def scalar_type_ok(gold, pred) -> bool:
    """Phần tử/ô có đúng kiểu so với gold không (số phải là JSON number, chuỗi phải là str)."""
    if isinstance(gold, bool):
        return isinstance(pred, bool)
    if is_number(gold):
        return is_number(pred)
    if isinstance(gold, str):
        return isinstance(pred, str)
    return True


def _alias_at(alias, i: int) -> list:
    """alias[i] nếu có (dùng cho list và table), ngược lại list rỗng."""
    if isinstance(alias, list) and i < len(alias) and isinstance(alias[i], list):
        return alias[i]
    return []


def match_list(gold: list, alias, pred: list) -> tuple[bool, str]:
    """List: cùng độ dài, so từng vị trí theo thứ tự; phần tử chuỗi nhận alias[i]."""
    if len(pred) != len(gold):
        return False, f"{WRONG_VALUE}: độ dài {len(pred)} != {len(gold)}"
    for i, (g, p) in enumerate(zip(gold, pred)):
        if not scalar_type_ok(g, p):
            return False, f"{WRONG_FORMAT}: phần tử [{i}] sai kiểu ({p!r})"
        if not match_scalar(g, p, _alias_at(alias, i)):
            return False, f"{WRONG_VALUE}: phần tử [{i}] {p!r} != {g!r}"
    return True, ""


def map_columns(gold_cols: list, pred_cols: list) -> list[int]:
    """Với mỗi cột đáp án, tìm chỉ số cột dự đoán tương ứng.

    So theo tên cột (đã chuẩn hóa); tên không khớp thì lấy cột cùng VỊ TRÍ.
    """
    pred_names = [normalize_str(c) if isinstance(c, str) else None for c in pred_cols]
    mapping = []
    for j, gc in enumerate(gold_cols):
        name = normalize_str(gc) if isinstance(gc, str) else None
        if name is not None and pred_names.count(name) == 1:
            mapping.append(pred_names.index(name))
        else:
            mapping.append(j)
    return mapping


def match_table(gold: dict, alias, pred: dict) -> tuple[bool, str]:
    """Table: cùng số dòng/cột; ghép dòng theo ô đầu tiên (có alias), thứ tự dòng tùy ý."""
    g_cols, g_rows = gold["columns"], gold["rows"]
    p_cols, p_rows = pred["columns"], pred["rows"]
    if len(p_rows) != len(g_rows):
        return False, f"{WRONG_VALUE}: số dòng {len(p_rows)} != {len(g_rows)}"
    if len(p_cols) != len(g_cols):
        return False, f"{WRONG_VALUE}: số cột {len(p_cols)} != {len(g_cols)}"

    col_map = map_columns(g_cols, p_cols)

    # Chiếu mỗi dòng dự đoán về thứ tự cột của đáp án
    projected = []
    for r, row in enumerate(p_rows):
        if any(k >= len(row) for k in col_map):
            return False, f"{WRONG_FORMAT}: dòng [{r}] thiếu ô"
        projected.append([row[k] for k in col_map])

    # Kiểm kiểu từng ô theo kiểu ô tương ứng của đáp án (ô số phải là JSON number)
    for j in range(len(g_cols)):
        g_cells = [row[j] for row in g_rows if j < len(row)]
        if not g_cells:
            continue
        for r, prow in enumerate(projected):
            if not scalar_type_ok(g_cells[0], prow[j]):
                return False, f"{WRONG_FORMAT}: ô dòng [{r}] cột {g_cols[j]!r} sai kiểu ({prow[j]!r})"

    # Ghép dòng: mỗi dòng đáp án tìm một dòng dự đoán chưa dùng khớp toàn bộ
    used = [False] * len(projected)
    for i, g_row in enumerate(g_rows):
        aliases = _alias_at(alias, i)
        found = False
        for r, prow in enumerate(projected):
            if used[r]:
                continue
            if not match_scalar(g_row[0], prow[0], aliases):
                continue
            if all(match_scalar(g, p) for g, p in zip(g_row[1:], prow[1:])):
                used[r] = found = True
                break
        if not found:
            return False, f"{WRONG_VALUE}: không có dòng khớp {g_row!r}"
    return True, ""


def match_value(qtype: str, gold, alias, pred) -> tuple[bool, str]:
    """So giá trị dự đoán với đáp án (pred đã đúng format). Trả về (đúng?, lý do nếu sai)."""
    if qtype in ("number", "percent"):
        ok = match_number(gold, pred)
    elif qtype in ("date", "boolean"):
        ok = gold == pred
    elif qtype == "string":
        ok = match_string(gold, pred, alias if isinstance(alias, list) else [])
    elif qtype == "list":
        return match_list(gold, alias, pred)
    elif qtype == "table":
        return match_table(gold, alias, pred)
    elif qtype == "unanswerable":
        ok = True
    else:
        ok = False
    return ok, "" if ok else f"{WRONG_VALUE}: {pred!r} != {gold!r}"


# ---------------------------------------------------------------------------
# Chấm một câu
# ---------------------------------------------------------------------------

def score_one(gold: dict, pred: dict | None) -> tuple[str, str]:
    """Chấm một câu. Trả về (CORRECT | WRONG | ABSTAIN, lý do)."""
    if pred is None:
        return ABSTAIN, "không có dòng"
    ptype = pred.get("type")
    if ptype == "abstain":
        return ABSTAIN, "abstain"
    # Dòng có "reason" không phải chuỗi thì không đọc được -> bỏ trống
    if "reason" in pred and not isinstance(pred["reason"], str):
        return ABSTAIN, "reason không phải chuỗi"

    gtype = gold["type"]
    if ptype != gtype:
        return WRONG, f"{WRONG_TYPE}: dự đoán {ptype!r}, đáp án {gtype!r}"
    if gtype == "unanswerable":
        return CORRECT, ""

    answer = pred.get("answer", _MISSING)
    if answer is _MISSING:
        return WRONG, f"{WRONG_FORMAT}: thiếu khóa answer"
    if not is_valid_format(gtype, answer):
        return WRONG, f"{WRONG_FORMAT}: {answer!r} không phải format {gtype}"

    ok, reason = match_value(gtype, gold["answer"], gold.get("alias", []), answer)
    return (CORRECT, "") if ok else (WRONG, reason)


# ---------------------------------------------------------------------------
# Thống kê và in kết quả
# ---------------------------------------------------------------------------

def print_table(title: str, headers: list[str], rows: list[list]) -> None:
    """In bảng căn cột đơn giản."""
    cells = [headers] + [[str(c) for c in r] for r in rows]
    widths = [max(len(r[j]) for r in cells) for j in range(len(headers))]
    print(f"\n{title}")
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for r in cells[1:]:
        print("  ".join([r[0].ljust(widths[0])] + [c.rjust(w) for c, w in zip(r[1:], widths[1:])]))


def group_rows(results: list[dict], key: str) -> list[list]:
    """Gom kết quả theo khóa (type / business_id): số câu, đúng, sai, bỏ trống, điểm."""
    groups: dict[str, Counter] = defaultdict(Counter)
    for r in results:
        groups[r[key]][r["status"]] += 1
    rows = []
    for name in sorted(groups):
        c = groups[name]
        n = sum(c.values())
        rows.append([name, n, c[CORRECT], c[WRONG], c[ABSTAIN], f"{(c[CORRECT] - c[WRONG]) / n:.4f}"])
    return rows


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Chấm điểm submission DataMate")
    parser.add_argument("--pred", required=True, help="file submission.jsonl")
    parser.add_argument("--gold", required=True, help="file answers.jsonl")
    parser.add_argument("--questions", help="file questions.jsonl (để thống kê theo business_id)")
    parser.add_argument("--errors", default="errors.jsonl", help="file ghi các câu sai")
    args = parser.parse_args(argv)

    golds, _ = load_jsonl(args.gold)
    preds, n_bad = load_jsonl(args.pred)

    # Gom dự đoán theo id; trùng id thì dòng sau cùng được dùng
    pred_by_id: dict = {}
    n_dup = 0
    for p in preds:
        if p["id"] in pred_by_id:
            n_dup += 1
        pred_by_id[p["id"]] = p
    gold_ids = {g["id"] for g in golds}
    n_unknown = sum(1 for pid in pred_by_id if pid not in gold_ids)
    if n_bad:
        print(f"[cảnh báo] {n_bad} dòng submission không đọc được -> coi như bỏ trống", file=sys.stderr)
    if n_dup:
        print(f"[cảnh báo] {n_dup} dòng trùng id trong submission -> dùng dòng sau cùng", file=sys.stderr)
    if n_unknown:
        print(f"[cảnh báo] {n_unknown} id trong submission không có trong đáp án -> bỏ qua", file=sys.stderr)

    questions = {}
    if args.questions:
        qs, _ = load_jsonl(args.questions)
        questions = {q["id"]: q for q in qs}

    # Chấm từng câu
    results = []
    errors = []
    for g in golds:
        pred = pred_by_id.get(g["id"])
        status, reason = score_one(g, pred)
        q = questions.get(g["id"], {})
        results.append({
            "id": g["id"],
            "type": g["type"],
            "business_id": q.get("business_id", "(không rõ)"),
            "status": status,
        })
        if status == WRONG:
            err = {"id": g["id"]}
            if "question" in q:
                err["question"] = q["question"]
            err["gold"] = {"type": g["type"], "answer": g.get("answer"), "alias": g.get("alias", [])}
            err["pred"] = pred
            err["reason"] = reason
            errors.append(err)

    # Tổng kết
    total = len(results)
    c = Counter(r["status"] for r in results)
    n_ok, n_wrong, n_abs = c[CORRECT], c[WRONG], c[ABSTAIN]
    score = (n_ok - n_wrong) / total if total else 0.0
    answered = n_ok + n_wrong
    acc = n_ok / answered if answered else 0.0

    print("=== TỔNG KẾT ===")
    print(f"Số câu        : {total}")
    print(f"Đúng / Sai / Bỏ trống: {n_ok} / {n_wrong} / {n_abs}")
    print(f"ĐIỂM          : {score:.4f}  (= (đúng - sai) / tổng)")
    print(f"Độ chính xác trên câu đã trả lời: {acc:.4f}  ({n_ok}/{answered})")

    headers = ["", "số câu", "đúng", "sai", "bỏ trống", "điểm"]
    print_table("=== THEO TYPE (đáp án) ===", ["type"] + headers[1:], group_rows(results, "type"))
    if args.questions:
        print_table("=== THEO BUSINESS_ID ===", ["business_id"] + headers[1:], group_rows(results, "business_id"))

    with open(args.errors, "w", encoding="utf-8") as f:
        for e in errors:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"\nĐã ghi {len(errors)} câu sai vào {args.errors}")

    return {"total": total, "correct": n_ok, "wrong": n_wrong, "abstain": n_abs,
            "score": score, "accuracy": acc}


if __name__ == "__main__":
    main()
