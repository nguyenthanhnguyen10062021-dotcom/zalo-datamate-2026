"""Synthetic contrasts for selective semantic verification, without BTC data."""
from copy import deepcopy
import json

import pytest

from nlu import Generation, execute_attempt, inspect_generation
from nlu.semantic import rejection_reason
from queryplan_fixtures import period_spec, plan


@pytest.mark.parametrize('question, candidate', [
    ('Tổng doanh thu tháng này là bao nhiêu?', plan()),
    ('tong dthu hom qua la bn', plan(period=period_spec('yesterday'))),
    ('Số đơn hàng hqua là bao nhiêu?', plan('order_count', period=period_spec('yesterday'))),
    ('Doanh thu 7 ngày gần nhất?', plan(period=period_spec('last_days', n=7))),
    ('Tháng 8 năm 2024 bán được bao nhiêu tiền?', plan(period=period_spec('month', month=8, year=2024))),
    ('T8/2024 doanh thu bao nhiêu?', plan(period=period_spec('month', month=8, year=2024))),
    ('Số đơn huỷ tuần rồi?', plan('cancelled_orders', period=period_spec('previous_week'))),
    ('Tỷ lệ huỷ đơn tháng này là bao nhiêu %?', plan('cancellation_rate')),
    ('Trung bình mỗi đơn tháng này mang về bao nhiêu doanh thu?', plan('average_order_value')),
    ('Doanh thu từ ngày 02/08/2024 đến hết ngày 05/08/2024?',
     plan(period=period_spec('date_range', start_date='2024-08-02', end_date='2024-08-05'))),
    ('Doanh thu từ đầu năm đến hết hôm nay?', plan(period=period_spec('year_to_date'))),
])
def test_supported_literal_slots_agree(question, candidate):
    before = deepcopy(candidate)
    assert rejection_reason(question, candidate) is None
    assert candidate == before


@pytest.mark.parametrize('question', [
    'Lãi gộp tháng này là bao nhiêu?',
    'Tiền nhập hàng tháng này là bao nhiêu?',
    'Doanh thu hàng kê đơn tháng này là bao nhiêu?',
    'Tháng này nhân viên An bán bao nhiêu tiền?',
    'Ngày nào tháng này có doanh thu cao nhất?',
    'Doanh thu từng tháng là bao nhiêu?',
    'Doanh thu tháng này có tăng liên tục không?',
    'Tháng này có bao nhiêu ngày bán từ 500000 đồng trở lên?',
    'Tháng này tiền thu máy cũ là bao nhiêu?',
    'Doanh thu tháng này của chi nhánh bờ sông là bao nhiêu?',
    'Doanh thu tháng này của Nước ép ổi là bao nhiêu?',
    'Doanh thu nhóm đồ uống tháng này là bao nhiêu?',
    'Doanh thu tháng này qua ví điện tử là bao nhiêu?',
    'Doanh thu tháng này của khách Nam là bao nhiêu?',
    'Doanh thu theo nhóm khách hàng tháng này là bao nhiêu?',
    'Doanh thu mỗi đơn tháng này là bao nhiêu?',
])
def test_schema_valid_scalar_plan_cannot_erase_question_scope(question):
    assert rejection_reason(question, plan()) is not None


def test_customer_conditional_count_cannot_become_order_count():
    assert rejection_reason('Có mấy khách mua từ 8 đơn tháng này?', plan('order_count'))
    assert rejection_reason('Số đơn trả hàng tháng này?', plan('order_count'))


def test_wrong_time_and_unsupported_question_do_not_dispatch():
    class NeverExecute:
        def execute(self, candidate):
            raise AssertionError('rejected plan reached execution')
    candidate = plan(period=period_spec('previous_month'))
    attempt = inspect_generation(Generation(json.dumps(candidate)))
    result = execute_attempt(attempt, NeverExecute(), 'synthetic', question='Doanh thu hôm qua?')
    assert result['status'] == 'semantic_rejected'
    assert result['semantic_reason'] == 'period_not_entailed'
    assert result['plan'] == candidate and result['submission']['type'] == 'abstain'


