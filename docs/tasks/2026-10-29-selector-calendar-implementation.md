# Triển khai sau review Argon — intent, preflight, calendar comparison

- Ngày: 2026-10-29; nền b290899/d99cac2; nhánh VuongNguyen. Có sẵn hồ sơ Flash/Argon và thay đổi tài liệu chưa commit; giữ nguyên.
- Người dùng giao triển khai theo thứ tự Codex thấy hợp lý. Không LLM/model, domain mới, evaluator patch, dependency mới, commit/push trong tác vụ này.

## Contract và acceptance chốt trước code

### Task1 — Intent/span và preflight

- Tiền bán/thu → revenue, đơn bán → order_count; khách và danh từ metric không được rơi vào quantity. Unit giữ đúng span gốc NFC/casefold, không quét lại toàn câu hoặc suy alias. Câu dư scope vẫn unparsed.
- Public `check_capability(normalized_plan)` tái sử dụng nguyên kiểm tra hiện có; giữ UnsupportedCapability/status/stage riêng với PlanValidationError. Không thu nhỏ selected sau khi biết lỗi.
- Audit tạo **receipt mới** với schema/capability status, resolution not_checked, execution not_run; không sửa packet/annotations41 đã freeze. Có thể ghi bổ sung kiểm resolve local với SalesMetrics validation trước, không scorer/gold/answer computation. Schema/capability/resolve không chứng minh plan hiểu đúng.
- Sửa thông báo manifest nói normalized/schema-valid. Unit/intent, preflight và input immutability có synthetic tests RED→GREEN. Freeze manifest_v3 trước chấm, báo đủ mọi kết quả, không chỉnh grammar theo mismatch.

### Task2 — Calendar-relative extension và grammar có giới hạn

- Thêm comparison-only `previous_calendar_month`, `previous_calendar_quarter`; không tham số phụ, main.kind tương ứng month/quarter. Resolve primary trước (năm ngầm định theo Rulebook), lấy kỳ lịch liền trước đầy đủ qua Periods. Năm1/Q1 hoặc tháng1/năm1 → PeriodResolutionError, giữ stage period. Không đổi business hoặc semantics previous_month/as_of, same_elapsed, before_period/Tết và partial-period.
- Giữ version plan1.0 vì extension enum additive chưa có consumer model/schema phát hành; validator cũ reject new kinds an toàn. Ghi contract/capability source hashes trong receipts/report; old plans giữ nguyên hành vi. Không thêm blanket guard fixed-vs-relative.
- Grammar chỉ mở các họ đã có audit: một số time/Telex abbreviations cố định, lời dẫn/hạt từ ở biên, comparison neo tháng/quý và growth clause sau comparison, top-k list tiêu chí rõ, share có explicit nhóm hàng/nhóm khách rõ scope. Mention không dấu vẫn giữ nguyên để resolver quyết định, không dùng catalog/gold/ID trong selector. Không cố bắt mọi tên hàng trần hoặc mọi viết tắt.
- Đơn vị/nhãn phải bảo toàn dấu và số; scalar, hai filter scopes, kỳ không hiểu được và domain mới vẫn reject. Mỗi họ có positive/negative contrast tests; lỗi phải giữ trong selected khi replay.
- Freeze manifest revision riêng sau Task2, trước scoring. Giữ v1/v2/v3 và annotations; không hứa quota số câu hoặc10/10API trước khi đo.

## File/kiểm chứng

- Sửa verification/selection.py, audit.py, manifest.py; queryplan/executor.py, __init__.py, contract.py, resolution.py; tests tổng hợp mới và docs hiện hành.
- Không sửa loader/business/evaluator. Mọi BTC rows/manifests/receipts/reports ở reports ignored.
- Targeted theo task, harness full/bare, local train inventory/replay và data profile baseline riêng. Review final diff và kiểm source/digests artifact cũ. Không chạy lại phép chấm nếu không có thay đổi ảnh hưởng sau lượt đã kiểm.

## Execution record

