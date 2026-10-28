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
sales.average_order_value(periods.this_month())
sales.quantity(periods.this_month(), unit='chai')
sales.top_products(periods.this_month(), k=3, metric='quantity')
sales.top_customers(periods.this_month(), k=3, metric='revenue')
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
| `cancellation_rate(period)` | percent, mẫu số là mọi trạng thái |
| `average_order_value(period, filters)` | number, làm tròn half-up về đồng |
| `quantity(period, filters, unit=None)` | number, tổng số lượng đơn vị cơ bản |
| `top_products(period, k=5, metric='quantity', filters=...)` | list tên hàng; metric `quantity`, `revenue`, `gross_profit` (§3 Hàng lời nhất), `orders` (số đơn có mặt hàng) |
| `top_customers(period, k=5, metric='revenue')` | list tên khách, metric revenue hoặc orders |
| `revenue_growth(period, comparison, filters)` | percent, (kỳ hỏi − kỳ so)/kỳ so |
| `revenue_share(period, filters)` | percent, doanh thu bộ lọc/doanh thu cả shop |

### API mở rộng

| API | Kết quả | Luật (đọc lúc chạy) |
|---|---|---|
| `best_period(period, granularity='day'\|'month', metric='revenue'\|'orders', kind='max'\|'min', filters)` | date `YYYY-MM-DD` / `YYYY-MM` | §1, §9 bằng nhau. Ngày/tháng không có đơn trong khoảng dữ liệu = 0; bằng nhau lấy kỳ sớm hơn |
| `revenue_series(periods, filters)` | list số theo đúng thứ tự `periods` | §1, §9 "list theo đúng thứ tự câu hỏi nêu" |
| `is_monotonic(periods, direction='increasing'\|'decreasing', filters)` | boolean; bằng nhau không tính là tăng/giảm | §1 |
| `price_on_date(product_id, day)` | number: đơn giá một đơn vị cơ bản, trước chiết khấu dòng, cả đơn huỷ/trả | §5 Giá bán X ngày D (**chỉ có ở rulebook train**) |
| `slow_moving_products(period, as_list=False, filters)` | number, hoặc list tên theo mã tăng dần | §5 Mặt hàng không bán được trong kỳ (ế) |
| `gross_profit(period, filters)` | number: doanh thu − Σ số lượng × giá vốn ghi trên dòng | §5 Lãi gộp |
| `customer_count(period, min_orders=None, max_orders=None)` | number: khách đã mua có số đơn trong [min, max] (gồm hai đầu) | §1 Số đơn, §2 Quá N/Từ N, §3 Xác định khách |
| `customer_share(period, min_orders=None, max_orders=None)` | percent trên số khách đã mua trong kỳ | như trên |
| `products_in_at_least(period, n, filters)` | number: mặt hàng có mặt trong ≥ n đơn hợp lệ | §1 Số đơn, §3 Mặt hàng |
| `top_staff(period, k=5)` | list mã nhân viên theo doanh thu | §3 Nhân viên bán giỏi nhất |
| `Answer.single()` | list xếp hạng → string phần tử đầu (câu hỏi một đối tượng) | §9 |

Số đơn có một mặt hàng (C8) và doanh thu/số lượng của một mặt hàng (C2) dùng API sẵn có: `order_count(period, Filters(product_ids=...))`, `revenue(...)`, `quantity(...)`.

Với điều kiện số đơn, tầng hiểu câu hỏi đổi cách nói theo §2: "từ N trở lên", "ít nhất N", "≥ N" → `min_orders=N`; "quá/hơn/trên N" → `min_orders=N+1`; "dưới N" → `max_orders=N-1`.

### Nhà thuốc (§6) và hiệu ứng tăng giá (§5)

Loader có thêm hai bảng chuẩn (tuỳ chọn, nạp vào `SalesMetrics` nếu có file):
`thuoc(ma_hang, hoat_chat, ke_don)` lấy từ danh mục thuốc, `bang_gia(ma_hang, ngay_ap_dung, gia)` lấy từ bảng/lịch sử giá. Hoạt chất giữ nguyên chuỗi của danh mục.

| API | Kết quả | Luật |
|---|---|---|
| `revenue/quantity/...(period, Filters(prescription=True\|False))` | thuốc kê đơn / mọi sản phẩm còn lại | Thuốc kê đơn |
| `prescription_share(period, prescription=True)` | percent: doanh thu phần lọc / doanh thu cả shop | Thuốc kê đơn ("tỉ lệ kê đơn tính theo doanh thu") |
| `revenue/...(period, Filters(active_ingredient='...'))` | doanh thu thuốc có hoạt chất ghi **đúng** như vậy; thuốc phối hợp là loại riêng | Doanh thu theo hoạt chất |
| `price_increase_effect(product_id, day, n)` | percent: số lượng cơ bản N ngày từ D (gồm D) so với N ngày ngay trước D, bỏ đơn huỷ/trả | Hiệu ứng tăng giá |

