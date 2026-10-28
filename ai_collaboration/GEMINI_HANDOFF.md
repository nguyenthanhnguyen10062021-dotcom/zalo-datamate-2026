# DataMate handoff to Gemini

Round: 001_business_to_nlu
Snapshot date: 2026-10-28 (Asia/Saigon)
Code commit: 1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b
Code permalink: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b
Working branch: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/VuongNguyen
Business source and tests below are committed at the code commit above.
Collaboration documents are packaged in the next commit on the same branch.
This file is self-contained. Local paths are provenance labels, not remotely accessible links.
Hashes identify UTF-8 file text with line endings normalized to LF (Windows CRLF does not affect them).
No Gemini response has been received yet. Proposals are not settled decisions.
Competition data, real questions/answers, cache, model weights and environment files are not included.
Loader and evaluator source are not included; request them before making source-level claims about those modules.

## Included files and SHA256

| File | SHA256 (UTF-8 / LF) |
|---|---|
| ai_collaboration/GEMINI_START_PROMPT.md | 318e2fa9324ba0580c5ba106661341bf01d1c672368a7c17f150eb3dba30a8ac |
| ai_collaboration/PROJECT_CONTEXT.md | 7ac3e38c8cd123001f46c8cc53fb8c61c8f49782eb3f9ae0b123c23e92af4967 |
| ai_collaboration/rounds/001_business_to_nlu/CODEX_REQUEST.md | 8cdcdb479de7d6d5fc469a4a88e6bb6a201979c5e9407e68ba1357fb9cd2c42a |
| docs/business.md | 21d3bc615c27aee72330c5ecb4231c3201a193939c57459e4efdcaf03e23ba6c |
| docs/validation.md | a05377559cf4ce6b01141f9e7fc07136fab77535b31f7abd6c8d9de70431cd72 |
| business/__init__.py | 6fba13fd1a176b4c1733aeb0bf6207bfc6f6907f49c837b4d5f751248b27d80c |
| business/rules.py | 9d448e1beb1bfc5e488c02cb2a9b872aed0a228efa83bff636c21dfc0d1d3422 |
| business/periods.py | 317f0698d3d6a0130c6410e1994a23805ca99cfdab60681b91635bfb9359b87f |
| business/sales.py | ba8c8d0665564669315a9a8520e4ee40047a03815aa8a14cc4cd683be54870ef |
| tests/conftest.py | 3dee1c3b48aa2b5775600e75c792a54f4ea2757ae0632308f229aa90a18b5cac |
| tests/test_business_periods.py | 7a0fde56862caedf15e4e39a87c0107cdac17273437448adebd572469b7a7d30 |
| tests/test_business_sales.py | c16df5b6fe677011f0f1898c82e36834a6b0b5be77375ce8cef9fdc8f004ed08 |
| tests/test_business_verification.py | 4f20ea057a82771fbf91d16b2e910379e3f1263bcf367c1f38aef1a354e88ef2 |
| verify_business.py | 02b5d8e30d81f8352c1348e6c5989c2f743c4e9302bb7c29eb5600da7880fe95 |

## Instructions

Source: `ai_collaboration/GEMINI_START_PROMPT.md`

Tôi đang phát triển project DataMate cho Zalo AI Challenge 2026 cùng Codex. Tôi muốn bạn tham gia phân tích, phản biện và thảo luận về các quyết định kỹ thuật.

Hãy đọc file GEMINI_HANDOFF.md tôi đính kèm. File có bối cảnh hiện tại, yêu cầu vòng 001 và mã nguồn/test liên quan. Bạn chỉ có snapshot trong file, chưa có quyền truy cập repo hay kết quả chạy mới.

Code nền của vòng này là commit `1c89252`, nhánh `VuongNguyen`:
https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/1c89252

Nếu bạn không đọc được GitHub thì dùng source đính kèm trong handoff; không coi việc không truy cập được link là bằng chứng file không tồn tại.

Hãy trả lời yêu cầu vòng 001 bằng tiếng Việt, theo thứ tự:

1. Tóm tắt điều bạn hiểu về trạng thái project và những gì đã/chưa được kiểm chứng.
2. Các nhận xét kỹ thuật quan trọng, có vị trí trong source snapshot và ví dụ phản chứng nếu có. Tách lỗi được chứng minh khỏi giả thuyết cần kiểm tra.
3. So sánh các hướng triển khai thực sự phù hợp với code hiện tại, đề xuất một hướng và giải thích đánh đổi.
4. Danh sách câu hỏi hoặc phản biện gửi lại Codex, kèm test/thử nghiệm có thể phân định.
5. Việc nhỏ nhất nên làm tiếp và tiêu chí nghiệm thu.

Không mặc nhiên đồng ý với Codex. Cũng không giả định rằng test pass hay 409/409 nghĩa là toàn bộ agent đã chính xác. Nếu thiếu file hoặc không đủ bằng chứng, nêu rõ cần xem gì; không đoán nội dung repo và không tuyên bố đã chạy code khi chưa chạy.

Tôi sẽ chuyển phản hồi của bạn về Codex để kiểm chứng bằng code và test, rồi gửi lại phần trả lời. Hãy phân biệt đề xuất của bạn với quyết định đã được người dùng chốt. Chưa yêu cầu bạn triển khai toàn bộ hệ thống hoặc chọn model cụ thể; trước tiên hãy hoàn thành vòng thảo luận này.

## Project context

Source: `ai_collaboration/PROJECT_CONTEXT.md`

# Bối cảnh project DataMate

Snapshot cập nhật ngày **2026-10-28**, timezone Asia/Saigon. Code nghiệp vụ, test và tài liệu đã commit tại `1c89252` trên nhánh `VuongNguyen`. Gói trao đổi này được commit kế tiếp trên cùng nhánh. SHA256 của nội dung từng file (UTF-8, chuẩn hóa xuống dòng LF) được đính kèm trong `GEMINI_HANDOFF.md`.

Repo: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/VuongNguyen

Phiên bản code cố định: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/1c89252

Gemini web không tự có quyền đọc repo chỉ vì được cung cấp link. Có thể dùng gói handoff tự chứa hoặc yêu cầu đúng source cần bổ sung. Báo cáo kiểm chứng tổng hợp được commit ở `docs/validation.md`; dữ liệu BTC và báo cáo từng câu chỉ có tại local.

## Mục tiêu

Tham gia bài DataMate của Zalo AI Challenge 2026: trả lời câu hỏi tiếng Việt trên CSV, Excel hoặc SQLite của doanh nghiệp nhỏ. Câu hỏi có `as_of_date` làm mốc thời gian. Mỗi split có rulebook và calendar riêng.

Các kiểu đáp án: number, percent, string, date, boolean, list, table, unanswerable; abstain là chủ động bỏ qua. Chấm +1 đúng, -1 sai, 0 bỏ qua. Cần tối ưu PA, đồng thời ghi rõ độ phủ và độ chính xác trên câu đã trả lời.

Theo tài liệu cuộc thi đang lưu trong workspace: tổng tham số các model inference không quá 15B, model công bố trước mốc BTC quy định; inference offline trong Docker. Không bắt logic theo ID doanh nghiệp/câu hỏi; không dùng public/private test để huấn luyện hoặc thu thập đáp án. Đây là tóm tắt tài liệu local, không phải xác nhận rằng thể lệ online chưa thay đổi.

