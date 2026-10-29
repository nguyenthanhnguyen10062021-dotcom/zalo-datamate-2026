"""Conservative development grammar. Selection never receives gold, IDs or data."""
import re
import unicodedata

from queryplan import PlanValidationError, validate_plan
from queryplan.contract import FILTER_FIELDS, OPERATIONS, PERIOD_FIELDS


PERIOD_RE = re.compile('|'.join(f'(?P<{kind}>{pattern})' for kind, pattern in (
    ('date_range', r'tu ngay \d{4}-\d{2}-\d{2} den(?: het)? ngay \d{4}-\d{2}-\d{2}'),
    ('date', r'ngay \d{4}-\d{2}-\d{2}'),
    ('today', r'hom nay'), ('yesterday', r'hom qua'),
    ('this_week', r'tuan nay'), ('previous_week', r'tuan truoc'),
    ('this_month', r'thang nay'), ('previous_month', r'thang truoc'),
    ('year_to_date', r'tu dau nam den nay'),
    ('last_days', r'\d+ ngay (?:gan nhat|qua)'),
    ('month', r'thang \d{1,2}(?:\s*(?:/|nam)\s*\d{4})?'),
    ('quarter', r'quy [1-4](?:\s*(?:/|nam)\s*\d{4})?'),
    ('tet', r'tet(?: nam)? \d{4}'),
)))
FILTER_RE = re.compile(r'\b(?:theo )?(nhom hang|nhom khach|kenh(?: ban)?|'
                       r'(?:hinh thuc )?thanh toan|mat hang|san pham) (x\d+x)\b')


def _fold(text):
    text = unicodedata.normalize('NFD', text.casefold().replace('đ', 'd'))
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn')


def _clean(text):
    # These connectors only join a recognized time/filter to the metric phrase.
    return ' '.join(re.sub(r'\b(?:ty trong|ti trong|trong|vao|cua)\b',
                          lambda m: m[0] if m[0] in ('ty trong', 'ti trong') else ' ', text).split())


def _period(text):
    matches = list(PERIOD_RE.finditer(text))
    if len(matches) != 1:
        return None, text
    match = matches[0]
    kind, value = match.lastgroup, match[0]
    spec = dict.fromkeys(PERIOD_FIELDS)
    spec['kind'] = kind
    numbers = list(map(int, re.findall(r'\d+', value)))
    if kind in ('month', 'quarter'):
        spec[kind] = numbers[0]
        spec['year'] = numbers[1] if len(numbers) > 1 else None
    elif kind == 'last_days':
        spec['n'] = numbers[0]
    elif kind == 'tet':
        spec['year'] = numbers[0]
    elif kind in ('date', 'date_range'):
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', value)
        spec.update(kind='date_range', start_date=dates[0], end_date=dates[-1])
    return spec, _clean(text[:match.start()] + ' ' + text[match.end():])


def _intent(text):
    patterns = (
        ('revenue_growth', r'doanh thu (?:tang|giam|thay doi|tang truong)(?: bao nhieu)? (?:phan tram|%)'),
        ('revenue_share', r'(?:ty trong|ti trong|ty le) doanh thu(?: la bao nhieu| bao nhieu(?: phan tram)?)?'),
        ('revenue_share', r'doanh thu chiem bao nhieu phan tram'),
        ('cancellation_rate', r'(?:ty le|ti le|phan tram) don(?: hang)? (?:bi )?huy(?: la bao nhieu(?: phan tram)?| bao nhieu(?: phan tram)?)?'),
        ('average_order_value', r'gia tri trung binh (?:mot|moi) don(?: hang)?(?: la bao nhieu)?'),
        ('cancelled_orders', r'(?:co )?bao nhieu don(?: hang)? (?:bi )?huy'),
        ('cancelled_orders', r'(?:tong )?so don(?: hang)? (?:bi )?huy(?: la bao nhieu)?'),
        ('order_count', r'(?:co )?bao nhieu don(?: hang)?'),
        ('order_count', r'(?:tong )?so don(?: hang)?(?: la bao nhieu| bao nhieu)?'),
        ('revenue', r'(?:tong )?doanh thu(?: la)?(?: bao nhieu(?: tien)?| duoc bao nhieu)?'),
    )
    for operation, pattern in patterns:
        if re.fullmatch(pattern, text):
            return operation, None, None
    match = re.fullmatch(r'ban (?:duoc )?bao nhieu ([\w]+)', text)
    if match:
        return 'quantity', None, match[1]
    match = re.fullmatch(r'top (\d+) (mat hang|san pham|mon|khach hang) '
                         r'(ban chay(?: nhat)?|theo doanh thu(?: cao nhat)?|mua nhieu tien nhat|theo so don)', text)
    if match:
        product = match[2] != 'khach hang'
        criterion = match[3]
        if criterion.startswith('ban chay') and not product or criterion == 'theo so don' and product:
            return None, None, None
        metric = 'quantity' if criterion.startswith('ban chay') else 'orders' if criterion == 'theo so don' else 'revenue'
        return 'top_products' if product else 'top_customers', dict(k=int(match[1]), metric=metric), None
    return None, None, None


