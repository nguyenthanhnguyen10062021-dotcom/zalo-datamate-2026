# Vòng 002 — Capability, verification và mức sẵn sàng đi tiếp

**Sau vòng review:** người dùng giao triển khai; [task intent/span/preflight/calendar/grammar](../../../docs/tasks/2026-10-29-selector-calendar-implementation.md) đã hoàn tất trong working tree, v4 396/396, chưa commit/push. Handoff và các nhận định “chưa sửa” bên dưới là snapshot trước triển khai, chưa có Gemini review code mới.

- Revision source: `d99cac2`, nhánh VuongNguyen; không thay snapshot vòng001.
- [Yêu cầu phản biện](REVIEW_REQUEST.md): năm câu hỏi và output contract.
- [Gói tự chứa để đính kèm](GEMINI_HANDOFF.md): source từ Git revision trên, fingerprints, tests tổng hợp và số liệu aggregate; không BTC rows/questions/answers/cache/secrets.
- [Prompt mở cuộc trao đổi](GEMINI_START_PROMPT.md): copy nguyên nội dung sau khi đính kèm handoff.

Người dùng đính chính: bản10298 bytes cũ là **Flash**; bản57250 bytes mới là **Argon, đối tượng phản biện chính**. Giữ hai bản riêng, không ghi đè:

- [Argon response01 đầy đủ](GEMINI_ARGON_RESPONSE_01.md), [review Codex01](CODEX_ARGON_REVIEW_01.md), [thư phản biện01](CODEX_REPLY_TO_ARGON_01.md). Header file Argon tự ghi Flash trái với xác nhận người dùng; giữ bytes và ghi attribution theo người dùng, không suy tên model kỹ thuật.
- **Mới nhất:** [Argon response02](GEMINI_ARGON_RESPONSE_02.md), [review Codex02](CODEX_ARGON_REVIEW_02.md), [thư chốt kỹ thuật02](CODEX_REPLY_TO_ARGON_02.md). Argon rút I2/I4 là blocker, điều chỉnh phương pháp; còn guard fixed-vs-relative quá rộng được Codex phản chứng. Đủ căn cứ chuẩn bị task intent/span/preflight trước, spec neo kỳ sau; chưa áp runtime/grammar và không cần kéo dài review nếu không có phản chứng mới.
- [Flash response01 bị cắt](GEMINI_RESPONSE_01.md), [review cũ](CODEX_REVIEW_01.md), [thư xin phần thiếu cũ](CODEX_REPLY_TO_GEMINI_01.md) là lịch sử nhánh phụ; không dùng thư xin phần thiếu cho bản Argon đầy đủ.

Transfer vẫn qua file do người dùng thực hiện, không có tích hợp gửi Gemini tự động. Runtime/selector chưa sửa sau nhận hai phản hồi.

Handoff được tạo từ Git objects, không từ reports hoặc đường dẫn dữ liệu local. Trạng thái dirty lúc snapshot: sạch ngay sau commit d99cac2; file packet/README routing sau đó nằm trong commit tài liệu riêng. Fingerprints trong handoff là bytes blob Git, có thể khác bytes working tree do CRLF. Không nhầm SHA256 payload artifact audit local với hash file nguồn. Các script nguồn có thể chứa string tên `answers.jsonl` để đọc local khi chạy verifier; gói không chứa nội dung file answers.

Handoff chứa 37 file, 268798 bytes trước chuyển đổi newline của Git; SHA256 bản UTF-8/LF: `3fe2d836f82e52b447f7e40ab489c8543abc04ab7aee99c82df582dd5f52e9fd`. Full kiểm trước bàn giao source: 487 passed/2 local_data deselected; bare 488 passed/1 skip helper cũ. Không chạy lại gold để đóng gói. Handoff không bao gồm loader hoặc artifact annotation từng câu, vì vậy yêu cầu Gemini nêu rõ phần không thể kiểm chứng từ gói và dùng synthetic counterexamples.
