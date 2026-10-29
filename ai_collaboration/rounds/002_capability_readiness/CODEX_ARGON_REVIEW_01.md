# Codex review phản hồi Argon — Vòng002/lượt01

Ngày 2026-10-29. Source `b290899`; source tính toán/verifier vẫn tương ứng handoff `d99cac2`. Đây là kiểm chứng phản hồi, chưa triển khai các chỉ dẫn sửa code trong tài liệu.

## Nguồn và đính chính model

Người dùng xác nhận bản cũ là Flash và bản mới là **Argon, đối tượng phản biện chính**. Giữ bản Flash 10298 bytes tại `GEMINI_RESPONSE_01.md` và các hồ sơ CODEX_REVIEW_01/CODEX_REPLY_TO_GEMINI_01 như lịch sử. Bản mới lưu nguyên bytes riêng tại `GEMINI_ARGON_RESPONSE_01.md`, 57250 bytes, SHA256 `b423996dcc05a6fade827ce7d27d52b60d6baf3ef78f0a18d6281bdbbb55ba09`.

Dòng đầu bản mới tự ghi “Gemini 3 Flash (Web / Paid tier)”, trái với xác nhận người dùng. Attribution trong hồ sơ theo người dùng là Argon; không sửa nội dung gốc hoặc tự suy tên model kỹ thuật. File mới đầy đủ năm câu hỏi và kết luận, khác bản Flash bị cắt.

## Kết luận chính

**Chấp nhận hướng củng cố lỗi có bằng chứng, giới hạn đầu tư regex và sớm đo baseline model/runner. Không chấp nhận nguyên các gate/sửa code do Argon đề xuất.** Có phản chứng mới hữu ích, nhưng một số findings đánh đồng kiểm schema với capability, helper direct với executor, và split business với split họ file. Đánh giá “nền executor đạt có điều kiện, chưa có baseline đầu-cuối” hợp lý; danh sách blocker cần thu hẹp theo kiểm chứng dưới đây.

## Kiểm chứng từng finding

### C1 — Nhầm metric thành unit: đúng, ưu tiên Important

Probe tổng hợp mới xác nhận:

- Hỏi tiền bán trong kỳ/ca → selected quantity với unit `tiền`, thay vì revenue.
- Hỏi bán được bao nhiêu đơn → selected quantity với unit `đơn`, không phải order_count.
- Hai dạng “thu được bao nhiêu tiền” và “bán được bao nhiêu doanh thu” trong probe bị **unparsed**, không phải đều selected quantity như nhãn finding có thể khiến người đọc hiểu.

Đây là lỗi selector hiện hành cần sửa. Nguy cơ tính sai khi catalog có unit trùng danh từ metric là có cơ sở, nhưng không chứng minh Critical toàn pipeline: selector là dev-only và chưa có model/runtime NLU. Không cần phóng mức ảnh hưởng mới ưu tiên được lỗi này.

Hướng sửa: nhận diện metric trước fallback quantity, giữ span của unit và dùng synthetic contrast tests. Không áp nguyên blacklist chứa `mon/loai/...` mà chưa kiểm tra rulebook/cách hỏi; từ chỉ đơn vị và danh từ metric có thể trùng sau bỏ dấu. Không thêm tiền vào alias/catalog. Chưa sửa trong lượt này.

### I2 — Schema-valid nhưng ngoài capability: hiện tượng đúng, không phải bypass executor

Ba plan tổng hợp (top_products metric orders; revenue có unit; today growth so before_period) đều qua `validate_plan` rồi trả `unsupported_capability` tại stage capability, trước khi đọc bảng. Tests hiện có đã chủ ý kiểm tra phân biệt này. [Contract](../../../docs/queryplan.md) và [spec](../../../docs/superpowers/specs/2026-10-29-capability-verifier.md) cũng ghi rõ selected plan có thể bị từ chối khi execute.

