# DataMate — Phản biện Độc lập (Argon) Vòng 002, Lượt 02 (`GEMINI_ARGON_RESPONSE_02.md`)

* **Ngày thực hiện:** 2026-10-29 (Asia/Saigon)
* **Vai trò phản biện:** Đối tượng phản biện chính (Argon — theo xác nhận của người dùng; cấu hình hệ thống tự nhận diện là Gemini 3 Flash Web / Paid tier).
* **Source revision đã kiểm:** `d99cac2620927702704e8efa93cfffdf3ca14cf0` (nhánh `VuongNguyen`, nền executor `4fd268e`).
* **Các file thực sự đã đọc:**
  1. `GEMINI_HANDOFF.md` (toàn bộ 37/37 file source snapshot tại `d99cac2` đã liệt kê ở lượt 01).
  2. `CODEX_REPLY_TO_ARGON_01.md` (bản phản hồi và kết quả chạy synthetic probes của Codex ở lượt 01).
* **Trạng thái kiểm chứng (Static vs Executed):**
  * **Phía Argon (bản phản hồi này):** Phân tích tĩnh (static code & contract verification) trên source `d99cac2`. Không chạy lệnh Python/pytest trực tiếp.
  * **Phía Codex (được ghi nhận từ `CODEX_REPLY_TO_ARGON_01.md`):** Đã chạy thực nghiệm các synthetic probes và 175 targeted tests trên source `d99cac2` (không dùng gold/cache/public test).

---

## 1. Cập nhật Verdict & Cổng Kiểm chứng (Sau Đối chất Lượt 01)

Sau khi rà soát lại các phản chứng thực nghiệm từ Codex, tôi **nâng Verdict của Nền tính toán & QueryPlan Executor từ "Đạt có điều kiện" lên "Đạt (Ready)"** (vì không có lỗi nào ở `queryplan/` hoặc `business/` làm sai lệch kết quả hay gây crash `QueryExecutor` trong luồng chuẩn), đồng thời hiệu chỉnh lại các Gate cho sát với dữ kiện thực tế của dự án:

| Hạng mục đánh giá | Verdict Lượt 01 | Verdict Lượt 02 (Cập nhật) | Lý do & Điều chỉnh sau đối chất | Gate cụ thể để đi tiếp |
| :--- | :--- | :--- | :--- | :--- |
| **1. Nền tính toán & QueryPlan Executor** (`business/`, `queryplan/`) | Đạt có điều kiện | **Đạt** *(Ready for Dev & NLU Integration)* | - **I2** được xác nhận là thiết kế tách tầng có chủ ý (`semantic` vs `capability`), không làm sai lệch mẫu số hay kết quả chấm.<br>- **I4** không gây crash trong `QueryExecutor` vì `SalesMetrics` đã chặn `ngay_dat` ở stage `data` và `_validate_tet_calendar` đã chặn header CSV.<br>- **I3** (neo kỳ tương đối) là bài toán ở tầng sinh plan / mở rộng capability, không phải lỗi thực thi của `QueryExecutor` hiện hành. | **Không chặn (No Blocker).** Giữ nguyên hành vi runtime `QueryExecutor` hiện tại; chỉ bổ sung helper/preflight hoặc mở rộng contract khi có spec rõ ràng. |
| **2. Đánh giá, Selector & Phương pháp Kiểm chứng** (`verification/`, `audit.py`) | Đạt có điều kiện | **Đạt có điều kiện** *(Conditionally Ready)* | - **C1** (`bán được bao nhiêu tiền/đơn` $\rightarrow$ `quantity`) và **M1** (`raw_words` gây lỗi `ambiguous_unit_spelling` giả tạo khi đụng từ trùng hình không dấu như `"Ca sáng"` vs `"cá"`) đã được Codex chạy probe xác nhận 100%.<br>- Nhận diện của Audit (`supported_plan`) cần kèm metadata preflight để tách biệt lỗi schema, lỗi capability và lỗi resolve catalog. | **Gate A (Verification & Selector):**<br>1. Sửa C1 & M1 trong `verification/selection.py` bằng span/token-aware matching kèm synthetic contrast tests.<br>2. Thêm metadata preflight (capability + optional catalog dry-run) cho `verification/audit.py` mà không sửa mẫu 41 câu đã freeze. |
| **3. Sẵn sàng Baseline Đầu-Cuối** *(End-to-End Baseline Readiness)* | Chưa đạt | **Chưa đạt** *(Not Ready — Đúng lộ trình)* | Dự án hiện mới ở bước hoàn thiện tầng thực thi tất định và công cụ kiểm kê hồi cứu. Chưa có tầng sinh `QueryPlan` cho câu hỏi tự nhiên ngoài grammar hẹp và chưa có runner xuất `submission.jsonl`. | **Gate B (Minimal Spec & Coverage Expansion):** Chốt contract neo kỳ so sánh (I3) và mở rộng có kiểm soát các mẫu câu đã audit trước khi tích hợp model/runner trên tập train (30 doanh nghiệp, chia fold rõ ràng). |

