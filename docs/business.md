# Thư viện nghiệp vụ trên schema chuẩn

`business/` là tầng tính toán tất định. Tầng hiểu câu hỏi gọi API bằng tham số rõ ràng; thư viện không nhận câu hỏi tự nhiên và không đọc đáp án train.

## Ví dụ

Chạy từ gốc repo sau khi đã chạy `load_all.py`:

```python
from business import Filters, Periods, Rulebook, SalesMetrics

rules = Rulebook.from_path('train/rulebook.md')
periods = Periods(rules, as_of_date='2026-03-04', calendar_path='train/calendar.csv')
sales = SalesMetrics.from_cache('cache/biz_101', 'train/rulebook.md', '2026-03-04')

answer = sales.revenue(periods.this_month())
print(answer.to_submission('example'))

sales.revenue(periods.this_month(), Filters(shift='sang'))
sales.order_count(periods.previous_week())
sales.cancelled_orders(periods.this_month())
sales.cancellation_rate(periods.this_month())
sales.cancellation_rate(periods.this_month(), Filters(channel='online'))
sales.average_order_value(periods.this_month())
sales.quantity(periods.this_month(), unit='chai')
sales.top_products(periods.this_month(), k=3, metric='quantity')
sales.top_customers(periods.this_month(), k=3, metric='revenue')
sales.top_customers(periods.this_month(), k=3, metric='revenue', filters=Filters(channel='online'))
sales.revenue_growth(periods.this_month(), periods.previous_month(same_elapsed=True))
sales.revenue_share(periods.this_month(), Filters(product_group='Đồ uống'))

tet = periods.tet(2026)
sales.revenue_growth(tet, periods.before(tet))
```

Thay đường dẫn cache bằng doanh nghiệp cần hỏi. Với public test, truyền `public_test/rulebook.md` và `public_test/calendar.csv`. Các ID chỉ dùng để chọn dữ liệu/ghi kết quả, không tham gia luật tính toán.

## Thời gian

- `DateRange(start, end)` nhận ngày ISO hoặc `datetime.date`, gồm cả hai đầu.
- `today()`, `yesterday()`, `last_days(n)`, `this_week()`, `previous_week()`, `this_month()`, `previous_month()`, `year_to_date()`.
- `month(month, year=None)`, `quarter(quarter, year=None)`: thiếu năm thì chọn năm nay nếu đầu kỳ không sau as_of_date, ngược lại chọn năm trước. Có năm thì trả cả kỳ.
- `previous_month(same_elapsed=True)` dùng để so với tháng này: cùng số ngày, chặn ở cuối tháng trước.
- `tet(year)` đọc hai mốc âm trong calendar được truyền vào, không dùng lịch từ Internet; `before(period)` lấy kỳ liền trước có cùng số ngày.
- Phép tính giao kỳ hỏi với khoảng dữ liệu và as_of_date. Kỳ giao một phần vẫn tính phần có dữ liệu; hoàn toàn ngoài khoảng thì unanswerable.

## Phép tính và bộ lọc

| API | Kết quả |
|---|---|
| `revenue(period, filters)` | number, tiền VND |
| `order_count(period, filters)` | number, số đơn hợp lệ |
| `cancelled_orders(period, filters)` | number, số đơn hủy |
| `cancellation_rate(period, filters=...)` | percent, mẫu số là mọi trạng thái trong cùng bộ lọc cấp đơn |
| `average_order_value(period, filters)` | number, làm tròn half-up về đồng |
| `quantity(period, filters, unit=None)` | number, tổng số lượng đơn vị cơ bản |
| `top_products(period, k=5, metric='quantity', filters=...)` | list tên hàng, metric quantity hoặc revenue |
| `top_customers(period, k=5, metric='revenue', filters=...)` | list tên khách, metric revenue hoặc orders |
| `revenue_growth(period, comparison, filters)` | percent, (kỳ hỏi − kỳ so)/kỳ so |
| `revenue_share(period, filters)` | percent, doanh thu bộ lọc/doanh thu cả shop |

`Filters` hỗ trợ `product_ids` (tuple mã hàng), `product_group`, `channel`, `payment`, `customer_group`, `shift` (`sang`/`chieu`). Truyền mã/nhãn đúng trong schema chuẩn; việc khớp tên, alias và cách nói thuộc tầng hiểu câu hỏi. Bộ lọc sản phẩm áp lên dòng hàng; bộ lọc kênh/thanh toán/khách/ca áp lên đơn. Với AOV có bộ lọc sản phẩm, tử số là doanh thu các dòng được lọc và mẫu số là số đơn có các dòng đó.

