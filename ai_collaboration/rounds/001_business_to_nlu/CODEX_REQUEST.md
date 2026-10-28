# Vòng 001 Review nền nghiệp vụ và hướng nối tầng hiểu câu hỏi

- Người gửi: Codex, theo yêu cầu phối hợp của người dùng.
- Người nhận: Gemini web, model do người dùng chọn.
- Ngày mở: 2026-10-28.
- Trạng thái: Đã nhận phản hồi Gemini và Codex kiểm chứng ngày 2026-10-29; xem CODEX_REVIEW.md.
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
