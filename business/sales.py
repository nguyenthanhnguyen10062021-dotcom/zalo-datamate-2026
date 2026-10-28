"""Sales operations on canonical loader tables, without questions or gold data."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
import json
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

from .periods import DateRange, as_date
from .rules import Rulebook, UnsupportedRule, folded


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

    def single(self):
        """Câu hỏi một đối tượng (§9): phần tử đầu của list xếp hạng, type string."""
        if self.type != 'list':
            return self
        if not self.answer:
            return Answer('unanswerable', reason=self.reason or 'Không có đối tượng')
        return Answer('string', self.answer[0], self.reason)


@dataclass(frozen=True)
class Filters:
    product_ids: tuple[str, ...] | None = None
    product_group: str | None = None
    channel: str | None = None
    payment: str | None = None
    customer_group: str | None = None
    shift: str | None = None
    size: str | None = None      # 'M'/'L': tên món kết thúc '(M)'/'(L)' (luật ngành cà phê)
    staff: str | None = None     # mã nhân viên ghi trên đơn

    def by_product(self):
        return self.product_ids is not None or self.product_group is not None or self.size is not None


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
        self.rules, self.as_of = rules, as_date(as_of_date)
        self.orders = tables['don_hang']
        self.lines = tables['dong_hang']
        self.products = tables['mat_hang']
        self.meta = tables['cua_hang']
        for frame, key in ((self.orders,'ma_don'), (self.products,'ma_hang')):
            if key not in frame or frame[key].isna().any() or frame[key].duplicated().any():
                raise DataError(f'Khóa {key} thiếu/trùng trong bảng chuẩn')
        if len(self.lines) and ('ma_don' not in self.lines or not self.lines['ma_don'].isin(self.orders['ma_don']).all()):
            raise DataError('Dòng hàng không nối được với đơn hàng')
        self._dates = pd.to_datetime(self.orders['ngay_dat'], errors='coerce').dt.normalize()
        if self._dates.isna().any():
            raise DataError('Ngày đặt thiếu/sai')

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
        if not selected['trang_thai'].isin(('hoan_thanh','dang_giao','huy','tra_hang')).all():
            raise DataError('Trạng thái đơn thiếu/chưa nhận diện')
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
        if filters.staff is not None:
            staff = self._column(self.orders,'ma_nhan_vien')
            if selected['ma_nhan_vien'].isna().any():
                raise DataError('Một số đơn thiếu nhân viên')
            if filters.staff not in set(staff.dropna()):
                raise _Unavailable('Không có mã nhân viên trong dữ liệu')
            selected = selected[selected['ma_nhan_vien'].eq(filters.staff)]
        if filters.shift is not None:
            start_min,end_min = self.rules.shift_minutes(filters.shift)
            self._column(self.orders,'thoi_diem_dat')
            ts = pd.to_datetime(selected['thoi_diem_dat'],errors='coerce')
            if ts.isna().any():
                raise DataError('Một số đơn thiếu giờ đặt')
            minute = ts.dt.hour*60+ts.dt.minute
            selected = selected[minute.between(start_min,end_min-1)]
        return selected

    def _line_sales(self, orders, filters: Filters, products_only=False):
        if not len(self.lines):
            raise _Unavailable('Không ghi dòng hàng')
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
            unknown = set(filters.product_ids)-set(self.products['ma_hang'])
            if unknown:
                raise _Unavailable('Không tìm thấy mã sản phẩm trong danh mục')
            lines = lines[lines['ma_hang'].isin(filters.product_ids)]
        if filters.product_group is not None:
            self.rules.require('Nhóm hàng','theo cot nhom hang','khong gop nhom khac ten')
            self._column(self.products,'nhom_hang')
            groups = self.products.set_index('ma_hang')['nhom_hang']
            mapped = lines['ma_hang'].map(groups)
            merchandise = lines['loai_dong'].isin(('hang','topping'))
            if (mapped.isna() & merchandise).any():
                raise DataError('Một số mặt hàng thiếu nhóm hàng')
            lines = lines[mapped.eq(filters.product_group).fillna(False)]
        if filters.size is not None:
            rule = self.rules.require('Size M, size L','ten ket thuc bang','khong phan biet hoa thuong')
            suffix = f'({filters.size})'
            if folded(suffix) not in folded(rule):
                raise UnsupportedRule(f'Rulebook không định nghĩa size {filters.size!r}')
            names = lines['ma_hang'].map(self.products.set_index('ma_hang')['ten_hang'])
            if names.isna().any():
                raise DataError('Một số dòng hàng thiếu tên món')
            suffix = ''.join(suffix.split()).casefold()
            lines = lines[names.map(lambda n: ''.join(str(n).split()).casefold().endswith(suffix))]
        return lines

    def _revenue_rule(self):
        self.rules.require('Doanh thu một đơn','thanh tien cac dong hang','khong tru giam gia tren ca don',
                           'khong cong thue VAT','khong gom phi giao hang')
        self.rules.require('Mặt hàng','phi phuc vu','van tinh vao doanh thu')

    def _revenue(self, period, filters):
        self._revenue_rule()
        orders = self._orders(period,filters,True)
        if len(self.lines):
            self._column(self.lines,'thanh_tien')
            return _sum(self._line_sales(orders,filters),'thanh_tien')
        if filters.by_product():
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
        if filters.by_product():
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
    def cancellation_rate(self, period: DateRange):
        if not self.meta.get('co_ma_don'):
            raise _Unavailable('Không xác định được số đơn')
        self.rules.require('Tỉ lệ đơn huỷ trong kỳ','moi don dat trong ky','moi trang thai','2 chu so')
        orders = self._orders(period,Filters(),False)
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
        if metric not in ('quantity','revenue','gross_profit','orders'):
            raise ValueError('metric must be quantity, revenue, gross_profit or orders')
        self.rules.require('Mặt hàng','phi phuc vu','khong xep hang')
        if metric == 'quantity':
            self.rules.require('Bán chạy','so luong quy ve don vi co ban')
        elif metric == 'orders':
            self._need_order_ids()
            self.rules.require('Số đơn','khong huy','so don co mot mat hang')
        else:
            self._revenue_rule()
        if metric == 'gross_profit':
            self.rules.require('Hàng lời nhất','tong lai gop')
        orders = self._orders(period,filters,True)
        lines = self._line_sales(orders,filters,True)
        if lines['ma_hang'].isna().any():
            raise DataError('Dòng hàng thiếu mã hàng')
        if metric == 'gross_profit':
            profit = self._line_profit(lines)
            grouped = {key:sum(group,Decimal(0)) for key,group in profit.groupby(lines['ma_hang'])}
        elif metric == 'orders':
            grouped = lines.groupby('ma_hang')['ma_don'].nunique().to_dict()
        else:
            column = 'so_luong_co_ban' if metric == 'quantity' else 'thanh_tien'
            _values(lines,column)
            grouped = {key:_sum(group,column) for key,group in lines.groupby('ma_hang')}
        return self._rank(grouped,self._product_names(),k)

    def _walkins(self, orders):
        if self.meta.get('co_ma_khach'):
            return orders['ma_khach'].isna()
        return orders['la_khach_le'].fillna(True).astype(bool)

    @_answer
    def top_customers(self, period: DateRange, k: int = 5, metric: str = 'revenue'):
        if metric not in ('revenue','orders'):
            raise ValueError('metric must be revenue or orders')
        self._ranking_rules()
        self.rules.require('Xác định khách','ma khach','khach le','khong xep hang','ten ghi tren don')
        orders = self._orders(period,Filters(),True)
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
        self.rules.require('Doanh thu theo nhóm khách','doanh thu ca shop')
        numerator,denominator = self._revenue(period,filters),self._revenue(period,Filters())
        if denominator == 0:
            raise _Unavailable('Tổng doanh thu bằng 0, không tính được tỷ trọng')
        return Answer('percent',_number(numerator/denominator*100,self.rules.rounding_places('percent')))
    # ---- Mở rộng: kỳ tốt nhất, chuỗi kỳ, giá bán, hàng ế, lãi gộp, đếm khách/mặt hàng, nhân viên ----

    def _need_order_ids(self):
        if not self.meta.get('co_ma_don'):
            raise _Unavailable('Sổ không ghi mã đơn, không xác định được số đơn')

    def _product_names(self):
        return self.products.set_index('ma_hang')['ten_hang'].to_dict()

    def _order_revenue(self, orders, filters):
        """Doanh thu §1 của từng đơn (float, theo index của orders); đơn không có dòng được lọc là 0."""
        self._revenue_rule()
        if len(self.lines):
            self._column(self.lines,'thanh_tien')
            lines = self._line_sales(orders,filters)
            amounts = _values(lines,'thanh_tien').groupby(lines['ma_don']).sum()
            return orders['ma_don'].map(amounts).fillna(0.0).astype(float)
        if filters.by_product():
            raise _Unavailable('Không có dòng hàng để lọc sản phẩm')
        self._column(self.orders,'tong_tien_hang')
        return _values(orders,'tong_tien_hang').astype(float)

    def _line_profit(self, lines):
        """Lãi gộp từng dòng (§5): thành tiền − số lượng × giá vốn ghi trên dòng (theo đơn vị bán)."""
        self.rules.require('Lãi gộp','doanh thu','gia von ghi tren dong ban','mot don vi ban','khong tu tinh lai gia von')
        self._column(self.lines,'gia_von_dong')
        merchandise = lines[lines['loai_dong'].isin(('hang','topping'))]
        if merchandise['gia_von_dong'].isna().any():
            raise DataError('Một số dòng bán thiếu giá vốn')
        revenue = _values(lines,'thanh_tien')
        cost = pd.Series(0.0,index=lines.index)
        cost.loc[merchandise.index] = _values(merchandise,'so_luong')*_values(merchandise,'gia_von_dong')
        return pd.Series([Decimal(str(round(r-c,6))) for r,c in zip(revenue,cost)],index=lines.index,dtype=object)

    def _identified(self, orders, labels=True):
        """§3 Xác định khách: bỏ khách lẻ; trả (đơn của khách định danh, cột khoá, nhãn tên).
        Chỉ đếm (labels=False) thì không cần cột tên khi tiệm có mã khách."""
        self.rules.require('Xác định khách','ma khach','khach le','khong xep hang','ten ghi tren don')
        if labels:
            self._column(self.orders,'ten_khach')
        orders = orders[~self._walkins(orders)]
        key = 'ma_khach' if self.meta.get('co_ma_khach') else 'khach_key'
        self._column(self.orders,key)
        if orders[key].isna().any():
            raise DataError('Khách hàng thiếu định danh')
        return orders, key, (orders.groupby(key)['ten_khach'].first().to_dict() if labels else {})

    def _bounds_rule(self, low, high):
        if low is None and high is None:
            return
        for value in (low, high):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('bounds must be non-negative integers')
        self.rules.require('Quá N, hơn N, trên N, dưới N','khong gom N','tu N tro len thi gom N')

    @staticmethod
    def _within(counts: pd.Series, low, high):
        mask = pd.Series(True,index=counts.index)
        if low is not None:
            mask &= counts >= low
        if high is not None:
            mask &= counts <= high
        return mask

    @_answer
    def best_period(self, period: DateRange, granularity: str = 'day', metric: str = 'revenue',
                    kind: str = 'max', filters: Filters = Filters()):
        """Ngày/tháng có doanh thu hoặc số đơn cao (thấp) nhất. Ngày không có đơn trong khoảng dữ liệu = 0."""
        if granularity not in ('day','month') or metric not in ('revenue','orders') or kind not in ('max','min'):
            raise ValueError('granularity day|month, metric revenue|orders, kind max|min')
        self._ranking_rules()
        start, end = self._range(period)
        orders = self._orders(period,filters,True)
        if metric == 'revenue':
            values = self._order_revenue(orders,filters)
        else:
            self._need_order_ids()
            self.rules.require('Số đơn','khong huy','khong tra')
            if filters.by_product():
                orders = orders[orders['ma_don'].isin(self._line_sales(orders,filters,True)['ma_don'])]
            values = pd.Series(1.0,index=orders.index)
        fmt = '%Y-%m-%d' if granularity == 'day' else '%Y-%m'
        keys = self._dates.loc[orders.index].dt.strftime(fmt)
        totals = {day.strftime(fmt):0.0 for day in pd.date_range(start,end,freq='D')}
        for key, value in values.groupby(keys).sum().items():
            totals[key] = round(float(value),6)
        if not any(totals.values()):
            raise _Unavailable('Không có doanh thu/đơn hợp lệ trong kỳ')
        sign = -1 if kind == 'max' else 1
        return Answer('date', min(totals, key=lambda key: (sign*totals[key], key)))

    @_answer
    def revenue_series(self, periods: list, filters: Filters = Filters()):
        """Doanh thu từng kỳ theo đúng thứ tự truyền vào (list số)."""
        if not periods:
            raise ValueError('periods must not be empty')
        self.rules.require_text('list theo dung thu tu cau hoi neu')
        places = self.rules.rounding_places('money')
        return Answer('list',[_number(self._revenue(p,filters),places) for p in periods])

    @_answer
    def is_monotonic(self, periods: list, direction: str = 'increasing', filters: Filters = Filters()):
        """Doanh thu tăng (giảm) liên tục: mỗi kỳ lớn hơn (nhỏ hơn) hẳn kỳ liền trước."""
        if direction not in ('increasing','decreasing') or len(periods) < 2:
            raise ValueError('direction increasing|decreasing and at least two periods')
        values = [self._revenue(p,filters) for p in periods]
        pairs = list(zip(values,values[1:]))
        ok = all(b > a for a,b in pairs) if direction == 'increasing' else all(b < a for a,b in pairs)
        return Answer('boolean',ok)

    @_answer
    def price_on_date(self, product_id: str, day):
        """§5 Giá bán X ngày D: đơn giá một đơn vị cơ bản, trước chiết khấu dòng, cả đơn huỷ/trả.
        CHƯA CHẮC: nhiều mức giá khác nhau trong ngày -> DataError (rulebook không nói chọn mức nào)."""
        self.rules.require('Giá bán X ngày D','mot don vi co ban','truoc chiet khau dong','ca dong cua don huy')
        day = as_date(day)
        self._range(DateRange(day,day))
        if not len(self.lines):
            raise _Unavailable('Không ghi dòng hàng')
        if product_id not in set(self.products['ma_hang']):
            raise _Unavailable('Không tìm thấy mã sản phẩm trong danh mục')
        self._column(self.lines,'don_gia')
        orders = self.orders.loc[self._dates.eq(pd.Timestamp(day)),'ma_don']
        lines = self.lines[self.lines['ma_don'].isin(orders) & self.lines['ma_hang'].eq(product_id)
                           & self.lines['loai_dong'].isin(('hang','topping'))]
        if not len(lines):
            raise _Unavailable('Không có dòng bán mặt hàng trong ngày')
        qty, base = _values(lines,'so_luong'), _values(lines,'so_luong_co_ban')
        if (qty == 0).any() or (base/qty <= 0).any():
            raise DataError('Số lượng dòng bán không quy đổi được')
        prices = {round(float(v),6) for v in _values(lines,'don_gia')*qty/base}
        if len(prices) != 1:
            raise DataError(f'Nhiều mức giá trong ngày: {sorted(prices)}')
        return Answer('number',_number(Decimal(str(prices.pop())),self.rules.rounding_places('money')))

    @_answer
    def slow_moving_products(self, period: DateRange, as_list: bool = False, filters: Filters = Filters()):
        """§5 Hàng ế: mặt hàng đã từng bán trước kỳ (đơn hợp lệ) nhưng trong kỳ không có đơn hợp lệ nào.
        Không có dữ liệu trước kỳ -> unanswerable (không biết hàng nào 'đã từng bán')."""
        self.rules.require('Mặt hàng không bán được trong kỳ (ế)','da tung ban truoc ky','trong ky khong co don nao')
        self.rules.require('Mặt hàng','phi phuc vu','khong dem')
        start, _ = self._range(period)
        first = pd.Timestamp(as_date(self.meta['ngay_bat_dau_du_lieu']))
        if pd.Timestamp(period.start) <= first:
            raise _Unavailable('Không có dữ liệu trước kỳ hỏi')
        before = self._orders(DateRange(first.date(),(start-pd.Timedelta(days=1)).date()),filters,True)
        sold_before = set(self._line_sales(before,filters,True)['ma_hang'])
        sold_now = set(self._line_sales(self._orders(period,filters,True),filters,True)['ma_hang'])
        if any(pd.isna(x) for x in sold_before | sold_now):
            raise DataError('Dòng hàng thiếu mã hàng')
        slow = sorted(sold_before - sold_now, key=str)
        if not as_list:
            return Answer('number',len(slow))
        self._ranking_rules()
        names = self._product_names()
        return Answer('list',[names[x] for x in slow])

    @_answer
    def gross_profit(self, period: DateRange, filters: Filters = Filters()):
        """§5 Lãi gộp: doanh thu (§1) − Σ số lượng × giá vốn ghi trên dòng bán. Không có giá vốn dòng -> unanswerable."""
        self._revenue_rule()
        orders = self._orders(period,filters,True)
        if not len(self.lines):
            raise _Unavailable('Không ghi dòng hàng')
        self._column(self.lines,'thanh_tien')
        profit = self._line_profit(self._line_sales(orders,filters))
        return Answer('number',_number(sum(profit,Decimal(0)),self.rules.rounding_places('money')))

    def _customer_orders(self, period, valid=True, labels=True):
        self._need_order_ids()
        self.rules.require('Số đơn','khong huy','so don cua mot khach','khach da mua')
        return self._identified(self._orders(period,Filters(),valid),labels)

    @_answer
    def customer_count(self, period: DateRange, min_orders: int | None = None, max_orders: int | None = None):
        """Số khách đã mua (§1, §3) có số đơn hợp lệ trong [min_orders, max_orders] (gồm hai đầu).
        'Từ N trở lên', 'ít nhất N' -> min_orders=N; 'quá/hơn N' -> min_orders=N+1 (§2)."""
        self._bounds_rule(min_orders,max_orders)
        orders, key, _ = self._customer_orders(period,labels=False)
        counts = orders.groupby(key).size()
        return Answer('number',int(self._within(counts,min_orders,max_orders).sum()))

    @_answer
    def customer_share(self, period: DateRange, min_orders: int | None = None, max_orders: int | None = None):
        """Phần trăm khách thoả điều kiện số đơn trong số khách đã mua trong kỳ."""
        self._bounds_rule(min_orders,max_orders)
        orders, key, _ = self._customer_orders(period,labels=False)
        counts = orders.groupby(key).size()
        if not len(counts):
            raise _Unavailable('Không có khách đã mua trong kỳ')
        share = Decimal(int(self._within(counts,min_orders,max_orders).sum()))/len(counts)*100
        return Answer('percent',_number(share,self.rules.rounding_places('percent')))

    @_answer
    def products_in_at_least(self, period: DateRange, n: int, filters: Filters = Filters()):
        """Số mặt hàng có mặt trong từ n đơn hợp lệ khác nhau trở lên (§1 Số đơn, §2 'từ N trở lên' gồm N)."""
        self._bounds_rule(n,None)
        self._need_order_ids()
        self.rules.require('Số đơn','khong huy','so don co mot mat hang')
        self.rules.require('Mặt hàng','phi phuc vu','khong dem')
        lines = self._line_sales(self._orders(period,filters,True),filters,True)
        if lines['ma_hang'].isna().any():
            raise DataError('Dòng hàng thiếu mã hàng')
        return Answer('number',int((lines.groupby('ma_hang')['ma_don'].nunique() >= n).sum()))

    def _staff_orders(self, period, valid=True):
        self._column(self.orders,'ma_nhan_vien')
        orders = self._orders(period,Filters(),valid)
        if orders['ma_nhan_vien'].isna().any():
            raise DataError('Một số đơn thiếu nhân viên')
        return orders

    @_answer
    def top_staff(self, period: DateRange, k: int = 5, metric: str = 'revenue'):
        """§3 Nhân viên bán giỏi nhất: theo doanh thu (§1), không theo số đơn. Trả list mã nhân viên."""
        if metric != 'revenue':
            raise ValueError('metric must be revenue')
        self._ranking_rules()
        self.rules.require('Nhân viên bán giỏi nhất','theo doanh thu','khong theo so don')
        orders = self._staff_orders(period)
        revenue = self._order_revenue(orders,Filters())
        grouped = {who:round(float(v),6) for who,v in revenue.groupby(orders['ma_nhan_vien']).sum().items()}
        return self._rank(grouped,{who:who for who in grouped},k)