Gemini web là cố vấn phát triển, không được mặc nhiên coi là model chạy trong giải pháp nộp thi. Chưa chọn model inference cuối cùng.

## Môi trường và dữ liệu local

- Windows, PowerShell; Python 3.14.10 trong `.venv/`.
- pandas 3.1.0, numpy 2.5.4, openpyxl 3.1.5, pyarrow 26.0.0, pytest 9.2.0.
- Train: 30 doanh nghiệp, 3000 câu hỏi và đáp án. Public: 14 doanh nghiệp; không có gold public trong workspace.
- Đã giải nén `train/`, `public_test/` đúng README và chạy loader trên 44 doanh nghiệp: 0 crash; checks 236 PASS, 116 bỏ qua, 0 FAIL. Những checks này không chứng minh mapping đúng cho mọi câu hỏi.
- Cache nằm ở `cache/<business_id>/`. Dữ liệu/cache/report chi tiết được Git ignore.
- Máy phát triển đã nhận diện RTX 3050 Laptop 6 GB VRAM; môi trường chạy inference cuối cùng chưa được thiết lập.

## Mã hiện có

| Thành phần | Trạng thái và vai trò |
|---|---|
| `loader/` | Mở file, làm sạch, parse README, suy kiểu và ánh xạ cột, dựng schema chuẩn và kiểm tra |
| `surveys/` | Công cụ khảo sát và tài liệu thiết kế; một số nội dung là đề xuất, không phải tính năng đã hoàn tất |
| `load_all.py` | Chạy train/public từ đường dẫn cố định và ghi cache, chưa phải runner inference nhận `/data` bất kỳ |
| `evaluate/` | Bộ chấm local, có test; chưa được chứng nhận là evaluator BTC |
| `check_with_gold.py` | Chọn một số câu train dạng bảo thủ và kiểm tra phép tính từ cache |
| `generalize_check.py` | Công cụ leave-one-group-out/độ phủ; chưa có lượt chạy mới để báo cáo trong handoff này |
| `business/` | Thư viện nghiệp vụ bán hàng bản đầu, gọi bằng tham số có cấu trúc |
| `verify_business.py` | So thư viện với gold và phép tính cũ trên cùng tập câu chọn lọc |

## Schema chuẩn có thể dùng

- `cua_hang`: khoảng ngày có dữ liệu, cờ có mã đơn/mã khách, `nang_luc`, thống kê nạp và thông tin rulebook.
- `don_hang`: mã đơn, ngày/giờ đặt, trạng thái, khách và khóa khách, nhóm khách, kênh, thanh toán, nhân viên, tiền hàng, giảm giá cấp đơn, tổng phải trả, nợ cuối dữ liệu…
- `dong_hang`: mã đơn, mã hàng, loại dòng, số lượng/đơn vị, số lượng cơ bản, đơn giá, giảm giá dòng, thành tiền, giá vốn dòng…
- `mat_hang`: mã/tên hàng, nhóm, đơn vị cơ bản, giá bán/giá vốn và một số thuộc tính ngành.
- `khach_hang`, `quy_doi_don_vi` và các bảng thô đã làm sạch cùng catalog/mapping.

Có tên cột không đồng nghĩa cột có dữ liệu đầy đủ hoặc ánh xạ đúng. Các bảng thanh toán, nhập hàng, kho, lô, giao hàng… chưa được chuẩn hóa đầy đủ thành API nghiệp vụ bản đầu.

## API nghiệp vụ hiện tại

Exports: `Rulebook`, `UnsupportedRule`, `Periods`, `DateRange`, `SalesMetrics`, `Filters`, `Answer`, `DataError`.

- Thời gian: today/yesterday, N ngày, tuần, tháng, quý, đầu năm, Tết tra calendar, kỳ liền trước cùng số ngày.
- Metrics: revenue, order_count, cancelled_orders, cancellation_rate, average_order_value, quantity, top_products, top_customers, revenue_growth, revenue_share.
- Filters: product_ids, product_group, channel, payment, customer_group, shift.
- Kết quả: `Answer`; chuyển thành object nộp bài bằng `to_submission(id)`.
- Thiếu loại dữ liệu/ngoài kỳ/mẫu số 0: unanswerable. Dữ liệu chuẩn lỗi hoặc thiếu một phần: `DataError`. Luật ngoài mẫu được hỗ trợ: `UnsupportedRule`. Hai lỗi sau không được tự coi là chứng minh câu hỏi unanswerable.
- Đọc file rulebook do người gọi truyền và kiểm tra các cụm điều khoản cần thiết. Đây là parser có phạm vi giới hạn, không suy luận mọi nội dung rulebook tiếng Việt bất kỳ.

Phí phục vụ được tính doanh thu nhưng bỏ khỏi xếp hạng sản phẩm; topping có thể là mặt hàng. Đơn hủy/trả loại cả đơn, đang giao vẫn tính. Số đơn cần mã thật. Tỷ lệ hủy có mẫu số mọi trạng thái. Xếp hòa theo mã. Tiền làm tròn half-up; tỷ lệ hai chữ số theo luật hỗ trợ.

API chi tiết và giới hạn nằm trong `docs/business.md`, cũng được chép trong handoff.

## Bằng chứng kiểm chứng gần nhất

- Full pytest chạy lại trước commit/push ngày 2026-10-28: **219 passed, 1 skipped**. Test cũ `evaluate/test_evaluate.py::test_self_score_real_file` tìm gold dưới `evaluate/` thay vì gốc repo nên vẫn bị bỏ qua; không phải thiếu đáp án train hiện tại.
- Bộ kiểm tra chọn **417/3000** câu, bỏ qua **8** theo bộ chọn cũ, đối chiếu được **409**.
- Thư viện mới khớp gold **409/409**, khớp phép tính cũ **409/409**, 0 lỗi.
- Thành phần: 187 doanh thu tháng, 76 số đơn hủy, 130 số lượng, 8 doanh thu ca sáng và 8 ca chiều.
- Đây là hồi quy trên tập con, **không phải** PA toàn bộ 3000 câu và không chứng minh các metric khác đều đúng trên dữ liệu thật.
- Có test tổng hợp cho các hàm khác và smoke API trên một doanh nghiệp train/một public. Có review độc lập; các lỗi phát hiện đã được tái hiện bằng test và sửa.
- Đã chạy lại `verify_business.py` trước khi chuẩn bị push: exit 0, vẫn khớp 409/409; `compileall` và `git diff --check` qua. Cần chạy lại sau thay đổi code có liên quan.

## Chưa có

Tầng hiểu câu hỏi/resolve thực thể, model weights/runtime inference, QueryPlan schema, dispatcher/validator, confidence/abstain toàn hệ thống, runner sinh full submission, log từng câu và Docker. Chưa có API kho, nợ, lợi nhuận và đầy đủ luật ngành.

## Hướng đang thảo luận

Review xem thư viện nghiệp vụ có đủ làm nền cho một lát cắt NLU đầu tiên không; chọn cách nối câu hỏi → kế hoạch có cấu trúc → phép tính → đáp án, và cách đánh giá trên train tách biệt. Chưa coi phương án nào là quyết định đã chốt.

## Round 001 request from Codex

Source: `ai_collaboration/rounds/001_business_to_nlu/CODEX_REQUEST.md`

