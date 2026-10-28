"""Sales operations on canonical loader tables, without questions or gold data."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
import json
from pathlib import Path
import unicodedata

import numpy as np
import pandas as pd

from .periods import DateRange, as_date
from .rules import Rulebook, UnsupportedRule


class DataError(ValueError):
    """Incomplete/inconsistent normalized data: an agent should abstain or repair."""


class _Unavailable(Exception):
    pass


@dataclass(frozen=True)
class Answer:
    type: str
    answer: object = None
    reason: str | None = None

    def to_submission(self, question_id: str) -> dict:
        result = {'id': question_id, 'type': self.type}
        if self.type not in ('unanswerable', 'abstain'):
            result['answer'] = self.answer
        if self.reason is not None:
            result['reason'] = self.reason
        return result


@dataclass(frozen=True)
class Filters:
    product_ids: tuple[str, ...] | None = None
    product_group: str | None = None
    channel: str | None = None
    payment: str | None = None
    customer_group: str | None = None
    shift: str | None = None


def _answer(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except _Unavailable as e:
            return Answer('unanswerable', reason=str(e))
    return call


def _number(value: Decimal, places=0):
    value = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return int(value) if value == value.to_integral_value() else float(value)


def _values(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        raise _Unavailable(f'Không có cột {column}')
    raw = frame[column]
    numeric = pd.to_numeric(raw, errors='coerce')
    if numeric.isna().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all() or raw.map(lambda x: isinstance(x, (bool,np.bool_))).any():
        raise DataError(f'Thiếu/sai giá trị ở cột {column}')
    return numeric


def _sum(frame: pd.DataFrame, column: str) -> Decimal:
    return sum((Decimal(str(v)) for v in _values(frame, column)), Decimal(0))


class SalesMetrics:
    """Use real order IDs for counts; retain synthetic IDs only for linking sales."""

    def __init__(self, tables: dict, rules: Rulebook, as_of_date):
        if not isinstance(tables, dict) or not {'don_hang', 'dong_hang', 'mat_hang', 'cua_hang'}.issubset(tables):
            raise DataError('Thiếu bảng chuẩn trong dữ liệu đầu vào')
        if not all(isinstance(tables[name], pd.DataFrame) for name in ('don_hang','dong_hang','mat_hang')) or not isinstance(tables['cua_hang'], dict):
            raise DataError('Sai kiểu bảng chuẩn trong dữ liệu đầu vào')
        self.rules, self.as_of = rules, as_date(as_of_date)
        self.orders = tables['don_hang']
        self.lines = tables['dong_hang']
        self.products = tables['mat_hang']
        self.meta = tables['cua_hang']
        if 'ma_don' not in self.orders or self.orders['ma_don'].isna().any() or self.orders['ma_don'].duplicated().any():
            raise DataError('Khóa ma_don thiếu/trùng trong bảng chuẩn')
        if 'ngay_dat' not in self.orders:
            raise DataError('Ngày đặt thiếu/sai')
        self._dates = pd.to_datetime(self.orders['ngay_dat'], errors='coerce').dt.normalize()
        if self._dates.isna().any():
            raise DataError('Ngày đặt thiếu/sai')

    def _validate_products(self):
        if 'ma_hang' not in self.products or self.products['ma_hang'].isna().any() or self.products['ma_hang'].duplicated().any():
            raise DataError('Khóa ma_hang thiếu/trùng trong bảng chuẩn')

    def _validate_lines(self):
        if len(self.lines) and ('ma_don' not in self.lines or not self.lines['ma_don'].isin(self.orders['ma_don']).all()):
            raise DataError('Dòng hàng không nối được với đơn hàng')

    @classmethod
    def from_cache(cls, cache_dir: str | Path, rulebook_path: str | Path, as_of_date):
        cache = Path(cache_dir)
        tables = {name: pd.read_parquet(cache/f'{name}.parquet') for name in ('don_hang','dong_hang','mat_hang')}
        tables['cua_hang'] = json.loads((cache/'cua_hang.json').read_text(encoding='utf-8'))
        return cls(tables, Rulebook.from_path(rulebook_path), as_of_date)

    def _range(self, period: DateRange):
        first = self.meta.get('ngay_bat_dau_du_lieu')
        last = self.meta.get('ngay_ket_thuc_du_lieu') or self.meta.get('ngay_cuoi_trong_du_lieu')
        if not first or not last:
            raise _Unavailable('Không biết khoảng ngày có dữ liệu')
        start, end = max(period.start,as_date(first)), min(period.end,as_date(last),self.as_of)
        if start > end:
            raise _Unavailable('Kỳ hỏi nằm hoàn toàn ngoài khoảng dữ liệu đã xảy ra')
        return pd.Timestamp(start), pd.Timestamp(end)

    def _column(self, frame, column):
        if column not in frame or not frame[column].notna().any():
            raise _Unavailable(f'Không ghi thông tin {column}')
        return frame[column]

    def _orders(self, period, filters: Filters, valid: bool):
        self.rules.require('Đơn thuộc kỳ nào', 'theo ngay dat')
        start, end = self._range(period)
        selected = self.orders.loc[self._dates.between(start,end)]
        status = self._column(self.orders,'trang_thai')
        if valid:
            self.rules.require('Đơn tính vào doanh thu', 'khong huy', 'khong tra hang', 'dang giao van tinh')
            selected = selected[~status.loc[selected.index].isin(('huy','tra_hang'))]
        for column, value in (('kenh_ban',filters.channel), ('hinh_thuc_tt',filters.payment), ('nhom_khach',filters.customer_group)):
            if value is None:
                continue
            if column == 'hinh_thuc_tt':
                self.rules.require('Doanh thu theo hình thức thanh toán','ghi tren don')
            if column == 'nhom_khach':
                self.rules.require('Doanh thu theo nhóm khách','cot nhom khach','khong thuoc nhom nao')
            self._column(self.orders,column)
            if selected[column].isna().any() and column != 'nhom_khach':
                raise DataError(f'Một số đơn thiếu {column}')
            mask = selected[column].eq(value).fillna(False)
            if column == 'nhom_khach':
                walkins = self._walkins(selected)
                if (selected[column].isna() & ~walkins).any():
                    raise DataError('Một số khách đã định danh thiếu nhóm khách')
                mask &= ~walkins
            selected = selected[mask]
        if filters.shift is not None:
            start_min,end_min = self.rules.shift_minutes(filters.shift)
            self._column(self.orders,'thoi_diem_dat')
            ts = pd.to_datetime(selected['thoi_diem_dat'],errors='coerce')
            if ts.isna().any():
                raise DataError('Một số đơn thiếu giờ đặt')
            minute = ts.dt.hour*60+ts.dt.minute
            selected = selected[minute.between(start_min,end_min-1)]
        if not selected['trang_thai'].isin(('hoan_thanh','dang_giao','huy','tra_hang')).all():
            raise DataError('Trạng thái đơn thiếu/chưa nhận diện')
        return selected

    def _line_sales(self, orders, filters: Filters, products_only=False):
        if not len(self.lines):
            raise _Unavailable('Không ghi dòng hàng')
        self._validate_lines()
        self._column(self.lines,'loai_dong')
        lines = self.lines[self.lines['ma_don'].isin(orders['ma_don'])]
        if not orders['ma_don'].isin(lines['ma_don']).all():
            raise DataError('Một số đơn trong kỳ không có dòng hàng')
        kinds = ('hang','topping') if products_only else ('hang','phi_phuc_vu','topping')
        if not lines['loai_dong'].isin(('hang','topping','phi_phuc_vu','voucher','dung_diem','phi_ship')).all():
            raise DataError('Không biết loại dòng hàng')
        lines = lines[lines['loai_dong'].isin(kinds)]
        if filters.product_ids is not None:
            if isinstance(filters.product_ids, str):
                raise ValueError('product_ids must be a sequence of IDs, not a string')
            self._validate_products()
            unknown = set(filters.product_ids)-set(self.products['ma_hang'])
            if unknown:
                raise _Unavailable('Không tìm thấy mã sản phẩm trong danh mục')
            lines = lines[lines['ma_hang'].isin(filters.product_ids)]
        if filters.product_group is not None:
            self.rules.require('Nhóm hàng','theo cot nhom hang','khong gop nhom khac ten')
            self._validate_products()
            self._column(self.products,'nhom_hang')
            groups = self.products.set_index('ma_hang')['nhom_hang']
            mapped = lines['ma_hang'].map(groups)
            merchandise = lines['loai_dong'].isin(('hang','topping'))
            if (mapped.isna() & merchandise).any():
                raise DataError('Một số mặt hàng thiếu nhóm hàng')
            lines = lines[mapped.eq(filters.product_group).fillna(False)]
        return lines

    def _revenue_rule(self):
        self.rules.require('Doanh thu một đơn','thanh tien cac dong hang','khong tru giam gia tren ca don',
                           'khong cong thue VAT','khong gom phi giao hang')
        self.rules.require('Mặt hàng','phi phuc vu','van tinh vao doanh thu')

    def _revenue(self, period, filters):
        self._revenue_rule()
        orders = self._orders(period,filters,True)
        if len(self.lines):
            self._validate_lines()
            self._column(self.lines,'thanh_tien')
            return _sum(self._line_sales(orders,filters),'thanh_tien')
        if filters.product_ids is not None or filters.product_group is not None:
            raise _Unavailable('Không có dòng hàng để lọc sản phẩm')
        self._column(self.orders,'tong_tien_hang')
        return _sum(orders,'tong_tien_hang')

    def _count(self, period, filters, cancelled=False):
        if not self.meta.get('co_ma_don'):
            raise _Unavailable('Sổ không ghi mã đơn, không xác định được số đơn')
        self.rules.require('Số đơn','khong huy','khong tra')
        orders = self._orders(period,filters,not cancelled)
        if cancelled:
            self.rules.require('Đơn bị huỷ','trang thai huy','khong phai don huy')
            orders = orders[orders['trang_thai']=='huy']
        if filters.product_ids is not None or filters.product_group is not None:
            lines = self._line_sales(orders,filters,True)
            orders = orders[orders['ma_don'].isin(lines['ma_don'])]
        return len(orders)

    @_answer
    def revenue(self, period: DateRange, filters: Filters = Filters()):
        return Answer('number',_number(self._revenue(period,filters),self.rules.rounding_places('money')))

    @_answer
    def order_count(self, period: DateRange, filters: Filters = Filters()):
        return Answer('number',self._count(period,filters))

    @_answer
    def cancelled_orders(self, period: DateRange, filters: Filters = Filters()):
        return Answer('number',self._count(period,filters,True))

    @_answer
    def cancellation_rate(self, period: DateRange, filters: Filters = Filters()):
        if filters.product_ids is not None or filters.product_group is not None:
            raise UnsupportedRule('Chưa hỗ trợ lọc sản phẩm cho tỷ lệ đơn hủy')
        if not self.meta.get('co_ma_don'):
            raise _Unavailable('Không xác định được số đơn')
        self.rules.require('Tỉ lệ đơn huỷ trong kỳ','moi don dat trong ky','moi trang thai','2 chu so')
        orders = self._orders(period,filters,False)
        if not len(orders):
            raise _Unavailable('Không có đơn để tính tỷ lệ')
        return Answer('percent',_number(Decimal(int(orders['trang_thai'].eq('huy').sum()))/len(orders)*100,self.rules.rounding_places('percent')))

    @_answer
    def average_order_value(self, period: DateRange, filters: Filters = Filters()):
        self.rules.require('Giá trị trung bình một đơn','nua dong lam tron len')
        count = self._count(period,filters)
        if not count:
            raise _Unavailable('Không có đơn hợp lệ để tính trung bình')
        return Answer('number',_number(self._revenue(period,filters)/count,self.rules.rounding_places('money')))

    @_answer
    def quantity(self, period: DateRange, filters: Filters = Filters(), unit: str | None = None):
        self.rules.require('Bán được bao nhiêu <đơn vị>','so luong quy ve don vi co ban','co don vi co ban la')
        orders = self._orders(period,filters,True)
        self._column(self.lines,'so_luong_co_ban')
        lines = self._line_sales(orders,filters,True)
        if unit is not None:
            self._validate_products()
            self._column(self.products,'don_vi_co_ban')
            base = self.products.set_index('ma_hang')['don_vi_co_ban']
            def unit_key(value):
                return ' '.join(unicodedata.normalize('NFC',value).casefold().split())
            base = base.map(lambda v:unit_key(v) if isinstance(v,str) else None)
            unit = unit_key(unit)
            if unit not in set(base.dropna()):
                raise _Unavailable('Không có đơn vị cơ bản được yêu cầu')
            mapped = lines['ma_hang'].map(base)
            if mapped.isna().any():
                raise DataError('Một số sản phẩm chưa xác định đơn vị cơ bản')
            lines = lines[mapped.eq(unit)]
        return Answer('number',_number(_sum(lines,'so_luong_co_ban'),6))

    def _ranking_rules(self):
        self.rules.require_text('theo ma tang dan')

    def _rank(self, grouped, labels, k):
        if type(k) is not int or k <= 0:
            raise ValueError('k must be a positive integer')
        ranked = sorted(grouped.items(), key=lambda item: (-item[1],str(item[0])))[:k]
        if not ranked:
            raise _Unavailable('Không có đối tượng để xếp hạng')
        names = [labels.get(key) for key,_ in ranked]
        if any(pd.isna(name) for name in names):
            raise DataError('Thiếu tên đối tượng xếp hạng')
        return Answer('list',names)

    @_answer
    def top_products(self, period: DateRange, k: int = 5, metric: str = 'quantity', filters: Filters = Filters()):
        self._ranking_rules()
        if metric not in ('quantity','revenue'):
            raise ValueError('metric must be quantity or revenue')
        self.rules.require('Mặt hàng','phi phuc vu','khong xep hang')
        self._validate_products()
        if metric == 'quantity':
            self.rules.require('Bán chạy','so luong quy ve don vi co ban')
        else:
            self._revenue_rule()
        orders = self._orders(period,filters,True)
        lines = self._line_sales(orders,filters,True)
        column = 'so_luong_co_ban' if metric == 'quantity' else 'thanh_tien'
        _values(lines,column)
        if lines['ma_hang'].isna().any():
            raise DataError('Dòng hàng thiếu mã hàng')
        grouped = {key:_sum(group,column) for key,group in lines.groupby('ma_hang')}
        return self._rank(grouped,self.products.set_index('ma_hang')['ten_hang'].to_dict(),k)

    def _walkins(self, orders):
        if self.meta.get('co_ma_khach'):
            return orders['ma_khach'].isna()
        return orders['la_khach_le'].fillna(True).astype(bool)

    @_answer
    def top_customers(self, period: DateRange, k: int = 5, metric: str = 'revenue', filters: Filters = Filters()):
        if metric not in ('revenue','orders'):
            raise ValueError('metric must be revenue or orders')
        if filters.product_ids is not None or filters.product_group is not None:
            raise UnsupportedRule('Chưa hỗ trợ lọc sản phẩm cho xếp hạng khách hàng')
        self._ranking_rules()
        self.rules.require('Xác định khách','ma khach','khach le','khong xep hang','ten ghi tren don')
        orders = self._orders(period,filters,True)
        self._column(self.orders,'ten_khach')
        orders = orders[~self._walkins(orders)]
        key = 'ma_khach' if self.meta.get('co_ma_khach') else 'khach_key'
        self._column(self.orders,key)
        if orders[key].isna().any():
            raise DataError('Khách hàng thiếu định danh')
        labels = orders.groupby(key)['ten_khach'].first().to_dict()
        if metric == 'orders':
            if not self.meta.get('co_ma_don'):
                raise _Unavailable('Không xác định được số đơn')
            grouped = orders.groupby(key).size().to_dict()
        else:
            self._revenue_rule()
            if len(self.lines):
                lines = self._line_sales(orders,Filters())
                _values(lines,'thanh_tien')
                frame = lines.merge(orders[['ma_don',key]],on='ma_don',validate='many_to_one')
                grouped = {who:_sum(group,'thanh_tien') for who,group in frame.groupby(key)}
            else:
                grouped = {who:_sum(group,'tong_tien_hang') for who,group in orders.groupby(key)}
        return self._rank(grouped,labels,k)

    @_answer
    def revenue_growth(self, period: DateRange, comparison: DateRange, filters: Filters = Filters()):
        self.rules.require('Phần trăm thay đổi, tăng trưởng','ky truoc','so am')
        current, baseline = self._revenue(period,filters), self._revenue(comparison,filters)
        if baseline == 0:
            raise _Unavailable('Kỳ so sánh bằng 0, không tính được tăng trưởng')
        return Answer('percent',_number((current-baseline)/baseline*100,self.rules.rounding_places('percent')))

    @_answer
    def revenue_share(self, period: DateRange, filters: Filters):
        if filters.customer_group is not None:
            self.rules.require('Doanh thu theo nhóm khách','doanh thu ca shop')
        numerator,denominator = self._revenue(period,filters),self._revenue(period,Filters())
        if denominator == 0:
            raise _Unavailable('Tổng doanh thu bằng 0, không tính được tỷ trọng')
        return Answer('percent',_number(numerator/denominator*100,self.rules.rounding_places('percent')))
