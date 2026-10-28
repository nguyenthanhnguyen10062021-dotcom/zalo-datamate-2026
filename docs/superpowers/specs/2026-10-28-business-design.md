# Thư viện nghiệp vụ bán hàng DataMate

Người dùng giao quyền triển khai bước 3 trên repo hiện tại. Mục tiêu là một API Python tất định nhận schema chuẩn, rulebook của đúng split và as_of_date, để tầng hiểu câu hỏi sau này gọi được. Không đọc answers.jsonl trong thư viện.

## Phương án

Giữ phép tính trong script kiểm tra sẽ khó tái sử dụng. Cho LLM sinh mọi phép tính chưa phù hợp vì chưa có tầng suy luận và khó kiểm thử luật. Chọn package `business/` dùng pandas hiện có, tách rulebook, thời gian và phép tính; giữ bộ phân loại câu hỏi hiện tại làm công cụ kiểm chứng độc lập.

## Phạm vi bản đầu

- DateRange gồm hai đầu; ngày, tuần, tháng, quý, đầu năm, N ngày và Tết tra calendar của split; kỳ so sánh tháng này lấy cùng số ngày tháng trước.
- Doanh thu, số đơn hợp lệ/hủy, tỷ lệ hủy, trung bình đơn, số lượng đơn vị cơ bản, tăng trưởng, tỷ trọng, xếp hạng sản phẩm/khách.
- Lọc sản phẩm, nhóm hàng, kênh, hình thức thanh toán, nhóm khách và ca khi cột cần thiết có dữ liệu.
- Đọc và kiểm tra những điều khoản rulebook mà mỗi thao tác sử dụng. Luật chưa được hỗ trợ phải báo lỗi UnsupportedRule, không âm thầm áp luật train. Không hứa diễn giải mọi rulebook tiếng Việt bất kỳ.
- Kết quả thiếu thông tin là unanswerable; schema/cache hỏng hoặc luật chưa hỗ trợ là lỗi rõ ràng để tầng agent có thể abstain. Thiếu giá trị ở dòng liên quan không được cộng thành 0.
- Đơn không có mã thật không đủ để đếm đơn hay tính trung bình đơn. Không huỷ/không trả, bao gồm đang giao; phí phục vụ vào doanh thu, loại khỏi xếp hạng sản phẩm. Giá trị tiền làm tròn half-up; tỷ lệ hai chữ số.
- Đọc cache từ đường dẫn người gọi truyền, không bắt ID doanh nghiệp/câu hỏi. Không sửa loader, dữ liệu và evaluator.

Kho, công nợ, giá vốn/lợi nhuận và luật ngành chưa đủ bảng chuẩn được để ngoài API bản đầu; không suy unanswerable chỉ vì bản phần mềm chưa có tính năng. Chưa làm NLU, model, CLI dự đoán hay Docker.

## Kiểm chứng

Lưu kết quả check_with_gold cũ làm baseline. Viết test dữ liệu tổng hợp cho ranh giới ngày/ca/làm tròn, số 0 với thiếu dữ liệu, loại cả đơn trả, mẫu số tỷ lệ hủy, fallback bảng đơn, xếp hạng hòa và khách lẻ. So API mới với cùng các câu đủ điều kiện của bộ kiểm tra cũ, báo rõ số câu so được/bỏ qua và mọi chênh lệch; đây không phải PA toàn bộ train.
