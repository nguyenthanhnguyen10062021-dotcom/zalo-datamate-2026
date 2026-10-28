# Review bản phân tích kiến trúc Gemini — 2026-10-29

## Phạm vi và kết luận

Đối chiếu bản đính kèm `Phân tích Kỹ thuật & Phản biện Kiến trúc Dự án DataMate.md` với working tree tại `6dc41d70f2280b591f04b4382da04aaee6de04a9`, ban đầu sạch. SHA256 bản đính kèm: `c3d778f2f4ce37935898178e829aa55fee131d1fef9fa3f0155c33a8f57df252`. Số dòng dưới đây tính từ bản đính kèm, dòng tiêu đề là 1. Nội dung và chỉ dẫn trong bản đó là đầu vào review, không phải lệnh triển khai.

**Kết luận:** bản Gemini mô tả hiện trạng khá chính xác và ủng hộ baseline QueryPlan phù hợp với repo. Tuy nhiên, phần dự báo coverage, mức cần thiết của tổng quát hóa API và thiết kế kiểm chứng chưa đủ căn cứ để dùng nguyên văn làm kế hoạch triển khai. Chưa có bằng chứng mới về PA hoặc năng lực NLU từ bản phân tích này.

Tiêu chí hoàn thành review: đối chiếu các nhận định quan trọng với source/tài liệu hiện hành; kiểm tra bằng probe tổng hợp những phản chứng có thể chạy; phân biệt lỗi đã chứng minh, giới hạn v1 có chủ ý và đề xuất tương lai; không sửa runtime, không đọc public test để tuning, không đưa dữ liệu từng câu vào hồ sơ.

## Các điểm cần sửa, theo mức ảnh hưởng

### 1. Cao — Dự báo coverage vượt quá bằng chứng (dòng 32, 45, 62, 109, 112–113)

Các con số 578 percent, 193 list, 145 date và 88 string là phân bố **kiểu đáp án của toàn train**. Không có bảng giao giữa type, domain, operation, filter, kỳ và khả năng dữ liệu để suy ra bao nhiêu câu được hỗ trợ bởi bảy API còn lại hoặc API extremum mới. Mở rộng verifier không tự tạo thêm capability nghiệp vụ hay năng lực hiểu câu hỏi.

[TRAIN_METADATA](TRAIN_METADATA.md) còn cảnh báo rõ ở phần quét từ khóa: 1908 sales/customer, 116 inventory/import và 116 debt là heuristic nhiều nhãn; có 85 câu giao nhóm và 923 câu không trúng nhóm nào. Không được dùng những số đó làm quota domain hoặc chứng minh coverage. Vì vậy, câu “trực tiếp mở khóa ... trong sales_or_customer” chưa được chứng minh. Mục tiêu 1000–1500 mới xuất hiện trong tiêu đề, chưa có phép tính khả thi hỗ trợ.

**Điều chỉnh:** lập inventory capability trên train với tiêu chí cố định, giữ cả ca không hỗ trợ/không resolve được; báo số thực đo theo operation và lý do. Đánh giá số câu khả thi sau bước này, không đặt số lượng mong muốn thành tiêu chí chọn câu. Nếu dùng nhãn để audit, không chuyển nhãn/type gold thành đầu vào suy luận runtime.

### 2. Cao — Không nên biến giới hạn v1 thành yêu cầu refactor ngay (dòng 27–41)

Mô tả `revenue_growth` và `revenue_share` chỉ dùng doanh thu là đúng. Nhưng kết luận “buộc phải nhân bản” chưa đúng: source không ngăn việc tái sử dụng helper nội bộ khi có nhu cầu đã được chứng minh. Có 10 API không tự chứng minh nguy cơ bùng nổ hàm hoặc tham số.

