"""Read the supplied split's rules; reject unsupported semantics explicitly."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import unicodedata


class UnsupportedRule(ValueError):
    """A requested operation cannot implement this rulebook safely."""


def folded(text: str) -> str:
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', text.replace('**', '').replace('`', '')).strip()


@dataclass(frozen=True)
class Rulebook:
    text: str
    source: str
    fingerprint: str
    rows: dict[str, str | None]

    @classmethod
    def from_text(cls, text: str, source: str = '<text>'):
        rows, scoped = {}, {}
        section = ''
        for line in text.splitlines():
            if line.strip().startswith('#'):
                section = folded(line.strip())
            if line.strip().startswith('|'):
                parts = [x.strip() for x in line.strip().strip('|').split('|')]
                if len(parts) == 2 and parts[0] and not parts[0].startswith('-'):
                    key = folded(parts[0])
                    if (section,key) in scoped and scoped[section,key] != parts[1]:
                        raise UnsupportedRule(f'Conflicting rule: {parts[0]}')
                    scoped[section,key] = parts[1]
                    # An ambiguous cross-industry label is unusable without an
                    # industry-specific implementation, but must not block core sales.
                    rows[key] = parts[1] if key not in rows or rows[key] == parts[1] else None
        if not rows:
            raise UnsupportedRule('No supported rule table found')
        return cls(text, str(source), sha256(text.encode('utf-8')).hexdigest(), rows)

    @classmethod
    def from_path(cls, path: str | Path):
        path = Path(path)
        return cls.from_text(path.read_text(encoding='utf-8-sig'), str(path.resolve()))

    def require(self, label: str, *fragments: str) -> str:
        value = self.rows.get(folded(label), '')
        if not value or not all(folded(part) in folded(value) for part in fragments):
            raise UnsupportedRule(f'Unsupported/missing rule {label!r} in {self.source}')
        return value.replace('**', '').replace('`', '')

    def require_text(self, *fragments: str):
        if not all(folded(part) in folded(self.text) for part in fragments):
            raise UnsupportedRule(f'Unsupported/missing rulebook convention in {self.source}')

    def implicit_year(self):
        self.require('Tháng M, quý Q không ghi năm', 'nam nay neu khong sau hom nay')
        value = folded(self.rows[folded('Tháng M, quý Q không ghi năm')])
        if not re.search(r'(sau hom nay thi cua|con lai) nam truoc', value):
            raise UnsupportedRule('Unsupported implicit-year fallback')

    def rounding_places(self, kind: str) -> int:
        text = folded(self.text)
        if kind == 'money' and re.search(r'\btien(?: ra so le)? lam tron ve dong', text):
            return 0
        if kind == 'percent':
            values = re.findall(r'phan tram(?: va so trung binh khac)? lam tron (\d+) chu so', text)
            if values and set(values) == {'2'}:
                return 2
        raise UnsupportedRule(f'Unsupported {kind} rounding convention')

    def shift_minutes(self, shift: str) -> tuple[int, int]:
        if shift not in ('sang', 'chieu'):
            raise ValueError('shift must be sang or chieu')
        value = folded(self.require('Ca sáng, ca chiều', 'theo gio tao don'))
        match = re.search(rf'ca {shift}\s+(\d{{2}}):(\d{{2}})\s*[–—-]\s*(\d{{2}}):(\d{{2}})', value)
        if not match:
            raise UnsupportedRule('Unsupported shift boundaries')
        h0, m0, h1, m1 = map(int, match.groups())
        start, end = h0 * 60 + m0, h1 * 60 + m1 + 1
        if not (0 <= h0 <= 23 and 0 <= h1 <= 23 and 0 <= m0 <= 59 and 0 <= m1 <= 59 and start < end):
            raise UnsupportedRule('Invalid shift boundaries')
        return start, end
