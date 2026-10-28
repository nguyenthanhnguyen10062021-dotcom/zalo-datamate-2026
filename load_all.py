#!/usr/bin/env python3
"""Nạp mọi tiệm (train + public_test) -> cache/<business_id>/, in tóm tắt và ghi load_report.md.

Chạy:  python load_all.py [--only biz_101,dev_012] [--workers 6] [--cache cache]

Cache mỗi tiệm:
  cache/<bid>/don_hang.parquet, dong_hang.parquet, mat_hang.parquet, quy_doi_don_vi.parquet
  cache/<bid>/cua_hang.json        metadata + năng lực (nang_luc)
  cache/<bid>/mapping.json         cột gốc -> khái niệm chuẩn, nguồn ánh xạ, vai trò bảng
  cache/<bid>/checks.json          kết quả kiểm tra tự động
  cache/<bid>/raw/*.parquet + raw_catalog.json   bảng thô sạch
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

SPLITS = [("train", Path("train")), ("public_test", Path("public_test"))]
SALES_ROLES = ("line", "order", "product", "conversion")

# cột chuẩn tính độ phủ (bỏ cột suy ra / cột của ngành mới chưa làm ở v0)
COVER_COLS = {
    "don_hang": ["ma_don", "ngay_dat", "thoi_diem_dat", "trang_thai", "ma_khach", "ten_khach", "nhom_khach",
                 "kenh_ban", "hinh_thuc_tt", "ma_nhan_vien", "tong_tien_hang", "giam_gia_don", "tong_phai_tra",
                 "con_no_cuoi_du_lieu"],
    "dong_hang": ["ma_hang", "ten_hang_goc", "so_luong", "don_vi", "so_luong_co_ban", "don_gia", "giam_gia_dong",
                  "thanh_tien", "gia_von_dong"],
    "mat_hang": ["ten_hang", "nhom_hang", "don_vi_co_ban", "gia_ban_hien_tai", "gia_von"],
}


def to_parquet(df: pd.DataFrame, path: Path) -> None:
    """Ghi parquet; cột object lẫn kiểu -> số nếu được, không thì chuỗi."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object:
            nonnull = df[c].dropna()
            if len(nonnull) and nonnull.map(lambda v: isinstance(v, bool)).all():
                df[c] = df[c].astype("boolean")
                continue
            num = pd.to_numeric(nonnull, errors="coerce") if len(nonnull) else nonnull
            if len(nonnull) and num.notna().all() and not nonnull.map(lambda v: isinstance(v, str)).any():
                df[c] = pd.to_numeric(df[c], errors="coerce")
            else:
                df[c] = df[c].map(lambda v: None if v is None or (isinstance(v, float) and v != v) else str(v)
                                  ).astype("string")
    df.to_parquet(path, index=False)


def mapping_records(res) -> list[dict]:
    out = []
    for tm in res["table_maps"]:
        for c in tm.table.columns:
            m = tm.cols.get(c)
            out.append({"bang": tm.table.name, "vai_tro": tm.role, "cot": c,
                        "khai_niem": m[0] if m else None, "nguon_anh_xa": m[1] if m else
                        ("cot_rong" if tm.table.kinds.get(c) == "empty" else "unmapped"),
                        "mo_ta_readme": tm.descs.get(c), "bang_chung": tm.evidence.get(c)})
    return out


def summarize(res, split: str) -> dict:
    ch = res["cua_hang"]
    cover = {}
    for tname, cols in COVER_COLS.items():
        df = res[tname]
        cover[tname] = {c: bool(c in df and df[c].notna().any()) for c in cols}
    n_cov = sum(v for d in cover.values() for v in d.values())
    n_all = sum(len(d) for d in cover.values())
    unmapped = [f"{tm.table.name}.{c}" for tm in res["table_maps"] if tm.role in SALES_ROLES for c in tm.unmapped]
    raw_ok = sum(1 for t in res["raw_tables"] if t.typed is not None and t.error is None and len(t.data))
    roles = {}
    for tm in res["table_maps"]:
        roles.setdefault(tm.role, []).append(tm.table.name)
    return {
        "split": split, "business_id": ch["business_id"], "so_don": len(res["don_hang"]),
        "so_dong_hang": len(res["dong_hang"]), "so_mat_hang": len(res["mat_hang"]),
        "ngay_bat_dau": ch["ngay_bat_dau_du_lieu"], "ngay_cuoi_du_lieu": ch["ngay_cuoi_trong_du_lieu"],
        "ngay_cuoi_readme": ch["ngay_ket_thuc_du_lieu"], "pct_cot_chuan": round(100 * n_cov / n_all, 1),
        "cot_chuan": cover, "unmapped": unmapped, "raw_ok": raw_ok, "raw_tong": len(res["raw_tables"]),
        "vai_tro_bang": roles, "checks": res["checks"], "loi": res["errors"], "thoi_gian": res["thoi_gian_nap"],
        "nang_luc": ch["nang_luc"], "nguon_trang_thai": ch["nguon_trang_thai"], "thong_ke": ch["thong_ke"],
    }