Vì vậy “không gọi `_capability` trong validator” không tự là bug tính toán hoặc lọt plan thực thi sai. Tuy nhiên, error text “normalized and executable” trong manifest nói quá khả năng kiểm tra; tên decision `supported_plan` của annotation cũng dễ bị hiểu thành đã chạy. Nên làm rõ theo các trục schema_valid / capability_supported / resolution_checked / execution_status, giữ provenance và mọi mẫu số.

Public pure capability checker dùng chung là một cải tiến có lý nếu cần preflight/audit, nhưng không bắt buộc hợp nhất vào validate_plan hoặc đổi `unsupported_capability` thành `invalid_plan`. Nếu đổi selection policy phải version manifest trước chấm, không loại plan đã biết abstain để làm report xanh. File annotation hiện tại là đề xuất schema-valid, chưa thực thi; không có bằng chứng 23 annotation thực tế vi phạm capability chỉ từ các ví dụ giả định của Argon.

### I3 — So kỳ lịch sử: đúng lỗi sinh plan, primitive mới là lựa chọn thiết kế

Probe mới xác nhận as_of2026-03-04, hỏi tháng1/2024 so tháng trước → plan primary tháng1/2024, comparison previous_month → resolver trả tháng2/2026 thay vì tháng12/2023. Đây là lỗi đường câu hỏi→plan cần xử lý.

`Periods.previous_month` hiện được định nghĩa theo as_of, không phải kỳ chính. Không đổi ngầm semantics business hoặc blanket reject mọi relative comparison ngoài cặp today/yesterday, this_month/previous_month: có câu hỏi cố ý nêu hai mốc độc lập. Với kỳ có năm tường minh có thể compile comparison month/year cụ thể; với năm ngầm định cần bước tất định có as_of/rulebook hoặc primitive neo kỳ được đặc tả rõ. Không nên đẩy phép tính lịch sang model bằng lời nhắc đơn thuần.

Primitive hẹp như previous_calendar_month/quarter có thể hữu ích. Tuy nhiên “previous_period” chung cho date_range/month/quarter/Tết có nhiều nghĩa; `Periods.before` đang mang luật trước Tết và khoảng liền trước cùng số ngày, không đồng nghĩa tháng lịch trước. Nếu thêm phải chốt contract và test biên/năm ngầm định, không coi đây là bản vá vài dòng được áp tự động.

### I4 — Ngày/calendar gây crash: chỉ đúng một phần, không tái hiện crash executor như kết luận

Probe tổng hợp trên luồng công khai QueryExecutor:

| Input | Kết quả thực chạy |
|---|---|
| Một ngay_dat là bad-date | data_error, stage data |
| Thiếu ngay_dat | data_error, stage data |
| Calendar thiếu header bắt buộc | period_error |
| Calendar có ô dư ở cuối dòng, đủ header/endpoints | answered, không có csv.Error |
| as_of_date=None khi khởi tạo | TypeError ở constructor, đúng contract caller phải truyền ngày hợp lệ |

Gọi riêng `resolve_filters` với ngày hỏng/thiếu cột phát DateParseError/KeyError; gọi riêng `Periods.tet` với CSV thiếu cột phát KeyError. Đây là thông tin robustness của direct API. Nhưng docstring `resolve_filters` quy định caller phải validate envelope/ngày với SalesMetrics trước; QueryExecutor đã làm đúng thứ tự, nên không thể chuyển phản chứng gọi trực tiếp thành chứng minh executor crash. Bọc coerce rồi lặng bỏ ngày lỗi cũng không được phép.

Argon còn mô tả sai csv.DictReader: ô dư tạo key None trong **row**, không chèn None vào `fieldnames`; strict=True không tự báo csv.Error chỉ vì thừa ô. Probe xác nhận. Có thể cân nhắc strict row-width hoặc bảo vệ direct Periods API trong task riêng, nhưng chưa phải blocker được chứng minh của executor hiện tại.

