"""API mở rộng của business/ trên dữ liệu và rulebook TỔNG HỢP (không dùng file BTC)."""
import pandas as pd
import pytest

from business import DateRange, Rulebook, UnsupportedRule
from business.sales import DataError, Filters, SalesMetrics
from conftest import RULES

# Rulebook giả lập: luật chung (conftest) + các dòng các API mở rộng cần.
EXT_RULES = RULES.replace(
    '| Số đơn | chỉ tính đơn không huỷ, không trả |',
    '| Số đơn | chỉ tính đơn không huỷ, không trả; cả khi đếm số đơn có một mặt hàng, số đơn của một khách. '
    'Khách đã mua trong kỳ là khách có ít nhất một đơn như vậy |').replace(
    '| Mặt hàng | Phí phục vụ không phải mặt hàng: không xếp hạng. Vẫn tính vào doanh thu |',
    '| Mặt hàng | Phí phục vụ không phải mặt hàng: không xếp hạng, không đếm. Vẫn tính vào doanh thu |') + '''
| Quá N, hơn N, trên N, dưới N | **không** gồm N. **Từ N trở lên** thì gồm N |
| Hàng lời nhất | theo tổng lãi gộp của mặt hàng |
| Nhân viên bán giỏi nhất | theo **doanh thu** của nhân viên trong kỳ, không theo số đơn |
| Mặt hàng không bán được trong kỳ (ế) | mặt hàng đã từng bán trước kỳ (không tính đơn huỷ, trả) nhưng trong kỳ không có đơn nào mua |
| Giá bán X ngày D | đơn giá trên dòng bán, cho **một đơn vị cơ bản**, **trước** chiết khấu dòng; tính cả dòng của đơn huỷ, đơn trả |
| Lãi gộp | doanh thu trừ giá vốn. Giá vốn dòng = số lượng nhân giá vốn ghi trên dòng bán (cho một đơn vị bán). Không tự tính lại giá vốn từ phiếu nhập |
### Cà phê
| Luật | Mặc định |
|---|---|
| Size M, size L | món có tên kết thúc bằng `(M)` hoặc `(L)`, không phân biệt hoa thường |
Câu hỏi nhiều số thì ghi list theo đúng thứ tự câu hỏi nêu. Phần trăm và số trung bình khác làm tròn 2 chữ số thập phân.
'''

# Các dòng chỉ có ở rulebook public (giả lập lại bằng lời của mình).
PUBLIC_ONLY = '''
| Luật | Mặc định |
|---|---|
| Khách trung thành nhất | khách có nhiều ngày có mua nhất trong kỳ |
| Khách sộp nhất | khách có giá trị trung bình một đơn cao nhất, chỉ xét khách có từ 3 đơn trở lên |
| Khách hay đổi ý nhất | khách có nhiều đơn huỷ nhất trong kỳ |
| Mặt hàng được ưa chuộng nhất | mặt hàng có mặt trong nhiều đơn nhất trong kỳ |
| Nhân viên, thợ chăm chỉ nhất | nhiều ngày làm việc nhất; ngày làm việc là ngày có ít nhất một đơn do người đó bán |
| Ngày đắt khách nhất | ngày có nhiều đơn nhất trong kỳ |
| Giờ cao điểm | khung một giờ tròn theo giờ tạo đơn có nhiều đơn nhất. Đáp án là giờ bắt đầu khung, type number |
| Trung bình mỗi ngày thứ X của kỳ | chia cho số ngày thứ X trong kỳ, kể cả ngày không có đơn |
'''

MARCH = DateRange('2026-03-01', '2026-03-31')
FEB = DateRange('2026-02-01', '2026-02-28')


@pytest.fixture
def ext_rules():
    return Rulebook.from_text(EXT_RULES)


@pytest.fixture
def public_rules():
    return Rulebook.from_text(EXT_RULES + PUBLIC_ONLY)


