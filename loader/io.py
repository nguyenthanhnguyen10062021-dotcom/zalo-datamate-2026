"""Mở file dữ liệu (csv / xlsx / sqlite) ở chế độ CHỈ ĐỌC và tìm dòng header.

Kết quả là danh sách RawSheet: mỗi sheet (xlsx), mỗi file (csv) hoặc mỗi bảng (sqlite) là một RawSheet
với các dòng thô (tuple giá trị gốc), chưa parse.
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import openpyxl
import pandas as pd

from .parsers import clean_str, is_strong_date, parse_number

HEADER_SCAN = 25


@dataclass
class RawSheet:
    file: str            # tên file
    sheet: str | None    # tên sheet (xlsx) / tên bảng (sqlite) / None (csv)
    kind: str            # xlsx | csv | sqlite
    rows: list[tuple]    # dòng thô
    header_idx: int | None = None   # sqlite: 0 (tên cột là dòng đầu)


def _is_empty(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _trim(rows: list[tuple]) -> list[tuple]:
    width = 0
    for r in rows:
        for i in range(len(r) - 1, -1, -1):
            if not _is_empty(r[i]):
                width = max(width, i + 1)
                break
    return [tuple(r[:width]) + (None,) * (width - len(r)) for r in rows]


def read_xlsx(path: Path) -> list[RawSheet]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        out = []
        for ws in wb.worksheets:
            rows = _trim([tuple(r) for r in ws.iter_rows(values_only=True)])
            out.append(RawSheet(path.name, ws.title, "xlsx", rows))
        return out
    finally:
        wb.close()


def _sniff_csv(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()[:200_000]
    text, enc = None, "utf-8-sig"
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


def read_csv(path: Path) -> list[RawSheet]:
    enc, sep = _sniff_csv(path)
    df = pd.read_csv(path, header=None, dtype=str, keep_default_na=False, encoding=enc, sep=sep,
                     engine="c" if len(sep) == 1 else "python", on_bad_lines="skip")
    rows = [tuple(None if v == "" else v for v in r) for r in df.itertuples(index=False, name=None)]
    return [RawSheet(path.name, None, "csv", _trim(rows))]


def read_sqlite(path: Path) -> list[RawSheet]:
    con = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        out = []
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for name in names:
            cur = con.execute(f'SELECT * FROM "{name}"')
            cols = tuple(d[0] for d in cur.description)
            rows = [cols] + [tuple(r) for r in cur.fetchall()]
            out.append(RawSheet(path.name, name, "sqlite", rows, header_idx=0))
        return out
    finally:
        con.close()


def read_any(path: Path) -> list[RawSheet]:
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return read_xlsx(path)
    if ext in (".csv", ".tsv", ".txt"):
        return read_csv(path)
    if ext in (".sqlite", ".sqlite3", ".db"):
        return read_sqlite(path)
    return []


def _is_label(v) -> bool:
    """Ô trông như tên cột: chuỗi, không phải số, không phải ngày."""
    if not isinstance(v, str):
        return False
    s = v.strip()
    return bool(s) and parse_number(s) is None and not is_strong_date(s)


def find_header(rows: list[tuple]) -> int | None:
    """Dòng header: dòng đầu tiên mà >= 70% ô có giá trị là nhãn chữ và đủ rộng so với dữ liệu bên dưới."""
    if not rows:
        return None
    nonempty = [sum(not _is_empty(v) for v in r) for r in rows[: HEADER_SCAN + 30]]
    width = max(nonempty) if nonempty else 0
    for i, r in enumerate(rows[:HEADER_SCAN]):
        n_ne = nonempty[i]
        n_label = sum(_is_label(v) for v in r)
        if n_ne >= 2 and n_label >= 0.7 * n_ne and n_ne >= 0.6 * width:
            return i
    return None


def header_names(rows: list[tuple], h: int) -> list[str]:
    """Tên cột từ dòng header; header gộp 2 dòng: ô trống ở dòng header lấy tên ở dòng ngay trên.
    Tên rỗng -> 'cot_<j>'; tên trùng -> thêm hậu tố '_2', '_3'."""
    hdr = list(rows[h])
    above = rows[h - 1] if h > 0 else ()
    names, seen = [], {}
    for j, v in enumerate(hdr):
        s = clean_str(v)
        if s is None and j < len(above):
            s = clean_str(above[j])
        if s is None:
            s = f"cot_{j}"
        base = s
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            s = f"{base}_{seen[base]}"
        names.append(s)
    return names