### M1 — Va chạm dấu unit: đúng phản chứng mới

Probe “Ca sáng ... bao nhiêu cá” trả `unparsed/ambiguous_unit_spelling`: raw_words chứa cả `Ca` và `cá`, cùng fold ca. Lấy dấu unit bằng tìm ngược toàn câu làm reject dù đúng vị trí unit không nhập nhằng. Nên giữ span/token alignment của unit. Đây là thiếu sót grammar/resolution text, chưa có số câu train bị ảnh hưởng từ phản chứng synthetic này.

`_clean` xóa từ nối toàn cục cũng là rủi ro khi mở grammar cho mention không nháy. Hiện quoted mentions được bảo vệ; không trình bày nguy cơ trong code tương lai như đã chứng minh lỗi tất cả tên hàng hiện tại.

### M2 — Table column mapping: xác nhận mất tính một-một, chưa ảnh hưởng v1

`map_columns(['A','B'], ['B','Other'])` trả `[0,0]`. Probe table tổng hợp gold row `[1,1]`, pred row `[1,999]` được score correct vì chiếu cùng cột0 hai lần, bỏ qua999. Đây là giới hạn thật của local table scorer, cần ghi lại và kiểm quy định BTC trước sửa vì đổi comparator có thể đổi scoring contract. 10 API v1 chưa trả table; không bắt toàn bộ baseline v1 chờ sửa table. Chưa chứng nhận evaluator tương đương BTC.

### L1 — Helper skip và output path: chỉ nhận phần đúng

Helper real-file có path lookup sai đã được ghi; hiện **đã có** marker local_data, nên đề nghị thêm marker như chưa có là không cập nhật source. Sửa lookup là nợ kỹ thuật riêng; self-score xanh cũng không chứng nhận tương đương BTC.

Probe gọi inventory CLI với output trùng calendar.csv **đã tồn tại** trả exit2, bytes input không đổi. Claim có thể ghi đè calendar hiện có không tái hiện: CLI đã reject out.exists. Inventory chưa bắt buộc suffix json hoặc cấm output mới nằm dưới custom input directory bên trong reports; đây là consistency/hygiene có thể cải thiện, khác với phá hủy input đã có. Vẫn cần phân biệt policy toàn bộ các input/cache path với chỉ kiểm một số protected files.

## Các vấn đề phương pháp cần sửa trong phản hồi Argon

1. **“44 doanh nghiệp train”, split34/10: sai nguồn dữ liệu.** Metadata repo ghi30 train,10 họ file A–J;44 là số doanh nghiệp loader từng chạy qua train/public. Không đưa public test vào tuning/holdout nội bộ hoặc dùng nó để đủ quota44.
2. **Business-disjoint không đồng nghĩa file-family-disjoint.** Hai tập không chung business vẫn có thể chung họ file; phải nêu rõ group definition và rebuild artifacts theo dev fold. Toàn train đã có exposure, không gọi một split mới là blind validation. Đây đã là quyết định trong repo.
3. **13 câu reason bucket không phải trần capability hai filter.** Một câu loại này có thể nằm ở comparison/operation/time bucket khác. Không suy lợi ích tối đa13/3000 từ13 multiple_filter_scopes. Audit nhỏ không là phân bố domain/capability toàn train.
4. **Mục tiêu10/10 API gold là mong muốn coverage, không quota để chọn theo gold.** Có thể freeze annotated plans hoặc mở grammar tường minh trước scoring, giữ cả mismatch và abstain. Không dùng 30 dòng regex, một phiên hoặc “đủ hết gold đúng” làm chứng cứ correctness; không hứa đạt9–10 API khi chưa inventory khả thi.
5. **Không có căn cứ “gần như toàn bộ125 nằm trong409”.**47 ca compared ở cancellation_rate22+AOV14+order_count7+growth4 gọi API ngoài ba API legacy đã đo; còn intersection ID chưa tính. Nên đo giao/khác thay vì suy đoán và không cộng hai mẫu số.
6. **Hash không chứng minh chống sửa lén hoặc replay bit-for-bit.** Manifest đang kiểm question/rulebook/selector; runner ghi một số hash trước hoặc sau đọc/thực thi. Không bảo vệ atomic snapshot mọi cache/calendar/runtime blob chỉ nhờ có SHA. Không cấp chứng nhận integrity rộng hơn code thực hiện.
7. **Không có timing benchmark trong gói** để khẳng định126 câu chạy “vài giây”. Tests nhiều không là benchmark hoặc bảo đảm architecture luôn nhanh. Không cần đổi SQL khi chưa có vấn đề đo được, nhưng cũng không cần tuyên bố cấm tuyệt đối mọi phương án tương lai.
8. **Schema và catalog-aware context hữu ích nhưng không chứng minh semantics hoặc100% model-valid.** Constrained decoding vẫn cần semantic/capability validation, retry/abstain và log tỷ lệ plan thô lỗi riêng; fallback abstain không biến output lỗi thành bằng chứng model sinh100% đúng. Metadata/catalog có as_of khác transactions cũng cần chính sách nguồn rõ, không chỉ cắt mọi bảng theo ngày không tồn tại.

