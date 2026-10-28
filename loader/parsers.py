"""Parse giá trị từng ô: số, tiền, số lượng, ngày, trạng thái đơn, khách lẻ, số điện thoại.

Mọi hàm đều tổng quát (không phụ thuộc tiệm), nhận một ô bất kỳ (None/str/int/float/datetime)
và trả None khi không parse được — không bao giờ đoán.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime, timedelta
from functools import lru_cache

# Ô lỗi của Excel coi như rỗng
EXCEL_ERRORS = {"#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NAME?", "#NUM!", "#NULL!", "#GETTING_DATA"}

EXCEL_EPOCH = datetime(1899, 12, 30)
SERIAL_MIN, SERIAL_MAX = 20000, 80000  # serial Excel hợp lý: 1954..2119


# ---------------------------------------------------------------------------
# Chuỗi
# ---------------------------------------------------------------------------

def is_null(v) -> bool:
    """Ô rỗng thật: None, NaN, pd.NA, NaT (không coi chuỗi 'nan'/'<NA>' là rỗng ở đây)."""
    if v is None or type(v).__name__ in ("NAType", "NaTType"):
        return True
    return isinstance(v, float) and math.isnan(v)


def clean_str(v) -> str | None:
    """NFC + strip + gộp khoảng trắng; ô rỗng / ô lỗi Excel -> None."""
    if is_null(v):
        return None
    s = unicodedata.normalize("NFC", str(v)).replace(" ", " ").strip()
    s = re.sub(r"\s+", " ", s)
    if not s or s.upper() in EXCEL_ERRORS or s.lower() in ("nan", "none", "null"):
        return None
    return s


@lru_cache(maxsize=200_000)
def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=200_000)
def name_key(s: str) -> str:
    """Khoá so khớp tên: bỏ dấu, chữ thường, chỉ giữ chữ-số cách nhau 1 khoảng trắng."""
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(s)).strip()


def nk(v) -> str | None:
    """name_key an toàn với ô rỗng / NaN."""
    s = clean_str(v)
    return name_key(s) if s else None


@lru_cache(maxsize=200_000)
def col_key(s: str) -> str:
    """Khoá tên cột: bỏ dấu, chữ thường, bỏ mọi ký tự không phải chữ-số.
    'MaHoaDon' và 'Mã hóa đơn' cùng ra 'mahoadon'; bỏ hậu tố đơn vị tiền '(đ)'."""
    s = re.sub(r"\((đ|d|vnd|vnđ)\)\s*$", "", str(s).strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]", "", strip_accents(s))


# ---------------------------------------------------------------------------
# Số / tiền / số lượng
# ---------------------------------------------------------------------------

def _to_num(x: float):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    if abs(x - round(x)) < 1e-6:
        return int(round(x))
    return x


@lru_cache(maxsize=500_000)
def _parse_number_str(s: str):
    s = s.replace(" ", " ").strip()
    if not s or s.upper() in EXCEL_ERRORS:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1].strip()
    if s[:1] in "+-":
        neg, s = (s[0] == "-"), s[1:].strip()
    # khoảng trắng làm phân cách nghìn: "129 000", "1 250 000"
    if re.fullmatch(r"\d{1,3}( \d{3})+", s):
        s = s.replace(" ", "")
    if re.fullmatch(r"\d+", s):
        val = float(s)
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):          # 45,000.0000 / 560,000
        val = float(s.replace(",", ""))
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):          # 1.250.000 / 45.000 (kiểu VN)
        if re.fullmatch(r"0\.\d{3}", s):                         # 0.125 là thập phân
            val = float(s)
        else:
            val = float(s.replace(".", "").replace(",", "."))
    elif re.fullmatch(r"\d+\.\d+", s):                          # 18.6
        val = float(s)
    elif re.fullmatch(r"\d+,\d+", s):                           # 16,56 (thập phân kiểu VN)
        val = float(s.replace(",", "."))
    else:
        return None
    return _to_num(-val if neg else val)


def parse_number(v):
    """Số thuần (không đơn vị). Trả int nếu là số nguyên, float nếu có phần lẻ, None nếu không phải số."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return _to_num(float(v))
    if isinstance(v, (datetime, date)):
        return None
    return _parse_number_str(str(v))


_CURRENCY_RE = re.compile(r"(đồng|dong|vnđ|vnd|đ|₫)$")


