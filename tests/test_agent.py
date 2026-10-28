"""Tầng agent trên dữ liệu TỔNG HỢP: spec, khớp tên, kỳ so, pipeline với LLM giả (không gọi model)."""
import json
from datetime import date

import pandas as pd
import pytest

from agent.dispatch import comparison_range, to_range
from agent.llm import Completion
from agent.pipeline import Agent, consistent
from agent.resolve import Ambiguous, Catalog
from agent.spec import Period, parse_spec
from business import Periods, Rulebook
from load_all import to_parquet
from test_business_ext import EXT_RULES, PUBLIC_ONLY


# ---- spec ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("spec, ok", [
    ({"op": "revenue", "answer_type": "number", "period": {"kind": "month", "month": 3, "year": 2026}}, True),
    ({"op": "revenue", "answer_type": "percent", "period": {"kind": "today"}}, False),        # type sai op
    ({"op": "revenue", "answer_type": "number"}, False),                                       # thiếu period
    ({"op": "xoa_du_lieu", "answer_type": "number"}, False),                                   # op ngoài danh sách
    ({"op": "revenue", "answer_type": "number", "period": {"kind": "month"}}, False),          # thiếu tháng
    ({"op": "revenue", "answer_type": "number", "period": {"kind": "previous_period"}}, False),  # chỉ cho comparison
    ({"op": "top_products", "answer_type": "string", "period": {"kind": "today"}, "metric": "tien"}, False),
    ({"op": "unsupported"}, True),
])
def test_spec_validation(spec, ok):
    assert (parse_spec(spec)[0] is not None) is ok
    assert (parse_spec(json.dumps(spec))[0] is not None) is ok


# ---- khớp tên ------------------------------------------------------------------------------------

@pytest.fixture
def tables():
    orders = pd.DataFrame([
        ['O1', '2026-03-02', '2026-03-02 08:15', 'hoan_thanh', 'K1', 'An', False, 'K1', 'tai_quay', 'tien_mat', 'NV001'],
        ['O2', '2026-03-03', '2026-03-03 15:00', 'hoan_thanh', 'K2', 'Bình', False, 'K2', 'zalo', 'chuyen_khoan', 'NV002'],
        ['O3', '2026-04-01', '2026-04-01 09:00', 'hoan_thanh', 'K1', 'An', False, 'K1', 'zalo', 'tien_mat', 'NV001'],
    ], columns=['ma_don', 'ngay_dat', 'thoi_diem_dat', 'trang_thai', 'ma_khach', 'ten_khach', 'la_khach_le', 'khach_key',
                'kenh_ban', 'hinh_thuc_tt', 'ma_nhan_vien'])
    lines = pd.DataFrame([
        ['O1', 'P1', 'hang', 2, 2, 30000, 60000], ['O2', 'P2', 'hang', 1, 1, 40000, 40000],
        ['O3', 'P1', 'hang', 1, 1, 30000, 30000],
    ], columns=['ma_don', 'ma_hang', 'loai_dong', 'so_luong', 'so_luong_co_ban', 'don_gia', 'thanh_tien'])
    products = pd.DataFrame([['P1', 'Cà phê sữa (M)', 'Cà phê', 'ly'], ['P2', 'Cà phê sữa (L)', 'Cà phê', 'ly'],
                             ['P3', 'Trà đào', 'Trà', 'ly']], columns=['ma_hang', 'ten_hang', 'nhom_hang', 'don_vi_co_ban'])
    return {'don_hang': orders, 'dong_hang': lines, 'mat_hang': products,
            'cua_hang': {'ngay_bat_dau_du_lieu': '2026-03-01', 'ngay_ket_thuc_du_lieu': '2026-04-30',
                         'co_ma_don': True, 'co_ma_khach': True, 'nang_luc': {'dong_hang': True}}}


def test_catalog_matching(tables):
    cat = Catalog(tables)
    assert cat.product_ids('ca phe sua (m)') == ('P1',)            # bỏ dấu, hoa thường
    assert cat.product_ids('món Trà đào') == ('P3',)               # tên danh mục nằm trọn trong chuỗi
    with pytest.raises(Ambiguous):
        cat.product_ids('cà phê sữa')                               # khớp 2 món -> không đoán
    with pytest.raises(Ambiguous):
        cat.product_ids('bánh mì')
    assert cat.group('tra') == 'Trà'
    assert cat.channel('bán tại quầy') == 'tai_quay'
    assert cat.payment('chuyển khoản') == 'chuyen_khoan'
    assert cat.staff_code('nv 002') == 'NV002'
    assert 'Cà phê' in cat.card(tables['cua_hang'])


