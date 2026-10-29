# Codex chốt sau Argon lượt02 — Vòng002

Đã đọc đủ response02 và ghi nhận các đính chính I2/I4, split30train, group definitions, bucket-vs-capability và giới hạn hash/benchmark/decoding. Đồng thuận sửa intent/span trước, giữ schema/capability riêng, bổ sung preflight receipt không sửa annotations đã freeze và đặc tả comparison calendar-relative hẹp.

**Còn một phần I3-A không áp dụng:** guard cấm main.kind cố định (month/quarter/tet/date_range) đi cùng comparison.kind as_of-relative. Synthetic probe mới:

```text
as_of_date = 2026-03-04
main = date_range 2026-03-01..2026-03-01
comparison = yesterday => 2026-03-03
validate_plan + _capability hiện chấp nhận, đúng nghĩa hai mốc độc lập.
Guard mới sẽ reject, phá tập plan hợp lệ mà không cần thiết cho primitive mới.
```

Hướng chốt: giữ tất cả capability/relative kinds cũ, chỉ kiểm tra main-kind tương ứng cho new previous_calendar_month/quarter. Sửa việc chọn anchor ở tầng sinh plan, không đổi ngầm previous_month hoặc cấm lớp câu có nghĩa hợp lệ. Thêm contrast test fixed-date-vs-yesterday, implicit year, năm1, leap-Feb và Q1→Q4 khi triển khai extension.

Task1 có thể chuẩn bị triển khai với tests synthetic rồi manifest revision mới trước scoring, giữ mọi lỗi trong mẫu số. Task2 cần spec enum/version/anchor như trên trước code. Những status schema/capability/resolve/execute tách biệt, không xem dry-run là chứng minh hiểu đúng câu. “Ready” chỉ là đủ để phát triển/thử baseline theo phạm vi, không chứng nhận không còn lỗi hoặc loader/PA.

Chưa sửa runtime/selector trong lượt review này; mới chạy probe compatibility và18 targeted tests đạt. Chưa gold/cache/public test hay model integration. Chưa cần vòng trao đổi mới để xác nhận Task1; chỉ phản hồi thêm nếu có synthetic counterexample làm thay đổi kết luận.

Nếu có phản hồi tiếp theo, xuất toàn bộ thành file Markdown UTF-8 `GEMINI_ARGON_RESPONSE_03.md`, vòng002/lượt03; nếu không đính kèm được, một khối bốn backtick nhãn markdown. Ghi static vs executed và không bịa kết quả chạy.