- Không có danh mục thuốc, hoặc danh mục không ghi cờ kê đơn / hoạt chất: unanswerable. Hoạt chất không có trong danh mục: unanswerable.
- `price_increase_effect`: mặt hàng có trong `bang_gia` thì D phải là lần tăng (giá mới > giá liền trước; tăng lên cùng một giá nhiều lần chỉ tính lần đầu), không thì `DataError`. Số lượng N ngày trước D bằng 0: unanswerable.
- **CHƯA CHẮC:** tiệm không có bảng giá thì tin ngày D do câu hỏi nêu (không kiểm chứng được D là lần tăng). Train có 84 câu tăng giá nhưng chỉ vài tiệm có bảng giá.
- **Hạn chế loader:** tiệm biz_123 ghi hoạt chất ở cột `ThanhPhanChinh` mà README không gọi tên đó là "hoạt chất", nên cột để unmapped; các câu hoạt chất của tiệm đó chưa trả lời được.

### Luật chỉ có trong rulebook public

Mỗi API đòi đúng dòng luật bằng `Rulebook.require`. Chạy với rulebook train sẽ ra `UnsupportedRule`. Không có đáp án gold nên **chỉ kiểm bằng test tổng hợp**.

| API | Dòng luật | Kết quả |
|---|---|---|
| `loyal_customers(period, k=1)` | Khách trung thành nhất | list tên khách, nhiều ngày có mua nhất |
| `big_spender_customers(period, k=1)` | Khách sộp nhất | list tên khách, giá trị trung bình một đơn cao nhất; ngưỡng "từ N đơn" đọc từ luật |
| `fickle_customers(period, k=1)` | Khách hay đổi ý nhất | list tên khách, nhiều đơn huỷ nhất |
| `favorite_products(period, k=1, filters)` | Mặt hàng được ưa chuộng nhất | list tên hàng, có mặt trong nhiều đơn nhất |
| `hardworking_staff(period, k=1)` | Nhân viên, thợ chăm chỉ nhất | list mã nhân viên, nhiều ngày làm việc nhất |
| `busiest_day(period)` | Ngày đắt khách nhất | date, ngày nhiều đơn nhất |
| `peak_hour(period)` | Giờ cao điểm | number, giờ bắt đầu khung một giờ nhiều đơn nhất |
| `weekday_average(period, weekday, metric='revenue'\|'orders')` | Trung bình mỗi ngày thứ X của kỳ | number; chia cho số ngày thứ X trong kỳ (0 = thứ Hai), kể cả ngày không có đơn |

### CHƯA CHẮC

- `price_on_date`: nhiều mức giá khác nhau trong cùng ngày → `DataError`, vì rulebook không nói chọn mức nào.
- `best_period(kind='min')`: ngày không có đơn trong khoảng dữ liệu được tính là 0. Kỳ bằng nhau: lấy kỳ sớm hơn (§9 "không có mã thì theo tên"). Train không có câu nào kiểm chứng biến thể này → kết quả mang `confidence='low'`.
- `slow_moving_products`: kỳ bắt đầu từ ngày đầu dữ liệu trở về trước → unanswerable, vì không có dữ liệu "trước kỳ".
- `gross_profit`: dòng phí phục vụ không có giá vốn được tính giá vốn 0; dòng hàng/topping thiếu giá vốn → `DataError`.
- `hardworking_staff`: ngày làm việc chỉ tính đơn hợp lệ, bỏ đơn huỷ/trả. Lý do: nhất quán với định nghĩa "số đơn" ở §1 ("chỉ tính đơn không huỷ, không trả"). Phiếu bảo hành không phải đơn huỷ/trả nên vẫn được tính, đúng như rulebook public ghi "kể cả phiếu bảo hành".
- `peak_hour`: bằng nhau lấy giờ sớm hơn.
- Mọi API C10 (luật chỉ có ở rulebook public, không có gold) trả `confidence='low'`.

### Độ tin cậy (`Answer.confidence`)

`Answer` có thêm trường `confidence`: `'normal'` (mặc định) hoặc `'low'`. `'low'` nghĩa là cách tính chưa có câu train nào kiểm chứng; tầng agent có thể dựa vào đó để abstain (sai bị −1, bỏ trống được 0). Trường này **không** ghi vào `to_submission`. `single()` giữ nguyên độ tin cậy của list gốc. Kết quả unanswerable do thiếu dữ liệu không bị hạ độ tin cậy.