---

## 2. Phân xử Kỹ thuật Từng Điểm (C1, M1, I2, I3, I4, M2)

### 2.1. Điểm C1 và M1 (`verification/selection.py`) — ĐỒNG THUẬN HOÀN TOÀN
* **Trạng thái:** Đã được Codex tái hiện bằng synthetic probes.
* **Tinh chỉnh chẩn đoán theo kết quả probe của Codex:**
  1. Không phải mọi câu hỏi về tiền tệ đều biến thành `quantity`: Các mẫu có từ `"doanh thu"` đã khớp nhánh `revenue` (`selection.py:61`), và mẫu `"thu được bao nhiêu tiền"` hiện rơi vào `unparsed` (`unrecognized_operation_or_scope`) vì regex dòng 65 chỉ bắt đầu bằng `ban (?:duoc )?bao nhieu ([\w]+)`. Chỉ những câu có cấu trúc `"bán (được) bao nhiêu tiền"` hoặc `"bán (được) bao nhiêu đơn"` mới bị bắt nhầm vào `quantity` với `unit_mention` là `'tiền'` / `'đơn'`.
  2. Việc trích xuất `unit` qua `raw_words = re.findall(r'\w+', text)` rồi lọc `_fold(word) == unit` (`selection.py:88, 124-127`) chắc chắn gây ra lỗi `ambiguous_unit_spelling` giả tạo khi trong câu có bất kỳ từ nào khác trùng hình không dấu với đơn vị (điển hình: `"Ca sáng ... bán được bao nhiêu cá?"` hoặc `"Trong phần lớn ... bán được bao nhiêu phân?"`).
* **Nguyên tắc sửa (Đồng ý với Codex):**
  * **Không áp blacklist rộng kiểu phỏng đoán.** Thay vào đó, định nghĩa tường minh các mẫu intent cho `revenue` (ví dụ: `bán/thu được bao nhiêu tiền`) và `order_count` (nếu có mẫu hợp lệ), đồng thời chỉ chặn các danh từ chỉ metric/tiền tệ đã được đối chứng bằng **synthetic contrast tests** (ví dụ: `"bán được bao nhiêu tiền"` $\rightarrow$ `revenue`, `"bán được bao nhiêu đơn"` $\rightarrow$ `order_count` hoặc `unparsed`, trong khi `"bán được bao nhiêu phần/ly/cá"` $\rightarrow$ `quantity`).
  * **Sửa M1 bằng cách bảo toàn span/token gốc:** Trích xuất trực tiếp từ đơn vị có dấu tại đúng vị trí ngữ pháp của capture group trong câu gốc (đã chuẩn hóa NFC và casefold nhưng **chưa xóa dấu**), thay vì xóa dấu cả câu rồi quét lại `raw_words` toàn cục.

### 2.2. Điểm I2 (`validate_plan` vs `_capability`) — THU HỒI MỨC IMPORTANT BUG, CHUYỂN THÀNH DESIGN CLARIFICATION & PREFLIGHT HELPER
* **Phản biện lại chính nhận định Lượt 01 của Argon:**
  * Codex hỏi: *"Hãy chỉ ra hậu quả sai answer/accounting nếu vẫn coi separation tự nó là bug Important."*
  * **Trả lời thẳng:** Sau khi kiểm tra lại `queryplan/executor.py:59-67` và `verification/runner.py:67-98`, tôi xác nhận **KHÔNG có hậu quả sai answer hay sai lệch mẫu số (accounting) nào** khi giữ nguyên sự tách biệt giữa `validate_plan()` và `_capability()`.
  * Cụ thể:
    1. Trong `QueryExecutor.execute()`, nếu một plan vượt qua `validate_plan()` nhưng vi phạm `_capability()`, nó lập tức bị bắt ở dòng 66 (`except UnsupportedCapability`) và trả về `_abstain('unsupported_capability', 'capability', str(exc))` **trước khi chạm vào `Periods`, `SalesMetrics` hay dữ liệu**.
    2. Trong `verification/runner.py:86-96`, kết quả `abstain` này được `score_one` chấm là `'abstain'`, đưa vào `counts['abstained']`, giữ nguyên trong mẫu số `selected = compared + abstained + execution_errors`, và làm `verification_exit_code` trả về `1`.
    3. Trong `docs/capability-verification.md:45`, tài liệu cũng đã ghi trước: *"Một plan được chọn vẫn có thể bị executor từ chối capability, không resolve được, hoặc thiếu dữ liệu."*