@lru_cache(maxsize=500_000)
def _parse_money_str(s: str):
    n = _parse_number_str(s)
    if n is not None:
        return n
    t = s.lower().replace(" ", "").replace(" ", "")
    neg = t.startswith("-")
    t = t.lstrip("+-")
    t = _CURRENCY_RE.sub("", t)
    if not t:
        return None
    m = re.fullmatch(r"(\d+)tr(\d{1,3})", t)                      # 1tr440 = 1.440.000
    if m:
        val = int(m[1]) * 1_000_000 + int(m[2].ljust(3, "0")) * 1_000
        return -val if neg else val
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(tr|triệu|trieu)", t)    # 16,56tr / 1.5tr
    if m:
        val = float(m[1].replace(",", ".")) * 1_000_000
        return _to_num(-val if neg else val)
    m = re.fullmatch(r"([\d.,]+)(k|nghìn|ngàn|nghin|ngan)", t)    # 38k / 25000k
    if m:
        base = _parse_number_str(m[1])
        if base is None:
            return None
        return _to_num(-(base * 1000) if neg else base * 1000)
    n = _parse_number_str(t)
    if n is None:
        return None
    return -n if neg else n


def parse_money(v):
    """Tiền: số thuần hoặc kèm đơn vị: 38.000đ, 38k, 1tr440, 16,56tr, 25000k, -53.500đ, 0đ."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return _to_num(float(v))
    if isinstance(v, (datetime, date)):
        return None
    return _parse_money_str(str(v))


@lru_cache(maxsize=200_000)
def _parse_quantity_str(s: str):
    n = _parse_number_str(s)
    if n is not None:
        return n, None
    m = re.fullmatch(r"\s*(-?\d+(?:[.,]\d+)?)\s*([^\d\s].*?)\s*", s)
    if not m:
        return None, None
    return _to_num(float(m[1].replace(",", "."))), m[2]


def parse_quantity(v):
    """Số lượng, có thể kèm chữ đơn vị: '3 chai' -> (3, 'chai'); 5 -> (5, None)."""
    if v is None or isinstance(v, bool):
        return None, None
    if isinstance(v, (int, float)):
        return _to_num(float(v)), None
    if isinstance(v, (datetime, date)):
        return None, None
    return _parse_quantity_str(str(v).strip())


# ---------------------------------------------------------------------------
# Ngày
# ---------------------------------------------------------------------------

_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?")
_DMY = re.compile(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})(?:,?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?")
_THG = re.compile(r"(?:ngày\s*)?(\d{1,2})\s*(?:thg|tháng)\s*(\d{1,2}),?\s*(?:năm\s*)?(\d{4})", re.I)
_NOYEAR = re.compile(r"(\d{1,2})[/\-](\d{1,2})")


def _mk(y, m, d, hh=None, mm=None, ss=None):
    try:
        return datetime(int(y), int(m), int(d), int(hh or 0), int(mm or 0), int(ss or 0))
    except ValueError:
        return None


def excel_serial_to_datetime(x: float) -> datetime | None:
    if not (SERIAL_MIN <= x <= SERIAL_MAX):
        return None
    return EXCEL_EPOCH + timedelta(days=float(x))


@lru_cache(maxsize=300_000)
def _parse_date_str(s: str, year_hint: int | None, allow_serial: bool):
    s = s.strip()
    if not s:
        return None
    m = _ISO.fullmatch(s)
    if m:
        return _mk(*m.groups())
    m = _DMY.fullmatch(s)
    if m:  # luôn dayfirst
        d, mo, y, hh, mi, ss = m.groups()
        y = int(y) + 2000 if len(y) == 2 else int(y)
        return _mk(y, mo, d, hh, mi, ss)
    m = _THG.fullmatch(s)
    if m:
        return _mk(m[3], m[2], m[1])
    m = _NOYEAR.fullmatch(s)
    if m and year_hint:
        return _mk(year_hint, m[2], m[1])
    if allow_serial and re.fullmatch(r"\d{5}(\.\d+)?", s):
        return excel_serial_to_datetime(float(s))
    return None


def parse_date(v, year_hint: int | None = None, allow_serial: bool = True) -> datetime | None:
    """Ngày (giữ giờ nếu có): datetime, serial Excel, '1 thg 7 2025', dd/mm/yyyy (LUÔN dayfirst), ISO,
    'd/m' không năm -> năm theo year_hint (năm của sheet)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=None)
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if hasattr(v, "to_pydatetime"):  # pandas Timestamp
        return v.to_pydatetime().replace(tzinfo=None)
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return None
        return excel_serial_to_datetime(float(v)) if allow_serial else None
    return _parse_date_str(unicodedata.normalize("NFC", str(v)), year_hint, allow_serial)