@pytest.fixture
def tables():
    orders = pd.DataFrame([
        # tháng 2 (trước kỳ): F2 huỷ nên P6 chưa "từng bán"
        ['F1', '2026-02-10', '2026-02-10 09:10', 'hoan_thanh', 'K1', 'An', False, 'NV1'],
        ['F2', '2026-02-11', '2026-02-11 10:00', 'huy', 'K2', 'Bình', False, 'NV2'],
        # tháng 3: 02/03 và 09/03 là thứ Hai
        ['O1', '2026-03-02', '2026-03-02 08:15', 'hoan_thanh', 'K1', 'An', False, 'NV1'],
        ['O2', '2026-03-02', '2026-03-02 08:45', 'hoan_thanh', 'K2', 'Bình', False, 'NV2'],
        ['O3', '2026-03-03', '2026-03-03 14:05', 'hoan_thanh', 'K1', 'An', False, 'NV2'],
        ['O4', '2026-03-03', '2026-03-03 15:30', 'huy', 'K2', 'Bình', False, 'NV1'],
        ['O5', '2026-03-09', '2026-03-09 08:00', 'tra_hang', 'K3', 'Chi', False, 'NV1'],
        ['O6', '2026-03-09', '2026-03-09 09:20', 'hoan_thanh', None, 'Khách lẻ', True, 'NV1'],
        ['O7', '2026-03-10', '2026-03-10 08:30', 'hoan_thanh', 'K1', 'An', False, 'NV1'],
        ['O8', '2026-03-10', '2026-03-10 09:00', 'huy', 'K1', 'An', False, 'NV2'],
    ], columns=['ma_don', 'ngay_dat', 'thoi_diem_dat', 'trang_thai', 'ma_khach', 'ten_khach', 'la_khach_le',
                'ma_nhan_vien'])
    orders['khach_key'] = orders['ma_khach']
    lines = pd.DataFrame([
        # ma_don, ma_hang, loai, so_luong, so_luong_co_ban, don_gia, thanh_tien, gia_von_dong
        ['F1', 'P3', 'hang', 1, 1, 20000, 20000, 12000],
        ['F1', 'P4', 'hang', 1, 1, 30000, 30000, 8000],
        ['F2', 'P6', 'hang', 1, 1, 5000, 5000, 3000],
        ['O1', 'P1', 'hang', 2, 2, 30000, 60000, 10000],
        ['O1', 'P2', 'hang', 1, 1, 40000, 35000, 15000],      # chiết khấu dòng 5000
        ['O1', 'S', 'phi_phuc_vu', 1, 1, 5000, 5000, None],
        ['O2', 'P1', 'hang', 1, 1, 30000, 30000, 10000],
        ['O3', 'P5', 'hang', 1, 24, 120000, 120000, 100000],  # 1 thùng = 24 chai
        ['O4', 'P1', 'hang', 1, 1, 32000, 32000, 10000],
        ['O5', 'P2', 'hang', 2, 2, 40000, 80000, 15000],
        ['O6', 'P4', 'hang', 1, 1, 30000, 30000, 8000],
        ['O7', 'P1', 'hang', 1, 1, 30000, 30000, 10000],
        ['O8', 'P4', 'hang', 1, 1, 30000, 30000, 8000],
    ], columns=['ma_don', 'ma_hang', 'loai_dong', 'so_luong', 'so_luong_co_ban', 'don_gia', 'thanh_tien',
                'gia_von_dong'])
    products = pd.DataFrame([
        ['P1', 'Cà phê (M)', 'ly'], ['P2', 'Cà phê (l)', 'ly'], ['P3', 'Bánh', 'cái'], ['P4', 'Trà', 'ly'],
        ['P5', 'Nước suối', 'chai'], ['P6', 'Kẹo', 'gói'], ['S', 'Phí phục vụ', None],
    ], columns=['ma_hang', 'ten_hang', 'don_vi_co_ban'])
    return {'don_hang': orders, 'dong_hang': lines, 'mat_hang': products,
            'cua_hang': {'ngay_bat_dau_du_lieu': '2026-02-01', 'ngay_ket_thuc_du_lieu': '2026-03-31',
                         'co_ma_don': True, 'co_ma_khach': True}}


def engine(tables, rules, as_of='2026-03-31'):
    return SalesMetrics(tables, rules, as_of)


# C1 ------------------------------------------------------------------------------------------------