* **Kết luận chốt I2:**
  * Việc tách **Structural/Semantic Schema Validation** (`validate_plan` $\rightarrow$ `invalid_plan`) và **v1 Execution Capability Check** (`_capability` $\rightarrow$ `unsupported_capability`) là **thiết kế có chủ ý và hợp lý**. Tôi **rút lại phân loại Important Bug cho I2**.
  * **Cách xử lý nhẹ nhàng nhất:**
    * Giữ nguyên `validate_plan(raw)` và giữ nguyên mẫu số `selected` của manifest.
    * Sửa chuỗi thông báo lỗi ở `verification/manifest.py:86` từ `'manifest plan must be normalized and executable'` thành `'manifest plan must be normalized and schema-valid'`.
    * Export hàm public `check_capability(plan)` (hoặc dùng lại `_capability`) để `verification/audit.py` ghi nhận thêm một trường metadata (ví dụ: `capability_status: "supported" | "unsupported_capability"`) khi kiểm tra các plan do AI đề xuất, giúp người đọc báo cáo phân biệt rõ plan chạy được ngay trên v1 với plan hợp lệ schema nhưng vượt ngưỡng capability v1.

### 2.3. Điểm I3 (Kỳ so sánh trong `revenue_growth`) — ĐỀ XUẤT CONTRACT NHỎ NHẤT (MINIMAL SPEC)
Codex phản hồi rất chuẩn xác:
1. Không được sửa nghĩa của `previous_month` hiện tại (vì `previous_month` trong `Periods` đang được định nghĩa là tháng trước của `as_of_date`).
2. Không được cấm cực đoan (blanket reject) mọi trường hợp `period` và `comparison_period` là hai mốc thời gian độc lập (ví dụ câu hỏi thực tế hoàn toàn có thể hỏi: *"Doanh thu tháng 3/2026 thay đổi bao nhiêu % so với tháng 1/2026?"* hoặc *"Doanh thu hôm nay tăng bao nhiêu % so với ngày 2026-03-01?"*).
3. Cần phân biệt rõ **3 khái niệm thời gian so sánh khác nhau** trong `Rulebook`:
   * **Loại 1 — Cùng số ngày ngay trước (`before_period`):** Độ dài $L = (\text{end} - \text{start}) + 1$ ngày, kết thúc vào $\text{start} - 1$ ngày. Hiện dùng cho dịp Tết (`periods.before(tet)`).
   * **Loại 2 — Cùng số ngày của tháng trước (`previous_month_same_elapsed`):** Dùng riêng khi `period.kind == 'this_month'` (từ ngày $1$ đến $\min(\text{as\_of.day}, \text{last\_day\_of\_prev\_month})$).
   * **Loại 3 — Tháng/Quý dương lịch liền trước của kỳ đang hỏi (`previous_calendar_month` / `previous_calendar_quarter` hoặc compile ở tầng tạo plan):** Ví dụ kỳ chính là Tháng 1/2024 ($01/01/2024 .. 31/01/2024$, 31 ngày) thì "tháng liền trước" là toàn bộ Tháng 12/2023 ($01/12/2023 .. 31/12/2023$, 31 ngày); nếu kỳ chính là Tháng 3/2024 (31 ngày) thì "tháng liền trước" là toàn bộ Tháng 2/2024 ($01/02/2024 .. 29/02/2024$, 29 ngày — **cả tháng dương lịch**, không phải 31 ngày lùi về trước như `before_period`).

**Đề xuất Contract Nhỏ nhất cho I3 (Để giải quyết cả năm tường minh, năm ngầm định và biên Năm 1):**

Để không làm xáo trộn 10 API của `business/` và giữ `validate_plan` đơn giản, có 2 phương án thiết kế sạch. Tôi khuyến nghị **Phương án I3-A (Thêm 2 comparison kinds neo lịch vào `queryplan`)** vì nó giải quyết triệt để bài toán **năm ngầm định (implicit year)** mà không bắt `select_question(text)` phải nhận thêm tham số `as_of_date` hay `rulebook`:

* **Đặc tả Phương án I3-A (Minimal Contract Extension):**
  1. **Giữ nguyên** mọi `PERIOD_KINDS` và các `COMPARISON_KINDS` hiện có (`yesterday`, `previous_week`, `previous_month`, `previous_month_same_elapsed`, `month`, `quarter`, `tet`, `date_range`, `before_period`). Không chặn các câu hỏi có 2 mốc độc lập (ví dụ `month(3, 2026)` so với `month(1, 2026)`).
  2. **Thêm** `'previous_calendar_month'` và `'previous_calendar_quarter'` (hoặc gộp thành `'previous_calendar_period'`) vào `COMPARISON_KINDS` trong `queryplan/contract.py` (không dùng tham số phụ, tất cả `n, month, quarter, year, start_date, end_date` đều phải `null`).
  3. **Kiểm tra ở `_capability(plan)` (`queryplan/executor.py`):**
     * Nếu `comparison['kind'] == 'previous_calendar_month'` mà `plan['period']['kind'] != 'month'`: raise `UnsupportedCapability`.
     * Nếu `comparison['kind'] == 'previous_calendar_quarter'` mà `plan['period']['kind'] != 'quarter'`: raise `UnsupportedCapability`.
     * **Chặn lỗi neo nhầm `as_of_date`:** Nếu `plan['period']['kind'] in ('month', 'quarter', 'tet', 'date_range')` (kỳ cố định không neo vào `as_of`) mà `comparison['kind'] in ('yesterday', 'previous_week', 'previous_month', 'previous_month_same_elapsed')` (kỳ tương đối neo vào `as_of`): raise `UnsupportedCapability('Kỳ cố định không so sánh với kỳ tương đối theo as_of_date; hãy dùng mốc tường minh hoặc previous_calendar_*')`. *(Lưu ý: Nếu thực tế có câu hỏi "Doanh thu tháng 1/2026 so với tháng trước của hôm nay", cách diễn đạt tiếng Việt "so với tháng trước" đi sau "tháng 1/2026" luôn có nghĩa là tháng 12/2025 chứ không bao giờ là tháng 2/2026).*
  4. **Thực thi ở `resolve_period(spec, periods, primary)` (`queryplan/resolution.py`):**
     * Vì `primary` (`DateRange` của `plan['period']`) **đã được resolve xong trước đó** (nghĩa là nếu `plan['period']` là `month(1, year=None)`, `periods.month(1, None)` đã dùng `as_of_date` và `Rulebook.implicit_year()` để tính ra `primary.start = date(resolved_year, 1, 1)`!):
     * Với `'previous_calendar_month'`:
       * Kiểm tra biên ở `_period_bounds`: nếu `primary.start.year == 1 and primary.start.month == 1` $\rightarrow$ raise `PeriodResolutionError('comparison would precede year 1')`.
       * Tính tháng trước từ `primary.start`:
         ```python
         prev_end = primary.start - timedelta(days=1)
         return periods.month(prev_end.month, prev_end.year)
         ```
     * Với `'previous_calendar_quarter'`:
       * Kiểm tra biên ở `_period_bounds`: nếu `primary.start.year == 1 and primary.start.month <= 3` $\rightarrow$ raise `PeriodResolutionError('comparison would precede year 1')`.
       * Tính quý trước từ `primary.start`:
         ```python
         prev_end = primary.start - timedelta(days=1)
         prev_q = (prev_end.month - 1) // 3 + 1
         return periods.quarter(prev_q, prev_end.year)
         ```
* **Tại sao Phương án I3-A là tối ưu nhất?**
  * `select_question(text)` vẫn **thuần túy nhận `text: str`** (không cần truyền `as_of_date` hay `rulebook` vào selector!).
  * Khi gặp câu *"Doanh thu tháng 1 tăng bao nhiêu phần trăm so với tháng trước?"* (năm ngầm định) hoặc *"Doanh thu tháng 1/2024 tăng bao nhiêu % so với tháng liền trước?"* (năm tường minh), selector/NLU chỉ cần sinh `period={'kind': 'month', 'month': 1, 'year': ...}` và `comparison_period={'kind': 'previous_calendar_month', ...}`. Mọi phép toán lùi năm (`2024-01` $\rightarrow$ `2023-12`), suy luận năm ngầm định và kiểm tra biên `0001-01` đều được `resolve_period` xử lý tất định 100%!

