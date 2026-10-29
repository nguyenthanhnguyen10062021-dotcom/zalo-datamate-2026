"""Conservative development grammar. Selection never receives gold, IDs or data."""
import re
import unicodedata

from queryplan import PlanValidationError, validate_plan
from queryplan.contract import FILTER_FIELDS, OPERATIONS, PERIOD_FIELDS


PERIOD_RE = re.compile('|'.join(f'(?P<{kind}>{pattern})' for kind, pattern in (
    ('date_range', r'tu ngay \d{4}-\d{2}-\d{2} den(?: het)? ngay \d{4}-\d{2}-\d{2}'),
    ('date', r'ngay \d{4}-\d{2}-\d{2}'),
    ('today', r'hom nay'), ('yesterday', r'hom qua'),
    ('this_week', r'tuan nay'), ('previous_week', r'tuan (?:truoc|roi)'),
    ('this_month', r'thang nay'), ('previous_month', r'thang (?:lien )?truoc(?: do)?'),
    ('previous_quarter', r'quy (?:lien )?truoc(?: do)?'),
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


def _fold_spans(text):
    """Keep original character spans even when folding changes string length."""
    folded, spans = [], []
    for index, character in enumerate(text):
        value = _fold(character)
        folded.append(value)
        spans.extend([(index, index + 1)] * len(value))
    return ''.join(folded), spans


def _quantity_unit_span(text):
    folded, spans = _fold_spans(text)
    matches = list(re.finditer(r'\bban\s+(?:duoc\s+)?bao\s+nhieu\s+(\w+)', folded))
    if len(matches) != 1:
        return None
    start, end = matches[0].span(1)
    left, right = spans[start][0], spans[end - 1][1]
    return text[left:right].casefold(), left, right


def _protect_unquoted_groups(text, mentions):
    """Only explicit group-kind labels ending at the share verb have a boundary."""
    folded, spans = _fold_spans(text)
    pattern = r'\bnhom\s+(?:hang|khach)\s+([^"\n]+?)\s+(?=(?:chiem|dong\s+gop)\b)'
    for match in reversed(list(re.finditer(pattern, folded))):
        label = match[1].strip()
        if (label in mentions or PERIOD_RE.search(label)
                or re.search(r'\b(?:va|hoac|nhom|kenh|thanh toan|ca sang|ca chieu)\b', label)):
            continue
        start, end = match.span(1)
        left, right = spans[start][0], spans[end - 1][1]
        token = f'x{len(mentions)}x'
        mentions[token] = text[left:right].strip()
        text = text[:left] + token + text[right:]
    return text


def _language_forms(text):
    # Fixed linguistic variants only. Entity and unit spans are already protected.
    for pattern, replacement in (
        (r'\b(?:dthu|doanhthu)\b', 'doanh thu'),
        (r'\bhqua\b', 'hom qua'), (r'\bthangs\b', 'thang'),
        (r'\bgaanf\b', 'gan'), (r'\bhangf\b', 'hang'),
        (r'\bth truoc\b', 'thang truoc'), (r'\bso vs\b', 'so voi'),
    ):
        text = re.sub(pattern, replacement, text)
    return text


def _clean(text):
    # These connectors only join a recognized time/filter to the metric phrase.
    text = re.sub(r'\b(?:(?:ca|toan bo)\s+)?cua hang\b', ' ', text)
    text = ' '.join(re.sub(r'\b(?:ty trong|ti trong|trong|vao|cua)\b',
                          lambda m: m[0] if m[0] in ('ty trong', 'ti trong') else ' ', text).split())
    text = re.sub(r'^(?:(?:cho toi biet|cho minh hoi|xem giup|coi gium|e)\s+)+', '', text)
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r'\s+(?:la gi|vay|ta|z|do|nha|nhe)$', '', text)
    return text


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
        ('revenue', r'(?:ban|thu) (?:duoc )?(?:tong cong )?bao nhieu (?:tien|dong|vnd)'),
        ('order_count', r'ban (?:duoc )?bao nhieu don(?: hang)?'),
        ('revenue_growth', r'doanh thu (?:tang|giam|tang hay giam|thay doi|tang truong)(?: bao nhieu)? (?:phan tram|%)'),
        ('revenue_share', r'(?:ty trong|ti trong|ty le) doanh thu(?: la bao nhieu| bao nhieu(?: phan tram)?)?'),
        ('revenue_share', r'doanh thu chiem bao nhieu phan tram'),
        ('revenue_share', r'(?:chiem|dong gop) bao nhieu (?:phan tram|%) doanh thu'),
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
    if match and match[1] not in ('tien', 'dong', 'vnd', 'don', 'khach'):
        return 'quantity', None, match[1]
    match = re.fullmatch(r'top (\d+) (mat hang|san pham|hang|mon|khach hang) '
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
    text = _protect_unquoted_groups(text, mentions)
    capture = _quantity_unit_span(text)
    unit_token, raw_unit = None, None
    if capture is not None:
        raw_unit, left, right = capture
        if raw_unit not in mentions and _fold(raw_unit) not in ('tien', 'dong', 'vnd', 'don', 'khach'):
            unit_token = f'x{len(mentions)}x'
            mentions[unit_token] = raw_unit
            text = text[:left] + unit_token + text[right:]
    text = _language_forms(' '.join(re.sub(r'[?!.,;:]', ' ', _fold(text)).split()))
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
        if comparison is None:
            return reject('unrecognized_comparison')
        metric_text = _clean(metric_text + ' ' + rest)
        if period['kind'] == 'this_month' and comparison['kind'] == 'previous_month':
            comparison['kind'] = 'previous_month_same_elapsed'
        elif period['kind'] == 'month' and comparison['kind'] == 'previous_month':
            comparison['kind'] = 'previous_calendar_month'
        elif period['kind'] == 'quarter' and comparison['kind'] == 'previous_quarter':
            comparison['kind'] = 'previous_calendar_quarter'
    operation, ranking, unit = _intent(_clean(metric_text))
    if operation is None:
        return reject('unrecognized_operation_or_scope')
    if unit is not None:
        if unit_token is None or unit != unit_token:
            return reject('ambiguous_unit_spelling')
        unit = raw_unit
    filters['unit_mention'] = unit
    plan = dict(version='1.0', status='supported', unsupported_reason=None,
                operation=operation, expected_type=OPERATIONS[operation], period=period,
                comparison_period=comparison, filters=filters, ranking=ranking)
    try:
        plan = validate_plan(plan)
    except PlanValidationError:
        return reject('invalid_plan_parameters')
    return dict(selection='selected', reason='matched_full_grammar', plan=plan)
