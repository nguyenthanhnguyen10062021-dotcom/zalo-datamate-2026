# Vòng 002 — Capability, verification và mức sẵn sàng đi tiếp

- Revision source: `d99cac2`, nhánh VuongNguyen; không thay snapshot vòng001.
- [Yêu cầu phản biện](REVIEW_REQUEST.md): năm câu hỏi và output contract.
- [Gói tự chứa để đính kèm](GEMINI_HANDOFF.md): source từ Git revision trên, fingerprints, tests tổng hợp và số liệu aggregate; không BTC rows/questions/answers/cache/secrets.
- [Prompt mở cuộc trao đổi](GEMINI_START_PROMPT.md): copy nguyên nội dung sau khi đính kèm handoff.

Mở một cuộc trò chuyện mới trên Gemini, upload GEMINI_HANDOFF.md và gửi prompt. Sau khi nhận file GEMINI_RESPONSE_01.md, lưu nguyên file vào thư mục vòng này và yêu cầu Codex kiểm chứng. Chưa có phản hồi hoặc xác nhận gửi Gemini trong hồ sơ này; transfer qua file do người dùng thực hiện.

Handoff được tạo từ Git objects, không từ reports hoặc đường dẫn dữ liệu local. Trạng thái dirty lúc snapshot: sạch ngay sau commit d99cac2; file packet/README routing sau đó nằm trong commit tài liệu riêng. Fingerprints trong handoff là bytes blob Git, có thể khác bytes working tree do CRLF. Không nhầm SHA256 payload artifact audit local với hash file nguồn. Các script nguồn có thể chứa string tên `answers.jsonl` để đọc local khi chạy verifier; gói không chứa nội dung file answers.

Handoff chứa 37 file, 268798 bytes trước chuyển đổi newline của Git; SHA256 bản UTF-8/LF: `3fe2d836f82e52b447f7e40ab489c8543abc04ab7aee99c82df582dd5f52e9fd`. Full kiểm trước bàn giao source: 487 passed/2 local_data deselected; bare 488 passed/1 skip helper cũ. Không chạy lại gold để đóng gói. Handoff không bao gồm loader hoặc artifact annotation từng câu, vì vậy yêu cầu Gemini nêu rõ phần không thể kiểm chứng từ gói và dùng synthetic counterexamples.