### 2.4. Điểm I4 (`resolve_filters` và `calendar.csv`) — HẠ MỨC ĐỘ TỪ IMPORTANT XUỐNG LOW (NON-BLOCKING ROBUSTNESS)
* **Đối chiếu với phản chứng của Codex:**
  1. Trong `QueryExecutor.execute()` (`queryplan/executor.py:78-80`), `SalesMetrics(self.tables, self.rules, self.as_of)` luôn chạy ở `stage = 'data'` **trước** khi `resolve_filters(...)` chạy ở `stage = 'resolve'`. Do đó, mọi lỗi thiếu cột `ngay_dat` hoặc giá trị `ngay_dat` không parse được đều đã bị `SalesMetrics.__init__` chặn và ném `DataError`, được `QueryExecutor` chuyển thành `data_error`/`abstain` đúng thiết kế. Hơn nữa, docstring của `resolve_filters` (`resolution.py:55-56`) đã ghi rõ tiền điều kiện: *"Caller must validate the canonical table envelope/order dates with SalesMetrics first."*
  2. Về `csv.DictReader(..., strict=True)` trong `_validate_tet_calendar` (`resolution.py:96-101`): Codex hoàn toàn đúng. Khi một dòng dữ liệu có nhiều ô hơn dòng header, `DictReader` gán các ô thừa vào `row[None]` (dạng `list`), còn `reader.fieldnames` vẫn giữ nguyên danh sách chuỗi của dòng đầu tiên (không chứa `None`), và vòng lặp `for f in fields:` chỉ đọc đúng 5 cột bắt buộc trong `fields`. Do đó, `_validate_tet_calendar` **không bị crash** bởi dòng thừa cột hay thiếu header.
* **Kết luận chốt I4:**
  * Tôi **rút lại mức Important của I4** và xác nhận **không có lỗi crash nào trong `QueryExecutor`**.
  * Chỉ ghi nhận ở mức **Low / Optional Clean-up** (không phải gate chặn): Việc `SalesMetrics.__init__` và `resolve_filters` cùng gọi `pd.to_datetime(orders['ngay_dat'])` là parse lặp lại 2 lần trên cùng một bảng trong mỗi lần `execute()`, và `Periods.tet()` khi gọi trực tiếp bên ngoài `QueryExecutor` không có lớp kiểm tra CSV như `_validate_tet_calendar`. Có thể giữ nguyên như hiện tại để tránh chạm vào `business/`.

### 2.5. Điểm M2 & L1 (`evaluate.py::map_columns`, `inventory_capabilities.py`, `test_evaluate.py`) — ĐỒNG THUẬN GHI NHẬN, KHÔNG CHẶN
* **M2 (`map_columns` trong `evaluate/evaluate.py:139-151`):** Cảm ơn Codex đã chạy probe xác nhận `[A, B]` với pred headers `[B, Other]` tạo `mapping = [0, 0]` khiến `pred row [1, 999]` vẫn được chấm `correct` khi so với `gold row [1, 1]`. Vì 10 API của v1 không trả về `table` và `evaluate.py` là bộ chấm tham chiếu theo spec BTC, hoàn toàn đồng ý **không tự ý sửa `evaluate.py`** lúc này mà chỉ ghi nhận vào tài liệu kỹ thuật.
* **L1:** Ghi nhận rằng `inventory_capabilities.py` khi gặp file đã tồn tại sẽ `parser.error` (exit 2, không ghi đè), và helper test trong `evaluate/` đã được gắn marker `local_data`. Tôi đóng điểm L1 tại đây.

---

## 3. Đính chính Phương pháp Luận & Số liệu Thực tế (Rút kinh nghiệm từ Lượt 01)

Tôi hoàn toàn tiếp thu và cập nhật lại 6 nguyên tắc phương pháp luận mà Codex đã chỉ ra để đảm bảo các bước tiếp theo không phạm sai lầm thiết kế:

1. **Quy mô tập Train thực tế:** Tập `train` chỉ có **30 doanh nghiệp** (con số 44 là tổng cả `train` + `public_test` từng chạy qua `loader`). Tuyệt đối **không dùng `public_test` để chia split hay tuning**, và sửa lại mọi đề xuất chia split về đúng quy mô **30 doanh nghiệp của `train`**.
2. **Bản chất của Split trên Train:**
   * Vì toàn bộ 30 doanh nghiệp trong `train` đã được khảo sát schema/loader và chạy qua các vòng kiểm chứng trước, bất kỳ phép chia nào trên 30 doanh nghiệp này đều là **đánh giá hồi cứu / cross-validation nội bộ (retrospective dev split)**, **không được gọi là "blind validation" hay "unseen holdout"**.
   * Cần phân biệt **Business-disjoint** (chia theo `business_id`) với **File-family disjoint** (chia theo họ cấu trúc bảng/nguồn dữ liệu từ `A` đến `J`). Nếu nhiều `business_id` dùng chung một template/file-family `A–J`, việc chỉ chia theo `business_id` vẫn có giao thoa về đặc trưng dữ liệu. Mọi dictionary/artifact sinh ra từ dữ liệu phải được đóng gói theo đúng fold.
3. **Không suy diễn trần lợi ích từ `13 multiple_filter_scopes`:** Con số 13 chỉ là các câu rơi vào nhánh `len(shifts) > 1 or repeated` của bộ lọc regex hiện tại trong `selection.py` (vốn chỉ nhận diện được filter khi nằm trong dấu nháy kép hoặc `ca sáng/chiều`). Trong `2190` câu của bucket `unrecognized_operation_or_scope` và `33` câu của `unrecognized_comparison` vẫn có các câu cần 2 filter scopes (như chính mẫu audit 10 câu `unrecognized_comparison` đã phát hiện thêm 1 ca so sánh 2 ca trong cùng kỳ). Do đó, tôi **rút lại phép tính $13/3000 = 0.43\%$**.
4. **Không hiểu nhầm giao thoa giữa `125` (verifier v2) và `409` (legacy):**
   * Verifier legacy (`verify_business.py`) chỉ kiểm tra 3 phép tính (`revenue`, `cancelled_orders`, `quantity`).
   * Trong khi đó, `verification_v2` của verifier mới có: `cancellation_rate` (22), `order_count` (7), `average_order_value` (14), `revenue_growth` (4) — tổng cộng **47/125 câu đã chấm nằm ở 4 phép tính mà verifier legacy hoàn toàn không hỗ trợ**. Do đó, ít nhất 47 câu này chắc chắn nằm ngoài tập 409. Tôi **rút lại nhận định suy đoán rằng "gần như toàn bộ 125 câu nằm trong 409"**; chỉ báo cáo số thực đo hoặc đo giao trực tiếp bằng ID khi cần.
5. **Ý nghĩa của mục tiêu 10/10 API trên tập Train:**
   * Đây là **mục tiêu mở rộng độ phủ kiểm chứng (diagnostic coverage goal)** thông qua việc mở grammar hợp lệ từ các mẫu câu hỏi, đóng băng manifest **trước** khi chấm và giữ nguyên mọi mismatch/abstain. Tuyệt đối không phải là "quota chọn câu theo kết quả khớp gold", và không lấy số dòng code (như "30 dòng regex") hay thời lượng phiên làm thước đo tính đúng đắn.
6. **Không tuyên bố quá mức về Hash, Latency và Constrained Decoding:**
   * Hash SHA256 hiện kiểm tra trước và sau khi replay, chưa phải cơ chế khóa tệp nguyên tử (atomic filesystem lock/snapshot) cho mọi bảng parquet hay module Python.
   * Gói bàn giao không có số đo benchmark thời gian chạy ("vài giây") hay thông số phần cứng đích.
   * Constrained decoding chỉ ép đầu ra tuân thủ **cú pháp JSON Schema**, hoàn toàn không đảm bảo model chọn đúng `operation`, đúng `period` hay đúng ngữ nghĩa câu hỏi.

---

## 4. Các Tests Phân định (Synthetic Discriminating Tests) Cần Bổ sung

Dưới đây là bộ synthetic tests cụ thể để phân định rõ các ca sửa lỗi ở bước tiếp theo mà vẫn bảo toàn 100% API, error stage và mẫu số:

```python
import pytest
from verification.selection import select_question
from queryplan import QueryExecutor, validate_plan
from queryplan_fixtures import plan, period_spec

# 1. Phân định C1: Intent tiền/doanh thu vs Đơn vị số lượng (Contrast Set)
@pytest.mark.parametrize("text,expected_selection,expected_op,expected_unit,expected_shift", [
    # Các câu hỏi về tiền -> phải vào revenue, không được vào quantity(unit='tiền')
    ("Tháng 9/2024 ca sáng bán được bao nhiêu tiền?", "selected", "revenue", None, "sang"),
    ("Tháng này thu được bao nhiêu tiền?", "selected", "revenue", None, None),
    # Các câu hỏi đơn vị hàng hóa hợp lệ có dấu -> giữ nguyên quantity và dấu
    ("Bán được bao nhiêu phần trong tháng 9/2024?", "selected", "quantity", "phần", None),
    ("Bán được bao nhiêu ly mặt hàng \"Cà phê\" tháng này?", "selected", "quantity", "ly", None),
])
def test_money_intent_vs_quantity_unit_contrast(text, expected_selection, expected_op, expected_unit, expected_shift):
    res = select_question(text)
    assert res["selection"] == expected_selection
    assert res["plan"]["operation"] == expected_op
    assert res["plan"]["filters"]["unit_mention"] == expected_unit
    assert res["plan"]["filters"]["shift"] == expected_shift


# 2. Phân định C1-đối kháng: "bán được bao nhiêu đơn" không được lọt vào quantity(unit='đơn')
@pytest.mark.parametrize("text", [
    "Tháng 9/2024 bán được bao nhiêu đơn?",
    "Tháng này bán được bao nhiêu khách?",
])
def test_non_unit_nouns_never_select_as_quantity_unit(text):
    res = select_question(text)
    if res["selection"] == "selected":
        assert res["plan"]["operation"] != "quantity"
        assert res["plan"]["filters"]["unit_mention"] is None


# 3. Phân định M1: Đơn vị có dấu không bị nhiễu bởi từ khác trùng hình không dấu trong câu
@pytest.mark.parametrize("text,expected_unit,expected_shift", [
    ("Ca sáng tháng 9/2024 bán được bao nhiêu cá?", "cá", "sang"),
    ("Ca chiều tháng này bán được bao nhiêu ca?", "ca", "chieu"),
    ("Tháng này mặt hàng \"Hợp tác\" bán được bao nhiêu hộp?", "hộp", None),
])
def test_unit_spelling_extracted_by_span_without_false_ambiguity(text, expected_unit, expected_shift):
    res = select_question(text)
    assert res["selection"] == "selected"
    assert res["plan"]["operation"] == "quantity"
    assert res["plan"]["filters"]["unit_mention"] == expected_unit
    assert res["plan"]["filters"]["shift"] == expected_shift


# 4. Phân định I3: Kỳ so sánh tương đối neo vào kỳ chính (tháng 1 lùi về tháng 12 năm trước, năm ngầm định, và biên năm 1)
def test_relative_previous_calendar_month_and_bounds(tables, rules):
    # Giả sử bổ sung kind='previous_calendar_month' cho comparison_period khi period.kind=='month'
    from queryplan.resolution import resolve_period
    from business import Periods, DateRange

    periods = Periods(rules, "2026-03-04")
    # 4a. Năm tường minh: Tháng 1/2024 -> kỳ chính 2024-01, kỳ so sánh 2023-12
    main_jan = resolve_period(period_spec("month", month=1, year=2024), periods)
    comp_dec = resolve_period(period_spec("previous_calendar_month"), periods, primary=main_jan)
    assert main_jan == DateRange("2024-01-01", "2024-01-31")
    assert comp_dec == DateRange("2023-12-01", "2023-12-31")

    # 4b. Năm ngầm định (implicit year): as_of = 2026-03-04, hỏi "Tháng 12" (không năm -> 2025-12)
    # Kỳ so sánh liền trước -> 2025-11
    main_implicit = resolve_period(period_spec("month", month=12, year=None), periods)
    comp_implicit = resolve_period(period_spec("previous_calendar_month"), periods, primary=main_implicit)
    assert main_implicit == DateRange("2025-12-01", "2025-12-31")
    assert comp_implicit == DateRange("2025-11-01", "2025-11-30")

    # 4c. Biên năm 1: Tháng 1/0001 -> kỳ so sánh lùi về năm 0 -> phải báo period_error (abstain)
    raw_bound = plan(
        "revenue_growth",
        period=period_spec("month", month=1, year=1),
        comparison_period=period_spec("previous_calendar_month"),
    )
    res_bound = QueryExecutor(tables, rules, "2026-03-04").execute(raw_bound)
    assert (res_bound.status, res_bound.stage, res_bound.answer.type) == ("period_error", "period", "abstain")
```

---

## 5. Chốt Đúng Hai Task Nhỏ Nhất Tiếp Theo (Minimal Actionable Tasks)

