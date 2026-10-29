# Vòng003 — Khởi động Codex / Gemini Web / Antigravity

- Ngày: 2026-10-29, Asia/Saigon.
- Trạng thái hiện hành: **đang lập plan NLU/Modal, chờ phản biện đúng bản plan của phiên Codex này**. Các tuyên bố đồng thuận C002/C003 và thư Codex05/06/07 cần đọc cùng đính chính attribution; chúng chưa chốt thay plan hiện hành.
- Người tham gia: người dùng, Codex, Antigravity (Gemini 3.8 Flash High). Gemini Web có thể đóng góp độc lập khi người dùng gửi file.
- Phạm vi hiện tại: lập kế hoạch/thảo luận, chưa triển khai NLU. Hai sửa dữ liệu đã hoàn tất theo task riêng. Người dùng cho phép Modal profile `vuonghungnguyen07`, upload dữ liệu vào tài khoản đó, tối đa **25 USD** cho đợt thử đầu tiên (thay mức20USD); chưa có run tính phí trong tác vụ plan.

**Đọc hiện tại:** [plan thực Codex06 P0–P9](messages/CODEX_TO_ANTIGRAVITY_06_NLU_MODAL_PLAN.md) và [yêu cầu đối chiếu Codex08](messages/CODEX_TO_ANTIGRAVITY_08_READ_ACTUAL_PLAN.md). Đã nhận Antigravity03–05; chưa có phản hồi xác nhận đúng plan có hậu tố `NLU_MODAL_PLAN` khi ghi cập nhật này. Mỗi bên chỉ ghi file của mình; không tự viết thay Codex hoặc suy đồng thuận từ tên file.


## File cần dùng

| File | Cách dùng |
|---|---|
| [BRIEF](BRIEF.md) | Cùng đề bài và giới hạn cho cả ba AI |
| [SOURCE_PACKET](SOURCE_PACKET.md) | Đính kèm cho Gemini; Antigravity dùng cùng snapshot và đối chiếu repo |
| [Prompt Gemini](GEMINI_START_PROMPT.md) | Copy vào chat Gemini mới sau khi đính kèm hai file trên |
| [Prompt Antigravity](ANTIGRAVITY_START_PROMPT.md) | Copy vào phiên Antigravity mới ở repo root |
| [Lập trường Codex01](messages/CODEX_POSITION_01.md) | Quan điểm ban đầu để hai bên phản biện, chưa phải quyết định |
| [Quy ước messages](messages/README.md) | Đường dẫn nhận phản hồi, cách đánh số và attribution |

BRIEF đã chứa lập trường Codex để hai bên nhận cùng bối cảnh. SOURCE_PACKET có commit nền, danh sách file dirty tại thời điểm đóng gói, fingerprint và phạm vi nguồn. Nó không tự cập nhật theo repo; tạo revision mới khi cần bổ sung hoặc thay source, không ghi đè bản đã gửi.

## Lượt đầu và tiêu chí kết thúc

1. Người dùng chuyển cùng BRIEF/SOURCE_PACKET sang hai phiên mới, kèm prompt tương ứng.
2. Nhận các phản hồi thật vào `messages/`; Antigravity có repo có thể ghi đúng một file phản hồi của mình.
3. Codex kiểm chứng nhận định quan trọng bằng source/test tổng hợp, ghi `CODEX_REVIEW_01.md` và thư phản biện theo từng người nhận nếu cần.
4. Khi đủ bằng chứng, cập nhật DECISIONS với ai đề xuất, ai quyết định, các ý kiến khác và giới hạn. Nếu triển khai được giao sau đó, dùng task contract riêng và ghi kết quả thực chạy.

Vòng này kết thúc khi có bước tiếp cụ thể, acceptance và các bất đồng còn mở được ghi rõ. Không bắt buộc cả ba AI đồng ý. Chưa tạo phản hồi hay tổng kết giả khi chưa nhận nội dung từ hai bên.

## Kiểm chứng khi chuẩn bị vòng

- `.\.venv\Scripts\python.exe scripts/harness.py map`: hoàn tất định hướng source.
- `.\.venv\Scripts\python.exe scripts/harness.py check`: PASS full, **545 passed, 2 local_data deselected**; fast kiểm134file ở lượt sau đóng gói.
- Kiểm bổ sung: liên kết trong7tài liệu mới hợp lệ;18fingerprint UTF-8/LF và nội dung source nhúng khớp working tree; vòng001/002 cùng ba snapshot gốc không thay đổi; không sửa Python hoặc tạo phản hồi giả.
- Không chạy data profile vì chỉ tổ chức tài liệu/packet, không đổi loading/business correctness. Chưa gửi Gemini/Antigravity, chưa commit/push.
