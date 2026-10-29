# Trao đổi giữa người dùng Codex và Gemini

Thư mục này dùng để đưa bối cảnh từ repo sang Gemini web, nhận phản biện rồi đưa về Codex kiểm chứng và triển khai. Mỗi vòng tập trung vào một vấn đề. Có thể dùng cùng cách này với LLM khác.

**Điểm tiếp tục 2026-10-29:** source inventory/verifier và audit tại `d99cac2`, executor ở `4fd268e`. Sau [Argon lượt02](rounds/002_capability_readiness/README.md), người dùng giao triển khai; [task mới](../docs/tasks/2026-10-29-selector-calendar-implementation.md) đã hoàn tất intent/span/preflight/calendar/grammar trong working tree, v4 đạt396/396, chưa commit/push hoặc LLM. Bản Flash, phản hồi và các snapshot bên dưới giữ nguyên làm lịch sử; handoff d99cac2 không chứa thay đổi mới.

## Cách mở vòng002 trước đây (lịch sử)

1. Mở cuộc trò chuyện mới trên Gemini, đính kèm [GEMINI_HANDOFF vòng002](rounds/002_capability_readiness/GEMINI_HANDOFF.md).
2. Copy và gửi [GEMINI_START_PROMPT vòng002](rounds/002_capability_readiness/GEMINI_START_PROMPT.md). Năm câu hỏi chi tiết nằm đầu handoff và trong [REVIEW_REQUEST](rounds/002_capability_readiness/REVIEW_REQUEST.md).
3. Nhận file response, lưu nguyên vào `rounds/002_capability_readiness/`, rồi giao Codex kiểm chứng. Vòng002 đã nhận Flash/Argon theo routing trên; chưa gửi tự động hoặc có review Gemini đối với code triển khai mới.

## Cách bắt đầu vòng001 trước đây (lịch sử)

Nhánh làm việc: [VuongNguyen trên GitHub](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/VuongNguyen). Bản code nền cho vòng 001: [`1c89252`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/tree/1c89252). Xem [bằng chứng kiểm chứng](../docs/validation.md).

1. Mở cuộc trò chuyện mới trên Gemini web và chọn model bạn muốn dùng.
2. Tải lên **[GEMINI_HANDOFF.md](GEMINI_HANDOFF.md)**. File này chứa bối cảnh, yêu cầu vòng đầu và bản chụp mã nguồn/test liên quan; Gemini không cần truy cập ổ đĩa của bạn.
3. Copy nội dung **[GEMINI_START_PROMPT.md](GEMINI_START_PROMPT.md)** vào tin nhắn rồi gửi.
4. Copy nguyên phản hồi Gemini vào **[rounds/001_business_to_nlu/GEMINI_RESPONSE.md](rounds/001_business_to_nlu/GEMINI_RESPONSE.md)**. Điền model/ngày nếu bạn biết; không cần chỉnh lại toàn bộ cấu trúc phản hồi.
5. Quay lại chat này và nhắn: **“Hãy đọc phản hồi Gemini ở vòng 001, phản biện và đề xuất bước tiếp theo.”**

Codex sẽ kiểm tra đề xuất với code, rulebook và test, ghi kết quả vào `CODEX_REVIEW.md`. Nếu cần hỏi tiếp, Codex chuẩn bị yêu cầu vòng kế tiếp để bạn gửi lại Gemini. Nếu bạn yêu cầu triển khai, Codex thực hiện phần đã được giao và ghi bằng chứng kiểm chứng.

Đây là trao đổi qua file do bạn chuyển tiếp. Việc tạo thư mục không kết nối tài khoản Gemini hoặc tự gửi nội dung lên web.

## Các file chính

| File | Mục đích |
|---|---|
| `GEMINI_HANDOFF.md` | File sẵn để tải lên Gemini, tự chứa cả bối cảnh và source snapshot |
| `GEMINI_START_PROMPT.md` | Tin nhắn mở đầu để copy vào Gemini |
| `PROJECT_CONTEXT.md` | Bối cảnh chung và giới hạn của repo |
| `DECISIONS.md` | Các quyết định đã có và các vấn đề còn mở |
| `rounds/001_business_to_nlu/` | Vòng đầu: review thư viện nghiệp vụ và hướng nối tầng hiểu câu hỏi |
| `templates/DISCUSSION_REQUEST.md` | Mẫu mở một vấn đề mới |