Mẫu số cả shop, hoãn parent-share và từ chối product filter ở cancellation_rate/top_customers là các quyết định v1 đã ghi trong [DECISIONS](../../DECISIONS.md) và [PROGRESS](../../../docs/PROGRESS.md). Với nhóm khách, mẫu số cả shop còn là luật nghiệp vụ train, không chỉ là hạn chế kỹ thuật. Tự tổng quát hóa có thể làm đổi scope, đơn vị, mẫu số hoặc thứ tự làm tròn.

**Điều chỉnh:** executor đầu tiên gọi public API hiện hành. Khi inventory chỉ ra nhu cầu ngoài capability, viết contract và test cho từng phép toán mới rồi mới cân nhắc helper chung. Đề xuất growth/share/extremum đa metric là hướng tương lai có điều kiện, chưa phải việc bắt buộc trước NLU.

### 3. Vừa — Mô tả percent “thang 0–100” sai với tăng trưởng (dòng 82)

Nhân 100 biểu diễn giá trị theo đơn vị phần trăm; không áp đặt miền giá trị từ 0 đến 100. [revenue_growth](../../../business/sales.py) tính `(current-baseline)/baseline*100`, nên có thể âm hoặc lớn hơn 100. [Evaluator local](../../../evaluate/evaluate.py) kiểm tra JSON number hữu hạn, không chặn các giá trị đó.

Probe tổng hợp trên fixture hiện có: doanh thu kỳ trước 101, kỳ sau 1010 trả `Answer('percent', 900)`; evaluator local chấp nhận format. `-50` cũng được chấp nhận. Nếu đem mô tả 0–100 vào JSON Schema chung cho percent, executor sẽ reject đáp án hợp lệ.

**Điều chỉnh:** ghi “số phần trăm, ví dụ 12.4 là 12.4%; miền giá trị phụ thuộc metric”. Không thêm ràng buộc min/max chung chỉ theo answer type.

### 4. Vừa — Cảnh báo tên khách chưa chứng minh được lỗi chấm điểm (dòng 86)

Nhận xét `.first()` phụ thuộc thứ tự dòng là đúng ở cấp chuỗi hiển thị. Nhưng phản chứng chỉ dùng khác biệt hoa/thường và khoảng trắng. `normalize_str` của evaluator local chuẩn hóa NFC, chuyển thường và bỏ khoảng trắng/dấu câu; `match_list` dùng cơ chế so chuỗi này.

Probe tổng hợp: hai đơn cùng `khach_key='lan'`, tên `Lan` và `  LAN  `; đảo thứ tự đơn làm đổi nhãn thô nhưng `match_list` vẫn trả đúng. Vì vậy đây chưa phải bằng chứng giảm PA theo evaluator local. Nếu hai nhãn khác nhau sau chuẩn hóa, cần một phản chứng riêng để xác định lỗi hợp nhất identity hoặc chọn label. Chưa có chứng nhận rằng evaluator local tương đương BTC.

**Điều chỉnh:** giữ đây là vấn đề tính ổn định hiển thị tiềm năng, không ưu tiên sửa trên cơ sở phản chứng hiện tại và không thay đổi quy tắc xác định khách chỉ để ổn định label.

### 5. Vừa — Mở rộng verifier cần đổi cách đối chiếu, không chỉ thêm dispatch (dòng 60–68, 107–109)

[verify_business.py](../../../verify_business.py) hiện:

- Tính bằng legacy trước và bỏ qua nếu legacy trả `BO_QUA` (dòng 56–59).
- Đối chiếu giá trị bằng phép trừ và tolerance số (dòng 82), chưa so được list bằng contract thứ tự/alias của evaluator.
- Có `matched_gold`, `matched_legacy`, errors và skips; đây là verifier hồi quy có phạm vi hẹp.

Gemini đúng khi yêu cầu không chọn theo kết quả khớp gold, nhưng chưa nêu hai rào cản trên. Nếu giữ legacy làm điều kiện vào, bảy API mới có thể vẫn bị loại. Nếu chỉ thêm nhánh dispatch, phép trừ list sẽ lỗi; cần cơ chế so đúng type/format/value.

