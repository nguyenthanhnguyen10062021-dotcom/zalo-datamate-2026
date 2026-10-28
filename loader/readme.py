"""Đọc README.md của một tiệm: danh sách file, mô tả cột, quy ước, ngày cuối dữ liệu, quy đổi đơn vị.

Chỉ dựa vào các mẫu câu chung của README (giống nhau giữa các tiệm), không có gì riêng cho tiệm nào.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .parsers import col_key, name_key


@dataclass
class Section:
    """Một mục '## Cột trong `file`[, sheet `sheet`]'."""
    file_pattern: str            # tên file, có thể chứa mẫu <tháng>
    sheet: str | None
    columns: dict[str, str]      # tên cột -> mô tả

    def matches(self, file: str, sheet: str | None) -> bool:
        pat = re.escape(self.file_pattern)
        pat = re.sub(r"\\<[^>]*\\>|<[^>]*>", r".+?", pat)
        ok_file = re.fullmatch(pat, file, flags=re.I) is not None or \
            Path(self.file_pattern).stem.lower() == Path(file).stem.lower()
        if not ok_file:
            # mục ghi theo tên danh sách / sheet (vd file gộp nhiều danh sách)
            ok_file = sheet is not None and Path(self.file_pattern).stem.lower() == str(sheet).lower()
        if not ok_file:
            return False
        return self.sheet is None or sheet is None or self.sheet.lower() == str(sheet).lower()


@dataclass
class ConventionPair:
    """Cặp cột–mô tả trích từ phần Quy ước: '**Giá trị** là số tiền trả lần đó',
    '`chi_tiet_don.TriGia` là thành tiền của dòng'."""
    column: str
    desc: str
    topic: str
    table: str | None = None     # với dạng `bang.cot`


@dataclass
class UnitConversion:
    ten_hang: str
    don_vi_lon: str
    he_so: float
    don_vi_nho: str


@dataclass
class ReadmeInfo:
    path: Path | None
    text: str = ""
    files: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    conventions: dict[str, str] = field(default_factory=dict)     # chủ đề -> câu
    convention_pairs: list[ConventionPair] = field(default_factory=list)
    end_date: date | None = None
    conversions: list[UnitConversion] = field(default_factory=list)
    conversion_sources: list[str] = field(default_factory=list)   # file/bảng chứa hệ số quy đổi

    def all_pairs(self) -> list[tuple[str, str]]:
        """Mọi cặp (tên cột, mô tả) trong các mục 'Cột trong'."""
        return [(c, d) for s in self.sections for c, d in s.columns.items()]

    def section_for(self, file: str, sheet: str | None, columns: list[str]) -> Section | None:
        """Mục mô tả ứng với một bảng: ưu tiên khớp tên file/sheet, sau đó khớp nhiều tên cột nhất."""
        cand = [s for s in self.sections if s.matches(file, sheet)]
        keys = {col_key(c) for c in columns}
        if cand:
            return max(cand, key=lambda s: len(keys & {col_key(c) for c in s.columns}))
        best, best_n = None, 0
        for s in self.sections:
            n = len(keys & {col_key(c) for c in s.columns})
            if n > best_n:
                best, best_n = s, n
        # chỉ nhận khi trùng phần lớn tên cột của mục
        if best is not None and best_n >= max(2, 0.6 * len(best.columns)):
            return best
        return None

    def convention_desc(self, column: str, table: str | None = None) -> str | None:
        k = col_key(column)
        for p in self.convention_pairs:
            if col_key(p.column) == k and (p.table is None or table is None or
                                           col_key(p.table) == col_key(table)):
                return p.desc
        return None


_PAIR_RE = re.compile(r"^\s*-\s+\*\*(.+?)\*\*:\s*(.+?)\s*$")
_SECTION_RE = re.compile(r"^##\s+Cột trong\s+`([^`]+)`(?:\s*,\s*sheet\s+`([^`]+)`)?", re.I)
_CONV_ITEM_RE = re.compile(r"^\s*-\s+(.+?):\s*1\s+(.+?)\s*=\s*([\d.,]+)\s+(.+?)\s*$")
_END_RE = re.compile(r"Dữ liệu có đến hết\s+(\d{1,2})/(\d{1,2})/(\d{4})")
# '**X** là ...' , '**X** đúng (TRUE/1) là ...' , '`bang.cot` là ...'
_IS_RE = re.compile(r"\*\*([^*]+)\*\*\s+(?:đúng\s*\([^)]*\)\s*)?là\s+([^;]+?)(?=;|\.\s|\.$|$)")
_IS_TICK_RE = re.compile(r"`(\w+)\.(\w+)`\s+(?:\([^)]*\)\s*)?(?:đúng\s*\([^)]*\)\s*)?là\s+([^;]+?)(?=;|\.\s|\.$|$)")


def parse_readme(path: str | Path | None) -> ReadmeInfo:
    if path is None or not Path(path).exists():
        return ReadmeInfo(path=None)
    path = Path(path)
    text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
    info = ReadmeInfo(path=path, text=text)

    m = _END_RE.search(text)
    if m:
        info.end_date = date(int(m[3]), int(m[2]), int(m[1]))

    heading = None
    cur: Section | None = None
    conv_topic = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur, conv_topic = None, None
            heading = line[3:].strip()
            sm = _SECTION_RE.match(line)
            if sm:
                cur = Section(file_pattern=sm[1], sheet=sm[2], columns={})
                info.sections.append(cur)
            continue
        if heading == "File":
            fm = re.match(r"^\s*-\s+`([^`]+)`", line)
            if fm:
                info.files.append(fm[1])
            continue
        if cur is not None:
            pm = _PAIR_RE.match(line)
            if pm:
                cur.columns[pm[1].strip()] = pm[2].strip()
            continue
        if heading and heading.lower().startswith("quy ước"):
            pm = _PAIR_RE.match(line)
            if pm:
                conv_topic = pm[1].strip()
                body = pm[2].strip()
                info.conventions[conv_topic] = body
                _collect_pairs(info, conv_topic, body)
                for src in re.findall(r"hệ số quy đổi ở (?:bảng\s+)?`([^`]+)`", body):
                    info.conversion_sources.append(src)
                continue
            cm = _CONV_ITEM_RE.match(line)
            if cm and conv_topic and name_key(conv_topic).startswith("quy doi"):
                he_so = float(cm[3].replace(",", "."))
                info.conversions.append(UnitConversion(cm[1].strip(), cm[2].strip(), he_so, cm[4].strip()))
    return info


def _collect_pairs(info: ReadmeInfo, topic: str, body: str) -> None:
    for m in _IS_TICK_RE.finditer(body):
        info.convention_pairs.append(ConventionPair(m[2], m[3].strip(), topic, table=m[1]))
    for m in _IS_RE.finditer(body):
        info.convention_pairs.append(ConventionPair(m[1].strip(), m[2].strip(), topic))
