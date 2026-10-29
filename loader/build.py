"""Dựng 5 bảng chuẩn cho MỘT tiệm: cua_hang, don_hang, dong_hang, mat_hang, quy_doi_don_vi.

Quy trình (không có logic riêng cho tiệm nào):
  1. Bảng thô sạch cho mọi file/sheet (raw.py).
  2. Mỗi cột -> các khái niệm ứng viên, theo thứ tự ưu tiên:
       (a)+(b) mô tả cột trong README của tiệm -> từ điển mô tả        [trọng số 3]
       (c)     tên cột -> từ điển tên cột (đếm trên README train)      [<= 2; tiền tố ký tự 0.95]
               tên cột sau khi BUNG VIẾT TẮT (abbrev.py) -> từ điển   [<= 1.5, chia cho số cách bung; nguồn 'abbrev*']
               cặp '**X** là ...' trong phần Quy ước của README        [1.5; 3 nếu chỉ rõ `bang.cot`]
       (d)     không có -> unmapped
  3. Vai trò của bảng (dòng hàng / đơn / mặt hàng / quy đổi / bảng lô / khác) suy từ tập khái niệm.
  4. Chốt khái niệm từng cột theo vai trò, kiểm tra kiểu dữ liệu (cột tiền phải là số, cột ngày phải là ngày).
  5. Suy theo CẤU TRÚC (ghi rõ nguồn 'cau_truc_*'), chỉ cho cột khoá và ngày đặt của sổ bán:
       - cột khoá (mã đơn / mã hàng) chưa ánh xạ: cột có tập giá trị trùng >= 90% với khoá đã biết ở bảng khác;
       - sổ bán chưa có ngày đặt: đúng một cột kiểu ngày có tên gợi ý ngày.
  5b. Suy từ GIÁ TRỊ (infer.py, nguồn 'gia_tri_*', bằng chứng ghi vào mapping.json) — chỉ lấp cột chưa ánh xạ
      hoặc ánh xạ yếu (< 1): ngày/thời điểm, SL×giá≈tiền, giảm giá dòng, phí giao/giảm giá đơn (cân bằng),
      SL cơ bản, mã đơn (nhóm liền kề / điền xuống), mã khách/NV (trùng danh sách), sổ phiếu (ngày + tiền).
  6. Dựng bảng chuẩn (+ khach_hang, nối nhóm khách vào đơn; tách topping ghép ô) + metadata năng lực (nang_luc).
"""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .mapping import (CONVERSION_CONCEPTS, DATE_CONCEPTS, LINE_CONCEPTS, NON_SALES, NUMERIC_CONCEPTS,
                      ORDER_CONCEPTS, PRODUCT_CONCEPTS, ROLE_ALLOWED, ROLE_SPECIFIC, Dictionaries,
                      build_dictionaries, default_train_readmes)
from .infer import (Inference, base_quantity, datetime_roles, key_overlap, ledger_columns, line_discount,
                    order_balance, order_id, qty_price_amount)
from .parsers import (HOAN_THANH, HUY, TRA_HANG, clean_str, col_key, combine_status, is_walkin, line_kind,
                      name_key, nk, normalize_channel, normalize_payment, normalize_status, parse_quantity,
                      split_phone, split_topping, status_from_text)
from .raw import RawTable, fill_down_raw, read_raw_tables, type_table
from .readme import ReadmeInfo, parse_readme

CODE_CONCEPTS = {"ma_don", "ma_hang", "ma_khach", "ma_nhan_vien", "ma_ban", "ma_lo"}
WEAK = 1.0   # trọng số < WEAK: ánh xạ yếu (tiền tố, viết tắt mơ hồ, cấu trúc) — lớp suy từ giá trị được phép thay


@dataclass
class TableMap:
    table: RawTable
    role: str
    cols: dict[str, tuple[str, str, float, str | None]] = field(default_factory=dict)  # col -> (concept, nguồn, w, mô tả)
    unmapped: list[str] = field(default_factory=list)
    descs: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)   # cột -> bằng chứng số học (lớp suy từ giá trị)
    id_scope: str = ""        # 'segment': mã đơn là số thứ tự trong sheet -> ghép tên sheet cho khỏi trùng

    def col_of(self, concept: str) -> str | None:
        for c, (k, *_rest) in self.cols.items():
            if k == concept:
                return c
        return None

    def concepts(self) -> set[str]:
        return {v[0] for v in self.cols.values()}


# ---------------------------------------------------------------------------
# 2. Ứng viên khái niệm cho từng cột
# ---------------------------------------------------------------------------

def _candidates(t: RawTable, readme: ReadmeInfo, dicts: Dictionaries):
    src0 = t.sources[0] if t.sources else {}
    file, sheet = src0.get("file", ""), src0.get("sheet")
    sec = readme.section_for(file, sheet, t.columns)
    sec_by_key = {col_key(c): d for c, d in sec.columns.items()} if sec else {}
    is_sqlite = Path(file).suffix.lower() in (".sqlite", ".sqlite3", ".db")
    out, descs = {}, {}
    for c in t.columns:
        if t.kinds.get(c) == "empty":
            continue
        cands = []
        desc = sec_by_key.get(col_key(c))
        if desc:
            descs[c] = desc
            k, how = dicts.concept_of_desc(desc)
            if k:
                cands.append((k, 3.0, how, desc))
        for k, w, how in dicts.name_candidates(c):
            cands.append((k, w, how, None))
        conv = readme.convention_desc(c, table=sheet if is_sqlite else None)
        if conv:
            descs.setdefault(c, conv)
            k, how = dicts.concept_of_desc(conv)
            if k:
                scoped = any(p.table and col_key(p.column) == col_key(c) for p in readme.convention_pairs)
                cands.append((k, 3.0 if scoped else 1.5, "quy_uoc_readme", conv))
        if cands:
            out[c] = sorted(cands, key=lambda x: -x[1])
    return out, descs


# ---------------------------------------------------------------------------
# 3. Vai trò bảng
# ---------------------------------------------------------------------------

def _role(t: RawTable, cands: dict, readme: ReadmeInfo) -> str:
    top = {cs[0][0] for cs in cands.values() if cs[0][1] >= 0.9}
    hang = top & {"ten_hang", "ma_hang"}
    src_names = {Path(s["file"]).stem.lower() for s in t.sources} | {str(s.get("sheet") or "").lower() for s in t.sources}
    # README chỉ ra nơi ghi hệ số ('hệ số quy đổi ở `X`'); X có thể là cả file nhiều sheet,
    # nên chỉ nhận bảng có tên gợi ý quy đổi
    pointed = any(Path(x).stem.lower() in src_names for x in readme.conversion_sources) and \
        re.search(r"quydoi|donvi|heso", col_key(t.name)) is not None
    sale_like = bool(hang) and bool(top & {"thanh_tien"}) and bool(top & {"so_luong", "don_gia", "ma_don", "ngay_dat"})
    if "ma_don" not in top and not sale_like and (top & {"he_so", "don_vi_lon", "ten_hang_qd"} or pointed):
        return "conversion"
    if "ma_don" in top and top & {"so_luong_tra", "ma_lo", "sl_lo"} and not hang:
        return "lot_sale"
    if top & {"ton_kho"}:
        return "inventory"
    if top & NON_SALES:
        # bảng thu tiền phải tham chiếu được tới đơn (mã đơn / mã phiếu thu)
        if top & {"so_tien_thu", "thoi_diem_thu", "ma_phieu_thu"} and top & {"ma_don", "ma_phieu_thu"}:
            return "payment"
        if top & {"ngay_nhap", "ma_phieu_nhap", "gia_nhap", "so_luong_nhap", "thanh_tien_nhap", "tong_tien_phieu_nhap"}:
            return "import"
        if top & {"ma_lo", "han_su_dung", "sl_nhap_co_ban"}:
            return "lot"
        if top & {"dot_giao", "ngay_giao", "bien_so", "tai_xe"}:
            return "delivery"
        if top & {"so_ngay_no", "han_thanh_toan"}:
            return "debt_term"
        if top & {"ngay_ap_dung", "gia_moi", "gia_cu"}:
            return "price"
        return "other"
    sale_marks = top & {"ma_don", "ngay_dat", "trang_thai", "thoi_diem_dat"}
    if hang and top & {"thanh_tien", "so_luong", "don_gia", "so_luong_co_ban"} and sale_marks:
        return "line"
    if sale_like:  # tên hàng + thành tiền + số lượng/đơn giá: sổ bán dù chưa nhận ra mã đơn / ngày
        return "line"
    # 'trang_thai' một mình không đủ (danh sách khách cũng có cột Trạng thái tài khoản)
    if not hang and top & {"ma_don", "ngay_dat", "tong_phai_tra", "tong_tien_hang", "hinh_thuc_tt"} \
            and len(top & ORDER_CONCEPTS) >= 3:
        return "order"
    if (hang or "ten" in top) and top & {"nhom_hang", "don_vi_co_ban", "don_vi", "gia_ban_hien_tai", "gia_von",
                                          "hoat_chat", "ke_don"}:
        return "product"
    if top & {"ma_khach", "ten", "ten_khach"} and top & {"sdt", "nhom_khach", "dia_chi"}:
        return "customer"
    if "ma_nhan_vien" in top and "ma_don" not in top:
        return "staff"
    return "other"


# ---------------------------------------------------------------------------
# 4. Chốt khái niệm theo vai trò + kiểm tra kiểu
# ---------------------------------------------------------------------------

def _type_ok(t: RawTable, col: str, concept: str) -> bool:
    kind = t.kinds.get(col)
    if concept in NUMERIC_CONCEPTS:
        return kind == "number"
    if concept in DATE_CONCEPTS:
        return kind == "date"
    return True


def _resolve(t: RawTable, role: str, cands: dict) -> dict:
    allowed = ROLE_ALLOWED.get(role)
    if role == "inventory":
        allowed = PRODUCT_CONCEPTS | {"ton_kho", "don_vi"}
    spec = ROLE_SPECIFIC.get(role, {})
    options = {}
    for c, cs in cands.items():
        opts = []
        for k, w, how, d in cs:
            k = spec.get(k, k)
            if allowed is not None and k not in allowed:
                continue
            if not _type_ok(t, c, k):
                continue
            opts.append((k, w, how, d))
        if opts:
            options[c] = opts
    if allowed is None:  # vai trò 'khác': giữ khái niệm mạnh nhất để báo cáo
        return {c: (os[0][0], os[0][2], os[0][1], os[0][3]) for c, os in options.items()}
    chosen, idx = {}, {c: 0 for c in options}
    changed = True
    while changed:
        changed = False
        by_concept = defaultdict(list)
        for c, i in idx.items():
            if i < len(options[c]):
                by_concept[options[c][i][0]].append(c)
        for k, cols in by_concept.items():
            if len(cols) > 1:
                fill = {c: t.typed[c].notna().mean() for c in cols}
                cols.sort(key=lambda c: (-options[c][idx[c]][1], -fill[c]))
                for c in cols[1:]:
                    idx[c] += 1
                    changed = True
    for c, i in idx.items():
        if i < len(options[c]):
            k, w, how, d = options[c][i]
            chosen[c] = (k, how, w, d)   # (khái niệm, nguồn, trọng số, mô tả)
    return chosen


def _structural_date(tm: TableMap) -> None:
    """Sổ bán chưa có ngày đặt: xét các cột kiểu ngày chưa ánh xạ có tên gợi ý ngày/giờ
    (nguồn 'cau_truc_kieu_ngay'). Một cột -> ngày đặt. Nhiều cột: nếu đúng một cột chỉ có ngày (không giờ)
    thì đó là ngày đặt, và nếu đúng một cột có giờ thì đó là thời điểm đặt. Còn lại: không đoán."""
    if tm.role not in ("line", "order") or tm.col_of("ngay_dat"):
        return
    t = tm.table
    cand = [c for c in t.columns if c not in tm.cols and t.kinds.get(c) == "date"
            and re.search(r"ngay|thoigian|date|gio|time", col_key(c))]
    if not cand:
        return
    if len(cand) == 1:
        tm.cols[cand[0]] = ("ngay_dat", "cau_truc_kieu_ngay", 0.5, None)
        return

    def has_time(c):
        s = pd.to_datetime(t.typed[c], errors="coerce").dropna()
        return len(s) > 0 and ((s.dt.hour + s.dt.minute + s.dt.second) > 0).mean() > 0.5
    date_only = [c for c in cand if not has_time(c)]
    with_time = [c for c in cand if has_time(c)]
    if len(date_only) == 1:
        tm.cols[date_only[0]] = ("ngay_dat", "cau_truc_kieu_ngay", 0.5, None)
        if len(with_time) == 1 and not tm.col_of("thoi_diem_dat"):
            tm.cols[with_time[0]] = ("thoi_diem_dat", "cau_truc_kieu_ngay", 0.5, None)


