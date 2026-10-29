"""Bounded language-family expansions with near-negative scope contrasts."""
import pytest

from verification.selection import select_question


@pytest.mark.parametrize('text,operation,kind', [
    ('Cho tôi biết dthu hqua', 'revenue', 'yesterday'),
    ('30 ngày gaanf nhất cửa hangf bán được bao nhiêu tiền?', 'revenue', 'last_days'),
    ('Tuần rồi top 4 hàng bán chạy nhất là gì?', 'top_products', 'previous_week'),
    ('Quý 2 năm 2024 cửa hàng bán được tổng cộng bao nhiêu tiền?', 'revenue', 'quarter'),
    ('Xem giúp tổng doanh thu 7 ngày gần nhất là bao nhiêu vậy?', 'revenue', 'last_days'),
    ('Doanh thu tháng 1/2024 thay đổi bao nhiêu % so với tháng liền trước?', 'revenue_growth', 'month'),
    ('Doanh thu tháng 12 tăng bao nhiêu phần trăm so với tháng trước?', 'revenue_growth', 'month'),
    ('Doanh thu quý 1/2024 tăng bao nhiêu phần trăm so với quý trước?', 'revenue_growth', 'quarter'),
    ('Doanh thu tháng 8/2026 so với tháng 8/2025 tăng hay giảm bao nhiêu %?', 'revenue_growth', 'month'),
    ('Trong tháng 6/2024, top 3 khách hàng mua nhiều tiền nhất là gì?', 'top_customers', 'month'),
    ('Trong tháng 6/2024, nhóm hàng Đồ uống đóng góp bao nhiêu phần trăm doanh thu cả cửa hàng?', 'revenue_share', 'month'),
    ('Trong tháng 6/2024, nhóm khách VIP chiếm bao nhiêu % doanh thu cả cửa hàng?', 'revenue_share', 'month'),
])
def test_clear_audited_language_families(text, operation, kind):
    result = select_question(text)
    assert result['selection'] == 'selected'
    assert result['plan']['operation'] == operation
    assert result['plan']['period']['kind'] == kind


def test_relative_comparison_anchor_and_explicit_pair():
    historical = select_question('Doanh thu tháng 1/2024 tăng bao nhiêu phần trăm so với tháng trước?')['plan']
    assert historical['comparison_period']['kind'] == 'previous_calendar_month'
    implicit = select_question('Doanh thu quý 1 tăng bao nhiêu phần trăm so với quý liền trước?')['plan']
    assert implicit['period']['year'] is None
    assert implicit['comparison_period']['kind'] == 'previous_calendar_quarter'
    explicit = select_question('Doanh thu tháng 8/2026 so với tháng 8/2025 tăng hay giảm bao nhiêu %?')['plan']
    assert explicit['comparison_period']['kind'] == 'month'
    assert explicit['comparison_period']['year'] == 2025


def test_unquoted_group_is_bounded_and_preserves_raw_label():
    result = select_question('Nhóm hàng Đồ uống đóng góp bao nhiêu % doanh thu tháng 9/2024?')
    assert result['plan']['filters']['product_group_mention'] == 'Đồ uống'
    assert result['plan']['filters']['customer_group_mention'] is None


@pytest.mark.parametrize('text', [
    'Nhóm A đóng góp bao nhiêu % doanh thu tháng 9/2024?',  # Ambiguous group kind.
    'Nhóm hàng A và nhóm hàng B đóng góp bao nhiêu % doanh thu tháng 9/2024?',
    'Nhóm hàng A chiếm bao nhiêu % doanh thu tháng 9/2024 riêng khách mới?',
    'Doanh thu ca chiều tuần trước chênh ca sáng bao nhiêu %?',
    'Doanh thu tháng 9/2024 so với tháng 8/2024 kênh "B" tăng bao nhiêu %?',
    'Trong tháng 9/2024 khách nào mua nhiều đơn nhất?',
    'Top 4 mặt hàng theo lãi gộp tháng này?',
    'Xem giúp tổng doanh thu bình quân 7 ngày gần nhất là bao nhiêu vậy?',
    'Cho tôi biết dthu hqua nhưng chỉ các đơn chưa trả tiền',
    'Doanh thu quý trước tăng bao nhiêu % so với quý trước nữa?',
])
def test_language_expansion_rejects_unrepresented_scope(text):
    result = select_question(text)
    assert result['selection'] == 'unparsed'
    assert result['plan'] is None