def is_strong_date(v) -> bool:
    """Ô chắc chắn là ngày (kiểu datetime hoặc chuỗi đúng mẫu ngày), không tính số serial."""
    if isinstance(v, (datetime, date)):
        return True
    if isinstance(v, str):
        s = v.strip()
        return bool(_ISO.fullmatch(s) or _DMY.fullmatch(s) or _THG.fullmatch(s))
    return False


def year_from_name(name: str | None) -> int | None:
    """Năm trong tên sheet / file: 'T01_2025', 'Thang 02 2025', 'BanHang_2026' -> 2025/2026."""
    if not name:
        return None
    m = re.search(r"(?<!\d)(20\d{2})(?!\d)", str(name))
    return int(m[1]) if m else None


# ---------------------------------------------------------------------------
# Trạng thái đơn (DESIGN.md c.2) — 4 giá trị chuẩn
# ---------------------------------------------------------------------------

HOAN_THANH, HUY, TRA_HANG, DANG_GIAO = "hoan_thanh", "huy", "tra_hang", "dang_giao"

STATUS_EXACT = {
    # hoàn thành
    "xong": HOAN_THANH, "ok": HOAN_THANH, "da lay": HOAN_THANH, "da xong": HOAN_THANH,
    "da hoan thanh": HOAN_THANH, "hoan thanh": HOAN_THANH, "thanh cong": HOAN_THANH,
    "da giao": HOAN_THANH, "completed": HOAN_THANH,
    # huỷ
    "da huy": HUY, "huy": HUY, "huy don": HUY, "da huy don": HUY, "khach huy": HUY,
    "cancel": HUY, "cancelled": HUY, "canceled": HUY, "khong giao duoc": HUY,
    # trả hàng
    "doi tra": TRA_HANG, "tra hang": TRA_HANG, "hang tra ve": TRA_HANG, "hoan tra": TRA_HANG,
    "tra lai": TRA_HANG, "da hoan hang": TRA_HANG, "da tra hang": TRA_HANG, "khach tra": TRA_HANG,
    "returned": TRA_HANG,
    # đang giao
    "dang giao": DANG_GIAO, "dang giao hang": DANG_GIAO, "dang van chuyen": DANG_GIAO,
    "dang gui": DANG_GIAO, "cho giao": DANG_GIAO, "shipping": DANG_GIAO,
    "dang giao dich": DANG_GIAO, "dang xu ly": DANG_GIAO,  # CHƯA CHẮC (DESIGN c.2)
}


@lru_cache(maxsize=10_000)
def normalize_status(v) -> str | None:
    """Chuẩn hoá trạng thái đơn; không nhận ra -> None."""
    s = clean_str(v)
    if s is None:
        return None
    k = name_key(s)
    if k in STATUS_EXACT:
        return STATUS_EXACT[k]
    return status_from_text(s)


def status_from_text(s: str | None) -> str | None:
    """Tìm trạng thái theo từ khoá trong một câu (ô ghi chú, trạng thái viết lạ)."""
    s = clean_str(s)
    if not s:
        return None
    k = " " + name_key(s) + " "
    if re.search(r" (huy|cancel(led)?|khong giao duoc) ", k):
        return HUY
    if re.search(r" (tra hang|tra lai|doi tra|hoan tra|hoan hang|tra ve|mang tra|return(ed)?) ", k):
        return TRA_HANG
    if re.search(r" (dang giao|dang van chuyen|dang gui|cho giao|shipping) ", k):
        return DANG_GIAO
    if re.search(r" (xong|hoan thanh|thanh cong|da giao|completed|ok) ", k):
        return HOAN_THANH
    if k.startswith(" dang "):  # đang giao / đang gửi / đang vận chuyển / đang xử lý... (từ vựng train)
        return DANG_GIAO
    return None


STATUS_PRIORITY = {TRA_HANG: 3, HUY: 2, DANG_GIAO: 1, HOAN_THANH: 0}


def combine_status(values) -> str | None:
    """Trạng thái của đơn từ trạng thái các dòng: tra_hang > huy > dang_giao > hoan_thanh.
    CHƯA CHẮC khi các dòng mâu thuẫn (không thấy trong dữ liệu train)."""
    best = None
    for v in values:
        if isinstance(v, str) and v in STATUS_PRIORITY and (best is None or STATUS_PRIORITY[v] > STATUS_PRIORITY[best]):
            best = v
    return best


# ---------------------------------------------------------------------------
# Hình thức thanh toán
# ---------------------------------------------------------------------------

def normalize_payment(v) -> str | None:
    s = clean_str(v)
    if s is None:
        return None
    k = name_key(s)
    if re.search(r"\b(cod|thu ho)\b", k):
        return "cod"
    if re.search(r"\b(ghi no|debt|no)\b", k):
        return "ghi_no"
    if re.search(r"\b(vi|ewallet|e wallet|momo|zalopay)\b", k):
        return "vi_dien_tu"
    if re.search(r"\b(chuyen khoan|transfer|ck|bank)\b", k):
        return "chuyen_khoan"
    if re.search(r"\b(tien mat|cash|tm)\b", k):
        return "tien_mat"
    return None


