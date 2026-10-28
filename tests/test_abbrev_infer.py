"""Unit test lớp bung viết tắt (abbrev.py) và lớp suy vai trò cột từ giá trị (infer.py).
Toàn bộ dữ liệu là DataFrame giả lập — không dùng dữ liệu public test làm test case."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from loader.abbrev import accent_form, expand, has_accents, is_abbreviated, tokenize  # noqa: E402
from loader.infer import (base_quantity, datetime_roles, key_overlap, ledger_columns, order_id,  # noqa: E402
                          qty_price_amount)
from loader.mapping import Dictionaries, build_dictionaries  # noqa: E402
from loader.parsers import normalize_channel, split_topping  # noqa: E402
from loader.readme import ReadmeInfo, Section  # noqa: E402


# ---------------------------------------------------------------------------
# abbrev
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, toks", [
    ("ThoiGianLap", ("thoi", "gian", "lap")),
    ("KenhBanHang", ("kenh", "ban", "hang")),
    ("MaNhanVien", ("ma", "nhan", "vien")),
    ("Đ.vị", ("dvi",)),
    ("S.L", ("sl",)),                 # chữ đơn ghép lại khi thành viết tắt đã biết
    ("Mã_KH-mua", ("ma", "kh", "mua")),
    ("Thành tiền (đ)", ("thanh", "tien", "d")),
    ("SL cơ bản", ("sl", "co", "ban")),
])
def test_tokenize(name, toks):
    assert tokenize(name) == toks


@pytest.mark.parametrize("name, expected", [
    ("SL", ("so", "luong")), ("Slg", ("so", "luong")), ("qty", ("so", "luong")), ("S.L", ("so", "luong")),
    ("ĐVT", ("don", "vi", "tinh")), ("Đ.vị", ("don", "vi")),
    ("Mã KH", ("ma", "khach", "hang")), ("Mã NV bán", ("ma", "nhan", "vien", "ban")),
    ("NCC", ("nha", "cung", "cap")), ("PTTT", ("phuong", "thuc", "thanh", "toan")),
    ("ĐG", ("don", "gia")), ("HĐ", ("hoa", "don")), ("GV", ("gia", "von")), ("ma_sp", ("ma", "san", "pham")),
    ("Cust ID", ("khach", "hang", "ma")), ("amt", ("thanh", "tien")),
])
def test_expand_first_variant(name, expected):
    assert expand(name)[0] == expected


def test_expand_ambiguous_keeps_all():
    v = expand("TT")
    assert ("thanh", "tien") in v and ("thanh", "toan") in v and ("trang", "thai") in v
    assert is_abbreviated("TT") and not is_abbreviated("Ngày bán")


def test_accent_forms():
    assert accent_form("Mã hóa đơn") == accent_form("Mã hoá đơn")      # vị trí dấu thanh khác kiểu
    assert accent_form("Hạng") != accent_form("Hàng")
    assert has_accents("Hạng") and not has_accents("Thanh tien")


def _dicts_from_pairs(pairs):
    info = ReadmeInfo(path=None, sections=[Section("x.csv", None, dict(pairs))])
    return build_dictionaries([info], use_rules=True)


def test_name_candidates_abbrev_and_accent_guard():
    d = _dicts_from_pairs([("Số lượng", "số lượng"), ("Hàng", "tên hàng"), ("Mã khách hàng", "mã khách"),
                           ("Thành tiền", "thành tiền sau giảm"), ("Kênh bán", "kênh bán")])
    best = lambda n: (d.name_candidates(n) or [(None, 0, "")])[0]  # noqa: E731
    assert best("Slg")[:1] == ("so_luong",) and best("Slg")[2] == "abbrev"
    assert best("Mã KH mua")[0] == "ma_khach"
    assert best("KenhBanHang")[0] == "kenh_ban"
    assert best("Thanh tien")[0] == "thanh_tien"          # không dấu: khớp
    assert best("Hạng")[0] is None                         # dấu khác 'Hàng': không khớp
    tt = {c for c, _w, _h in d.name_candidates("TT")}
    assert "thanh_tien" in tt                              # mơ hồ: là một ứng viên, trọng số chia nhỏ
    assert all(w < 1.0 for _c, w, _h in d.name_candidates("TT"))


# ---------------------------------------------------------------------------
# infer: bộ ba SL × đơn giá ≈ thành tiền
# ---------------------------------------------------------------------------

def _sales_frame(n=400, seed=0, discount=True):
    rng = np.random.default_rng(seed)
    q = rng.integers(1, 6, n)
    p = rng.choice([15000, 22000, 35000, 120000], n)
    a = q * p
    if discount:
        d = rng.random(n) < 0.1
        a = np.where(d, a - 1000 * q, a)
    noise = rng.integers(100000, 900000, n)        # cột tiền khác không liên quan
    return pd.DataFrame({"A": q, "B": p, "C": a, "D": noise, "E": rng.integers(1, 30, n)})


def test_triple_found_with_evidence():
    df = _sales_frame()
    res = {i.col: i.concept for i in qty_price_amount(df, list(df.columns))}
    assert res == {"A": "so_luong", "B": "don_gia", "C": "thanh_tien"}
    ev = qty_price_amount(df, list(df.columns))[0].evidence
    assert "SL×đơn giá≈thành tiền" in ev and "%" in ev


def test_triple_respects_fixed_and_rejects_noise():
    df = _sales_frame()
    res = qty_price_amount(df, ["B", "C", "D"], fixed={"so_luong": "A"})
    assert {i.col: i.concept for i in res} == {"B": "don_gia", "C": "thanh_tien"}
    rnd = pd.DataFrame(np.random.default_rng(1).integers(1, 10**6, (300, 4)), columns=list("WXYZ"))
    assert qty_price_amount(rnd, list(rnd.columns)) == []          # không có quan hệ -> không đoán


def test_triple_needs_qty_above_one():
    df = pd.DataFrame({"q": [1] * 100, "p": [5000] * 100, "a": [5000] * 100})
    assert qty_price_amount(df, ["q", "p", "a"]) == []             # SL luôn 1: không phân biệt được giá/thành tiền


# ---------------------------------------------------------------------------
# infer: số lượng cơ bản
# ---------------------------------------------------------------------------

def test_base_quantity():
    rows = []
    for i in range(300):
        item, unit, f = [("Bia", "lon", 1), ("Bia", "thùng", 24), ("Nước", "chai", 1)][i % 3]
        q = i % 4 + 1
        rows.append({"item": item, "unit": unit, "q": q, "base": q * f, "x": (i * 7919) % 97 + 1})
    df = pd.DataFrame(rows)
    inf = base_quantity(df, "q", ["base", "x"], ["item", "unit"])
    assert inf is not None and inf.col == "base" and "hằng theo" in inf.evidence
    assert base_quantity(df, "q", ["x"], ["item", "unit"]) is None
    assert base_quantity(df, "q", ["base"], []) is None            # thiếu (hàng, đơn vị): không đủ bằng chứng


# ---------------------------------------------------------------------------
# infer: ngày / thời điểm
# ---------------------------------------------------------------------------

def test_datetime_roles():
    base = datetime(2025, 3, 1)
    df = pd.DataFrame({"d": [base + timedelta(days=i // 10) for i in range(100)],
                       "t": [base + timedelta(days=i // 10, hours=7, minutes=i) for i in range(100)]})
    got = {i.concept: i.col for i in datetime_roles(df, ["d", "t"], need_date=True, need_time=True)}
    assert got == {"ngay_dat": "d", "thoi_diem_dat": "t"}
    two_time = df.assign(t2=df["t"] + timedelta(hours=1))
    assert not [i for i in datetime_roles(two_time, ["t", "t2"], False, True)]   # 2 ứng viên -> không đoán


# ---------------------------------------------------------------------------
# infer: mã đơn
# ---------------------------------------------------------------------------

def _orders(n_orders=60, fill=True, code=True):
    rows = []
    for o in range(n_orders):
        day = datetime(2025, 1, 1) + timedelta(days=o // 6)
        for j in range(1 + o % 3):
            oid = (f"HD{o:05d}" if code else o + 1)
            rows.append({"id": oid if (fill or j == 0) else None, "day": day, "item": f"SP{j}",
                         "status": "xong", "cust": f"K{o % 7}"})
    return pd.DataFrame(rows)


def test_order_id_repeated_codes():
    df = _orders()
    inf = order_id(df, ["id", "item", "status", "cust"], pd.Series(["s"] * len(df)), "day")
    assert inf is not None and inf.col == "id" and inf.mode == "lap" and "ngày hằng" in inf.evidence


def test_order_id_fill_down_stt():
    df = _orders(fill=False, code=False)
    inf = order_id(df, ["id", "item", "status", "cust"], pd.Series(["s"] * len(df)), "day")
    assert inf is not None and inf.col == "id" and inf.mode.startswith("dien_xuong") and "theo_sheet" in inf.mode


def test_order_id_rejects_non_contiguous():
    df = _orders()
    df["id"] = df["id"].sample(frac=1, random_state=0).to_numpy()          # xáo trộn: không còn nhóm liền kề
    assert order_id(df, ["id"], pd.Series(["s"] * len(df)), "day") is None


# ---------------------------------------------------------------------------
# infer: trùng khoá danh sách, sổ phiếu
# ---------------------------------------------------------------------------

def test_key_overlap():
    df = pd.DataFrame({"a": ["KH01", "KH02", "KH03", None, "KH01", "KH05"], "b": ["x", "y", "z", "w", "v", "u"]})
    inf = key_overlap(df, ["a", "b"], {"KH01", "KH02", "KH03", "KH04", "KH05"}, "ma_khach", "danh sách khách")
    assert inf.col == "a" and "100.0%" in inf.evidence
    assert key_overlap(df, ["b"], {"KH01", "KH02", "KH03", "KH04", "KH05"}, "ma_khach", "x") is None


def test_ledger_columns():
    n = 50
    df = pd.DataFrame({"ngay": [datetime(2025, 7, 1) + timedelta(days=i % 20) for i in range(n)],
                       "tien": [150000 + 1000 * i for i in range(n)], "viec": ["thay nhớt"] * n})
    got = {i.concept: i.col for i in ledger_columns(df, {"ngay": "date", "tien": "number", "viec": "text"})}
    assert got == {"ngay_dat": "ngay", "thanh_tien": "tien"}
    df2 = df.assign(tien2=df["tien"] * 2)
    assert ledger_columns(df2, {"ngay": "date", "tien": "number", "tien2": "number"}) == []   # 2 cột tiền: không đoán


# ---------------------------------------------------------------------------
# topping, kênh bán
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Trà sữa (M) + 2 Trân châu (10.000)", ("Trà sữa (M)", [("Trân châu", 2, 10000.0)])),
    ("Cà phê (L) + Kem (8.000đ) + Thạch (5k)", ("Cà phê (L)", [("Kem", 1, 8000.0), ("Thạch", 1, 5000.0)])),
    ("Paracetamol + Cafein", None),          # không đúng mẫu topping -> không tách
    ("Trà sữa (M)", None),
])
def test_split_topping(raw, expected):
    assert split_topping(raw) == expected


@pytest.mark.parametrize("raw, expected", [("store", "tai_quay"), ("Tại quầy", "tai_quay"), ("zalo_oa", "zalo"),
                                           ("phone", "dien_thoai"), ("Shopee", "san_tmdt"), ("abc", "abc")])
def test_normalize_channel(raw, expected):
    assert normalize_channel(raw) == expected


# ---------------------------------------------------------------------------
# infer: giảm giá dòng, cân bằng cấp đơn
# ---------------------------------------------------------------------------

def test_line_discount():
    from loader.infer import line_discount
    rng = np.random.default_rng(3)
    q = rng.integers(1, 5, 200)
    p = rng.choice([20000, 45000], 200)
    d = np.where(rng.random(200) < 0.2, 2000, 0)
    df = pd.DataFrame({"q": q, "p": p, "a": q * p - d, "d": d, "z": rng.integers(0, 5000, 200)})
    inf = line_discount(df, "q", "p", "a", ["d", "z"])
    assert inf is not None and inf.col == "d" and inf.concept == "giam_gia_dong"
    df0 = df.assign(d=0, a=q * p)
    assert line_discount(df0, "q", "p", "a", ["d"]) is None        # luôn 0: không đủ bằng chứng


def test_order_balance():
    from loader.infer import order_balance
    rng = np.random.default_rng(4)
    t = rng.integers(50, 900, 200) * 1000
    g = np.where(rng.random(200) < 0.3, 10000, 0)
    ship = np.where(rng.random(200) < 0.2, 15000, 0)
    df = pd.DataFrame({"T": t, "G": g, "S": ship, "P": t - g + ship, "N": rng.integers(0, 9, 200)})
    got = order_balance(df, "T", "P", "G", ["S", "N"])
    assert [(i.col, i.concept) for i in got] == [("S", "phi_giao")]
    df2 = pd.DataFrame({"T": t, "X": g, "P": t - g})
    got2 = order_balance(df2, "T", "P", None, ["X"])
    assert [(i.col, i.concept) for i in got2] == [("X", "giam_gia_don")]
