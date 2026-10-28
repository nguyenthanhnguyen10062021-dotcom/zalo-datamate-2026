# Trao đổi giữa người dùng Codex và Gemini

Thư mục này dùng để đưa bối cảnh từ repo sang Gemini web, nhận phản biện rồi đưa về Codex kiểm chứng và triển khai. Mỗi vòng tập trung vào một vấn đề. Có thể dùng cùng cách này với LLM khác.

## Bắt đầu ngay

Nhánh làm việc: [VuongNguyen trên GitHub](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/VuongNguyen). Bản code nền cho vòng 001: [`1c89252`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/1c89252). Xem [bằng chứng kiểm chứng](../docs/validation.md).

1. Mở cuộc trò chuyện mới trên Gemini web và chọn model bạn muốn dùng.
2. Tải lên **[GEMINI_HANDOFF.md](GEMINI_HANDOFF.md)**. File này chứa bối cảnh, yêu cầu vòng đầu và bản chụp mã nguồn/test liên quan; Gemini không cần truy cập ổ đĩa của bạn.
3. Copy nội dung **[GEMINI_START_PROMPT.md](GEMINI_START_PROMPT.md)** vào tin nhắn rồi gửi.
4. Copy nguyên phản hồi Gemini vào **[rounds/001_business_to_nlu/GEMINI_RESPONSE.md](rounds/001_business_to_nlu/GEMINI_RESPONSE.md)**. Điền model/ngày nếu bạn biết; không cần chỉnh lại toàn bộ cấu trúc phản hồi.
5. Quay lại chat này và nhắn: **“Hãy đọc phản hồi Gemini ở vòng 001, phản biện và đề xuất bước tiếp theo.”**

Codex sẽ kiểm tra đề xuất với code, rulebook và test, ghi kết quả vào `CODEX_REVIEW.md`. Nếu cần hỏi tiếp, Codex chuẩn bị yêu cầu vòng kế tiếp để bạn gửi lại Gemini. Nếu bạn yêu cầu triển khai, Codex thực hiện phần đã được giao và ghi bằng chứng kiểm chứng.

Đây là trao đổi qua file do bạn chuyển tiếp. Việc tạo thư mục không kết nối tài khoản Gemini hoặc tự gửi nội dung lên web.

## Các file chính

| File | Mục đích |
|---|---|
| `GEMINI_HANDOFF.md` | File sẵn để tải lên Gemini, tự chứa cả bối cảnh và source snapshot |
| `GEMINI_START_PROMPT.md` | Tin nhắn mở đầu để copy vào Gemini |
| `PROJECT_CONTEXT.md` | Bối cảnh chung và giới hạn của repo |
| `DECISIONS.md` | Các quyết định đã có và các vấn đề còn mở |
| `rounds/001_business_to_nlu/` | Vòng đầu: review thư viện nghiệp vụ và hướng nối tầng hiểu câu hỏi |
| `templates/DISCUSSION_REQUEST.md` | Mẫu mở một vấn đề mới |

## Vòng đầu đang hỏi gì

Thư viện nghiệp vụ bán hàng đã có bản đầu. Cần review giới hạn hiện tại và chọn cách xây tầng hiểu câu hỏi gọi thư viện: kế hoạch JSON có kiểm tra, sinh code, hay cách kết hợp. Đây là đề bài thảo luận; chưa chốt triển khai tầng NLU.

## Duy trì qua nhiều vòng

- Mở vòng mới theo tên `002_<chu_de>`, `003_<chu_de>`; giữ vòng cũ để tra lại lý do quyết định.
- Phân biệt rõ nội dung do Codex viết, phản hồi Gemini và quyết định của người dùng. Không ghi rằng hai bên đã đồng ý khi chưa có phản hồi.
- Khi code hoặc kết quả kiểm chứng thay đổi, nhờ Codex cập nhật `PROJECT_CONTEXT.md` và tạo lại `GEMINI_HANDOFF.md` trước khi gửi. Bản upload là snapshot, không tự đồng bộ với repo.
- Mỗi handoff ghi code commit và SHA256 của source đính kèm (nội dung UTF-8 với xuống dòng LF). Khi có thay đổi chưa commit cần ghi rõ; không dùng commit nền để ngụ ý các thay đổi đó đã nằm trên GitHub.
- Nguồn chuẩn là code hiện tại, dữ liệu/rulebook đúng split và kết quả chạy thực tế. Nếu nhận xét cũ mâu thuẫn với nguồn mới, kiểm chứng rồi cập nhật quyết định.
- Packet hiện chỉ gồm tài liệu kỹ thuật, source, test tổng hợp và số liệu kiểm chứng tổng hợp. Không tự đưa dữ liệu doanh nghiệp, câu hỏi/đáp án BTC, cache hoặc file môi trường vào packet. Nếu cần ví dụ, ưu tiên fixture tổng hợp và chỉ thêm đúng phần phục vụ vấn đề đang hỏi.
- Gemini hỗ trợ phát triển và review. Pipeline nộp thi vẫn tuân theo yêu cầu chạy offline bằng model hợp lệ của cuộc thi.

## Câu lệnh trao đổi với Codex

> Cập nhật gói Gemini theo trạng thái repo hiện tại. Chủ đề tiếp theo là …

> Đọc GEMINI_RESPONSE.md của vòng 001, kiểm chứng từng nhận xét và viết phản hồi cho Gemini.

> Dựa trên quyết định đã chốt ở vòng 001, triển khai … và cập nhật kết quả test vào hồ sơ trao đổi.