| API | confidence |
|---|---|
| `best_period(kind='min')` | low |
| `loyal_customers`, `big_spender_customers`, `fickle_customers`, `favorite_products`, `hardworking_staff`, `busiest_day`, `peak_hour`, `weekday_average` | low |
| các API còn lại | normal (đã có câu train khớp gold, hoặc là bản gốc đã kiểm chứng 409/409) |

`Filters` hỗ trợ `product_ids` (tuple mã hàng), `product_group`, `channel`, `payment`, `customer_group`, `shift` (`sang`/`chieu`), `size` (`M`/`L`: tên món kết thúc `(M)`/`(L)`, không phân biệt hoa thường, theo luật ngành cà phê) và `staff` (mã nhân viên ghi trên đơn). Truyền mã/nhãn đúng trong schema chuẩn; việc khớp tên, alias và cách nói thuộc tầng hiểu câu hỏi. Bộ lọc sản phẩm áp lên dòng hàng; bộ lọc kênh/thanh toán/khách/ca áp lên đơn. Với AOV có bộ lọc sản phẩm, tử số là doanh thu các dòng được lọc và mẫu số là số đơn có các dòng đó.

Doanh thu gồm phí phục vụ/topping, không trừ voucher cấp đơn, không cộng ship/VAT. Xếp hạng và số lượng mặt hàng bỏ phí phục vụ, có topping. Hủy/trả loại cả đơn, đang giao vẫn tính. Khi không có bảng dòng hàng, chỉ doanh thu toàn đơn có thể dùng `tong_tien_hang`, không suy từ tiền đã thu hoặc tổng phải trả.

## Kết quả thiếu dữ liệu và giới hạn

- `Answer(type, answer, reason, confidence)` và `to_submission(question_id)` tạo JSON object; chưa phải runner xuất toàn bộ submission.
- Không có loại thông tin cần thiết, ngoài khoảng dữ liệu, hoặc mẫu số bằng 0: `Answer('unanswerable', reason=...)`.
- Dữ liệu chuẩn có khóa trùng, ngày/status sai, giá trị liên quan thiếu một phần: `DataError`. Tầng agent cần sửa mapping hoặc abstain; không tự đổi lỗi này thành đáp án 0.
- `UnsupportedRule`: điều khoản được dùng thiếu hoặc khác các mẫu mà bản này hỗ trợ. Cần bổ sung implementation/kiểm thử, hoặc agent abstain. Đây không phải kết luận câu hỏi không có đáp án trong dữ liệu.
- Rulebook được đọc từ file người gọi truyền, có source và SHA256. Bản này kiểm tra các cụm điều khoản cần thiết cho thao tác; không phải bộ suy luận ngôn ngữ tự nhiên cho mọi cách viết hoặc mọi thay đổi của rulebook. Cần rà soát lại khi BTC cập nhật luật.
- Đếm đơn/AOV/tỷ lệ hủy cần mã đơn thật (`co_ma_don`); mã nhân tạo của loader chỉ phục vụ nối dòng hàng.
- `quantity(unit=None)` cộng số lượng cơ bản của mọi hàng; người gọi phải bảo đảm đó là phép cộng mà câu hỏi yêu cầu. Chỉ định `unit` để cộng riêng một đơn vị cơ bản.
- Chưa hỗ trợ kho, nhập, nợ, lãi ròng, lô/hạn dùng và phần lớn luật ngành (đã có: size cà phê, lãi gộp từ giá vốn dòng). Thiếu tính năng không đồng nghĩa dữ liệu unanswerable. Các bảng đó cần được loader chuẩn hóa trước.
- Thư viện dựa trên cache đã làm sạch; không khôi phục số lượng hoặc quan hệ mà loader ánh xạ sai. Test/kiểm tra loader vẫn cần thiết.

## Kiểm chứng

```powershell
python -m pytest -q
python verify_business.py --train train --cache cache --out reports/business_verification
```

Verifier ghi `.json` và `.md`. Phần cũ dùng cùng bộ chọn câu bảo thủ của `check_with_gold.py`; phần mở rộng có bộ chọn regex riêng cho C1–C9, chấm bằng `evaluate.score_one` và in 5 câu lệch/lỗi đầu tiên mỗi loại. Phần cũ: báo tổng câu train, số được chọn, số bị bỏ qua, số lỗi, số khớp gold và phép tính cũ. Đây là kiểm chứng hồi quy trên tập con, không phải PA toàn bộ train. Chỉ công cụ kiểm chứng bên ngoài `business/` đọc gold.

Baseline trước thay đổi: `reports/gold_before_business.md`, 263/263 câu doanh thu/hủy và 146/146 câu số lượng/ca. Test của thư viện dùng dữ liệu tổng hợp; file cuộc thi không được thêm vào Git.
