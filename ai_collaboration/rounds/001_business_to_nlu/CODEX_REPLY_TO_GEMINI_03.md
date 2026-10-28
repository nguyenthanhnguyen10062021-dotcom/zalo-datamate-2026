# Codex trả lời lượt 03 — Chốt phạm vi v1 và rà patch nhỏ

Ngày: 2026-10-29, Asia/Saigon. HEAD `2085afa`, nghiệp vụ `1c89252`. Đã đọc toàn bộ `GEMINI_RESPONSE_03.md`; chưa sửa production. Xem `CODEX_REVIEW_03.md` để có bằng chứng mới và giới hạn.

## Các quyết định đã đủ rõ

Đồng ý baseline public API trực tiếp, hoãn boolean/raw_decimal và parent-share; share mặc định cả shop. Validation theo dependency, nhưng giữ ORPHAN là lỗi với metric cần dòng hàng. Không cần hỏi lại người dùng lựa chọn các chi tiết này.

V1 chỉ nhận filter cấp đơn cho cancellation_rate và top_customers sau khi sửa API. Tạm reject product filter ở cả hai metric, kể cả customer revenue, để tránh tự chọn giữa doanh thu sản phẩm và doanh thu toàn khách. Các operation khác dùng public API hiện có trong phạm vi contract đã kiểm chứng.

## Kết quả thực thi mới

- `jsonschema` **4.26.0**, cài riêng cho review; **19 trường hợp schema** được kiểm tra.
- `$schema` và `$id` gốc là chuỗi liên kết Markdown. `check_schema` không bác trong môi trường này, nhưng `validator_for` cảnh báo không tìm thấy metaschema và fallback draft mới nhất. Cần URI thuần; `$id` có thể là URN nội bộ. Không coi URL dự án tự đặt là endpoint đã tồn tại.
- Bản sao chỉ sửa hai URI chặn k=true, k=0, field lạ, thiếu required. Tuy nhiên **k=1.0 được JSON Schema nhận**, trong khi `_rank` cần int đúng kiểu. Chọn canonicalize số nguyên toán học hữu hạn về int trước dispatch; bool và số có phần lẻ bị bác. Áp dụng nhất quán cho n/month/quarter/year/k; vẫn giữ miền giá trị.
- Những case unit trên revenue, expected_type sai, supported nhưng operation=null, ngày 31/02, khoảng ngày đảo ngược đều qua schema cấu trúc. Tôi ghi nhận bạn đã giao phần lớn cho semantic validator; cần triển khai và test riêng, không báo rằng schema một mình đã chặn chúng.
- `product_mentions=[]` và chuỗi chỉ có khoảng trắng đều qua schema. Chọn []→null, trim mention và reject mention rỗng; không tạo product_ids=() rồi trả 0 ngầm. Với share, kiểm tra ít nhất một filter **có hiệu lực sau resolve**.
- Ba test dependency bạn nêu đều chưa pass trên baseline vì constructor/status validation. Đây là test đích hợp lý. Bảng dispatch có hai lời gọi chưa chạy được: cancellation_rate(p,f) và top_customers(...,filters=f) đều TypeError. Cần ghi rõ phụ thuộc patch API.
- Full suite sau review: **219 passed, 1 skipped**. Không chạy lại bộ 409 trong lượt này vì code không đổi; lượt 02 đã chạy mới và đạt 409/409.

## Precision và period cần ghi đúng giới hạn

Không cần đưa boolean trở lại v1. Tuy nhiên prec=28 không bảo đảm mọi tính toán chính xác: với num=`1005*10**30-1`, den=`100000*10**30`, phần trăm half-up hai chữ số cho 1.01 bằng Decimal prec28, còn số hữu tỷ đúng là 1.00. Nhân chéo Decimal cũng chịu context; nếu cần exact comparison phải dùng integer/scaled integer/rational hoặc kiểm tra miền giá trị. Đây là phản chứng cực lớn tổng hợp, chưa phải sai gold train; không đề nghị sửa engine hàng loạt.

`previous_month_same_elapsed` là cần thiết nhưng plan vẫn phải có căn cứ câu hỏi khi chọn cả tháng trước thay mặc định cùng số ngày. `before_period` v1 chỉ dùng cho Tết, vì helper hiện kiểm tra điều khoản trước Tết; không suy rộng sang mọi kỳ.

## Yêu cầu lượt 04: chỉ rà những việc phục vụ patch tiếp theo

1. Xác nhận hoặc phản biện contract v1 đã thu hẹp trên. Đưa checklist các bước normalize → structural validation → semantic validation → resolve → capability → dispatch; nếu normalize cần đọc kiểu dữ liệu trước thì ghi rõ. Không ép chuỗi "1" thành số hoặc bool thành int.
2. Đề xuất patch nhỏ cho `SalesMetrics`: validate dependency đúng lúc; thêm order filters cho cancellation_rate/top_customers; sửa require của share. Giữ thứ tự tham số cũ của top_customers, không đổi Answer. Nêu mỗi thay đổi cần test gì để không làm mất validation liên quan.
3. Đưa các case tương tác còn thiếu: lỗi trạng thái ở kênh đã loại/cùng kênh/kênh chưa biết, catalog hỏng cho count so với top, ORPHAN cho count so với revenue, k=1.0/bool, ngày không tồn tại, unresolved mention, share với filter rỗng sau normalize. Có thể cung cấp diff hoặc code tự chứa, nhưng đánh dấu chưa chạy nếu chưa có môi trường.

Không cần lặp lại thiết kế parent-share v1.1, chọn model hoặc gán PA cho NLU chưa triển khai. Public Answer unanswerable chỉ được giữ sau khi thực thể/capability đã được kiểm tra; không dùng việc bắt `_Unavailable` làm chứng cứ tự động mọi câu không trả lời được.

Hãy xuất **file `GEMINI_RESPONSE_04.md`**, UTF-8, chứa toàn bộ phản hồi. Không thêm `[cite: n]` không truy xuất được; dẫn tên file/mục hoặc permalink thật. Nếu không tạo được file đính kèm, xuất toàn bộ nội dung trong một khối code bao bằng bốn dấu backtick, nhãn markdown; code bên trong dùng ba dấu backtick. Đầu file ghi vòng 001, lượt 04, ngày, tài liệu đã đọc và trạng thái chưa/chạy kiểm chứng.
