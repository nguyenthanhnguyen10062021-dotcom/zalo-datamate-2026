#!/usr/bin/env python3
"""Regression on the legacy checker's selected train questions, not full PA.

Gold data is read ONLY here, never by business/. Selection intentionally retains
the legacy checker's restrictions so the before/after denominators are visible.
"""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path

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


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train',type=Path,default=Path('train'))
    parser.add_argument('--cache',type=Path,default=Path('cache'))
    parser.add_argument('--out',type=Path,default=Path('reports/business_verification'))
    args=parser.parse_args(argv)
    result=verify(args.train,args.cache)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    mismatches=[r for r in result['rows'] if not r['matched_gold']]
    lines=['# Kiểm chứng thư viện nghiệp vụ trên tập câu chọn lọc','',
           'Đây là kiểm chứng hồi quy theo bộ chọn câu cũ, không phải PA toàn bộ train.', '',
           f"- Tổng câu train: {result['total_train']}; được chọn: {result['selected']}; ngoài bộ chọn: {result['outside_selection']}.",
           f"- Bộ cũ bỏ qua: {result['legacy_skipped']}; so được: {result['compared']}; lỗi: {len(result['errors'])}.",
           f"- Khớp gold: {result['matched_gold']}/{result['compared']}; khớp phép tính cũ: {result['matched_legacy']}/{result['compared']}.",
           f"- Rulebook SHA256: {result['rulebook_sha256']}",'', '## Chênh lệch và lỗi','',
           '```json',json.dumps({'mismatches':mismatches,'errors':result['errors']},ensure_ascii=False,indent=2),'```']
    args.out.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')},ensure_ascii=False,indent=2))
    return 1 if mismatches or result['errors'] else 0


if __name__=='__main__':
    raise SystemExit(main())