def process(shop_dir: str, split: str, split_root: str, cache_root: str) -> dict:
    warnings.simplefilter("ignore")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from loader import load_business
    from loader.raw import save_raw

    shop_dir, cache = Path(shop_dir), Path(cache_root) / Path(shop_dir).name
    t0 = time.time()
    try:
        res = load_business(shop_dir, Path(split_root) / "rulebook.md", train_dir=Path(split_root).parent / "train")
    except Exception as e:  # noqa: BLE001
        return {"split": split, "business_id": shop_dir.name, "crash": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(), "thoi_gian": round(time.time() - t0, 1)}
    cache.mkdir(parents=True, exist_ok=True)
    for name in ("don_hang", "dong_hang", "mat_hang", "quy_doi_don_vi", "khach_hang"):
        to_parquet(res[name], cache / f"{name}.parquet")
    (cache / "cua_hang.json").write_text(json.dumps(res["cua_hang"], ensure_ascii=False, indent=1, default=str),
                                         encoding="utf-8")
    maps = mapping_records(res)
    (cache / "mapping.json").write_text(json.dumps(maps, ensure_ascii=False, indent=1), encoding="utf-8")
    (cache / "checks.json").write_text(json.dumps(res["checks"], ensure_ascii=False, indent=1), encoding="utf-8")
    describe = {(m["bang"], m["cot"]): m["mo_ta_readme"] for m in maps}
    concepts = {(m["bang"], m["cot"]): m["khai_niem"] for m in maps}
    save_raw(res["raw_tables"], cache, describe, concepts)
    return summarize(res, split)


def write_report(summaries: list[dict], path: Path) -> None:
    L = ["# Báo cáo nạp dữ liệu — loader v0", "",
         "Sinh bởi `load_all.py`. % cột chuẩn = số cột chuẩn (don_hang, dong_hang, mat_hang; xem COVER_COLS) có dữ liệu.",
         "", "## Tổng quan", "",
         "| bộ | tiệm | đơn | dòng hàng | khoảng ngày (README) | % cột chuẩn | bảng thô OK | kiểm tra PASS/FAIL | giây |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        if "crash" in s:
            L.append(f"| {s['split']} | {s['business_id']} | ❌ CRASH | | | | | | {s['thoi_gian']} |")
            continue
        npass = sum(c["ket_qua"] == "PASS" for c in s["checks"])
        nfail = sum(c["ket_qua"] == "FAIL" for c in s["checks"])
        rng = f"{s['ngay_bat_dau']} → {s['ngay_cuoi_du_lieu']} ({s['ngay_cuoi_readme']})"
        L.append(f"| {s['split']} | {s['business_id']} | {s['so_don']} | {s['so_dong_hang']} | {rng} | "
                 f"{s['pct_cot_chuan']} | {s['raw_ok']}/{s['raw_tong']} | {npass}/{nfail} | {s['thoi_gian']} |")
    L += ["", "## Chi tiết từng tiệm", ""]
    for s in summaries:
        L.append(f"### {s['split']} / {s['business_id']}")
        if "crash" in s:
            L += ["", "```", s["traceback"], "```", ""]
            continue
        L.append(f"- đơn {s['so_don']}, dòng hàng {s['so_dong_hang']}, mặt hàng {s['so_mat_hang']}; "
                 f"ngày {s['ngay_bat_dau']} → {s['ngay_cuoi_du_lieu']} (README: {s['ngay_cuoi_readme']}); "
                 f"nạp {s['thoi_gian']}s")
        L.append(f"- trạng thái lấy từ: {s['nguon_trang_thai']}; thống kê: {s['thong_ke']}")
        L.append("- vai trò bảng: " + "; ".join(f"**{r}**: {', '.join(v)}" for r, v in s["vai_tro_bang"].items()))
        missing = [f"{t}.{c}" for t, d in s["cot_chuan"].items() for c, ok in d.items() if not ok]
        L.append(f"- % cột chuẩn có dữ liệu: {s['pct_cot_chuan']}% — thiếu: {', '.join(missing) or '(không)'}")
        L.append(f"- cột unmapped (bảng bán/mặt hàng/quy đổi): {', '.join(s['unmapped']) or '(không)'}")
        L.append(f"- bảng thô làm sạch thành công: {s['raw_ok']}/{s['raw_tong']}")
        if s["loi"]:
            L.append(f"- lỗi: {s['loi']}")
        nl = s["nang_luc"]
        L.append(f"- năng lực CÓ: {', '.join(k for k, v in nl.items() if v)}")
        L.append(f"- năng lực KHÔNG có: {', '.join(k for k, v in nl.items() if not v)}")
        L.append("")
        L.append("| kiểm tra | kết quả | số liệu | ngưỡng |")
        L.append("|---|---|---|---|")
        for c in s["checks"]:
            L.append(f"| {c['kiem_tra']} | {c['ket_qua']} | {str(c['so_lieu']).replace('|', '/')} | {c['nguong']} |")
        L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="danh sách business_id, cách nhau dấu phẩy")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cache", default="cache")
    ap.add_argument("--report", default="load_report.md")
    args = ap.parse_args(argv)
    only = set(args.only.split(",")) if args.only else None

    jobs = []
    for split, root in SPLITS:
        for d in sorted((root / "data").iterdir()):
            if d.is_dir() and (only is None or d.name in only):
                jobs.append((str(d), split, str(root), args.cache))
    t0 = time.time()
    results = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process, *j): j for j in jobs}
        for f in as_completed(futs):
            s = f.result()
            results[(s["split"], s["business_id"])] = s
            flag = "CRASH " + s["crash"] if "crash" in s else \
                f"đơn {s['so_don']:>6} dòng {s['so_dong_hang']:>7} cột chuẩn {s['pct_cot_chuan']:>5}%"
            print(f"[{time.time() - t0:6.1f}s] {s['split']:11s} {s['business_id']}: {flag}", flush=True)
    summaries = [results[(j[1], Path(j[0]).name)] for j in jobs]
    write_report(summaries, Path(args.report))
    n_crash = sum("crash" in s for s in summaries)
    print(f"Xong {len(summaries)} tiệm, {n_crash} crash, {time.time() - t0:.0f}s -> {args.report}")


if __name__ == "__main__":
    main()
