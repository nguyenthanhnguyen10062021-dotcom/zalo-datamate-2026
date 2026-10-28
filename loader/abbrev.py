"""Tách token tên cột và bung viết tắt thông dụng trong sổ sách bán hàng Việt Nam.

Bảng viết tắt là kiến thức CHUNG về cách ghi sổ (tiếng Việt có/không dấu, tiếng Anh), không phải theo tiệm.
Viết tắt mơ hồ (vd 'tt' = thành tiền / thanh toán / trạng thái) giữ mọi cách bung; lớp suy từ giá trị
(infer.py) và kiểm tra kiểu dữ liệu sẽ quyết định.
"""

from __future__ import annotations

import itertools
import re
import unicodedata
from functools import lru_cache

from .parsers import strip_accents

# token (đã bỏ dấu, chữ thường) -> các cách bung (cụm không dấu)
ABBREV: dict[str, list[str]] = {
    # số lượng, đơn vị
    "sl": ["so luong"], "slg": ["so luong"], "sluong": ["so luong"], "soluong": ["so luong"],
    "qty": ["so luong"], "quantity": ["so luong"], "qtty": ["so luong"],
    "dvt": ["don vi tinh"], "dv": ["don vi"], "dvi": ["don vi"], "donvi": ["don vi"], "dvtinh": ["don vi tinh"],
    "unit": ["don vi tinh"], "uom": ["don vi tinh"],
    "qd": ["quy doi"], "qdoi": ["quy doi"],
    # tiền, giá
    "tt": ["thanh tien", "thanh toan", "trang thai"],
    "ttien": ["thanh tien"], "thtien": ["thanh tien"],
    "amt": ["thanh tien"], "amount": ["thanh tien"], "total": ["tong tien"], "subtotal": ["tong tien hang"],
    "dg": ["don gia"], "dgia": ["don gia"], "price": ["don gia"], "unitprice": ["don gia"],
    "gv": ["gia von"], "cogs": ["gia von"], "cost": ["gia von"],
    "ck": ["chiet khau", "chuyen khoan"], "discount": ["giam gia"], "disc": ["giam gia"],
    "km": ["khuyen mai"], "vat": ["thue"], "tax": ["thue"],
    "pttt": ["phuong thuc thanh toan"], "httt": ["hinh thuc thanh toan"], "pt": ["phuong thuc"],
    "ht": ["hinh thuc"], "payment": ["hinh thuc thanh toan"], "paymethod": ["hinh thuc thanh toan"],
    "tm": ["tien mat"], "cash": ["tien mat"],
    # đơn, chứng từ
    "hd": ["hoa don"], "hdon": ["hoa don"], "bill": ["hoa don"], "invoice": ["hoa don"], "inv": ["hoa don"],
    "order": ["don hang"], "ord": ["don hang"], "dh": ["don hang"],
    "ct": ["chung tu"], "pn": ["phieu nhap"], "px": ["phieu xuat"],
    "stt": ["so thu tu"],
    # hàng hoá
    "sp": ["san pham"], "mh": ["mat hang"], "hh": ["hang hoa"], "hhoa": ["hang hoa"],
    "product": ["san pham"], "item": ["mat hang"], "sku": ["ma hang"], "goods": ["hang hoa"],
    "category": ["nhom hang"], "cat": ["nhom hang"], "nhomhang": ["nhom hang"],
    # người
    "kh": ["khach hang"], "khang": ["khach hang"], "cust": ["khach hang"], "customer": ["khach hang"],
    "client": ["khach hang"],
    "nv": ["nhan vien"], "nvien": ["nhan vien"], "emp": ["nhan vien"], "employee": ["nhan vien"],
    "staff": ["nhan vien"], "seller": ["nhan vien ban"], "cashier": ["thu ngan"],
    "ncc": ["nha cung cap"], "supplier": ["nha cung cap"], "vendor": ["nha cung cap"],
    "sdt": ["so dien thoai"], "dthoai": ["dien thoai"], "phone": ["so dien thoai"], "tel": ["so dien thoai"],
    "mobile": ["so dien thoai"],
    "dc": ["dia chi"], "dchi": ["dia chi"], "addr": ["dia chi"], "address": ["dia chi"],
    # thời gian
    "date": ["ngay"], "day": ["ngay"], "time": ["thoi gian"], "datetime": ["thoi gian"], "tg": ["thoi gian"],
    "created": ["thoi gian tao"], "hsd": ["han su dung"], "exp": ["han su dung"], "expiry": ["han su dung"],
    "nsx": ["ngay san xuat"],
    # khác
    "status": ["trang thai"], "state": ["trang thai"], "ttrang": ["trang thai"],
    "channel": ["kenh ban"], "source": ["nguon"],
    "note": ["ghi chu"], "notes": ["ghi chu"], "memo": ["ghi chu"], "remark": ["ghi chu"], "gchu": ["ghi chu"],
    "name": ["ten"], "group": ["nhom"], "id": ["ma"], "code": ["ma"], "no": ["so"],
    "ship": ["giao hang"], "shipping": ["giao hang"], "delivery": ["giao hang"],
    "tl": ["ti le"], "lo": ["lo"],
}

