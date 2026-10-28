"""Unit test các hàm parse với ví dụ thật trong DESIGN.md mục b. Chạy: pytest tests/"""

import re
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from loader.mapping import DESC_RULES, classify_desc, desc_key  # noqa: E402
from loader.parsers import (DANG_GIAO, HOAN_THANH, HUY, TRA_HANG, clean_str, col_key, combine_status,  # noqa: E402
                            is_walkin, line_kind, name_key, normalize_payment, normalize_status, parse_date,
                            parse_money, parse_number, parse_quantity, split_phone, year_from_name)
from loader.readme import parse_readme  # noqa: E402


# --- số / tiền (DESIGN b.9, b.10, b.11) --------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("560,000", 560000),            # phẩy nghìn (biz_101)
    ("45,000.0000", 45000),         # kiểu MISA (nhóm C)
    ("129 000", 129000),            # khoảng trắng nghìn (dev_007)
    ("1.250.000", 1250000),         # chấm nghìn kiểu VN
    ("16,56", 16.56),               # phẩy thập phân
    ("18.6", 18.6),
    (4820000, 4820000),
    (25000.0, 25000),
    ("0", 0),
    ("#N/A", None), ("#VALUE!", None), ("", None), (None, None), ("abc", None),
])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("38.000đ", 38000),             # biz_105
    ("38k", 38000),                 # biz_105
    ("1tr440", 1440000),            # biz_117
    ("26tr220", 26220000),          # biz_117
    ("16,56tr", 16560000),          # biz_117
    ("1,84tr", 1840000),            # biz_117
    ("25000k", 25000000),           # biz_124 SoTay
    ("11,067tr", 11067000),         # dev_003
    ("19tr990", 19990000),          # dev_014
    ("20,1tr", 20100000),           # dev_014
    ("-53.500đ", -53500),           # dòng trả hàng biz_105
    ("0đ", 0),
    ("655 000", 655000),
    ("45,000.0000", 45000),
    ("#VALUE!", None),
    ("nợ 79k", None),               # câu chữ: không đoán
])
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("3 chai", (3, "chai")), ("1 hộp", (1, "hộp")), ("2 vỉ", (2, "vỉ")), (5, (5, None)), ("-1", (-1, None)),
    ("abc", (None, None)),
])
def test_parse_quantity(raw, expected):
    assert parse_quantity(raw) == expected


# --- ngày (DESIGN b.12, b.13) -----------------------------------------------------------------------

@pytest.mark.parametrize("raw, hint, expected", [
    ("01/02/2025", None, datetime(2025, 2, 1)),               # dayfirst
    ("13/07/2026", None, datetime(2026, 7, 13)),
    ("1 thg 6 2025", None, datetime(2025, 6, 1)),             # biz_101
    ("15 thg 12 2025", None, datetime(2025, 12, 15)),
    (45689, None, datetime(2025, 2, 1)),                      # serial Excel (biz_105)
    ("45689", None, datetime(2025, 2, 1)),                    # serial trong CSV (biz_111)
    ("2025-01-01 06:03:04", None, datetime(2025, 1, 1, 6, 3, 4)),
    ("2025-03-01", None, datetime(2025, 3, 1)),
    ("4/1", 2025, datetime(2025, 1, 4)),                      # không năm -> năm của sheet (biz_117)
    ("4/1", None, None),
    (datetime(2025, 2, 1, 8, 9), None, datetime(2025, 2, 1, 8, 9)),
    ("31/02/2025", None, None),
    ("abc", None, None),
])
def test_parse_date(raw, hint, expected):
    assert parse_date(raw, hint) == expected


@pytest.mark.parametrize("name, year", [("T01_2025", 2025), ("Thang 02 2025", 2025), ("Tháng 01-2026", 2026),
                                        ("04.2025", 2025), ("BanHang_2026.xlsx", 2026), ("Sheet1", None)])
def test_year_from_name(name, year):
    assert year_from_name(name) == year


