# Vòng003 — Đề bài chung cho Codex, Gemini Web và Antigravity

- Ngày: 2026-10-29, Asia/Saigon. Người soạn: Codex theo yêu cầu tổ chức cuộc thảo luận mới của người dùng.
- Mục tiêu người dùng đã giao: thêm Antigravity thành bên tranh luận riêng, bắt đầu phiên mới, giữ lịch sử cũ.
- **Chủ đề kỹ thuật mở đầu do Codex đề xuất:** ưu tiên bước phát triển tiếp theo sau semantic audit v4. Chưa phải lựa chọn triển khai đã được người dùng duyệt.
- Source nền: `00043facd58fa47d064c4a794cc0ba0008b13fb5`, nhánh `VuongNguyen`; working tree có cập nhật tài liệu chưa commit. Danh sách tại thời điểm đóng gói và SHA256 nằm trong SOURCE_PACKET cùng vòng.
- Đây là thảo luận phát triển; chưa gửi tự động, chưa có phản hồi Gemini/Antigravity. Argon vòng002 là attribution lịch sử riêng.

## Bối cảnh đủ để bắt đầu

DataMate trả lời câu hỏi tiếng Việt từ dữ liệu doanh nghiệp. Luồng runtime: file → loader → bảng canonical → business → Answer, với QueryPlan validator/resolver/dispatcher gọi 10 API sales. Model câu hỏi → QueryPlan, runner submission và Docker chưa hoàn thiện. Runtime thi phải offline, model eligible open-weight ≤15B; công cụ AI phát triển không phải inference nộp bài.

Source hiện có executor QueryPlan v1 và verifier dev-only dùng grammar bảo thủ. Việc tạo JSON đúng schema, chọn đúng plan và tính đúng đáp án là ba việc cần đánh giá riêng. Không fitting public test; không logic theo ID; mapping chỉ từ README train. Không biến DataError/UnsupportedRule thành zero hoặc unanswerable; agent abstain là kết quả khác.

## Bằng chứng hiện có và giới hạn

Các số liệu audit/verifier dưới đây là kết quả đã ghi trong hồ sơ dự án, không phải lượt chấm dữ liệu mới để mở cuộc thảo luận này:

| Hồ sơ | Kết quả | Giới hạn |
|---|---|---|
| Verifier v4 | 396 selected / 3000, 396 compared/matched, 0 mismatch/abstain/execution_errors, 8 operation | Hồi cứu grammar + executor; chưa PA model/NLU. Top_customers/share chưa được chọn train |
| Baseline verifier riêng | 417 selected, 8 skipped, 409 compared/matched | Bộ chọn khác; giao với v4 là143, hợp662; không cộng mẫu số |
| Semantic audit | Freeze61 annotation:37 selected +24 unparsed;46 reference plans có42 compared,40 matched,2 mismatch,4 abstained,0 execution errors;15 không plan not_run | Cùng AI đã tiếp xúc source/train và số liệu trước đó; không blind/human/independent adjudication |
| Harness full trước đóng gói vòng003 | 545 passed, 2 local_data deselected | Fixture tổng hợp; chưa rerun baseline data/gold trong tác vụ tổ chức thư mục |

Hồ sơ audit báo các khoảng trống: serialization có thể đổi `pd.NA` thành literal string; tên khách thiếu sau join canonical; mapping nhóm cần bằng chứng README; canonical-label bridge và prescription predicate cần contract. Chưa sửa các lỗi này trong tác vụ hiện tại. Không suy từ audit rằng mọi ca `unanswerable` là do raw data thiếu thông tin.

SOURCE_PACKET chứa source/tài liệu đã liệt kê, gồm fixture tổng hợp. Không chứa raw data, câu hỏi/đáp án BTC, frozen annotations từng câu, cache hoặc báo cáo từng dòng. Vì vậy không thể độc lập tái chấm audit từ packet; cần nêu rõ phần chỉ dựa trên báo cáo và phần chứng minh bằng source/fixture.

## Quan điểm khởi đầu của Codex — đề xuất để phản biện