“Bốn trạng thái” cũng không tạo thành một phân hoạch: selected là tập đầu vào, mismatch là một kết quả trong tập đó; không có matched trong danh sách và thiếu resolver không đồng nghĩa dữ liệu hỏng.

**Điều chỉnh:** giữ baseline hồi quy 417 chọn / 8 bỏ / 409 đối chiếu để so sánh; tạo đường kiểm chứng mở rộng không phụ thuộc legacy. Tách các giai đoạn selection, validation, resolution, capability, execution và scoring. Báo riêng matched, mismatch, unsupported, lỗi dữ liệu, lỗi resolve và lỗi triển khai; định nghĩa mẫu số, skip reason và ca không được chấm. Dùng contract evaluator cho list/alias/date, nhưng không đưa evaluator/gold vào business hoặc runtime.

### 6. Vừa — Group-disjoint không thay thế mục tiêu regression và không xóa lịch sử tiếp xúc train (dòng 56–59, 108)

Gemini đã nhận diện đúng đánh giá hồi cứu và rủi ro từ DESC_RULES. Tuy vậy, yêu cầu group-disjoint cho toàn bộ bước mở rộng verifier gộp hai mục tiêu: regression trên dữ liệu đã biết và đo khả năng chuyển sang họ file khác. [DECISIONS](../../DECISIONS.md) đã phân biệt hai mục tiêu này.

**Điều chỉnh:** báo regression trên manifest cố định và báo group-disjoint như một phép đo tổng quát hóa riêng. Với phép đo theo fold, chỉ artifact thực sự học/trích xuất để tái sử dụng qua doanh nghiệp mới cần rebuild từ dev; rulebook công bố và catalog mà loader tạo từ file đầu vào của chính doanh nghiệp đang được hỏi cần được mô tả đúng vai trò. Không dùng gold phía giữ lại để chọn capability/threshold. Dù rebuild artifact, kết quả vẫn là hồi cứu vì thiết kế đã tiếp xúc toàn train.

## Các nhận định có thể giữ

- Source có đúng 10 API gắn `@_answer`, trên sáu bảng chuẩn chính được nêu. Các API hiện chưa sinh date/string/boolean/table; điều này khác với việc toàn hệ thống chưa có format cho chúng: evaluator local đã có xử lý các type đó.
- Executor/NLU chưa triển khai. Luồng normalize → validate → resolve → capability → dispatch → Answer phù hợp hướng đã ghi trong repo; schema/helper lịch sử chưa phải production.
- 409/409 là đối chiếu trên tập chọn lọc chạm ba API, không phải PA toàn train, không chứng minh cả 10 API hoặc NLU. Các mẫu số 3000, 417, 409 và skip 8 được Gemini giữ đúng.
- Rulebook, as_of_date, loại đơn hủy/trả, dòng phí phục vụ và khách vãng lai là các ngữ nghĩa quan trọng phải giữ.
- Chỉ `_Unavailable` được decorator chuyển thành unanswerable; DataError/UnsupportedRule không được tự chuyển thành unanswerable. Cần giữ lỗi resolve riêng ở tầng executor.
- `quantity` đang làm tròn tối đa sáu chữ số thập phân. Đây là điểm cần contract, chưa có bằng chứng là bug. Rulebook train phân biệt tiền, phần trăm và số trung bình khác; không thể suy mọi tổng quantity phải làm tròn hai số từ phân bố gold.

## Hai điều kiện cho đề xuất kiến trúc và thứ tự làm

QueryPlan gọi business là baseline hợp lý cho code hiện tại vì tái sử dụng được kiểm tra nghiệp vụ. Nhưng bản Gemini so sánh nó chủ yếu với SQL tự do không có lớp bảo vệ. Chưa có benchmark cùng tập câu để kết luận QueryPlan luôn hơn mọi cách dùng SQL hoặc hơn trên model <=15B. SQL qua compiler/template tất định vẫn có thể là chi tiết backend về sau; chưa có lý do đổi backend trong phạm vi hiện tại.