- Trạng thái **completed** trong working tree, chưa commit/push. Intent/span và public capability preflight được làm trước; calendar comparison và grammar có giới hạn được làm sau. Không sửa loader/business/evaluator, dependency hoặc tích hợp LLM.
- RED→GREEN: Task1 có 7 failures trước sửa intent/span và lỗi import preflight chưa tồn tại; calendar có 12 failures trước primitive; grammar có 13 failures trước mở rộng. Bốn file tests mới cuối cùng **58 passed**, gồm negative contrasts, input immutability, compatibility và expected literals độc lập.
- `doctor`: Python 3.14.10, 5 packages khớp pin, local data ready. `harness.py check --profile data` exit0: full **545 passed, 2 local_data deselected**; local_data **1 passed, 1 skipped** helper evaluator cũ. Bare `pytest -q -rs`: **546 passed, 1 skipped** cùng helper. Fast sau cập nhật tài liệu exit0, kiểm124 repository files, links/boundaries/budgets/whitespace qua; reports/cache/data không tracked. Không chạy hosted CI/Linux.
- V3 freeze sau Task1, trước chấm: **126 selected, 126 compared/matched, 0 mismatch/abstain/execution_errors**, 7 operation, exit0. Sửa ca tiền thành revenue; không thêm alias tiền. Giữ nguyên manifest/report v1/v2; v3 giữ source fingerprint của Task1, hiện stale với selector cuối và không được replay âm thầm.
- V4 freeze sau Task2 synthetic checks, trước chấm: **396 selected/3000**, **2604 outside_selection**; **396 compared/matched, 0 mismatch/abstain/execution_errors**, exit0. Có 395 answered và 1 business unanswerable. Phủ 8 operation: revenue242, order_count39, revenue_growth32, cancellation_rate26, AOV25, cancelled_orders20, top_products10, quantity2. Top_customers/share chưa có selected train, chỉ synthetic. Giữ cả 126 selected v3, thêm270; không loại ca cũ theo gold.
- Baseline legacy riêng trong data profile: **417 selected, 8 skipped, 409 compared/matched gold và legacy, errors=[]**. Giao tập compared baseline với v4 là143, hợp662; không cộng 396+409 thành805 câu riêng biệt, không gọi hợp662 là một lượt chấm thống nhất hoặc PA toàn train.
- Audit giữ nguyên packet/annotations41 và payload digests cũ. `preflight_capability_v2.json` là envelope mới: **23 capability supported, 18 not_checked**; optional filter resolution **19 not_required, 4 resolved**, không tính đáp án hoặc scorer. Resolution ở receipt schema/capability vẫn not_checked; kiểm filter không chứng minh period/execution/semantic correctness. V1 local receipt từng được append metadata sau hash nên dùng envelope v2 cho provenance đầy đủ.
- Đã đối chiếu source hashes report v4 với runtime cuối; kiểm envelope/receipt hashes và input file hashes xác nhận packet/annotations gốc không bị đổi. Manifest file SHA256 v3 `79877e549750a8683fc39a385c288f9c4e7f72e877a6dcc9aa1330270f4a5589`; v4 `9ebd4ecc38f093d2c4828de6adb9611cbc57c1658817d063c7b3896bac831bb6`. Selector cuối SHA256 `887f1f651925d4fba2c899b7e3db71a5e8455ca0a0de99f3e9a729923fb2ac82`.
- Reports/manifest/receipt/cache fingerprints và rows chỉ local ignored ở reports/capability_inventory/ và reports/harness/. Không chỉnh grammar sau khi thấy kết quả v3/v4; không human adjudication, blind holdout hoặc PA model/NLU. Review diff cuối do chính agent triển khai thực hiện, không có reviewer độc lập mới.
- Next action: audit kế tiếp các bucket còn lại bằng question-only annotation trước grammar; chốt contract riêng nếu cần scalar hoặc hai filter scope. Giữ top_customers/share là khoảng trống kiểm chứng train, không nới grammar để đạt quota API. Model/runner cần tác vụ và acceptance riêng.
