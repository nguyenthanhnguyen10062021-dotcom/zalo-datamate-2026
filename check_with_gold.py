#!/usr/bin/env python3
"""Kiểm tra loader bằng đáp án train: doanh thu tháng M/YYYY và số đơn huỷ tháng M/YYYY.

Chạy:  python check_with_gold.py [--cache cache] [--out gold_report.md]

Lọc câu hỏi (bảo thủ — chỉ nhận câu chắc chắn đúng dạng):
  * có cụm tháng cụ thể 'tháng M/YYYY' / 'tháng M năm YYYY' (không nhận 'tháng này');
  * bỏ cụm tháng, mọi từ còn lại phải thuộc DANH SÁCH TRẮNG từ đệm của câu hỏi
    "tổng doanh thu" (hoặc "bao nhiêu đơn huỷ"); có từ lạ (tên hàng, nhóm, ca, kênh, %…) -> bỏ qua.
Tính theo rulebook §1 từ 5 bảng chuẩn:
  doanh thu = Σ thanh_tien các dòng (hàng + phí phục vụ) của đơn KHÔNG huỷ, KHÔNG trả hàng, theo ngày đặt;
  tiệm không có dòng hàng: Σ tong_tien_hang của đơn (tiền hàng trước giảm giá đơn);
  kỳ nằm hoàn toàn ngoài [ngày bắt đầu, ngày cuối README] -> unanswerable (§7).
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

HUY, TRA_HANG = "huy", "tra_hang"
REVENUE_LINE_KINDS = ("hang", "phi_phuc_vu", "topping")


# ---------------------------------------------------------------------------
# Chuẩn hoá câu hỏi
# ---------------------------------------------------------------------------

def _strip(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _telex(s: str) -> str:
    """Sửa lỗi gõ Telex sót: âm tiết tiếng Việt không kết thúc bằng f/s/r/x/j; dd, aa, ee, oo, ow, uw, aw."""
    s = s.replace("dd", "d")
    s = re.sub(r"(aa|ee|oo)", lambda m: m.group(0)[0], s)
    s = re.sub(r"([aou])w", r"\1", s)
    return re.sub(r"\b([a-z]*[aeiouy][a-z]*?)[fsrxj]\b",
                  lambda m: m.group(1) if len(m.group(0)) > 2 else m.group(0), s)


def norm_question(q: str) -> str:
    s = _telex(_strip(q))
    s = re.sub(r"[?.,!:;\"'()]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


MONTH_RE = re.compile(r"\bthang (\d{1,2}) ?(?:/|-|nam) ?(\d{4})\b")

FILLER = set("""
doanh thu dthu dt doanhthu revenue tong cong total toan bo ca het
cua cua hang quan tiem shop ban duoc dc ban ra thu ve thu duoc mang ve tien hang
bao nhieu nhieu nhiu bnhiu bnhieu bn la the nao
trong cho hoi toi biet minh xem giup gium jum coi check e a oi ad em anh chi
z vay va nhi nha ne ha do ta the thi u nhe nhen nay a
""".split())
FILLER_PHRASES = ["cua hang", "thu ve", "thu duoc", "ban duoc", "ban ra", "tong cong", "bao nhieu",
                  "doanh thu", "cho hoi", "cho toi biet", "xem giup", "coi giup"]
CANCEL_FILLER = FILLER | set("don hoa bi huy da so may dem co".split()) - {"tien"}
QTY_FILLER = (FILLER | set("ban duoc dc ra may so luong tong cong mat san pham mon tat ca cac loai het xuat".split())) \
    - {"tien", "doanh", "thu", "dthu", "doanhthu", "revenue"}
QTY_RE = re.compile(r"\b(bao nhieu|may|so|bn|bnhiu|bnhieu|nhieu)\s+([a-z0-9]+)\b")
BO_QUA = "bo_qua"   # câu không phân tích chắc chắn được với dữ liệu của tiệm -> không chấm


def classify_question(q: str):
    """-> ('doanh_thu' | 'so_don_huy', thang, nam) hoặc None."""
    s = norm_question(q)
    m = MONTH_RE.search(s)
    if not m or len(MONTH_RE.findall(s)) != 1:
        return None
    month, year = int(m[1]), int(m[2])
    rest = (s[: m.start()] + " " + s[m.end():]).strip()
    words = rest.split()
    if "huy" in words and re.search(r"\b(bao nhieu|may|so|dem)\b.*\bdon\b|\bdon\b.*\bhuy\b", rest) \
            and not re.search(r"ti le|ty le|phan tram|%", rest):
        if all(w in CANCEL_FILLER for w in words):
            return "so_don_huy", month, year
        return None
    revenue = re.search(r"doanh thu|dthu|doanhthu|revenue|(ban|thu) (duoc|ve|ra).*tien|tien.*(ban|thu)", rest)
    shift = re.search(r"\bca (sang|chieu)\b", rest)
    if revenue and shift:   # doanh thu ca sáng / ca chiều (rulebook §2)
        words2 = (rest[: shift.start()] + " " + rest[shift.end():]).split()
        if all(w in FILLER for w in words2):
            return f"doanh_thu_ca_{shift[1]}", month, year
        return None
    if revenue:
        if all(w in FILLER for w in words):
            return "doanh_thu", month, year
        return None
    # số lượng bán <đơn vị> [<mặt hàng>] (rulebook §3) — đơn vị / mặt hàng tra theo dữ liệu tiệm lúc chấm
    if QTY_RE.search(rest) and re.search(r"\bban\b", rest) and \
            not re.search(r"%|phan tram|ti le|size|trung binh|\btien\b|\bdon\b", rest):
        return "so_luong", month, year, rest
    return None


# ---------------------------------------------------------------------------
# Tính từ bảng chuẩn
# ---------------------------------------------------------------------------

def _eligible_lines(don, dong, start, end):
    nd = pd.to_datetime(don["ngay_dat"], errors="coerce")
    ok = don[(nd >= start) & (nd <= end) & ~don["trang_thai"].isin([HUY, TRA_HANG])]
    return ok, dong[dong["ma_don"].isin(ok["ma_don"])]


def _quantity(tables: dict, rest: str, start, end):
    """Số lượng bán quy về đơn vị cơ bản (§3). Đơn vị và mặt hàng phải nhận ra được từ dữ liệu của tiệm."""
    from loader.parsers import nk
    mh, dong = tables.get("mat_hang"), tables["dong_hang"]
    if mh is None or "so_luong_co_ban" not in dong or dong["so_luong_co_ban"].isna().all():
        return "unanswerable"
    m = QTY_RE.search(rest)
    unit = m[2]
    units = {norm_question(u) for col in ("don_vi_co_ban",) for u in mh[col].dropna().astype(str)}
    if unit not in {u.split()[0] for u in units if u}:
        return BO_QUA
    keys = {}
    for code, name in zip(mh["ma_hang"], mh["ten_hang"]):
        if isinstance(name, str) and name.strip():
            keys.setdefault(norm_question(name), set()).add(code)
    text = " " + rest + " "
    found = [k for k in keys if k and f" {k} " in text]
    item_key = max(found, key=len) if found else None
    left = text.replace(f" {item_key} ", " ") if item_key else text
    left = left.replace(m[0], " ")
    if not all(w in QTY_FILLER for w in left.split()):
        return BO_QUA
    base = {c: (norm_question(u) if isinstance(u, str) else "") for c, u in zip(mh["ma_hang"], mh["don_vi_co_ban"])}
    if item_key:
        codes = keys[item_key]
        if any(base.get(c, "").split()[:1] != [unit] for c in codes):
            return BO_QUA   # hỏi theo đơn vị khác đơn vị cơ bản của hàng: luật chưa rõ -> không chấm
    else:
        codes = {c for c, b in base.items() if b and b.split()[0] == unit}
    _ok, lines = _eligible_lines(tables["don_hang"], dong, start, end)
    lines = lines[lines["ma_hang"].isin(codes) & lines["loai_dong"].isin(["hang"])]
    return round(float(pd.to_numeric(lines["so_luong_co_ban"], errors="coerce").sum()), 6)


def _shift_revenue(tables: dict, shift: str, start, end):
    """Doanh thu ca sáng (06:00–13:59) / ca chiều (14:00–21:59) theo giờ tạo đơn (§2)."""
    don, dong = tables["don_hang"], tables["dong_hang"]
    if "thoi_diem_dat" not in don or don["thoi_diem_dat"].isna().all():
        return "unanswerable"
    ok, lines = _eligible_lines(don, dong, start, end)
    h = pd.to_datetime(ok["thoi_diem_dat"], errors="coerce").dt.hour
    sel = ok[(h >= 6) & (h < 14)] if shift == "sang" else ok[(h >= 14) & (h < 22)]
    lines = lines[lines["ma_don"].isin(sel["ma_don"]) & lines["loai_dong"].isin(REVENUE_LINE_KINDS)]
    return round(float(pd.to_numeric(lines["thanh_tien"], errors="coerce").sum()))


def compute(tables: dict, kind: str, month: int, year: int, rest: str = ""):
    don, dong, ch = tables["don_hang"], tables["dong_hang"], tables["cua_hang"]
    start = pd.Timestamp(year, month, 1)
    end = start + pd.offsets.MonthEnd(0)
    d0, d1 = ch.get("ngay_bat_dau_du_lieu"), ch.get("ngay_ket_thuc_du_lieu") or ch.get("ngay_cuoi_trong_du_lieu")
    if d0 is None:
        return None
    if end < pd.Timestamp(d0) or start > pd.Timestamp(d1):
        return "unanswerable"
    nd = pd.to_datetime(don["ngay_dat"], errors="coerce")
    in_month = don[(nd >= start) & (nd <= end)]
    if kind == "so_don_huy":
        return int((in_month["trang_thai"] == HUY).sum())
    if kind.startswith("doanh_thu_ca_"):
        return _shift_revenue(tables, kind.rsplit("_", 1)[1], start, end)
    if kind == "so_luong":
        return _quantity(tables, rest, start, end)
    ok = in_month[~in_month["trang_thai"].isin([HUY, TRA_HANG])]
    if len(dong):
        lines = dong[dong["ma_don"].isin(ok["ma_don"]) & dong["loai_dong"].isin(REVENUE_LINE_KINDS)]
        return round(float(pd.to_numeric(lines["thanh_tien"], errors="coerce").sum()))
    tth = pd.to_numeric(ok["tong_tien_hang"], errors="coerce")
    if don["tong_tien_hang"].isna().all():
        return None   # không có dòng hàng cũng không có tiền hàng của đơn: không tính được (không trả 0)
    return round(float(tth.sum()))


def load_cached(cache_dir: Path) -> dict:
    return {"don_hang": pd.read_parquet(cache_dir / "don_hang.parquet", columns=[
                "ma_don", "ngay_dat", "trang_thai", "tong_tien_hang", "thoi_diem_dat"]),
            "dong_hang": pd.read_parquet(cache_dir / "dong_hang.parquet", columns=[
                "ma_don", "loai_dong", "thanh_tien", "ma_hang", "so_luong_co_ban"]),
            "mat_hang": pd.read_parquet(cache_dir / "mat_hang.parquet", columns=["ma_hang", "ten_hang", "don_vi_co_ban"]),
            "cua_hang": json.loads((cache_dir / "cua_hang.json").read_text(encoding="utf-8"))}


def gold_questions(train_dir: Path = Path("train")) -> list[dict]:
    qs = [json.loads(l) for l in open(train_dir / "questions.jsonl", encoding="utf-8")]
    ans = {a["id"]: a for a in (json.loads(l) for l in open(train_dir / "answers.jsonl", encoding="utf-8"))}
    out = []
    for q in qs:
        c = classify_question(q["question"])
        if c is None:
            continue
        g = ans[q["id"]]
        if g["type"] not in ("number", "unanswerable"):
            continue
        out.append({**q, "loai": c[0], "thang": c[1], "nam": c[2], "rest": c[3] if len(c) > 3 else "",
                    "gold_type": g["type"], "gold": g["answer"]})
    return out


def evaluate(get_tables, questions: list[dict], shops: set | None = None) -> dict:
    """get_tables(business_id) -> dict bảng (hoặc None nếu tiệm không nạp được)."""
    by_shop = defaultdict(list)
    cache = {}
    for q in questions:
        bid = q["business_id"]
        if shops is not None and bid not in shops:
            continue
        if bid not in cache:
            cache[bid] = get_tables(bid)
        t = cache[bid]
        got = None if t is None else compute(t, q["loai"], q["thang"], q["nam"], q.get("rest", ""))
        if got == BO_QUA:
            continue
        gold = "unanswerable" if q["gold_type"] == "unanswerable" else q["gold"]
        ok = got == gold if isinstance(gold, str) or not isinstance(got, (int, float)) else abs(got - gold) <= 1e-6
        by_shop[bid].append({**q, "tinh_duoc": got, "khop": bool(ok)})
    return dict(by_shop)


BASIC = ("doanh_thu", "so_don_huy")
EXTENDED = ("doanh_thu_ca_sang", "doanh_thu_ca_chieu", "so_luong")


def summary_rows(by_shop: dict, kinds=BASIC) -> list[tuple]:
    rows = []
    for bid in sorted(by_shop):
        items = [i for i in by_shop[bid] if i["loai"] in kinds]
        if not items:
            continue
        n = len(items)
        k = sum(i["khop"] for i in items)
        rows.append((bid, n, k, 100 * k / n if n else 0.0))
    return rows


def _section(by_shop: dict, kinds, title: str, cols: list[tuple[str, tuple]]) -> list[str]:
    rows = summary_rows(by_shop, kinds)
    tot_n, tot_k = sum(r[1] for r in rows), sum(r[2] for r in rows)
    L = [f"## {title}", "", f"**Tổng: {tot_k}/{tot_n} câu khớp ({100 * tot_k / max(tot_n, 1):.1f}%), "
                            f"{len(rows)} tiệm.**", "",
         "| tiệm | số câu | khớp | % | " + " | ".join(c for c, _k in cols) + " |",
         "|---|---|---|---|" + "---|" * len(cols)]
    for bid, n, k, pct in rows:
        cells = []
        for _c, ks in cols:
            it = [i for i in by_shop[bid] if i["loai"] in ks]
            cells.append(f"{sum(i['khop'] for i in it)}/{len(it)}")
        L.append(f"| {bid} | {n} | {k} | {pct:.0f}% | " + " | ".join(cells) + " |")
    L += ["", "| tiệm | loại | tháng | đáp án | tính được | chênh | câu hỏi |", "|---|---|---|---|---|---|---|"]
    for bid in sorted(by_shop):
        for i in by_shop[bid]:
            if i["khop"] or i["loai"] not in kinds:
                continue
            diff = ""
            if isinstance(i["gold"], (int, float)) and isinstance(i["tinh_duoc"], (int, float)):
                diff = f"{i['tinh_duoc'] - i['gold']:+,}"
            L.append(f"| {bid} | {i['loai']} | {i['thang']}/{i['nam']} | "
                     f"{i['gold'] if i['gold'] is not None else 'unanswerable'} | {i['tinh_duoc']} | {diff} | "
                     f"{i['question'][:70]} |")
    return L + [""]


def write_report(by_shop: dict, path: Path, title: str = "Kiểm tra loader bằng đáp án train") -> None:
    L = [f"# {title}", "",
         "Lọc câu bằng danh sách trắng (xem `check_with_gold.py`); câu không phân tích chắc chắn được với dữ liệu "
         "của tiệm thì không chấm. Khớp = bằng tuyệt đối với answers.jsonl.", ""]
    L += _section(by_shop, BASIC, "Cơ bản: doanh thu tháng, số đơn huỷ tháng",
                  [("doanh thu", ("doanh_thu",)), ("huỷ", ("so_don_huy",))])
    L += _section(by_shop, EXTENDED, "Mở rộng: doanh thu ca sáng/chiều (§2), số lượng bán (§3)",
                  [("ca sáng", ("doanh_thu_ca_sang",)), ("ca chiều", ("doanh_thu_ca_chieu",)),
                   ("số lượng", ("so_luong",))])
    path.write_text("\n".join(L), encoding="utf-8")


def _print(by_shop, kinds, label):
    rows = summary_rows(by_shop, kinds)
    tot_n, tot_k = sum(r[1] for r in rows), sum(r[2] for r in rows)
    print(f"== {label}")
    for bid, n, k, pct in rows:
        print(f"{bid:8s} {n:4d} {k:5d} {pct:5.0f}%")
    print(f"TỔNG {label}: {tot_k}/{tot_n} = {100 * tot_k / max(tot_n, 1):.1f}%; "
          f"tiệm >= 90%: {sum(r[3] >= 90 for r in rows)}/{len(rows)}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="cache")
    ap.add_argument("--out", default="gold_report.md")
    args = ap.parse_args(argv)
    qs = gold_questions()
    cache = Path(args.cache)

    def get(bid):
        p = cache / bid
        return load_cached(p) if (p / "don_hang.parquet").exists() else None

    by_shop = evaluate(get, qs)
    _print(by_shop, EXTENDED, "mở rộng (ca, số lượng)")
    _print(by_shop, BASIC, "cơ bản (doanh thu, huỷ)")
    write_report(by_shop, Path(args.out))
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