Thay vì mở một lộ trình dài hoặc tích hợp model khi chưa chốt xong các mẫu câu cơ bản đã audit, tôi thống nhất với hướng tiếp cận thận trọng của Codex và đề xuất **đúng 2 task nhỏ nhất, khép kín và kiểm chứng được ngay**:

### Task 1: Sửa lỗi Intent Tiền / Span Đơn vị (C1, M1) và Preflight Metadata cho Audit (I2)
* **Phạm vi sửa đổi tối thiểu:**
  1. `verification/selection.py`:
     * Nhận diện đúng mẫu câu hỏi doanh thu dùng từ `"tiền"` (như `"bán/thu được bao nhiêu tiền"`) về `operation='revenue'`.
     * Ngăn các danh từ chỉ đơn hàng/khách/tiền tệ bị bắt nhầm vào `unit_mention` của `quantity` (kèm contrast tests giữ nguyên các đơn vị hợp lệ có dấu như `"phần"`, `"ly"`, `"hộp"`, `"cá"`).
     * Trích xuất `unit_mention` trực tiếp từ span tương ứng trên chuỗi giữ dấu (NFC + casefold) thay vì dò tìm toàn cục trên `raw_words`, triệt tiêu lỗi `ambiguous_unit_spelling` giả tạo khi câu có từ `"Ca sáng"` hoặc từ trùng hình không dấu.
  2. `verification/manifest.py` & `verification/audit.py`:
     * Sửa thông báo lỗi ở `manifest.py:86` cho chuẩn xác với vai trò của `validate_plan()`.
     * Thêm kiểm tra preflight nhẹ (hoặc hàm `check_capability`) trong công cụ audit để gắn nhãn phân biệt rõ: plan hợp lệ cả schema lẫn capability v1 vs plan vướng giới hạn capability/resolution, **nhưng không sửa đổi tập mẫu 41 câu đã đóng băng ở `audit_v1`**.
* **Acceptance Checks:**
  * Toàn bộ unit tests hiện có + bộ synthetic tests phân định C1/M1 mới đều PASS.
  * Tạo manifest mới (ví dụ `manifest_v3.json`) và chạy `verify_queryplans.py`: Xác nhận ca abstain do nhầm `"tiền"` thành `quantity` ở v2 được giải quyết đúng ngữ nghĩa, mẫu số `total = selected + outside_selection` và `selected = compared + abstained + execution_errors` được bảo toàn tuyệt đối.

### Task 2: Chốt Spec Neo Kỳ So Sánh (I3) & Mở rộng Có Kiểm Soát các Họ Grammar Đã Audit
* **Phạm vi sửa đổi tối thiểu:**
  1. `queryplan/contract.py`, `queryplan/executor.py`, `queryplan/resolution.py`:
     * Triển khai contract nhỏ nhất cho phép tính tăng trưởng so với tháng/quý dương lịch liền trước neo vào kỳ chính (như Phương án I3-A: hỗ trợ cả năm tường minh, năm ngầm định qua `primary`, chặn `year=1, month=1` thành `period_error`, vẫn cho phép so sánh 2 mốc độc lập tường minh và giữ nguyên nghĩa của `previous_month` neo theo `as_of_date`).
  2. `verification/selection.py`:
     * Mở rộng có kiểm soát các họ ngôn ngữ đã có căn cứ từ 22 ca `supported_plan` trong `audit_v1` (biến thể thời gian, so sánh neo kỳ, xếp hạng `top_products`/`top_customers`, và tỷ trọng `revenue_share` rõ scope).
     * Các mẫu câu cần 2 filter scopes (`multiple_filter_scopes`), câu hỏi trả về `string` đơn lẻ (scalar top-1) hoặc thuộc domain chưa hỗ trợ (công nợ, nhập hàng, lãi gộp) tiếp tục giữ ở trạng thái `unparsed` / `unsupported` rõ ràng.
* **Acceptance Checks:**
  * Mọi quy tắc grammar mở rộng đều phải có synthetic contrast tests (câu đúng nghĩa được chọn + câu gần giống nhưng lệch scope/nhiều điều kiện bị từ chối) trước khi chạm vào tập `train`.
  * Đóng băng manifest revision mới trước khi chạy `verify_queryplans.py`.
  * Báo cáo trung thực toàn bộ các con số thực đo (`selected`, `compared`, `matched`, `mismatch`, `abstained`, `execution_errors`) theo từng operation mà không loại bỏ bất kỳ câu nào sau khi nhìn kết quả chấm.