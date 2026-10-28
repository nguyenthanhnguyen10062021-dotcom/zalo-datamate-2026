from copy import deepcopy

import pandas as pd
import pytest

from business import DateRange, Rulebook, UnsupportedRule
from business.sales import Answer, DataError, Filters, SalesMetrics


@pytest.fixture
def tables():
    # Synthetic orders: two valid, one returned, one cancelled, one future.
    orders = pd.DataFrame([
        ['O1','2026-03-01','2026-03-01 13:59:59','hoan_thanh','K2','Lan',False,'K2','VIP','tai_quan','tien_mat',101],
        ['O2','2026-03-02','2026-03-02 14:00:00','dang_giao','K1','Lan',False,'K1','VIP','online','cod',100],
        ['O3','2026-03-02','2026-03-02 15:00:00','tra_hang','K1','Lan',False,'K1','VIP','online','cod',900],
        ['O4','2026-03-03','2026-03-03 10:00:00','huy',None,None,True,None,None,'online','tien_mat',900],
        ['O5','2026-03-20','2026-03-20 10:00:00','hoan_thanh','K1','Lan',False,'K1','VIP','online','cod',800],
    ], columns=['ma_don','ngay_dat','thoi_diem_dat','trang_thai','ma_khach','ten_khach','la_khach_le','khach_key',
                'nhom_khach','kenh_ban','hinh_thuc_tt','tong_tien_hang'])
    lines = pd.DataFrame([
        ['O1','P2','hang',1,80], ['O1','S','phi_phuc_vu',1,21],
        ['O2','P1','hang',1,90], ['O2','T','topping',1,10],
        ['O3','P1','hang',9,900], ['O4','P1','hang',9,900], ['O5','P1','hang',8,800],
    ], columns=['ma_don','ma_hang','loai_dong','so_luong_co_ban','thanh_tien'])
    products = pd.DataFrame([
        ['P1','Cà phê','Đồ uống','ly'], ['P2','Trà','Đồ uống','ly'],
        ['T','Trân châu','Topping','phần'], ['S','Phí phục vụ',None,None],
    ], columns=['ma_hang','ten_hang','nhom_hang','don_vi_co_ban'])
    return {'don_hang':orders,'dong_hang':lines,'mat_hang':products,
            'cua_hang':{'ngay_bat_dau_du_lieu':'2026-01-01','ngay_ket_thuc_du_lieu':'2026-03-31',
                        'co_ma_don':True,'co_ma_khach':True}}


@pytest.fixture
def period():
    return DateRange('2026-03-01','2026-03-31')


def test_revenue_excludes_entire_return_order_and_future(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.revenue(period).answer == 201
    assert engine.order_count(period).answer == 2
    assert engine.cancelled_orders(period).answer == 1
    assert engine.cancellation_rate(period).answer == 25
    assert engine.average_order_value(period).answer == 101  # 100.5 half-up


def test_filters_and_shifts_follow_order_time(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.revenue(period, Filters(shift='sang')).answer == 101
    assert engine.revenue(period, Filters(shift='chieu')).answer == 100
    assert engine.revenue(period, Filters(payment='cod')).answer == 100
    assert engine.revenue(period, Filters(channel='online')).answer == 100
    assert engine.revenue(period, Filters(product_group='Đồ uống')).answer == 170
    assert engine.revenue(period, Filters(product_ids=('P1',))).answer == 90
    assert engine.revenue_share(period, Filters(product_group='Đồ uống')).answer == 84.58


def test_quantity_uses_base_unit_and_top_products_excludes_service(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.quantity(period, unit='ly').answer == 2
    assert engine.quantity(period, unit='phần').answer == 1
    assert engine.top_products(period, k=9).answer == ['Cà phê','Trà','Trân châu']
    assert engine.top_products(period, k=2, metric='revenue').answer == ['Cà phê','Trà']


def test_customer_ids_keep_same_names_distinct_and_walkins_excluded(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    ranked = engine.top_customers(period, k=5)
    assert ranked.answer == ['Lan','Lan']
    tables['don_hang'].loc[0, ['ma_khach','khach_key']] = None
    tables['don_hang'].loc[0, 'la_khach_le'] = True
    assert SalesMetrics(tables,rules,'2026-03-04').top_customers(period).answer == ['Lan']


def test_outside_data_is_unanswerable_but_empty_supported_period_is_zero(tables, rules):
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.revenue(DateRange('2025-01-01','2025-01-31')).type == 'unanswerable'
    assert engine.revenue(DateRange('2026-02-01','2026-02-28')).answer == 0
    assert engine.revenue(DateRange('2026-03-10','2026-03-15')).type == 'unanswerable'
    assert engine.average_order_value(DateRange('2026-02-01','2026-02-28')).type == 'unanswerable'


def test_order_level_revenue_fallback_without_lines(tables, rules, period):
    tables['dong_hang'] = tables['dong_hang'].iloc[:0]
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.revenue(period).answer == 201
    assert engine.quantity(period).type == 'unanswerable'
    assert engine.revenue(period, Filters(product_ids=('P1',))).type == 'unanswerable'


def test_missing_or_partial_values_do_not_silently_sum_to_zero(tables, rules, period):
    tables['dong_hang'].loc[0,'thanh_tien'] = None
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period)
    tables['don_hang']['hinh_thuc_tt'] = None
    assert SalesMetrics(tables,rules,'2026-03-04').revenue(period, Filters(payment='cod')).type == 'unanswerable'


def test_unknown_status_and_duplicate_order_keys_rejected(tables, rules, period):
    tables['don_hang'].loc[0,'trang_thai'] = None
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period)
    tables['don_hang'].loc[0,'trang_thai'] = 'hoan_thanh'
    tables['don_hang'].loc[1,'ma_don'] = 'O1'
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04')


def test_no_real_order_ids_and_unmapped_quantities_rejected(tables, rules, period):
    tables['cua_hang']['co_ma_don'] = False
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.order_count(period).type == 'unanswerable'
    assert engine.average_order_value(period).type == 'unanswerable'
    tables['dong_hang'].loc[0,'so_luong_co_ban'] = None
    with pytest.raises(DataError):
        engine.quantity(period)


def test_growth_zero_denominator_and_answer_serialization(tables, rules, period):
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.revenue_growth(DateRange('2026-03-02','2026-03-02'), DateRange('2026-03-01','2026-03-01')).answer == -0.99
    assert engine.revenue_growth(period, DateRange('2026-02-01','2026-02-28')).type == 'unanswerable'
    assert engine.revenue(period).to_submission('q') == {'id':'q','type':'number','answer':201}
    assert 'answer' not in Answer('unanswerable',reason='missing').to_submission('q')


def test_changed_revenue_rule_rejected_and_changed_shift_parsed(tables, rules, period):
    changed = Rulebook.from_text(rules.text.replace('không gồm phí giao hàng','gồm phí giao hàng'))
    with pytest.raises(UnsupportedRule):
        SalesMetrics(tables,changed,'2026-03-04').revenue(period)
    shifted = Rulebook.from_text(rules.text.replace('06:00–13:59','06:00–12:59'))
    assert SalesMetrics(tables,shifted,'2026-03-04').revenue(period, Filters(shift='sang')).answer == 0


def test_inputs_not_mutated_and_partial_period_allowed(tables, rules):
    original = deepcopy(tables)
    result = SalesMetrics(tables,rules,'2026-03-04').revenue(DateRange('2025-12-01','2026-03-02'))
    assert result.answer == 201
    for name in ('don_hang','dong_hang','mat_hang'):
        pd.testing.assert_frame_equal(tables[name],original[name])


@pytest.mark.parametrize('missing', ['product_group','customer_group'])
def test_unknown_group_does_not_disappear_from_filtered_revenue(tables, rules, period, missing):
    if missing == 'product_group':
        tables['mat_hang'].loc[0,'nhom_hang'] = None
        filters = Filters(product_group='Đồ uống')
    else:
        tables['don_hang'].loc[1,'nhom_khach'] = None
        filters = Filters(customer_group='VIP')
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period,filters)


@pytest.mark.parametrize('method', ['revenue','top_customers'])
def test_partially_missing_line_coverage_is_detected(tables,rules,period,method):
    tables['dong_hang'] = tables['dong_hang'][tables['dong_hang']['ma_don']!='O2']
    with pytest.raises(DataError):
        getattr(SalesMetrics(tables,rules,'2026-03-04'),method)(period)


def test_unknown_line_kind_is_not_dropped(tables,rules,period):
    tables['dong_hang'].loc[0,'loai_dong']='unknown'
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period)


def test_changed_share_denominator_rejected(tables,rules,period):
    changed = Rulebook.from_text(rules.text.replace('doanh thu cả shop','doanh thu các đơn có khách'))
    with pytest.raises(UnsupportedRule):
        SalesMetrics(tables,changed,'2026-03-04').revenue_share(period,Filters(customer_group='VIP'))