def test_comparison_periods_are_computed_by_code():
    rules = Rulebook.from_text(EXT_RULES)
    periods = Periods(rules, '2026-03-15')
    month = Period(kind='month', month=1, year=2026)
    base = to_range(month, periods, {})
    prev = comparison_range(Period(kind='previous_period'), month, base, periods, {})
    assert (prev.start, prev.end) == (date(2025, 12, 1), date(2025, 12, 31))
    this = Period(kind='this_month')
    same = comparison_range(Period(kind='previous_period'), this, to_range(this, periods, {}), periods, {})
    assert (same.start, same.end) == (date(2026, 2, 1), date(2026, 2, 15))     # §2 cùng số ngày tháng trước
    last = comparison_range(Period(kind='same_period_last_year'), month, base, periods, {})
    assert (last.start, last.end) == (date(2025, 1, 1), date(2025, 1, 31))


# ---- pipeline với LLM giả ----------------------------------------------------------------------------

class FakeLLM:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def complete(self, messages, schema=None, temperature=None, seed=None):
        self.calls += 1
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return Completion(reply if isinstance(reply, str) else json.dumps(reply), 10, 5, 0.01)


@pytest.fixture
def agent_env(tmp_path, tables):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'rulebook.md').write_text(EXT_RULES + PUBLIC_ONLY, encoding='utf-8')
    (data / 'calendar.csv').write_text('date,lunar_year,lunar_month,lunar_day,lunar_leap\n', encoding='utf-8')
    shop = tmp_path / 'cache' / 'shop_x'
    shop.mkdir(parents=True)
    for name in ('don_hang', 'dong_hang', 'mat_hang'):
        to_parquet(tables[name], shop / f'{name}.parquet')
    (shop / 'cua_hang.json').write_text(json.dumps(tables['cua_hang']), encoding='utf-8')
    bank = tmp_path / 'bank.jsonl'
    bank.write_text(json.dumps({'id': 'b1', 'business_id': 'other', 'question': 'doanh thu tháng 2/2026',
                                'spec': {'op': 'revenue', 'answer_type': 'number',
                                         'period': {'kind': 'month', 'month': 2, 'year': 2026}}}) + '\n')
    cfg = {'self_consistency': {'temperature': 0.7, 'seeds': [1, 2, 3]}}
    q = {'id': 'q1', 'business_id': 'shop_x', 'question': 'doanh thu tháng 3/2026?', 'as_of_date': '2026-04-30'}
    return lambda llm: Agent(cfg, data, tmp_path / 'cache', bank, llm=llm), q


MARCH = {'op': 'revenue', 'answer_type': 'number', 'period': {'kind': 'month', 'month': 3, 'year': 2026}}


def test_pipeline_answers_and_abstains(agent_env):
    make, q = agent_env
    assert make(FakeLLM([MARCH])).answer(q)['final_a'] == {'type': 'number', 'answer': 100000}
    # spec lỗi -> sửa 1 lần -> được
    llm = FakeLLM(['{"op": "revenue"}', MARCH])
    rec = make(llm).answer(q)
    assert rec['final_a']['answer'] == 100000 and rec['greedy']['fixed'] and llm.calls == 2
    # lỗi cả 2 lần -> abstain
    assert make(FakeLLM(['không phải json'])).answer(q)['greedy']['reason'] == 'spec_invalid'
    assert make(FakeLLM([{'op': 'unsupported'}])).answer(q)['greedy']['reason'] == 'op_unsupported'
    bad_name = {**MARCH, 'product': 'cà phê sữa'}
    assert make(FakeLLM([bad_name])).answer(q)['greedy']['reason'] == 'ambiguous_name'
    peak = {'op': 'peak_hour', 'answer_type': 'number', 'period': MARCH['period']}
    rec = make(FakeLLM([peak])).answer(q)
    assert rec['greedy']['reason'] == 'low_confidence' and rec['greedy']['would_be']['answer'] == 8


def test_self_consistency(agent_env):
    make, q = agent_env
    rec = make(FakeLLM([MARCH])).answer(q, self_consistency=True)
    assert rec['final_b'] == rec['final_a'] and len(rec['samples']) == 3
    other = {**MARCH, 'period': {'kind': 'month', 'month': 4, 'year': 2026}}
    rec = make(FakeLLM([MARCH, MARCH, other, MARCH])).answer(q, self_consistency=True)
    assert rec['final_a']['answer'] == 100000 and rec['final_b'] == {'type': 'abstain'}
    assert consistent({'submission': {'type': 'abstain'}}, []) == {'type': 'abstain'}