def select_question(text: str) -> dict:
    """Consume the entire supported grammar; leave unknown scope unselected."""
    def reject(reason):
        return dict(selection='unparsed', reason=reason, plan=None)
    if not isinstance(text, str) or not text.strip():
        return reject('empty_question')
    text = unicodedata.normalize('NFC', text)
    if re.search(r'\bx\d+x\b', text):
        return reject('reserved_mention_token')
    mentions = {}
    def quoted(match):
        token = f'x{len(mentions)}x'
        mentions[token] = next(v for v in match.groups() if v is not None).strip()
        return token
    text = re.sub(r'["“]([^"“”]+)["”]|[\'‘]([^\'‘’]+)[\'’]', quoted, text)
    raw_words = re.findall(r'\w+', text)
    text = ' '.join(re.sub(r'[?!.,;:]', ' ', _fold(text)).split())
    parts = re.split(r'\bso voi\b', text)
    if len(parts) > 2:
        return reject('multiple_comparisons')
    text = parts[0]  # v1 has one filter scope; never lift filters from the comparison.
    filters = dict.fromkeys(FILTER_FIELDS)
    repeated = False
    def filter_match(match):
        nonlocal repeated
        label, token = match.groups()
        if token not in mentions:
            repeated = True
            return match[0]
        field = ('product_group_mention' if label == 'nhom hang' else
                 'customer_group_mention' if label == 'nhom khach' else
                 'channel_mention' if label.startswith('kenh') else
                 'payment_mention' if 'thanh toan' in label else 'product_mentions')
        if filters[field] is not None:
            repeated = True
        filters[field] = [mentions[token]] if field == 'product_mentions' else mentions[token]
        return ' '
    text = FILTER_RE.sub(filter_match, text)
    shifts = re.findall(r'\bca (sang|chieu)\b', text)
    if len(shifts) > 1 or repeated:
        return reject('multiple_filter_scopes')
    if shifts:
        filters['shift'] = shifts[0]
        text = re.sub(r'\bca (?:sang|chieu)\b', ' ', text)
    parts[0] = text
    period, metric_text = _period(parts[0])
    if period is None:
        return reject('missing_or_multiple_periods')
    comparison = None
    if len(parts) == 2:
        comparison, rest = _period(parts[1])
        if comparison is None or rest:
            return reject('unrecognized_comparison')
        if period['kind'] == 'this_month' and comparison['kind'] == 'previous_month':
            comparison['kind'] = 'previous_month_same_elapsed'
    operation, ranking, unit = _intent(_clean(metric_text))
    if operation is None:
        return reject('unrecognized_operation_or_scope')
    if unit is not None:
        spellings = {word.casefold() for word in raw_words if _fold(word) == unit}
        if len(spellings) != 1:
            return reject('ambiguous_unit_spelling')
        unit = spellings.pop()
    filters['unit_mention'] = unit
    plan = dict(version='1.0', status='supported', unsupported_reason=None,
                operation=operation, expected_type=OPERATIONS[operation], period=period,
                comparison_period=comparison, filters=filters, ranking=ranking)
    try:
        plan = validate_plan(plan)
    except PlanValidationError:
        return reject('invalid_plan_parameters')
    return dict(selection='selected', reason='matched_full_grammar', plan=plan)
