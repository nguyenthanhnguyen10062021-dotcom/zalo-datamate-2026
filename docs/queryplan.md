# QueryPlan executor v1

`queryplan/` nhận JSON plan đã được tầng trước trích xuất, kiểm tra và gọi public API `business/`. Bản này chưa hiểu câu hỏi tiếng Việt, chưa tích hợp model và chưa có runner submission. Không thêm dependency; validator Python thực hiện contract dưới đây, chưa có JSON Schema cho constrained decoding.

## Gọi executor

Caller đưa bảng chuẩn vào `tables`, cùng `Rulebook`, ngày câu hỏi và calendar đúng split. Loader/cache loading nằm ngoài executor. Dữ liệu chỉ đọc.

```python
from business import Rulebook
from queryplan import QueryExecutor

executor = QueryExecutor(
    tables, Rulebook.from_path('train/rulebook.md'),
    as_of_date='2026-03-04', calendar_path='train/calendar.csv',
)
plan = {
    'version': '1.0', 'status': 'supported', 'unsupported_reason': None,
    'operation': 'quantity', 'expected_type': 'number',
    'period': {
        'kind': 'this_month', 'n': None, 'month': None, 'quarter': None,
        'year': None, 'start_date': None, 'end_date': None,
    },
    'comparison_period': None,
    'filters': {
        'product_mentions': None, 'product_group_mention': None,
        'channel_mention': None, 'payment_mention': None,
        'customer_group_mention': None, 'shift': None, 'unit_mention': 'ly',
    },
    'ranking': None,
}
result = executor.execute(plan)  # dict từ json.loads cũng dùng được
print(result.status, result.stage, result.answer)
submission_row = result.answer.to_submission('example')
```

Chỉ ghi `submission_row` không giữ được phân loại lỗi nội bộ; caller nên ghi thêm `status`, `stage` và reason vào báo cáo local ignored. Executor không tự ghi log/file. Một instance có thể execute nhiều plan; không cache kết quả nên caller không được sửa bảng giữa các lần hỏi nếu cần cùng snapshot.

## Contract

Mọi object phải đủ key như ví dụ; không nhận key lạ. Trường không dùng phải `null` (`None` trong Python). `validate_plan(raw)` trả dict độc lập sau normalize → structural → semantic validation; lỗi phát sinh `PlanValidationError` có `stage`. `execute` chuyển lỗi này thành `invalid_plan`/abstain.

- Số nguyên: chấp nhận `1.0` hữu hạn và chuẩn hóa thành `int`; reject bool, chuỗi số, số lẻ, NaN/Infinity. `k,n > 0`; month 1..12; quarter 1..4; year 1..9999.
- Mention: chuỗi không rỗng sau strip; `product_mentions` là list chuỗi hoặc null. `[]` chuẩn hóa thành null, không thành bộ lọc rỗng trả 0.
- `expected_type`: number cho revenue/order_count/cancelled_orders/average_order_value/quantity; percent cho cancellation_rate/revenue_growth/revenue_share; list cho top_products/top_customers. Phần trăm tăng trưởng có thể âm hoặc lớn hơn 100.
- `ranking`: bắt buộc với top_products/top_customers, gồm `k` và `metric`; operation khác phải null. Top products nhận quantity/revenue, top customers nhận revenue/orders.
- `unit_mention` chỉ dùng với quantity. Cancellation rate/top customers chỉ nhận filter cấp đơn. Share phải có filter thực sau normalize và luôn có mẫu số cả shop. Xem [ngữ nghĩa API](business.md).

### Thời gian

Period luôn có kind,n,month,quarter,year,start_date,end_date. Các kind today/yesterday/this_week/previous_week/this_month/previous_month/previous_month_same_elapsed/year_to_date không cần tham số; last_days cần n; month cần month và year tùy chọn; quarter tương tự; tet cần year; date_range cần hai ngày ISO tồn tại và không đảo đầu/cuối. Các tham số không dùng phải null.

Comparison chỉ dùng cho revenue_growth, nhận yesterday/previous_week/previous_month/previous_month_same_elapsed/month/quarter/tet/date_range/before_period. `before_period` chỉ áp dụng khi kỳ chính là tet. Comparison same_elapsed chỉ áp dụng với this_month. Growth this_month có comparison null sẽ dùng cùng số ngày tháng trước theo rulebook; growth với kỳ chính khác phải có comparison. `previous_month` tường minh nghĩa cả tháng trước: tầng NLU tương lai phải chọn theo câu hỏi, không tự đổi mặc định.