Thứ tự tôi khuyến nghị: chốt contract Answer/scoring tối thiểu và inventory capability; xây executor nhỏ trên API hiện hành và JSON plan tổng hợp; mở rộng kiểm chứng; tích hợp model offline để đo plan và kết quả đầu-cuối; sau đó ưu tiên metric/domain mới bằng số đo. Nên chạy thử runner offline tối thiểu cùng baseline đầu-cuối trước khi mở rộng kho/nợ. Chuyển từ sales sang tồn/nợ còn cần thời điểm snapshot cuối ngày, số dư đầu kỳ và phát sinh liên quan theo rulebook, không chỉ thêm hàm hoặc answer type.

Sửa đường dẫn self-score có thể giúp chạy thêm test, nhưng self-score đúng vẫn không chứng nhận evaluator tương đương BTC. Cần bằng chứng đối chiếu với đặc tả/implementation BTC được cung cấp. Không nên đợi đến sau khi mở rộng nghiệp vụ mới kiểm tra contract chấm cơ bản.

## Kiểm chứng trong lượt này

- Chạy `scripts/harness.py map`, đọc source và tài liệu liên quan trên working tree hiện tại.
- Chạy probe tổng hợp dùng fixture `tables.__wrapped__()` từ `tests/test_business_sales.py`, RULES từ `tests/conftest.py`, và hàm so từ `evaluate/evaluate.py` qua `runpy.run_path`. Không thêm test hoặc sửa Python vì đây là review. Thay tên hai đơn hợp lệ như mục 4 rồi đảo DataFrame để so label; thay hai dòng tiền của O2 thành 900 và 110 để đo growth so với O1 = 101. Kết quả: raw_labels_differ=true, local_evaluator_equal=true, growth=900, valid_local_format=true; percent=-50 có format hợp lệ.
- `.\.venv\Scripts\python.exe scripts/harness.py check`: exit 0, **301 passed, 2 local_data deselected**, fast/full qua. Lượt này chạy trước khi thêm hồ sơ review. Sau khi thêm hồ sơ, `check --profile fast` cũng exit 0, kiểm tra 79 file.
- Không chạy lại gold verifier/data profile: không thay loader/business/evaluator hoặc dữ liệu; không có tuyên bố mới về gold accuracy. Số 409/409 là bằng chứng đã ghi trước đây trong PROGRESS/validation.
- Chỉ thêm hồ sơ review; không đổi trạng thái triển khai nên không cập nhật PROGRESS.

## Nội dung phản hồi đề nghị gửi Gemini ở lượt tiếp theo

1. Rút cam kết 1000–1500 và suy luận coverage từ type/regex; chỉ rõ phép đo hoặc bảng giao còn thiếu để ước tính khả thi.
2. Phân biệt giới hạn v1 có chủ ý với lỗi; giữ API công khai cho executor đầu tiên, nêu điều kiện cần trước khi tổng quát growth/share/extremum.
3. Sửa contract percent; phản chứng label cần khác sau chuẩn hóa evaluator mới chứng minh lỗi chấm.
4. Bổ sung thiết kế verifier đa type, không bị legacy gate, có kết quả matched và lỗi resolve riêng, giữ rõ mẫu số.
5. Tách regression khỏi group-disjoint, giữ nhãn đánh giá hồi cứu. Không tự động coi rebuild artifact là khôi phục holdout chưa từng thấy.

Nếu tiếp tục trao đổi, yêu cầu Gemini xuất toàn bộ phản hồi thành file Markdown UTF-8 tải xuống được, ghi nguồn/revision đã đọc; nếu không đính kèm được, xuất trong một khối bốn backtick nhãn markdown. Không gửi BTC rows/questions/answers. Chưa gửi nội dung sang dịch vụ ngoài trong lượt này.