# Vòng 001 Review nền nghiệp vụ và hướng nối tầng hiểu câu hỏi

- Người gửi: Codex, theo yêu cầu phối hợp của người dùng.
- Người nhận: Gemini web, model do người dùng chọn.
- Ngày mở: 2026-10-28.
- Trạng thái: Đã chuẩn bị yêu cầu, chưa nhận phản hồi Gemini.
- Source snapshot: code commit `1c89252`, nhánh `VuongNguyen`; xem danh sách SHA256 trong `GEMINI_HANDOFF.md`.

## Vấn đề cần giải quyết

Chúng tôi đã làm loader và thư viện bán hàng bản đầu. Bước tiếp theo đang cân nhắc là tầng hiểu câu hỏi. Cần phản biện xem những hợp đồng hiện tại đã đủ để nối một lát cắt agent đầu tiên chưa, và chọn cách biểu diễn kế hoạch truy vấn dễ kiểm tra, tổng quát với doanh nghiệp/mẫu file mới.

Đề xuất ban đầu của Codex là dùng một kế hoạch JSON có schema, gọi whitelist API nghiệp vụ, kiểm tra tham số và khả năng dữ liệu trước khi thực thi; có thể bổ sung đường xử lý riêng sau khi đo được độ phủ. Đây là đề xuất để phản biện, chưa phải quyết định.

## Nhờ Gemini phân tích

1. **Review hợp đồng hiện tại:** lỗi/giới hạn nào của `Rulebook`, `Periods`, `SalesMetrics`, `Answer` và `Filters` sẽ làm tầng hiểu câu hỏi tính sai hoặc nhận định sai khả năng trả lời? Chỉ rõ thao tác, input tổng hợp và kết quả đúng. Nếu code đã có kiểm tra cho trường hợp đó, hãy phân biệt phần còn thiếu với phần đã xử lý.
2. **So sánh kiến trúc:** JSON gọi API, LLM sinh SQL/Python, và cách kết hợp. Đánh giá theo phạm vi API hiện có, khả năng tổng quát, tính tái lập, độ khó kiểm tra, thời gian chạy và giới hạn offline. Không cần chọn model cụ thể trong vòng này.
3. **Đề xuất hợp đồng kế hoạch:** nêu trường tối thiểu để biểu diễn metric, kỳ hỏi/kỳ so, thực thể, bộ lọc, thứ tự, top-k, kiểu đáp án và bằng chứng. Phân biệt điều LLM suy luận với điều runtime phải tự kiểm chứng. Chỉ ra trường hợp API hiện tại chưa biểu diễn được, ví dụ boolean/date/table hoặc nhiều metric.
4. **Không trả lời được hay chưa hỗ trợ:** cách phân biệt dữ liệu không có thông tin, mapping chưa chắc, luật chưa hỗ trợ, không hiểu câu hỏi và lỗi runtime. Không biến thiếu tính năng thành unanswerable.
5. **Đánh giá:** đề xuất cách tách train theo doanh nghiệp/nhóm mẫu file, tránh dùng cùng tập chọn lọc để vừa phát triển vừa tuyên bố tổng quát. Nêu nên đo PA, coverage, lỗi type/format, thời gian và các ablation nào trước.

## Ví dụ tổng hợp để thảo luận

Đây là ví dụ tự tạo, không phải câu hỏi BTC:

- “Doanh thu tháng này so với cùng số ngày tháng trước tăng bao nhiêu phần trăm?” — cần kỳ so, mốc as_of_date, mẫu số 0 và dấu âm/dương.
- “Cho tôi 3 món bán chạy nhất tuần rồi.” — cần resolve thời gian, phân biệt số lượng với doanh thu, tie-break theo mã, xuất list.
- “Khách nào còn nợ tính đến hôm nay?” — API công nợ chưa có; dữ liệu nguồn có thể vẫn có thông tin, nên không được tự kết luận unanswerable.
- “Tháng này có bán tốt hơn tháng trước không?” — cần làm rõ metric và kỳ so theo rulebook; boolean chưa có dispatcher trong repo.

## Mong muốn nhận lại

Một bản review có ưu tiên và ví dụ kiểm chứng, một hướng kiến trúc được khuyến nghị, phác thảo contract đủ nhỏ để thử, và tối đa 5 câu hỏi gửi lại Codex. Không cần viết cả codebase.

Với mỗi lỗi/đề xuất quan trọng, nêu: căn cứ trong snapshot → ảnh hưởng → test/thử nghiệm phân định → cách sửa hoặc đánh đổi. Những phần không thể kết luận từ snapshot hãy ghi là chưa kiểm chứng.

## API guide

Source: `docs/business.md`

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
| `top_products(period, k=5, metric='quantity', filters=...)` | list tên hàng, metric quantity hoặc revenue |
| `top_customers(period, k=5, metric='revenue')` | list tên khách, metric revenue hoặc orders |
| `revenue_growth(period, comparison, filters)` | percent, (kỳ hỏi − kỳ so)/kỳ so |
| `revenue_share(period, filters)` | percent, doanh thu bộ lọc/doanh thu cả shop |

`Filters` hỗ trợ `product_ids` (tuple mã hàng), `product_group`, `channel`, `payment`, `customer_group`, `shift` (`sang`/`chieu`). Truyền mã/nhãn đúng trong schema chuẩn; việc khớp tên, alias và cách nói thuộc tầng hiểu câu hỏi. Bộ lọc sản phẩm áp lên dòng hàng; bộ lọc kênh/thanh toán/khách/ca áp lên đơn. Với AOV có bộ lọc sản phẩm, tử số là doanh thu các dòng được lọc và mẫu số là số đơn có các dòng đó.

Doanh thu gồm phí phục vụ/topping, không trừ voucher cấp đơn, không cộng ship/VAT. Xếp hạng và số lượng mặt hàng bỏ phí phục vụ, có topping. Hủy/trả loại cả đơn, đang giao vẫn tính. Khi không có bảng dòng hàng, chỉ doanh thu toàn đơn có thể dùng `tong_tien_hang`, không suy từ tiền đã thu hoặc tổng phải trả.

## Kết quả thiếu dữ liệu và giới hạn

- `Answer(type, answer, reason)` và `to_submission(question_id)` tạo JSON object; chưa phải runner xuất toàn bộ submission.
- Không có loại thông tin cần thiết, ngoài khoảng dữ liệu, hoặc mẫu số bằng 0: `Answer('unanswerable', reason=...)`.
- Dữ liệu chuẩn có khóa trùng, ngày/status sai, giá trị liên quan thiếu một phần: `DataError`. Tầng agent cần sửa mapping hoặc abstain; không tự đổi lỗi này thành đáp án 0.
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

## Latest verification evidence

Source: `docs/validation.md`

# Trạng thái kiểm chứng ngày 2026-10-28

