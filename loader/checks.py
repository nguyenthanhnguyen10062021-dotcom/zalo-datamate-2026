"""Kiểm tra tự động sau khi nạp (DESIGN.md mục e). Mỗi kiểm tra trả PASS / FAIL / BO_QUA + số liệu."""

from __future__ import annotations

import re
from datetime import timedelta

import numpy as np
import pandas as pd

from .parsers import HUY, normalize_status, parse_date, parse_money, year_from_name


def _r(name, ok, so_lieu, nguong):
    return {"kiem_tra": name, "ket_qua": "BO_QUA" if ok is None else ("PASS" if ok else "FAIL"),
            "so_lieu": so_lieu, "nguong": nguong}


def check_end_date(res):
    ch = res["cua_hang"]
    end, last = ch.get("ngay_ket_thuc_du_lieu"), ch.get("ngay_cuoi_trong_du_lieu")
    if not end or not last:
        return _r("ngay_cuoi_khop_README", None, f"README={end}, du_lieu={last}", "<= README và trong 7 ngày")
    e, l_ = pd.Timestamp(end), pd.Timestamp(last)
    ok = (l_ <= e) and (l_ >= e - timedelta(days=7))
    return _r("ngay_cuoi_khop_README", ok, f"README={end}, ngày đặt lớn nhất={last}", "<= README và trong 7 ngày")


def check_status(res):
    d = res["don_hang"]
    goc = d["trang_thai_goc"].dropna()
    if res["cua_hang"]["nguon_trang_thai"] != "cot_trang_thai" or not len(goc):
        return _r("trang_thai_anh_xa_duoc", None, f"nguồn trạng thái: {res['cua_hang']['nguon_trang_thai']}", "100%")
    ok_mask = goc.map(lambda v: normalize_status(v) is not None)
    bad = goc[~ok_mask].value_counts().head(5).to_dict()
    pct = ok_mask.mean() * 100
    return _r("trang_thai_anh_xa_duoc", pct == 100, f"{pct:.2f}% ({len(goc)} đơn); chưa nhận ra: {bad}", "100%")


def _sale_lines(dong):
    return dong[dong["loai_dong"].isin(["hang", "phi_phuc_vu", "topping"])]


def check_order_sum(res):
    d, l_ = res["don_hang"], res["dong_hang"]
    if not len(l_) or d["tong_tien_hang"].isna().all():
        return _r("tong_dong_bang_tien_hang_don", None, "không có tong_tien_hang hoặc dòng hàng", ">= 99% đơn")
    s = _sale_lines(l_).groupby("ma_don")["thanh_tien"].sum()
    m = d.set_index("ma_don")["tong_tien_hang"].dropna()
    common = m.index.intersection(s.index)
    if not len(common):
        return _r("tong_dong_bang_tien_hang_don", None, "không đơn nào có cả hai", ">= 99% đơn")
    ok = (np.abs(m[common].astype(float) - s[common].astype(float)) <= 1).mean() * 100
    return _r("tong_dong_bang_tien_hang_don", ok >= 99, f"{ok:.2f}% của {len(common)} đơn", ">= 99% đơn")


def check_daily_totals(res):
    """Dòng tổng theo ngày (đã bỏ khỏi dữ liệu) so với tổng tính lại từ bảng chuẩn."""
    rows = [r for t in res["raw_tables"] for r in t.total_rows]
    if not rows:
        return _r("dong_tong_ngay_khop", None, "không có dòng tổng", ">= 99% ngày")
    d, l_ = res["don_hang"], res["dong_hang"]
    nd = pd.to_datetime(d["ngay_dat"], errors="coerce")
    by_day = {}
    if len(l_):
        x = _sale_lines(l_).merge(d[["ma_don", "trang_thai"]].assign(_d=nd.values), on="ma_don", how="left")
        by_day["dong_tat_ca"] = x.groupby("_d")["thanh_tien"].sum()
        by_day["dong_khong_huy"] = x[x["trang_thai"] != HUY].groupby("_d")["thanh_tien"].sum()
    for col in ("tong_tien_hang", "tong_phai_tra"):
        if d[col].notna().any():
            by_day[col] = d.assign(_d=nd).groupby("_d")[col].sum()
    n_day, n_ok = 0, 0
    for r in rows:
        label = next((c for c in r["cells"] if c and re.search(r"\d{1,2}/\d{1,2}", c)), None)
        if not label:
            continue
        m = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", label)
        year = int(m[3]) if m[3] else (year_from_name(r["__sheet"]) or year_from_name(r["__file"]))
        day = parse_date(f"{m[1]}/{m[2]}", year) if year else None
        if day is None:
            continue
        n_day += 1
        nums = {parse_money(c) for c in r["cells"] if c and parse_money(c) is not None}
        if any(abs(float(s.get(pd.Timestamp(day), np.nan)) - float(v)) <= 1 for s in by_day.values() for v in nums):
            n_ok += 1
    if not n_day:
        return _r("dong_tong_ngay_khop", None, f"{len(rows)} dòng tổng, không có dòng tổng theo ngày", ">= 99% ngày")
    pct = n_ok / n_day * 100
    return _r("dong_tong_ngay_khop", pct >= 99, f"{n_ok}/{n_day} ngày khớp ({pct:.1f}%)", ">= 99% ngày")


