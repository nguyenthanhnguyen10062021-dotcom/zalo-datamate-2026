"""spec -> gọi business API -> Answer đúng format §9. Không đọc câu hỏi, không đọc gold."""
from __future__ import annotations

from datetime import date, timedelta

from business import DateRange, Filters, Periods
from business.periods import as_date
from business.sales import Answer, SalesMetrics

from .resolve import Catalog
from .spec import Period, Spec


class Unsupported(ValueError):
    """Spec hợp lệ nhưng không thực thi được bằng API hiện có (op unsupported, kỳ chưa hỗ trợ...)."""


def to_range(p: Period, periods: Periods, meta: dict) -> DateRange:
    """Kỳ có cấu trúc -> DateRange theo as_of_date + rulebook (business.Periods)."""
    k = p.kind
    if k == "today":
        return periods.today()
    if k == "yesterday":
        return periods.yesterday()
    if k == "this_week":
        return periods.this_week()
    if k == "previous_week":
        return periods.previous_week()
    if k == "this_month":
        return periods.this_month()
    if k == "previous_month":
        return periods.previous_month()
    if k == "previous_month_same_elapsed":
        return periods.previous_month(same_elapsed=True)
    if k == "month":
        return periods.month(p.month, p.year)
    if k == "quarter":
        return periods.quarter(p.quarter, p.year)
    if k == "year":
        return DateRange(date(p.year, 1, 1), date(p.year, 12, 31))
    if k == "year_to_date":
        return periods.year_to_date()
    if k == "last_days":
        return periods.last_days(p.n)
    if k == "date":
        d = date(p.year, p.month, p.day)
        return DateRange(d, d)
    if k == "range":
        return DateRange(date(p.year, p.month, p.day), date(p.end_year, p.end_month, p.end_day))
    if k == "month_range":
        return DateRange(periods.month(p.month, p.year).start, periods.month(p.end_month, p.end_year).end)
    if k == "tet":
        return periods.tet(p.year)
    if k == "before_tet":
        return periods.before(periods.tet(p.year))
    if k == "all_time":
        return DateRange(as_date(meta["ngay_bat_dau_du_lieu"]), periods.as_of)
    raise Unsupported(f"kỳ {k} chỉ dùng cho comparison hoặc chưa hỗ trợ")