def test_filters_must_cover_literal_mentions_and_must_not_be_invented():
    candidate = plan()
    candidate['filters']['product_mentions'] = ['Nước ép ổi']
    question = 'Doanh thu Nước ép ổi tháng này là bao nhiêu?'
    assert rejection_reason(question, candidate) is None
    assert rejection_reason('Doanh thu tháng này?', candidate) == 'filter_not_in_question'
    assert rejection_reason(question, plan()) == 'unverified_question_scope'
    # Substrings cannot be used to claim a different literal mention.
    candidate['filters']['product_mentions'] = ['ổi']
    assert rejection_reason(question, candidate) == 'unverified_question_scope'


def test_explicit_unit_and_shift_must_survive_in_plan():
    candidate = plan('quantity')
    candidate['filters']['unit_mention'] = 'ly'
    assert rejection_reason('Tháng này quán bán được mấy ly?', candidate) is None
    candidate['filters']['unit_mention'] = None
    assert rejection_reason('Tháng này quán bán được mấy ly?', candidate)
    candidate = plan('order_count')
    assert rejection_reason('Số đơn ca sáng tháng này?', candidate) is not None
    candidate['filters']['shift'] = 'sang'
    assert rejection_reason('Số đơn ca sáng tháng này?', candidate) is None


def test_top_requires_explicit_list_count_and_correct_rulebook_metric():
    candidate = plan('top_products')
    candidate['ranking'] = dict(k=4, metric='quantity')
    assert rejection_reason('Liệt kê 4 món bán chạy nhất tháng này?', candidate) is None
    candidate['ranking']['metric'] = 'revenue'
    assert rejection_reason('Liệt kê 4 món bán chạy nhất tháng này?', candidate) == 'ranking_metric_not_entailed'
    assert rejection_reason('Món nào doanh thu cao nhất tháng này?', candidate) == 'ranking_count_not_entailed'
    candidate = plan('top_customers')
    assert rejection_reason('Liệt kê 3 khách chi tiêu nhiều nhất tháng này?', candidate) is None
    candidate = plan('top_products')
    assert rejection_reason('Liệt kê 3 khách hàng chi tiêu nhiều nhất tháng này?', candidate)
    assert rejection_reason('Liệt kê 3 mặt hàng theo doanh thu tháng này?', candidate)


def test_growth_preserves_comparison_anchor_and_direction():
    candidate = plan('revenue_growth', period=period_spec('month', month=8, year=2024),
                     comparison_period=period_spec('previous_calendar_month'))
    question = 'Doanh thu tháng 8/2024 tăng bao nhiêu % so với tháng trước?'
    assert rejection_reason(question, candidate) is None
    candidate['comparison_period'] = period_spec('previous_month')
    assert rejection_reason(question, candidate) == 'comparison_not_entailed'
    candidate = plan('revenue_growth', period=period_spec('month', month=8, year=2024),
                     comparison_period=period_spec('month', month=7, year=2024))
    question = 'Doanh thu tháng 8/2024 tăng bao nhiêu % so với tháng 7/2024?'
    assert rejection_reason(question, candidate) is None
    candidate['period'], candidate['comparison_period'] = candidate['comparison_period'], candidate['period']
    assert rejection_reason(question, candidate) == 'period_not_entailed'


@pytest.mark.parametrize('answer', [
    {'id':'synthetic', 'type':'number', 'answer':0},
    {'id':'synthetic', 'type':'unanswerable', 'reason':'Synthetic evidence'},
])
def test_gate_does_not_recast_zero_or_proven_unanswerable(answer):
    class Answer:
        def to_submission(self, qid):
            return answer
    class Result:
        status, stage = 'original_status', 'dispatch'
    Result.answer = Answer()
    class Executor:
        def execute(self, received):
            return Result()
    result = execute_attempt(inspect_generation(Generation(json.dumps(plan()))),
                             Executor(), 'synthetic', question='Doanh thu tháng này?')
    assert result['submission'] == answer and result['status'] == 'original_status'
