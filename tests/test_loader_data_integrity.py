"""Synthetic regressions for canonical customer labels and cache missingness."""
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from business import DateRange, SalesMetrics
from load_all import to_parquet
from loader.build import _as_key, _join_customers


@pytest.mark.parametrize('dtype', [object, 'string'])
def test_cache_keys_keep_missingness_and_literal_strings(tmp_path, dtype):
    keys = _as_key(pd.Series(['001', pd.NA, None, np.nan, '', '<NA>', 'NaT'], dtype=dtype))
    frame = pd.DataFrame({'ma_khach': keys})
    original = frame.copy(deep=True)
    path = tmp_path / 'keys.parquet'
    to_parquet(frame, path)
    restored = pd.read_parquet(path)['ma_khach']
    assert restored.isna().tolist() == keys.isna().tolist()
    assert restored.dropna().tolist() == ['001', '<NA>', 'NaT']
    pd.testing.assert_frame_equal(frame, original)


def test_cache_object_text_preserves_all_missing_scalars(tmp_path):
    values = pd.Series(['001', None, np.nan, pd.NA, pd.NaT, '<NA>', 'NaT', ''], dtype=object)
    path = tmp_path / 'text.parquet'
    to_parquet(pd.DataFrame({'text': values}), path)
    restored = pd.read_parquet(path)['text']
    assert restored.isna().tolist() == values.isna().tolist()
    assert restored.dropna().tolist() == ['001', '<NA>', 'NaT', '']


def test_cache_preserves_numeric_boolean_datetime_and_mixed_values(tmp_path):
    frame = pd.DataFrame({
        'number': pd.Series([Decimal('12.5'), pd.NA, None], dtype=object),
        'flag': pd.Series([True, False, pd.NA], dtype=object),
        'date': pd.to_datetime(['2026-03-01', None, '2026-03-02']),
        'mixed': pd.Series(['001', 12, pd.NA], dtype=object),
        'empty': pd.Series([None, pd.NA, pd.NaT], dtype=object),
        'nested': pd.Series([['A', 'B'], {'key': 1}, None], dtype=object),
    })
    original = frame.copy(deep=True)
    path = tmp_path / 'types.parquet'
    to_parquet(frame, path)
    restored = pd.read_parquet(path)
    assert restored['number'].iloc[0] == 12.5
    assert restored['number'].isna().tolist() == [False, True, True]
    assert restored['flag'].dropna().tolist() == [True, False]
    assert restored['flag'].isna().tolist() == [False, False, True]
    pd.testing.assert_series_equal(restored['date'], frame['date'])
    assert restored['mixed'].dropna().tolist() == ['001', '12']
    assert restored['mixed'].isna().tolist() == [False, False, True]
    assert restored['empty'].isna().all()
    assert restored['nested'].dropna().tolist() == ["['A', 'B']", "{'key': 1}"]
    pd.testing.assert_frame_equal(frame, original)


def customer_catalog(ids, names):
    return pd.DataFrame({'ma_khach': ids, 'ten_khach': names,
                         'nhom_khach': [None] * len(ids),
                         'sdt': [None] * len(ids), 'dia_chi': [None] * len(ids)})


def test_customer_join_fills_unique_code_without_changing_identity_or_source():
    orders = pd.DataFrame({'ma_khach': ['001', '002', None, 'UNKNOWN', 'DUP'],
        'ten_khach': [None, 'Invoice name', None, None, None],
        'ten_khach_goc': [None, 'Invoice name (0900000000)', None, None, None],
        'khach_key': ['001', '002', None, 'UNKNOWN', 'DUP'],
        'la_khach_le': [False, False, True, False, False]}, index=[2, 4, 6, 8, 10])
    original = orders.copy(deep=True)
    customers = customer_catalog(['001', '002', 'DUP', 'DUP', None],
        ['Catalog A', 'Catalog B', 'Duplicate A', 'Duplicate B', 'Missing code'])
    catalog_before = customers.copy(deep=True)
    joined, count = _join_customers(orders, customers, True)
    assert joined.loc[2, 'ten_khach'] == 'Catalog A'
    assert joined.loc[4, 'ten_khach'] == 'Invoice name'
    assert joined.loc[[6, 8, 10], 'ten_khach'].isna().all()
    assert count == 1
    pd.testing.assert_frame_equal(joined[original.columns.drop('ten_khach')],
                                  original.drop(columns='ten_khach'))
    pd.testing.assert_frame_equal(customers, catalog_before)


def test_customer_join_adds_absent_name_column_by_unique_code():
    orders = pd.DataFrame({'ma_khach': ['001'], 'khach_key': ['001']})
    joined, _ = _join_customers(orders, customer_catalog(['001'], ['Catalog A']), True)
    assert joined['ten_khach'].tolist() == ['Catalog A']


@pytest.mark.parametrize('co_ma_khach', [False, True])
def test_customer_join_without_catalog_codes_does_not_infer_missing_names(co_ma_khach):
    orders = pd.DataFrame({'ma_khach': ['001', None], 'ten_khach': [None, 'Invoice name'],
                           'khach_key': ['catalog a', 'invoice name']})
    customers = customer_catalog([None, None], ['Catalog A', 'Invoice name'])
    customers['nhom_khach'] = ['Group A', 'Group B']
    joined, _ = _join_customers(orders, customers, co_ma_khach)
    assert pd.isna(joined.loc[0, 'ten_khach'])
    assert joined.loc[1, 'ten_khach'] == 'Invoice name'
    assert joined['nhom_khach'].tolist() == ['Group A', 'Group B']


def test_customer_join_cache_and_ranking_exclude_walkins(tmp_path, rules):
    orders = pd.DataFrame({'ma_don': ['O1', 'O2'], 'ngay_dat': ['2026-03-01'] * 2,
        'trang_thai': ['hoan_thanh'] * 2, 'ma_khach': _as_key(pd.Series(['001', pd.NA], dtype='string')),
        'ten_khach': [None, None], 'ten_khach_goc': [None, None],
        'khach_key': _as_key(pd.Series(['001', pd.NA], dtype='string')),
        'la_khach_le': [False, True], 'tong_tien_hang': [100, 900]})
    joined, _ = _join_customers(orders, customer_catalog(['001'], ['Catalog A']), True)
    path = tmp_path / 'orders.parquet'
    to_parquet(joined, path)
    tables = {'don_hang': pd.read_parquet(path), 'dong_hang': pd.DataFrame(),
              'mat_hang': pd.DataFrame(), 'cua_hang': {'co_ma_khach': True, 'co_ma_don': True,
                'ngay_bat_dau_du_lieu': '2026-03-01', 'ngay_ket_thuc_du_lieu': '2026-03-31'}}
    engine = SalesMetrics(tables, rules, '2026-03-04')
    period = DateRange('2026-03-01', '2026-03-31')
    for metric in ('revenue', 'orders'):
        answer = engine.top_customers(period, k=5, metric=metric)
        assert answer.type == 'list'
        assert answer.answer == ['Catalog A']
    assert engine.revenue(period).answer == 1000
