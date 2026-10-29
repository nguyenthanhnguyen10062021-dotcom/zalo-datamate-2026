"""Conservative question/plan agreement; no answer, ID, catalog or score input.

This is a selective safety gate, not a complete Vietnamese parser. A plan is
accepted only when its intent, literal slots and remaining vocabulary are
accounted for. Unknown wording abstains rather than silently dropping scope.
"""
import re
import unicodedata


GATE_VERSION = 'semantic-safety-1'


def _fold(text):
    text = unicodedata.normalize('NFD', text.casefold().replace('đ', 'd'))
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn')


def _words(text):
    return ' '.join(re.findall(r'\w+', _fold(text)))


def _contains(text, phrase):
    return f' {phrase} ' in f' {text} '


def _normalize(question):
    text = _fold(question)
    aliases = {
        'dthu': 'doanh thu', 'dt': 'doanh thu', 'revenue': 'doanh thu',
        'hqua': 'hom qua', 'hnay': 'hom nay', 'bua nay': 'hom nay',
        'bua qua': 'hom qua', 'trc': 'truoc', 'dc': 'duoc', 'vs': 'voi',
        'bn': 'bao nhieu', 'bnhiu': 'bao nhieu', 'bnhieu': 'bao nhieu',
        'nhiu': 'nhieu', 'ko': 'khong', 'hok': 'khong',
    }
    for source, target in aliases.items():
        text = re.sub(r'\b' + re.escape(source) + r'\b', target, text)
    text = re.sub(r'\bt\s*(\d{1,2})(?=\s*/)', r'thang \1', text)
    text = re.sub(r'\bth(?=\s*(?:\d|nay|truoc))', 'thang', text)
    return ' '.join(text.split())


def _period(kind, **values):
    return dict(kind=kind, n=None, month=None, quarter=None, year=None,
                start_date=None, end_date=None) | values


# Parse literal slots only. Calendar arithmetic/year inference remains in queryplan.
_PERIOD_PATTERNS = (
    ('date_range', r'tu\s+(?:ngay\s+)?(\d{1,2}/\d{1,2}/\d{4})\s+(?:den|toi)\s+(?:het\s+)?(?:ngay\s+)?(\d{1,2}/\d{1,2}/\d{4})'),
    ('date', r'\bngay\s+(\d{1,2}/\d{1,2}/\d{4})\b'),
    ('year_to_date', r'\btu\s+(?:dau nam|(?:ngay\s+)?1/1(?:\s+nam nay)?)\s*(?:(?:den|toi)\s*)?(?:het\s*)?(?:hom nay|nay)\b'),
    ('last_days', r'\b(\d+)\s+ngay\s+(?:gan nhat|qua)\b'),
    ('this_month', r'\b(?:tu\s+dau\s+)?thang nay(?:\s+(?:den|toi)\s+(?:het\s+)?hom nay)?\b'),
    ('previous_month', r'\bthang\s+(?:lien\s+)?(?:truoc|roi)(?:\s+do)?\b'),
    ('this_week', r'\btuan nay\b'),
    ('previous_week', r'\btuan\s+(?:truoc|roi)\b'),
    ('today', r'\bhom nay\b'),
    ('yesterday', r'\bhom qua\b'),
    ('month', r'\bthang\s+(\d{1,2})(?:\s*(?:/|nam)\s*(\d{4}))?\b'),
    ('quarter', r'\bquy\s+([1-4])(?:\s*(?:/|nam)\s*(\d{4}))?\b'),
    ('tet', r'\b(?:dip\s+|mua\s+)?tet(?:\s+nam)?\s+(\d{4})\b'),
)


def _iso(value):
    day, month, year = map(int, value.split('/'))
    return f'{year:04d}-{month:02d}-{day:02d}'


def _extract_periods(text):
    found = []
    for kind, pattern in _PERIOD_PATTERNS:
        for match in list(re.finditer(pattern, text)):
            values = match.groups()
            if kind in ('month', 'quarter'):
                spec = _period(kind, **{kind: int(values[0]),
                    'year': int(values[1]) if values[1] else None})
            elif kind == 'date_range':
                spec = _period(kind, start_date=_iso(values[0]), end_date=_iso(values[1]))
            elif kind == 'date':
                spec = _period('date_range', start_date=_iso(values[0]), end_date=_iso(values[0]))
            elif kind == 'last_days':
                spec = _period(kind, n=int(values[0]))
            elif kind == 'tet':
                spec = _period(kind, year=int(values[0]))
            else:
                spec = _period(kind)
            found.append((match.start(), spec))
        # Keep offsets stable while consuming spans, so ordering is textual.
        text = re.sub(pattern, lambda m: ' ' * len(m[0]), text)
    return [spec for _, spec in sorted(found)], text