def _shift_year(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:              # 29/02
        return d.replace(year=d.year + years, day=28)


def comparison_range(c: Period, base: Period, base_range: DateRange, periods: Periods, meta: dict) -> DateRange:
    """Kỳ so. previous_period / same_period_last_year tính từ kỳ hỏi bằng code (LLM không tự trừ ngày)."""
    if c.kind == "previous_period":
        if base.kind == "this_month":
            return periods.previous_month(same_elapsed=True)       # §2 Tháng này: so cùng số ngày tháng trước
        if base.kind == "month":
            m, y = (base_range.start.month - 1, base_range.start.year) if base_range.start.month > 1 else \
                (12, base_range.start.year - 1)
            return periods.month(m, y)
        if base.kind == "quarter":
            q = (base_range.start.month - 1) // 3 + 1
            return periods.quarter(q - 1, base_range.start.year) if q > 1 else periods.quarter(4, base_range.start.year - 1)
        if base.kind == "year":
            return DateRange(date(base.year - 1, 1, 1), date(base.year - 1, 12, 31))
        if base.kind in ("date", "today", "yesterday", "last_days", "range", "previous_week"):
            days = (base_range.end - base_range.start).days + 1
            return DateRange(base_range.start - timedelta(days=days), base_range.start - timedelta(days=1))
        raise Unsupported(f"chưa định nghĩa kỳ trước của {base.kind}")
    if c.kind == "same_period_last_year":
        if base.kind in ("month", "quarter", "year", "date", "range", "month_range"):
            return DateRange(_shift_year(base_range.start, -1), _shift_year(base_range.end, -1))
        raise Unsupported(f"chưa định nghĩa cùng kỳ năm trước của {base.kind}")
    return to_range(c, periods, meta)


def to_filters(s: Spec, cat: Catalog) -> Filters:
    return Filters(
        product_ids=cat.product_ids(s.product) if s.product and s.op != "price_on_date" else None,
        product_group=cat.group(s.product_group) if s.product_group else None,
        channel=cat.channel(s.channel) if s.channel else None,
        payment=cat.payment(s.payment) if s.payment else None,
        customer_group=cat.customer_group(s.customer_group) if s.customer_group else None,
        shift=s.shift, size=s.size,
        staff=cat.staff_code(s.staff) if s.staff else None)


def execute(s: Spec, engine: SalesMetrics, periods: Periods, cat: Catalog) -> Answer:
    """Thực thi spec đã hợp lệ. Có thể ném Ambiguous / Unsupported / UnsupportedRule / DataError."""
    if s.op == "unsupported":
        raise Unsupported("LLM: không có op phù hợp")
    if s.op == "unanswerable":
        return Answer("unanswerable", reason="LLM: dữ liệu bán hàng không có thông tin này")
    meta = engine.meta
    period = to_range(s.period, periods, meta) if s.period else None
    f = to_filters(s, cat)
    k = s.k or (1 if s.answer_type == "string" else 5)
    op = s.op
    if op == "revenue":
        a = engine.revenue(period, f)
    elif op == "order_count":
        a = engine.order_count(period, f)
    elif op == "cancelled_orders":
        a = engine.cancelled_orders(period, f)
    elif op == "cancellation_rate":
        a = engine.cancellation_rate(period)
    elif op == "average_order_value":
        a = engine.average_order_value(period, f)
    elif op == "quantity":
        a = engine.quantity(period, f, unit=cat.unit(s.unit) if s.unit else None)
    elif op == "top_products":
        a = engine.top_products(period, k=k, metric=s.metric or "quantity", filters=f)
    elif op == "top_customers":
        a = engine.top_customers(period, k=k, metric=s.metric or "revenue")
    elif op == "revenue_growth":
        a = engine.revenue_growth(period, comparison_range(s.comparison, s.period, period, periods, meta), f)
    elif op == "revenue_share":
        a = engine.revenue_share(period, f)
    elif op == "best_period":
        a = engine.best_period(period, s.granularity, s.metric or "revenue", s.kind, f)
    elif op == "revenue_series":
        a = engine.revenue_series([to_range(p, periods, meta) for p in s.periods], f)
    elif op == "is_monotonic":
        a = engine.is_monotonic([to_range(p, periods, meta) for p in s.periods], s.direction, f)
    elif op == "price_on_date":
        ids = cat.product_ids(s.product)
        if len(ids) != 1:
            raise Unsupported("tên hàng ứng với nhiều mã")
        if period.start != period.end:
            raise Unsupported("giá bán cần đúng một ngày")
        a = engine.price_on_date(ids[0], period.start)
    elif op == "slow_moving_products":
        a = engine.slow_moving_products(period, as_list=s.answer_type == "list", filters=f)
    elif op == "gross_profit":
        a = engine.gross_profit(period, f)
    elif op == "customer_count":
        a = engine.customer_count(period, s.min_orders, s.max_orders)
    elif op == "customer_share":
        a = engine.customer_share(period, s.min_orders, s.max_orders)
    elif op == "products_in_at_least":
        a = engine.products_in_at_least(period, s.min_orders, f)
    elif op == "top_staff":
        a = engine.top_staff(period, k=k)
    elif op == "loyal_customers":
        a = engine.loyal_customers(period, k=k)
    elif op == "big_spender_customers":
        a = engine.big_spender_customers(period, k=k)
    elif op == "fickle_customers":
        a = engine.fickle_customers(period, k=k)
    elif op == "favorite_products":
        a = engine.favorite_products(period, k=k, filters=f)
    elif op == "hardworking_staff":
        a = engine.hardworking_staff(period, k=k)
    elif op == "busiest_day":
        a = engine.busiest_day(period)
    elif op == "peak_hour":
        a = engine.peak_hour(period)
    elif op == "weekday_average":
        a = engine.weekday_average(period, s.weekday, s.metric or "revenue")
    else:
        raise Unsupported(f"op {op} chưa nối")
    return format_answer(a, s)


def format_answer(a: Answer, s: Spec) -> Answer:
    """Khớp type với answer_type của spec (§9): câu hỏi một đối tượng -> string; còn lại phải trùng type."""
    if a.type == "unanswerable":
        return a
    if s.answer_type == "string" and a.type == "list":
        a = a.single()
    if a.type == "date" and s.answer_type == "date":
        return a
    if a.type != s.answer_type:
        raise Unsupported(f"API trả {a.type}, câu hỏi cần {s.answer_type}")
    return a