Resolver gọi `Periods` hiện hành, không tự tính lại lịch, không tra Internet. Tháng/quý thiếu năm, kỳ giao một phần và giới hạn as_of_date theo [API thời gian](business.md). Lỗi/mất calendar báo period_error; rule chưa hỗ trợ báo unsupported_rule.

Adapter kiểm tra header/ô bắt buộc, lunar_leap và hai mốc Tết của CSV trước khi gọi API. Chỉ lỗi đọc/parse input ở boundary đó được đổi thành PeriodResolutionError; không bắt chung ValueError/KeyError từ các hàm Periods. Kỳ vượt phạm vi ngày biểu diễn được được kiểm tra tường minh và báo period_error.

### Resolve tên và đơn vị

Khóa so khớp dùng NFC, casefold và gộp khoảng trắng; giữ dấu tiếng Việt/dấu câu. Không fuzzy, không synonym tự đoán. Product mention là **tên hàng** trong catalog, chưa hỗ trợ cú pháp chọn mã. Nhiều mã cùng tên là ambiguous, kể cả cùng nhóm/đơn vị; không tự cộng nhiều mã. Mention lặp cùng mã chỉ lọc một lần.

Nhóm hàng, kênh, thanh toán, nhóm khách trả nhãn raw đúng schema cho business. Nếu nhiều nhãn raw khác nhau có cùng khóa chuẩn hóa, báo ambiguous vì chọn một nhãn sẽ làm mất dòng. Nhãn cấp đơn chỉ tra trong đơn đến as_of_date, nhưng không giới hạn vào kỳ hỏi: một nhãn đã biết có thể có doanh số 0 trong kỳ. Đơn vị trả tường minh, chuẩn hóa giống quantity của business.

Không có cột/toàn bộ thông tin cần resolve bị thiếu → unanswerable ở stage resolve. Có thông tin nhưng mention không khớp → unresolved_entity/abstain. Catalog thiếu/trùng mã, một phần tên hàng thiếu hoặc nhãn sai kiểu → data_error. Các lỗi dữ liệu tính toán khác do business kiểm tra theo dependency; resolver không kiểm tra catalog khi đếm đơn không có filter sản phẩm.

### Plan không hỗ trợ

`status='unsupported'` cần unsupported_reason thuộc unsupported_domain/unsupported_answer_type/unsupported_comparison_or_denominator/ambiguous_question/unparseable_time. Tất cả operation,expected_type,period,comparison_period,filters,ranking phải null. Executor trả unsupported_plan/abstain, không chạm dữ liệu.

## Kết quả và lỗi

`ExecutionResult(answer, status, stage)` giữ `Answer` tương thích API cũ.

| status | Answer.type | Ý nghĩa |
|---|---|---|
| answered | number/percent/list | Business trả thành công |
| unanswerable | unanswerable | Thiếu loại thông tin ở resolve hoặc business xác định không trả lời được; phân biệt bằng stage/reason |
| invalid_plan | abstain | Sai normalize/structure/semantic contract |
| unsupported_plan | abstain | Tầng trước khai báo câu ngoài phạm vi |
| unsupported_capability | abstain | Tổ hợp filter/metric/comparison ngoài v1 |
| unresolved_entity | abstain | Có dữ liệu nhãn nhưng không khớp |
| ambiguous_entity | abstain | Nhiều đối tượng/nhãn cùng khớp |
| data_error | abstain | DataError từ dữ liệu chuẩn |
| unsupported_rule | abstain | UnsupportedRule, không phải dữ liệu không có đáp án |
| period_error | abstain | Không resolve được kỳ/calendar |

Stage: normalize/structure/semantic/capability/period/data/resolve/dispatch. Lỗi implementation bất ngờ và API trả sai answer type phát sinh exception, không bị đổi thành abstain/unanswerable. Caller truyền ngày as_of_date không hợp lệ sẽ lỗi ngay khi khởi tạo.

## Kiểm chứng và phần tiếp theo

Tests dùng bảng/plan/calendar tổng hợp: cả 10 operation có expected value độc lập và đối chiếu public API; kiểm tra resolver, thời gian, lỗi, capability và input bất biến. Chạy `python -m pytest tests/test_queryplan_contract.py tests/test_queryplan_executor.py -q`, rồi harness full/data.

Verifier legacy vẫn chỉ gọi business trên tập chọn lọc. Đã có [inventory và verifier độc lập](capability-verification.md) chạy QueryExecutor trên frozen manifest bằng grammar dev bảo thủ; chưa có model NLU. Tiếp theo cần audit/mở rộng plan coverage độc lập gold rồi tích hợp model offline và đo riêng plan correctness/kết quả đầu-cuối. Chưa tuyên bố PA của model từ unit test, bộ manifest hồi cứu hoặc 409 câu legacy.
