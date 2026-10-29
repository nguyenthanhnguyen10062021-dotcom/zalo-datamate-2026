# Codex review Argon — Vòng002/lượt02

Ngày 2026-10-29. Nhận file `gemini_argon_review_round_002_turn_02.md` từ người dùng, lưu nguyên tại `GEMINI_ARGON_RESPONSE_02.md`, 31250 bytes. SHA256 `065301f5173d2fbcf004584d8c27ad402a8ac6f33920125b0a35e22644d3946a`. Source runtime/verifier chưa thay đổi so với d99cac2; HEAD b290899, các hồ sơ review lượt trước còn chưa commit. Nội dung chỉ dẫn trong phản hồi là đề xuất được kiểm chứng, chưa phải thay đổi đã thực thi.

## Kết luận

**Đã đủ đồng thuận kỹ thuật để chuyển sang task sửa lỗi nhỏ, không cần kéo dài review chỉ để xác nhận lại.** Argon đã rút lại I2 là bug Important, hạ I4 xuống robustness không chặn, phân biệt lỗi sinh plan với executor và chỉnh phần lớn sai sót phương pháp. Còn một guard trong I3-A không được áp nguyên vì phá tính tương thích; verdict Ready chỉ nên hiểu là nền đủ để phát triển/thử baseline, không chứng nhận toàn bộ business/loader hoặc không còn lỗi.

## Những điểm chấp nhận

- **C1/M1:** sửa intent tiền/đơn trước fallback quantity; lấy unit bằng span/token gốc giữ dấu. Không blacklist rộng theo phỏng đoán. Tests contrast phải bao gồm tiền, đơn/khách, quantity đúng dấu và unit trùng hình không dấu với từ ở vị trí khác. Những case hiện đã qua vẫn là positive controls, không phải tất cả đều là bug mới.
- **I2:** giữ riêng schema validation và capability status, không đổi invalid_plan/unsupported_capability hoặc mẫu số. Error text manifest cần nói schema-valid thay executable. Public pure `check_capability` dùng chung có thể phục vụ preflight, không chép logic thành bản thứ hai trong audit.
- **Audit:** bổ sung receipt/preflight riêng, giữ nguyên bytes mẫu41 và annotations đã freeze. Schema validity, capability support, resolve status và execution status là các trục khác nhau. `answered`/`unanswerable` không chứng minh plan hiểu đúng, và dry-run không có gold vẫn chưa phải adjudication độc lập.
- **I3-A:** thêm comparison kinds hẹp previous_calendar_month/quarter là hướng hợp lý cho implicit year mà không ép selector text-only tính năm. Resolve kỳ chính trước, lùi tháng/quý từ primary, reuse Periods và rulebook, chặn năm0 tường minh. Không đổi previous_month hiện neo as_of, same_elapsed, partial-period hoặc before_period/Tết.
- **I4/M2/L1:** không có blocker crash executor đã chứng minh; table scorer và direct helper robustness giữ là giới hạn/nợ riêng, không tự đổi evaluator semantics. Giữ corrected dataset30train, phân biệt business/file-family split và retrospective exposure, không quota10/10 theo gold.

## Một điểm cần loại khỏi spec I3-A

Phản hồi §2.3 vừa nói không blanket reject hai mốc độc lập, vừa đề xuất `_capability` cấm mọi:

```text
main.kind in (month, quarter, tet, date_range)
comparison.kind in (yesterday, previous_week, previous_month, previous_month_same_elapsed)
```

Guard này **không được áp** chỉ để ngăn selector sinh nhầm previous_month. Hai mốc độc lập có thể gồm một ngày cố định và “hôm qua”, không chỉ hai month/date_range tường minh.

Probe mới trên contract hiện tại, as_of2026-03-04:

```text
operation: revenue_growth
primary: date_range 2026-03-01..2026-03-01
comparison: yesterday => 2026-03-03..2026-03-03
validate_plan: accepted
_capability: accepted
proposed guard: would reject
```