`cancellation_rate` và `top_customers` nhận bộ lọc cấp đơn (`channel`, `payment`, `customer_group`, `shift`); truyền `product_ids` hoặc `product_group` vào hai API này phát sinh `UnsupportedRule`. `top_customers` giữ nguyên thứ tự tham số cũ; `filters` được thêm ở cuối. Tỷ trọng vẫn chia cho doanh thu cả shop cùng kỳ; chỉ yêu cầu điều khoản nhóm khách khi bộ lọc đó được dùng.

Doanh thu gồm phí phục vụ/topping, không trừ voucher cấp đơn, không cộng ship/VAT. Xếp hạng và số lượng mặt hàng bỏ phí phục vụ, có topping. Hủy/trả loại cả đơn, đang giao vẫn tính. Khi không có bảng dòng hàng, chỉ doanh thu toàn đơn có thể dùng `tong_tien_hang`, không suy từ tiền đã thu hoặc tổng phải trả.

## Kết quả thiếu dữ liệu và giới hạn

- `Answer(type, answer, reason)` và `to_submission(question_id)` tạo JSON object; chưa phải runner xuất toàn bộ submission.
- Không có loại thông tin cần thiết, ngoài khoảng dữ liệu, hoặc mẫu số bằng 0: `Answer('unanswerable', reason=...)`.
- Dữ liệu chuẩn có khóa trùng, ngày/status sai, giá trị liên quan thiếu một phần: `DataError`. Tầng agent cần sửa mapping hoặc abstain; không tự đổi lỗi này thành đáp án 0.
- Đầu vào phải có đủ `don_hang`, `dong_hang`, `mat_hang` là DataFrame và `cua_hang` là dict; thiếu bảng hoặc sai kiểu là `DataError`. Bảng không có loại thông tin được biểu diễn bằng bảng rỗng đúng cấu trúc, không bằng cách xóa key.
- Kiểm tra khóa sản phẩm và liên kết dòng hàng chạy khi metric phụ thuộc chúng. Catalog lỗi hoặc dòng mồ côi không chặn đếm đơn thuần; vẫn chặn các thao tác cần tra cứu sản phẩm hoặc đọc dòng hàng. Không bỏ dòng mồ côi chỉ vì không nối được với đơn trong kỳ.
- Với metric loại hủy/trả, trạng thái hủy/trả đã xác định được loại trước khi kiểm tra bộ lọc cấp đơn. Trạng thái chưa biết chỉ được bỏ qua khi các trường hợp lệ khác chứng minh đơn ngoài phạm vi truy vấn. Tỷ lệ hủy giữ mọi trạng thái trong mẫu số và vẫn kiểm tra các trường cần lọc.
- `UnsupportedRule`: điều khoản được dùng thiếu hoặc khác các mẫu mà bản này hỗ trợ. Cần bổ sung implementation/kiểm thử, hoặc agent abstain. Đây không phải kết luận câu hỏi không có đáp án trong dữ liệu.
- Rulebook được đọc từ file người gọi truyền, có source và SHA256. Bản này kiểm tra các cụm điều khoản cần thiết cho thao tác; không phải bộ suy luận ngôn ngữ tự nhiên cho mọi cách viết hoặc mọi thay đổi của rulebook. Cần rà soát lại khi BTC cập nhật luật.
- Đếm đơn/AOV/tỷ lệ hủy cần mã đơn thật (`co_ma_don`); mã nhân tạo của loader chỉ phục vụ nối dòng hàng.
- `quantity(unit=None)` cộng số lượng cơ bản của mọi hàng; người gọi phải bảo đảm đó là phép cộng mà câu hỏi yêu cầu. Chỉ định `unit` để cộng riêng một đơn vị cơ bản.
- Chưa hỗ trợ kho, nhập, nợ, lãi, lô/hạn dùng và toàn bộ luật ngành. Thiếu tính năng không đồng nghĩa dữ liệu unanswerable. Các bảng đó cần được loader chuẩn hóa trước.
- Thư viện dựa trên cache đã làm sạch; không khôi phục số lượng hoặc quan hệ mà loader ánh xạ sai. Test/kiểm tra loader vẫn cần thiết.

## Kiểm chứng

```powershell
python -m pytest -q
python verify_business.py --train train --cache cache --out reports/business_verification
```

Verifier ghi `.json` và `.md`, dùng cùng bộ chọn câu bảo thủ của `check_with_gold.py`: báo tổng câu train, số được chọn, số bị bỏ qua, số lỗi, số khớp gold và phép tính cũ. Đây là kiểm chứng hồi quy trên tập con, không phải PA toàn bộ train. Chỉ công cụ kiểm chứng bên ngoài `business/` đọc gold.

Baseline trước thay đổi: `reports/gold_before_business.md`, 263/263 câu doanh thu/hủy và 146/146 câu số lượng/ca. Test của thư viện dùng dữ liệu tổng hợp; file cuộc thi không được thêm vào Git.
