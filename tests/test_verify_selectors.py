"""Hàm phụ của bộ chọn câu trong verifier (câu tự viết, không lấy từ file BTC)."""
from verify_business import ORDERS_BOUND, _bounds, _contiguous, _month_seq


def test_month_sequences():
    assert _month_seq('doanh thu 3 thang lien nhau ket thuc o thang 2/2026 la bao nhieu') == [(12, 2025), (1, 2026), (2, 2026)]
    assert _month_seq('tu thang 11/2025 den thang 1/2026 doanh thu moi thang') == [(11, 2025), (12, 2025), (1, 2026)]
    assert _month_seq('tu thang 3/2025 qua thang 4/2025 roi thang 6/2025') == [(3, 2025), (4, 2025), (6, 2025)]
    assert not _contiguous([(3, 2025), (4, 2025), (6, 2025)])
    assert _contiguous([(12, 2025), (1, 2026)])
    assert _month_seq('doanh thu ngay 17/01/2026') == []


def test_order_bounds_follow_section_2():
    def bounds(text):
        return _bounds(ORDERS_BOUND.search(text))
    assert bounds('khach mua tu 3 don tro len') == (3, None)
    assert bounds('khach mua it nhat 4 don') == (4, None)
    assert bounds('mat hang co mat o ≥ 7 don hang khac nhau') == (7, None)
    assert bounds('khach mua hon 2 don') == (3, None)
    assert bounds('khach mua duoi 2 don') == (None, 1)
    assert bounds('khach mua tu 3 don') is None          # thiếu "trở lên": không đoán