def test_changed_percentage_precision_rejected(tables,rules):
    changed=Rulebook.from_text(rules.text.replace('phần trăm làm tròn 2 chữ số','phần trăm làm tròn 1 chữ số'))
    with pytest.raises(UnsupportedRule):
        SalesMetrics(tables,changed,'2026-03-04').revenue_growth(DateRange('2026-03-02','2026-03-02'),DateRange('2026-03-01','2026-03-01'))


def test_selected_missing_amount_is_data_error_not_unanswerable(tables,rules):
    tables['dong_hang'].loc[2:3,'thanh_tien']=None
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(DateRange('2026-03-02','2026-03-02'))


def test_base_unit_matching_ignores_case(tables,rules,period):
    tables['mat_hang'].loc[:1,'don_vi_co_ban']='Ly'
    assert SalesMetrics(tables,rules,'2026-03-04').quantity(period,unit='ly').answer==2


@pytest.mark.parametrize('name', ['don_hang', 'dong_hang', 'mat_hang', 'cua_hang'])
@pytest.mark.parametrize('problem', ['missing', 'wrong_type'])
def test_malformed_table_structure_is_data_error(tables, rules, name, problem):
    if problem == 'missing':
        del tables[name]
    else:
        tables[name] = None
    with pytest.raises(DataError):
        SalesMetrics(tables, rules, '2026-03-04')


@pytest.mark.parametrize('tables', [None, []])
def test_non_dictionary_input_is_data_error(tables, rules):
    with pytest.raises(DataError):
        SalesMetrics(tables, rules, '2026-03-04')


def test_missing_order_date_column_is_data_error(tables, rules):
    del tables['don_hang']['ngay_dat']
    with pytest.raises(DataError, match='Ngày đặt'):
        SalesMetrics(tables, rules, '2026-03-04')


@pytest.mark.parametrize('problem', ['duplicate', 'missing_key', 'missing_column'])
def test_catalog_errors_do_not_block_pure_order_metrics(tables, rules, period, problem):
    if problem == 'duplicate':
        tables['mat_hang'].loc[1, 'ma_hang'] = 'P1'
    elif problem == 'missing_key':
        tables['mat_hang'].loc[1, 'ma_hang'] = None
    else:
        del tables['mat_hang']['ma_hang']
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.order_count(period).answer == 2
    assert engine.cancelled_orders(period).answer == 1
    assert engine.cancellation_rate(period).answer == 25
    assert engine.top_customers(period, metric='orders').answer == ['Lan', 'Lan']


@pytest.mark.parametrize('operation', ['top_products', 'quantity', 'product_ids', 'product_group'])
def test_catalog_errors_still_block_product_dependencies(tables, rules, period, operation):
    tables['mat_hang'].loc[1, 'ma_hang'] = 'P1'
    engine = SalesMetrics(tables, rules, '2026-03-04')
    with pytest.raises(DataError, match='ma_hang'):
        if operation == 'top_products':
            engine.top_products(period)
        elif operation == 'quantity':
            engine.quantity(period, unit='ly')
        elif operation == 'product_ids':
            engine.order_count(period, Filters(product_ids=('P1',)))
        else:
            engine.revenue(period, Filters(product_group='Đồ uống'))


def test_orphan_lines_only_block_line_dependent_metrics(tables, rules, period):
    tables['dong_hang'] = pd.concat([
        tables['dong_hang'],
        pd.DataFrame([['ORPHAN', 'P1', 'hang', 1, 50]], columns=tables['dong_hang'].columns),
    ], ignore_index=True)
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.order_count(period).answer == 2
    assert engine.cancelled_orders(period).answer == 1
    assert engine.cancellation_rate(period).answer == 25
    assert engine.top_customers(period, metric='orders').answer == ['Lan', 'Lan']
    for call in (
        lambda: engine.revenue(period),
        lambda: engine.average_order_value(period),
        lambda: engine.quantity(period),
        lambda: engine.top_products(period),
        lambda: engine.top_customers(period, metric='revenue'),
        lambda: engine.order_count(period, Filters(product_ids=('P1',))),
    ):
        with pytest.raises(DataError, match='Dòng hàng không nối được'):
            call()