Đã chạy lại trên workspace Windows/Python 3.14.10 trước khi đưa bản thư viện nghiệp vụ và gói trao đổi Gemini lên nhánh `VuongNguyen`.

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q -rs` | 219 passed, 1 skipped |
| `python -m compileall -q business verify_business.py` | Exit 0 |
| `git diff --check` | Exit 0 |
| `python verify_business.py` | Exit 0, khớp gold 409/409 và phép tính cũ 409/409, 0 lỗi |

Verifier chọn 417 trong 3000 câu train; 8 câu bị bộ kiểm tra cũ bỏ qua, còn 409 câu đối chiếu được: 187 doanh thu tháng, 76 số đơn hủy, 130 số lượng, 8 ca sáng và 8 ca chiều. Đây là kiểm chứng hồi quy trên tập con, không phải PA toàn bộ train. Các API khác được kiểm thử bằng dữ liệu tổng hợp; không suy rộng kết quả 409/409 cho toàn bộ agent.

Test bỏ qua là `evaluate/test_evaluate.py::test_self_score_real_file`: helper hiện tìm gold dưới `evaluate/`, không tìm `train/answers.jsonl` ở gốc repo. Dữ liệu train thực tế đã có tại local. Chưa sửa evaluator trong phạm vi triển khai này.

Lượt loader đã chạy trước đó trên 44 doanh nghiệp: 0 crash, 236 PASS, 116 kiểm tra bỏ qua, 0 FAIL. Không chạy lại loader trong lượt chuẩn bị GitHub này vì không sửa loader hoặc dữ liệu.

Chi tiết đối chiếu từng câu và báo cáo loader ở `reports/business_verification.*`, `reports/gold_before_business.md`, `load_report.md` tại local, được Git ignore. File này chỉ ghi số liệu tổng hợp để người đọc GitHub thấy bằng chứng và giới hạn kiểm chứng.

## Source snapshot business/__init__.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/business/__init__.py

```python
"""Deterministic business operations on the loader's canonical schema."""
from .periods import DateRange, Periods
from .rules import Rulebook, UnsupportedRule
from .sales import Answer, DataError, Filters, SalesMetrics

__all__ = ['DateRange', 'Periods', 'Rulebook', 'UnsupportedRule', 'Answer', 'DataError', 'Filters', 'SalesMetrics']
```

## Source snapshot business/rules.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/business/rules.py

```python
"""Read the supplied split's rules; reject unsupported semantics explicitly."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import unicodedata


class UnsupportedRule(ValueError):
    """A requested operation cannot implement this rulebook safely."""


def folded(text: str) -> str:
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', text.replace('**', '').replace('`', '')).strip()


@dataclass(frozen=True)
class Rulebook:
    text: str
    source: str
    fingerprint: str
    rows: dict[str, str | None]

    @classmethod
    def from_text(cls, text: str, source: str = '<text>'):
        rows, scoped = {}, {}
        section = ''
        for line in text.splitlines():
            if line.strip().startswith('#'):
                section = folded(line.strip())
            if line.strip().startswith('|'):
                parts = [x.strip() for x in line.strip().strip('|').split('|')]
                if len(parts) == 2 and parts[0] and not parts[0].startswith('-'):
                    key = folded(parts[0])
                    if (section,key) in scoped and scoped[section,key] != parts[1]:
                        raise UnsupportedRule(f'Conflicting rule: {parts[0]}')
                    scoped[section,key] = parts[1]
                    # An ambiguous cross-industry label is unusable without an
                    # industry-specific implementation, but must not block core sales.
                    rows[key] = parts[1] if key not in rows or rows[key] == parts[1] else None
        if not rows:
            raise UnsupportedRule('No supported rule table found')
        return cls(text, str(source), sha256(text.encode('utf-8')).hexdigest(), rows)

    @classmethod
    def from_path(cls, path: str | Path):
        path = Path(path)
        return cls.from_text(path.read_text(encoding='utf-8-sig'), str(path.resolve()))

    def require(self, label: str, *fragments: str) -> str:
        value = self.rows.get(folded(label), '')
        if not value or not all(folded(part) in folded(value) for part in fragments):
            raise UnsupportedRule(f'Unsupported/missing rule {label!r} in {self.source}')
        return value.replace('**', '').replace('`', '')

    def require_text(self, *fragments: str):
        if not all(folded(part) in folded(self.text) for part in fragments):
            raise UnsupportedRule(f'Unsupported/missing rulebook convention in {self.source}')

    def implicit_year(self):
        self.require('Tháng M, quý Q không ghi năm', 'nam nay neu khong sau hom nay')
        value = folded(self.rows[folded('Tháng M, quý Q không ghi năm')])
        if not re.search(r'(sau hom nay thi cua|con lai) nam truoc', value):
            raise UnsupportedRule('Unsupported implicit-year fallback')

    def rounding_places(self, kind: str) -> int:
        text = folded(self.text)
        if kind == 'money' and re.search(r'\btien(?: ra so le)? lam tron ve dong', text):
            return 0
        if kind == 'percent':
            values = re.findall(r'phan tram(?: va so trung binh khac)? lam tron (\d+) chu so', text)
            if values and set(values) == {'2'}:
                return 2
        raise UnsupportedRule(f'Unsupported {kind} rounding convention')

    def shift_minutes(self, shift: str) -> tuple[int, int]:
        if shift not in ('sang', 'chieu'):
            raise ValueError('shift must be sang or chieu')
        value = folded(self.require('Ca sáng, ca chiều', 'theo gio tao don'))
        match = re.search(rf'ca {shift}\s+(\d{{2}}):(\d{{2}})\s*[–—-]\s*(\d{{2}}):(\d{{2}})', value)
        if not match:
            raise UnsupportedRule('Unsupported shift boundaries')
        h0, m0, h1, m1 = map(int, match.groups())
        start, end = h0 * 60 + m0, h1 * 60 + m1 + 1
        if not (0 <= h0 <= 23 and 0 <= h1 <= 23 and 0 <= m0 <= 59 and 0 <= m1 <= 59 and start < end):
            raise UnsupportedRule('Invalid shift boundaries')
        return start, end
```

## Source snapshot business/periods.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/business/periods.py

```python
"""Explicit date-period API. Natural-language question parsing belongs upstream."""
from calendar import monthrange
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .rules import Rulebook


def as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else date.fromisoformat(value)


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self):
        object.__setattr__(self, 'start', as_date(self.start))
        object.__setattr__(self, 'end', as_date(self.end))
        if self.start > self.end:
            raise ValueError('start must not be after end')


class Periods:
    def __init__(self, rules: Rulebook, as_of_date, calendar_path: str | Path | None = None):
        self.rules, self.as_of = rules, as_date(as_of_date)
        self.calendar_path = Path(calendar_path) if calendar_path is not None else None

    def today(self):
        return DateRange(self.as_of, self.as_of)

    def yesterday(self):
        day = self.as_of - timedelta(days=1)
        return DateRange(day, day)

    def last_days(self, n: int):
        if type(n) is not int or n <= 0:
            raise ValueError('n must be a positive integer')
        self.rules.require('N ngày gần nhất', 'ke ca hom nay', 'ngay cuoi la hom nay')
        return DateRange(self.as_of - timedelta(days=n-1), self.as_of)

    def this_week(self):
        self.rules.require('Tuần', 'bat dau thu Hai', 'den het hom nay')
        return DateRange(self.as_of - timedelta(days=self.as_of.weekday()), self.as_of)

    def previous_week(self):
        self.rules.require('Tuần', 'bat dau thu Hai', 'thu Hai den Chu nhat')
        end = self.this_week().start - timedelta(days=1)
        return DateRange(end - timedelta(days=6), end)

    def this_month(self):
        self.rules.require('Tháng này', 'tu ngay 1 den het hom nay')
        return DateRange(self.as_of.replace(day=1), self.as_of)

    def previous_month(self, same_elapsed: bool = False):
        end = self.as_of.replace(day=1) - timedelta(days=1)
        if same_elapsed:
            self.rules.require('Tháng này', 'cung so ngay', 'thang truoc')
            end = end.replace(day=min(end.day, self.as_of.day))
        return DateRange(self.month(end.month, end.year).start, end)

    def month(self, month: int, year: int | None = None):
        if type(month) is not int or not 1 <= month <= 12:
            raise ValueError('month must be 1..12')
        if year is None:
            self.rules.implicit_year()
            year = self.as_of.year - (month > self.as_of.month)
        self.rules.require('Tháng M/Y', 'ca thang')
        return DateRange(date(year, month, 1), date(year, month, monthrange(year, month)[1]))

    def quarter(self, quarter: int, year: int | None = None):
        if type(quarter) is not int or not 1 <= quarter <= 4:
            raise ValueError('quarter must be 1..4')
        self.rules.require('Tháng M, quý Q không ghi năm', 'quy theo duong lich', '3 thang')
        month = 3 * (quarter - 1) + 1
        if year is None:
            self.rules.implicit_year()
            year = self.as_of.year - (month > self.as_of.month)
        return DateRange(date(year, month, 1), self.month(month + 2, year).end)

    def year_to_date(self):
        self.rules.require('Từ đầu năm, từ đầu năm tới nay', '01/01', 'den het hom nay')
        return DateRange(date(self.as_of.year, 1, 1), self.as_of)

    def tet(self, year: int):
        self.rules.require('Tết năm Y, dịp Tết, mùa Tết', '23 thang Chap', 'mung 10 thang Gieng', 'calendar.csv')
        if self.calendar_path is None:
            raise ValueError('calendar_path is required for Tet')
        matches = {(year-1, 12, 23): [], (year, 1, 10): []}
        with self.calendar_path.open(encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                if row['lunar_leap'].lower() not in ('false', '0'):
                    continue
                key = tuple(int(row[c]) for c in ('lunar_year','lunar_month','lunar_day'))
                if key in matches:
                    matches[key].append(row['date'])
        if any(len(v) != 1 for v in matches.values()):
            raise ValueError(f'calendar has missing/ambiguous Tet endpoints for {year}')
        return DateRange(matches[(year-1,12,23)][0], matches[(year,1,10)][0])

    def before(self, period: DateRange):
        self.rules.require('Tết năm Y, dịp Tết, mùa Tết', 'cung so ngay ngay truoc')
        return DateRange(period.start - (period.end - period.start) - timedelta(days=1),
                         period.start - timedelta(days=1))
```

## Source snapshot business/sales.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/business/sales.py

```python
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
from .rules import Rulebook


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
        if metric not in ('quantity','revenue'):
            raise ValueError('metric must be quantity or revenue')
        self.rules.require('Mặt hàng','phi phuc vu','khong xep hang')
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
```

## Source snapshot tests/conftest.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/tests/conftest.py

```python
"""Synthetic rulebook: core tests do not require competition data downloads."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from business import Rulebook