def test_best_period_day_month_and_ties(tables, ext_rules):
    e = engine(tables, ext_rules)
    assert e.best_period(MARCH).answer == '2026-03-02'                         # 130000
    assert e.best_period(MARCH, metric='orders').answer == '2026-03-02'        # 2 đơn
    assert e.best_period(MARCH, kind='min').answer == '2026-03-01'             # ngày trống = 0, ngày sớm nhất
    both = DateRange('2026-02-01', '2026-03-31')
    assert e.best_period(both, granularity='month').answer == '2026-03'
    assert e.best_period(both, granularity='month', kind='min').answer == '2026-02'
    assert e.best_period(DateRange('2026-03-09', '2026-03-10')).answer == '2026-03-09'  # bằng nhau: ngày sớm hơn
    assert e.best_period(DateRange('2025-01-01', '2025-01-31')).type == 'unanswerable'


# C2 (đã có qua Filters) + C5 size + nhân viên --------------------------------------------------------

def test_product_size_and_staff_filters(tables, ext_rules):
    e = engine(tables, ext_rules)
    assert e.revenue(MARCH, Filters(product_ids=('P1',))).answer == 120000
    assert e.quantity(MARCH, Filters(size='M'), unit='ly').answer == 4
    assert e.quantity(MARCH, Filters(size='L'), unit='ly').answer == 1        # '(l)' không phân biệt hoa thường
    assert e.revenue(MARCH, Filters(size='m')).answer == 120000
    with pytest.raises(UnsupportedRule):
        e.quantity(MARCH, Filters(size='S'))
    assert e.revenue(MARCH, Filters(staff='NV2')).answer == 150000
    assert e.revenue(MARCH, Filters(staff='NV9')).type == 'unanswerable'


def test_size_requires_rule(tables, rules):
    with pytest.raises(UnsupportedRule):
        engine(tables, rules).quantity(MARCH, Filters(size='M'))


# C3 ------------------------------------------------------------------------------------------------

def test_price_on_date(tables, ext_rules):
    e = engine(tables, ext_rules)
    assert e.price_on_date('P1', '2026-03-02').answer == 30000
    assert e.price_on_date('P2', '2026-03-02').answer == 40000     # trước chiết khấu dòng
    assert e.price_on_date('P1', '2026-03-03').answer == 32000     # dòng của đơn huỷ vẫn tính
    assert e.price_on_date('P5', '2026-03-03').answer == 5000      # 120000 / 24 chai
    assert e.price_on_date('P3', '2026-03-02').type == 'unanswerable'
    assert engine(tables, ext_rules, '2026-03-02').price_on_date('P1', '2026-03-03').type == 'unanswerable'
    tables['dong_hang'].loc[tables['dong_hang']['ma_don'].eq('O2'), 'don_gia'] = 31000
    with pytest.raises(DataError):
        engine(tables, ext_rules).price_on_date('P1', '2026-03-02')


def test_price_rule_missing_is_unsupported(tables, rules):
    with pytest.raises(UnsupportedRule):
        engine(tables, rules).price_on_date('P1', '2026-03-02')


# C4 ------------------------------------------------------------------------------------------------

def test_revenue_series_and_monotonic(tables, ext_rules):
    e = engine(tables, ext_rules)
    assert e.revenue_series([FEB, MARCH]).answer == [50000, 310000]
    assert e.is_monotonic([FEB, MARCH]).answer is True
    assert e.is_monotonic([MARCH, FEB]).answer is False
    assert e.is_monotonic([MARCH, FEB], 'decreasing').answer is True
    assert e.is_monotonic([FEB, FEB]).answer is False                          # bằng nhau không phải tăng
    assert e.revenue_series([DateRange('2025-01-01', '2025-01-31'), MARCH]).type == 'unanswerable'


# C6 ------------------------------------------------------------------------------------------------

def test_slow_moving_products(tables, ext_rules):
    e = engine(tables, ext_rules)
    assert e.slow_moving_products(MARCH).answer == 1                          # P3; P6 chỉ bán ở đơn huỷ
    assert e.slow_moving_products(MARCH, as_list=True).answer == ['Bánh']
    assert e.slow_moving_products(FEB).type == 'unanswerable'                 # không có dữ liệu trước kỳ


# C7 ------------------------------------------------------------------------------------------------

