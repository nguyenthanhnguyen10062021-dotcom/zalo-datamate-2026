"""Nhà thuốc (kê đơn, hoạt chất) và hiệu ứng tăng giá trên dữ liệu + rulebook TỔNG HỢP."""
import pandas as pd
import pytest

from business import DateRange, Rulebook, UnsupportedRule
from business.sales import DataError, Filters, SalesMetrics
from test_business_ext import EXT_RULES

DRUG_RULES = EXT_RULES + '''
| Luật | Mặc định |
|---|---|
| Thuốc kê đơn | **Thuốc kê đơn** = sản phẩm ghi kê đơn trong danh mục thuốc; mọi sản phẩm còn lại là **hàng không kê đơn**. Tỉ lệ kê đơn tính theo doanh thu |
| Doanh thu theo hoạt chất | doanh thu (§1) các thuốc có hoạt chất ghi **đúng như vậy** trong danh mục thuốc. Thuốc phối hợp nhiều hoạt chất là **một loại riêng**, không tính vào từng hoạt chất trong đó |
| Hiệu ứng tăng giá | lần tăng giá = ngày D giá mới cao hơn giá liền trước (theo bảng giá); tăng lên cùng một giá nhiều lần thì lấy lần đầu. So số lượng (đơn vị cơ bản) **N ngày kể từ D** (tính cả D) với **N ngày ngay trước D**; cả hai khoảng bỏ đơn huỷ và đơn trả |
'''
MARCH = DateRange('2026-03-01', '2026-03-31')


@pytest.fixture
def rules():
    return Rulebook.from_text(DRUG_RULES)


@pytest.fixture
def tables():
    def order(i, day, status='hoan_thanh'):
        return [f'O{i}', day, f'{day} 09:00', status, None, None, True, None]
    days = ['2026-03-01', '2026-03-02', '2026-03-03', '2026-03-04', '2026-03-05', '2026-03-06', '2026-03-07']
    orders = pd.DataFrame([order(i + 1, d) for i, d in enumerate(days)] + [order(8, '2026-03-04', 'huy'),
                                                                          order(9, '2026-03-05', 'tra_hang')],
                          columns=['ma_don', 'ngay_dat', 'thoi_diem_dat', 'trang_thai', 'ma_khach', 'ten_khach',
                                   'la_khach_le', 'khach_key'])
    # ma_don, ma_hang, so_luong, tien. Giá P1 tăng ngày 04/03: trước (01-03) 1+2+1, từ 04/03 (04-06) 2+4+1
    lines = pd.DataFrame([
        ['O1', 'P1', 1, 10], ['O2', 'P1', 2, 20], ['O3', 'P1', 1, 10],
        ['O4', 'P1', 2, 26], ['O5', 'P1', 4, 52], ['O6', 'P1', 1, 13],
        ['O7', 'P2', 3, 300], ['O1', 'P3', 1, 100], ['O2', 'P4', 1, 40],
        ['O8', 'P1', 50, 650], ['O9', 'P1', 50, 650],           # huỷ/trả không tính vào số lượng
    ], columns=['ma_don', 'ma_hang', 'so_luong', 'thanh_tien'])
    lines['loai_dong'] = 'hang'
    lines['so_luong_co_ban'] = lines['so_luong']
    lines['don_gia'] = lines['thanh_tien'] / lines['so_luong']
    products = pd.DataFrame([[c, c, 'viên'] for c in ('P1', 'P2', 'P3', 'P4')],
                            columns=['ma_hang', 'ten_hang', 'don_vi_co_ban'])
    thuoc = pd.DataFrame([['P1', 'Loratadin', False], ['P2', 'Paracetamol', True],
                          ['P3', 'Paracetamol + Cafein', False], ['P4', None, None]],
                         columns=['ma_hang', 'hoat_chat', 'ke_don'])
    bang_gia = pd.DataFrame([['P1', '2026-01-01', 10], ['P1', '2026-03-04', 13], ['P1', '2026-03-10', 12],
                             ['P1', '2026-03-12', 13], ['P2', '2026-01-01', 100]],
                            columns=['ma_hang', 'ngay_ap_dung', 'gia'])
    bang_gia['ngay_ap_dung'] = pd.to_datetime(bang_gia['ngay_ap_dung'])
    return {'don_hang': orders, 'dong_hang': lines, 'mat_hang': products, 'thuoc': thuoc, 'bang_gia': bang_gia,
            'cua_hang': {'ngay_bat_dau_du_lieu': '2026-01-01', 'ngay_ket_thuc_du_lieu': '2026-03-31',
                         'co_ma_don': True, 'co_ma_khach': False}}