# ---------------------------------------------------------------------------
# Khách hàng
# ---------------------------------------------------------------------------

_PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?!\d)")
WALKIN_KEYS = {"khach le", "le", "kl", "khach vang lai", "vang lai", "khach le khong luu", "k l"}


def split_phone(v) -> tuple[str | None, str | None]:
    """'Nguyễn Văn A (0900000001)' -> ('Nguyễn Văn A', '0900000001'). Giữ nguyên nếu không có SĐT."""
    s = clean_str(v)
    if s is None:
        return None, None
    m = _PHONE_RE.search(s)
    if not m:
        return s, None
    phone = re.sub(r"\D", "", m[0])
    name = (s[: m.start()] + " " + s[m.end():])
    name = re.sub(r"\(\s*\)", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" -–—,;:()")
    return (name or None), phone


def is_walkin(name) -> bool:
    """Khách lẻ: 'Khách lẻ', 'khách lẻ', 'lẻ', 'kl'..."""
    s = clean_str(name)
    return s is None or name_key(s) in WALKIN_KEYS


# ---------------------------------------------------------------------------
# Loại dòng hàng
# ---------------------------------------------------------------------------

def line_kind(ten_hang) -> str:
    """hang / phi_phuc_vu / voucher / dung_diem / phi_ship. ('topping' chỉ khi tách topping ghép ô — chưa làm ở v0.)"""
    s = clean_str(ten_hang)
    if s is None:
        return "hang"
    k = name_key(s)
    if k.startswith("phi phuc vu"):
        return "phi_phuc_vu"
    if k.startswith("voucher"):
        return "voucher"
    if re.fullmatch(r"dung \d+ diem.*", k):
        return "dung_diem"
    if re.fullmatch(r"phi (ship|giao hang|giao|van chuyen)", k):
        return "phi_ship"
    return "hang"


# ---------------------------------------------------------------------------
# Kênh bán
# ---------------------------------------------------------------------------

def normalize_channel(v) -> str | None:
    """Kênh bán -> tai_quay / zalo / dien_thoai / san_tmdt / facebook / online / app_giao_do_an;
    không nhận ra -> khoá chữ thường của giá trị gốc (không đoán)."""
    s = clean_str(v)
    if s is None:
        return None
    k = name_key(s)
    if re.search(r"\b(store|tai quay|tai tiem|tai cua hang|offline|quay)\b", k):
        return "tai_quay"
    if "zalo" in k:
        return "zalo"
    if re.search(r"\b(phone|dien thoai|goi dien|hotline)\b", k):
        return "dien_thoai"
    if re.search(r"\b(san|tmdt|shopee|lazada|tiki|tiktok|sendo)\b", k):
        return "san_tmdt"
    if re.search(r"\b(facebook|fb|messenger)\b", k):
        return "facebook"
    if re.search(r"\b(grab|shopeefood|baemin|gojek|be)\b", k):
        return "app_giao_do_an"
    if re.search(r"\b(web|website|online)\b", k):
        return "online"
    return k.replace(" ", "_")


# ---------------------------------------------------------------------------
# Topping ghi chung ô với món: "Trà sữa (M) + 2 Trân châu (10.000)"
# ---------------------------------------------------------------------------

_TOPPING_SEG = re.compile(r"(?:(\d+)\s*(?:x\s*)?)?(.+?)\s*\(\s*([\d.,]+\s*(?:đ|₫|k|vnđ|vnd)?)\s*\)", re.I)


def split_topping(name) -> tuple[str, list[tuple[str, int, float]]] | None:
    """Tách ô 'Món + [n] Topping (tiền) + ...' -> (tên món, [(tên topping, số phần, tiền)]).
    Chỉ tách khi MỌI phần sau dấu ' + ' đều đúng mẫu '[số] tên (tiền)'; không thì trả None (không đoán)."""
    s = clean_str(name)
    if s is None or " + " not in s:
        return None
    parts = [p.strip() for p in s.split(" + ")]
    main, rest = parts[0], parts[1:]
    if not main or not rest:
        return None
    tops = []
    for p in rest:
        m = _TOPPING_SEG.fullmatch(p)
        if not m:
            return None
        money = parse_money(m[3])
        if money is None:
            return None
        tops.append((m[2].strip(), int(m[1]) if m[1] else 1, float(money)))
    return main, tops