def check_price_qty(res):
    l_ = res["dong_hang"]
    x = l_[l_["loai_dong"] == "hang"].dropna(subset=["don_gia", "so_luong", "thanh_tien"])
    if not len(x):
        return _r("gia_x_sl_vs_thanh_tien", None, "thiếu đơn giá / số lượng / thành tiền", ">= 99% không vượt")
    gross = x["don_gia"].astype(float) * x["so_luong"].astype(float)
    disc = x["giam_gia_dong"].astype(float).fillna(0) if x["giam_gia_dong"].notna().any() else 0
    tt = x["thanh_tien"].astype(float)
    exact = (np.abs(gross - disc - tt) <= 1).mean() * 100
    not_over = (np.abs(tt) <= np.abs(gross) + 1).mean() * 100
    return _r("gia_x_sl_vs_thanh_tien", not_over >= 99,
              f"khớp đúng {exact:.2f}%, không vượt {not_over:.2f}% ({len(x)} dòng)", ">= 99% không vượt")


def check_factor(res):
    st = res["cua_hang"]["thong_ke"]
    n, ok = st.get("he_so_doi_chieu", 0), st.get("he_so_khop", 0)
    if not n:
        return _r("he_so_quy_doi_khop", None, "không có cột số lượng cơ bản trong file để đối chiếu", ">= 99%")
    return _r("he_so_quy_doi_khop", ok / n >= 0.99, f"{ok}/{n} dòng ({ok / n * 100:.2f}%)", ">= 99%")


def check_product_link(res):
    l_ = res["dong_hang"]
    if not len(l_):
        return _r("dong_hang_noi_duoc_mat_hang", None, "không có dòng hàng", "<= 1% không nối được")
    # bảng quy đổi chỉ liệt kê hàng có đơn vị lớn -> không phải danh mục đầy đủ
    has_catalog = any(tm.role in ("product", "inventory") for tm in res["table_maps"])
    if not has_catalog:
        return _r("dong_hang_noi_duoc_mat_hang", None, "tiệm không có danh mục hàng đầy đủ (mã tự sinh từ tên)",
                  "<= 1% không nối được")
    hang = l_[l_["loai_dong"] == "hang"]
    if not len(hang):
        return _r("dong_hang_noi_duoc_mat_hang", None, "không có dòng hàng", "<= 1% không nối được")
    mh = res["mat_hang"]
    only_from_lines = set(mh.loc[mh["nguon"] == "dong_hang", "ma_hang"])
    n_bad = int(hang["ma_hang"].isin(only_from_lines).sum())
    pct = n_bad / len(hang) * 100
    return _r("dong_hang_noi_duoc_mat_hang", pct <= 1, f"{pct:.2f}% dòng không nối được ({n_bad})",
              "<= 1% không nối được")


def check_parse_fail(res):
    n_cells = n_fail = 0
    for t in res["raw_tables"]:
        if t.typed is None:
            continue
        for c, k in t.kinds.items():
            if k != "number":
                continue
            raw = t.data[c]
            ne = raw.map(lambda v: v is not None and not (isinstance(v, float) and v != v) and str(v).strip() != "")
            n_cells += int(ne.sum())
            n_fail += int((ne & t.typed[c].isna()).sum())
    if not n_cells:
        return _r("o_so_parse_loi", None, "không có cột số", "<= 0.1%")
    pct = n_fail / n_cells * 100
    return _r("o_so_parse_loi", pct <= 0.1, f"{pct:.3f}% ({n_fail}/{n_cells} ô)", "<= 0.1%")


ALL_CHECKS = [check_end_date, check_status, check_order_sum, check_daily_totals, check_price_qty, check_factor,
              check_product_link, check_parse_fail]


def run_checks(res) -> list[dict]:
    out = []
    for f in ALL_CHECKS:
        try:
            out.append(f(res))
        except Exception as e:  # noqa: BLE001
            out.append(_r(f.__name__.replace("check_", ""), False, f"lỗi khi kiểm tra: {type(e).__name__}: {e}", ""))
    return out
