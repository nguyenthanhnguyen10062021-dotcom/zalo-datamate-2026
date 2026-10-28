import json

import pandas as pd

from verify_business import verify


def test_verifier_checks_library_and_counts_excluded_questions(tmp_path, rules):
    train = tmp_path/'train'
    train.mkdir()
    (train/'rulebook.md').write_text(rules.text,encoding='utf-8')
    questions = [
        {'id':'q1','business_id':'synthetic','question':'doanh thu tháng 3/2026 bao nhiêu','as_of_date':'2026-03-04'},
        {'id':'q2','business_id':'synthetic','question':'câu không hỗ trợ','as_of_date':'2026-03-04'},
    ]
    gold = [{'id':'q1','type':'number','answer':123}, {'id':'q2','type':'string','answer':'x'}]
    for name,rows in [('questions',questions),('answers',gold)]:
        (train/f'{name}.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows),encoding='utf-8')
    cache=tmp_path/'cache'/'synthetic'
    cache.mkdir(parents=True)
    pd.DataFrame([{'ma_don':'O1','ngay_dat':'2026-03-01','trang_thai':'hoan_thanh',
                   'tong_tien_hang':123,'thoi_diem_dat':'2026-03-01 09:00:00'}]).to_parquet(cache/'don_hang.parquet')
    pd.DataFrame([{'ma_don':'O1','ma_hang':'P1','loai_dong':'hang','thanh_tien':123,'so_luong_co_ban':1}]).to_parquet(cache/'dong_hang.parquet')
    pd.DataFrame([{'ma_hang':'P1','ten_hang':'Món thử','don_vi_co_ban':'ly'}]).to_parquet(cache/'mat_hang.parquet')
    (cache/'cua_hang.json').write_text(json.dumps({'co_ma_don':True,'ngay_bat_dau_du_lieu':'2026-03-01','ngay_ket_thuc_du_lieu':'2026-03-31'}),encoding='utf-8')
    result=verify(train,tmp_path/'cache')
    assert result['total_train']==2
    assert result['selected']==result['compared']==result['matched_gold']==1
    assert result['outside_selection']==1
    assert result['errors']==[]
    assert result['rows'][0]['legacy']==result['rows'][0]['library']['answer']==123
