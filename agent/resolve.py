"""Khớp chuỗi trong spec (tên hàng, nhóm, kênh, ...) với danh mục của tiệm -> mã/nhãn chuẩn.

Không đoán: không thấy hoặc nhiều ứng viên ngang nhau -> Ambiguous (agent abstain).
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from loader.parsers import normalize_channel, normalize_payment


class Ambiguous(ValueError):
    """Tên trong câu hỏi không khớp chắc chắn một đối tượng trong dữ liệu."""


def norm(text) -> str:
    """Bỏ dấu, thường hoá, bỏ dấu câu: so khớp tên không phân biệt cách viết."""
    s = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w%]+", " ", s)).strip()


def _values(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame:
        return []
    return sorted({str(v) for v in frame[column].dropna().unique() if str(v).strip()})


class Catalog:
    """Danh mục một tiệm (tên hàng, nhóm, kênh, thanh toán, nhóm khách, nhân viên, đơn vị cơ bản)."""

    def __init__(self, tables: dict):
        products = tables["mat_hang"]
        orders = tables["don_hang"]
        self.products: dict[str, set[str]] = {}
        for code, name in zip(products["ma_hang"], products["ten_hang"]):
            if isinstance(name, str) and name.strip():
                self.products.setdefault(norm(name), set()).add(code)
        self.product_names = {c: n for c, n in zip(products["ma_hang"], products["ten_hang"]) if isinstance(n, str)}
        self.groups = _values(products, "nhom_hang")
        self.units = _values(products, "don_vi_co_ban")
        self.channels = _values(orders, "kenh_ban")
        self.payments = _values(orders, "hinh_thuc_tt")
        self.customer_groups = _values(orders, "nhom_khach")
        self.staff = _values(orders, "ma_nhan_vien")
        thuoc = tables.get("thuoc")
        self.ingredients = _values(thuoc, "hoat_chat") if thuoc is not None else []

    # ---- sản phẩm ----
    def product_ids(self, text: str) -> tuple[str, ...]:
        key = norm(text)
        if not key:
            raise Ambiguous("tên hàng rỗng")
        if key in self.products:
            return tuple(sorted(self.products[key]))
        # tên trong câu hỏi chứa trọn tên danh mục (vd thêm chữ "món", "ly") hoặc ngược lại
        padded = f" {key} "
        inside = [n for n in self.products if f" {n} " in padded]
        if inside:
            best = max(inside, key=len)
            if any(n not in best for n in inside):
                raise Ambiguous(f"'{text}' khớp nhiều mặt hàng")
            return tuple(sorted(self.products[best]))
        around = [n for n in self.products if padded in f" {n} "]
        if len(around) == 1:
            return tuple(sorted(self.products[around[0]]))
        raise Ambiguous(f"không tìm thấy hoặc nhiều mặt hàng khớp '{text}' ({len(around)} ứng viên)")

    # ---- nhãn ----
    @staticmethod
    def _label(text: str, labels: list[str], what: str) -> str:
        key = norm(text)
        exact = [v for v in labels if norm(v) == key]
        if len(exact) == 1:
            return exact[0]
        part = [v for v in labels if key and (f" {key} " in f" {norm(v)} " or f" {norm(v)} " in f" {key} ")]
        if len(part) == 1:
            return part[0]
        raise Ambiguous(f"{what} '{text}' không khớp chắc chắn ({len(exact) or len(part)} ứng viên)")

    def group(self, text: str) -> str:
        return self._label(text, self.groups, "nhóm hàng")

    def customer_group(self, text: str) -> str:
        return self._label(text, self.customer_groups, "nhóm khách")

    def channel(self, text: str) -> str:
        code = normalize_channel(text)
        if code and code in self.channels:
            return code
        return self._label(text, self.channels, "kênh bán")

    def payment(self, text: str) -> str:
        code = normalize_payment(text)
        if code and code in self.payments:
            return code
        return self._label(text, self.payments, "hình thức thanh toán")

    def staff_code(self, text: str) -> str:
        key = norm(text).replace(" ", "")
        found = [s for s in self.staff if norm(s).replace(" ", "") == key]
        if len(found) == 1:
            return found[0]
        if not self.staff:
            return text.strip().upper()     # tiệm không ghi nhân viên: business/ trả unanswerable
        raise Ambiguous(f"nhân viên '{text}' không khớp mã nào")

    def active_ingredient(self, text: str) -> str:
        """Hoạt chất phải KHỚP ĐÚNG (bỏ dấu, hoa thường, dấu câu): thuốc phối hợp là loại riêng nên không khớp một phần."""
        key = norm(text)
        found = [v for v in self.ingredients if norm(v) == key]
        if len(found) == 1:
            return found[0]
        raise Ambiguous(f"hoạt chất '{text}' không khớp đúng hoạt chất nào trong danh mục")

    def unit(self, text: str) -> str:
        key = norm(text)
        found = [u for u in self.units if norm(u) == key]
        if len(found) == 1:
            return found[0]
        return text.strip()                 # business/ trả unanswerable nếu không có đơn vị cơ bản này

    def card(self, meta: dict, limit: int = 25) -> str:
        """Thẻ dữ liệu ngắn cho prompt (không có business_id)."""
        caps = meta.get("nang_luc", {})
        have = [k for k, v in caps.items() if v is True]
        lines = [f"- Dữ liệu từ {meta.get('ngay_bat_dau_du_lieu')} đến {meta.get('ngay_ket_thuc_du_lieu')}",
                 f"- Có mã đơn: {bool(meta.get('co_ma_don'))}; có mã khách: {bool(meta.get('co_ma_khach'))}",
                 f"- Thông tin có ghi: {', '.join(have) or '(ít)'}"]
        for title, values in (("Nhóm hàng", self.groups), ("Kênh bán", self.channels),
                              ("Hình thức thanh toán", self.payments), ("Nhóm khách", self.customer_groups),
                              ("Mã nhân viên", self.staff), ("Đơn vị cơ bản", self.units)):
            if values:
                more = f" (+{len(values) - limit})" if len(values) > limit else ""
                lines.append(f"- {title}: {', '.join(values[:limit])}{more}")
        lines.append(f"- Số mặt hàng: {len(self.product_names)}")
        return "\n".join(lines)