def test_unknown_status_on_excluded_channel_does_not_block_query(tables, rules, period):
    tables['don_hang'].loc[0, 'trang_thai'] = 'bad_status'
    engine = SalesMetrics(tables, rules, '2026-03-04')
    online = Filters(channel='online')
    assert engine.revenue(period, online).answer == 100
    assert engine.cancelled_orders(period, online).answer == 1
    assert engine.cancellation_rate(period, online).answer == 33.33
    assert engine.top_customers(period, filters=online).answer == ['Lan']
    # The share denominator includes the whole shop, including the bad order.
    with pytest.raises(DataError, match='Trạng thái đơn'):
        engine.revenue_share(period, online)


@pytest.mark.parametrize('channel', ['online', None])
def test_unknown_status_not_proven_outside_channel_still_blocks(tables, rules, period, channel):
    tables['don_hang'].loc[0, ['trang_thai', 'kenh_ban']] = ['bad_status', channel]
    engine = SalesMetrics(tables, rules, '2026-03-04')
    online = Filters(channel='online')
    for call in (
        lambda: engine.revenue(period, online),
        lambda: engine.cancelled_orders(period, online),
        lambda: engine.cancellation_rate(period, online),
        lambda: engine.top_customers(period, filters=online),
    ):
        with pytest.raises(DataError):
            call()


@pytest.mark.parametrize('row,column,filters,expected', [
    (2, 'kenh_ban', Filters(channel='online'), 100),
    (3, 'hinh_thuc_tt', Filters(payment='cod'), 100),
    (2, 'nhom_khach', Filters(customer_group='VIP'), 201),
    (2, 'thoi_diem_dat', Filters(shift='chieu'), 100),
])
def test_known_cancelled_or_returned_orders_are_excluded_before_filters(
    tables, rules, period, row, column, filters, expected,
):
    tables['don_hang'].loc[row, column] = None
    assert SalesMetrics(tables, rules, '2026-03-04').revenue(period, filters).answer == expected


@pytest.mark.parametrize('row', [2, 3])
def test_cancellation_rate_retains_returned_and_cancelled_order_dependencies(tables, rules, period, row):
    tables['don_hang'].loc[row, 'hinh_thuc_tt'] = None
    engine = SalesMetrics(tables, rules, '2026-03-04')
    with pytest.raises(DataError, match='hinh_thuc_tt'):
        engine.cancellation_rate(period, Filters(payment='cod'))


@pytest.mark.parametrize('metric', ['orders', 'revenue'])
@pytest.mark.parametrize('channel,expected', [('online', 'Khách online'), ('tai_quan', 'Khách tại quán')])
def test_customer_ranking_order_filters_preserve_positional_api(tables, rules, period, metric, channel, expected):
    names = {'K1': 'Khách online', 'K2': 'Khách tại quán'}
    tables['don_hang']['ten_khach'] = tables['don_hang']['ma_khach'].map(names)
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.top_customers(period, 1, metric, Filters(channel=channel)).answer == [expected]


@pytest.mark.parametrize('operation', ['cancellation_rate', 'top_customers'])
@pytest.mark.parametrize('filters', [Filters(product_ids=('P1',)), Filters(product_group='Đồ uống')])
def test_unsupported_product_filters_are_explicitly_rejected(tables, rules, period, operation, filters):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    with pytest.raises(UnsupportedRule):
        getattr(engine, operation)(period, filters=filters)


@pytest.mark.parametrize('filters,expected', [
    (Filters(product_group='Đồ uống'), 84.58),
    (Filters(channel='online'), 49.75),
])
def test_non_customer_share_does_not_require_customer_group_rule(tables, rules, period, filters, expected):
    no_customer_rule = Rulebook.from_text('\n'.join(
        line for line in rules.text.splitlines() if not line.startswith('| Doanh thu theo nhóm khách |')
    ))
    engine = SalesMetrics(tables, no_customer_rule, '2026-03-04')
    assert engine.revenue_share(period, filters).answer == expected
    with pytest.raises(UnsupportedRule):
        engine.revenue_share(period, Filters(customer_group='VIP'))


def test_customer_share_denominator_keeps_walkin_revenue(tables, rules, period):
    tables['don_hang'].loc[0, ['ma_khach', 'ten_khach', 'khach_key', 'nhom_khach']] = None
    tables['don_hang'].loc[0, 'la_khach_le'] = True
    assert SalesMetrics(tables, rules, '2026-03-04').revenue_share(
        period, Filters(customer_group='VIP'),
    ).answer == 49.75
