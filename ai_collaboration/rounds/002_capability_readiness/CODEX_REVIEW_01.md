# Codex kiểm chứng phản hồi Gemini vòng002/lượt01 — 2026-10-29

## Nguồn và phạm vi

Nhận file người dùng từ Downloads, giữ nguyên bytes tại `GEMINI_RESPONSE_01.md`. SHA256: `520b2a5c7cf1404ede1ec521915ba1c3d3463faf6a0b75431886a4fc2e014935`, 10298 bytes. Source hiện tại `b290899`; runtime/verification tương ứng snapshot `d99cac2`. Working tree sạch trước nhận file (ngoại trừ warning permission .pytest_tmp đã biết).

**Phản hồi bị cắt giữa Câu 2**, kết thúc ở chuỗi “`verification/runner.py` tu”. Không có phần trả lời Câu 3–5, lựa chọn hai đầu việc hoặc các gate đầy đủ. Không diễn giải phần thiếu thành Gemini đã đồng ý. Các chỉ dẫn sửa trong phản hồi là đề xuất để review, chưa thực thi.

## Kết quả kiểm chứng phần đã có

| Nhận định | Đánh giá của Codex |
|---|---|
| Intent tiền bán bị gán quantity | **Đúng, tái hiện được**, đã được audit trước. Chưa sửa trong source. Cần sửa intent bằng luật tổng quát và contrast tests, không thêm alias tiền vào đơn vị. |
| Kỳ lịch sử so tháng trước bị neo sai | **Đúng ở đường câu hỏi → plan**, có phản chứng mới chạy được. Cần phân biệt lỗi selector với contract Periods/QueryExecutor. |
| Top1 scalar/string chưa hỗ trợ | **Đúng là giới hạn v1 có chủ ý**, chưa phải bug API trả list. Không tự unwrap list hoặc đổi expected_type. |
| So khớp subset không chứng minh coverage/PA | **Đúng**, kết quả 125/125 và 409/409 phải giữ phạm vi. Accidental agreement có thể xảy ra. |
| 125/125 chứng minh ánh xạ tham số chuẩn xác | **Khẳng định quá mức**: chỉ chứng minh kết quả trùng gold theo scorer trên các câu compared; sai period/filter vẫn có thể cho cùng đáp án. Cần audit plan hoặc contrast tests để kiểm mapping. |
| JSON Schema/BNF là điều kiện bắt buộc trước baseline đầu-cuối | **Chưa đủ căn cứ để coi là blocker**. Runtime đã có validator nghiêm ngặt. Schema cho constrained decoding là lựa chọn adapter/robustness đáng cân nhắc khi tích hợp model, không phải bằng chứng executor sai hoặc điều kiện logic bắt buộc để chạy baseline. |
| Handoff có 36 file và đã đọc đủ 36 | **Sai số đếm**: handoff có 37 block `### File:`. Danh sách Gemini nêu cũng cần đối chiếu với bảng kê; không xác nhận thay Gemini rằng đã đọc/băm thực tế. |
| Selected126/3000 là4.17%, ngoài selection95.83% | **Nhầm mẫu số/tử số**: selected là4.20%, ngoài selection95.80%;125 compared/3000 mới là4.17%. Không đánh đồng selected với compared. |

## Phản chứng thời gian và vị trí sửa cần cân nhắc

Probe tổng hợp không đọc gold/cache: as_of_date `2026-03-04`, hỏi doanh thu tháng1/2024 thay đổi phần trăm so tháng trước. `select_question` trả plan tháng1/2024, comparison.kind=`previous_month`. `resolve_period` trả kỳ chính `2024-01-01..2024-01-31` và kỳ so sánh `2026-02-01..2026-02-28`; ý câu hỏi cần `2023-12-01..2023-12-31`.

Vậy nhận định về hậu quả là đúng. Tuy nhiên, public `Periods.previous_month()` và relative kinds của plan vốn neo theo as_of_date, còn annotation audit đã đề xuất tháng/năm tường minh cho so sánh neo kỳ lịch sử. Không thể suy rằng phải đổi business/Periods để primary-relative chỉ vì selector tạo plan sai. Hướng sửa nhỏ là selector/NLU sinh comparison `month=12,year=2023` khi câu hỏi neo vào tháng1/2024. Có thể cân nhắc capability guard hoặc trường anchor rõ để ngăn nhầm, nhưng cần test tương thích và hỗ trợ câu hỏi có hai mốc độc lập; không áp dụng blanket reject/đổi semantics vội.

Đề xuất mở `before_period` cho mọi kỳ cũng không tự giải quyết: API `Periods.before` hiện mang luật so trước Tết và độ dài kỳ ngay trước, không đồng nghĩa tháng lịch liền trước cho mọi month/date_range/quarter. Cần contract riêng nếu muốn tổng quát hóa.

Probe intent tiền tổng hợp cũng trả `operation=quantity`, `unit_mention=tiền` như phản hồi. Chỉ xác nhận hành vi, không chạy sửa hoặc ghi test kỳ vọng mới vào suite trong tác vụ đọc/review.

## Kiểm chứng và giới hạn lượt này

- Đã đọc toàn bộ file nhận được và kiểm tra điểm kết thúc, kích thước, SHA256; copy nguyên bytes.
- Chạy hai probe tổng hợp nói trên bằng Rulebook fixture, selector và resolve_period; không gold, cache hoặc mạng. Đếm37 source blocks và tính lại tỷ lệ từ denominator đã công bố.
- Không sửa runtime/selector, không chạy gold/data profile, không có số PA mới. Fast harness chạy sau cập nhật hồ sơ. Full487/bare488 thuộc lượt trước, không trình bày là chạy mới ở đây.
- Cần Gemini trả phần còn thiếu và làm rõ phân loại lỗi thời gian trước khi coi cuộc review hoàn tất. Thư tiếp theo: `CODEX_REPLY_TO_GEMINI_01.md`.