def engine(tables, rules, as_of='2026-03-31'):
    return SalesMetrics(tables, rules, as_of)


def test_prescription_revenue_and_share(tables, rules):
    e = engine(tables, rules)
    total = 10 + 20 + 10 + 26 + 52 + 13 + 300 + 100 + 40
    assert e.revenue(MARCH).answer == total
    assert e.revenue(MARCH, Filters(prescription=True)).answer == 300
    assert e.revenue(MARCH, Filters(prescription=False)).answer == total - 300   # kể cả P4 không ghi cờ
    assert e.prescription_share(MARCH).answer == round(300 / total * 100, 2)
    assert e.prescription_share(MARCH, prescription=False).answer == round((total - 300) / total * 100, 2)


def test_active_ingredient_is_exact_and_combos_are_separate(tables, rules):
    e = engine(tables, rules)
    assert e.revenue(MARCH, Filters(active_ingredient='paracetamol')).answer == 300       # không lẫn thuốc phối hợp
    assert e.revenue(MARCH, Filters(active_ingredient='Paracetamol + Cafein')).answer == 100
    assert e.revenue(MARCH, Filters(active_ingredient='Loratadin')).answer == 131
    assert e.revenue(MARCH, Filters(active_ingredient='Cafein')).type == 'unanswerable'    # không có trong danh mục


def test_drug_filters_need_data_and_rules(tables, rules):
    no_table = {k: v for k, v in tables.items() if k != 'thuoc'}
    assert engine(no_table, rules).revenue(MARCH, Filters(prescription=True)).type == 'unanswerable'
    tables['thuoc'] = tables['thuoc'].assign(ke_don=None)
    assert engine(tables, rules).revenue(MARCH, Filters(prescription=True)).type == 'unanswerable'
    with pytest.raises(UnsupportedRule):
        engine(tables, Rulebook.from_text(EXT_RULES)).revenue(MARCH, Filters(active_ingredient='Loratadin'))


def test_price_increase_effect(tables, rules):
    e = engine(tables, rules)
    # N=3: trước 04/03 = 1+2+1 = 4; từ 04/03 = 2+4+1 = 7 (đơn huỷ/trả bỏ) -> +75%
    assert e.price_increase_effect('P1', '2026-03-04', 3).answer == 75
    assert e.price_increase_effect('P1', '2026-03-04', 3).confidence == 'normal'
    assert e.price_increase_effect('P1', '2026-03-04', 1).answer == 100           # ngày D bán 2, ngày trước D bán 1
    with pytest.raises(DataError):
        e.price_increase_effect('P1', '2026-03-10', 3)        # giảm giá, không phải lần tăng
    with pytest.raises(DataError):
        e.price_increase_effect('P1', '2026-03-12', 3)        # lên lại mức 13 lần thứ hai: chỉ lần đầu tính
    assert e.price_increase_effect('P3', '2026-03-04', 3).answer == -100           # P3 không có trong bảng giá: tin D
    assert e.price_increase_effect('P4', '2026-03-05', 2).type == 'unanswerable'   # 2 ngày trước D bán 0: chia 0


def test_price_increase_without_price_list_uses_given_day(tables, rules):
    del tables['bang_gia']
    assert engine(tables, rules).price_increase_effect('P1', '2026-03-04', 3).answer == 75


def test_price_increase_percent_negative_and_rules(tables, rules):
    e = engine(tables, rules)
    with pytest.raises(DataError):
        e.price_increase_effect('P1', '2026-03-06', 2)        # có bảng giá: 06/03 không phải ngày tăng
    del tables['bang_gia']
    # không có bảng giá: tin ngày D. N=2 từ 06/03: 1+0 = 1; 2 ngày trước: 2+4 = 6 (từ 04/03) -> (1-6)/6 = -83,33%
    assert engine(tables, rules).price_increase_effect('P1', '2026-03-06', 2).answer == -83.33
    with pytest.raises(UnsupportedRule):
        engine(tables, Rulebook.from_text(EXT_RULES)).price_increase_effect('P1', '2026-03-04', 3)