RULES = '''
Hôm nay là as_of_date. Bản ghi ngày sau hôm nay coi như chưa xảy ra.
| Luật | Mặc định |
|---|---|
| Đơn tính vào doanh thu | đơn không huỷ và không trả hàng. Đang giao vẫn tính |
| Đơn thuộc kỳ nào | theo ngày đặt, không theo ngày giao hay ngày thu tiền |
| Số đơn | chỉ tính đơn không huỷ, không trả |
| Đơn bị huỷ | đơn có trạng thái huỷ. Đơn trả hàng không phải đơn huỷ |
| Doanh thu một đơn | tổng thành tiền các dòng hàng. Không trừ giảm giá trên cả đơn; không cộng thuế VAT, không gồm phí giao hàng |
| Tỉ lệ đơn huỷ trong kỳ | phần trăm đơn huỷ trong mọi đơn đặt trong kỳ, mọi trạng thái. Làm tròn 2 chữ số thập phân |
| Mặt hàng | Phí phục vụ không phải mặt hàng: không xếp hạng. Vẫn tính vào doanh thu |
| Bán chạy | theo số lượng quy về đơn vị cơ bản, bỏ đơn huỷ, trả |
| Bán được bao nhiêu <đơn vị> | cộng số lượng quy về đơn vị cơ bản của các mặt hàng có đơn vị cơ bản là <đơn vị> |
| Nhóm hàng | theo cột nhóm hàng, đúng tên nhóm câu hỏi nêu; không gộp nhóm khác tên |
| Xác định khách | Shop có mã khách: mỗi mã khách là một khách; khách lẻ không đếm và không xếp hạng. Shop không có mã khách: xác định khách theo tên ghi trên đơn |
| Doanh thu theo nhóm khách | theo cột nhóm khách. Đơn không ghi khách không thuộc nhóm nào. Tỉ trọng chia cho doanh thu cả shop |
| Doanh thu theo hình thức thanh toán | theo hình thức ghi trên đơn, không theo lần trả nợ |
| Giá trị trung bình một đơn | làm tròn về đồng, nửa đồng làm tròn lên |
| Phần trăm thay đổi, tăng trưởng | so với kỳ trước; giảm thì ra số âm |
| N ngày gần nhất | N ngày kể cả hôm nay, ngày cuối là hôm nay |
| Tuần | bắt đầu **thứ Hai**. Tuần này đến hết hôm nay. Tuần trước thứ Hai đến Chủ nhật |
| Tháng M/Y | cả tháng |
| Tháng này | từ ngày 1 đến hết hôm nay. So tháng trước cùng số ngày |
| Tháng M, quý Q không ghi năm | năm nay nếu không sau hôm nay, còn lại năm trước. Quý theo dương lịch, 3 tháng |
| Từ đầu năm, từ đầu năm tới nay | từ 01/01 đến hết hôm nay |
| Tết năm Y, dịp Tết, mùa Tết | từ 23 tháng Chạp đến mùng 10 tháng Giêng, tra calendar.csv. So trước Tết = cùng số ngày ngay trước |
| Ca sáng, ca chiều | theo giờ tạo đơn: ca sáng 06:00–13:59, ca chiều 14:00–21:59 |
Bằng nhau: xếp theo mã tăng dần (không có mã thì theo tên).
Làm tròn: tiền làm tròn về đồng; phần trăm làm tròn 2 chữ số thập phân.
'''


@pytest.fixture
def rules():
    return Rulebook.from_text(RULES)
```

## Source snapshot tests/test_business_periods.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/tests/test_business_periods.py

```python
from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from business import DateRange, Periods, Rulebook, UnsupportedRule


def test_month_to_date_comparison_clamps_february(rules):
    p = Periods(rules, '2024-03-31')
    assert p.this_month() == DateRange('2024-03-01', '2024-03-31')
    assert p.previous_month(same_elapsed=True) == DateRange('2024-02-01', '2024-02-29')
    assert p.previous_month() == DateRange('2024-02-01', '2024-02-29')
    assert Periods(rules, '2024-03-05').previous_month(same_elapsed=True).end == date(2024, 2, 5)