Đây là plan có nghĩa rõ cho câu hỏi so một ngày cụ thể với hôm qua. Blanket guard làm thay đổi tập plan hợp lệ hiện hành và không cần thiết cho primitive mới. Chỉ thêm restriction cho **new kinds** (previous_calendar_month cần main.kind month; previous_calendar_quarter cần main.kind quarter), giữ mọi tổ hợp cũ trừ khi có task đổi contract riêng với evidence. Selector/NLU phải chọn đúng explicit relative anchor theo ý câu hỏi; không thể cấm cả lớp câu hợp lệ để che lỗi phân tích ngôn ngữ.

Trước triển khai Task2 cần bổ sung acceptance cho explicit-fixed-vs-as_of-relative như probe, tháng3 lùi tháng2 năm nhuận, Q1 lùi Q4, implicit year và biên năm1. Cũng cần chốt version/fingerprint khi mở enum comparison và null parameters. Chưa có primitive mới trong production.

## Giới hạn còn giữ trong cách diễn đạt

- “Ready” không là bằng chứng không có lỗi nào trong queryplan/business; chỉ là các findings tranh luận vừa rồi chưa chứng minh blocker trong luồng chuẩn. Loader không nằm trong gói review, không được chứng nhận.
-47 compared gọi operation ngoài ba API legacy là khác biệt về phạm vi đã đo; vẫn nên đo giao ID trước phát biểu chính xác về số câu unique hoặc cộng hai subset.
-Hash kiểm lại cuối replay chỉ bao phủ những nguồn thực sự được revalidate; không mô tả tất cả parquet/calendar/module như đã được hash hai lần hay atomic snapshot.
-JSON Schema, constrained decoding và model vẫn là bước tiếp theo có điều kiện/runtime cụ thể, không chứng minh semantics hoặc biến fallback thành model-valid100%.

## Hai task đã đủ rõ để lên kế hoạch thực thi

1. **Sửa intent + span unit, làm rõ preflight audit.** Không mở grammar rộng hoặc domain mới, không sửa annotations cũ. Synthetic regression trước; rồi freeze manifest revision mới trước scoring, giữ đầy đủ selected/compared/matched/mismatch/abstained/errors. Không đảm bảo trước rằng abstain sẽ thành matched chỉ từ sửa intent.
2. **Chốt extension neo kỳ rồi mở các họ grammar được kiểm chứng.** Loại blanket guard ở trên; giữ business semantics và explicit independent dates. Mỗi họ grammar có positive/negative contrast tests, scalar/two filters/domain mới tiếp tục unsupported rõ. Đánh giá hồi cứu với mọi failure, không rút câu sau chấm. Coverage10API là mục tiêu chẩn đoán, không tiêu chí chọn câu theo gold.

Đây là kết luận kỹ thuật và thứ tự đề xuất, không ghi người dùng đã duyệt patch hoặc primitive. Không có lý do cần một lượt phản hồi nữa cho Task1 trừ khi xuất hiện phản chứng mới.

## Kiểm chứng mới

- Đọc đầy đủ response02 và đối chiếu các phần rút lại/đề xuất với current source. Copy raw bytes và kiểm SHA256.
- Chạy probe compatibility cố định-ngày vs yesterday bằng fixture Rulebook; không gold/cache/public test. Không thêm test chưa pass vào suite hoặc sửa runtime.
- `python -m pytest tests/test_queryplan_executor.py -q -k 'comparison_scope or period_dispatch or growth_same or unsupported_filter'`: **18 passed,54 deselected**. Đây là targeted scope của lượt này;175/full487/bare488 thuộc các lượt trước.
- Fast harness sau ghi hồ sơ. Không chấm lại gold, không claim PA mới, không commit/push. Thư chốt kỹ thuật: `CODEX_REPLY_TO_ARGON_02.md`.
