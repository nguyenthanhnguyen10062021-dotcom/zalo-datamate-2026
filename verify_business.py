#!/usr/bin/env python3
"""Regression on the legacy checker's selected train questions, not full PA.

Gold data is read ONLY here, never by business/. Selection intentionally retains
the legacy checker's restrictions so the before/after denominators are visible.
"""
import argparse
import importlib.util
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re

import pandas as pd

import check_with_gold as legacy
from business import DataError, DateRange, Filters, Periods, Rulebook, SalesMetrics, UnsupportedRule


def quantity_request(tables, rest):
    """Resolve the same conservative unit/product subset as the old checker."""
    match = legacy.QTY_RE.search(rest)
    unit = match[2]
    products = tables['mat_hang']
    units = [u for u in products['don_vi_co_ban'].dropna().unique() if legacy.norm_question(u).split()[:1]==[unit]]
    if not units:
        return None
    names = {}
    for code,name in zip(products['ma_hang'],products['ten_hang']):
        if isinstance(name,str) and name.strip():
            names.setdefault(legacy.norm_question(name),set()).add(code)
    text = f' {rest} '
    found = [name for name in names if name and f' {name} ' in text]
    item = max(found,key=len) if found else None
    left = text.replace(f' {item} ',' ') if item else text
    left = left.replace(match[0],' ')
    if not all(word in legacy.QTY_FILLER for word in left.split()):
        return None
    return units[0], Filters(product_ids=tuple(sorted(names[item])) if item else None)