def test_week_and_relative_days_cross_year(rules):
    p = Periods(rules, '2026-01-01')
    assert p.this_week() == DateRange('2025-12-29', '2026-01-01')
    assert p.previous_week() == DateRange('2025-12-22', '2025-12-28')
    assert p.last_days(3) == DateRange('2025-12-30', '2026-01-01')
    assert p.yesterday() == DateRange('2025-12-31', '2025-12-31')
    assert p.today() == DateRange('2026-01-01', '2026-01-01')
    assert p.year_to_date() == DateRange('2026-01-01', '2026-01-01')


def test_implicit_year_and_explicit_full_period(rules):
    p = Periods(rules, '2026-03-04')
    assert p.month(8) == DateRange('2025-08-01', '2025-08-31')
    assert p.month(3) == DateRange('2026-03-01', '2026-03-31')
    assert p.month(8, 2026) == DateRange('2026-08-01', '2026-08-31')
    assert p.quarter(4) == DateRange('2025-10-01', '2025-12-31')
    assert p.quarter(1) == DateRange('2026-01-01', '2026-03-31')


def test_tet_uses_supplied_calendar_and_equal_prior_window(rules, tmp_path):
    calendar = tmp_path / 'calendar.csv'
    calendar.write_text('date,lunar_day,lunar_month,lunar_year,lunar_leap\n'
                        '2026-02-10,23,12,2025,false\n'
                        '2026-02-26,10,1,2026,false\n'
                        '2026-03-26,10,1,2026,true\n', encoding='utf-8')
    p = Periods(rules, '2026-03-01', calendar)
    assert p.tet(2026) == DateRange('2026-02-10', '2026-02-26')
    assert p.before(p.tet(2026)) == DateRange('2026-01-24', '2026-02-09')
    with pytest.raises(ValueError, match='calendar'):
        p.tet(2027)


def test_changed_week_rule_is_not_silently_accepted(rules):
    changed = Rulebook.from_text(rules.text.replace('bắt đầu **thứ Hai**', 'bắt đầu **Chủ nhật**'))
    with pytest.raises(UnsupportedRule):
        Periods(changed, '2026-03-04').this_week()


@pytest.mark.parametrize('start,end', [('2026-03-05','2026-03-04'), ('bad','2026-03-04')])
def test_invalid_ranges_rejected(start, end):
    with pytest.raises(ValueError):
        DateRange(start, end)


def test_invalid_counts_and_missing_calendar(rules):
    p = Periods(rules, '2026-03-04')
    for n in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            p.last_days(n)
    with pytest.raises(ValueError):
        p.month(13)
    with pytest.raises(ValueError):
        p.quarter(0)
    with pytest.raises(ValueError, match='calendar'):
        p.tet(2026)


def test_duplicate_rule_labels_in_different_industries_are_scoped(rules):
    text = rules.text + '\n### Điện thoại\n| Bảo hành | theo số máy |\n### Sửa xe\n| Bảo hành | theo số phiếu |\n'
    parsed = Rulebook.from_text(text)
    assert Periods(parsed, '2026-03-04').this_week() == DateRange('2026-03-02','2026-03-04')
    with pytest.raises(UnsupportedRule):
        parsed.require('Bảo hành')


@pytest.mark.parametrize('method,value', [('month',8),('quarter',4)])
def test_reversed_implicit_year_rule_rejected(rules,method,value):
    changed=Rulebook.from_text(rules.text.replace('năm nay nếu không sau hôm nay, còn lại năm trước',
                                               'năm trước nếu không sau hôm nay, còn lại năm nay'))
    with pytest.raises(UnsupportedRule):
        getattr(Periods(changed,'2026-03-04'),method)(value)
```

## Source snapshot tests/test_business_sales.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/tests/test_business_sales.py

```python
from copy import deepcopy

import pandas as pd
import pytest

from business import DateRange, Rulebook, UnsupportedRule
from business.sales import Answer, DataError, Filters, SalesMetrics


@pytest.fixture
def tables():
    # Synthetic orders: two valid, one returned, one cancelled, one future.
    orders = pd.DataFrame([
        ['O1','2026-03-01','2026-03-01 13:59:59','hoan_thanh','K2','Lan',False,'K2','VIP','tai_quan','tien_mat',101],
        ['O2','2026-03-02','2026-03-02 14:00:00','dang_giao','K1','Lan',False,'K1','VIP','online','cod',100],
        ['O3','2026-03-02','2026-03-02 15:00:00','tra_hang','K1','Lan',False,'K1','VIP','online','cod',900],
        ['O4','2026-03-03','2026-03-03 10:00:00','huy',None,None,True,None,None,'online','tien_mat',900],
        ['O5','2026-03-20','2026-03-20 10:00:00','hoan_thanh','K1','Lan',False,'K1','VIP','online','cod',800],
    ], columns=['ma_don','ngay_dat','thoi_diem_dat','trang_thai','ma_khach','ten_khach','la_khach_le','khach_key',
                'nhom_khach','kenh_ban','hinh_thuc_tt','tong_tien_hang'])
    lines = pd.DataFrame([
        ['O1','P2','hang',1,80], ['O1','S','phi_phuc_vu',1,21],
        ['O2','P1','hang',1,90], ['O2','T','topping',1,10],
        ['O3','P1','hang',9,900], ['O4','P1','hang',9,900], ['O5','P1','hang',8,800],
    ], columns=['ma_don','ma_hang','loai_dong','so_luong_co_ban','thanh_tien'])
    products = pd.DataFrame([
        ['P1','Cà phê','Đồ uống','ly'], ['P2','Trà','Đồ uống','ly'],
        ['T','Trân châu','Topping','phần'], ['S','Phí phục vụ',None,None],
    ], columns=['ma_hang','ten_hang','nhom_hang','don_vi_co_ban'])
    return {'don_hang':orders,'dong_hang':lines,'mat_hang':products,
            'cua_hang':{'ngay_bat_dau_du_lieu':'2026-01-01','ngay_ket_thuc_du_lieu':'2026-03-31',
                        'co_ma_don':True,'co_ma_khach':True}}


@pytest.fixture
def period():
    return DateRange('2026-03-01','2026-03-31')


