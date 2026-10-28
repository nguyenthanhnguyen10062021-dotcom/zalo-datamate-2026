# Harness Engineering cho DataMate

Ngày: 2026-10-29 (Asia/Saigon). Phạm vi: triển khai harness phát triển mà người dùng yêu cầu; không triển khai executor/NLU.

## Mục tiêu và hiện trạng

Giúp agent mới tìm đúng source, giữ ranh giới kiến trúc, kiểm chứng thay đổi và bàn giao qua nhiều phiên. Baseline chạy mới: Python 3.14.10, 258 passed, 1 skipped; nhánh VuongNguyen, worktree sạch trước thay đổi. Repo có loader, business, evaluator, tài liệu trạng thái và lịch sử Gemini; chưa có AGENTS.md hoặc CI.

## Các cách tiếp cận

1. Chỉ thêm hướng dẫn: ít bảo trì nhưng không ngăn được vi phạm kiến trúc hoặc kết luận sai về test.
2. Hướng dẫn ngắn + kiểm tra stdlib + CI + task record: tận dụng code/test hiện có; đây là lựa chọn triển khai của Codex theo phạm vi người dùng giao.
3. Agent runner riêng, memory service, tự review/merge: tăng chi phí bảo trì; chưa có bằng chứng cần thiết ở repo này.

## Thiết kế

- Root AGENTS.md là bản đồ ngắn; hướng dẫn loader/business/evaluate/ai_collaboration chỉ bổ sung luật cục bộ. Agent ở root phải đọc file cục bộ trước khi sửa vì không giả định client tự nạp mọi file con.
- docs/README.md định tuyến tới kiến trúc, API, validation, PROGRESS và hồ sơ lịch sử. Giữ PROGRESS là trạng thái dự án duy nhất; task record chỉ chứa phạm vi và bằng chứng của tác vụ dài.
- scripts/harness.py dùng stdlib, Python >=3.10, chạy từ mọi cwd với interpreter hiện hành. doctor báo môi trường; check mặc định full, có fast/full/data.
- fast kiểm tra file được Git theo dõi và file mới không bị ignore; không duyệt dataset/venv. Chặn tracking dữ liệu/môi trường, import ngược tầng, import mạng tại runtime hiện có, gold filename trong loader/business, dependency ngoài stdlib của evaluator; kiểm tra link local của tài liệu hiện hành và ngân sách AGENTS (root 6000 bytes, cục bộ 3000 bytes); git diff --check cho staged và unstaged.
- full chạy fast + pytest tests/ evaluate/ loại marker local_data. data chạy full + local_data + verifier hiện có; yêu cầu đầu vào local, so được ít nhất một câu, tất cả khớp gold, không lỗi.
- CI Ubuntu/Windows, Python 3.14, requirements hiện có, chạy cùng profile full. CI không tải dữ liệu BTC và không gọi model/API.
- Theo steering người dùng: tham khảo Trail-Code revision 19865ff4274dc77d977b5519c920dc71e1b54aa3. Thêm map/context lấy signatures và reverse import closure từ working-tree AST mỗi lần chạy; output có limit/total. docs/context-index.json định tuyến quyết định theo touches/read/summary và được kiểm tra đường dẫn bằng chứng. Không cài package Trail hoặc hook/global config; đây là thiết kế độc lập theo các pattern đã nghiên cứu.
- Mọi lỗi có file/lý do/cách xử lý; mã thoát khác 0 khi kiểm tra thất bại. Harness không tự cài package, xóa file, commit, push hoặc thay cấu hình agent cá nhân.

## Ranh giới và giới hạn

Không di chuyển/xóa dữ liệu hay snapshot Gemini; không đổi phép tính nghiệp vụ, evaluator, dependency production hoặc con số PA. Static AST checks là tripwire cho import/literal, không phải sandbox hoặc chứng minh offline tuyệt đối; dynamic import/subprocess và logic theo ID vẫn cần review. Chưa có end-to-end smoke từ câu tự nhiên vì executor/NLU chưa có.

## Tiêu chí hoàn tất

Tài liệu có đường đi rõ; fast/full/data và doctor chạy thực tế; kiểm thử guard bằng fixture tổng hợp và Git repo tạm (vi phạm import, gold, data tracking, link hỏng, thiếu dữ liệu, báo cáo rỗng); CI dùng cùng lệnh local; kết quả và giới hạn cập nhật vào PROGRESS/validation. Không tăng hạ tầng agent ngoài phạm vi này.
