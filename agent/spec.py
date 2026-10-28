"""Hợp đồng spec v0: LLM chỉ xuất JSON này; code quy ra ngày, khớp tên, gọi business/.

LLM KHÔNG tự tính số hay ngày: kỳ hỏi là cấu trúc (kind + số chép từ câu hỏi), tên hàng/nhóm/kênh là chuỗi
như trong câu hỏi; code khớp với danh mục của tiệm để ra mã.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

PeriodKind = Literal[
    "today", "yesterday", "this_week", "previous_week", "this_month", "previous_month",
    "previous_month_same_elapsed", "month", "quarter", "year", "year_to_date", "last_days", "date", "range",
    "month_range", "tet", "before_tet", "all_time",
    "previous_period", "same_period_last_year"]   # hai kind cuối chỉ dùng cho `comparison`, tính từ `period`

AnswerType = Literal["number", "percent", "date", "boolean", "string", "list", "table", "unanswerable"]

# op -> (kiểu đáp án hợp lệ, trường bắt buộc, mô tả 1 dòng cho prompt)
OPS: dict[str, tuple[tuple[str, ...], tuple[str, ...], str]] = {
    "revenue": (("number",), ("period",), "doanh thu / tiền bán / tiền hàng (§1), có thể lọc"),
    "order_count": (("number",), ("period",), "số đơn hợp lệ (không huỷ, không trả)"),
    "cancelled_orders": (("number",), ("period",), "số đơn bị huỷ"),
    "cancellation_rate": (("percent",), ("period",), "tỉ lệ đơn huỷ (%)"),
    "average_order_value": (("number",), ("period",), "giá trị trung bình một đơn"),
    "quantity": (("number",), ("period",), "số lượng bán quy về đơn vị cơ bản; unit = đơn vị câu hỏi nêu (ly, chai...)"),
    "top_products": (("list", "string"), ("period", "metric"),
                     "xếp hạng mặt hàng; metric quantity|revenue|gross_profit|orders; k = số mục"),
    "top_customers": (("list", "string"), ("period", "metric"), "xếp hạng khách; metric revenue|orders"),
    "revenue_growth": (("percent",), ("period", "comparison"), "% thay đổi doanh thu kỳ hỏi so với kỳ so"),
    "revenue_share": (("percent",), ("period",), "% doanh thu của phần lọc (nhóm hàng, kênh...) trên cả shop"),
    "best_period": (("date",), ("period", "granularity", "kind"),
                    "ngày/tháng có doanh thu (metric revenue) hoặc số đơn (orders) cao nhất (max) / thấp nhất (min)"),
    "revenue_series": (("list",), ("periods",), "doanh thu từng kỳ theo thứ tự câu hỏi nêu"),
    "is_monotonic": (("boolean",), ("periods", "direction"), "doanh thu tăng (increasing) / giảm liên tục?"),
    "price_on_date": (("number",), ("product", "period"), "giá bán một đơn vị cơ bản của mặt hàng trong một ngày"),
    "slow_moving_products": (("number", "list"), ("period",), "số (hoặc danh sách) mặt hàng ế trong kỳ"),
    "gross_profit": (("number",), ("period",), "lãi gộp"),
    "customer_count": (("number",), ("period",), "số khách đã mua, có thể theo số đơn min_orders/max_orders"),
    "customer_share": (("percent",), ("period",), "% khách thoả điều kiện số đơn trên số khách đã mua"),
    "products_in_at_least": (("number",), ("period", "min_orders"), "số mặt hàng có mặt trong >= min_orders đơn"),
    "top_staff": (("list", "string"), ("period",), "nhân viên bán giỏi nhất (theo doanh thu)"),
    "loyal_customers": (("list", "string"), ("period",), "khách trung thành nhất (luật public)"),
    "big_spender_customers": (("list", "string"), ("period",), "khách sộp nhất (luật public)"),
    "fickle_customers": (("list", "string"), ("period",), "khách hay đổi ý / huỷ nhiều nhất (luật public)"),
    "favorite_products": (("list", "string"), ("period",), "mặt hàng được ưa chuộng nhất (luật public)"),
    "hardworking_staff": (("list", "string"), ("period",), "nhân viên chăm chỉ nhất (luật public)"),
    "busiest_day": (("date",), ("period",), "ngày đắt khách nhất (luật public)"),
    "peak_hour": (("number",), ("period",), "giờ cao điểm (luật public)"),
    "weekday_average": (("number",), ("period", "weekday"), "trung bình mỗi ngày thứ X (luật public), weekday 0=thứ Hai"),
    "unanswerable": (("unanswerable",), (), "dữ liệu bán hàng không thể có thông tin này (ý kiến, cảm nhận, bên ngoài)"),
    "unsupported": ((), (), "câu hỏi hợp lệ nhưng không có op phù hợp (công nợ, tồn kho, nhập hàng, ...)"),
}
OpName = Literal[tuple(OPS)]  # type: ignore[valid-type]

METRICS = {"top_products": {"quantity", "revenue", "gross_profit", "orders"}, "top_customers": {"revenue", "orders"},
           "best_period": {"revenue", "orders"}, "weekday_average": {"revenue", "orders"}}


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: PeriodKind
    n: int | None = None          # last_days
    day: int | None = None        # date; range: ngày đầu
    month: int | None = None      # month, date; range: tháng đầu
    year: int | None = None       # month/quarter/year/date/tet; null = theo luật năm ngầm định
    quarter: int | None = None
    end_day: int | None = None    # range: ngày cuối
    end_month: int | None = None
    end_year: int | None = None

    @model_validator(mode="after")
    def _check(self):
        need = {"last_days": ("n",), "month": ("month",), "quarter": ("quarter",), "year": ("year",),
                "date": ("day", "month", "year"), "tet": ("year",), "before_tet": ("year",),
                "range": ("day", "month", "year", "end_day", "end_month", "end_year"),
                "month_range": ("month", "year", "end_month", "end_year")}.get(self.kind, ())
        missing = [f for f in need if getattr(self, f) is None]
        if missing:
            raise ValueError(f"period {self.kind} thiếu {missing}")
        return self


class Spec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: OpName
    answer_type: AnswerType | None = None
    period: Period | None = None
    comparison: Period | None = None
    periods: list[Period] | None = None
    product: str | None = None
    product_group: str | None = None
    channel: str | None = None
    payment: str | None = None
    customer_group: str | None = None
    shift: Literal["sang", "chieu"] | None = None
    size: Literal["M", "L"] | None = None
    staff: str | None = None
    unit: str | None = None
    k: int | None = None
    metric: str | None = None
    granularity: Literal["day", "month"] | None = None
    kind: Literal["max", "min"] | None = None
    direction: Literal["increasing", "decreasing"] | None = None
    min_orders: int | None = None
    max_orders: int | None = None
    weekday: int | None = None

    @model_validator(mode="after")
    def _check(self):
        types, required, _ = OPS[self.op]
        if self.op == "unsupported":
            return self
        if self.answer_type is None:
            raise ValueError("thiếu answer_type")
        if self.answer_type not in types:
            raise ValueError(f"answer_type {self.answer_type} không hợp với op {self.op} (cho phép {types})")
        missing = [f for f in required if getattr(self, f) in (None, [], "")]
        if missing:
            raise ValueError(f"op {self.op} thiếu {missing}")
        if self.op in METRICS and self.metric is not None and self.metric not in METRICS[self.op]:
            raise ValueError(f"metric {self.metric} không hợp với op {self.op}")
        if self.k is not None and not 1 <= self.k <= 50:
            raise ValueError("k ngoài 1..50")
        if self.weekday is not None and not 0 <= self.weekday <= 6:
            raise ValueError("weekday ngoài 0..6")
        for p in [self.period] + list(self.periods or []):
            if p is not None and p.kind in ("previous_period", "same_period_last_year"):
                raise ValueError(f"kind {p.kind} chỉ dùng cho comparison")
        if self.periods is not None and len(self.periods) < (2 if self.op == "is_monotonic" else 1):
            raise ValueError("periods quá ít")
        return self


def parse_spec(data) -> tuple[Spec | None, str | None]:
    """dict/JSON -> (Spec, None) hoặc (None, lỗi)."""
    try:
        return (Spec.model_validate_json(data) if isinstance(data, str) else Spec.model_validate(data)), None
    except ValidationError as e:
        return None, "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())[:500]


def json_schema() -> dict:
    """Schema cho structured output của vLLM (guided JSON)."""
    return Spec.model_json_schema()