## Vòng đầu đang hỏi gì

Thư viện nghiệp vụ bán hàng đã có bản đầu. Cần review giới hạn hiện tại và chọn cách xây tầng hiểu câu hỏi gọi thư viện: kế hoạch JSON có kiểm tra, sinh code, hay cách kết hợp. Đây là đề bài thảo luận; chưa chốt triển khai tầng NLU.

**Cập nhật 2026-10-29:** đã nhận phản hồi Gemini và hoàn tất [review của Codex](rounds/001_business_to_nlu/CODEX_REVIEW.md). Để thảo luận tiếp, gửi Gemini [CODEX_REPLY_TO_GEMINI.md](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI.md) kèm [TRAIN_METADATA.md](rounds/001_business_to_nlu/TRAIN_METADATA.md). Có thể đính kèm CODEX_REVIEW.md nếu cần đầy đủ căn cứ. Đây là các file local mới; handoff ngày 2026-10-28 vẫn giữ làm snapshot lịch sử, chưa bao gồm review này.

Đã nhận và kiểm chứng [GEMINI_RESPONSE_02.md](rounds/001_business_to_nlu/GEMINI_RESPONSE_02.md), giữ nguyên nội dung người dùng copy. Kết quả ở [CODEX_REVIEW_02.md](rounds/001_business_to_nlu/CODEX_REVIEW_02.md). Lượt tiếp theo: gửi [CODEX_REPLY_TO_GEMINI_02.md](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI_02.md) cùng review 02, dùng [GEMINI_PROMPT_03.md](rounds/001_business_to_nlu/GEMINI_PROMPT_03.md), nhận file `GEMINI_RESPONSE_03.md`.

**Lượt 03:** đã kiểm chứng [GEMINI_RESPONSE_03.md](rounds/001_business_to_nlu/GEMINI_RESPONSE_03.md). Gửi [CODEX_REPLY_TO_GEMINI_03.md](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI_03.md) cùng [CODEX_REVIEW_03.md](rounds/001_business_to_nlu/CODEX_REVIEW_03.md), dùng [GEMINI_PROMPT_04.md](rounds/001_business_to_nlu/GEMINI_PROMPT_04.md), nhận `GEMINI_RESPONSE_04.md`. Đã thống nhất phạm vi baseline nhỏ; các patch API và executor vẫn chưa triển khai.

**Cập nhật sau lượt 04:** đã kiểm chứng [GEMINI_RESPONSE_04.md](rounds/001_business_to_nlu/GEMINI_RESPONSE_04.md) trên baseline và các bản ứng viên tách biệt. Gói mới gồm [thư Codex](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI_04.md), [review 04](rounds/001_business_to_nlu/CODEX_REVIEW_04.md) và [diff Codex đã sửa](rounds/001_business_to_nlu/CODEX_BUSINESS_PATCH_04.diff); dùng [prompt 05](rounds/001_business_to_nlu/GEMINI_PROMPT_05.md), nhận `GEMINI_RESPONSE_05.md`. Diff chưa áp dụng vào production.

**Trạng thái code mới nhất:** đã áp dụng bản sửa và commit tại [`c567b29`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/commit/c567b29); thêm 39 ca kiểm thử, full suite đạt 258 passed, 1 skipped, verifier đạt 409/409. Xem [hồ sơ triển khai](rounds/001_business_to_nlu/CODEX_IMPLEMENTATION_04.md) để có phạm vi thay đổi. Các gói handoff/review trước đó là snapshot lịch sử; khi trao đổi tiếp cần kèm cập nhật này và source/test tại commit mới.

## Quyền chủ động kiểm chứng và trao đổi

