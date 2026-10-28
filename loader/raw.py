"""Bảng thô sạch: dựng cho MỌI file/sheet của tiệm, không cần biết bảng đó là gì.

Các bước (T0 trong DESIGN.md):
  tìm header -> bỏ dòng trống, header lặp, dòng tổng ('^(tổng|cộng)'), dòng ghi chú 1 ô
  -> gộp sheet/file cùng cấu trúc (thêm cột nguồn __file, __sheet, __row)
  -> suy kiểu từng cột (ngày / số / chữ) rồi parse THEO TỪNG Ô
  -> (chỉ cho bản lưu parquet) điền xuống nếu nhận ra cấu trúc nhóm dòng.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .io import RawSheet, find_header, header_names, read_any
from .parsers import (clean_str, col_key, is_strong_date, parse_date, parse_money, parse_quantity,
                      year_from_name)

META = ["__file", "__sheet", "__row"]
TOTAL_RE = re.compile(r"^\s*(tổng|cộng|total)\b", re.I)
CODE_RE = re.compile(r"^[A-Za-z]{1,6}[-_]?\d{2,}$")
DATE_NAME_HINT = re.compile(r"ngay|thoigian|date|han|gio|time")


@dataclass
class RawTable:
    name: str
    columns: list[str]
    data: pd.DataFrame                    # giá trị gốc từng ô (object) + cột META
    sources: list[dict] = field(default_factory=list)
    total_rows: list[dict] = field(default_factory=list)   # dòng tổng đã bỏ (giữ để kiểm tra)
    kinds: dict[str, str] = field(default_factory=dict)    # cột -> date | number | text | empty
    typed: pd.DataFrame | None = None
    filled: list[str] = field(default_factory=list)        # cột đã điền xuống trong bản parquet
    error: str | None = None

    def year_hints(self) -> pd.Series:
        """Năm suy từ tên sheet (ưu tiên) hoặc tên file — cho ngày không ghi năm (rulebook §8)."""
        sh = self.data["__sheet"].map(lambda s: year_from_name(s))
        fi = self.data["__file"].map(lambda s: year_from_name(s))
        return sh.fillna(fi)


def _is_empty(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or (isinstance(v, str) and not v.strip())


def _clean_sheet(sh: RawSheet) -> tuple[list[str], list[tuple], dict, list[dict]] | None:
    rows = sh.rows
    if not rows:
        return None
    h = sh.header_idx if sh.header_idx is not None else find_header(rows)
    if h is None:
        return None
    names = header_names(rows, h)
    hdr_key = [col_key(n) for n in names]
    width = len(names)
    body, totals = [], []
    stats = {"header_lap": 0, "dong_tong": 0, "dong_trong": 0, "dong_ghi_chu": 0}
    for i in range(h + 1, len(rows)):
        r = tuple(rows[i][:width]) + (None,) * (width - len(rows[i]))
        nonempty = [v for v in r if not _is_empty(v)]
        if not nonempty:
            stats["dong_trong"] += 1
            continue
        if [col_key(v) if isinstance(v, str) else None for v in r] == hdr_key:
            stats["header_lap"] += 1
            continue
        if any(isinstance(v, str) and TOTAL_RE.match(v) for v in r):
            stats["dong_tong"] += 1
            totals.append({"__file": sh.file, "__sheet": sh.sheet, "__row": i,
                           "cells": [str(v) if not _is_empty(v) else None for v in r]})
            continue
        if len(nonempty) <= 1 and width >= 4:
            stats["dong_ghi_chu"] += 1
            continue
        body.append(r + (sh.file, sh.sheet, i))
    src = {"file": sh.file, "sheet": sh.sheet, "dong_header": h, "so_dong": len(body), **stats}
    return names, body, src, totals


_STEM_SUFFIX = re.compile(r"([_\-\s]?(T|Thang|Tháng)?\d{1,2}[_\-\s]\d{4}|[_\-\s]\d{4}|[_\-\s]\d{1,2})$", re.I)


def _base_name(file: str, sheet: str | None, multi_struct: bool) -> str:
    stem = Path(file).stem
    for _ in range(2):
        stem = _STEM_SUFFIX.sub("", stem)
    if sheet and (multi_struct or Path(file).suffix.lower() in (".sqlite", ".db", ".sqlite3")):
        return f"{stem}__{sheet}" if Path(file).suffix.lower() not in (".sqlite", ".db", ".sqlite3") else sheet
    return stem


def _safe(name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_") or "bang"


def read_raw_tables(business_dir: str | Path) -> tuple[list[RawTable], list[dict]]:
    """Đọc mọi file của tiệm -> bảng thô (chưa parse). Trả thêm danh sách lỗi đọc."""
    business_dir = Path(business_dir)
    groups: "OrderedDict[tuple, dict]" = OrderedDict()
    errors = []
    for path in sorted(business_dir.iterdir()):
        if path.name.lower() == "readme.md" or path.name.startswith(".") or not path.is_file():
            continue
        try:
            sheets = read_any(path)
        except Exception as e:  # noqa: BLE001 — một file lỗi không được làm hỏng cả tiệm
            errors.append({"file": path.name, "loi": f"{type(e).__name__}: {e}"})
            continue
        cleaned = []
        for sh in sheets:
            res = _clean_sheet(sh)
            if res is None:
                errors.append({"file": path.name, "sheet": sh.sheet, "loi": "không tìm được header"})
                continue
            cleaned.append((sh, res))
        n_struct = len({tuple(col_key(c) for c in res[0]) for _, res in cleaned})
        for sh, (names, body, src, totals) in cleaned:
            sig = tuple(col_key(c) for c in names)
            g = groups.get(sig)
            if g is None:
                g = groups[sig] = {"name": _base_name(sh.file, sh.sheet, n_struct > 1), "names": names,
                                   "rows": [], "sources": [], "totals": []}
            g["rows"].extend(body)
            g["sources"].append(src)
            g["totals"].extend(totals)

    tables, used = [], set()
    for g in groups.values():
        name = _safe(g["name"])
        base, k = name, 2
        while name in used:
            name, k = f"{base}_{k}", k + 1
        used.add(name)
        df = pd.DataFrame(g["rows"], columns=g["names"] + META, dtype=object)
        tables.append(RawTable(name=name, columns=g["names"], data=df, sources=g["sources"], total_rows=g["totals"]))
    return tables, errors


# ---------------------------------------------------------------------------
# Suy kiểu và parse từng ô
# ---------------------------------------------------------------------------

def _is_serial(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return 20000 <= v <= 80000
    return isinstance(v, str) and re.fullmatch(r"\d{5}(\.\d+)?", v.strip()) is not None and 20000 <= float(v) <= 80000


def infer_kind(name: str, values: list) -> str:
    vals = [v for v in values if not _is_empty(v)]
    if not vals:
        return "empty"
    if len(vals) > 4000:
        step = len(vals) // 4000 + 1
        vals = vals[::step]
    n = len(vals)
    strong = sum(is_strong_date(v) or (isinstance(v, str) and parse_date(v, 2000, False) is not None) for v in vals)
    serial = sum(_is_serial(v) for v in vals)
    hint = DATE_NAME_HINT.search(col_key(name)) is not None
    if strong / n >= 0.3 and (strong + serial) / n >= 0.95:
        return "date"
    if hint and (strong + serial) / n >= 0.95:
        return "date"
    num = sum(parse_money(v) is not None for v in vals)
    if num / n >= 0.95:
        return "number"
    qty = sum(parse_quantity(v)[0] is not None for v in vals)
    if qty / n >= 0.95 and num / n >= 0.3:
        return "number"
    return "text"


def _parse_cell(kind: str, v, year):
    if _is_empty(v):
        return None
    if kind == "date":
        return parse_date(v, year)
    if kind == "number":
        x = parse_money(v)
        return x if x is not None else parse_quantity(v)[0]
    s = clean_str(v)
    if s is not None and isinstance(v, float) and v.is_integer():
        s = str(int(v))
    return s


def type_table(t: RawTable) -> RawTable:
    years = t.year_hints().tolist()
    typed = {}
    for c in t.columns:
        col = t.data[c].tolist()
        kind = infer_kind(c, col)
        t.kinds[c] = kind
        vals = [_parse_cell(kind, v, int(y) if y == y and y is not None else None) for v, y in zip(col, years)]
        if kind == "date":
            typed[c] = pd.to_datetime(pd.Series(vals, dtype=object), errors="coerce")
        elif kind == "number":
            typed[c] = pd.to_numeric(pd.Series(vals, dtype=object), errors="coerce")
        else:
            typed[c] = pd.Series(vals, dtype="string")
    for m in META:
        typed[m] = t.data[m].astype("string") if m != "__row" else t.data[m].astype("int64")
    t.typed = pd.DataFrame(typed)
    return t


# ---------------------------------------------------------------------------
# Điền xuống (chỉ cho bản parquet của bảng thô)
# ---------------------------------------------------------------------------

def _primary_id(t: RawTable, cols: list[str]) -> str | None:
    """Cột định danh chính của bảng: cột mã (dạng CODE123) có nhiều giá trị khác nhau nhất;
    không có cột mã thì cột STT. Cột mã ít giá trị (mã khách, mã NV) không phải định danh chính."""
    best, best_n = None, 0
    for c in cols:
        vals = t.typed[c].dropna().astype(str)
        if len(vals) and vals.str.fullmatch(CODE_RE).mean() >= 0.8 and vals.nunique() > best_n:
            best, best_n = c, vals.nunique()
    if best is None:
        best = next((c for c in cols if col_key(c) in ("stt", "sothutu")), None)
    return best


def fill_down_raw(t: RawTable) -> RawTable:
    """Nhận ra cấu trúc nhóm dòng: cột định danh chính (mã đơn / STT) chỉ ghi ở dòng đầu nhóm và >= 2 cột
    trống CÙNG những dòng đó (thông tin cấp nhóm) -> lấy giá trị dòng đầu nhóm, trong phạm vi từng sheet.
    Cột trống vì không có dữ liệu (vd mã khách trống = khách lẻ) không bị điền vì định danh chính vẫn có."""
    df = t.typed
    if df is None or len(df) < 10:
        return t
    cols = [c for c in t.columns if t.kinds.get(c) != "empty"]
    pid = _primary_id(t, cols)
    if pid is None:
        return t
    empty = {c: df[c].isna().to_numpy() for c in cols}
    if not (0.05 <= empty[pid].mean() <= 0.95):
        return t
    group = [d for d in cols if (empty[d] == empty[pid]).mean() >= 0.98]
    others = [d for d in cols if d not in group]
    if len(group) < 2 or not others or not any((~empty[d] & empty[pid]).any() for d in others):
        return t
    seg = (df["__file"].astype(str) + "|" + df["__sheet"].astype(str)).to_numpy()
    block = np.zeros(len(df), dtype=np.int64)
    cur, last_seg = -1, None
    for i in range(len(df)):  # khối = dòng có định danh + các dòng trống định danh ngay sau nó (cùng sheet)
        if seg[i] != last_seg or not empty[pid][i]:
            cur, last_seg = cur + 1, seg[i]
        block[i] = cur
    keys = pd.Series(block, index=df.index)
    for d in group:
        df[d] = df[d].where(~df[d].isna(), df.groupby(keys, sort=False)[d].transform("first"))
    t.filled.extend(group)
    t.typed = df
    return t


# ---------------------------------------------------------------------------
# Lưu
# ---------------------------------------------------------------------------

def save_raw(tables: list[RawTable], out_dir: Path, describe: dict | None = None,
             concepts: dict | None = None) -> list[dict]:
    """Ghi raw/<bảng>.parquet và trả về catalog (list dict) để ghi raw_catalog.json."""
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    catalog = []
    for t in tables:
        entry = {"bang": t.name, "nguon": t.sources, "so_dong": int(len(t.data)), "dong_tong_da_bo": len(t.total_rows),
                 "loi": t.error, "cot": []}
        if t.typed is not None:
            try:
                out = t.typed.copy()
                out.columns = [str(c) for c in out.columns]
                out.to_parquet(raw_dir / f"{t.name}.parquet", index=False)
                entry["file"] = f"raw/{t.name}.parquet"
            except Exception as e:  # noqa: BLE001
                entry["loi"] = f"ghi parquet lỗi: {type(e).__name__}: {e}"
            for c in t.columns:
                s = t.typed[c]
                samples = [str(x) for x in s.dropna().unique()[:5]]
                entry["cot"].append({
                    "ten_goc": c,
                    "mo_ta": (describe or {}).get((t.name, c)),
                    "khai_niem": (concepts or {}).get((t.name, c)),
                    "kieu": t.kinds.get(c),
                    "mau": samples,
                    "pct_trong": round(float(s.isna().mean() * 100), 1) if len(s) else 100.0,
                    "dien_xuong": c in t.filled,
                })
        catalog.append(entry)
    (out_dir / "raw_catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1, default=str),
                                              encoding="utf-8")
    return catalog