_UNSUPPORTED = re.compile(
    r'\b(?:ton kho|ton cuoi|con ton|het hang|nhap hang|danh hang|tien nhap|gia nhap|'
    r'gia von|lai gop|lai rong|loi nhuan|hoa hong|tien cong|cong no|thu no|tra no|'
    r'no them|con no|con thieu|thu may cu|tra gop|bao hanh|ke don|hoat chat|han dung|'
    r'nhan vien|tho|chi phi|luot kham|cham cong|gia ban|doi gia|tang gia|tra hang|'
    r'khong ban|chua ban|ban cham|bi e|mon e|hang e|size)\b')
_MULTI = re.compile(
    r'\b(?:ngay nao|thang nao|quy nao|tuan nao|moi thang|tung thang|tung ngay|'
    r'theo (?:tung )?(?:thang|ngay)|(?:moi|tung) (?:mat hang|nhom|khach)|'
    r'lien tuc|lan luot|theo thu tu|'
    r'bao nhieu khach|may khach|nhieu khach|so khach|so ngay|may ngay|'
    r'bao nhieu ngay|may mat hang|bao nhieu mat hang)\b')

# Only connective/measurement words that add no new predicate are disposable.
# Entity words, numeric thresholds, negation and actor names are deliberately absent.
_FILLER = frozenset('''
a ah ak oi e em toi minh ban giup gium ho cho hoi xem check coi biet tinh dem
vay vayj nhi nha nhe ha hen ta do roi z voi va la thi co cua trong o vao
tu den toi het nay ca shop cua hang quan tiem tong cong tat
bao nhieu may duoc ban ra thu ve tien dong doanh thu so don hang
trung binh moi mot gia tri mang ve
bi da huy ti ty le phan tram tang giam thay doi hon kem so voi cung ky
chiem ti ty trong tren tong theo nhom kenh hinh thuc thanh toan tra bang
mat san pham mon loai hang chi tieu mua nhat cao nhieu tien
liet ke danh sach nhung nao top ban chay hot sang chieu ca
'''.split())


def _intent(text, plan):
    percent = '%' in text or re.search(r'\b(?:phan tram|ti le|ty le|ti trong|ty trong)\b', text)
    money = re.search(r'\b(?:doanh thu|tien ban|ban.*tien|thu ve.*tien)\b', text)
    orders = re.search(r'\bdon(?: hang)?\b', text)
    cancel = re.search(r'\bhuy\b', text)
    if cancel and orders:
        return 'cancellation_rate' if percent else 'cancelled_orders'
    if re.search(r'\btrung binh\b', text) and orders and money:
        return 'average_order_value'
    if plan['operation'].startswith('top_'):
        return plan['operation']  # The ranking witness is checked separately.
    if money and percent:
        if re.search(r'\b(?:chiem|ti trong|ty trong)\b', text):
            return 'revenue_share'
        if re.search(r'\b(?:tang|giam|thay doi|hon|kem)\b', text) and re.search(r'\bso\b', text):
            return 'revenue_growth'
        return None
    if orders and re.search(r'\b(?:so don|bao nhieu don|may don|nhieu don)\b', text):
        return 'order_count'
    if money:
        return 'revenue'
    if (plan['filters']['unit_mention'] is not None
            and re.search(r'\b(?:ban|so luong|so|bao nhieu|may)\b', text)):
        return 'quantity'
    return None