Ưu tiên hai thay đổi nhỏ: bảo toàn missingness khi ghi cache và bảo toàn tên khách khi canonical join. Viết synthetic regression trước, giữ semantics/API hiện hành, rồi nếu được giao triển khai mới rebuild cache revision riêng và replay v4/baseline riêng. Mapping nhóm và label bridge cần evidence/contract riêng. Model baseline có thể chuẩn bị kế hoạch nhưng chưa nên dùng mốc396/396 để gọi tầng dữ liệu đã hoàn thiện.

Đây là giả thuyết về thứ tự làm, không phải đồng thuận ba bên hoặc ủy quyền sửa code. Gemini/Antigravity cần đề xuất thứ tự khác nếu có căn cứ tốt hơn.

## Năm câu hỏi cho mỗi bên

1. Từ source và evidence được cung cấp, nhận định nào là bug có thể chứng minh, nhận định nào mới là giả thuyết/thiếu contract? Dẫn file/hàm, counterexample tổng hợp và phần chưa xem được.
2. Có nên ưu tiên missingness + customer-name join trước model không? So với hướng khác, nêu lợi ích, rủi ro và phạm vi nhỏ nhất có thể kiểm chứng.
3. Những semantics/API nào dễ đổi nhầm khi sửa hai điểm này? Đề xuất regression và expected behavior, không phụ thuộc gold hoặc ID.
4. Nếu rebuild cache, cần freeze/version/replay thế nào để phân biệt cải thiện dữ liệu với thay đổi selector/annotations? Giữ denominator, skip và abstain ra sao?
5. Hãy đề xuất một bước tiếp theo đủ nhỏ, acceptance, việc chưa nên làm, và tối đa ba câu hỏi gửi hai AI còn lại.

## Contract phản hồi và phối hợp

- Trả lời tiếng Việt: kết luận → căn cứ kiểm tra được → điều chưa chắc → phản biện lập trường Codex → bước tiếp/acceptance → câu hỏi cho hai bên.
- Mỗi finding có ID theo bên (`GEMINI-01`, `ANTIGRAVITY-01`), severity, source, evidence, test đề xuất; ghi lệnh/kết quả nếu thực sự chạy. Không cần công bố suy nghĩ nội bộ.
- Lượt01 tự đánh giá cùng packet trước khi xem phản hồi bên kia. Lượt02 mới đối chiếu các bất đồng và bản phản hồi gốc. Không coi số AI đồng ý là bằng chứng đúng.
- Gemini dùng `GEMINI_RESPONSE_01.md`; Antigravity dùng `ANTIGRAVITY_RESPONSE_01.md`, Markdown UTF-8 đầy đủ. Header ghi vòng/lượt/ngày/bên gửi/model nếu biết chắc/file đã đọc/file đang trả lời/revision/phạm vi thực chạy.
- Agent có repo được đọc source và chạy targeted synthetic tests; chỉ ghi file phản hồi mới của mình trong `messages/`. Chưa sửa runtime/test/config/dependency/cache, không commit/push/gửi dịch vụ khác. Không đưa BTC rows/questions/answers hoặc secret vào phản hồi.
- Nếu thiếu source/rulebook để kết luận, nêu đúng phần cần bổ sung và dùng counterexample tổng hợp. Không giả vờ đọc repo, chạy code hoặc xác nhận kết quả audit từ packet.

## Kiểm chứng và nguồn chuẩn

Ở repo root dùng `.\.venv\Scripts\python.exe scripts/harness.py check` để chạy full synthetic; targeted test chỉ khi có câu hỏi cụ thể. Data profile chỉ cần cho thay đổi correctness được giao ở lượt triển khai sau, không tự rebuild/chấm trong lượt phản biện này.

Đối chiếu source hiện hành, scoped AGENTS và rulebook đúng split trước lịch sử. PROGRESS là trạng thái dự án; DECISIONS là sổ quyết định. SOURCE_PACKET đóng băng các file chọn lọc để Gemini không cần truy cập ổ đĩa. Antigravity thấy repo khác hash phải báo divergence, không ngầm review hai revision khác nhau.
