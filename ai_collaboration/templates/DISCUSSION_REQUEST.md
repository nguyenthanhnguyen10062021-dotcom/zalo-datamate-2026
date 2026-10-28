# Vòng NNN Chủ đề

- Người gửi:
- Người nhận/model:
- Ngày:
- Trạng thái: đề xuất/chờ phản hồi/đang kiểm chứng/đã chốt.
- Base commit và SHA256 của source snapshot:

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

Hãy tạo và đính kèm một file Markdown UTF-8 có thể tải xuống, tên `GEMINI_RESPONSE_<NN>.md` (bên gửi thay `<NN>` bằng số lượt phản hồi trước khi gửi prompt). File phải chứa toàn bộ phản hồi, không chỉ bản tóm tắt. Dùng tiêu đề, đoạn văn, danh sách, bảng Markdown và khối code có nhãn ngôn ngữ; không gộp các mục hoặc hàng bảng thành một dòng dài. Đầu file ghi vòng thảo luận, lượt phản hồi, ngày và các file nguồn đã đọc. Chỉ ghi model nếu biết chắc, không tự đoán.

Nếu giao diện không hỗ trợ tạo file đính kèm, xuất toàn bộ nội dung file trong một khối code duy nhất bao bằng bốn dấu backtick, nhãn `markdown`, để người dùng lưu thành file; các khối code bên trong dùng ba dấu backtick. Không tuyên bố đã tạo file tải xuống nếu chỉ trả văn bản trong chat.
