"""Prompt: system cố định (để vLLM prefix-cache) + thẻ dữ liệu tiệm + few-shot BM25 + câu hỏi."""
from __future__ import annotations

import json

from .spec import OPS, parse_spec


def canonical(spec: dict) -> str:
    """Spec theo ĐÚNG thứ tự trường của schema. Bắt buộc: guided decoding sinh khoá theo thứ tự schema, ví dụ
    viết khác thứ tự thì model bỏ sót trường (vd mất `product` vì đã viết `unit` trước)."""
    parsed, _ = parse_spec(spec)
    return parsed.model_dump_json(exclude_none=True) if parsed else json.dumps(spec, ensure_ascii=False)

PERIOD_HELP = """\
Kỳ (period / comparison / periods[i]) là object {"kind": ..., các số CHÉP từ câu hỏi}. KHÔNG tự tính ngày.
- today, yesterday, this_week, previous_week ("tuần trước/tuần rồi"), this_month ("tháng này", "từ đầu tháng tới nay"),
  previous_month ("tháng trước" cả tháng), year_to_date ("từ đầu năm"), all_time (không nêu kỳ)
- month {month, year}: "tháng 3/2026"; thiếu năm thì year=null
- quarter {quarter, year}; year {year}; last_days {n}: "7 ngày gần nhất"
- date {day, month, year}: một ngày; range {day, month, year, end_day, end_month, end_year}: "từ 01/02/2026 đến hết 07/02/2026"
- month_range {month, year, end_month, end_year}: "từ tháng 6/2025 đến tháng 8/2025"
- tet {year}: "dịp Tết 2026"; before_tet {year}: cùng số ngày ngay trước Tết
- Chỉ cho comparison: previous_period (kỳ liền trước của period: "so với tháng trước/kỳ trước"),
  same_period_last_year ("so với cùng kỳ năm trước")"""

FIELD_HELP = """\
Trường khác (để null nếu không dùng):
- answer_type: number | percent | date | boolean | string | list | unanswerable. Hỏi MỘT đối tượng ("mặt hàng nào", "ai")
  -> string; "top 3", "liệt kê" -> list; "%"/"tỉ lệ"/"tỉ trọng" -> percent; "có ... không" -> boolean; "ngày/tháng nào" -> date.
- product: tên mặt hàng như trong câu hỏi; product_group: tên nhóm hàng; channel: kênh bán; payment: hình thức thanh toán;
  customer_group: nhóm khách; staff: mã nhân viên (vd "NV002"); shift: "sang" | "chieu"; size: "M" | "L".
- unit: đơn vị câu hỏi đếm ("ly", "chai", "kg"...); k: số mục của top/liệt kê (hỏi một đối tượng: k=1).
- metric: top_products quantity|revenue|gross_profit|orders; top_customers revenue|orders; best_period revenue|orders.
- granularity: day|month; kind: max|min; direction: increasing|decreasing.
- min_orders / max_orders: số đơn GỒM hai đầu. "từ N trở lên", "ít nhất N", ">= N" -> min_orders=N;
  "quá/hơn/trên N" -> min_orders=N+1; "dưới N" -> max_orders=N-1.
- weekday: 0=thứ Hai ... 6=Chủ nhật.
- prescription: true = thuốc kê đơn, false = hàng không kê đơn ("trừ thuốc kê đơn ra"); dùng với revenue hoặc prescription_share.
- active_ingredient: hoạt chất đúng như câu hỏi (thuốc phối hợp "A + B" là MỘT loại riêng, giữ nguyên chuỗi).
- days: số ngày N của price_increase_effect; period phải là {"kind":"date",...} = ngày tăng giá D."""