def _as_key(s: pd.Series) -> pd.Series:
    """Cột khoá -> chuỗi đã strip ('ORD001', 12.0 -> '12')."""
    def f(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
            return None
        if isinstance(v, (float, np.floating)) and float(v).is_integer():
            return str(int(v))
        return clean_str(v)
    return s.map(f).astype(object)


def _structural_keys(tms: list[TableMap]) -> None:
    """Cột khoá chưa ánh xạ: cột chữ có >= 90% giá trị nằm trong tập khoá đã biết ở bảng khác."""
    for concept, roles_need, roles_ref in (("ma_don", ("order", "line", "lot_sale"), ("line", "order", "payment")),
                                           ("ma_hang", ("product", "line", "conversion", "inventory"),
                                            ("line", "product"))):
        ref = set()
        for tm in tms:
            c = tm.col_of(concept)
            if tm.role in roles_ref and c:
                ref |= set(_as_key(tm.table.typed[c]).dropna())
        # số thứ tự thuần (1, 2, 3...) trùng với cột số nào cũng được -> không phải bằng chứng
        if len(ref) < 5 or sum(str(v).isdigit() for v in ref) / len(ref) >= 0.5:
            continue
        for tm in tms:
            if tm.role not in roles_need or tm.col_of(concept):
                continue
            best, best_r = None, 0.0
            for c in tm.table.columns:
                if c in tm.cols or tm.table.kinds.get(c) == "empty":
                    continue
                vals = _as_key(tm.table.typed[c]).dropna()
                if len(vals) < 5:
                    continue
                r = vals.isin(ref).mean()
                if r > best_r:
                    best, best_r = c, r
            if best is not None and best_r >= 0.9:
                tm.cols[best] = (concept, "cau_truc_trung_gia_tri", 0.5, None)


# ---------------------------------------------------------------------------
# 4b. Lớp suy từ GIÁ TRỊ (infer.py) — chỉ lấp cột chưa ánh xạ / ánh xạ yếu, luôn kèm bằng chứng
# ---------------------------------------------------------------------------

def _assign(tm: TableMap, inf: Inference, source: str) -> bool:
    """Gán khái niệm suy từ giá trị. Không đè ánh xạ mạnh; nếu khái niệm đang nằm ở cột khác với ánh xạ yếu
    thì gỡ ở cột đó."""
    cur = tm.cols.get(inf.col)
    if cur and cur[2] >= WEAK and cur[0] != inf.concept:
        return False
    other = tm.col_of(inf.concept)
    if other and other != inf.col:
        if tm.cols[other][2] >= WEAK:
            return False
        del tm.cols[other]
        tm.evidence.pop(other, None)
    tm.cols[inf.col] = (inf.concept, source, 0.9, None)
    tm.evidence[inf.col] = inf.evidence
    return True


def _free_cols(tm: TableMap, kinds: tuple[str, ...]) -> list[str]:
    """Cột chưa ánh xạ hoặc ánh xạ yếu, theo kiểu dữ liệu."""
    t = tm.table
    return [c for c in t.columns if t.kinds.get(c) in kinds and (c not in tm.cols or tm.cols[c][2] < WEAK)]


def _strong(tm: TableMap, concept: str) -> str | None:
    c = tm.col_of(concept)
    return c if c and tm.cols[c][2] >= WEAK else None


def _value_layer(tms: list[TableMap]) -> None:
    for tm in tms:
        if tm.role not in ("line", "order"):
            continue
        t, df = tm.table, tm.table.typed
        # (1) ngày / thời điểm
        need_time, need_date = not tm.col_of("thoi_diem_dat"), not tm.col_of("ngay_dat")
        if need_time or need_date:
            for inf in datetime_roles(df, _free_cols(tm, ("date",)), need_date, need_time):
                _assign(tm, inf, "gia_tri_thoi_diem")
        # (0) kiểm chứng ánh xạ YẾU bằng đẳng thức: giảm giá dòng phải thoả thành tiền = SL × đơn giá − d
        q0, p0, a0, gd = (tm.col_of(k) for k in ("so_luong", "don_gia", "thanh_tien", "giam_gia_dong"))
        if gd and tm.cols[gd][2] < WEAK and q0 and p0 and a0 and line_discount(df, q0, p0, a0, [gd]) is None:
            tm.evidence[gd] = f"gỡ ánh xạ yếu giam_gia_dong: không thoả thành tiền = SL×đơn giá − {gd}"
            del tm.cols[gd]
        # (1b) cân bằng cấp đơn: phí giao / giảm giá đơn
        tg, pt = tm.col_of("tong_tien_hang"), tm.col_of("tong_phai_tra")
        if tg and pt and not (tm.col_of("phi_giao") and tm.col_of("giam_gia_don")):
            used = {c for c, v in tm.cols.items() if v[2] >= WEAK}
            for inf in order_balance(df, tg, pt, tm.col_of("giam_gia_don"),
                                     [c for c in _free_cols(tm, ("number",)) if c not in used]):
                _assign(tm, inf, "gia_tri_can_bang_don")
        if tm.role != "line":
            continue
        # (2) bộ ba số lượng × đơn giá ≈ thành tiền
        fixed = {k: _strong(tm, k) for k in ("so_luong", "don_gia", "thanh_tien") if _strong(tm, k)}
        if len(fixed) < 3:
            free = _free_cols(tm, ("number",))
            for inf in qty_price_amount(df, free, fixed):
                _assign(tm, inf, "gia_tri_bo_ba")
        # (2b) giảm giá dòng: thành tiền = SL × đơn giá − d
        q, p, a = tm.col_of("so_luong"), tm.col_of("don_gia"), tm.col_of("thanh_tien")
        if q and p and a and not tm.col_of("giam_gia_dong"):
            inf = line_discount(df, q, p, a, [c for c in _free_cols(tm, ("number",)) if c not in (q, p, a)])
            if inf:
                _assign(tm, inf, "gia_tri_giam_gia_dong")
        # (3) số lượng cơ bản
        q = tm.col_of("so_luong")
        if q and not tm.col_of("so_luong_co_ban"):
            groups = [c for c in (tm.col_of("ma_hang") or tm.col_of("ten_hang"), tm.col_of("don_vi")) if c]
            inf = base_quantity(df, q, [c for c in _free_cols(tm, ("number",)) if c != q], groups if len(groups) == 2 else [])
            if inf:
                _assign(tm, inf, "gia_tri_sl_co_ban")
        # (4) mã đơn
        if not tm.col_of("ma_don"):
            cand = [c for c in _free_cols(tm, ("text", "number")) if c not in (q, tm.col_of("don_gia"),
                                                                                tm.col_of("thanh_tien"))]
            cand += [c for c, v in tm.cols.items() if v[0] == "stt_dong" and c not in cand]
            date_col = tm.col_of("ngay_dat") or tm.col_of("thoi_diem_dat")
            seg = df["__file"].astype(str) + "|" + df["__sheet"].astype(str)
            inf = order_id(df[cand + ([date_col] if date_col else [])], cand, seg, date_col)
            if inf:
                if tm.cols.get(inf.col, ("",))[0] == "stt_dong":
                    del tm.cols[inf.col]
                if _assign(tm, inf, "gia_tri_ma_don") and "theo_sheet" in inf.mode:
                    tm.id_scope = "segment"

    # (5) mã khách / mã nhân viên: trùng khoá của bảng danh sách khách / nhân viên
    for concept, ref_role in (("ma_khach", "customer"), ("ma_nhan_vien", "staff")):
        ref, ref_name = set(), []
        for tm in tms:
            c = tm.col_of(concept)
            if tm.role == ref_role and c:
                ref |= set(_as_key(tm.table.typed[c]).dropna())
                ref_name.append(tm.table.name)
        for tm in tms:
            if tm.role not in ("line", "order") or tm.col_of(concept):
                continue
            inf = key_overlap(tm.table.typed, _free_cols(tm, ("text",)), ref, concept, "/".join(ref_name))
            if inf:
                _assign(tm, inf, "gia_tri_trung_khoa")

    # (6) tiệm không có bảng bán nào nhận ra được: sổ ghi mỗi dòng một phiếu (ngày + tiền)
    if not any(tm.role in ("line", "order") for tm in tms):
        cands = []
        for tm in tms:
            # bảng tác nghiệp KHÔNG tham chiếu mã đơn (giao hàng / hạn nợ / thu tiền thật thì phải có mã đơn);
            # không xét danh mục, nhập hàng, bảng giá, lô, tồn kho
            if tm.role not in ("other", "payment", "delivery", "debt_term") or tm.col_of("ma_don"):
                continue
            kinds = {c: k for c, k in tm.table.kinds.items() if k in ("date", "number")}
            infs = ledger_columns(tm.table.typed, kinds)
            if infs:
                cands.append((len(tm.table.typed), tm, infs))
        if cands:
            _n, tm, infs = max(cands, key=lambda x: x[0])
            keep = {c: v for c, v in tm.cols.items() if v[0] in ("ghi_chu", "trang_thai")}
            tm.role, tm.cols, tm.evidence = "line", keep, {}
            for inf in infs:
                _assign(tm, inf, "gia_tri_so_phieu")


def map_tables(tables: list[RawTable], readme: ReadmeInfo, dicts: Dictionaries) -> list[TableMap]:
    tms = []
    for t in tables:
        if t.typed is None:
            continue
        cands, descs = _candidates(t, readme, dicts)
        role = _role(t, cands, readme)
        tm = TableMap(table=t, role=role, descs=descs)
        tm.cols = _resolve(t, role, cands)
        tms.append(tm)
    _structural_keys(tms)
    _value_layer(tms)
    _structural_keys(tms)   # lần 2: khoá vừa suy ở bảng dòng hàng làm tham chiếu cho bảng khác
    for tm in tms:
        _structural_date(tm)
        tm.unmapped = [c for c in tm.table.columns if c not in tm.cols and tm.table.kinds.get(c) != "empty"]
    return tms


# ---------------------------------------------------------------------------
# 5. Dựng bảng chuẩn
# ---------------------------------------------------------------------------

def _frame(tm: TableMap, concepts: set[str]) -> pd.DataFrame:
    """Lấy các cột đã ánh xạ (thuộc `concepts`) của bảng, giá trị đã parse; thêm nguon, __file, __sheet, __row."""
    t = tm.table
    df = pd.DataFrame(index=t.typed.index)
    for c, (k, *_r) in tm.cols.items():
        if k in concepts:
            s = t.typed[c]
            df[k] = _as_key(s) if k in CODE_CONCEPTS else s
    for m in ("__file", "__sheet", "__row"):
        df[m] = t.typed[m]
    df["nguon"] = t.typed["__file"].astype(str) + "|" + t.typed["__sheet"].fillna("").astype(str)
    if tm.id_scope == "segment" and "ma_don" in df:   # số thứ tự đơn trong từng sheet -> ghép tên sheet
        df["ma_don"] = [None if v is None else f"{n}#{v}" for v, n in zip(df["ma_don"], df["nguon"])]
    return df


def _fill_order_level(df: pd.DataFrame, order_cols: list[str]) -> pd.DataFrame:
    """Điền xuống các cột cấp đơn (rulebook §8):
    - dòng trống mã đơn: lấy giá trị của dòng đầu nhóm (dòng có mã đơn gần nhất phía trên, trong cùng sheet);
    - dòng có mã đơn nhưng trống cột cấp đơn: lấy giá trị đầu tiên khác rỗng của cùng mã đơn."""
    if "ma_don" not in df or df["ma_don"].isna().all():
        return df
    seg = df["nguon"]
    block = df["ma_don"].notna().astype(int).groupby(seg).cumsum()
    need = df["ma_don"].isna() & (block > 0)
    if need.any():
        for c in ["ma_don"] + [c for c in order_cols if c != "ma_don"]:
            first = df.groupby([seg, block], sort=False)[c].transform("first")
            df.loc[need, c] = first[need]
    for c in order_cols:
        if c == "ma_don" or not df[c].isna().any():
            continue
        df[c] = df[c].fillna(df.groupby("ma_don", sort=False)[c].transform("first"))
    return df


def _unit_key(u) -> str | None:
    s = clean_str(u)
    return name_key(s) if s else None


class ProductIndex:
    """Nối tên hàng -> mã hàng: khớp chữ thường + khoảng trắng, sau đó khớp bỏ dấu nếu duy nhất."""

    def __init__(self):
        self.exact: dict[str, str] = {}
        self.loose: dict[str, set] = defaultdict(set)

    @staticmethod
    def k_exact(s: str) -> str:
        return re.sub(r"\s+", " ", clean_str(s).lower())

    def add(self, name, code):
        if clean_str(name) is None or code is None:
            return
        self.exact.setdefault(self.k_exact(name), code)
        self.loose[name_key(name)].add(code)

    def find(self, name):
        if clean_str(name) is None:
            return None
        c = self.exact.get(self.k_exact(name))
        if c:
            return c
        s = self.loose.get(name_key(name))
        return next(iter(s)) if s and len(s) == 1 else None


def _ke_don(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    k = name_key(str(v))
    if k in ("true", "1", "co", "x", "yes", "ke don"):
        return True
    if k in ("false", "0", "khong", "no"):
        return False
    return None


def build_products(tms: list[TableMap], readme: ReadmeInfo):
    """mat_hang + quy_doi_don_vi."""
    recs: dict[str, dict] = {}
    idx = ProductIndex()
    fields = ["ten_hang", "nhom_hang", "don_vi_co_ban", "gia_ban_hien_tai", "gia_von", "hoat_chat", "ke_don"]

    def upsert(code, row, nguon):
        r = recs.setdefault(code, {"ma_hang": code, "nguon": nguon})
        for f in fields:
            v = row.get(f)
            if r.get(f) is None and v is not None and not (isinstance(v, float) and np.isnan(v)) and v is not pd.NA:
                r[f] = v
        if row.get("ten_hang") is not None:
            idx.add(row["ten_hang"], code)

    # danh mục hàng trước, bảng tồn kho sau (tên trong danh mục là tên chuẩn)
    for tm in sorted([x for x in tms if x.role in ("product", "inventory")], key=lambda x: x.role != "product"):
        df = _frame(tm, PRODUCT_CONCEPTS)
        for row in df.to_dict("records"):
            code = row.get("ma_hang")
            if code is None:
                code = idx.find(row.get("ten_hang")) if row.get("ten_hang") else None
            if code is None and row.get("ten_hang"):
                code = "TEN:" + name_key(row["ten_hang"])
            if code is None:
                continue
            if "ke_don" in row:
                row["ke_don"] = _ke_don(row["ke_don"])
            upsert(code, row, row["nguon"])

    # quy đổi: từ bảng quy đổi + từ README
    conv_rows = []  # (code|None, ten|None, don_vi_lon, he_so_raw, don_vi_nho, nguon)
    for tm in [x for x in tms if x.role == "conversion"]:
        t = tm.table
        df = _frame(tm, CONVERSION_CONCEPTS)
        unit_col = next((k for k in ("don_vi_lon", "don_vi") if k in df), None)
        small_col = "don_vi_co_ban" if "don_vi_co_ban" in df and unit_col != "don_vi_co_ban" else None
        if unit_col is None and "don_vi_co_ban" in df:
            unit_col = "don_vi_co_ban"
        hs = df["he_so"] if "he_so" in df else None
        if hs is None:  # bảng quy đổi do README chỉ ra nhưng cột hệ số không có tên quen: cột số nguyên nhỏ (cấu trúc)
            num_cols = [c for c in t.columns if c not in tm.cols and t.kinds.get(c) == "number"]
            for c in num_cols:
                s = t.typed[c].dropna()
                if len(s) and (s >= 1).all() and (s % 1 == 0).all() and s.median() < 1000:
                    hs = t.typed[c]
                    tm.cols[c] = ("he_so", "cau_truc_so_nguyen_nho", 0.5, None)
                    tm.unmapped = [x for x in tm.unmapped if x != c]
                    break
            if hs is None:  # hệ số dạng chữ ('2 vỉ'): cột chữ chưa ánh xạ có số đứng đầu
                for c in [c for c in t.columns if c not in tm.cols]:
                    s = t.data[c].dropna()
                    if len(s) and s.map(lambda v: parse_quantity(v)[0] is not None).mean() >= 0.95:
                        hs = t.data[c]
                        tm.cols[c] = ("he_so", "cau_truc_so_kem_don_vi", 0.5, None)
                        break
        if hs is None or unit_col is None:
            continue
        raw_hs = t.data[hs.name] if hs.name in t.data else hs
        for i, row in enumerate(df.to_dict("records")):
            conv_rows.append((row.get("ma_hang"), row.get("ten_hang"), row.get(unit_col), raw_hs.iloc[i],
                              row.get(small_col) if small_col else None, row["nguon"]))
    for u in readme.conversions:
        conv_rows.append((None, u.ten_hang, u.don_vi_lon, u.he_so, u.don_vi_nho, "README"))

    # gắn mã cho dòng quy đổi; thêm mặt hàng nếu chưa có
    resolved = []
    for code, ten, lon, hs, nho, nguon in conv_rows:
        if code is None and ten:
            code = idx.find(ten) or "TEN:" + name_key(ten)
            if code not in recs:
                upsert(code, {"ten_hang": ten, "don_vi_co_ban": nho}, nguon)
        if code is None or clean_str(lon) is None:
            continue
        if nho and recs.get(code, {}).get("don_vi_co_ban") is None:
            recs.setdefault(code, {"ma_hang": code, "nguon": nguon})["don_vi_co_ban"] = nho
        resolved.append((code, lon, hs, nguon))

    # hệ số nhiều cấp: '2 vỉ' = 2 x hệ số của vỉ
    factors: dict[tuple, float] = {}
    pending = list(resolved)
    for _ in range(5):
        nxt = []
        for code, lon, hs, nguon in pending:
            q, unit = parse_quantity(hs)
            if q is None:
                continue
            if unit is None:
                factors[(code, _unit_key(lon))] = (float(q), nguon)
            else:
                base = recs.get(code, {}).get("don_vi_co_ban")
                if base is not None and _unit_key(unit) == _unit_key(base):
                    factors[(code, _unit_key(lon))] = (float(q), nguon)
                elif (code, _unit_key(unit)) in factors:
                    factors[(code, _unit_key(lon))] = (float(q) * factors[(code, _unit_key(unit))][0], nguon)
                else:
                    nxt.append((code, lon, hs, nguon))
        if not nxt or len(nxt) == len(pending):
            break
        pending = nxt

    mat_hang = pd.DataFrame(list(recs.values()))
    for f in ["ma_hang"] + fields + ["nguon"]:
        if f not in mat_hang:
            mat_hang[f] = None
    unit_names = {}
    for code, lon, _hs, _n in resolved:
        unit_names.setdefault((code, _unit_key(lon)), clean_str(lon))
    qrows = [{"ma_hang": code, "don_vi": unit_names.get((code, uk), uk), "he_so_co_ban": f, "nguon": n}
             for (code, uk), (f, n) in factors.items()]
    for r in recs.values():
        if r.get("don_vi_co_ban"):
            qrows.append({"ma_hang": r["ma_hang"], "don_vi": clean_str(r["don_vi_co_ban"]), "he_so_co_ban": 1.0,
                          "nguon": "don_vi_co_ban"})
    quy_doi = pd.DataFrame(qrows, columns=["ma_hang", "don_vi", "he_so_co_ban", "nguon"]).drop_duplicates(
        subset=["ma_hang", "don_vi"])
    return mat_hang, quy_doi, idx, recs


def build_customers(tms: list[TableMap]) -> pd.DataFrame:
    """Danh sách khách (bảng vai trò 'customer'): mã, tên (đã tách SĐT), SĐT, nhóm, địa chỉ."""
    parts = []
    for tm in [x for x in tms if x.role == "customer"]:
        df = _frame(tm, ROLE_ALLOWED["customer"])
        if "ten_khach" in df:
            sp = df["ten_khach"].map(split_phone)
            df["ten_khach"] = [n for n, _p in sp]
            ph = pd.Series([p for _n, p in sp], index=df.index)
            df["sdt"] = df["sdt"].map(lambda v: None if v is None or v != v else str(v)) if "sdt" in df else ph
            df["sdt"] = df["sdt"].fillna(ph)
        parts.append(df)
    cols = ["ma_khach", "ten_khach", "sdt", "nhom_khach", "dia_chi", "nguon"]
    if not parts:
        return pd.DataFrame(columns=cols)
    out = pd.concat(parts, ignore_index=True)
    for c in cols:
        if c not in out:
            out[c] = None
    return out[cols]


def _join_customers(orders: pd.DataFrame, customers: pd.DataFrame, co_ma_khach: bool):
    """Nối danh sách khách vào đơn: theo mã khách; tiệm không có mã khách thì theo tên (khớp khoá tên, duy nhất).
    Chỉ lấp ô còn trống; tên khách chỉ bổ sung khi nối theo mã duy nhất.
    Không thay tên gốc, định danh hoặc phân loại khách lẻ của đơn."""
    fill_columns = ("nhom_khach", "sdt_khach", "dia_chi_khach")
    for c in fill_columns:
        if c not in orders:
            orders[c] = None
    if not len(customers) or not len(orders):
        return orders, 0
    cust = customers.rename(columns={"sdt": "sdt_khach", "dia_chi": "dia_chi_khach"})
    if co_ma_khach and cust["ma_khach"].notna().any():
        key_o, key_c = orders["ma_khach"], cust["ma_khach"]
        fill_columns = ("ten_khach", *fill_columns)
        if "ten_khach" not in orders:
            orders["ten_khach"] = None
    else:
        key_o = orders["khach_key"]
        key_c = cust["ten_khach"].map(nk)
    cust = cust.assign(_k=key_c.values).dropna(subset=["_k"])
    cust = cust[~cust["_k"].duplicated(keep=False)].set_index("_k")   # chỉ nhận khoá duy nhất
    n = 0
    for c in fill_columns:
        if c in cust:
            filled = key_o.map(cust[c])
            n = max(n, int((orders[c].isna() & filled.notna()).sum()))
            orders[c] = orders[c].where(orders[c].notna(), filled)
    return orders, n


def _split_toppings(lines: pd.DataFrame):
    """Topping ghi chung ô với món ('Trà sữa (M) + 2 Trân châu (10.000)') -> thêm dòng topping riêng,
    trừ tiền topping khỏi thành tiền của món (tổng tiền dòng giữ nguyên). Không tách nếu tiền âm."""
    if "ten_hang" not in lines or "thanh_tien" not in lines or not len(lines):
        return lines, 0
    mask = lines["ten_hang"].astype("string").str.contains(" + ", regex=False, na=False)
    if not mask.any():
        return lines, 0
    new_rows, n = [], 0
    for i in lines.index[mask]:
        sp = split_topping(lines.at[i, "ten_hang"])
        tt = pd.to_numeric(pd.Series([lines.at[i, "thanh_tien"]]), errors="coerce").iloc[0]
        if sp is None or pd.isna(tt):
            continue
        main, tops = sp
        rest = float(tt) - sum(m for _t, _q, m in tops)
        if rest < -1:
            continue
        lines.at[i, "ten_hang"] = main
        lines.at[i, "thanh_tien"] = rest
        for name, qty, money in tops:
            r = lines.loc[i].to_dict()
            r.update({"ten_hang": name, "so_luong": qty, "so_luong_co_ban": qty, "don_vi": None,
                      "don_gia": money / qty, "thanh_tien": money, "giam_gia_dong": None, "gia_von_dong": None,
                      "stt_dong": None, "ma_hang": None, "_topping": True})
            new_rows.append(r)
        n += 1
    if new_rows:
        lines = pd.concat([lines, pd.DataFrame(new_rows)], ignore_index=True)
    return lines, n


def build_sales(tms: list[TableMap], idx: ProductIndex, recs: dict, quy_doi: pd.DataFrame):
    """don_hang + dong_hang."""
    customers = build_customers(tms)
    line_tms = [tm for tm in tms if tm.role == "line"]
    order_tms = [tm for tm in tms if tm.role == "order"]
    lot_tms = [tm for tm in tms if tm.role == "lot_sale"]
    info = {"co_ma_don": False, "co_ma_hang": False, "dedup": 0, "khong_quy_doi": 0, "dong_hang_khong_ma": 0,
            "nguon_trang_thai": None}

    # ---- dòng hàng
    parts = []
    for tm in line_tms:
        df = _frame(tm, LINE_CONCEPTS | ORDER_CONCEPTS)
        has_id = "ma_don" in df and df["ma_don"].notna().any()
        if has_id:
            info["co_ma_don"] = True
            order_cols = [c for c in df.columns if c in ORDER_CONCEPTS]
            df = _fill_order_level(df, order_cols)
            # khử dòng trùng trong cùng đơn (sau điền xuống), so mọi cột gốc
            key_cols = [c for c in df.columns if c not in ("__row",)] + \
                [c for c in tm.unmapped if c in tm.table.typed]
            keyframe = pd.concat([df[[c for c in df.columns if c not in ("__row",)]],
                                  tm.table.typed[[c for c in tm.unmapped]]], axis=1).astype(str)
            dup = keyframe.duplicated(keep="first") & df["ma_don"].notna()
            info["dedup"] += int(dup.sum())
            df = df[~dup]
        else:  # sổ không ghi mã đơn: mỗi dòng một lần bán, KHÔNG khử trùng (§8)
            df["ma_don"] = "R:" + df["nguon"] + "|" + df["__row"].astype(str)
        parts.append(df)
    lines = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["ma_don"])
    lines, info["topping_tach"] = _split_toppings(lines)

    # ---- đơn
    oparts = []
    for tm in order_tms:
        df = _frame(tm, ORDER_CONCEPTS)
        if "ma_don" not in df:
            continue
        info["co_ma_don"] = True
        oparts.append(df[df["ma_don"].notna()])
    otab = pd.concat(oparts, ignore_index=True) if oparts else pd.DataFrame(columns=["ma_don"])
    otab = otab.drop_duplicates(subset=["ma_don"], keep="first")

    # trạng thái từ dòng (nếu sổ ghi trạng thái theo dòng)
    if len(lines):
        if "so_luong" in lines:
            lines["so_luong"] = pd.to_numeric(lines["so_luong"], errors="coerce")
        lines["_st"] = lines["trang_thai"].map(normalize_status) if "trang_thai" in lines else None

    agg_cols = [c for c in ORDER_CONCEPTS if c in lines.columns and c != "ma_don"]
    if len(lines):
        pos = lines if "so_luong" not in lines else lines[~(lines["so_luong"] < 0)]
        lagg = pos.groupby("ma_don", sort=False)[agg_cols + ["nguon"]].first() if agg_cols else \
            pos.groupby("ma_don", sort=False)[["nguon"]].first()
        rest = lines.groupby("ma_don", sort=False)[agg_cols + ["nguon"]].first() if agg_cols else \
            lines.groupby("ma_don", sort=False)[["nguon"]].first()
        lagg = lagg.combine_first(rest)
        if "trang_thai" in lines:
            lagg["_st_line"] = lines.groupby("ma_don", sort=False)["_st"].agg(lambda s: combine_status(s.tolist()))
        if "so_luong" in lines:
            lagg["_neg"] = lines.groupby("ma_don", sort=False)["so_luong"].agg(lambda s: bool((s < 0).any()))
    else:
        lagg = pd.DataFrame()

    o = otab.set_index("ma_don") if len(otab) else pd.DataFrame()
    orders = o.combine_first(lagg) if len(o) and len(lagg) else (o if len(o) else lagg)
    orders = orders.reset_index().rename(columns={"index": "ma_don"})
    if "ma_don" not in orders:
        orders["ma_don"] = []

    # trạng thái đơn
    st = pd.Series([None] * len(orders), index=orders.index, dtype=object)
    if "trang_thai" in orders and orders["trang_thai"].notna().any():
        st = orders["trang_thai"].map(normalize_status)
        info["nguon_trang_thai"] = "cot_trang_thai"
        if "_st_line" in orders:
            st = st.where(st.notna(), orders["_st_line"])
    elif "ghi_chu" in orders and orders["ghi_chu"].notna().any():
        st = orders["ghi_chu"].map(status_from_text)
        info["nguon_trang_thai"] = "ghi_chu"
    orders["trang_thai_goc"] = orders["trang_thai"] if "trang_thai" in orders else (
        orders["ghi_chu"] if info["nguon_trang_thai"] == "ghi_chu" else None)
    if info["nguon_trang_thai"] is None:
        info["nguon_trang_thai"] = "khong_co (coi là hoàn thành)"
    if info["nguon_trang_thai"] != "cot_trang_thai":
        st = st.fillna(HOAN_THANH)
    # trả hàng: dòng số lượng âm, hoặc bảng lô có số lượng trả > 0
    ret = set()
    if "_neg" in orders:
        ret |= set(orders.loc[orders["_neg"] == True, "ma_don"])  # noqa: E712
    for tm in lot_tms:
        df = _frame(tm, {"ma_don", "so_luong_tra"})
        if "ma_don" in df and "so_luong_tra" in df:
            ret |= set(df.loc[pd.to_numeric(df["so_luong_tra"], errors="coerce") > 0, "ma_don"].dropna())
    info["don_tra_tu_dong_am_hoac_lo"] = len(ret)
    mask_ret = orders["ma_don"].isin(ret) & (st != HUY)
    st = st.where(~mask_ret, TRA_HANG)
    orders["trang_thai"] = st

    # ngày / giờ
    if "ngay_dat" in orders:
        nd = pd.to_datetime(orders["ngay_dat"], errors="coerce")
        has_time = (nd.dropna().dt.hour + nd.dropna().dt.minute > 0).mean() if nd.notna().any() else 0
        if "thoi_diem_dat" not in orders and has_time > 0.5:
            orders["thoi_diem_dat"] = nd
        orders["ngay_dat"] = nd.dt.normalize()
    elif "thoi_diem_dat" in orders:
        orders["ngay_dat"] = pd.to_datetime(orders["thoi_diem_dat"], errors="coerce").dt.normalize()
    if "thoi_diem_dat" in orders:
        orders["thoi_diem_dat"] = pd.to_datetime(orders["thoi_diem_dat"], errors="coerce")

    # khách
    co_ma_khach = "ma_khach" in orders and orders["ma_khach"].notna().any()
    goc = orders["ten_khach"] if "ten_khach" in orders else pd.Series([None] * len(orders), index=orders.index)
    orders["ten_khach_goc"] = goc
    split = goc.map(lambda v: split_phone(v))
    orders["ten_khach"] = [None if is_walkin(n) else n for n, _p in split]
    if co_ma_khach:
        orders["la_khach_le"] = orders["ma_khach"].isna()
        orders["khach_key"] = orders["ma_khach"]
    else:
        orders["la_khach_le"] = orders["ten_khach"].isna()
        orders["khach_key"] = orders["ten_khach"].map(nk)
    if "hinh_thuc_tt" in orders:
        orders["hinh_thuc_tt_goc"] = orders["hinh_thuc_tt"]
        orders["hinh_thuc_tt"] = orders["hinh_thuc_tt"].map(normalize_payment)
    if "sdt" in orders:          # SĐT / địa chỉ ghi ngay trên đơn
        orders["sdt_khach"] = orders["sdt"].map(lambda v: None if v is None or v != v else str(v))
    if "dia_chi" in orders:
        orders["dia_chi_khach"] = orders["dia_chi"]
    if "kenh_ban" in orders:
        orders["kenh_ban_goc"] = orders["kenh_ban"]
        orders["kenh_ban"] = orders["kenh_ban"].map(normalize_channel)
    orders, info["khach_noi_duoc"] = _join_customers(orders, customers, co_ma_khach)

    # ---- hoàn thiện dòng hàng
    if len(lines):
        if "ma_hang" in lines and lines["ma_hang"].notna().any():
            info["co_ma_hang"] = True
        if "ma_hang" not in lines:
            lines["ma_hang"] = None
        if "ten_hang" in lines:
            miss = lines["ma_hang"].isna() & lines["ten_hang"].notna()
            lines.loc[miss, "ma_hang"] = lines.loc[miss, "ten_hang"].map(idx.find)
            if "_topping" in lines:   # tên topping trong ô ghép không kèm chữ 'Topping'
                tp = lines["_topping"].eq(True) & lines["ma_hang"].isna()
                lines.loc[tp, "ma_hang"] = lines.loc[tp, "ten_hang"].map(lambda n: idx.find(f"Topping {n}"))
            miss = lines["ma_hang"].isna() & lines["ten_hang"].notna()
            info["dong_hang_khong_ma"] = int(miss.sum())
            lines.loc[miss, "ma_hang"] = "TEN:" + lines.loc[miss, "ten_hang"].map(nk)
        names = {}
        if "ten_hang" in lines:
            names = lines.dropna(subset=["ma_hang", "ten_hang"]).groupby("ma_hang")["ten_hang"].agg(
                lambda s: s.value_counts().index[0]).to_dict()
        for code in lines["ma_hang"].dropna().unique():
            if code not in recs:
                recs[code] = {"ma_hang": code, "ten_hang": names.get(code), "nguon": "dong_hang"}
        # số lượng cơ bản
        if "so_luong_co_ban" not in lines:
            lines["so_luong_co_ban"] = np.nan
        lines["so_luong_co_ban"] = pd.to_numeric(lines["so_luong_co_ban"], errors="coerce")
        if "so_luong" not in lines:
            lines["so_luong"] = np.nan
        fac = {(r.ma_hang, _unit_key(r.don_vi)): r.he_so_co_ban for r in quy_doi.itertuples()}
        base = {k: _unit_key(v.get("don_vi_co_ban")) for k, v in recs.items()}

        def factor(code, unit):
            uk = _unit_key(unit)
            if uk is None:            # dòng không ghi đơn vị: không tra được hệ số
                return 1.0, False
            if base.get(code) == uk:
                return 1.0, True
            f = fac.get((code, uk))
            return (f, True) if f is not None else (1.0, False)
        units = lines["don_vi"] if "don_vi" in lines else pd.Series([None] * len(lines), index=lines.index)
        # đối chiếu: số lượng cơ bản ghi trong file / số lượng = hệ số tra được (kiểm tra mục e)
        src = lines["so_luong_co_ban"].notna() & lines["so_luong"].notna() & (lines["so_luong"] != 0)
        n_chk = n_ok = 0
        for c, u, a, b in zip(lines.loc[src, "ma_hang"], units[src], lines.loc[src, "so_luong_co_ban"],
                              lines.loc[src, "so_luong"]):
            f, found = factor(c, u)
            if found:
                n_chk += 1
                n_ok += abs(a / b - f) < 1e-6
        info["he_so_doi_chieu"], info["he_so_khop"] = n_chk, int(n_ok)
        # mặt hàng chưa có đơn vị cơ bản: lấy đơn vị của các dòng có SL cơ bản (ghi trong file) = SL
        # (bằng chứng: >= 95% các dòng như vậy của mặt hàng cùng một đơn vị)
        info["don_vi_co_ban_suy_tu_dong"] = 0
        if src.any() and "don_vi" in lines:  # noqa: SIM102
            one = lines[src & (np.abs(lines["so_luong_co_ban"] - lines["so_luong"]) < 1e-9)]
            for code, units_s in one.groupby("ma_hang")["don_vi"]:
                if code in recs and not clean_str(recs[code].get("don_vi_co_ban")):
                    vc = units_s.dropna().map(clean_str).value_counts()
                    if len(vc) and vc.iloc[0] / vc.sum() >= 0.95:
                        recs[code]["don_vi_co_ban"] = vc.index[0]
                        info["don_vi_co_ban_suy_tu_dong"] += 1
        # §10: mặt hàng không có dòng quy đổi nào -> mọi đơn vị bán là đơn vị cơ bản (hệ số 1);
        # nhận khi >= 95% dòng của mặt hàng cùng một đơn vị
        has_conv = set(quy_doi.loc[quy_doi["he_so_co_ban"] != 1, "ma_hang"]) if len(quy_doi) else set()
        if "don_vi" in lines:
            for code, units_s in lines.groupby("ma_hang")["don_vi"]:
                if code in recs and code not in has_conv and not clean_str(recs[code].get("don_vi_co_ban")):
                    vc = units_s.dropna().map(clean_str).value_counts()
                    if len(vc) and vc.iloc[0] / vc.sum() >= 0.95:
                        recs[code]["don_vi_co_ban"] = vc.index[0]
                        info["don_vi_co_ban_suy_tu_dong"] += 1
        base = {k: _unit_key(v.get("don_vi_co_ban")) for k, v in recs.items()}
        need = lines["so_luong_co_ban"].isna() & lines["so_luong"].notna()
        if need.any():
            res = [factor(c, u) for c, u in zip(lines.loc[need, "ma_hang"], units[need])]
            lines.loc[need, "so_luong_co_ban"] = lines.loc[need, "so_luong"].to_numpy() * np.array([r[0] for r in res])
            info["khong_quy_doi"] = int(sum(1 for r in res if not r[1]))
        name_src = lines["ten_hang"] if "ten_hang" in lines else lines["ma_hang"].map(
            lambda c: recs.get(c, {}).get("ten_hang"))
        lines["ten_hang_goc"] = name_src
        lines["loai_dong"] = name_src.map(line_kind)
        if "_topping" in lines:
            lines.loc[lines["_topping"].eq(True), "loai_dong"] = "topping"
    return orders, lines, info


DON_HANG_COLS = ["ma_don", "ngay_dat", "thoi_diem_dat", "trang_thai", "trang_thai_goc", "ma_khach", "ten_khach",
                 "ten_khach_goc", "la_khach_le", "khach_key", "nhom_khach", "sdt_khach", "dia_chi_khach",
                 "kenh_ban", "kenh_ban_goc", "hinh_thuc_tt", "hinh_thuc_tt_goc",
                 "ma_nhan_vien", "tong_tien_hang", "giam_gia_don", "phi_giao", "tong_phai_tra",
                 "con_no_cuoi_du_lieu", "ma_ban", "khu_vuc", "so_khach", "ma_khuyen_mai", "ghi_chu",
                 "thu_may_cu", "la_bao_hanh", "nguon"]
DONG_HANG_COLS = ["ma_don", "stt_dong", "ma_hang", "ten_hang_goc", "loai_dong", "so_luong", "don_vi",
                  "so_luong_co_ban", "don_gia", "giam_gia_dong", "thanh_tien", "gia_von_dong", "imei", "nguon"]
MAT_HANG_COLS = ["ma_hang", "ten_hang", "ten_khac", "nhom_hang", "don_vi_co_ban", "gia_ban_hien_tai", "gia_von",
                 "hang", "so_size", "loai", "con_kinh_doanh", "la_hang_che_bien", "hoat_chat", "ke_don", "nguon"]


def _select(df: pd.DataFrame, cols: list[str], rename: dict | None = None) -> pd.DataFrame:
    df = df.rename(columns=rename or {})
    for c in cols:
        if c not in df:
            df[c] = None
    return df[cols].reset_index(drop=True)


def _capabilities(orders, lines, mat_hang, quy_doi, tms, info) -> dict:
    def has(df, c):
        return c in df and df[c].notna().any()
    roles = Counter(tm.role for tm in tms)
    allc = set().union(*[tm.concepts() for tm in tms]) if tms else set()
    gio = has(orders, "thoi_diem_dat")
    return {
        "dong_hang": len(lines) > 0,
        "ma_don": info["co_ma_don"], "ma_hang": info["co_ma_hang"], "ma_khach": has(orders, "ma_khach"),
        "trang_thai": info["nguon_trang_thai"] in ("cot_trang_thai", "ghi_chu"),
        "gio_dat": gio,
        "ten_khach": has(orders, "ten_khach"), "nhom_khach": has(orders, "nhom_khach"),
        "kenh_ban": has(orders, "kenh_ban"), "hinh_thuc_tt": has(orders, "hinh_thuc_tt"),
        "nhan_vien": has(orders, "ma_nhan_vien"), "ban": has(orders, "ma_ban"),
        "tong_tien_hang": has(orders, "tong_tien_hang"), "giam_gia_don": has(orders, "giam_gia_don"),
        "tong_phai_tra": has(orders, "tong_phai_tra"), "con_no": has(orders, "con_no_cuoi_du_lieu"),
        "don_gia": has(lines, "don_gia"), "gia_von_dong": has(lines, "gia_von_dong"),
        "giam_gia_dong": has(lines, "giam_gia_dong"),
        "nhom_hang": has(mat_hang, "nhom_hang"), "gia_von_danh_muc": has(mat_hang, "gia_von"),
        "hoat_chat": has(mat_hang, "hoat_chat"), "ke_don": has(mat_hang, "ke_don"),
        "quy_doi": len(quy_doi[quy_doi["he_so_co_ban"] != 1]) > 0 if len(quy_doi) else False,
        # bảng khác (chưa dựng ở v0, chỉ ghi nhận có hay không)
        "thanh_toan": roles["payment"] > 0, "nhap_hang": roles["import"] > 0,
        "gia_nhap": bool(allc & {"gia_nhap", "thanh_tien_nhap", "tong_tien_phieu_nhap"}),
        "ton_kho": roles["inventory"] > 0, "lo_hang": bool(allc & {"ma_lo", "han_su_dung"}),
        "giao_hang": roles["delivery"] > 0, "han_no": roles["debt_term"] > 0, "bang_gia": roles["price"] > 0,
        "danh_sach_khach": roles["customer"] > 0, "dia_chi_khach": "dia_chi" in allc,
    }


def load_business(business_dir: str | Path, rulebook_path: str | Path | None = None,
                  dictionaries: Dictionaries | None = None, train_dir: str | Path = "train") -> dict:
    """Nạp một tiệm -> dict gồm 5 bảng chuẩn + metadata + bảng thô + ánh xạ + kiểm tra.

    `dictionaries`: từ điển ánh xạ; mặc định xây từ README của TRAIN (`train_dir`).
    """
    from .checks import run_checks

    t0 = time.time()
    business_dir = Path(business_dir)
    readme = parse_readme(business_dir / "README.md")
    if dictionaries is None:
        dictionaries = build_dictionaries(default_train_readmes(train_dir))
    rulebook = Path(rulebook_path).read_text(encoding="utf-8") if rulebook_path and Path(rulebook_path).exists() else ""

    tables, errors = read_raw_tables(business_dir)
    for t in tables:
        try:
            type_table(t)
        except Exception as e:  # noqa: BLE001
            t.error = f"{type(e).__name__}: {e}"
            errors.append({"bang": t.name, "loi": t.error})
    tms = map_tables(tables, readme, dictionaries)
    mat_hang, quy_doi, idx, recs = build_products(tms, readme)
    orders, lines, info = build_sales(tms, idx, recs, quy_doi)
    khach_hang = build_customers(tms)
    mat_hang = pd.DataFrame(list(recs.values()))

    don_hang = _select(orders, DON_HANG_COLS, {"con_no": "con_no_cuoi_du_lieu"})
    dong_hang = _select(lines, DONG_HANG_COLS)
    mat_hang = _select(mat_hang, MAT_HANG_COLS)

    nd = pd.to_datetime(don_hang["ngay_dat"], errors="coerce")
    cua_hang = {
        "business_id": business_dir.name,  # chỉ dùng làm nhãn / tên thư mục cache
        "ngay_bat_dau_du_lieu": nd.min().date().isoformat() if nd.notna().any() else None,
        "ngay_cuoi_trong_du_lieu": nd.max().date().isoformat() if nd.notna().any() else None,
        "ngay_ket_thuc_du_lieu": readme.end_date.isoformat() if readme.end_date else None,
        "co_ma_khach": bool(don_hang["ma_khach"].notna().any()),
        "co_ma_hang": info["co_ma_hang"], "co_ma_don": info["co_ma_don"],
        "nang_luc": _capabilities(orders, lines, mat_hang, quy_doi, tms, info),
        "nguon_trang_thai": info["nguon_trang_thai"],
        "rulebook": str(rulebook_path) if rulebook_path else None,
        "rulebook_so_ky_tu": len(rulebook),
        "thong_ke": {k: v for k, v in info.items() if k not in ("co_ma_don", "co_ma_hang", "nguon_trang_thai")},
    }

    for tm in tms:  # điền xuống cho bản parquet thô (sau khi đã dùng bản chưa điền để dựng bảng chuẩn)
        try:
            fill_down_raw(tm.table)
        except Exception as e:  # noqa: BLE001
            errors.append({"bang": tm.table.name, "loi": f"điền xuống: {e}"})

    result = {
        "cua_hang": cua_hang, "don_hang": don_hang, "dong_hang": dong_hang, "mat_hang": mat_hang,
        "khach_hang": khach_hang,
        "quy_doi_don_vi": quy_doi.reset_index(drop=True), "raw_tables": tables, "table_maps": tms,
        "readme": readme, "errors": errors,
    }
    result["checks"] = run_checks(result)
    result["thoi_gian_nap"] = round(time.time() - t0, 2)
    return result