def rejection_reason(question: str, plan: dict) -> str | None:
    """Return a stable reason for abstention, never repair or calculate a plan.

    Caller must first parse/validate/check capability. Unsupported plans already
    abstain at the executor and are left alone. Vocabulary coverage is intentional:
    passing these checks is evidence of agreement, not a confidence probability.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError('Semantic verification requires a nonempty question')
    if plan['status'] != 'supported':
        return None
    text = _normalize(question)
    words = _words(text)
    if _UNSUPPORTED.search(words):
        return 'unsupported_question_semantics'
    if _MULTI.search(words):
        return 'unsupported_answer_shape'
    operation = plan['operation']
    if _intent(words + (' %' if '%' in text else ''), plan) != operation:
        return 'operation_not_entailed'
    shifts = re.findall(r'\bca (sang|chieu)\b', words)
    if shifts and (len(set(shifts)) != 1 or plan['filters']['shift'] != shifts[0]):
        return 'shift_not_entailed'
    if operation != 'average_order_value' and re.search(r'\b(?:moi|tung) don\b', words):
        return 'unsupported_answer_shape'

    # Mentions must actually occur in the input; do not silently substitute a
    # canonical label or erase a predicate invented by the model.
    remaining = text
    for field, value in plan['filters'].items():
        if value is None:
            continue
        for mention in value if isinstance(value, list) else [value]:
            phrase = _words(mention)
            if not _contains(_words(remaining), phrase):
                return 'filter_not_in_question'
            pattern = r'(?<!\w)' + r'\W+'.join(map(re.escape, phrase.split())) + r'(?!\w)'
            remaining = re.sub(pattern, ' ', remaining)

    if operation.startswith('top_'):
        noun = r'(?:khach(?: hang)?)' if operation == 'top_customers' else r'(?:mat hang|san pham|mon|hang)'
        match = re.search(r'\b(?:top\s+)?(\d+)\s+' + noun + r'\b', remaining)
        if match is None:
            match = re.search(r'\btop\s+(\d+)\b', remaining)
        if match is None or int(match[1]) != plan['ranking']['k']:
            return 'ranking_count_not_entailed'
        if operation == 'top_products' and re.search(r'\bkhach\b', _words(remaining)):
            return 'ranking_entity_not_entailed'
        if not re.search(r'\b(?:top|nhat)\b', words):
            return 'ranking_metric_not_entailed'
        if re.search(r'\b(?:ban chay|ban (?:duoc )?nhieu nhat|hot nhat)\b', words):
            metric = 'quantity' if operation == 'top_products' else None
        elif re.search(r'\b(?:doanh thu|chi tieu|tien mua|mua.*tien)\b', words):
            metric = 'revenue'
        elif operation == 'top_customers' and re.search(r'\b(?:so don|nhieu don)\b', words):
            metric = 'orders'
        else:
            metric = None
        if metric != plan['ranking']['metric']:
            return 'ranking_metric_not_entailed'
        # A list must describe the right objects, not employees/days/groups.
        if not re.search(r'\b' + noun + r'\b', words):
            return 'ranking_entity_not_entailed'
        remaining = remaining[:match.start()] + ' ' + remaining[match.end():]
    elif re.search(r'\b(?:ai|nao|nhat|liet ke|danh sach)\b',
                   re.sub(r'\bgan nhat\b', '', words)):
        return 'unsupported_answer_shape'

    periods, remaining = _extract_periods(remaining)
    if operation == 'revenue_growth':
        main = plan['period']
        comparison = plan['comparison_period']
        if len(periods) != 2:
            return 'period_not_verified'
        # Questions can mention comparison first. Match by explicit slots, then
        # check the comparison relative to the primary, without computing dates.
        if periods[0]['kind'] == 'previous_month':
            expected_main, other = periods[1], periods[0]
        else:
            expected_main, other = periods[0], periods[1]
        if main != expected_main:
            return 'period_not_entailed'
        if other['kind'] == 'previous_month':
            if main['kind'] == 'this_month':
                if comparison not in (None, _period('previous_month_same_elapsed')):
                    return 'comparison_not_entailed'
            elif main['kind'] == 'month':
                if comparison != _period('previous_calendar_month'):
                    return 'comparison_not_entailed'
            else:
                return 'comparison_not_verified'
        elif comparison != other:
            return 'comparison_not_entailed'
    elif periods != [plan['period']]:
        return 'period_not_entailed'

    remaining_words = _words(remaining)
    if (re.search(r'\bnhom\b', remaining_words)
            and plan['filters']['product_group_mention'] is None
            and plan['filters']['customer_group_mention'] is None):
        return 'missing_group_filter'
    if re.search(r'\bkenh\b', remaining_words) and plan['filters']['channel_mention'] is None:
        return 'missing_channel_filter'
    if (re.search(r'\b(?:thanh toan|tra bang)\b', remaining_words)
            and plan['filters']['payment_mention'] is None):
        return 'missing_payment_filter'
    filler = _FILLER
    if operation == 'top_customers' or plan['filters']['customer_group_mention'] is not None:
        filler = filler | {'khach'}
    residue = set(remaining_words.split()) - filler
    if residue:
        return 'unverified_question_scope'
    return None