def test_gross_profit(tables, ext_rules):
    e = engine(tables, ext_rules)
    assert e.gross_profit(MARCH).answer == 147000          # 310000 − 163000; phí phục vụ không có giá vốn
    assert e.top_products(MARCH, k=4, metric='gross_profit').answer == ['Cà phê (M)', 'Trà', 'Cà phê (l)', 'Nước suối']
    tables['dong_hang'].loc[0, 'gia_von_dong'] = None
    tables['dong_hang'].loc[3, 'gia_von_dong'] = None
    with pytest.raises(DataError):
        engine(tables, ext_rules).gross_profit(MARCH)
    tables['dong_hang'] = tables['dong_hang'].drop(columns='gia_von_dong')
    assert engine(tables, ext_rules).gross_profit(MARCH).type == 'unanswerable'


# C8 ------------------------------------------------------------------------------------------------

def test_customer_and_product_counts(tables, ext_rules):
    e = engine(tables, ext_rules)
    assert e.customer_count(MARCH).answer == 2                     # K1, K2; K3 chỉ có đơn trả, khách lẻ bỏ
    assert e.customer_count(MARCH, min_orders=3).answer == 1       # từ 3 trở lên gồm 3
    assert e.customer_count(MARCH, min_orders=4).answer == 0
    assert e.customer_count(MARCH, max_orders=1).answer == 1
    assert e.customer_share(MARCH, min_orders=2).answer == 50
    assert e.products_in_at_least(MARCH, 2).answer == 1            # P1 có mặt 3 đơn
    assert e.products_in_at_least(MARCH, 1).answer == 4            # phí phục vụ không đếm
    assert e.order_count(MARCH, Filters(product_ids=('P1',))).answer == 3


def test_count_bounds_need_rule(tables, rules):
    with pytest.raises(UnsupportedRule):
        engine(tables, rules).customer_count(MARCH, min_orders=2)


# C9 ------------------------------------------------------------------------------------------------

def test_top_staff_by_revenue(tables, ext_rules):
    e = engine(tables, ext_rules)
    top = e.top_staff(MARCH, k=2)
    assert top.answer == ['NV1', 'NV2']                            # 160000 > 150000
    assert top.single().type == 'string' and top.single().answer == 'NV1'


# C10 -----------------------------------------------------------------------------------------------

def test_public_only_rules(tables, public_rules):
    e = engine(tables, public_rules)
    assert e.loyal_customers(MARCH).answer == ['An']                       # 3 ngày
    assert e.big_spender_customers(MARCH).answer == ['An']                 # chỉ An có ≥ 3 đơn
    assert e.fickle_customers(MARCH, k=2).answer == ['An', 'Bình']         # 1-1, theo mã
    assert e.favorite_products(MARCH).answer == ['Cà phê (M)']
    assert e.hardworking_staff(MARCH).answer == ['NV1']                    # 3 ngày (bỏ đơn huỷ/trả)
    assert e.busiest_day(MARCH).answer == '2026-03-02'
    peak = e.peak_hour(MARCH)
    assert peak.type == 'number' and peak.answer == 8
    assert e.weekday_average(MARCH, 0).answer == 32000                     # 160000 / 5 thứ Hai
    assert e.weekday_average(MARCH, 0, metric='orders').answer == 0.6
    assert e.weekday_average(MARCH, 1).answer == 30000


def test_big_spender_threshold_read_from_rule(tables, ext_rules):
    text = EXT_RULES + PUBLIC_ONLY.replace('từ 3 đơn', 'từ 4 đơn')
    assert engine(tables, Rulebook.from_text(text)).big_spender_customers(MARCH).type == 'unanswerable'


@pytest.mark.parametrize('call', [
    lambda e: e.loyal_customers(MARCH), lambda e: e.big_spender_customers(MARCH),
    lambda e: e.fickle_customers(MARCH), lambda e: e.favorite_products(MARCH),
    lambda e: e.hardworking_staff(MARCH), lambda e: e.busiest_day(MARCH), lambda e: e.peak_hour(MARCH),
    lambda e: e.weekday_average(MARCH, 0),
])
def test_public_only_rules_unsupported_without_rows(tables, ext_rules, call):
    with pytest.raises(UnsupportedRule):
        call(engine(tables, ext_rules))


def test_customer_count_needs_no_names_when_codes_exist(tables, ext_rules):
    tables['don_hang'] = tables['don_hang'].drop(columns='ten_khach')
    assert engine(tables, ext_rules).customer_count(MARCH, min_orders=3).answer == 1
