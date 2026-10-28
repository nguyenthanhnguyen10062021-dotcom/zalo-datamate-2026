# Bối cảnh project DataMate

**Trạng thái kết thúc phiên 2026-10-29:** bản sửa sau review Gemini lượt 04 đã áp dụng và đẩy lên `VuongNguyen` tại [`c567b29`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/commit/c567b29); hồ sơ trao đổi đã đẩy tại `211e492`. Thêm 39 ca kiểm thử, full suite đạt 258 passed, 1 skipped và verifier đạt 409/409. Xem [tiến độ/điểm tiếp tục](../docs/PROGRESS.md), [triển khai](rounds/001_business_to_nlu/CODEX_IMPLEMENTATION_04.md) và [validation](../docs/validation.md). Bối cảnh dưới đây được cập nhật theo code hiện hành; `GEMINI_HANDOFF.md` ngày 2026-10-28 là snapshot lịch sử riêng.

Bối cảnh cập nhật ngày **2026-10-29**, timezone Asia/Saigon. Code nghiệp vụ và test hiện hành nằm tại `c567b29`. Handoff cũ giữ source `1c89252` và SHA256 của các file ở thời điểm đó; không dùng các hash cũ để kiểm tra nội dung file hiện tại đã thay đổi.

Repo: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/VuongNguyen

Phiên bản code cố định hiện hành: https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/c567b29

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
- cancellation_rate và top_customers đã nhận filter cấp đơn; product filter ở hai API này bị reject rõ ràng. Kiểm tra catalog/liên kết dòng hàng theo dependency của metric; vẫn chặn ORPHAN khi dùng dòng hàng.
- Kết quả: `Answer`; chuyển thành object nộp bài bằng `to_submission(id)`.
- Thiếu loại dữ liệu/ngoài kỳ/mẫu số 0: unanswerable. Dữ liệu chuẩn lỗi hoặc thiếu một phần: `DataError`. Luật ngoài mẫu được hỗ trợ: `UnsupportedRule`. Hai lỗi sau không được tự coi là chứng minh câu hỏi unanswerable.
- Đọc file rulebook do người gọi truyền và kiểm tra các cụm điều khoản cần thiết. Đây là parser có phạm vi giới hạn, không suy luận mọi nội dung rulebook tiếng Việt bất kỳ.

Phí phục vụ được tính doanh thu nhưng bỏ khỏi xếp hạng sản phẩm; topping có thể là mặt hàng. Đơn hủy/trả loại cả đơn, đang giao vẫn tính. Số đơn cần mã thật. Tỷ lệ hủy có mẫu số mọi trạng thái. Xếp hòa theo mã. Tiền làm tròn half-up; tỷ lệ hai chữ số theo luật hỗ trợ.

API chi tiết và giới hạn nằm trong `docs/business.md`, cũng được chép trong handoff.

## Bằng chứng kiểm chứng gần nhất

- Full pytest chạy trên code chính sau patch ngày 2026-10-29: **258 passed, 1 skipped**, gồm 39 ca mới lưu trong repo. Test cũ `evaluate/test_evaluate.py::test_self_score_real_file` tìm gold dưới `evaluate/` thay vì gốc repo nên vẫn bị bỏ qua; không phải thiếu đáp án train hiện tại.
- Bộ kiểm tra chọn **417/3000** câu, bỏ qua **8** theo bộ chọn cũ, đối chiếu được **409**.
- Thư viện mới khớp gold **409/409**, khớp phép tính cũ **409/409**, 0 lỗi.
- Thành phần: 187 doanh thu tháng, 76 số đơn hủy, 130 số lượng, 8 doanh thu ca sáng và 8 ca chiều.
- Đây là hồi quy trên tập con, **không phải** PA toàn bộ 3000 câu và không chứng minh các metric khác đều đúng trên dữ liệu thật.
- Có test tổng hợp cho các hàm khác và smoke API trên một doanh nghiệp train/một public. Có review độc lập; các lỗi phát hiện đã được tái hiện bằng test và sửa.
- Đã chạy mới `verify_business.py --out reports/business_verification_applied04` trên code chính sau patch: exit 0, khớp 409/409, 0 lỗi; `git diff --check` qua. Cần chạy lại sau thay đổi code có liên quan. Lượt cập nhật tài liệu cuối phiên không chạy lại code/test.

## Chưa có

Tầng hiểu câu hỏi/resolve thực thể, model weights/runtime inference, QueryPlan schema, dispatcher/validator, confidence/abstain toàn hệ thống, runner sinh full submission, log từng câu và Docker. Chưa có API kho, nợ, lợi nhuận và đầy đủ luật ngành.

## Hướng tiếp theo đã thống nhất

Triển khai executor QueryPlan v1: normalize → structural/semantic validation → resolve period/entity/unit → capability → public API → Answer/log. V1 hoãn boolean/raw_decimal và parent-share. Resolver cần unit tường minh và policy tên trùng nhiều mã; schema phải có URI thuần. Sau executor mới tích hợp model câu hỏi → QueryPlan và đánh giá NLU riêng.

Đã kiểm chứng đến phản hồi Gemini 04; prompt 05 đã sẵn, chưa có GEMINI_RESPONSE_05.md trong repo khi kết thúc phiên. Codex tiếp tục tự kiểm chứng phản hồi mới theo ủy quyền của người dùng, không chờ duyệt từng chi tiết. Xem [thứ tự công việc phiên sau](../docs/PROGRESS.md).