def test_revenue_excludes_entire_return_order_and_future(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.revenue(period).answer == 201
    assert engine.order_count(period).answer == 2
    assert engine.cancelled_orders(period).answer == 1
    assert engine.cancellation_rate(period).answer == 25
    assert engine.average_order_value(period).answer == 101  # 100.5 half-up


def test_filters_and_shifts_follow_order_time(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.revenue(period, Filters(shift='sang')).answer == 101
    assert engine.revenue(period, Filters(shift='chieu')).answer == 100
    assert engine.revenue(period, Filters(payment='cod')).answer == 100
    assert engine.revenue(period, Filters(channel='online')).answer == 100
    assert engine.revenue(period, Filters(product_group='Đồ uống')).answer == 170
    assert engine.revenue(period, Filters(product_ids=('P1',))).answer == 90
    assert engine.revenue_share(period, Filters(product_group='Đồ uống')).answer == 84.58


def test_quantity_uses_base_unit_and_top_products_excludes_service(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.quantity(period, unit='ly').answer == 2
    assert engine.quantity(period, unit='phần').answer == 1
    assert engine.top_products(period, k=9).answer == ['Cà phê','Trà','Trân châu']
    assert engine.top_products(period, k=2, metric='revenue').answer == ['Cà phê','Trà']


def test_customer_ids_keep_same_names_distinct_and_walkins_excluded(tables, rules, period):
    engine = SalesMetrics(tables, rules, '2026-03-04')
    ranked = engine.top_customers(period, k=5)
    assert ranked.answer == ['Lan','Lan']
    tables['don_hang'].loc[0, ['ma_khach','khach_key']] = None
    tables['don_hang'].loc[0, 'la_khach_le'] = True
    assert SalesMetrics(tables,rules,'2026-03-04').top_customers(period).answer == ['Lan']


def test_outside_data_is_unanswerable_but_empty_supported_period_is_zero(tables, rules):
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.revenue(DateRange('2025-01-01','2025-01-31')).type == 'unanswerable'
    assert engine.revenue(DateRange('2026-02-01','2026-02-28')).answer == 0
    assert engine.revenue(DateRange('2026-03-10','2026-03-15')).type == 'unanswerable'
    assert engine.average_order_value(DateRange('2026-02-01','2026-02-28')).type == 'unanswerable'


def test_order_level_revenue_fallback_without_lines(tables, rules, period):
    tables['dong_hang'] = tables['dong_hang'].iloc[:0]
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.revenue(period).answer == 201
    assert engine.quantity(period).type == 'unanswerable'
    assert engine.revenue(period, Filters(product_ids=('P1',))).type == 'unanswerable'


def test_missing_or_partial_values_do_not_silently_sum_to_zero(tables, rules, period):
    tables['dong_hang'].loc[0,'thanh_tien'] = None
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period)
    tables['don_hang']['hinh_thuc_tt'] = None
    assert SalesMetrics(tables,rules,'2026-03-04').revenue(period, Filters(payment='cod')).type == 'unanswerable'


def test_unknown_status_and_duplicate_order_keys_rejected(tables, rules, period):
    tables['don_hang'].loc[0,'trang_thai'] = None
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period)
    tables['don_hang'].loc[0,'trang_thai'] = 'hoan_thanh'
    tables['don_hang'].loc[1,'ma_don'] = 'O1'
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04')


def test_no_real_order_ids_and_unmapped_quantities_rejected(tables, rules, period):
    tables['cua_hang']['co_ma_don'] = False
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.order_count(period).type == 'unanswerable'
    assert engine.average_order_value(period).type == 'unanswerable'
    tables['dong_hang'].loc[0,'so_luong_co_ban'] = None
    with pytest.raises(DataError):
        engine.quantity(period)


def test_growth_zero_denominator_and_answer_serialization(tables, rules, period):
    engine = SalesMetrics(tables,rules,'2026-03-04')
    assert engine.revenue_growth(DateRange('2026-03-02','2026-03-02'), DateRange('2026-03-01','2026-03-01')).answer == -0.99
    assert engine.revenue_growth(period, DateRange('2026-02-01','2026-02-28')).type == 'unanswerable'
    assert engine.revenue(period).to_submission('q') == {'id':'q','type':'number','answer':201}
    assert 'answer' not in Answer('unanswerable',reason='missing').to_submission('q')


def test_changed_revenue_rule_rejected_and_changed_shift_parsed(tables, rules, period):
    changed = Rulebook.from_text(rules.text.replace('không gồm phí giao hàng','gồm phí giao hàng'))
    with pytest.raises(UnsupportedRule):
        SalesMetrics(tables,changed,'2026-03-04').revenue(period)
    shifted = Rulebook.from_text(rules.text.replace('06:00–13:59','06:00–12:59'))
    assert SalesMetrics(tables,shifted,'2026-03-04').revenue(period, Filters(shift='sang')).answer == 0


def test_inputs_not_mutated_and_partial_period_allowed(tables, rules):
    original = deepcopy(tables)
    result = SalesMetrics(tables,rules,'2026-03-04').revenue(DateRange('2025-12-01','2026-03-02'))
    assert result.answer == 201
    for name in ('don_hang','dong_hang','mat_hang'):
        pd.testing.assert_frame_equal(tables[name],original[name])


@pytest.mark.parametrize('missing', ['product_group','customer_group'])
def test_unknown_group_does_not_disappear_from_filtered_revenue(tables, rules, period, missing):
    if missing == 'product_group':
        tables['mat_hang'].loc[0,'nhom_hang'] = None
        filters = Filters(product_group='Đồ uống')
    else:
        tables['don_hang'].loc[1,'nhom_khach'] = None
        filters = Filters(customer_group='VIP')
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period,filters)


@pytest.mark.parametrize('method', ['revenue','top_customers'])
def test_partially_missing_line_coverage_is_detected(tables,rules,period,method):
    tables['dong_hang'] = tables['dong_hang'][tables['dong_hang']['ma_don']!='O2']
    with pytest.raises(DataError):
        getattr(SalesMetrics(tables,rules,'2026-03-04'),method)(period)


def test_unknown_line_kind_is_not_dropped(tables,rules,period):
    tables['dong_hang'].loc[0,'loai_dong']='unknown'
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(period)


def test_changed_share_denominator_rejected(tables,rules,period):
    changed = Rulebook.from_text(rules.text.replace('doanh thu cả shop','doanh thu các đơn có khách'))
    with pytest.raises(UnsupportedRule):
        SalesMetrics(tables,changed,'2026-03-04').revenue_share(period,Filters(customer_group='VIP'))


def test_changed_percentage_precision_rejected(tables,rules):
    changed=Rulebook.from_text(rules.text.replace('phần trăm làm tròn 2 chữ số','phần trăm làm tròn 1 chữ số'))
    with pytest.raises(UnsupportedRule):
        SalesMetrics(tables,changed,'2026-03-04').revenue_growth(DateRange('2026-03-02','2026-03-02'),DateRange('2026-03-01','2026-03-01'))


def test_selected_missing_amount_is_data_error_not_unanswerable(tables,rules):
    tables['dong_hang'].loc[2:3,'thanh_tien']=None
    with pytest.raises(DataError):
        SalesMetrics(tables,rules,'2026-03-04').revenue(DateRange('2026-03-02','2026-03-02'))


def test_base_unit_matching_ignores_case(tables,rules,period):
    tables['mat_hang'].loc[:1,'don_vi_co_ban']='Ly'
    assert SalesMetrics(tables,rules,'2026-03-04').quantity(period,unit='ly').answer==2
```

## Source snapshot tests/test_business_verification.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/tests/test_business_verification.py

```python
import json

import pandas as pd

from verify_business import verify