MAX_VARIANTS = 6


def _split_camel(s: str) -> str:
    """'ThoiGianLap' -> 'Thoi Gian Lap'; 'MaHH2' -> 'Ma HH 2'. Hoạt động cả với chữ có dấu."""
    out = []
    for i, ch in enumerate(s):
        if i and ch.isalpha() and ch.isupper() and (s[i - 1].isalpha() and s[i - 1].islower()):
            out.append(" ")
        elif i and ((ch.isdigit() and s[i - 1].isalpha()) or (ch.isalpha() and s[i - 1].isdigit())):
            out.append(" ")
        out.append(ch)
    return "".join(out)


@lru_cache(maxsize=50_000)
def tokenize(name: str) -> tuple[str, ...]:
    """Tên cột -> token: NFC, tách camelCase/PascalCase, bỏ dấu, chữ thường, bỏ dấu câu (. / _ - ( ) ...).
    Chữ cái đơn đứng trước token khác được thử ghép (vd 'Đ.vị' -> 'd' 'vi' -> 'dvi') nếu ghép ra viết tắt."""
    s = unicodedata.normalize("NFC", str(name))
    s = _split_camel(s)
    s = strip_accents(s)
    toks = [t for t in re.split(r"[^a-z0-9]+", s) if t]
    merged, i = [], 0
    while i < len(toks):
        if len(toks[i]) == 1 and i + 1 < len(toks) and (toks[i] + toks[i + 1]) in ABBREV:
            merged.append(toks[i] + toks[i + 1])
            i += 2
        else:
            merged.append(toks[i])
            i += 1
    return tuple(merged)


@lru_cache(maxsize=50_000)
def expand(name: str) -> tuple[tuple[str, ...], ...]:
    """Mọi cách bung tên cột thành dãy token đầy đủ (tối đa MAX_VARIANTS cách).
    Token không phải viết tắt giữ nguyên. Cả tên viết liền ('slg', 'pttt') lẫn từng token đều được thử."""
    toks = tokenize(name)
    if not toks:
        return ()
    whole = "".join(toks)
    if len(toks) > 1 and whole in ABBREV:   # vd 'S.L' -> 's','l' -> 'sl'
        return tuple(tuple(v.split()) for v in ABBREV[whole])[:MAX_VARIANTS]
    options = [[tuple(v.split()) for v in ABBREV[t]] if t in ABBREV else [(t,)] for t in toks]
    out = []
    for combo in itertools.product(*options):
        out.append(tuple(w for part in combo for w in part))
        if len(out) >= MAX_VARIANTS:
            break
    return tuple(out)


def is_abbreviated(name: str) -> bool:
    """Tên cột có chứa ít nhất một token viết tắt (để ghi nguồn 'abbrev')."""
    toks = tokenize(name)
    return any(t in ABBREV for t in toks) or ("".join(toks) in ABBREV and len(toks) > 1)


# ---------------------------------------------------------------------------
# Chuẩn hoá vị trí dấu thanh ('hóa' ~ 'hoá', 'thủy' ~ 'thuỷ') để so khớp có dấu
# ---------------------------------------------------------------------------

_TONES = "̣̀́̃̉"  # huyền, sắc, ngã, hỏi, nặng


@lru_cache(maxsize=50_000)
def accent_form(s: str) -> str:
    """Dạng so khớp CÓ dấu: chữ thường, chỉ chữ-số, vị trí dấu thanh chuẩn hoá (oa, oe, uy đặt dấu ở nguyên âm sau)."""
    d = unicodedata.normalize("NFD", str(s).lower())
    d = re.sub(r"[^\w\u0300-\u036f]", "", d)   # giữ dấu kết hợp (combining marks)
    # đưa dấu thanh ở o/u (trong oa, oe, uy) sang nguyên âm sau: 'o' + tone + 'a' -> 'o' + 'a' + tone
    d = re.sub(rf"([ou])([{_TONES}])([aey])", r"\1\3\2", d)
    return unicodedata.normalize("NFC", d)


def has_accents(s: str) -> bool:
    return accent_form(s) != re.sub(r"[^\w]", "", strip_accents(str(s)).lower())
