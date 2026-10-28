"""Ghi cache: ô rỗng phải là null thật sau khi ghi/đọc parquet, không thành chuỗi "<NA>"/"nan"/"None"."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from load_all import json_value, to_parquet  # noqa: E402
from loader.parsers import is_null  # noqa: E402

FAKE_NULLS = {"<NA>", "nan", "NaN", "None", "NaT"}


def test_parquet_roundtrip_keeps_nulls(tmp_path):
    df = pd.DataFrame({
        "obj_mixed": pd.Series(["KH01", None, np.nan, pd.NA, pd.NaT, 12], dtype=object),
        "string_dtype": pd.Series(["KH01", None, "KH02", None, "KH03", None], dtype="string"),
        "obj_numbers": pd.Series([1, None, 2.5, pd.NA, 3, np.nan], dtype=object),
        "obj_bools": pd.Series([True, None, False, pd.NA, True, False], dtype=object),
    })
    path = tmp_path / "t.parquet"
    to_parquet(df, path)
    back = pd.read_parquet(path)
    for col in df.columns:
        assert back[col].isna().tolist() == df[col].isna().tolist(), col
        texts = set(back[col].dropna().astype(str))
        assert not texts & FAKE_NULLS, (col, texts)
    assert back["obj_mixed"].dropna().tolist() == ["KH01", "12"]
    assert back["obj_numbers"].dropna().tolist() == [1, 2.5, 3]
    assert back["obj_bools"].dropna().tolist() == [True, False, True, False]


def test_string_dtype_column_written_from_object(tmp_path):
    # Trường hợp gây lỗi cũ: cột object chứa pd.NA (lấy từ cột kiểu "string") lẫn chuỗi
    col = pd.Series(["KH01", "KH02"], dtype="string").reindex([0, 1, 2]).astype(object)
    to_parquet(pd.DataFrame({"ma_khach": col}), tmp_path / "t.parquet")
    back = pd.read_parquet(tmp_path / "t.parquet")["ma_khach"]
    assert back.isna().tolist() == [False, False, True]


@pytest.mark.parametrize("value, expected", [(None, True), (np.nan, True), (pd.NA, True), (pd.NaT, True),
                                             ("", False), ("nan", False), (0, False)])
def test_is_null(value, expected):
    assert is_null(value) is expected


def test_json_value_keeps_real_types():
    # numpy.bool_ từng bị default=str ghi thành chuỗi "False" (chuỗi này lại là truthy)
    meta = {"co": np.bool_(True), "khong": np.bool_(False), "n": np.int64(3), "rong": pd.NA,
            "ngay": pd.Timestamp("2026-01-02")}
    back = json.loads(json.dumps(meta, default=json_value))
    assert back == {"co": True, "khong": False, "n": 3, "rong": None, "ngay": "2026-01-02 00:00:00"}


def test_build_thuoc_keeps_only_drug_rows():
    from loader.build import build_thuoc
    mat = pd.DataFrame({'ma_hang': ['A', 'B', 'C', 'D'], 'hoat_chat': ['Loratadin', None, ' ', None],
                        'ke_don': [None, True, None, None]})
    out = build_thuoc(mat)
    assert out['ma_hang'].tolist() == ['A', 'B'] and out['hoat_chat'].isna().tolist() == [False, True]
    assert list(build_thuoc(mat.iloc[0:0]).columns) == ['ma_hang', 'hoat_chat', 'ke_don']
