# Áp dụng bản sửa nghiệp vụ sau review lượt 04

Ngày: 2026-10-29, Asia/Saigon. Người dùng yêu cầu đưa bản sửa đã kiểm chứng vào code chính, chuyển phản chứng thành test trong repo và chạy lại kiểm tra.

## Đã triển khai

Đã áp dụng `CODEX_BUSINESS_PATCH_04.diff` vào `business/sales.py`, đúng bản ứng viên Codex đã kiểm chứng ở lượt 04:

- Kiểm tra đủ bảng và kiểu cấu trúc cache, phát sinh DataError rõ ràng.
- Kiểm tra khóa catalog/liên kết dòng hàng theo dependency của metric; vẫn chặn ORPHAN khi dùng dòng hàng.
- Loại đơn hủy/trả đã biết trước bộ lọc cho metric chỉ tính đơn hợp lệ; kiểm tra trạng thái chưa biết sau bộ lọc. Tỷ lệ hủy vẫn xét mọi trạng thái.
- Thêm order filters cho cancellation_rate và top_customers; reject product filters bằng UnsupportedRule đã import đúng. Giữ thứ tự tham số cũ và cấu trúc Answer.
- Revenue share chỉ yêu cầu điều khoản nhóm khách khi dùng bộ lọc nhóm khách; mẫu số vẫn cả shop.

Không thay đổi số học, làm tròn hoặc bổ sung tầng NLU/QueryPlan.

## Test đã lưu trong repo

Thêm **39 ca kiểm thử** trong `tests/test_business_sales.py`, gồm:

- Thiếu bảng, sai kiểu dữ liệu đầu vào, thiếu cột ngày.
- Catalog thiếu/trùng khóa: đếm đơn vẫn chạy, metric phụ thuộc catalog bị chặn.
- ORPHAN: metric cấp đơn vẫn chạy, metric cần dòng hàng bị chặn.
- Trạng thái lỗi ở kênh khác, cùng kênh hoặc kênh chưa biết; mẫu số share vẫn kiểm tra cả shop.
- Ba phản chứng regression của patch Gemini và trường hợp thiếu giờ ở đơn trả hàng.
- Tỷ lệ hủy không bỏ đơn hủy/trả thiếu thông tin cần lọc.
- Order filters trên xếp hạng khách với cả revenue/orders và giữ cách gọi tham số vị trí; reject product filter ở cả hai API mới.
- Share không phụ thuộc sai vào luật nhóm khách; doanh thu khách vãng lai vẫn nằm trong mẫu số.

Trước khi áp dụng code, đã chạy một tập 19 ca mới trên baseline và tái hiện được lỗi. Sau khi áp dụng, full suite qua.

## Kiểm chứng trên code chính

- `python -m pytest -q -rs`: **258 passed, 1 skipped**. Skip cũ ở `evaluate/test_evaluate.py:80` do helper tìm `answers.jsonl` sai vị trí; không phải thiếu gold train.
- `python verify_business.py --out reports/business_verification_applied04`: **exit 0, 409/409 khớp gold và phép tính cũ, 0 lỗi**; chọn 417 câu, legacy bỏ qua 8. Đây là lượt chạy mới trên code chính sau khi áp dụng patch, không dùng lại kết quả từ bản sao.
- `git diff --check`: qua. Đã so source chính với ứng viên và xác nhận nội dung giống nhau; kiểm tra UTF-8 và các liên kết tài liệu đều qua.

Verifier là hồi quy trên tập chọn lọc, không phải PA toàn train hoặc bằng chứng NLU đã hoạt động. Dữ liệu, đáp án từng câu và report chi tiết chỉ lưu local.

## Trạng thái source và hồ sơ trao đổi

Code chính, test và tài liệu API đã commit tại [`c567b29`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/commit/c567b29) trên nhánh `VuongNguyen`. Base trước khi áp dụng là `2085afa`; không dùng base đó để ngụ ý chứa bản sửa mới. Hồ sơ trao đổi được lưu trong commit tài liệu kế tiếp.

SHA256 nội dung UTF-8 chuẩn hóa xuống dòng LF tại thời điểm triển khai:

- `business/sales.py`: `636c59bd394795075be7a0b3b9c9fa3f227a6105de96c73b27fca87b27cbe638`.
- `tests/test_business_sales.py`: `bb6abad7d3537c4cf1e30c9a3334e5aea40c84f0f95716e4555fed5d44b39b3c`.

`CODEX_REVIEW_04.md`, `CODEX_REPLY_TO_GEMINI_04.md`, `GEMINI_HANDOFF.md` và bản diff giữ vai trò hồ sơ lịch sử trước khi áp dụng. Khi tiếp tục gửi Gemini phải kèm cập nhật triển khai này và source/test hiện hành; không dùng snapshot nghiệp vụ `1c89252` như thể đó vẫn là toàn bộ code mới nhất.