## Ưu tiên đề nghị sau review

1. **Sửa nhóm lỗi sinh plan đã tái hiện, chốt preflight semantics:** intent tiền/đơn trước fallback quantity, span unit, compiler thời gian có context tất định; làm rõ schema-valid/capability/resolve/execution bằng metadata/checker nếu cần. Synthetic contrast tests trước, không đổi business ngầm hoặc ép mọi lỗi thành invalid_plan. Freeze manifest/annotation revision mới trước chấm; giữ mọi câu lỗi. Hướng tới coverage ranking/share bằng trường hợp có diễn giải tường minh, không quota gold bắt buộc để bắt đầu task kế.
2. **Baseline model offline + runner có ngân sách/phạm vi rõ:** chọn runtime/model sau khi kiểm điều kiện máy/competition được cung cấp, nối strict validation/capability/resolve/execute, đo cả valid-plan thô, precision/coverage/abstain/error và latency. Đánh giá business-disjoint/file-family-disjoint đúng định nghĩa, gắn nhãn hồi cứu và kiểm artifact leakage. Không mở rộng domain, scalar hoặc hai filters chỉ để ép coverage trước baseline.

Dry-run annotations không đọc gold là bước kiểm thực thi có giá trị, nhưng `answered` hoặc `unanswerable` không chứng minh hiểu đúng câu. Nên giữ annotation freeze ban đầu, bổ sung receipt độc lập về capability/resolution/execution status; không ghi đè quyết định AI hoặc gọi đó là human adjudication.

## Kiểm chứng trong lượt này

- Lưu nguyên bản Argon, không ghi đè Flash. Dùng source/tests synthetic; không đọc gold, train rows, public test hoặc cache doanh nghiệp.
- Probe review local: `reports/gemini_round002_argon/probes.py`, output `probe_results.json`; dữ liệu lịch/CLI đều synthetic. Có warnings pandas do cố ý đưa bad-date; assertions đúng kết quả nêu trên. Không thêm regression tests lỗi vào suite hoặc áp fix trong lượt review.
- Targeted `tests/test_queryplan_contract.py`, `test_queryplan_executor.py`, `test_capability_inventory.py`, `test_queryplan_verification.py`, `test_plan_annotation_audit.py`: **175 passed**, chạy mới. Fast harness sau khi ghi hồ sơ; full487/bare488 và gold subset thuộc lượt trước, không claim đã chạy lại.
- Source runtime/verification không đổi. Không commit/push hoặc gửi Gemini tự động. Thư phản biện chính tiếp theo: `CODEX_REPLY_TO_ARGON_01.md`; không dùng thư xin phần bị cắt của Flash cho bản Argon đầy đủ này.
