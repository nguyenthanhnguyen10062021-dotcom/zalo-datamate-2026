#!/usr/bin/env python3
"""Khảo sát dữ liệu DataMate: đọc README + mở thử mọi file của mọi tiệm, xuất survey_raw.md.

Chạy:  python survey.py [--out survey_raw.md] [--only biz_101,dev_012]

Chỉ ĐỌC dữ liệu gốc (xlsx mở read-only, sqlite mở mode=ro), không ghi gì vào train/ hay public_test/.
Thư viện: pandas (đọc csv), openpyxl (đọc xlsx), sqlite3.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sqlite3
import sys
import time
from collections import Counter
from datetime import date, datetime, time as dtime
from pathlib import Path

import openpyxl
import pandas as pd

ROOTS = [("train", Path("train/data")), ("public_test", Path("public_test/data"))]

N_HEAD = 10          # số dòng dữ liệu in ra sau dòng header
HEADER_SCAN = 25     # quét bao nhiêu dòng đầu để tìm header
MAX_CELL = 38        # cắt ô dài khi in
ENUM_MAX = 15        # cột có <= ngần này giá trị khác nhau thì liệt kê hết
EXAMPLES = 3         # số ví dụ mỗi mẫu giá trị

# ---------------------------------------------------------------------------
# Nhận dạng mẫu giá trị (để phát hiện các kiểu "bẩn")
# ---------------------------------------------------------------------------

PATTERNS = [
    # (tên mẫu, regex) — thứ tự quan trọng: mẫu cụ thể trước
    ("rỗng", re.compile(r"^\s*$")),
    ("số_nguyên", re.compile(r"^-?\d+$")),
    ("số_thập_phân", re.compile(r"^-?\d+\.\d+$")),
    ("số_phẩy_thập_phân", re.compile(r"^-?\d+,\d{1,2}$")),
    ("số_có_phân_cách", re.compile(r"^-?\d{1,3}([.,]\d{3})+([.,]\d+)?$")),
    ("tiền_kèm_đơn_vị", re.compile(r"^-?[\d.,]+\s*(đ|₫|vnd|vnđ|k|tr|triệu|nghìn|ngàn)\.?$", re.I)),
    ("phần_trăm", re.compile(r"^-?[\d.,]+\s*%$")),
    ("ngày_iso", re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")),
    ("ngày_giờ_iso", re.compile(r"^\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$")),
    ("ngày_dmy", re.compile(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}$")),
    ("ngày_giờ_dmy", re.compile(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\s+\d{1,2}:\d{2}(:\d{2})?$")),
    ("ngày_không_năm", re.compile(r"^\d{1,2}[/-]\d{1,2}$")),
    ("ngày_chữ", re.compile(r"(thg|tháng|ngày)\s*\d", re.I)),
    ("giờ", re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")),
    ("điện_thoại", re.compile(r"^(\+?84|0)\d{8,10}$")),
    ("số_kèm_đơn_vị", re.compile(r"^-?\d+([.,]\d+)?\s*[^\d\s.,%].*$")),
    ("mã", re.compile(r"^[A-Za-z]{1,6}[-_]?\d{2,}$")),
    ("chữ_kèm_sđt", re.compile(r"\D.*\b0\d{9}\b")),
]


def classify(v) -> str:
    """Trả về tên mẫu của một giá trị ô."""
    if v is None:
        return "rỗng"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, datetime):
        return "datetime" if v.time() == dtime(0, 0) else "datetime+giờ"
    if isinstance(v, date):
        return "date"
    if isinstance(v, dtime):
        return "time"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float(nguyên)" if v.is_integer() else "float"
    s = str(v).strip()
    for name, rx in PATTERNS:
        if rx.search(s) if name in ("ngày_chữ", "chữ_kèm_sđt") else rx.match(s):
            return name
    return "chữ"


def is_empty(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def is_label(v) -> bool:
    """Ô trông giống tên cột: chuỗi không rỗng, không phải số/ngày."""
    return isinstance(v, str) and classify(v) in ("chữ", "mã")


def show(v) -> str:
    """Hiển thị gọn một ô trong bảng markdown."""
    if v is None:
        return ""
    if isinstance(v, datetime):
        s = v.strftime("%Y-%m-%d %H:%M") if v.time() != dtime(0, 0) else v.strftime("%Y-%m-%d")
        return "📅" + s
    if isinstance(v, float) and v.is_integer():
        s = f"{v:.1f}"
    else:
        s = str(v) if not isinstance(v, str) else repr(v)[1:-1] if "\n" in v else v
    s = s.replace("|", "\\|").replace("\n", "⏎")
    return s if len(s) <= MAX_CELL else s[: MAX_CELL - 1] + "…"


# ---------------------------------------------------------------------------
# Đọc file -> danh sách "bảng thô" (tên, list các dòng)
# ---------------------------------------------------------------------------

def read_xlsx(path: Path) -> list[tuple[str, list[tuple], dict]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
        # bỏ cột trống ở cuối (openpyxl đôi khi trả về max_column rộng hơn)
        width = max((max((i + 1 for i, v in enumerate(r) if not is_empty(v)), default=0) for r in rows), default=0)
        rows = [r[:width] + (None,) * (width - len(r)) for r in rows]
        out.append((ws.title, rows, {"sheet_state": ws.sheet_state}))
    wb.close()
    return out


def read_xlsx_merged(path: Path) -> dict[str, list[str]]:
    """Ô gộp (merged cells) theo sheet — cần mở chế độ thường nên chỉ làm với file nhỏ."""
    if path.stat().st_size > 3_000_000:
        return {}
    wb = openpyxl.load_workbook(path, data_only=True)
    res = {ws.title: [str(r) for r in ws.merged_cells.ranges] for ws in wb.worksheets}
    wb.close()
    return {k: v for k, v in res.items() if v}


def sniff_csv(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()[:200_000]
    for enc in ("utf-8-sig", "utf-16", "cp1258", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    try:
        sep = csv.Sniffer().sniff(text[:20_000], delimiters=",;\t|").delimiter
    except csv.Error:
        sep = ","
    return enc, sep


def read_csv(path: Path) -> list[tuple[str, list[tuple], dict]]:
    enc, sep = sniff_csv(path)
    df = pd.read_csv(path, header=None, dtype=str, keep_default_na=False, encoding=enc, sep=sep,
                     engine="python", on_bad_lines="warn")
    rows = [tuple(None if v == "" else v for v in r) for r in df.itertuples(index=False, name=None)]
    return [("(csv)", rows, {"encoding": enc, "sep": repr(sep)})]


def read_sqlite(path: Path) -> list[tuple[str, list[tuple], dict]]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out = []
    objs = con.execute("SELECT type, name, sql FROM sqlite_master WHERE type IN ('table','view') "
                       "AND name NOT LIKE 'sqlite_%' ORDER BY type, name").fetchall()
    for typ, name, sql in objs:
        cur = con.execute(f'SELECT * FROM "{name}"')
        cols = tuple(d[0] for d in cur.description)
        rows = [cols] + [tuple(r) for r in cur.fetchall()]
        out.append((f"{typ}:{name}", rows, {"sql": sql}))
    fks = []
    for typ, name, _ in objs:
        for fk in con.execute(f'PRAGMA foreign_key_list("{name}")'):
            fks.append(f"{name}.{fk[3]} -> {fk[2]}.{fk[4]}")
    con.close()
    if fks:
        out[0][2]["foreign_keys"] = fks
    return out


# ---------------------------------------------------------------------------
# Phân tích một bảng thô
# ---------------------------------------------------------------------------

TOTAL_RE = re.compile(r"^\s*(tổng|cộng|total)\b", re.I)


def find_header(rows: list[tuple]) -> int | None:
    """Tìm chỉ số dòng header thật: dòng đầu tiên mà đa số ô có giá trị là nhãn chữ,
    và đủ rộng so với các dòng dữ liệu bên dưới."""
    scan = rows[:HEADER_SCAN]
    if not scan:
        return None
    nonempty = [sum(not is_empty(v) for v in r) for r in rows[: HEADER_SCAN + 30]]
    width = max(nonempty) if nonempty else 0
    for i, r in enumerate(scan):
        n_label = sum(is_label(v) for v in r)
        n_ne = nonempty[i]
        if n_ne >= 2 and n_label >= 0.7 * n_ne and n_ne >= 0.6 * width:
            return i
    return None


def analyze(rows: list[tuple]) -> dict:
    h = find_header(rows)
    header = rows[h] if h is not None else tuple(f"c{j}" for j in range(len(rows[0]) if rows else 0))
    body = rows[(h + 1) if h is not None else 0:]
    n_blank = sum(all(is_empty(v) for v in r) for r in body)
    data = [r for r in body if not all(is_empty(v) for v in r)]

    # dòng header lặp lại giữa dữ liệu (file ghép nhiều lần xuất)
    n_rep_header = sum(1 for r in data if h is not None and r == header)
    # dòng tổng: cuối bảng hoặc tổng theo ngày xen giữa ("Tổng ngày 01/04", "Cộng ngày 01/05/2025"),
    # có thể nằm ở bất kỳ cột nào (cột khách, cột tên hàng...)
    total_rows = [r for r in data if r != header and any(isinstance(v, str) and TOTAL_RE.match(v) for v in r)]
    # dòng trùng hoàn toàn
    cnt = Counter(data)
    dups = [(r, c) for r, c in cnt.items() if c > 1]
    n_dup_rows = sum(c - 1 for _, c in dups)

    cols = []
    for j, name in enumerate(header):
        vals = [r[j] if j < len(r) else None for r in data]
        pats = Counter()
        ex: dict[str, list] = {}
        for v in vals:
            p = classify(v)
            pats[p] += 1
            if p != "rỗng":
                lst = ex.setdefault(p, [])
                if len(lst) < EXAMPLES and v not in lst:
                    lst.append(v)
        nonempty = [v for v in vals if not is_empty(v)]
        uniq = Counter(str(v).strip() for v in nonempty)
        # ô trống "kiểu nhóm dòng": trống nhưng dòng trước có giá trị
        n_fill = sum(1 for k in range(1, len(vals)) if is_empty(vals[k]) and not is_empty(vals[k - 1]))
        cols.append({
            "name": name, "n": len(vals), "n_empty": len(vals) - len(nonempty),
            "patterns": pats, "examples": ex, "n_unique": len(uniq),
            "enum": uniq.most_common(ENUM_MAX) if 0 < len(uniq) <= ENUM_MAX and len(nonempty) >= 5 else None,
            "n_fill": n_fill,
        })
    return {"header_idx": h, "header": header, "n_data": len(data), "n_blank": n_blank,
            "n_rep_header": n_rep_header, "total_rows": total_rows[:3], "n_total_rows": len(total_rows),
            "n_dup_rows": n_dup_rows, "dup_example": dups[0] if dups else None, "cols": cols}


# ---------------------------------------------------------------------------
# Xuất markdown
# ---------------------------------------------------------------------------

def md_rows(rows: list[tuple], start: int) -> list[str]:
    if not rows:
        return []
    w = max(len(r) for r in rows)
    out = ["| dòng | " + " | ".join(f"c{j}" for j in range(w)) + " |",
           "|---|" + "---|" * w]
    for i, r in enumerate(rows):
        cells = [show(v) for v in r] + [""] * (w - len(r))
        out.append(f"| {start + i} | " + " | ".join(cells) + " |")
    return out


def md_table(name: str, rows: list[tuple], meta: dict, a: dict) -> list[str]:
    L = [f"#### {name}"]
    for k, v in meta.items():
        if k == "sql":
            L.append(f"```sql\n{v}\n```")
        elif k == "foreign_keys":
            L.append("- khóa ngoại: " + "; ".join(v))
        elif k != "sheet_state" or v != "visible":
            L.append(f"- {k}: {v}")
    h = a["header_idx"]
    L.append(f"- tổng dòng thô: {len(rows)} | dòng header (0-based): **{h}** | dòng dữ liệu: {a['n_data']}"
             f" | dòng trống: {a['n_blank']}")
    flags = []
    if h:
        flags.append(f"header LỆCH {h} dòng")
    if a["n_rep_header"]:
        flags.append(f"header lặp lại {a['n_rep_header']} lần trong dữ liệu")
    if a["n_total_rows"]:
        flags.append(f"{a['n_total_rows']} dòng tổng/cộng")
    if a["n_dup_rows"]:
        flags.append(f"{a['n_dup_rows']} dòng trùng hoàn toàn")
    if flags:
        L.append("- ⚠️ " + "; ".join(flags))
    if a["dup_example"]:
        r, c = a["dup_example"]
        L.append(f"- ví dụ dòng trùng (x{c}): `{' | '.join(show(v) for v in r)}`")
    for r in a["total_rows"]:
        L.append(f"- ví dụ dòng tổng: `{' | '.join(show(v) for v in r)}`")

    end = (h + 1 if h is not None else 0) + N_HEAD
    L.append("")
    L += md_rows(rows[:end], 0)
    L.append("")
    L.append("| # | cột | trống% | ô trống sau ô có giá trị | số giá trị khác | mẫu giá trị (số ô) | ví dụ |")
    L.append("|---|---|---|---|---|---|---|")
    for j, c in enumerate(a["cols"]):
        n = c["n"] or 1
        pats = ", ".join(f"{p}:{k}" for p, k in c["patterns"].most_common() if p != "rỗng")
        exs = "; ".join(f"{p}→" + " / ".join(f"`{show(v)}`" for v in vs) for p, vs in c["examples"].items())
        L.append(f"| {j} | {show(c['name'])} | {100 * c['n_empty'] / n:.0f} | {c['n_fill']} | {c['n_unique']}"
                 f" | {pats} | {exs} |")
    enums = [(c["name"], c["enum"]) for c in a["cols"] if c["enum"]]
    if enums:
        L.append("")
        L.append("Giá trị của các cột ít giá trị:")
        for name, en in enums:
            L.append(f"- **{show(name)}**: " + ", ".join(f"`{show(v)}`({k})" for v, k in en))
    L.append("")
    return L


def survey_file(path: Path) -> tuple[list[str], tuple, str]:
    """Trả về (các dòng markdown, chữ ký cấu trúc file, tóm tắt một dòng).

    Chữ ký = danh sách (dòng header, tên cột) của các sheet; hai file cùng chữ ký
    (vd. 17 file bán hàng theo tháng) chỉ cần in chi tiết một lần.
    """
    ext = path.suffix.lower()
    L = [f"### 📄 {path.name}  ({path.stat().st_size / 1024:.0f} KB)"]
    try:
        if ext in (".xlsx", ".xlsm"):
            tables = read_xlsx(path)
            merged = read_xlsx_merged(path)
        elif ext == ".csv":
            tables, merged = read_csv(path), {}
        elif ext in (".sqlite", ".db", ".sqlite3"):
            tables, merged = read_sqlite(path), {}
        else:
            return L + [f"- (bỏ qua, đuôi {ext})", ""], (), ""
    except Exception as e:  # noqa: BLE001 — khảo sát: ghi lỗi rồi đi tiếp
        return L + [f"- ❌ LỖI ĐỌC: {type(e).__name__}: {e}", ""], (), ""

    if ext in (".xlsx", ".xlsm"):
        L.append(f"- số sheet: {len(tables)}: " + ", ".join(f"`{t[0]}`({len(t[1])} dòng)" for t in tables))

    file_sig = []
    n_data = n_dup = n_total = 0
    prev_sig = None
    same_as = []
    for name, rows, meta in tables:
        if not rows:
            L.append(f"#### {name}\n- (trống)\n")
            continue
        a = analyze(rows)
        n_data += a["n_data"]
        n_dup += a["n_dup_rows"]
        n_total += a["n_total_rows"]
        sig = (a["header_idx"], tuple(show(v) for v in a["header"]))
        file_sig.append(sig)
        if sig == prev_sig:
            same_as.append(f"`{name}`({a['n_data']} dòng"
                           + (f", {a['n_dup_rows']} trùng" if a["n_dup_rows"] else "") + ")")
            continue
        if same_as:
            L.append(f"- Các sheet sau CÙNG header với sheet trên: {', '.join(same_as)}\n")
            same_as = []
        prev_sig = sig
        L += md_table(name, rows, meta, a)
        if name in merged:
            L.append(f"- ô gộp: {', '.join(merged[name][:20])}" + (" …" if len(merged[name]) > 20 else ""))
            L.append("")
    if same_as:
        L.append(f"- Các sheet sau CÙNG header với sheet trên: {', '.join(same_as)}\n")
    short = (f"`{path.name}`({n_data} dòng"
             + (f", {n_dup} trùng" if n_dup else "") + (f", {n_total} dòng tổng" if n_total else "") + ")")
    return L, tuple(file_sig), short


README_KEEP = 6  # danh sách / bảng trong README dài hơn thì chỉ giữ ngần này dòng đầu


def compact_readme(text: str, full: bool) -> str:
    """Rút gọn các khối dòng liệt kê dài (vd. hàng trăm dòng quy đổi đơn vị) trong README."""
    if full:
        return text
    out, run = [], []

    def flush():
        if len(run) > README_KEEP + 2:
            out.extend(run[:README_KEEP])
            out.append(f"  - … (lược {len(run) - README_KEEP} dòng cùng dạng; xem README gốc)")
        else:
            out.extend(run)
        run.clear()

    for line in text.splitlines():
        is_item = re.match(r"^\s*([-*]|\d+\.)\s", line) or line.lstrip().startswith("|")
        # dòng tiêu đề bảng markdown (|---|) luôn giữ, không tính vào khối
        if is_item and not (run and line.lstrip().startswith("|") != run[-1].lstrip().startswith("|")):
            run.append(line)
        else:
            flush()
            if is_item:
                run.append(line)
            else:
                out.append(line)
    flush()
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="survey_raw.md")
    ap.add_argument("--only", help="danh sách tiệm, cách nhau dấu phẩy")
    ap.add_argument("--full-readme", action="store_true", help="in README nguyên văn, không rút gọn")
    args = ap.parse_args(argv)
    only = set(args.only.split(",")) if args.only else None

    out = ["# Khảo sát dữ liệu DataMate (sinh tự động bởi survey.py)", "",
           "Quy ước: dòng đánh số từ 0 theo file thô; `📅` = ô kiểu ngày của Excel; "
           "'ô trống sau ô có giá trị' = số ô trống mà dòng ngay trên có giá trị (dấu hiệu ô gộp / nhóm dòng).", ""]
    t0 = time.time()
    for split, root in ROOTS:
        for shop in sorted(p for p in root.iterdir() if p.is_dir()):
            if only and shop.name not in only:
                continue
            print(f"[{time.time() - t0:6.1f}s] {split}/{shop.name}", file=sys.stderr)
            out += [f"## {split} / {shop.name}", ""]
            readme = shop / "README.md"
            if readme.exists():
                out += ["<details open><summary>README.md</summary>", "",
                        compact_readme(readme.read_text(encoding="utf-8").strip(), args.full_readme), "", "</details>", ""]
            seen: dict[tuple, list] = {}  # chữ ký cấu trúc -> danh sách tóm tắt các file trùng cấu trúc
            for f in sorted(shop.iterdir()):
                if f.name == "README.md" or f.name.startswith("."):
                    continue
                lines, sig, short = survey_file(f)
                if sig and sig in seen:
                    seen[sig].append(short)
                    continue
                if sig:
                    seen[sig] = [lines[0].removeprefix("### 📄 ").split("  (")[0], len(out) + len(lines)]
                out += lines + [""]
            # ghi chú các file cùng cấu trúc ngay sau file đầu tiên của nhóm (chèn từ cuối lên để giữ chỉ số)
            for first, pos, *others in sorted(seen.values(), key=lambda v: -v[1]):
                if others:
                    out.insert(pos, f"- **{len(others)} file khác CÙNG CẤU TRÚC với `{first}`**: {', '.join(others)}")
            out.append("---")
            out.append("")
    Path(args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"Xong sau {time.time() - t0:.0f}s -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