def verify(train_dir=Path('train'), cache_dir=Path('cache')):
    train_dir,cache_dir = Path(train_dir),Path(cache_dir)
    rules = Rulebook.from_path(train_dir/'rulebook.md')
    questions = legacy.gold_questions(train_dir)
    total = len([line for line in (train_dir/'questions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()])
    rows,skipped,errors,tables_by_shop,engines = [],[],[],{},{}
    for q in questions:
        bid = q['business_id']
        try:
            if bid not in tables_by_shop:
                cache=cache_dir/bid
                # The five checked operations only need these narrow columns.
                # Avoid retaining full customer/order metadata for every shop.
                tables_by_shop[bid]=legacy.load_cached(cache)
            tables=tables_by_shop[bid]
            old=legacy.compute(tables,q['loai'],q['thang'],q['nam'],q.get('rest',''))
            if old==legacy.BO_QUA:
                skipped.append({'id':q['id'],'reason':'legacy bo_qua'})
                continue
            if bid not in engines:
                engines[bid]=SalesMetrics(tables,rules,q['as_of_date'])
            engine=engines[bid]
            # This verifier is sequential; reuse validated tables/date indexes,
            # while setting each question's reference date explicitly.
            engine.as_of=date.fromisoformat(q['as_of_date'])
            period=Periods(rules,q['as_of_date']).month(q['thang'],q['nam'])
            if q['loai']=='doanh_thu':
                answer=engine.revenue(period)
            elif q['loai']=='so_don_huy':
                answer=engine.cancelled_orders(period)
            elif q['loai'].startswith('doanh_thu_ca_'):
                answer=engine.revenue(period,Filters(shift=q['loai'].rsplit('_',1)[1]))
            elif q['loai']=='so_luong':
                request=quantity_request(tables,q['rest'])
                if request is None:
                    raise DataError('Verifier cannot resolve legacy quantity request')
                unit,filters=request
                answer=engine.quantity(period,filters,unit=unit)
            else:
                raise ValueError(f'Unsupported verification kind: {q["loai"]}')
            wanted=q['gold_type']
            matched=answer.type==wanted and (wanted=='unanswerable' or abs(answer.answer-q['gold'])<=1e-6)
            rows.append({'id':q['id'],'business_id':bid,'kind':q['loai'],'legacy':old,
                         'gold_type':wanted,'gold':q['gold'],'library':answer.to_submission(q['id']),
                         'matched_gold':matched,'matched_legacy':(old=='unanswerable' if answer.type=='unanswerable' else old==answer.answer)})
        except (DataError,UnsupportedRule,ValueError,KeyError,OSError) as exc:
            errors.append({'id':q['id'],'business_id':bid,'error':f'{type(exc).__name__}: {exc}'})
    return {'total_train':total,'selected':len(questions),'outside_selection':total-len(questions),
            'legacy_skipped':len(skipped),'compared':len(rows),'matched_gold':sum(r['matched_gold'] for r in rows),
            'matched_legacy':sum(r['matched_legacy'] for r in rows),'errors':errors,
            'by_kind':dict(Counter(r['kind'] for r in rows)),'skipped':skipped,'rows':rows,
            'rulebook_source':rules.source,'rulebook_sha256':rules.fingerprint}


# ---- Mở rộng: bộ chọn câu bảo thủ cho các API mới --------------------------------------------------
# CHỈ dùng trong verifier để ĐO độ phủ/độ khớp trên train; không phải tầng hiểu câu hỏi lúc thi.

def _load_scorer():
    path = Path(__file__).resolve().parent/'evaluate'/'evaluate.py'
    spec = importlib.util.spec_from_file_location('datamate_evaluate', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCORER = _load_scorer()

EXT_KINDS = {
    'C1': 'ngày/tháng doanh thu cao nhất', 'C2': 'doanh thu một mặt hàng', 'C3': 'giá bán mặt hàng ngày D',
    'C4': 'doanh thu nhiều tháng / tăng liên tục', 'C5': 'số ly size M/L', 'C6': 'số mặt hàng ế',
    'C7': 'lãi gộp', 'C8': 'đếm khách / mặt hàng theo số đơn', 'C9': 'nhân viên',
}
MONTH_TOKEN = re.compile(r'(?<![\d/])(\d{1,2})/(\d{4})\b')
DATE_TOKEN = re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b')
RANGE_RE = re.compile(r'\btu (\d{1,2})/(\d{1,2})/(\d{4}) den het (\d{1,2})/(\d{1,2})/(\d{4})\b')
LAST_DAYS = re.compile(r'\b(\d+) ngay gan nhat\b')
OTHER_PERIOD = re.compile(r'\b(tuan|hom nay|hnay|hom qua|hqua|bua|quy|nam nay|tu dau|ngay gan nhat)\b')
COUNT_WORDS = {'hai': 2, 'ba': 3, 'bon': 4, 'nam': 5, 'sau': 6}
ORDERS_BOUND = re.compile(r'(\btu|\bo|\bit nhat|≥|>=|\bqua|\bhon|\btren|\bduoi) ?(\d+) don(?: hang)?(?: khac nhau)?( tro len)?')
C2_WORDS = legacy.FILLER | set('mat hang mon san pham tien ve dc duoc ra ban bn bnhiu nhiu total tong cong thu la'.split())


class _Ctx:
    """Thông tin một tiệm cho bộ chọn: danh mục tên hàng (chuẩn hoá) và đơn vị cơ bản."""

    def __init__(self, tables):
        products = tables['mat_hang']
        self.names = {}
        for code, name in zip(products['ma_hang'], products['ten_hang']):
            if isinstance(name, str) and name.strip():
                self.names.setdefault(legacy.norm_question(name), set()).add(code)
        self.base = {c: u for c, u in zip(products['ma_hang'], products['don_vi_co_ban']) if isinstance(u, str)}
        self.periods = None

    def product(self, t):
        """Tên hàng dài nhất xuất hiện nguyên cụm trong câu; có hai hàng khác nhau -> bỏ (không đoán)."""
        text = f' {t} '
        found = [n for n in self.names if n and f' {n} ' in text]
        if not found:
            return None
        best = max(found, key=len)
        if any(n not in best for n in found):
            return None
        return best, tuple(sorted(self.names[best]))


def _one_month(t, periods):
    if OTHER_PERIOD.search(t) or DATE_TOKEN.search(t):
        return None
    months = legacy.MONTH_RE.findall(t)
    if len(months) == 1 and len(MONTH_TOKEN.findall(t)) <= 1 and 'thang nay' not in t:
        return periods.month(int(months[0][0]), int(months[0][1]))
    if not months and not MONTH_TOKEN.search(t) and re.search(r'\bthang nay\b', t):
        return periods.this_month()
    return None


def _month_seq(t):
    """Danh sách tháng (m, y) theo thứ tự câu hỏi nêu, hoặc khoảng 'từ tháng a đến tháng b', 'N tháng kết thúc ở'."""
    tokens = [(int(m), int(y)) for m, y in MONTH_TOKEN.findall(t)]
    end = re.search(r'\b(\d+|hai|ba|bon|nam|sau) thang lien (?:nhau|tiep) ket thuc o thang (\d{1,2})/(\d{4})', t)
    if end:
        n = int(end[1]) if end[1].isdigit() else COUNT_WORDS[end[1]]
        m, y = int(end[2]), int(end[3])
        seq = []
        for _ in range(n):
            seq.insert(0, (m, y))
            m, y = (m - 1, y) if m > 1 else (12, y - 1)
        return seq
    if len(tokens) == 2 and re.search(r'\btu thang \d{1,2}/\d{4} (?:den|toi|qua) thang \d{1,2}/\d{4}', t) \
            and not re.search(r'\b(roi|r)\b', t):
        (m, y), seq = tokens[0], []
        while (y, m) <= (tokens[1][1], tokens[1][0]) and len(seq) < 24:
            seq.append((m, y))
            m, y = (m + 1, y) if m < 12 else (1, y + 1)
        return seq
    return tokens if len(tokens) >= 2 else []


def _contiguous(seq):
    return all((m2, y2) == ((m1 % 12) + 1, y1 + (m1 == 12)) for (m1, y1), (m2, y2) in zip(seq, seq[1:]))


def sel_c1(t, ctx):
    if not re.search(r'\b(ngay|thang) nao\b', t) or not re.search(r'doanh thu|dthu|revenue|nhieu tien|nhiu tien|ban dat', t):
        return None
    if re.search(r'han dung|het han|\blo\b|\bdon\b|khach|mat hang|nhom|\bca (sang|chieu)\b|nhan vien', t):
        return None
    kind = 'max' if re.search(r'cao nhat|lon nhat|nhieu tien nhat|nhiu tien nhat|dat nhat', t) else \
        'min' if re.search(r'thap nhat|it tien nhat|it nhat', t) else None
    if kind is None:
        return None
    if re.search(r'\bngay nao\b', t):
        period = _one_month(t, ctx.periods)
        return period and (lambda e: e.best_period(period, 'day', kind=kind))
    seq = _month_seq(t)
    if len(seq) < 2 or not _contiguous(seq):
        return None
    period = DateRange(ctx.periods.month(*seq[0]).start, ctx.periods.month(*seq[-1]).end)
    return lambda e: e.best_period(period, 'month', kind=kind)


def sel_c2(t, ctx):
    found = ctx.product(t)
    if found is None or 'tien' not in t.split():
        return None
    period = _one_month(t, ctx.periods)
    rest = legacy.MONTH_RE.sub(' ', f' {t} '.replace(f' {found[0]} ', ' ')).replace('thang nay', ' ')
    if period is None or not all(w in C2_WORDS for w in rest.split()):
        return None
    return lambda e: e.revenue(period, Filters(product_ids=found[1]))


def sel_c3(t, ctx):
    if not re.search(r'\b(gia ban|don gia)\b', t) or re.search(r'tang gia|doi gia|nhap|binh quan|trung binh|gia von', t):
        return None
    dates, found = DATE_TOKEN.findall(t), ctx.product(t)
    if len(dates) != 1 or found is None or len(found[1]) != 1:
        return None
    unit = re.search(r'\bmot (\w+)', f' {t} '.replace(f' {found[0]} ', ' '))
    base = ctx.base.get(found[1][0])
    if not unit or not base or legacy.norm_question(base) != unit[1]:
        return None
    d, m, y = map(int, dates[0])
    return lambda e: e.price_on_date(found[1][0], date(y, m, d))


def sel_c4(t, ctx):
    if not re.search(r'\b(doanh thu|dthu|revenue)\b', t) or re.search(r'thang nao|nhom|khach|mat hang|size|\bca (sang|chieu)\b', t):
        return None
    seq = _month_seq(t)
    if len(seq) < 2:
        return None
    periods = [ctx.periods.month(m, y) for m, y in seq]
    if re.search(r'tang lien tuc', t):
        return lambda e: e.is_monotonic(periods, 'increasing')
    if re.search(r'giam lien tuc', t):
        return lambda e: e.is_monotonic(periods, 'decreasing')
    if re.search(r'moi thang|tung thang|lan luot|theo thu tu thoi gian', t):
        return lambda e: e.revenue_series(periods)
    return None


def sel_c5(t, ctx):
    size = re.search(r'\bly size (m|l)\b', t)
    if not size or re.search(r'nhom|khach|\bca (sang|chieu)\b|tien|doanh thu|dthu', t) or ctx.product(t):
        return None
    period = _one_month(t, ctx.periods)
    return period and (lambda e: e.quantity(period, Filters(size=size[1].upper()), unit='ly'))


def sel_c6(t, ctx):
    if not re.search(r'\bmat hang (bi )?e\b|\bmat hang ban cham\b|\bmat hang khong ban (duoc|dc)\b', t) \
            or re.search(r'liet ke|nhung mat hang|mat hang nao|van dang ban', t):
        return None
    if not re.search(r'\b(may|bao nhieu|bnhiu|bn|dem|so)\b', t):
        return None
    r = RANGE_RE.search(t)
    if r:
        d1, m1, y1, d2, m2, y2 = map(int, r.groups())
        period = DateRange(date(y1, m1, d1), date(y2, m2, d2))
    elif LAST_DAYS.search(t):
        period = ctx.periods.last_days(int(LAST_DAYS.search(t)[1]))
    else:
        return None
    return lambda e: e.slow_moving_products(period)


def sel_c7(t, ctx):
    if re.search(r'nhom|khach|nhan vien|ke don', t):
        return None
    period = _one_month(t, ctx.periods)
    if period is None:
        return None
    if re.search(r'\b(hang|mat hang) nao\b', t) and re.search(r'loi nhat|lai gop.*cao nhat', t):
        return lambda e: e.top_products(period, k=1, metric='gross_profit').single()
    if re.search(r'\blai gop\b', t) and not re.search(r'\bnao\b', t) and ctx.product(t) is None:
        return lambda e: e.gross_profit(period)
    return None


def _bounds(match):
    word, n, more = match[1], int(match[2]), bool(match[3])
    if word in ('it nhat', '≥', '>=') or (word in ('tu', 'o') and more):
        return n, None
    if word in ('qua', 'hon', 'tren'):
        return n + 1, None
    if word == 'duoi':
        return None, n - 1
    return None


def sel_c8(t, ctx):
    if re.search(r'\bno\b|tra no|cong no|thieu|nhom', t):
        return None
    match = ORDERS_BOUND.search(t)
    bounds = match and _bounds(match)
    period = _one_month(t, ctx.periods)
    if not bounds or period is None:
        return None
    low, high = bounds
    percent = re.search(r'%|phan tram|ti le', t)
    if re.search(r'\bkhach\b', t) and not re.search(r'mat hang', t):
        if percent:
            return lambda e: e.customer_share(period, low, high)
        if re.search(r'\b(bao nhieu|may|so|bn|bnhiu|nhieu|dem)\b', t):
            return lambda e: e.customer_count(period, low, high)
    if re.search(r'\bmat hang\b', t) and re.search(r'xuat hien|co mat|duoc mua', t) and high is None and not percent:
        return lambda e: e.products_in_at_least(period, low)
    return None


def sel_c9(t, ctx):
    if 'nhan vien' not in t:
        return None
    period = _one_month(t, ctx.periods)
    if period is None:
        return None
    code = re.search(r'\bnhan vien ma (nv) ?(\d+)\b', t)
    if code and re.search(r'ban duoc|ban dc|tien|doanh thu|dthu', t) and not re.search(r'\bnao\b|so don|khach', t):
        staff = f'NV{code[2]}'
        return lambda e: e.revenue(period, Filters(staff=staff))
    if re.search(r'ban gioi nhat|nhan vien nao co (doanh thu|dthu) cao nhat', t):
        return lambda e: e.top_staff(period, k=1).single()
    return None


SELECTORS = [('C1', sel_c1), ('C4', sel_c4), ('C3', sel_c3), ('C5', sel_c5), ('C6', sel_c6), ('C7', sel_c7),
             ('C8', sel_c8), ('C9', sel_c9), ('C2', sel_c2)]


def _full_tables(cache):
    tables = {name: pd.read_parquet(cache/f'{name}.parquet') for name in ('don_hang', 'dong_hang', 'mat_hang')}
    tables['cua_hang'] = json.loads((cache/'cua_hang.json').read_text(encoding='utf-8'))
    return tables


def _gold_value(gold):
    return gold.get('answer') if gold['type'] != 'unanswerable' else None


def verify_extended(train_dir=Path('train'), cache_dir=Path('cache'), exclude=()):
    """Chạy bộ chọn mở rộng trên mọi câu train (trừ câu bộ cũ đã chọn), gọi API, chấm bằng evaluate.score_one."""
    train_dir, cache_dir = Path(train_dir), Path(cache_dir)
    rules = Rulebook.from_path(train_dir/'rulebook.md')
    calendar = train_dir/'calendar.csv'
    questions = [json.loads(l) for l in (train_dir/'questions.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    golds = {g['id']: g for g in (json.loads(l) for l in (train_dir/'answers.jsonl').read_text(encoding='utf-8').splitlines() if l.strip())}
    kinds = {k: {'name': EXT_KINDS[k], 'selected': 0, 'matched': 0, 'mismatched': 0, 'errors': Counter(),
                 'mismatch_examples': [], 'error_examples': []} for k in EXT_KINDS}
    shops, rows = {}, []
    exclude = set(exclude)
    for q in questions:
        if q['id'] in exclude:
            continue
        bid = q['business_id']
        cache = cache_dir/bid
        if not (cache/'cua_hang.json').exists():
            continue
        if bid not in shops:
            tables = _full_tables(cache)
            try:
                shops[bid] = (SalesMetrics(tables, rules, q['as_of_date']), _Ctx(tables))
            except DataError as exc:
                shops[bid] = (exc, _Ctx(tables))
        engine, ctx = shops[bid]
        ctx.periods = Periods(rules, q['as_of_date'], calendar)
        t = legacy.norm_question(q['question'])
        for kind, selector in SELECTORS:
            try:
                call = selector(t, ctx)
            except (ValueError, UnsupportedRule):
                call = None
            if call:
                break
        else:
            continue
        stat, gold = kinds[kind], golds[q['id']]
        stat['selected'] += 1
        row = {'id': q['id'], 'business_id': bid, 'kind': kind, 'question': q['question'],
               'gold_type': gold['type'], 'gold': _gold_value(gold)}
        try:
            if isinstance(engine, Exception):
                raise engine
            engine.as_of = date.fromisoformat(q['as_of_date'])
            answer = call(engine)
            row['library'] = answer.to_submission(q['id'])
            status, reason = SCORER.score_one(gold, row['library'])
            if status == SCORER.CORRECT:
                stat['matched'] += 1
                row['status'] = 'khop'
            elif answer.type == 'unanswerable':
                stat['errors']['unanswerable'] += 1
                row['status'], row['reason'] = 'loi', answer.reason
            else:
                stat['mismatched'] += 1
                row['status'], row['reason'] = 'lech', reason
        except (DataError, UnsupportedRule, ValueError, KeyError) as exc:
            stat['errors'][type(exc).__name__] += 1
            row['status'], row['reason'] = 'loi', f'{type(exc).__name__}: {exc}'
        rows.append(row)
        bucket = 'mismatch_examples' if row['status'] == 'lech' else 'error_examples' if row['status'] == 'loi' else None
        if bucket and len(stat[bucket]) < 5:
            stat[bucket].append({k: row.get(k) for k in ('id', 'business_id', 'question', 'gold_type', 'gold', 'library', 'reason')})
    for stat in kinds.values():
        stat['errors'] = dict(stat['errors'])
    return {'by_kind': kinds, 'rows': rows, 'public_only_with_train_rulebook': _public_only_check(shops, rules)}


def _public_only_check(shops, rules):
    """Các luật chỉ có ở rulebook public phải ra UnsupportedRule khi chạy với rulebook train."""
    engine = next((e for e, _ in shops.values() if not isinstance(e, Exception)), None)
    if engine is None:
        return {}
    period = DateRange(engine.meta['ngay_bat_dau_du_lieu'], engine.meta['ngay_bat_dau_du_lieu'])
    calls = {'loyal_customers': lambda: engine.loyal_customers(period),
             'big_spender_customers': lambda: engine.big_spender_customers(period),
             'fickle_customers': lambda: engine.fickle_customers(period),
             'favorite_products': lambda: engine.favorite_products(period),
             'hardworking_staff': lambda: engine.hardworking_staff(period),
             'busiest_day': lambda: engine.busiest_day(period), 'peak_hour': lambda: engine.peak_hour(period),
             'weekday_average': lambda: engine.weekday_average(period, 0)}
    result = {}
    for name, call in calls.items():
        try:
            call()
            result[name] = 'KHÔNG chặn'
        except UnsupportedRule:
            result[name] = 'UnsupportedRule'
    return result


def _ext_lines(ext, legacy_result):
    kinds = ext['by_kind']
    selected = legacy_result['selected'] + sum(k['selected'] for k in kinds.values())
    matched = legacy_result['matched_gold'] + sum(k['matched'] for k in kinds.values())
    total_line = (f"API hiện có phủ được {selected}/{legacy_result['total_train']} câu train (chọn được), khớp {matched} "
                  f"(bộ cũ {legacy_result['matched_gold']}/{legacy_result['selected']} + mở rộng "
                  f"{sum(k['matched'] for k in kinds.values())}/{sum(k['selected'] for k in kinds.values())})")
    lines = ['## Bộ chọn mở rộng (C1–C9)', '',
             'Bộ chọn regex bảo thủ, chỉ dùng trong verifier; câu bộ cũ đã chọn không chọn lại.', '',
             '| Loại | Nội dung | Chọn | Khớp | Lệch | Lỗi (UnsupportedRule / DataError / unanswerable / khác) |',
             '|---|---|---|---|---|---|']
    for kind, k in kinds.items():
        e = k['errors']
        other = sum(v for n, v in e.items() if n not in ('UnsupportedRule', 'DataError', 'unanswerable'))
        lines.append(f"| {kind} | {k['name']} | {k['selected']} | {k['matched']} | {k['mismatched']} | "
                     f"{e.get('UnsupportedRule', 0)} / {e.get('DataError', 0)} / {e.get('unanswerable', 0)} / {other} |")
    lines += ['', f'**{total_line}**', '', '### C10: luật chỉ có ở rulebook public, chạy với rulebook train', '']
    lines += [f'- `{name}`: {status}' for name, status in ext['public_only_with_train_rulebook'].items()]
    lines += ['', 'Không có đáp án gold cho C10: chỉ kiểm bằng test tổng hợp.', '']
    for kind, k in kinds.items():
        if k['mismatch_examples'] or k['error_examples']:
            lines += [f'### {kind} — 5 câu lệch / lỗi đầu tiên', '', '```json',
                      json.dumps({'lech': k['mismatch_examples'], 'loi': k['error_examples']}, ensure_ascii=False, indent=1),
                      '```', '']
    return lines, total_line


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train',type=Path,default=Path('train'))
    parser.add_argument('--cache',type=Path,default=Path('cache'))
    parser.add_argument('--out',type=Path,default=Path('reports/business_verification'))
    args=parser.parse_args(argv)
    result=verify(args.train,args.cache)
    legacy_ids=[r['id'] for r in result['rows']]+[s['id'] for s in result['skipped']]+[e['id'] for e in result['errors']]
    ext=verify_extended(args.train,args.cache,legacy_ids)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.with_suffix('.json').write_text(json.dumps({**result,'extended':ext},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    mismatches=[r for r in result['rows'] if not r['matched_gold']]
    ext_lines,total_line=_ext_lines(ext,result)
    lines=['# Kiểm chứng thư viện nghiệp vụ trên tập câu chọn lọc','',
           'Đây là kiểm chứng hồi quy theo bộ chọn câu cũ, không phải PA toàn bộ train.', '',
           f"- Tổng câu train: {result['total_train']}; được chọn: {result['selected']}; ngoài bộ chọn: {result['outside_selection']}.",
           f"- Bộ cũ bỏ qua: {result['legacy_skipped']}; so được: {result['compared']}; lỗi: {len(result['errors'])}.",
           f"- Khớp gold: {result['matched_gold']}/{result['compared']}; khớp phép tính cũ: {result['matched_legacy']}/{result['compared']}.",
           f"- Rulebook SHA256: {result['rulebook_sha256']}",'', '## Chênh lệch và lỗi','',
           '```json',json.dumps({'mismatches':mismatches,'errors':result['errors']},ensure_ascii=False,indent=2),'```','',
           *ext_lines]
    args.out.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')},ensure_ascii=False,indent=2))
    print('\n'.join(ext_lines[:16]))
    print(total_line)
    return 1 if mismatches or result['errors'] else 0


if __name__=='__main__':
    raise SystemExit(main())
