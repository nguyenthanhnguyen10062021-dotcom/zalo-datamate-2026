# Vòng NNN Chủ đề

- Người gửi:
- Người nhận/model:
- Ngày:
- Trạng thái: đề xuất/chờ phản hồi/đang kiểm chứng/đã chốt.
- Base commit và SHA256 của source snapshot:
- Dirty state / packet revision:
- Trả lời file/finding nào:
- File thực đọc / lệnh và kết quả thực chạy / phần chưa kiểm:

Với vòng ba AI, dùng cùng một BRIEF/packet cho Codex, Gemini Web và Antigravity; prompt riêng chỉ điều chỉnh cách truy cập và nơi lưu phản hồi. Lượt đầu lấy ý kiến riêng, lượt tiếp mới trao đổi phản biện chéo. Không đồng nhất Antigravity với Argon lịch sử.

## Kết quả cần đạt

Nêu một vấn đề chính, vì sao cần xử lý và điều gì được coi là giải quyết xong.

## Bối cảnh mới so với vòng trước

Code, dữ liệu/schema, giới hạn, kết quả test hoặc quyết định nào đã thay đổi? Phân biệt dữ kiện được kiểm chứng, giả định và đề xuất.

## Quan điểm hiện tại của bên gửi

Đề xuất, lý do và các phương án đã cân nhắc. Không coi đây là lựa chọn đã được người dùng chốt nếu chưa có căn cứ.

## Cần bên kia phản biện

Tối đa 5 câu hỏi rõ ràng. Với mỗi vấn đề quan trọng, đề nghị nêu ví dụ phản chứng hoặc thử nghiệm có thể phân định.

## Source và bằng chứng đính kèm

Chép nội dung file thực sự cần vào handoff hoặc đính kèm riêng. Đường dẫn local một mình không giúp LLM web đọc được repo. Ghi lệnh kiểm chứng và kết quả thực tế; nếu chưa chạy thì ghi chưa chạy.

## Định dạng phản hồi

Kết luận → căn cứ → mức chắc chắn → phương án/đánh đổi → test đề xuất → câu hỏi gửi lại. Không cần mô tả suy nghĩ nội bộ; cần giải thích kỹ thuật có thể kiểm tra.

Hãy tạo và đính kèm một file Markdown UTF-8 có thể tải xuống, tên `<PARTICIPANT>_RESPONSE_<NN>.md` (bên gửi thay bằng `GEMINI_RESPONSE_01.md` hoặc `ANTIGRAVITY_RESPONSE_01.md` và số lượt đúng trước khi gửi prompt). Nếu agent có repo và được giao ghi phản hồi, ghi đúng file mới trong `messages/` của vòng, không ghi đè file có sẵn. File phải chứa toàn bộ phản hồi, không chỉ bản tóm tắt. Dùng tiêu đề, đoạn văn, danh sách, bảng Markdown và khối code có nhãn ngôn ngữ; không gộp các mục hoặc hàng bảng thành một dòng dài. Đầu file ghi vòng thảo luận, lượt phản hồi, ngày, file đang trả lời và các file nguồn thực đọc. Chỉ ghi model nếu biết chắc, không tự đoán. Ghi findings theo ID của bên gửi để Codex kiểm chứng riêng từng nhận định; phân biệt đề xuất, kết luận kỹ thuật và triển khai đã làm.

Nếu giao diện không hỗ trợ tạo file đính kèm, xuất toàn bộ nội dung file trong một khối code duy nhất bao bằng bốn dấu backtick, nhãn `markdown`, để người dùng lưu thành file; các khối code bên trong dùng ba dấu backtick. Không tuyên bố đã tạo file tải xuống nếu chỉ trả văn bản trong chat.
