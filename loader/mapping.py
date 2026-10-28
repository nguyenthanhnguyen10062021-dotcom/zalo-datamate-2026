"""Từ điển ánh xạ cột -> khái niệm chuẩn.

Hai từ điển, đều XÂY TỪ README (hàm `build_dictionaries`, truyền vào danh sách README của TRAIN):
  * từ điển mô tả:  mô tả cột (đã chuẩn hoá) -> khái niệm
  * từ điển tên cột: khoá tên cột -> Counter(khái niệm)  (đếm số README dùng tên đó cho khái niệm đó)

Khái niệm của một mô tả được xác định bằng DESC_RULES: các quy tắc từ khoá viết ra từ bộ từ vựng
mô tả cột của README train (mỗi quy tắc phải khớp ít nhất một mô tả trong README train — có test).
Không có gì riêng cho tiệm nào.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .abbrev import accent_form, expand, has_accents, is_abbreviated
from .parsers import col_key, strip_accents
from .readme import ReadmeInfo, parse_readme

# (regex trên mô tả đã bỏ dấu + chữ thường, khái niệm). Thứ tự quan trọng: cụ thể trước, chung sau.
DESC_RULES: list[tuple[str, str]] = [
    (r"cot trong|khong co du lieu", "cot_trong"),
    (r"^ngay tao", "ngay_tao"),
    # nhập hàng
    (r"tong tien (cua ca )?phieu nhap", "tong_tien_phieu_nhap"),
    (r"tien nhap cua ca dong", "thanh_tien_nhap"),
    (r"^gia nhap", "gia_nhap"),
    (r"^so luong nhap \(don vi co ban\)", "sl_nhap_co_ban"),
    (r"^so luong nhap", "so_luong_nhap"),
    (r"^ngay nhap", "ngay_nhap"),
    (r"^ma phieu nhap", "ma_phieu_nhap"),
    (r"trang thai phieu nhap", "trang_thai_nhap"),
    (r"^don vi nhap", "don_vi_nhap"),
    (r"so thu tu dong trong phieu nhap", "stt_nhap"),
    (r"^ma nha cung cap", "ma_ncc"),
    (r"^nha cung cap", "ncc"),
    # lô, hạn dùng
    (r"so luong ban lay tu lo", "sl_lo"),
    (r"so luong khach tra lai", "so_luong_tra"),
    (r"^so lo", "ma_lo"),
    (r"^han su dung", "han_su_dung"),
    # kho
    (r"^ton kho|^ton cuoi ngay|^ton sau lan", "ton_kho"),
    # giao hàng
    (r"dot giao", "dot_giao"),
    (r"^ngay giao", "ngay_giao"),
    (r"bien so", "bien_so"),
    (r"tai xe", "tai_xe"),
    # hạn nợ
    (r"so ngay duoc no", "so_ngay_no"),
    (r"^han thanh toan", "han_thanh_toan"),
    # thu tiền
    (r"^thoi diem thu", "thoi_diem_thu"),
    (r"^ma phieu thu", "ma_phieu_thu"),
    (r"^so tien$|so tien tra lan do", "so_tien_thu"),
    # bảng giá
    (r"ngay bat dau ap dung gia", "ngay_ap_dung"),
    (r"gia ban ap dung", "gia_moi"),
    (r"gia truoc lan doi", "gia_cu"),
    # quy đổi
    (r"^he so", "he_so"),
    (r"^don vi lon", "don_vi_lon"),
    (r"file chi co mat hang co don vi lon", "ten_hang_qd"),
    # đơn hàng (cấp đơn)
    (r"con no|chua thu", "con_no"),
    (r"^da thanh toan", "da_tra"),
    (r"tong tien hang|tien hang cua don", "tong_tien_hang"),
    (r"phai tra cho ca don|^tong tien don", "tong_phai_tra"),
    (r"^giam gia$", "giam_gia"),
    (r"ma khuyen mai", "ma_khuyen_mai"),
    (r"ma ca ban hang", "ma_ca"),
    # dòng hàng
    (r"^thanh tien", "thanh_tien"),
    (r"so luong da doi ra don vi co ban", "so_luong_co_ban"),
    (r"^don vi co ban", "don_vi_co_ban"),
    (r"^don vi tinh", "don_vi"),
    (r"^ma hang", "ma_hang"),
    (r"^ten hang", "ten_hang"),
    (r"^nhom hang", "nhom_hang"),
    (r"gia ban hien tai", "gia_ban_hien_tai"),
    (r"^gia von", "gia_von"),
    (r"^don gia", "don_gia"),
    (r"so thu tu dong trong don", "stt_dong"),
    (r"^so luong", "so_luong"),
    (r"^ma don", "ma_don"),
    (r"^ma khach", "ma_khach"),
    (r"^ten khach", "ten_khach"),
    (r"^ten$", "ten"),
    (r"^ngay ban", "ngay_dat"),
    (r"thoi diem dat don|gio dat don", "thoi_diem_dat"),
    (r"^trang thai don", "trang_thai"),
    (r"^ghi chu", "ghi_chu"),
    (r"^kenh ban", "kenh_ban"),
    (r"^hinh thuc thanh toan", "hinh_thuc_tt"),
    (r"^nhom khach", "nhom_khach"),
    (r"so dien thoai", "sdt"),
    (r"^dia chi", "dia_chi"),
    (r"ma nhan vien", "ma_nhan_vien"),
    (r"^ban$", "ma_ban"),
    (r"khu vuc", "khu_vuc"),
    (r"so khach cua don", "so_khach"),
    # thuốc
    (r"^hoat chat", "hoat_chat"),
    (r"thuoc ke don", "ke_don"),
]
_DESC_RULES_RE = [(re.compile(p), c) for p, c in DESC_RULES]

# Khái niệm chung -> khái niệm cụ thể theo vai trò bảng
ROLE_SPECIFIC = {
    "line": {"ten": "ten_hang", "giam_gia": "giam_gia_dong", "gia_von": "gia_von_dong"},
    "order": {"ten": "ten_khach", "giam_gia": "giam_gia_don"},
    "product": {"ten": "ten_hang", "don_vi": "don_vi_co_ban", "ten_hang_qd": "ten_hang"},
    "conversion": {"ten": "ten_hang", "ten_hang_qd": "ten_hang"},
    "customer": {"ten": "ten_khach", "ten_khach": "ten_khach"},
}

ORDER_CONCEPTS = {
    "ma_don", "ngay_dat", "thoi_diem_dat", "trang_thai", "ma_khach", "ten_khach", "nhom_khach",
    "kenh_ban", "hinh_thuc_tt", "ma_nhan_vien", "tong_tien_hang", "giam_gia_don", "tong_phai_tra",
    "da_tra", "con_no", "ma_ban", "khu_vuc", "so_khach", "ghi_chu", "ma_khuyen_mai", "sdt", "dia_chi",
    "phi_giao", "giam_gia_don",
}
LINE_CONCEPTS = {
    "ma_don", "stt_dong", "ma_hang", "ten_hang", "so_luong", "don_vi", "so_luong_co_ban", "don_gia",
    "giam_gia_dong", "thanh_tien", "gia_von_dong", "nhom_hang",
}
PRODUCT_CONCEPTS = {
    "ma_hang", "ten_hang", "nhom_hang", "don_vi_co_ban", "gia_ban_hien_tai", "gia_von", "hoat_chat", "ke_don",
}
CONVERSION_CONCEPTS = {"ma_hang", "ten_hang", "don_vi_lon", "don_vi", "don_vi_co_ban", "he_so"}

ROLE_ALLOWED = {
    "line": LINE_CONCEPTS | ORDER_CONCEPTS,
    "order": ORDER_CONCEPTS,
    "product": PRODUCT_CONCEPTS,
    "conversion": CONVERSION_CONCEPTS,
    "lot_sale": {"ma_don", "ma_lo", "sl_lo", "so_luong_tra", "stt_dong"},
    "customer": {"ma_khach", "ten_khach", "sdt", "nhom_khach", "dia_chi"},
    "staff": {"ma_nhan_vien"},
}

# Khái niệm cho thấy bảng KHÔNG phải sổ bán (nhập, lô, kho, giao, nợ, thu tiền, bảng giá)
NON_SALES = {
    "tong_tien_phieu_nhap", "thanh_tien_nhap", "gia_nhap", "sl_nhap_co_ban", "so_luong_nhap", "ngay_nhap",
    "ma_phieu_nhap", "trang_thai_nhap", "don_vi_nhap", "stt_nhap", "ma_ncc", "ncc", "sl_lo", "so_luong_tra",
    "ma_lo", "han_su_dung", "ton_kho", "dot_giao", "ngay_giao", "bien_so", "tai_xe", "so_ngay_no",
    "han_thanh_toan", "thoi_diem_thu", "ma_phieu_thu", "so_tien_thu", "ngay_ap_dung", "gia_moi", "gia_cu",
    "he_so", "don_vi_lon", "ten_hang_qd",
}

NUMERIC_CONCEPTS = {
    "so_luong", "so_luong_co_ban", "don_gia", "giam_gia", "giam_gia_dong", "giam_gia_don", "thanh_tien",
    "gia_von", "gia_von_dong", "tong_tien_hang", "tong_phai_tra", "da_tra", "con_no", "gia_ban_hien_tai",
    "so_khach", "stt_dong", "sl_lo", "so_luong_tra", "phi_giao",
}
DATE_CONCEPTS = {"ngay_dat", "thoi_diem_dat"}


def classify_desc(desc: str | None) -> str | None:
    """Khái niệm của một mô tả cột (theo DESC_RULES); None nếu không quy tắc nào khớp."""
    if not desc:
        return None
    d = re.sub(r"\s+", " ", strip_accents(desc)).strip()
    for rx, concept in _DESC_RULES_RE:
        if rx.search(d):
            return concept
    return None


def desc_key(desc: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(desc)).strip()


@dataclass
class Dictionaries:
    desc: dict[str, str] = field(default_factory=dict)             # desc_key -> khái niệm
    names: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    name_forms: dict[str, set] = field(default_factory=lambda: defaultdict(set))      # khoá -> dạng có dấu
    variants: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))  # tên đã bung (liền)
    variant_tokens: dict[tuple, Counter] = field(default_factory=lambda: defaultdict(Counter))
    use_rules: bool = True       # mô tả chưa thấy trong từ điển: có áp DESC_RULES trực tiếp không
    sources: list[str] = field(default_factory=list)

    def concept_of_desc(self, desc: str | None) -> tuple[str | None, str]:
        if not desc:
            return None, ""
        k = desc_key(desc)
        if k in self.desc:
            return self.desc[k], "tu_dien_mo_ta"
        if self.use_rules:
            c = classify_desc(desc)
            if c:
                return c, "quy_tac_mo_ta"
        return None, ""

    def concepts_of_name(self, name: str) -> list[tuple[str, float]]:
        """(Giữ cho tương thích) khái niệm theo tên cột, không bung viết tắt."""
        return [(c, w / 2.0) for c, w, how in self.name_candidates(name, use_abbrev=False)]

    def _accent_ok(self, name: str, key: str) -> bool:
        """Tên cột có dấu mà mọi tên cùng khoá (bỏ dấu) trong từ điển đều mang DẤU KHÁC -> không khớp
        ('Hạng' không phải 'Hàng'). Tên không dấu ('Thanh tien') thì khớp được."""
        if not has_accents(name):
            return True
        forms = self.name_forms.get(key, set())
        return not forms or accent_form(name) in forms or not any(f != key for f in forms)

    def name_candidates(self, name: str, use_abbrev: bool = True) -> list[tuple[str, float, str]]:
        """Ứng viên khái niệm theo TÊN cột -> [(khái niệm, trọng số, nguồn)].

        1. khớp đúng khoá tên (README train)                     trọng số 2 x tỉ lệ    nguồn 'tu_dien_ten'
        2. khớp tiền tố ký tự dài nhất >= 6 ('Trạng thái giao')   0.95 x tỉ lệ            'tu_dien_ten_tien_to'
        3. bung viết tắt rồi khớp (tên đã bung của README train,
           hoặc mô tả train, hoặc DESC_RULES nếu bật)              1.5 / số cách bung    'abbrev'
        4. bung rồi khớp tiền tố TOKEN (>= 1 từ đủ nghĩa)          0.8 x độ phủ / số cách 'abbrev_tien_to'
        """
        out: dict[str, tuple[float, str]] = {}

        def add(concept, w, how):
            if concept and (concept not in out or out[concept][0] < w):
                out[concept] = (w, how)

        k = col_key(name)
        cnt = self.names.get(k)
        if cnt and self._accent_ok(name, k):
            total = sum(cnt.values())
            for c, n in cnt.items():
                add(c, 2.0 * n / total, "tu_dien_ten")
        elif not cnt:
            pref = [p for p in self.names if len(p) >= 6 and k.startswith(p) and p != k]
            if pref:
                best = self.names[max(pref, key=len)]
                total = sum(best.values())
                for c, n in best.items():
                    add(c, 0.95 * n / total, "tu_dien_ten_tien_to")   # khớp mờ: < 1 (yếu), lớp giá trị được kiểm chứng
        if not use_abbrev:
            return sorted(((c, w, h) for c, (w, h) in out.items()), key=lambda x: -x[1])

        variants = expand(name)
        nv = max(len(variants), 1)
        abbreviated = is_abbreviated(name)
        for toks in variants:
            phrase = " ".join(toks)
            vk = "".join(toks)
            # tên không có viết tắt: đã xét ở bước 1 (kèm kiểm tra dấu), chỉ còn khớp tiền tố token
            vc = self.variants.get(vk) if abbreviated else None
            if vc:
                total = sum(vc.values())
                for c, n in vc.items():
                    add(c, 1.5 * n / total / nv, "abbrev")
            if abbreviated and phrase in self.desc:
                add(self.desc[phrase], 1.5 / nv, "abbrev")
            elif abbreviated and self.use_rules:
                add(classify_desc(phrase), 1.0 / nv, "abbrev")
            # tiền tố token: tên train (đã bung) là phần đầu của tên cột, hoặc ngược lại
            best, best_cov = None, 0.0
            for vt, vcnt in self.variant_tokens.items():
                if vt == toks or not vt:
                    continue
                if toks[: len(vt)] == vt and (len(vt) >= 2 or len(vt[0]) >= 3):
                    cov = len(vt) / len(toks)
                elif len(toks) >= 2 and vt[: len(toks)] == toks:
                    cov = 0.6 * len(toks) / len(vt)
                else:
                    continue
                if cov > best_cov:
                    best, best_cov = vcnt, cov
            if best:
                total = sum(best.values())
                for c, n in best.items():
                    add(c, 0.8 * best_cov * n / total / nv, "abbrev_tien_to")
        # từ đầu chung của tiếng Việt: cột bắt đầu bằng 'Tên' là một tên (vai trò bảng quyết định tên hàng/khách)
        if not out and variants and variants[0][:1] == ("ten",) and len(variants[0]) >= 2:
            add("ten", 0.4, "abbrev_tu_dau")
        return sorted(((c, w, h) for c, (w, h) in out.items()), key=lambda x: -x[1])


def build_dictionaries(readmes: list[str | Path | ReadmeInfo], use_rules: bool = True) -> Dictionaries:
    """Xây từ điển từ danh sách README cho trước (vd: README của train, trừ một nhóm khi kiểm tra).
    Tên cột train được lưu cả dạng gốc lẫn dạng đã bung viết tắt."""
    d = Dictionaries(use_rules=use_rules)
    for r in readmes:
        info = r if isinstance(r, ReadmeInfo) else parse_readme(r)
        if info.path is not None:
            d.sources.append(str(info.path))
        for col, desc in info.all_pairs():
            concept = classify_desc(desc)
            if concept is None:
                continue
            d.desc[desc_key(desc)] = concept
            k = col_key(col)
            d.names[k][concept] += 1
            d.name_forms[k].add(accent_form(col))
            for toks in expand(col):
                d.variants["".join(toks)][concept] += 1
                d.variant_tokens[toks][concept] += 1
        for p in info.convention_pairs:
            concept = classify_desc(p.desc)
            if concept is not None:
                d.desc.setdefault(desc_key(p.desc), concept)
    return d


def default_train_readmes(train_dir: str | Path = "train") -> list[Path]:
    return sorted(Path(train_dir, "data").glob("*/README.md"))
