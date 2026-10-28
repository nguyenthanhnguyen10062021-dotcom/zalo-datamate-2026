#!/usr/bin/env python3
"""Kiểm tra khả năng tổng quát của loader (giả lập private test có mẫu file chưa gặp).

(a) Leave-one-group-out trên train: với mỗi nhóm mẫu file A–J (đọc từ bảng nhóm trong DESIGN.md),
    xây từ điển KHÔNG dùng README của các tiệm thuộc nhóm đó, nạp các tiệm nhóm đó, chấm như check_with_gold.
    Hai chế độ:
      - 'tu_dien'   : chỉ dùng từ điển (mô tả / tên cột) xây từ README còn lại — mô tả chưa thấy là không biết;
      - 'quy_tac'   : thêm DESC_RULES áp trực tiếp lên mô tả chưa thấy (quy tắc viết từ toàn bộ README train,
                      nên chế độ này lạc quan hơn thực tế — CHƯA CHẮC mức lạc quan).
    So với "không giấu" (cache của load_all.py, từ điển xây từ toàn bộ README train).
(b) Loader chung trên các tiệm public_test có mẫu file MỚI (nhóm đánh dấu 🆕 trong DESIGN.md):
    % cột thô ánh xạ được vào 5 bảng chuẩn, % bảng thô làm sạch thành công. Không có code riêng cho tiệm nào.

Chạy:  python generalize_check.py [--design surveys/DESIGN.md] [--workers 7]   (cần chạy load_all.py trước)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

import check_with_gold as G

ROOT = Path(__file__).resolve().parent


def parse_groups(design_path: Path) -> list[dict]:
    """Bảng nhóm mẫu file trong DESIGN.md: | **X. tên** | mô tả | Train | Test | Ngành |"""
    groups = []
    for line in design_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*\*\*([A-Z])\.\s*([^*]+)\*\*\s*(🆕)?\s*\|(.*)$", line)
        if not m:
            continue
        cells = [c.strip() for c in m[4].split("|")]
        if len(cells) < 3:
            continue
        train_cell, test_cell = cells[1], cells[2]
        train = sorted({f"biz_{n}" for n in re.findall(r"(?<!\d)(1\d\d)(?!\d)", train_cell)})
        test = sorted(set(re.findall(r"dev_\d{3}", test_cell)))
        groups.append({"nhom": m[1], "ten": m[2].strip(), "moi": bool(m[3]), "train": train, "test": test})
    return groups


def _load_one(shop: str, exclude: list[str], use_rules: bool) -> dict:
    warnings.simplefilter("ignore")
    sys.path.insert(0, str(ROOT))
    from loader import build_dictionaries, load_business
    from load_all import COVER_COLS
    readmes = [p for p in sorted((ROOT / "train" / "data").glob("*/README.md")) if p.parent.name not in exclude]
    d = build_dictionaries(readmes, use_rules=use_rules)
    try:
        res = load_business(ROOT / "train" / "data" / shop, ROOT / "train" / "rulebook.md", dictionaries=d)
    except Exception as e:  # noqa: BLE001
        return {"shop": shop, "loi": f"{type(e).__name__}: {e}"}
    n_cov = sum(bool(c in res[t] and res[t][c].notna().any()) for t, cols in COVER_COLS.items() for c in cols)
    n_all = sum(len(cols) for cols in COVER_COLS.values())
    return {"shop": shop,
            "tables": {"don_hang": res["don_hang"][["ma_don", "ngay_dat", "trang_thai", "tong_tien_hang",
                                                    "thoi_diem_dat"]],
                       "dong_hang": res["dong_hang"][["ma_don", "loai_dong", "thanh_tien", "ma_hang",
                                                      "so_luong_co_ban"]],
                       "mat_hang": res["mat_hang"][["ma_hang", "ten_hang", "don_vi_co_ban"]],
                       "cua_hang": res["cua_hang"]},
            "pct_cot_chuan": round(100 * n_cov / n_all, 1),
            "so_cot_unmapped": sum(len(tm.unmapped) for tm in res["table_maps"]
                                   if tm.role in ("line", "order", "product", "conversion"))}


def _cov_from_cache(shop: str) -> float | None:
    rep = ROOT / "cache" / shop / "don_hang.parquet"
    if not rep.exists():
        return None
    from load_all import COVER_COLS
    n_cov = 0
    for t, cols in COVER_COLS.items():
        df = pd.read_parquet(ROOT / "cache" / shop / f"{t}.parquet")
        n_cov += sum(bool(c in df and df[c].notna().any()) for c in cols)
    return round(100 * n_cov / sum(len(c) for c in COVER_COLS.values()), 1)


def leave_one_group_out(groups, questions, workers):
    jobs = []
    for g in groups:
        if g["moi"] or not g["train"]:
            continue
        for mode in ("tu_dien", "quy_tac"):
            for s in g["train"]:
                jobs.append((g["nhom"], mode, s, g["train"]))
    out = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_load_one, s, excl, mode == "quy_tac"): (n, mode, s) for n, mode, s, excl in jobs}
        for f, key in futs.items():
            out[key] = f.result()
            print(f"  LOGO nhóm {key[0]} [{key[1]}] {key[2]}: xong", flush=True)

    def score(get, shops, kinds=G.BASIC):
        by = G.evaluate(get, [q for q in questions if q["loai"] in kinds], set(shops))
        n = sum(len(v) for v in by.values())
        k = sum(i["khop"] for v in by.values() for i in v)
        return k, n, by

    rows, details = [], {}
    for g in groups:
        if g["moi"] or not g["train"]:
            continue
        base = score(lambda b: G.load_cached(ROOT / "cache" / b), g["train"])
        res_mode = {}
        for mode in ("tu_dien", "quy_tac"):
            def get(b, mode=mode):
                r = out.get((g["nhom"], mode, b))
                return None if r is None or "loi" in r else r["tables"]
            res_mode[mode] = score(get, g["train"])
            details[(g["nhom"], mode)] = res_mode[mode][2]
        base_ext = score(lambda b: G.load_cached(ROOT / "cache" / b), g["train"], G.EXTENDED)
        hold_ext = score(lambda b, g=g: (lambda r: None if r is None or "loi" in r else r["tables"])(
            out.get((g["nhom"], "tu_dien", b))), g["train"], G.EXTENDED)
        cov_base = [_cov_from_cache(s) for s in g["train"]]
        cov_hold = [out[(g["nhom"], "tu_dien", s)].get("pct_cot_chuan") for s in g["train"]]
        rows.append({"nhom": g["nhom"], "ten": g["ten"], "tiem": g["train"],
                     "khong_giau": base[:2], "giau_tu_dien": res_mode["tu_dien"][:2],
                     "giau_quy_tac": res_mode["quy_tac"][:2],
                     "mo_rong_khong_giau": base_ext[:2], "mo_rong_giau_tu_dien": hold_ext[:2],
                     "cot_chuan_khong_giau": sum(cov_base) / len(cov_base),
                     "cot_chuan_giau": sum(x for x in cov_hold if x is not None) / len(cov_hold),
                     "loi": [out[(g["nhom"], m, s)]["loi"] for m in ("tu_dien", "quy_tac") for s in g["train"]
                             if "loi" in out[(g["nhom"], m, s)]]})
    return rows, details


def new_pattern_coverage(groups):
    from loader.mapping import CONVERSION_CONCEPTS, LINE_CONCEPTS, ORDER_CONCEPTS, PRODUCT_CONCEPTS
    std = LINE_CONCEPTS | ORDER_CONCEPTS | PRODUCT_CONCEPTS | CONVERSION_CONCEPTS
    roles = {"line", "order", "product", "conversion", "inventory"}
    rows = []
    for g in groups:
        if not g["moi"]:
            continue
        for shop in g["test"]:
            cdir = ROOT / "cache" / shop
            if not (cdir / "mapping.json").exists():
                rows.append({"nhom": g["nhom"], "tiem": shop, "loi": "chưa có cache"})
                continue
            maps = json.loads((cdir / "mapping.json").read_text(encoding="utf-8"))
            cat = json.loads((cdir / "raw_catalog.json").read_text(encoding="utf-8"))
            cols = [m for m in maps if m["nguon_anh_xa"] != "cot_rong"]
            mapped = [m for m in cols if m["vai_tro"] in roles and m["khai_niem"] in std]
            ok_tab = [t for t in cat if t.get("file") and not t.get("loi") and t["so_dong"] > 0]
            don = pd.read_parquet(cdir / "don_hang.parquet", columns=["ma_don"])
            dong = pd.read_parquet(cdir / "dong_hang.parquet", columns=["ma_don"])
            vt = {}
            for m in maps:
                vt.setdefault(m["vai_tro"], set()).add(m["bang"])
            rows.append({"nhom": g["nhom"], "ten": g["ten"], "tiem": shop,
                         "pct_cot_map": round(100 * len(mapped) / max(len(cols), 1), 1),
                         "cot_map": len(mapped), "cot_tong": len(cols),
                         "bang_tho_ok": len(ok_tab), "bang_tho_tong": len(cat),
                         "so_don": len(don), "so_dong_hang": len(dong),
                         "vai_tro": {k: sorted(v) for k, v in vt.items()},
                         "cot_chua_map": sorted(f"{m['bang']}.{m['cot']}" for m in cols if m not in mapped)})
    return rows


def _v0_logo(path: Path) -> dict:
    """Số liệu leave-one-group-out của bản trước (reports/generalize_report_v0.md) để so trước/sau."""
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*([A-J])\.\s.*?\|\s*(\d+)/(\d+) \([^)]*\)\s*\|\s*(\d+)/(\d+)", line)
        if m:
            out[m[1]] = (int(m[4]), int(m[5]))
    return out


def _fmt(x):
    a, n = x
    return f"{a}/{n} ({100 * a / max(n, 1):.0f}%)"


def write_report(logo_rows, details, new_rows, path: Path, baseline: dict, after: dict):
    v0 = _v0_logo(ROOT / "reports" / "generalize_report_v0.md")
    L = ["# Kiểm tra khả năng tổng quát — loader v0.2 (bước 2c: viết tắt + suy từ giá trị)", "",
         "## (a) Leave-one-group-out trên train", "",
         "Từ điển xây KHÔNG dùng README của nhóm đang kiểm tra. Cơ bản = doanh thu tháng + số đơn huỷ (263 câu); "
         "mở rộng = doanh thu ca sáng/chiều + số lượng bán (check_with_gold.py).", "",
         "| nhóm | tiệm | cơ bản: không giấu | cơ bản: giấu (chỉ từ điển) — v0 → nay | cơ bản: giấu + quy tắc | "
         "mở rộng: không giấu | mở rộng: giấu (chỉ từ điển) | % cột chuẩn không giấu → giấu |",
         "|---|---|---|---|---|---|---|---|"]
    tot = {k: [0, 0] for k in ("khong_giau", "giau_tu_dien", "giau_quy_tac", "mo_rong_khong_giau",
                                "mo_rong_giau_tu_dien")}
    tot_v0 = [0, 0]
    for r in logo_rows:
        for k in tot:
            tot[k][0] += r[k][0]
            tot[k][1] += r[k][1]
        before = v0.get(r["nhom"])
        if before:
            tot_v0[0] += before[0]
            tot_v0[1] += before[1]
        L.append(f"| {r['nhom']}. {r['ten']} | {', '.join(r['tiem'])} | {_fmt(r['khong_giau'])} | "
                 f"{_fmt(before) if before else '?'} → {_fmt(r['giau_tu_dien'])} | {_fmt(r['giau_quy_tac'])} | "
                 f"{_fmt(r['mo_rong_khong_giau'])} | {_fmt(r['mo_rong_giau_tu_dien'])} | "
                 f"{r['cot_chuan_khong_giau']:.1f} → {r['cot_chuan_giau']:.1f} |")
    L.append(f"| **Tổng** | | **{_fmt(tot['khong_giau'])}** | **{_fmt(tuple(tot_v0))} → {_fmt(tot['giau_tu_dien'])}** | "
             f"**{_fmt(tot['giau_quy_tac'])}** | **{_fmt(tot['mo_rong_khong_giau'])}** | "
             f"**{_fmt(tot['mo_rong_giau_tu_dien'])}** | |")
    errs = [e for r in logo_rows for e in r["loi"]]
    if errs:
        L += ["", f"Lỗi khi nạp: {errs}"]
    L += ["", "### Câu lệch khi giấu nhóm (cơ bản, chỉ từ điển)", "",
          "| nhóm | tiệm | loại | tháng | đáp án | tính được |", "|---|---|---|---|---|---|"]
    for (nhom, mode), by in sorted(details.items()):
        if mode != "tu_dien":
            continue
        for b, items in sorted(by.items()):
            for i in items:
                if not i["khop"]:
                    L.append(f"| {nhom} | {b} | {i['loai']} | {i['thang']}/{i['nam']} | {i['gold']} | {i['tinh_duoc']} |")

    L += ["", "## (b) Loader chung trên tiệm public_test có mẫu file MỚI — trước / sau bước 2c", "",
          "% cột map = cột thô (bỏ cột rỗng) được ánh xạ vào khái niệm của 5 bảng chuẩn, trong bảng có vai trò "
          "bán / đơn / mặt hàng / quy đổi / tồn kho. Trước = cache v0 (reports/baseline_v0.json).", "",
          "| nhóm | tiệm | % cột map trước → sau | % cột chuẩn trước → sau | đơn trước → sau | dòng hàng | bảng thô OK | vai trò nhận ra |",
          "|---|---|---|---|---|---|---|---|"]
    for r in new_rows:
        if "loi" in r:
            L.append(f"| {r['nhom']} | {r['tiem']} | {r['loi']} | | | | | |")
            continue
        b = baseline.get(r["tiem"], {})
        a = after.get(r["tiem"], {})
        vt = "; ".join(f"{k}: {', '.join(v)}" for k, v in r["vai_tro"].items() if k != "other")
        L.append(f"| {r['nhom']}. {r['ten']} | {r['tiem']} | {b.get('pct_cot_map', '?')}% → **{r['pct_cot_map']}%** "
                 f"({r['cot_map']}/{r['cot_tong']}) | {b.get('pct_cot_chuan', '?')}% → {a.get('pct_cot_chuan', '?')}% | "
                 f"{b.get('so_don', '?')} → {r['so_don']} | {r['so_dong_hang']} | {r['bang_tho_ok']}/{r['bang_tho_tong']} | {vt} |")
    if new_rows:
        tm = sum(r.get("cot_map", 0) for r in new_rows)
        tc = sum(r.get("cot_tong", 0) for r in new_rows)
        bm = sum(baseline.get(r["tiem"], {}).get("cot_map", 0) for r in new_rows)
        bc = sum(baseline.get(r["tiem"], {}).get("cot_tong", 0) for r in new_rows)
        L.append(f"| **Tổng** | | **{100 * bm / max(bc, 1):.1f}% → {100 * tm / max(tc, 1):.1f}%** | | | | | |")
    L += ["", "### Cột vẫn chưa map ở tiệm mẫu mới", ""]
    for r in new_rows:
        if "cot_chua_map" in r:
            L.append(f"- **{r['tiem']}**: {', '.join(r['cot_chua_map'])}")

    L += ["", "## (c) Mọi tiệm — trước / sau bước 2c", "",
          "| tiệm | % cột map trước → sau | % cột chuẩn trước → sau | số đơn trước → sau |", "|---|---|---|---|"]
    for shop in sorted(after):
        b, a = baseline.get(shop, {}), after[shop]
        L.append(f"| {shop} | {b.get('pct_cot_map', '?')} → {a['pct_cot_map']} | {b.get('pct_cot_chuan', '?')} → "
                 f"{a['pct_cot_chuan']} | {b.get('so_don', '?')} → {a['so_don']} |")
    path.write_text("\n".join(L), encoding="utf-8")


def shop_metrics() -> dict:
    """% cột map, % cột chuẩn, số đơn của mọi tiệm trong cache (cùng định nghĩa với reports/baseline_v0.json)."""
    from load_all import COVER_COLS
    from loader.mapping import CONVERSION_CONCEPTS, LINE_CONCEPTS, ORDER_CONCEPTS, PRODUCT_CONCEPTS
    std = LINE_CONCEPTS | ORDER_CONCEPTS | PRODUCT_CONCEPTS | CONVERSION_CONCEPTS
    roles = {"line", "order", "product", "conversion", "inventory"}
    out = {}
    for d in sorted((ROOT / "cache").iterdir()):
        if not (d / "mapping.json").exists():
            continue
        maps = json.loads((d / "mapping.json").read_text(encoding="utf-8"))
        cols = [m for m in maps if m["nguon_anh_xa"] != "cot_rong"]
        mapped = [m for m in cols if m["vai_tro"] in roles and m["khai_niem"] in std]
        n_cov = 0
        for t, cs in COVER_COLS.items():
            df = pd.read_parquet(d / f"{t}.parquet")
            n_cov += sum(bool(c in df and df[c].notna().any()) for c in cs)
        out[d.name] = {"pct_cot_map": round(100 * len(mapped) / max(len(cols), 1), 1), "cot_map": len(mapped),
                       "cot_tong": len(cols),
                       "pct_cot_chuan": round(100 * n_cov / sum(len(c) for c in COVER_COLS.values()), 1),
                       "so_don": len(pd.read_parquet(d / "don_hang.parquet", columns=["ma_don"]))}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="surveys/DESIGN.md")
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--out", default="generalize_report.md")
    args = ap.parse_args(argv)
    groups = parse_groups(Path(args.design))
    print("Nhóm đọc từ DESIGN.md:", [(g["nhom"], g["train"], g["test"], "MỚI" if g["moi"] else "") for g in groups])
    qs = G.gold_questions()
    logo_rows, details = leave_one_group_out(groups, qs, args.workers)
    new_rows = new_pattern_coverage(groups)
    base_path = ROOT / "reports" / "baseline_v0.json"
    baseline = json.loads(base_path.read_text(encoding="utf-8")) if base_path.exists() else {}
    write_report(logo_rows, details, new_rows, Path(args.out), baseline, shop_metrics())
    print()
    print(f"{'nhóm':5s} {'không giấu':>12s} {'giấu-từ điển':>14s} {'giấu-quy tắc':>14s}")
    for r in logo_rows:
        f = lambda x: f"{x[0]}/{x[1]}"  # noqa: E731
        print(f"{r['nhom']:5s} {f(r['khong_giau']):>12s} {f(r['giau_tu_dien']):>14s} {f(r['giau_quy_tac']):>14s}")
    print()
    for r in new_rows:
        if "loi" not in r:
            print(f"{r['tiem']}: cột map {r['pct_cot_map']}%, bảng thô {r['bang_tho_ok']}/{r['bang_tho_tong']}, "
                  f"đơn {r['so_don']}, dòng {r['so_dong_hang']}")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
