# Harness Engineering cho workspace

Harness là môi trường giúp coding agent tìm đúng ngữ cảnh, thực hiện thay đổi trong ranh giới rõ, nhận phản hồi từ kiểm tra và để lại bằng chứng cho phiên sau. Bản này phục vụ phát triển DataMate; pipeline nộp thi vẫn chạy offline theo [ràng buộc dự án](../README.md).

## Nghiên cứu và lựa chọn

Nghiên cứu ngày 2026-10-29 qua TinyFish và GitHub connector; đọc nguồn chính thay vì chỉ dựa vào snippet. Các áp dụng bên dưới là lựa chọn của Codex cho repo này, không phải tuyên bố rằng mọi cơ chế trong nguồn đã được cài đặt.

| Nguồn | Nguyên tắc áp dụng |
|---|---|
| [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/) | Hướng dẫn ngắn làm bản đồ, tri thức nằm trong repo, invariant quan trọng có kiểm tra tự động và lỗi đủ rõ để sửa |
| [OpenAI Docs: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) và [best practices](https://learn.chatgpt.com/guides/best-practices) | Dùng hướng dẫn theo scope; root trỏ tới tài liệu chuyên đề. Codex nạp chuỗi hướng dẫn theo đường tới cwd, không tự đọc mọi file con |
| [Anthropic: Effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | Chỉ lấy ngữ cảnh cần cho tác vụ, giữ định danh/đường dẫn để truy xuất sâu khi cần |
| [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) | Tiến độ bền vững, làm từng bước có thể kiểm chứng, ghi kết quả và điểm tiếp tục |
| [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents) | Bắt đầu từ cơ chế đơn giản; thêm orchestration khi có lợi ích đo được |

## Tham khảo Trail-Code theo yêu cầu người dùng

Đã đọc README và mã nguồn [Trail-Code tại revision 19865ff](https://github.com/trailhq/Trail-Code/tree/19865ff4274dc77d977b5519c920dc71e1b54aa3). Repo này bổ sung graph và learnings cho coding agent. Học các mẫu thiết kế; không sao chép code và không cài Trail vào máy trong tác vụ này.

| Mẫu từ Trail | Áp dụng tại DataMate | Phạm vi thực tế |
|---|---|---|
| [Refresh trước truy vấn](https://github.com/trailhq/Trail-Code/blob/19865ff4274dc77d977b5519c920dc71e1b54aa3/src/graph/refresh.ts) | map/context parse working-tree bằng AST mỗi lần chạy | Gồm thay đổi chưa commit; không có cache cũ hoặc file graph sinh thêm |
| [Điều hướng/API theo tác vụ](https://github.com/trailhq/Trail-Code/blob/19865ff4274dc77d977b5519c920dc71e1b54aa3/src/hosts/instructions.ts) | map cho định hướng; context cho signatures, dòng source và module phụ thuộc | Chỉ Python/import tĩnh; không có ranked semantic search, call graph hay MCP riêng |
| [Traversal phụ thuộc](https://github.com/trailhq/Trail-Code/blob/19865ff4274dc77d977b5519c920dc71e1b54aa3/src/graph/traverse.ts) | Reverse import closure, loại vòng lặp, giới hạn output và báo tổng số | Gợi ý phạm vi review/test; không được dùng để bỏ full suite |
| [Learnings theo file](https://github.com/trailhq/Trail-Code/blob/19865ff4274dc77d977b5519c920dc71e1b54aa3/src/notes/notes.ts) | context-index chứa touches, summary và link bằng chứng; trả đúng mục liên quan | Ledger vẫn ở DECISIONS; không tự khai thác lịch sử chat hoặc tạo “trí nhớ” từ mọi phiên |
| [Output ổn định](https://github.com/trailhq/Trail-Code/blob/19865ff4274dc77d977b5519c920dc71e1b54aa3/src/graph/write.ts) | JSON theo thứ tự ổn định; không timestamp/cache sinh lại | Không cần thêm storage/daemon ở quy mô hiện tại |

README Trail công bố benchmark trên workload của họ; chưa có phép đo cho DataMate, nên không hứa giảm token/thời gian theo các tỷ lệ đó. Nếu về sau cần call graph đa ngôn ngữ/MCP, có thể đánh giá Trail thật bằng trial có đo lường. Đọc trước [host init](https://github.com/trailhq/Trail-Code/blob/19865ff4274dc77d977b5519c920dc71e1b54aa3/src/hosts/init.ts) và [telemetry gate](https://github.com/trailhq/Trail-Code/blob/19865ff4274dc77d977b5519c920dc71e1b54aa3/src/telemetry/gate.ts): setup có thể ghi cấu hình user và bản published có telemetry. Tham khảo repo không đồng nghĩa đã ủy quyền cài tool hoặc hook toàn máy.

## Dùng hằng ngày

Sau khi cài requirements bằng interpreter của venv (xem [README](../README.md)):

```powershell
.\.venv\Scripts\python.exe scripts/harness.py doctor
.\.venv\Scripts\python.exe scripts/harness.py map --limit 30
.\.venv\Scripts\python.exe scripts/harness.py context business/sales.py --limit 30
.\.venv\Scripts\python.exe scripts/harness.py check --profile fast
.\.venv\Scripts\python.exe scripts/harness.py check
# Khi cần đối chiếu train local và đã có cache phù hợp:
.\.venv\Scripts\python.exe scripts/harness.py check --profile data
```

Linux/macOS: dùng `.venv/bin/python` hoặc `python` sau khi activate. Có thể gọi script bằng đường dẫn tuyệt đối từ cwd khác; root luôn được xác định từ vị trí script. map/context chỉ đọc source theo danh sách Git (tracked + untracked không bị ignore), bỏ dataset/env, không gọi API/model. context nhận đường dẫn tính từ gốc repo. Output mặc định tối đa 30 mục mỗi phần, có trường total; tăng limit tới 200 hoặc dùng `rg` để tìm đầy đủ. Graph chỉ thấy import tĩnh; dynamic import, dispatch, monkey patch và data dependency cần review source.

1. Đầu tác vụ: đọc AGENTS, PROGRESS, map/context cho file liên quan; nêu hành vi cần đạt.
2. Đọc source span và đúng tài liệu mà context trả về; kiểm tra scoped AGENTS trước khi sửa.
3. Thay đổi nhỏ kèm test có ý nghĩa; chạy targeted tests trong lúc làm.
4. Kết thúc: full; dùng data cho thay đổi tính đúng loader/business khi đủ input; review diff và ghi lệnh/kết quả/giới hạn.
5. Việc qua nhiều phiên: dùng [task template](tasks/TEMPLATE.md) hoặc plan đang có, ghi next action. Thêm quyết định bền vững vào [ledger](../ai_collaboration/DECISIONS.md) và cập nhật routing khi file liên quan đổi.

## Kiểm tra nào chứng minh điều gì

| Mức | Kiểm tra | Không chứng minh |
|---|---|---|
| doctor | Python, Git, versions đúng pin; dữ liệu local tùy chọn | Hành vi nghiệp vụ đúng |
| fast | Hygiene Git, syntax AST, dependency/offline import, gold literal, link local của docs hiện hành, budget AGENTS, whitespace staged/unstaged | Không có rò rỉ bí mật/động qua mọi cách; đúng luật nghiệp vụ |
| full (mặc định/CI) | fast + test synthetic, loại marker local_data | Đúng trên dữ liệu thực, PA toàn train, pipeline NLU đã có |
| data | full + local_data + verify_business; reject compared=0, mismatch hoặc errors | Cả 10 API hoặc toàn bộ 3000 câu/NLU đúng |

Data profile cần train/rulebook.md, questions.jsonl, answers.jsonl và cache có don_hang.parquet. Với thay đổi loader, rebuild cache phù hợp trước khi dùng; verifier đọc cache nên không tự chứng minh loader mới đúng. Báo cáo chi tiết ở `reports/harness/business_verification.json` và `.md` được ignore. Luôn công bố mẫu số so sánh và lý do skip; helper self-score real-file cũ có skip đã ghi trong [validation](validation.md).

fast đọc file source/docs trong inventory Git, không quét đệ quy venv/dataset. File bị add -f vào train/cache vẫn bị phát hiện. Link check chỉ áp dụng AGENTS, README hiện hành và docs hiện hành; không sửa lịch sử rounds hay thiết kế cũ vì các link snapshot. Root AGENTS tối đa 6000 bytes, scoped 3000 bytes; vượt thì tách chi tiết ra tài liệu có link.

AST guard bắt import mạng đã liệt kê tại loader/business/queryplan/evaluate và gold filename literal tại loader/business/queryplan. Guard cấm queryplan import loader/dev tools và cấm loader/business import ngược queryplan. Đây là kiểm tra tĩnh hỗ trợ review, không phải sandbox mạng hoặc bộ chứng minh chống leakage. Quy tắc theo ID và nguồn gốc dữ liệu vẫn do test/review kiểm chứng. Giữ production dependency hiện có; chưa thêm linter/formatter/typechecker toàn repo để tránh thay đổi ngoài phạm vi.

## CI và bảo trì

[Workflow](../.github/workflows/ci.yml) chạy cùng full profile trên Ubuntu/Windows, Python 3.14, không tải dữ liệu BTC. Version action tham khảo README chính thức của [checkout](https://github.com/actions/checkout) và [setup-python](https://github.com/actions/setup-python). Kiểm tra kết quả hosted sau khi workflow được push; chạy local không chứng minh runner hosted đã thành công.

Khi agent lặp lại một lỗi, ưu tiên biến phản chứng thành test/guard có thông báo sửa cụ thể; chỉ thêm hướng dẫn nếu cần ngữ cảnh con người. Giữ PROGRESS là trạng thái dự án, context-index chỉ là chỉ mục. Không thêm bot tự merge, memory server, swarm reviewer hoặc tự gửi Gemini khi chưa có nhu cầu thực tế.
