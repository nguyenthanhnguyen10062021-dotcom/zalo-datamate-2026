"""Synthetic contrasts for metric intent and lossless unit captures."""
import unicodedata

import pytest

from verification.selection import select_question


@pytest.mark.parametrize('text,operation,unit,shift', [
    ('Tháng 9/2024 ca sáng bán được bao nhiêu tiền?', 'revenue', None, 'sang'),
    ('Tháng này thu được bao nhiêu tiền?', 'revenue', None, None),
    ('Bán được bao nhiêu đồng tháng này?', 'revenue', None, None),
    ('Bán được bao nhiêu đơn tháng này?', 'order_count', None, None),
    ('Tháng này bán được bao nhiêu đơn hàng?', 'order_count', None, None),
    ('Bán được bao nhiêu phần trong tháng 9/2024?', 'quantity', 'phần', None),
    ('Ca sáng tháng 9/2024 bán được bao nhiêu cá?', 'quantity', 'cá', 'sang'),
    ('Ca chiều tháng này bán được bao nhiêu ca?', 'quantity', 'ca', 'chieu'),
    ('Bán được bao nhiêu tạ tháng này?', 'quantity', 'tạ', None),
    ('Tháng này mặt hàng "Hợp tác" bán được bao nhiêu hộp?', 'quantity', 'hộp', None),
])
def test_intent_and_unit_span(text, operation, unit, shift):
    raw = unicodedata.normalize('NFD', text)
    actual = select_question(raw)
    assert actual['selection'] == 'selected'
    assert actual['plan']['operation'] == operation
    assert actual['plan']['filters']['unit_mention'] == unit
    assert actual['plan']['filters']['shift'] == shift


@pytest.mark.parametrize('text', [
    'Tháng này bán được bao nhiêu khách?',
    'Tháng này bán được bao nhiêu phần trăm?',
    'Bán được bao nhiêu tiền tháng này trừ tiền ship?',
    'Bán được bao nhiêu ly tháng này riêng khách mới?',
    'Bán được bao nhiêu đơn tháng này và tháng trước?',
    'Bán được bao nhiêu ly kênh "A" tháng này so với tháng trước kênh "B"?',
])
def test_intent_fix_does_not_swallow_unsupported_scope(text):
    assert select_question(text)['selection'] == 'unparsed'