def test_verifier_checks_library_and_counts_excluded_questions(tmp_path, rules):
    train = tmp_path/'train'
    train.mkdir()
    (train/'rulebook.md').write_text(rules.text,encoding='utf-8')
    questions = [
        {'id':'q1','business_id':'synthetic','question':'doanh thu tháng 3/2026 bao nhiêu','as_of_date':'2026-03-04'},
        {'id':'q2','business_id':'synthetic','question':'câu không hỗ trợ','as_of_date':'2026-03-04'},
    ]
    gold = [{'id':'q1','type':'number','answer':123}, {'id':'q2','type':'string','answer':'x'}]
    for name,rows in [('questions',questions),('answers',gold)]:
        (train/f'{name}.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows),encoding='utf-8')
    cache=tmp_path/'cache'/'synthetic'
    cache.mkdir(parents=True)
    pd.DataFrame([{'ma_don':'O1','ngay_dat':'2026-03-01','trang_thai':'hoan_thanh',
                   'tong_tien_hang':123,'thoi_diem_dat':'2026-03-01 09:00:00'}]).to_parquet(cache/'don_hang.parquet')
    pd.DataFrame([{'ma_don':'O1','ma_hang':'P1','loai_dong':'hang','thanh_tien':123,'so_luong_co_ban':1}]).to_parquet(cache/'dong_hang.parquet')
    pd.DataFrame([{'ma_hang':'P1','ten_hang':'Món thử','don_vi_co_ban':'ly'}]).to_parquet(cache/'mat_hang.parquet')
    (cache/'cua_hang.json').write_text(json.dumps({'co_ma_don':True,'ngay_bat_dau_du_lieu':'2026-03-01','ngay_ket_thuc_du_lieu':'2026-03-31'}),encoding='utf-8')
    result=verify(train,tmp_path/'cache')
    assert result['total_train']==2
    assert result['selected']==result['compared']==result['matched_gold']==1
    assert result['outside_selection']==1
    assert result['errors']==[]
    assert result['rows'][0]['legacy']==result['rows'][0]['library']['answer']==123
```

## Source snapshot verify_business.py

GitHub: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/blob/1c892521fa5bcc6abb0761ff0dd80e0587ed6d8b/verify_business.py

```python
#!/usr/bin/env python3
"""Regression on the legacy checker's selected train questions, not full PA.

Gold data is read ONLY here, never by business/. Selection intentionally retains
the legacy checker's restrictions so the before/after denominators are visible.
"""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path

import pandas as pd

import check_with_gold as legacy
from business import DataError, DateRange, Filters, Periods, Rulebook, SalesMetrics, UnsupportedRule


def quantity_request(tables, rest):
    """Resolve the same conservative unit/product subset as the old checker."""
    match = legacy.QTY_RE.search(rest)
    unit = match[2]
    products = tables['mat_hang']
    units = [u for u in products['don_vi_co_ban'].dropna().unique() if legacy.norm_question(u).split()[:1]==[unit]]
    if not units:
        return None
    names = {}
    for code,name in zip(products['ma_hang'],products['ten_hang']):
        if isinstance(name,str) and name.strip():
            names.setdefault(legacy.norm_question(name),set()).add(code)
    text = f' {rest} '
    found = [name for name in names if name and f' {name} ' in text]
    item = max(found,key=len) if found else None
    left = text.replace(f' {item} ',' ') if item else text
    left = left.replace(match[0],' ')
    if not all(word in legacy.QTY_FILLER for word in left.split()):
        return None
    return units[0], Filters(product_ids=tuple(sorted(names[item])) if item else None)


def verify(train_dir=Path('train'), cache_dir=Path('cache')):
    train_dir,cache_dir = Path(train_dir),Path(cache_dir)
    rules = Rulebook.from_path(train_dir/'rulebook.md')
    questions = legacy.gold_questions(train_dir)
    total = len([line for line in (train_dir/'questions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()])
    rows,skipped,errors,tables_by_shop,engines = [],[],[],{},{}
    for q in questions:
        bid = q['business_id']
        try:
            if bid not in tables_by_shop:
                cache=cache_dir/bid
                # The five checked operations only need these narrow columns.
                # Avoid retaining full customer/order metadata for every shop.
                tables_by_shop[bid]=legacy.load_cached(cache)
            tables=tables_by_shop[bid]
            old=legacy.compute(tables,q['loai'],q['thang'],q['nam'],q.get('rest',''))
            if old==legacy.BO_QUA:
                skipped.append({'id':q['id'],'reason':'legacy bo_qua'})
                continue
            if bid not in engines:
                engines[bid]=SalesMetrics(tables,rules,q['as_of_date'])
            engine=engines[bid]
            # This verifier is sequential; reuse validated tables/date indexes,
            # while setting each question's reference date explicitly.
            engine.as_of=date.fromisoformat(q['as_of_date'])
            period=Periods(rules,q['as_of_date']).month(q['thang'],q['nam'])
            if q['loai']=='doanh_thu':
                answer=engine.revenue(period)
            elif q['loai']=='so_don_huy':
                answer=engine.cancelled_orders(period)
            elif q['loai'].startswith('doanh_thu_ca_'):
                answer=engine.revenue(period,Filters(shift=q['loai'].rsplit('_',1)[1]))
            elif q['loai']=='so_luong':
                request=quantity_request(tables,q['rest'])
                if request is None:
                    raise DataError('Verifier cannot resolve legacy quantity request')
                unit,filters=request
                answer=engine.quantity(period,filters,unit=unit)
            else:
                raise ValueError(f'Unsupported verification kind: {q["loai"]}')
            wanted=q['gold_type']
            matched=answer.type==wanted and (wanted=='unanswerable' or abs(answer.answer-q['gold'])<=1e-6)
            rows.append({'id':q['id'],'business_id':bid,'kind':q['loai'],'legacy':old,
                         'gold_type':wanted,'gold':q['gold'],'library':answer.to_submission(q['id']),
                         'matched_gold':matched,'matched_legacy':(old=='unanswerable' if answer.type=='unanswerable' else old==answer.answer)})
        except (DataError,UnsupportedRule,ValueError,KeyError,OSError) as exc:
            errors.append({'id':q['id'],'business_id':bid,'error':f'{type(exc).__name__}: {exc}'})
    return {'total_train':total,'selected':len(questions),'outside_selection':total-len(questions),
            'legacy_skipped':len(skipped),'compared':len(rows),'matched_gold':sum(r['matched_gold'] for r in rows),
            'matched_legacy':sum(r['matched_legacy'] for r in rows),'errors':errors,
            'by_kind':dict(Counter(r['kind'] for r in rows)),'skipped':skipped,'rows':rows,
            'rulebook_source':rules.source,'rulebook_sha256':rules.fingerprint}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train',type=Path,default=Path('train'))
    parser.add_argument('--cache',type=Path,default=Path('cache'))
    parser.add_argument('--out',type=Path,default=Path('reports/business_verification'))
    args=parser.parse_args(argv)
    result=verify(args.train,args.cache)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    mismatches=[r for r in result['rows'] if not r['matched_gold']]
    lines=['# Kiểm chứng thư viện nghiệp vụ trên tập câu chọn lọc','',
           'Đây là kiểm chứng hồi quy theo bộ chọn câu cũ, không phải PA toàn bộ train.', '',
           f"- Tổng câu train: {result['total_train']}; được chọn: {result['selected']}; ngoài bộ chọn: {result['outside_selection']}.",
           f"- Bộ cũ bỏ qua: {result['legacy_skipped']}; so được: {result['compared']}; lỗi: {len(result['errors'])}.",
           f"- Khớp gold: {result['matched_gold']}/{result['compared']}; khớp phép tính cũ: {result['matched_legacy']}/{result['compared']}.",
           f"- Rulebook SHA256: {result['rulebook_sha256']}",'', '## Chênh lệch và lỗi','',
           '```json',json.dumps({'mismatches':mismatches,'errors':result['errors']},ensure_ascii=False,indent=2),'```']
    args.out.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','skipped')},ensure_ascii=False,indent=2))
    return 1 if mismatches or result['errors'] else 0


if __name__=='__main__':
    raise SystemExit(main())
```