# Ví dụ TỰ VIẾT (không lấy từ train/public): mỗi op chính một ví dụ.
SYNTHETIC = [
    ("Tỉ lệ đơn bị huỷ tháng 4/2026 là bao nhiêu %?",
     {"op": "cancellation_rate", "answer_type": "percent", "period": {"kind": "month", "month": 4, "year": 2026}}),
    ("Giá trị trung bình mỗi đơn tuần trước là bao nhiêu?",
     {"op": "average_order_value", "answer_type": "number", "period": {"kind": "previous_week"}}),
    ("Hôm qua cửa hàng bán được mấy đơn?", {"op": "order_count", "answer_type": "number", "period": {"kind": "yesterday"}}),
    ("Doanh thu quý 1 năm 2026 là bao nhiêu?",
     {"op": "revenue", "answer_type": "number", "period": {"kind": "quarter", "quarter": 1, "year": 2026}}),
    ("Doanh thu tháng 5/2026 thay đổi bao nhiêu % so với tháng liền trước?",
     {"op": "revenue_growth", "answer_type": "percent", "period": {"kind": "month", "month": 5, "year": 2026},
      "comparison": {"kind": "previous_period"}}),
    ("Từ đầu tháng này đến hôm nay doanh thu tăng hay giảm bao nhiêu % so với cùng kỳ tháng trước?",
     {"op": "revenue_growth", "answer_type": "percent", "period": {"kind": "this_month"},
      "comparison": {"kind": "previous_period"}}),
    ("Cho tôi 3 khách mua nhiều tiền nhất tháng 2/2026",
     {"op": "top_customers", "answer_type": "list", "period": {"kind": "month", "month": 2, "year": 2026},
      "metric": "revenue", "k": 3}),
    ("Tháng 1/2026 khách nào mua nhiều đơn nhất?",
     {"op": "top_customers", "answer_type": "string", "period": {"kind": "month", "month": 1, "year": 2026},
      "metric": "orders", "k": 1}),
    ("Mặt hàng nào bán chạy nhất tháng 9/2025?",
     {"op": "top_products", "answer_type": "string", "period": {"kind": "month", "month": 9, "year": 2025},
      "metric": "quantity", "k": 1}),
    ("Tháng 4/2026 bán được bao nhiêu chai Nước suối 500ml?",
     {"op": "quantity", "answer_type": "number", "period": {"kind": "month", "month": 4, "year": 2026},
      "product": "Nước suối 500ml", "unit": "chai"}),
    ("Top 5 món bán chạy nhất 7 ngày gần nhất",
     {"op": "top_products", "answer_type": "list", "period": {"kind": "last_days", "n": 7}, "metric": "quantity", "k": 5}),
    ("Nhóm hàng Đồ uống chiếm bao nhiêu % doanh thu tháng 3/2026?",
     {"op": "revenue_share", "answer_type": "percent", "period": {"kind": "month", "month": 3, "year": 2026},
      "product_group": "Đồ uống"}),
    ("Doanh thu các đơn thanh toán chuyển khoản tháng này là bao nhiêu?",
     {"op": "revenue", "answer_type": "number", "period": {"kind": "this_month"}, "payment": "chuyển khoản"}),
    ("Khách nhóm sỉ mua bao nhiêu tiền trong tháng 6/2026?",
     {"op": "revenue", "answer_type": "number", "period": {"kind": "month", "month": 6, "year": 2026},
      "customer_group": "sỉ"}),
    ("Thuốc kê đơn chiếm bao nhiêu % doanh thu tháng 6/2026?",
     {"op": "prescription_share", "answer_type": "percent", "period": {"kind": "month", "month": 6, "year": 2026},
      "prescription": True}),
    ("Trừ thuốc kê đơn ra, tháng 2/2026 các mặt hàng còn lại bán được bao nhiêu tiền?",
     {"op": "revenue", "answer_type": "number", "period": {"kind": "month", "month": 2, "year": 2026},
      "prescription": False}),
    ("Thuốc có hoạt chất Cetirizin tháng 3/2026 bán được bao nhiêu tiền?",
     {"op": "revenue", "answer_type": "number", "period": {"kind": "month", "month": 3, "year": 2026},
      "active_ingredient": "Cetirizin"}),
    ("Từ ngày 05/02/2026, Nước suối 500ml tăng giá lên 6.000đ. 7 ngày kể từ ngày đó so với 7 ngày ngay trước, "
     "số chai bán ra thay đổi bao nhiêu %?",
     {"op": "price_increase_effect", "answer_type": "percent", "product": "Nước suối 500ml", "days": 7,
      "period": {"kind": "date", "day": 5, "month": 2, "year": 2026}}),
    ("Đến hết hôm nay khách còn nợ bao nhiêu tiền?", {"op": "unsupported"}),
    ("Nhân viên nào phục vụ khách vui vẻ nhất?", {"op": "unanswerable", "answer_type": "unanswerable"}),
]


def system_prompt() -> str:
    ops = "\n".join(f"- {name}: {desc} [answer_type: {'|'.join(types) or '-'}]" for name, (types, _, desc) in OPS.items())
    examples = "\n".join(f"Hỏi: {q}\nSpec: {canonical(s)}" for q, s in SYNTHETIC)
    return f"""Bạn chuyển câu hỏi tiếng Việt về dữ liệu bán hàng của một cửa hàng nhỏ thành MỘT spec JSON.
Bạn KHÔNG tính số, KHÔNG tính ngày, KHÔNG trả lời câu hỏi: chương trình sẽ tính theo spec.
Câu hỏi có thể viết tắt, không dấu, sai chính tả (dthu = doanh thu, bn/bnhiu = bao nhiêu, hnay = hôm nay, hqua = hôm qua).
"Bán được bao nhiêu tiền", "tiền hàng", "thu về" = doanh thu (op revenue).

Danh sách op (chỉ dùng các op này):
{ops}

{PERIOD_HELP}

{FIELD_HELP}

Nguyên tắc:
- Câu hỏi về công nợ, tồn kho, nhập hàng, nhà cung cấp, hạn dùng/lô, giao hàng, tăng giá, chi phí, lãi ròng, bảo hành,
  hoạt chất, thuốc kê đơn, hoặc cần phép tính mà không op nào làm đúng -> op "unsupported".
- Ý kiến, cảm nhận, kiến thức bên ngoài (không thể có trong sổ bán hàng) -> op "unanswerable".
- Không chắc op hoặc tham số -> "unsupported". Không bịa tên, mã, số.

Ví dụ minh hoạ:
{examples}"""


def user_prompt(question: str, as_of: str, card: str) -> str:
    return f"Thông tin cửa hàng:\n{card}\nHôm nay (as_of_date): {as_of}\n\nCâu hỏi: {question}\nTrả về spec JSON."


def messages(question: str, as_of: str, card: str, shots: list[dict]) -> list[dict]:
    """system -> các cặp few-shot (user/assistant) -> câu hỏi."""
    msgs = [{"role": "system", "content": system_prompt()}]
    for ex in shots:
        msgs.append({"role": "user", "content": f"Câu hỏi: {ex['question']}\nTrả về spec JSON."})
        msgs.append({"role": "assistant", "content": canonical(ex["spec"])})
    msgs.append({"role": "user", "content": user_prompt(question, as_of, card)})
    return msgs