Từ 2026-10-29, người dùng yêu cầu Codex tự động kiểm chứng các đề xuất kỹ thuật của Gemini và coi đây là cuộc trao đổi kỹ thuật giữa hai bên. Khi có phản hồi mới, Codex tự đọc source, chạy thử nghiệm/test phù hợp, phản biện, ghi kết luận và chuẩn bị lượt tiếp theo; không dừng lại hỏi người dùng duyệt từng nhận định hoặc chọn thay chi tiết kỹ thuật. Luôn phân biệt đề xuất, quyết định kỹ thuật và thay đổi đã thực thi. Việc trao đổi hiện vẫn qua file; chưa có cầu nối tự gửi/nhận với Gemini web.

## Yêu cầu Gemini xuất file ở các lượt sau

Theo yêu cầu của người dùng, mỗi prompt tiếp theo cần yêu cầu Gemini đính kèm toàn bộ phản hồi dưới dạng file Markdown UTF-8 tải xuống được. Ví dụ cho lượt phản hồi tiếp theo:

> Hãy tạo và đính kèm file `GEMINI_RESPONSE_05.md` chứa toàn bộ phản hồi bằng Markdown UTF-8, có tiêu đề, đoạn văn, danh sách, bảng và khối code dễ đọc. Đầu file ghi vòng 001, lượt phản hồi 05, ngày và các file nguồn đã đọc. Nếu không thể tạo file tải xuống, hãy xuất toàn bộ nội dung trong một khối code bao bằng bốn dấu backtick, nhãn markdown, để tôi lưu thành file. Không chỉ gửi bản tóm tắt và không tuyên bố đã tạo file nếu chưa có đính kèm.

Tăng số lượt cho các phản hồi tiếp theo; lưu file mới cùng thư mục vòng thảo luận, không ghi đè phản hồi cũ. [Mẫu yêu cầu thảo luận](templates/DISCUSSION_REQUEST.md) đã có phần hướng dẫn xuất file này. Không sửa prompt hoặc handoff lịch sử chỉ để cập nhật định dạng phản hồi.

## Duy trì qua nhiều vòng

- Mở vòng mới theo tên `002_<chu_de>`, `003_<chu_de>`; giữ vòng cũ để tra lại lý do quyết định.
- Phân biệt rõ nội dung do Codex viết, phản hồi Gemini và quyết định của người dùng. Không ghi rằng hai bên đã đồng ý khi chưa có phản hồi.
- Khi code hoặc kết quả kiểm chứng thay đổi, nhờ Codex cập nhật `PROJECT_CONTEXT.md` và tạo lại `GEMINI_HANDOFF.md` trước khi gửi. Bản upload là snapshot, không tự đồng bộ với repo.
- Mỗi handoff ghi code commit và SHA256 của source đính kèm (nội dung UTF-8 với xuống dòng LF). Khi có thay đổi chưa commit cần ghi rõ; không dùng commit nền để ngụ ý các thay đổi đó đã nằm trên GitHub.
- Nguồn chuẩn là code hiện tại, dữ liệu/rulebook đúng split và kết quả chạy thực tế. Nếu nhận xét cũ mâu thuẫn với nguồn mới, kiểm chứng rồi cập nhật quyết định.
- Packet hiện chỉ gồm tài liệu kỹ thuật, source, test tổng hợp và số liệu kiểm chứng tổng hợp. Không tự đưa dữ liệu doanh nghiệp, câu hỏi/đáp án BTC, cache hoặc file môi trường vào packet. Nếu cần ví dụ, ưu tiên fixture tổng hợp và chỉ thêm đúng phần phục vụ vấn đề đang hỏi.
- Gemini hỗ trợ phát triển và review. Pipeline nộp thi vẫn tuân theo yêu cầu chạy offline bằng model hợp lệ của cuộc thi.

## Câu lệnh trao đổi với Codex

> Cập nhật gói Gemini theo trạng thái repo hiện tại. Chủ đề tiếp theo là …

> Đọc GEMINI_RESPONSE.md của vòng 001, kiểm chứng từng nhận xét và viết phản hồi cho Gemini.

> Dựa trên quyết định đã chốt ở vòng 001, triển khai … và cập nhật kết quả test vào hồ sơ trao đổi.
