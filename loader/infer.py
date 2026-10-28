"""Suy vai trò cột từ GIÁ TRỊ (bằng chứng số học) — dùng khi tên cột mơ hồ hoặc chưa ánh xạ được.

Mọi hàm là hàm thuần trên DataFrame (đã parse theo ô), trả về Inference kèm chuỗi bằng chứng.
Bằng chứng dưới ngưỡng -> trả None (để unmapped), không đoán.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

CODE_RE = re.compile(r"^[A-Za-z]{1,6}[-_]?\d{2,}$")


@dataclass
class Inference:
    col: str
    concept: str
    evidence: str
    mode: str = ""          # thông tin thêm (vd mã đơn 'dien_xuong' / 'theo_sheet')


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _sample(df: pd.DataFrame, n: int = 5000) -> pd.DataFrame:
    if len(df) <= n:
        return df
    return df.iloc[np.linspace(0, len(df) - 1, n).astype(int)]


def _intlike_share(s: pd.Series) -> float:
    s = _num(s).dropna()
    return float((np.abs(s - np.round(s)) < 1e-9).mean()) if len(s) else 0.0


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


# ---------------------------------------------------------------------------
# Bộ ba số lượng × đơn giá ≈ thành tiền
# ---------------------------------------------------------------------------

def qty_price_amount(df: pd.DataFrame, numeric_cols: list[str], fixed: dict[str, str] | None = None,
                     min_rows: int = 30, min_ok: float = 0.95, min_exact: float = 0.5) -> list[Inference]:
    """Tìm bộ cột (q, p, a) thoả a ≈ q × p (cho phép a <= q × p do giảm giá, a >= 50% q × p) ở >= 95% dòng
    và khớp ĐÚNG ở >= 50% dòng. q: số nguyên nhỏ; p, a: tiền. `fixed` = vai trò đã biết {khái niệm: cột}.
    Trả về Inference cho các cột CHƯA nằm trong `fixed`."""
    fixed = fixed or {}
    d = _sample(df[[c for c in dict.fromkeys(numeric_cols + list(fixed.values())) if c in df]])
    num = {c: _num(d[c]) for c in d.columns}
    med = {c: float(num[c].abs().median()) if num[c].notna().any() else 0.0 for c in d.columns}
    q_c = [c for c in d.columns if _intlike_share(num[c]) >= 0.95 and 0 < med[c] <= 1000]
    m_c = [c for c in d.columns if med[c] >= 100]
    if "so_luong" in fixed:
        q_c = [fixed["so_luong"]]
    p_c = [fixed["don_gia"]] if "don_gia" in fixed else m_c
    a_c = [fixed["thanh_tien"]] if "thanh_tien" in fixed else m_c
    best = None
    for q in q_c:
        for p in p_c:
            for a in a_c:
                if len({q, p, a}) < 3:
                    continue
                m = num[q].notna() & num[p].notna() & num[a].notna()
                n = int(m.sum())
                if n < min_rows:
                    continue
                qv, pv, av = num[q][m].to_numpy(), num[p][m].to_numpy(), num[a][m].to_numpy()
                if (np.abs(qv) > 1).mean() < 0.02:   # cần dòng SL > 1 để phân biệt đơn giá với thành tiền
                    continue
                prod = qv * pv
                exact = np.abs(av - prod) <= 1
                ok = exact | ((av <= prod + 1) & (av >= 0.5 * prod) & (prod > 0))
                r_ok, r_ex = float(ok.mean()), float(exact.mean())
                if r_ok >= min_ok and r_ex >= min_exact and (best is None or (r_ok, r_ex) > best[0]):
                    best = ((r_ok, r_ex), q, p, a, n)
    if best is None:
        return []
    (r_ok, r_ex), q, p, a, n = best
    ev = f"SL×đơn giá≈thành tiền ở {_pct(r_ok)} dòng (khớp đúng {_pct(r_ex)}, n={n}); bộ cột ({q}, {p}, {a})"
    out = []
    for col, concept in ((q, "so_luong"), (p, "don_gia"), (a, "thanh_tien")):
        if fixed.get(concept) != col:
            out.append(Inference(col, concept, ev))
    return out


# ---------------------------------------------------------------------------
# Số lượng cơ bản
# ---------------------------------------------------------------------------

def base_quantity(df: pd.DataFrame, qty_col: str, cand_cols: list[str], group_cols: list[str],
                  min_rows: int = 30) -> Inference | None:
    """Cột số c là số lượng quy về đơn vị cơ bản nếu tỉ số c / SL là số nguyên >= 1 ở >= 99% dòng,
    bằng 1 ở >= 20% dòng, > 1 ở >= 1% dòng, và HẰNG theo (mặt hàng, đơn vị) ở >= 99% dòng."""
    if not group_cols:
        return None
    best = None
    for c in cand_cols:
        if c == qty_col:
            continue
        q, v = _num(df[qty_col]), _num(df[c])
        m = q.notna() & v.notna() & (q != 0)
        for g in group_cols:
            m &= df[g].notna()
        n = int(m.sum())
        if n < min_rows:
            continue
        r = (v[m] / q[m]).round(9)
        integral = ((r >= 1 - 1e-9) & (np.abs(r - r.round()) < 1e-9)).mean()
        one, many = (r == 1).mean(), (r > 1).mean()
        if integral < 0.99 or one < 0.2 or many < 0.01:
            continue
        key = df.loc[m, group_cols].astype(str).agg("|".join, axis=1)
        tmp = pd.DataFrame({"k": key.to_numpy(), "r": r.to_numpy()})
        mode_r = tmp.groupby("k")["r"].agg(lambda s: s.value_counts().index[0])
        consistent = float((tmp["r"].to_numpy() == tmp["k"].map(mode_r).to_numpy()).mean())
        if consistent >= 0.99 and (best is None or consistent > best[0]):
            best = (consistent, c, integral, one, n)
    if best is None:
        return None
    consistent, c, integral, one, n = best
    return Inference(c, "so_luong_co_ban",
                     f"{c}/SL là số nguyên ở {_pct(integral)} dòng, =1 ở {_pct(one)}, hằng theo "
                     f"({', '.join(group_cols)}) ở {_pct(consistent)} dòng (n={n})")


# ---------------------------------------------------------------------------
# Ngày / thời điểm
# ---------------------------------------------------------------------------

def time_share(s: pd.Series) -> float:
    d = pd.to_datetime(s, errors="coerce").dropna()
    if not len(d):
        return 0.0
    return float(((d.dt.hour + d.dt.minute + d.dt.second) > 0).mean())


def datetime_roles(df: pd.DataFrame, date_cols: list[str], need_date: bool, need_time: bool) -> list[Inference]:
    """Cột kiểu ngày: có giờ khác 00:00 ở >= 50% dòng -> thời điểm đặt; chỉ ngày (< 1% có giờ) -> ngày đặt.
    Chỉ gán khi có ĐÚNG một cột ứng viên cho mỗi vai trò."""
    out = []
    shares = {c: time_share(df[c]) for c in date_cols}
    with_time = [c for c, s in shares.items() if s >= 0.5]
    date_only = [c for c, s in shares.items() if s < 0.01]
    if need_time and len(with_time) == 1:
        c = with_time[0]
        out.append(Inference(c, "thoi_diem_dat", f"{_pct(shares[c])} giá trị có giờ khác 00:00"))
    if need_date and len(date_only) == 1:
        c = date_only[0]
        out.append(Inference(c, "ngay_dat", f"cột ngày duy nhất không có giờ ({_pct(1 - shares[c])} giá trị 00:00)"))
    return out


# ---------------------------------------------------------------------------
# Mã đơn
# ---------------------------------------------------------------------------

def order_id(df: pd.DataFrame, cand_cols: list[str], seg: pd.Series, date_col: str | None = None,
             min_groups: int = 10) -> Inference | None:
    """Cột mã đơn của một sổ dòng hàng chưa có mã đơn. Hai dạng:
      'lap'        : giá trị ghi ở mọi dòng, lặp lại thành NHÓM LIỀN KỀ (>= 98% giá trị chỉ xuất hiện một khúc);
      'dien_xuong' : chỉ ghi ở dòng đầu nhóm (5–95% ô trống), giá trị KHÔNG lặp trong cùng sheet (>= 99%).
    Cả hai: ngày (nếu có) HẰNG trong nhóm ở >= 98% nhóm, số nhóm >= min_groups.
    Không có cột ngày thì chỉ nhận cột dạng mã (CODE123)."""
    seg = seg.astype(str).reset_index(drop=True)
    d = df.reset_index(drop=True)
    best = None
    for c in cand_cols:
        s = d[c]
        nn = s.notna()
        if nn.sum() < min_groups:
            continue
        key = s.map(lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA
                    else (str(int(v)) if isinstance(v, (float, np.floating)) and float(v).is_integer() else str(v)))
        is_code = key.dropna().str.fullmatch(CODE_RE).mean() >= 0.8
        empty = 1 - nn.mean()
        if empty <= 0.02:
            mode = "lap"
            nun = key.groupby(seg).nunique().sum()
            ratio = nun / len(key)
            if not (0.01 <= ratio <= 0.9):
                continue
            change = (key != key.shift()) | (seg != seg.shift())
            runs = int(change.sum())
            contiguity = nun / runs if runs else 0
            if contiguity < 0.98:
                continue
            groups = pd.Series(list(zip(seg, key)))
            n_groups = int(nun)
            ev_shape = f"{n_groups} nhóm, {_pct(contiguity)} giá trị chỉ nằm trong một khúc liền kề"
        elif 0.05 <= empty <= 0.95:
            mode = "dien_xuong"
            vals = pd.DataFrame({"seg": seg[nn], "k": key[nn]})
            uniq = 1 - vals.duplicated(["seg", "k"]).mean()
            if uniq < 0.99:
                continue
            first_ok = d.groupby(seg)[c].apply(lambda x: pd.notna(x.iloc[0])).mean()
            if first_ok < 0.9:
                continue
            block = nn.astype(int).groupby(seg).cumsum()
            groups = pd.Series(list(zip(seg, block)))
            n_groups = int(nn.sum())
            ev_shape = (f"{n_groups} nhóm, ghi ở dòng đầu nhóm ({_pct(empty)} ô trống), "
                        f"không lặp trong sheet ở {_pct(uniq)} giá trị")
        else:
            continue
        if n_groups < min_groups:
            continue
        if date_col is not None:
            dd = pd.to_datetime(d[date_col], errors="coerce").dt.normalize()
            tmp = pd.DataFrame({"g": groups.astype(str), "d": dd})
            const = float((tmp.dropna().groupby("g")["d"].nunique() <= 1).mean()) if tmp["d"].notna().any() else 0
            if const < 0.98:
                continue
            ev = f"{ev_shape}; ngày hằng trong {_pct(const)} nhóm"
        elif is_code:
            const, ev = 1.0, f"{ev_shape}; giá trị dạng mã (không có cột ngày để đối chiếu)"
        else:
            continue
        score = (const, is_code, mode == "lap", n_groups)
        if best is None or score > best[0]:
            scope = "theo_sheet" if not is_code else ""
            best = (score, Inference(c, "ma_don", ev, mode=f"{mode}{'+' + scope if scope else ''}"))
    return best[1] if best else None


# ---------------------------------------------------------------------------
# Khoá trùng với danh sách khác (mã khách, mã nhân viên...)
# ---------------------------------------------------------------------------

def key_overlap(df: pd.DataFrame, cand_cols: list[str], ref: set, concept: str, ref_name: str,
                min_ratio: float = 0.9, min_values: int = 5) -> Inference | None:
    """Cột có >= 90% giá trị (khác rỗng) nằm trong tập khoá `ref` của bảng danh sách."""
    if len(ref) < min_values:
        return None
    best = None
    for c in cand_cols:
        vals = df[c].dropna().astype(str).str.strip()
        vals = vals[vals != ""]
        if len(vals) < min_values:
            continue
        r = float(vals.isin(ref).mean())
        if r >= min_ratio and (best is None or r > best[0]):
            best = (r, c, len(vals))
    if best is None:
        return None
    r, c, n = best
    return Inference(c, concept, f"{_pct(r)} giá trị ({n} ô) nằm trong khoá của {ref_name}")


# ---------------------------------------------------------------------------
# Sổ phiếu (mỗi dòng một giao dịch) — khi tiệm không có bảng bán nào nhận ra được
# ---------------------------------------------------------------------------

def ledger_columns(df: pd.DataFrame, kinds: dict[str, str], min_rows: int = 30) -> list[Inference]:
    """Bảng có ĐÚNG một cột ngày và ĐÚNG một cột tiền (số, trung vị >= 1.000, >= 90% ô có giá trị)
    -> sổ ghi mỗi dòng một phiếu: cột ngày = ngày, cột tiền = tiền phiếu."""
    if len(df) < min_rows:
        return []
    dates = [c for c, k in kinds.items() if k == "date"]
    money = [c for c, k in kinds.items() if k == "number" and _num(df[c]).notna().mean() >= 0.9
             and _num(df[c]).abs().median() >= 1000]
    if len(dates) != 1 or len(money) != 1:
        return []
    ev = (f"bảng có đúng 1 cột ngày ({dates[0]}) và 1 cột tiền ({money[0]}, trung vị "
          f"{_num(df[money[0]]).median():,.0f}), không có mã tham chiếu đơn -> mỗi dòng một phiếu")
    concept_date = "thoi_diem_dat" if time_share(df[dates[0]]) >= 0.5 else "ngay_dat"
    return [Inference(dates[0], concept_date, ev), Inference(money[0], "thanh_tien", ev)]


# ---------------------------------------------------------------------------
# Giảm giá dòng; phí giao / giảm giá đơn (cân bằng số học)
# ---------------------------------------------------------------------------

def line_discount(df: pd.DataFrame, q: str, p: str, a: str, cand_cols: list[str],
                  min_rows: int = 30) -> Inference | None:
    """Cột d là giảm giá dòng nếu thành tiền = SL × đơn giá − d ở >= 98% dòng và d > 0 ở >= 1% dòng
    (nếu d luôn 0 thì không đủ bằng chứng)."""
    best = None
    for d in cand_cols:
        if d in (q, p, a):
            continue
        qv, pv, av, dv = (_num(df[c]) for c in (q, p, a, d))
        m = qv.notna() & pv.notna() & av.notna() & dv.notna()
        n = int(m.sum())
        if n < min_rows:
            continue
        ok = (np.abs(qv[m] * pv[m] - dv[m] - av[m]) <= 1).mean()
        nz = (dv[m] > 0).mean()
        if ok >= 0.98 and nz >= 0.01 and (best is None or ok > best[0]):
            best = (ok, d, nz, n)
    if best is None:
        return None
    ok, d, nz, n = best
    return Inference(d, "giam_gia_dong", f"thành tiền = SL×đơn giá − {d} ở {_pct(ok)} dòng ({d} > 0 ở {_pct(nz)}, n={n})")


def order_balance(df: pd.DataFrame, total_goods: str, payable: str, discount: str | None, cand_cols: list[str],
                  min_rows: int = 30) -> list[Inference]:
    """Cân bằng cấp đơn: phải trả = tiền hàng − giảm giá đơn + phí giao.
    Tìm cột chưa biết x: (a) phí giao nếu phải trả = tiền hàng − giảm + x; (b) giảm giá đơn (khi chưa có)
    nếu phải trả = tiền hàng − x. Cần đúng ở >= 98% dòng và x > 0 ở >= 1% dòng."""
    T, P = _num(df[total_goods]), _num(df[payable])
    G = _num(df[discount]).fillna(0) if discount else pd.Series(0, index=df.index)
    out = []
    for concept, sign in (("phi_giao", +1), ("giam_gia_don", -1)):
        if concept == "giam_gia_don" and discount:
            continue
        best = None
        for x in cand_cols:
            if x in (total_goods, payable, discount):
                continue
            X = _num(df[x])
            m = T.notna() & P.notna() & X.notna()
            n = int(m.sum())
            if n < min_rows:
                continue
            ok = (np.abs(T[m] - G[m] + sign * X[m] - P[m]) <= 1).mean()
            nz = (X[m] > 0).mean()
            if ok >= 0.98 and nz >= 0.01 and (best is None or ok > best[0]):
                best = (ok, x, nz, n)
        if best:
            ok, x, nz, n = best
            sym = "+" if sign > 0 else "−"
            out.append(Inference(x, concept, f"phải trả = tiền hàng − giảm giá đơn {sym} {x} ở {_pct(ok)} dòng "
                                             f"({x} > 0 ở {_pct(nz)}, n={n})"))
            break
    if out or discount:
        return out
    # cả giảm giá đơn lẫn phí giao đều chưa biết: thử từng CẶP (g, s) với phải trả = tiền hàng − g + s
    cols = [c for c in cand_cols if c not in (total_goods, payable)]
    best = None
    for g in cols:
        for sh in cols:
            if g == sh:
                continue
            Gv, Sv = _num(df[g]), _num(df[sh])
            m = T.notna() & P.notna() & Gv.notna() & Sv.notna()
            n = int(m.sum())
            if n < min_rows:
                continue
            ok = (np.abs(T[m] - Gv[m] + Sv[m] - P[m]) <= 1).mean()
            nzg, nzs = (Gv[m] > 0).mean(), (Sv[m] > 0).mean()
            if ok >= 0.98 and nzg >= 0.01 and nzs >= 0.01 and (best is None or ok > best[0]):
                best = (ok, g, sh, n)
    if best:
        ok, g, sh, n = best
        ev = f"phải trả = tiền hàng − {g} + {sh} ở {_pct(ok)} dòng (n={n})"
        out = [Inference(g, "giam_gia_don", ev), Inference(sh, "phi_giao", ev)]
    return out