# --- trạng thái (DESIGN c.2), thanh toán, khách, loại dòng ---------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Xong", HOAN_THANH), ("đã lấy", HOAN_THANH), ("Đã giao", HOAN_THANH), ("ok", HOAN_THANH),
    ("completed", HOAN_THANH), ("Thành công", HOAN_THANH),
    ("Đã hủy", HUY), ("Đã huỷ", HUY), ("khách hủy", HUY), ("cancelled", HUY),
    ("Không giao được", HUY),            # kiểm chứng bằng đáp án biz_124
    ("Đổi trả", TRA_HANG), ("hàng trả về", TRA_HANG), ("Đã hoàn hàng", TRA_HANG), ("Khách trả", TRA_HANG),
    ("returned", TRA_HANG),
    ("Đang giao", DANG_GIAO), ("đang gửi", DANG_GIAO), ("Chờ giao", DANG_GIAO), ("shipping", DANG_GIAO),
    ("Đang vận chuyển", DANG_GIAO),
    (None, None), ("abc", None),
])
def test_normalize_status(raw, expected):
    assert normalize_status(raw) == expected


def test_combine_status():
    assert combine_status([HOAN_THANH, TRA_HANG]) == TRA_HANG
    assert combine_status([HOAN_THANH, None]) == HOAN_THANH
    assert combine_status([None]) is None


@pytest.mark.parametrize("raw, expected", [
    ("Tiền mặt", "tien_mat"), ("cash", "tien_mat"), ("Chuyển khoản", "chuyen_khoan"), ("transfer", "chuyen_khoan"),
    ("Ví điện tử", "vi_dien_tu"), ("ewallet", "vi_dien_tu"), ("Thu hộ (COD)", "cod"), ("cod", "cod"),
    ("Ghi nợ", "ghi_no"), ("debt", "ghi_no"),
])
def test_normalize_payment(raw, expected):
    assert normalize_payment(raw) == expected


@pytest.mark.parametrize("raw, name, phone", [
    ("Nguyễn Văn A (0900000001)", "Nguyễn Văn A", "0900000001"),
    ("Trần Thị B 0900000002", "Trần Thị B", "0900000002"),
    ("Lê Văn C - 0900 000 003", "Lê Văn C", "0900000003"),
    ("Nguyễn Phương An", "Nguyễn Phương An", None),
])
def test_split_phone(raw, name, phone):
    assert split_phone(raw) == (name, phone)


@pytest.mark.parametrize("raw, expected", [("Khách lẻ", True), ("khách lẻ", True), ("lẻ", True), ("kl", True),
                                           (None, True), ("Lê Hải Phúc", False)])
def test_is_walkin(raw, expected):
    assert is_walkin(raw) is expected


def test_name_keys():
    assert name_key("Ngo Nam Dung") == name_key("Ngô Nam Dũng")          # khác dấu -> cùng khoá so khớp
    assert name_key("Rau  muống xào tỏi") == name_key("rau muống xào tỏi")  # khoảng trắng thừa
    assert name_key("PEPSI 330ML") == name_key("Pepsi 330ml")
    assert col_key("MaHoaDon") == col_key("Mã hóa đơn")
    assert col_key("Thành tiền (đ)") == col_key("Thành tiền")
    assert clean_str("  Coca  Cola  ") == "Coca Cola"
    assert clean_str("#N/A") is None


@pytest.mark.parametrize("raw, expected", [("Phí phục vụ", "phi_phuc_vu"), ("Voucher", "voucher"),
                                           ("Dùng 50 điểm", "dung_diem"), ("Phí ship", "phi_ship"),
                                           ("Cà phê sữa (M)", "hang")])
def test_line_kind(raw, expected):
    assert line_kind(raw) == expected


# --- ràng buộc: quy tắc mô tả chỉ được rút ra từ README TRAIN ----------------------------------------

def test_every_desc_rule_seen_in_train_readmes():
    descs = []
    for p in sorted((ROOT / "train" / "data").glob("*/README.md")):
        info = parse_readme(p)
        descs += [d for _, d in info.all_pairs()] + [x.desc for x in info.convention_pairs]
    if not descs:
        pytest.skip("không có dữ liệu train")
    keys = [desc_key(d) for d in descs]
    unused = [pat for pat, _ in DESC_RULES if not any(re.search(pat, k) for k in keys)]
    assert not unused, f"quy tắc không khớp mô tả nào của README train: {unused}"


def test_classify_desc_examples():
    assert classify_desc("thành tiền sau giảm") == "thanh_tien"
    assert classify_desc("tên khách (Khách lẻ nếu không lưu)") == "ten_khach"
    assert classify_desc("số lượng đã đổi ra đơn vị cơ bản") == "so_luong_co_ban"
    assert classify_desc("giá nhập một đơn vị (theo đơn vị nhập của dòng)") == "gia_nhap"
    assert classify_desc("ngày sửa") is None          # mô tả của ngành mới (sửa xe): không đoán
