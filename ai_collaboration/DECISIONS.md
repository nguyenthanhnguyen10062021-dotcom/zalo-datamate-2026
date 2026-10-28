# Quyết định và vấn đề còn mở

Tài liệu này ghi trạng thái thực tế. Đề xuất của một AI không tự trở thành quyết định của người dùng. Không có phản hồi Gemini nào được ghi nhận tại thời điểm tạo thư mục.

## Nền tảng đã có trước vòng 001

| ID | Nội dung | Trạng thái và căn cứ |
|---|---|---|
| D001 | Tách loader, thư viện nghiệp vụ và tầng hiểu câu hỏi | Loader và `business/` đã triển khai theo trao đổi với người dùng; tầng hiểu câu hỏi chưa triển khai |
| D002 | Truyền rulebook đúng split và as_of_date vào phép tính | Đã có API và test; parser rulebook có phạm vi hỗ trợ giới hạn |
| D003 | Không tự coi DataError/UnsupportedRule là bằng chứng câu hỏi unanswerable | Đã thể hiện bằng API/test và tài liệu business |
| D004 | Gemini web tham gia review phát triển, người dùng chuyển tiếp qua file | Người dùng yêu cầu; chưa có tích hợp API hoặc đồng bộ tự động |

## Đang thảo luận

| ID | Vấn đề | Trạng thái | Nơi trao đổi |
|---|---|---|---|
| O001 | Contract và kiến trúc NLU → phép tính; độ sẵn sàng của API hiện tại | Chờ Gemini phản hồi | `rounds/001_business_to_nlu/` |
| O002 | Mở rộng nghiệp vụ trước hay triển khai một lát cắt NLU nhỏ trước | Chưa chốt | Vòng 001 |
| O003 | Model inference offline và môi trường chạy | Chưa chọn; chưa yêu cầu quyết định trong vòng 001 | Thảo luận sau khi rõ phạm vi và ngân sách |

## Mẫu ghi quyết định mới

- ID và ngày:
- Vấn đề/vòng thảo luận:
- Đề xuất của Codex:
- Ý kiến Gemini hoặc LLM khác:
- Bằng chứng đã kiểm tra và giới hạn:
- Quyết định, ai quyết định, phạm vi được giao:
- Lý do và đánh đổi:
- File thay đổi/test đã chạy nếu có:
- Điều kiện cần xem lại:
