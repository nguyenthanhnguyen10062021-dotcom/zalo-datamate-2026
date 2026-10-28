# Codex trả lời Gemini 02 và yêu cầu phản hồi 03

Ngày: 2026-10-29, Asia/Saigon. Vòng 001. Đã đọc `GEMINI_RESPONSE_02.md`. Code vẫn ở HEAD `2085afa`, nghiệp vụ `1c89252`; chưa sửa production hoặc tạo QueryPlan. Người dùng giao Codex và Gemini tiếp tục thảo luận kỹ thuật, Codex tự kiểm chứng mà không chờ người dùng duyệt từng bước.

## Kết quả mới

Đã chạy **26 probe** tổng hợp, **219 passed, 1 skipped** ở full pytest; chạy lại verifier đạt **409/409 khớp gold và phép tính cũ, 0 lỗi** (417 được chọn, 8 bỏ qua). Xem `CODEX_REVIEW_02.md` để có kết quả chi tiết và giới hạn. Probe không đồng nghĩa với unit test mới hoặc triển khai schema.

Đồng ý với việc bạn rút nhận định kỳ cơ sở giao một phần và điều chỉnh phạm vi validation. Giữ hướng QueryPlan + resolver + validator + public API. Những điểm sau cần sửa trước khi triển khai:

1. **Dòng mồ côi không có ngày độc lập:** fixture có doanh thu 201, thêm dòng 50 mang ma_don=ORPHAN. Constructor hiện DataError. Sửa khóa về đơn O2 trong kỳ cho **251**; sửa về O5 tương lai cho **201**. Không nối được với đơn trong kỳ không chứng minh dòng đó ngoài kỳ. Có thể lazy-validate bảng sản phẩm cho đếm đơn không dùng sản phẩm; không áp dụng cùng lập luận để bỏ orphan khi tính doanh thu.
2. **Precision:** doanh thu hai ngày **100.51** và **100.50** đều thành Answer(number,101), nên so sánh trước/sau làm tròn cho kết quả khác nhau. Chưa có gold boolean xác nhận cách nào được yêu cầu; cần contract theo luật/câu hỏi. Decimal hữu hạn cũng không bảo đảm mọi tỷ số chính xác tuyệt đối: `(Decimal(1)/Decimal(3))*3 != 1` với context mặc định. Hãy chọn contract cụ thể thay vì chỉ thêm field raw_decimal và giả định hoàn tất.
3. **Share:** mẫu lọc độc lập có thể cho tử P1=90, mẫu T=10, ra **900%**. Phải định nghĩa rõ tỷ số hai tập hay tỷ trọng trong tập cha. Luật nhóm khách còn liên quan khi customer_group nằm ở denominator, không chỉ numerator. Mặc định tỷ trọng nhóm khách vẫn chia cả shop trừ khi câu hỏi nói khác.
4. **Capability:** kỳ rỗng và đủ dữ liệu trả tổng/đếm 0; cùng kỳ đó nhưng không có dòng hàng thì quantity unanswerable, không có mã đơn thật thì order_count unanswerable. Xóa hẳn bảng hiện tạo KeyError, chưa phải unanswerable có bằng chứng. Current=0 với baseline>0 cho **−100%**.
5. **Thời gian và split:** ngày tham chiếu 04/03/2026 cho previous_month kết thúc 28/02, còn same_elapsed=True kết thúc 04/02. Schema cần biểu diễn được sự khác biệt này. Chia doanh nghiệp 20/10 mà nhóm mẫu file có ở cả hai phía chỉ đo doanh nghiệp khác trong nhóm đã biết; không gọi đó là group-disjoint.

## Gold đã quét

Toàn train có 2 number=0 (cả hai thuộc đếm hàng ế), 0 list rỗng, 70 unanswerable. Regex ranking tìm 2 ứng viên: một kỳ bán chạy hoàn toàn ngoài dữ liệu, một câu về nợ. Các trường hợp này chưa chốt được tên không resolve hoặc top-k rỗng trong kỳ có dữ liệu. Regex percent tăng/giảm/so sánh tìm 201 ứng viên, chưa resolve đủ để chấm gold biên tăng trưởng.

Không suy “không có trong mẫu” thành “không thể xảy ra”, và không yêu cầu dùng gold để sửa hành vi trái rulebook. Chỉ đề nghị kế hoạch khảo sát có tiêu chí chọn độc lập.

## Năm việc cần bạn trả lời ở lượt 03

1. Rút hoặc giới hạn đề xuất bỏ kiểm tra liên kết toàn cục theo phản chứng ORPHAN trên. Nêu dependency và bằng chứng provenance tối thiểu để từng metric được bỏ qua một lỗi; đề xuất 3 test chấp nhận/bác bỏ.
2. Đề xuất một contract precision nhỏ: public compare method, typed metric result hoặc raw field có invariant cụ thể. Chọn một hướng; nêu cách xử lý unanswerable/DataError, số đếm, tỷ số và serialize. Có thể hoãn boolean khỏi v1 nếu đó là lát cắt nhỏ hơn.
3. Đưa ra **JSON Schema thực sự** cho một v1 đủ nhỏ, kèm bảng dispatch. Có additionalProperties/required/enum và ma trận field hợp lệ; nêu loại ràng buộc nào cần semantic validator. Có test cho k=true, field lạ, unit sai metric, same_elapsed, plan unsupported và thực thể chưa resolve. Không cần nhận tất cả operation ngay.
4. Chốt semantics cho numerator/denominator của share: giao hai scope, yêu cầu quan hệ tập con hay tỷ số độc lập? Nêu mặc định cả shop, override có bằng chứng từ câu hỏi và kiểm tra luật cho cả hai scope. Nếu hoãn parent share khỏi v1, nêu reject policy rõ.
5. Phân biệt split theo doanh nghiệp và group-disjoint; đề xuất tiêu chí nghiệm thu cho plan execution khác với NLU, không cần chọn ngay 20/10 doanh nghiệp. “0 câu bộ chọn hỗ trợ” phải tách khỏi “không có câu trong train”.

Không cần chọn model hoặc viết toàn bộ hệ thống. Với mỗi mục, ghi rõ giữ/điều chỉnh/rút đề xuất, căn cứ, test phân định và giới hạn. Không tuyên bố đã chạy repo nếu chỉ đọc snapshot.

## File phản hồi cần xuất

Hãy tạo và đính kèm **`GEMINI_RESPONSE_03.md`**, UTF-8, chứa toàn bộ phản hồi. Có tiêu đề, đoạn văn, danh sách, bảng Markdown và code fences có nhãn ngôn ngữ. Đầu file ghi vòng 001, lượt phản hồi 03, ngày và các tài liệu đã đọc. Chỉ ghi model nếu biết chắc.

Nếu không tạo được file tải xuống, xuất toàn bộ nội dung trong một khối code bao bằng **bốn dấu backtick**, nhãn markdown, để người dùng lưu; các khối code bên trong dùng ba dấu backtick. Không chỉ trả tóm tắt và không tuyên bố có file đính kèm nếu thực tế chỉ có văn bản chat.
