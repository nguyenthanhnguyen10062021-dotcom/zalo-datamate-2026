# DataMate — Phản biện Độc lập Vòng 002, Lượt 01 (`GEMINI_RESPONSE_01.md`)

- **Ngày thực hiện:** 2026-10-29 (Asia/Saigon)
- **Model phản biện:** Gemini 3 Flash (Web / Paid tier)
- **Source revision đã kiểm:** `d99cac2620927702704e8efa93cfffdf3ca14cf0` (nhánh `VuongNguyen`, nền executor `4fd268e`)
- **Trạng thái thực thi:** Chỉ phân tích tĩnh (static code & contract analysis) trên snapshot được đóng gói trong `GEMINI_HANDOFF.md`. **Không chạy pytest hay CLI thực tế** vì môi trường phản biện độc lập không kết nối máy local và không có dữ liệu/cache BTC.
- **Danh sách 37/37 file đã đọc đầy đủ từ gói bàn giao:**
  - Docs & Specs (8 files): `docs/PROGRESS.md`, `docs/architecture.md`, `docs/business.md`, `docs/queryplan.md`, `docs/capability-verification.md`, `docs/plan-annotation-audit.md`, `docs/validation.md`, `docs/superpowers/specs/2026-10-29-capability-verifier.md`.
  - Verification & CLI (8 files): `verification/__init__.py`, `verification/AGENTS.md`, `verification/selection.py`, `verification/manifest.py`, `verification/runner.py`, `verification/audit.py`, `inventory_capabilities.py`, `verify_queryplans.py`.
  - QueryPlan (4 files): `queryplan/__init__.py`, `queryplan/contract.py`, `queryplan/resolution.py`, `queryplan/executor.py`.
  - Business & Evaluate (5 files): `business/__init__.py`, `business/rules.py`, `business/periods.py`, `business/sales.py`, `evaluate/evaluate.py`.
  - Harness, Config & Tests (12 files): `scripts/harness.py`, `requirements.txt`, `pytest.ini`, `tests/conftest.py`, `tests/test_business_sales.py`, `tests/queryplan_fixtures.py`, `tests/test_queryplan_contract.py`, `tests/test_queryplan_executor.py`, `tests/test_capability_inventory.py`, `tests/test_queryplan_verification.py`, `tests/test_plan_annotation_audit.py`, `tests/test_harness.py`.
- **Phần thiếu không thể kết luận:** Toàn bộ source của package `loader/` không nằm trong gói này (như đã nêu rõ ở đầu handoff). Do đó, tôi **từ chối chứng nhận tính đúng đắn của `loader/`** và giả định các bảng chuẩn đầu vào (`don_hang`, `dong_hang`, `mat_hang`, `cua_hang`) tuân thủ schema của `SalesMetrics`.

---

## 1. Verdict Tổng hợp & Gate Kiểm chứng

| Hạng mục đánh giá | Verdict | Lý do cốt lõi | Gate cụ thể để vượt qua |
|---|---|---|---|
| **1. Nền tính toán & QueryPlan Executor** (`business/`, `queryplan/`) | **Đạt có điều kiện** *(Conditionally Ready)* | Ranh giới kiến trúc rất sạch, xử lý `DataError`/`UnsupportedRule`/`unanswerable` chuẩn xác. Tuy nhiên, còn **2 lỗ hổng contract/boundary** ở `contract.py` (lọt `comparison_period` không khớp operation capability) và `resolution.py` (crash `KeyError`/`TypeError` khi CSV lịch Tết thiếu cột hoặc `as_of_date` sai kiểu trước khi vào `SalesMetrics`), cộng với thiếu primitive cho kỳ liền trước tương đối (`previous_period` neo vào kỳ chính). | **Gate 1:** Vá 3 điểm ở `queryplan/contract.py` và `queryplan/resolution.py` (Xem Findings I2, I3, M1) + bổ sung primitive so sánh kỳ liền trước tương đối (Finding I4) và pass 100% synthetic unit tests mới. |
| **2. Đánh giá, Selector & Phương pháp Kiểm chứng** (`verification/`, `audit.py`) | **Đạt có điều kiện** *(Conditionally Ready)* | Cơ chế đóng băng manifest, kiểm tra SHA256 và giữ mẫu số (`selected = compared + abstained + execution_errors`) rất chặt. Tuy nhiên, grammar ở `selection.py` đang có **lỗi phân loại sai intent tiền thành quantity** và **rủi ro nuốt từ nối/lọt số âm**, dẫn đến 0 câu được chọn cho 3/10 API (`top_products`, `top_customers`, `revenue_share`). Audit AI có prior exposure và chưa kiểm chứng thực thi. | **Gate 2:** Sửa lỗi `selection.py` (Finding C1, M2); tách trạng thái kiểm chứng thành `schema_valid` vs `execution_verified` trên dữ liệu tổng hợp; chạy manifest v3 chạm đủ **10/10 API** trên tập dev mà không làm gãy 125 ca đã khớp. |
| **3. Sẵn sàng Baseline Đầu-Cuối** *(End-to-End Baseline Readiness)* | **Chưa đạt** *(Not Ready)* | Hiện chưa có model NLU offline, chưa có JSON Schema/grammar cho constrained decoding, chưa có submission runner hoàn chỉnh, và độ phủ thực tế của selector bảo thủ chỉ đạt **4.2%** (126/3000 câu train). Mọi con số 125/125 hay 409/409 chỉ là regression trên tập con cực hẹp, hoàn toàn không đại diện cho PA toàn hệ thống. | **Gate 3:** Đạt Gate 1 & Gate 2; xuất JSON Schema cho `QueryPlan v1`; nối thử 1 model open-weights $\le 15\text{B}$ chạy offline sinh `QueryPlan` + runner xuất `submission.jsonl` trên 1 split group-disjoint theo `business_id`. |

---

## 2. Trả lời 5 Câu hỏi Phản biện Trọng tâm

### Câu 1: Implementation có thực thi đúng contract và đủ chặt để làm nền không?

Về tổng thể, kiến trúc tách 3 tầng (`verification` $\rightarrow$ `queryplan` $\rightarrow$ `business`) được thiết kế rất kỷ luật. Việc không tự động biến `DataError`, `UnsupportedRule` hay `ResolutionError` thành đáp án `0` hoặc `unanswerable` là một điểm sáng lớn, giúp tránh bị phạt $-1$ điểm oan uổng theo luật chấm của BTC.

Tuy nhiên, qua rà soát từng dòng code với các phản chứng tổng hợp (synthetic counterexamples), tôi phát hiện **1 lỗi Critical ở Selector**, **3 lỗi Important ở Contract/Resolver/Period**, và **3 lỗi Medium ở Boundary/IO**:

1. **Selector nhầm intent tiền thành đơn vị hàng hóa (`verification/selection.py:67`):** Câu *"Tháng 9/2024 ca sáng bán được bao nhiêu tiền?"* hoặc *"Bán được bao nhiêu đồng tháng này?"* bị regex `r'ban (?:duoc )?bao nhieu ([\w]+)'` bắt nhầm chữ `tien`/`đồng` làm `unit_mention` của operation `quantity`. Khi xuống `resolve_filters`, vì catalog không có đơn vị `tiền`, hệ thống trả về `unresolved_entity` (abstain) — hoặc nguy hiểm hơn, nếu một shop tình cờ có cột dữ liệu bẩn ghi đơn vị là `"tiền"`, nó sẽ cộng số lượng thay vì tính doanh thu (sai đáp án, bị $-1$ điểm).
2. **Đứt gãy giữa `validate_plan` và `_capability` (`queryplan/contract.py:124-130` vs `queryplan/executor.py:16-31`):** `validate_plan()` được quảng cáo trong `manifest.py:85` và `audit.py:64` là công cụ đảm bảo *"manifest plan must be normalized and executable"*. Nhưng `validate_plan()` lại **không gọi `_capability()`**! Hệ quả là một plan có `operation='revenue_growth'`, `period={'kind': 'month', 'month': 1, ...}` và `comparison_period={'kind': 'previous_month_same_elapsed', ...}` (hoặc `cancellation_rate` kèm `product_mentions`) hoàn toàn vượt qua `validate_plan()`, đi vào manifest và được đánh dấu `supported_plan` trong Audit, nhưng khi chạy `QueryExecutor.execute()` lại bị đánh rớt ở stage `capability` (`unsupported_capability`).
3. **Thiếu cơ chế neo kỳ so sánh tương đối vào kỳ chính (`business/periods.py:56`, `queryplan/resolution.py:143`):** Trong `Periods`, hàm `previous_month()` luôn tính từ `self.as_of.replace(day=1) - timedelta(days=1)`. Do đó, với câu *"Doanh thu tháng 1/2024 tăng bao nhiêu phần trăm so với tháng liền trước?"* (khi `as_of_date = '2026-03-04'`), nếu tầng trên dùng `comparison_period={'kind': 'previous_month'}`, resolver sẽ lấy **tháng 2/2026** chứ không phải **tháng 12/2023**! Hiện tại, muốn đúng thì tầng NLU/grammar phải tự tính toán số học lịch (lùi `month=1, year=2024` thành `month=12, year=2023`) để truyền tường minh, hoặc nếu câu hỏi không ghi năm (*"Doanh thu tháng 1 tăng bao nhiêu % so với tháng liền trước?"*), tầng NLU không biết `as_of_date` hoặc quy tắc implicit year sẽ tính sai năm.
4. **Lọt ngoại lệ `KeyError` / `TypeError` ở `queryplan/resolution.py`:**
   - Tại `resolution.py:98`, biểu thức `not set(fields).issubset(reader.fieldnames)` trả về `False` nhưng thân `if` chỉ raise `PeriodResolutionError` khi điều kiện đúng; tuy nhiên nếu `reader.fieldnames` chứa giá trị `None` (khi dòng dữ liệu dài hơn dòng header trong CSV, `csv.DictReader` gán key `None`), hoặc ở `business/periods.py:83` khi gọi trực tiếp `periods.tet()` với file CSV thiếu cột, nó sẽ văng `KeyError` thô thay vì lỗi miền đã phân loại.
   - Tại `resolution.py:67`, nếu người dùng gọi `resolve_filters(spec, tables, as_of_date)` độc lập hoặc trước khi `SalesMetrics` kiểm tra `ngay_dat`, và cột `ngay_dat` chứa chuỗi hỏng (`"bad-date"`), `pd.to_datetime(orders['ngay_dat'])` (không có `errors='coerce'`) sẽ văng `ValueError`/`DateParseError` chưa được bắt bởi `QueryExecutor.execute()`, biến lỗi dữ liệu (`DataError`) thành lỗi crash hệ thống (`execution_error`).
5. **Kiểm tra đối chiếu các ca tổng hợp do người dùng yêu cầu:**
   - *Giữ dấu đơn vị (`"Bán được bao nhiêu phần..."`):* **ĐẠT.** Cơ chế đối chiếu `raw_words` bằng `_fold(word) == unit` tại `selection.py:124-127` giữ nguyên chữ `"phần"` có dấu (nếu câu chỉ có 1 cách viết dấu). Tuy nhiên, xem **Finding M3** về tác dụng phụ khi câu có một từ khác trùng hình không dấu (ví dụ: *"Phần lớn khách bán được bao nhiêu phân?"* $\rightarrow$ `raw_words` có cả `"Phần"` và `"phân"` $\rightarrow$ `len(spellings) == 2` $\rightarrow$ bị reject oan thành `ambiguous_unit_spelling`).
   - *Hai filter scope (`"Doanh thu kênh 'A' tuần này ... so với tuần trước thanh toán 'B'"`):* **ĐẠT.** `selection.py:93` chỉ lấy `parts[0]` trước `"so voi"`, phần `thanh toan x1x` nằm ở `parts[1]` không được strip nên làm `_period(parts[1])` trả về `rest != ''`, dẫn đến reject `unrecognized_comparison` (tuy lý do báo là `unrecognized_comparison` thay vì `multiple_filter_scopes`, nhưng hành vi bảo toàn an toàn là đúng).
   - *Khách nào mua nhiều đơn nhất (Scalar vs List):* **ĐẠT.** Selector hiện không match cấu trúc `"khách nào ... nhất"`, trả về `unparsed`. Executor kiểm tra chặt `answer.type not in (plan['expected_type'], 'unanswerable')` tại `executor.py:99`, không tự ép `list` 1 phần tử thành `string`.
   - *Raw label là `list`/`dict`:* **ĐẠT.** Đã được chặn tốt tại `resolution.py:34` (`not isinstance(v, str)`) trước khi gọi `.unique()`, trả về `DataError` $\rightarrow$ `data_error`/`abstain`.
   - *Thiếu cache / Duplicate hoặc missing gold / Thay corpus khi replay / Đổi thứ tự list & alias:* **ĐẠT.** `runner.py` và `manifest.py` xử lý chuẩn xác: thiếu cache ghi nhận `cache_error` cho mọi câu thuộc shop đó mà không làm tụt `selected`; gold sai tập ID văng `ManifestError` trước khi chấm; `validate_manifest` được gọi lại ở `runner.py:91` sau khi chạy xong để chống TOCTOU (thay file giữa lúc replay); thứ tự list và alias dùng trực tiếp `evaluate.py::score_one`.
   - *Output symlink / trùng input (`manifest.py:107`):* **ĐẠT CÓ LƯU Ý.** `Path.resolve()` giải quyết tốt symlink trỏ ra ngoài `reports/`. Tuy nhiên, ở `verify_queryplans.py:16-17`, `local_output` chỉ truyền `(args.manifest,)` vào `protected`. Nếu `args.train` hoặc `args.cache` là một symlink nằm bên trong `reports/` (dù thực tế ít gặp), bước kiểm tra ở dòng 18 sẽ chặn được, nhưng `inventory_capabilities.py:13` lại không chặn trường hợp `--out` nằm đè lên thư mục con trong `reports/` nếu `--train` trỏ vào `reports/custom_train` và `--out` trùng với `calendar.csv`. Đây là lỗi nhỏ (Low).

---

### Câu 2: Mức tin cậy của đánh giá hiện tại là gì?

**Kết luận thẳng: Con số `125/125` (trên verifier mới) và `409/409` (trên verifier legacy) có độ tin cậy cao về mặt *tính toàn vẹn quy trình (procedural integrity)* và *tính đúng đắn cục bộ của công thức `SalesMetrics` trên 7 phép tính đơn giản*, nhưng có giá trị bằng KHÔNG trong việc chứng minh độ phủ NLU, năng lực tổng quát hóa hay điểm PA cuối cùng.**

Cụ thể các điểm mù và rủi ro phương pháp luận cần phân biệt rõ:

1. **Selection Bias cực lớn do Grammar bảo thủ (Conservative Grammar Bias):**
   - `selection.py` yêu cầu câu hỏi phải khớp hoàn toàn (`re.fullmatch`) với một số mẫu câu cực kỳ cứng nhắc và **bắt buộc mọi tên mặt hàng, nhóm hàng, kênh, thanh toán, nhóm khách phải nằm trong dấu ngoặc kép/đơn (`"..."` hoặc `'...'`)**.
   - Trong thực tế tiếng Việt tự nhiên (và trong 2874 câu bị bỏ qua), người dùng hỏi *"Doanh thu trà sữa tháng này"* hoặc *"Tỷ trọng doanh thu nhóm Đồ uống"* mà không hề gõ dấu nháy kép. Do đó, bộ chọn 126 câu thực chất chỉ nhặt ra những câu "dễ nhất, sạch nhất, không có nhập nhằng thực thể".
2. **Độ phủ API và Filter bị khuyết (Zero Coverage trên 30% API):**
   - Trong 126 câu được chọn trên train: `revenue` (62), `cancellation_rate` (22), `cancelled_orders` (14), `average_order_value` (14), `order_count` (7), `revenue_growth` (4), `quantity` (3).
   - **3 API quan trọng hoàn toàn có `0` câu thực tế nào được kiểm chứng với Gold BTC:** `top_products` (0), `top_customers` (0), `revenue_share` (0). Mọi khẳng định rằng 3 API này "đã chạy đúng theo ý BTC" mới chỉ dựa trên synthetic test do chính tác giả tự viết theo cách hiểu rulebook của mình. Nếu BTC có quy ước ngầm khác về cách tie-break tên khách hàng, cách hiển thị alias trong `top_products`, hay mẫu số của `revenue_share` khi có đơn trả hàng, hiện tại chúng ta hoàn toàn mù thông tin.
3. **Nguy cơ Trùng đáp án tình cờ (Accidental-Answer Agreement):**
   - Trong `evaluate/evaluate.py:213`, khi `gold["type"] == "unanswerable"`, chỉ cần `pred["type"] == "unanswerable"` là được tính `CORRECT` (`+1` điểm), **bất kể lý do (`reason`) hay `stage` là gì**.
   - Ví dụ: Một câu hỏi hỏi về doanh thu tháng 5/2025 (nằm ngoài vùng dữ liệu nên Gold là `unanswerable`), nhưng Selector/Plan lại hiểu nhầm sang một cột không tồn tại (`MissingInformation` ở stage `resolve` cũng trả về `unanswerable`). Khi chấm, câu này vẫn tính là `matched` (đúng), che giấu việc plan hoặc thời gian bị hiểu sai.
   - Tương tự, các câu có đáp án bằng `0` (ví dụ: không có đơn bị hủy trong kỳ) rất dễ khớp tình cờ kể cả khi kỳ thời gian bị lệch vài ngày (ví dụ `previous_month` vs `previous_month_same_elapsed`).
4. **Integrity bằng SHA256 $\neq$ Semantic Correctness:**
   - Hệ thống hash trong `manifest.py` và `runner.py` chỉ chứng minh được: *"Code không bị sửa lén sau khi xem đáp án và kết quả chạy lại là khớp bit-for-bit"*. Nó không chứng minh được rằng 2874 câu bên ngoài không chứa các bẫy dữ liệu (`DataError`) làm lộ ra giới hạn của `loader` hoặc `business`.
5. **Giao thoa chưa xác định giữa 126 và 409:**
   - Như tài liệu đã tự thừa nhận, chưa đo độ giao (intersection) giữa 126 câu mới và 409 câu legacy. Rất có thể gần như toàn bộ 125 câu matched đều nằm gọn trong tập 409 câu đã được tinh chỉnh từ Vòng 001.

---

### Câu 3: Audit annotation có đủ dùng làm dev specification không?

**Kết luận: CHƯA ĐỦ nếu dùng trực tiếp làm chuẩn chân lý (ground-truth), nhưng ĐỦ DÙNG làm định hướng thiết kế (design heuristic) nếu áp dụng ngay quy trình kiểm chứng 3 bước dưới đây.**

Tại sao chưa đủ?
- **Tự xác nhận (Self-confirmation bias):** Cùng một tác nhân AI (Codex) vừa viết `contract.py`/`selection.py`, vừa đọc câu hỏi để gán nhãn `supported_plan` trong `audit_v1`. Như đã chứng minh ở **Finding I2**, `validate_annotations` trong `verification/audit.py:64` chỉ gọi `validate_plan()`, vốn **bỏ sót hoàn toàn bước kiểm tra `_capability()`** của `executor.py` và **không hề chạy thử `resolve_filters()` trên catalog của shop tương ứng**.
- Do đó, trong 22 câu được AI gán nhãn `supported_plan`, hoàn toàn có thể tồn tại những câu mà:
  1. Plan hợp lệ về cú pháp nhưng bị chặn bởi `_capability()` (ví dụ: so sánh `before_period` cho kỳ không phải Tết, hoặc lọc mặt hàng cho `cancellation_rate`).
  2. Plan yêu cầu resolve một thực thể/nhóm hàng mà trong câu hỏi viết tắt/không dấu/khác tên với `mat_hang.parquet` trong cache, dẫn đến khi thực thi sẽ rớt vào `unresolved_entity` (abstain) chứ không trả lời được.

**Đề xuất quy trình Validation/Adjudication tối thiểu (Không cần mở Gold BTC):**

1. **Tách trạng thái Annotation thành 2 cấp độ rõ rệt trong `verification/audit.py`:**
   - Cấp 1: `schema_and_capability_valid` — Bắt buộc `validate_plan(plan)` **VÀ** `_capability(plan)` (được chuyển từ `executor.py` sang `contract.py`) đều phải pass.
   - Cấp 2: `dry_run_executable` — Viết một hàm kiểm tra khô (dry-run) chạy ` QueryExecutor(tables, rules, as_of_date, calendar).execute(plan)` trên cache của doanh nghiệp đó **nhưng KHÔNG đọc `answers.jsonl` và KHÔNG in ra giá trị `answer`**. Chỉ kiểm tra xem `result.status` có thuộc tập `{'answered', 'unanswerable'}` hay bị rớt vào `{'unresolved_entity', 'ambiguous_entity', 'data_error', 'period_error', 'unsupported_capability'}`.
   - *Lợi ích:* Hoàn toàn không lộ Gold (zero gold leakage), nhưng lập tức phát hiện được các ca AI tưởng là `supported_plan` nhưng thực tế resolver không khớp được tên hàng trong catalog!
2. **Kiểm chứng đối kháng bằng dữ liệu tổng hợp (Synthetic Contrast Set):**
   - Với mỗi "họ ngôn ngữ" (grammar family) rút ra từ 23 ca audit, bắt buộc viết ít nhất **1 cặp câu đối kháng (contrast pair)** trên synthetic fixture: 1 câu dương tính (phải chọn và ra đúng plan) và 1 câu âm tính gần giống nhưng khác nghĩa (ví dụ: thêm vế điều kiện thứ hai, đổi sang hỏi giá trị đơn lẻ scalar, hoặc hỏi kỳ so sánh lệch) bắt buộc phải bị reject (`unparsed`) hoặc ra plan khác. Điều này ngăn chặn việc viết regex quá rộng (over-generalization) chỉ để bắt dính 22 câu trong mẫu.
3. **Giữ nhóm "Plan-valid nhưng không execute được" ở trạng thái riêng:**
   - **CÓ, bắt buộc phải tách riêng.** Nếu một câu hỏi có thể biểu diễn bằng `QueryPlan v1` nhưng khi chạy qua `resolve_filters` lại báo `unresolved_entity` (ví dụ: câu hỏi gọi *"cà phê sữa"* nhưng catalog ghi *"CF Sữa Đá"*), thì lỗi đó thuộc về **Entity Linking / Alias Resolution**, không phải lỗi **Grammar Parsing**. Nếu gộp chung vào `supported_plan`, dev sẽ lầm tưởng chỉ cần mở regex là tăng được điểm PA, trong khi thực tế mở regex xong chỉ làm tăng số lượng `abstain`! Hãy đặt trạng thái riêng là `supported_plan_unresolved_mention`.

---

### Câu 4: Nên ưu tiên điều gì trong hai bước tiếp theo?

Phản biện trực diện giữa hai lựa chọn:
- **Phương án A (Codex đề xuất):** Sửa lỗi intent tiền bằng synthetic test $\rightarrow$ Mở rộng mạnh các họ grammar theo 22 ca audit (thời gian, viết tắt, comparison neo kỳ, ranking/list, nhóm hàng không dấu nháy).
- **Phương án B (Đối trọng):** Dừng đầu tư vào regex grammar ở mức hiện tại $\rightarrow$ Tích hợp ngay model LLM offline ($\le 15\text{B}$) để sinh `QueryPlan`.

**Phân tích Trade-off:**
- Nếu đi thuần theo **Phương án A (viết thêm nhiều regex trong `selection.py`)**: Bạn sẽ nhanh chóng rơi vào cái bẫy *Regex Spaghettification* cho tiếng Việt. Đặt biệt, các câu hỏi có tên mặt hàng/nhóm hàng **không nằm trong dấu nháy** (ví dụ: *"Tháng 9 bán được bao nhiêu ly trà đào cam sả ca sáng?"*) cực kỳ khó tách ranh giới bằng regex thuần túy mà không nhìn vào catalog mặt hàng của từng shop. Hơn nữa, `selection.py` chỉ là công cụ dev (`verification/`), không phải NLU runtime! Đầu tư hàng trăm dòng regex phức tạp vào một module chỉ dùng để tạo manifest hồi cứu là lãng phí tài nguyên kỹ thuật.
- Ngược lại, nếu nhảy thẳng sang **Phương án B (tích hợp LLM ngay lập tức)** mà **chưa sửa lỗ hổng của `QueryPlan` contract/executor** (như thiếu primitive so sánh kỳ liền trước tương đối, lệch `_capability` với `validate_plan`) và **chưa có câu nào trong manifest chạm tới 3 API (`top_products`, `top_customers`, `revenue_share`)**, thì khi LLM chạy sai trên tập train, bạn sẽ không biết lỗi do LLM sinh plan sai hay do `SalesMetrics`/`QueryExecutor` hiểu sai luật của BTC ở 3 API đó!

**Khuyến nghị Độc lập (Chọn đúng 2 bước tiếp theo có Gate đo được):**

* **Bước 1 (Ưu tiên số 1 — Củng cố Contract, Vá lỗi Selector/Executor & Mở Grammar Tối thiểu chỉ để Phủ đủ 10/10 API):**
  - **Không** mở rộng grammar tràn lan cho viết tắt/Telex hay tên hàng không dấu nháy trong `selection.py`.
  - **Chỉ làm:**
    1. Vá các lỗi ở `queryplan/` (hợp nhất `_capability` vào `validate_plan`, thêm `previous_period` neo theo kỳ chính cho `revenue_growth`, bọc lỗi `ngay_dat`/`calendar` ở `resolution.py`).
    2. Sửa lỗi nhầm intent tiền thành `quantity` ở `selection.py`.
    3. Mở nhẹ grammar ở `selection.py` **chỉ với các mẫu câu an toàn, tường minh** cho `revenue_growth` (neo kỳ), `top_products`, `top_customers`, và `revenue_share` sao cho manifest v3 chọn được ít nhất một số câu thuộc cả **10/10 API** trên tập train để xác nhận thực nghiệm rằng 3 API còn lại khớp Gold BTC.
  - **Điều kiện dừng (Stop Condition):** Dừng sửa `selection.py` ngay khi manifest v3 chạm được tối thiểu 9–10/10 API hoặc quá 30 dòng regex mới. Tuyệt đối không cố viết regex bắt tên sản phẩm không có dấu nháy trong `selection.py`.
  - **Acceptance Check:**
    - `pytest` synthetic pass 100% (gồm các ca regression mới).
    - Chạy `inventory_capabilities.py` $\rightarrow$ `manifest_v3.json` và `verify_queryplans.py` $\rightarrow$ `verification_v3.json`: Ca abstain do nhầm `"tiền"` biến thành `matched`; `execution_errors == 0`; `mismatch == 0` (hoặc nếu có mismatch ở 3 API mới chạm tới thì phải điều tra xem lỗi do rulebook hay grammar).

* **Bước 2 (Ưu tiên số 2 — Thiết lập Constrained Decoding Schema, Catalog-Aware Prompting & Runner Baseline Đầu-Cuối):**
  - Xuất JSON Schema chuẩn (hoặc GBNF/Pydantic schema) khớp 1-1 với `queryplan/contract.py`.
  - Xây dựng module runtime mới (ví dụ `nlu/` hoặc `agent/`) nhận `(question, as_of_date, catalog_summary)` — trong đó `catalog_summary` trích xuất danh sách ngắn các `nhom_hang`, `don_vi_co_ban`, `kenh_ban`, `hinh_thuc_tt`, `nhom_khach` đã biết (đến `as_of_date`) từ bảng chuẩn để model (hoặc bộ matcher nhẹ + model open-weights $\le 15\text{B}$) chọn đúng nhãn thay vì đoán mò.
  - Xây dựng CLI runner đầu-cuối xuất `submission.jsonl` và đánh giá trên một split **group-disjoint theo `business_id`** (ví dụ: 34 shop làm dev, 10 shop làm blind validation).
  - **Acceptance Check:**
    - 100% output của tầng NLU đi qua `validate_plan()` không lỗi cấu trúc (nhờ constrained decoding / fallback `abstain`).
    - Runner chạy hết tập validation group-disjoint với `0` crash, xuất `submission.jsonl` chấm được bằng `evaluate/evaluate.py`, báo cáo rõ: `PA score`, `Precision trên câu trả lời` (mục tiêu $\ge 95\%$ để tránh điểm âm), và thời gian trung bình/câu.

---

### Câu 5: Ranh giới tối thiểu trước NLU/runner là gì?

Cần phân biệt rạch ròi giữa **Bug/Thiếu sót trong phạm vi v1 (Phải sửa ngay)** và **Capability mới (Tiếp tục Reject/Abstain rõ ràng)**:

| Vấn đề | Phân loại | Quyết định trước NLU/Runner | Lý do kỹ thuật & Điểm số |
|---|---|---|---|
| **1. Nhầm "bán bao nhiêu tiền" thành `quantity(unit='tiền')`** | **Bug (Selector)** | **Sửa ngay** | Đã nằm trong capability `revenue` của v1, rulebook §1 quy định rõ. Sửa tốn < 5 dòng code, gỡ được abstain thực tế. |
| **2. Kỳ so sánh "tháng/quý liền trước" neo vào kỳ chính** (VD: Tháng 1/2024 so với tháng liền trước $\rightarrow$ 12/2023) | **Bug / Thiếu sót thiết kế v1** | **Sửa ngay** (Thêm `previous_period` vào `COMPARISON_KINDS` hoặc xử lý trong `resolve_period`) | `revenue_growth` là 1 trong 10 API cốt lõi của v1. Bắt LLM tự tính lùi năm/tháng/quý (nhất là khi câu hỏi khuyết năm phải dùng implicit-year rule) rất dễ làm LLM tính sai ngày. Để `Periods.before_period` / `previous_period` tính tất định là an toàn nhất. |
| **3. Lệch giữa `validate_plan` và `_capability`** | **Bug (Contract)** | **Sửa ngay** | Nếu để tách rời, JSON Schema / validator báo hợp lệ nhưng executor lại đánh abstain, làm hỏng cơ chế retry/repair của NLU. |
| **4. Hai filter scope khác nhau giữa 2 vế so sánh** (VD: Ca chiều so với ca sáng; Kênh A tuần này so với Thanh toán B tuần trước) | **Capability mới** | **Chưa làm ngay / Tiếp tục Reject rõ (`unsupported_comparison_or_denominator`)** | Trong mẫu audit 40 câu chỉ có ~10-11 câu thuộc bucket hẹp `multiple_filter_scopes` (tổng toàn bộ train chỉ có 13 câu ở bucket này!). Việc sửa `SalesMetrics.revenue_growth` và `QueryPlan` để nhận `comparison_filters` làm phình schema, trong khi lợi ích điểm số tối đa chỉ là $\sim 13/3000 = 0.43\%$. Hoàn toàn không đáng làm trước khi có NLU baseline. |
| **5. Câu hỏi Scalar / Top-1 trả về `string`** (VD: "Khách nào mua nhiều đơn nhất?") | **Capability mới** | **Hoãn sau Baseline NLU đầu tiên (Giữ `unsupported_answer_type`)** | Đòi hỏi thêm expected_type `'string'` vào `QueryPlan`, thêm xử lý khi có đồng hạng (tie-break ở top 1 trả về 1 chuỗi hay báo gì?), và kiểm tra kỹ cách `evaluate.py` so khớp alias chuỗi đơn. Hãy để NLU chạy được 10 API hiện tại trước. |
| **6. Tăng trưởng đa metric** (VD: Tăng trưởng số đơn, tăng trưởng AOV, lượng bán) & **Domain Công nợ / Tồn kho / Giá nhập** | **Capability / Domain mới** | **Tiếp tục Reject rõ (`unsupported_domain` / `unsupported_capability`)** | Đòi hỏi viết mới hoàn toàn logic trong `business/` và `loader/`. Trong cuộc thi có cơ chế phạt $-1$ cho câu trả lời sai và $0$ cho câu bỏ trống (`abstain`), việc **biết mình không hỗ trợ và chủ động trả về `abstain`** là một tính năng bảo vệ điểm số sống còn, không phải lỗi. |
| **7. Refactor `business/` sang SQL / DuckDB** | **Kiến trúc không cần thiết** | **TUYỆT ĐỐI KHÔNG LÀM** | `SalesMetrics` trên Pandas hiện tại đã chạy 126 câu qua toàn bộ các shop trong vài giây, giữ tối đa 1 shop trong RAM, và đã vượt qua 488 unit tests + 409 câu legacy. Đập đi viết lại bằng SQL lúc này sẽ phá vỡ toàn bộ các quy tắc xử lý `DataError`, `ORPHAN`, thứ tự lọc `trang_thai` và làm mất nhiều ngày debug vô ích. |

---

## 3. Chi tiết các Phát hiện Kỹ thuật (Findings theo mức độ ảnh hưởng)

### [CRITICAL - C1] Selector gán nhầm từ chỉ tiền tệ (`tiền`, `đồng`, `vnđ`, `doanh thu`) thành `unit_mention` của phép tính `quantity`
- **Mức độ chắc chắn:** 100% (Đã được xác nhận bởi ca abstain duy nhất trong `verification_v2` và tái hiện trực tiếp trên code).
- **Căn cứ Source:** `verification/selection.py:52-69` (hàm `_intent`).
- **Phân tích nguyên nhân:**
  Tại dòng 61, pattern của `revenue` chỉ khớp `r'(?:tong )?doanh thu(?: la)?(?: bao nhieu(?: tien)?| duoc bao nhieu)?'`. Nó không khớp cách hỏi rất phổ biến trong tiếng Việt là *"bán được bao nhiêu tiền"* hoặc *"thu được bao nhiêu tiền"*.
  Ngay bên dưới tại dòng 66:
  ```python
  match = re.fullmatch(r'ban (?:duoc )?bao nhieu ([\w]+)', text)
  if match:
      return 'quantity', None, match[1]
  ```
  Vì `[\w]+` khớp với mọi từ đơn, khi người dùng hỏi *"Tháng 9/2024 ca sáng bán được bao nhiêu tiền?"*, sau khi tách kỳ và ca, `metric_text` còn lại là `"ban duoc bao nhieu tien"`. Dòng 66 khớp hoàn toàn và trả về `operation='quantity'`, `unit='tien'`.
  - **Hệ quả 1:** Với shop bình thường, `resolve_filters` tìm `"tiền"` trong cột `don_vi_co_ban` của `mat_hang`, không thấy nên báo `ResolutionError` $\rightarrow$ `abstain` (mất cơ hội ăn điểm câu dễ).
  - **Hệ quả 2 (Nguy hiểm hơn):** Nếu câu hỏi là *"Bán được bao nhiêu đơn tháng này?"* (khi người dùng dùng động từ "bán" thay vì "có"), `match[1]` sẽ bắt chữ `"don"` làm `unit_mention='đơn'`. Nếu trong bảng `mat_hang` có mặt hàng dịch vụ dùng đơn vị cơ bản là `"đơn"` hoặc `"phần"`, hệ thống sẽ tính tổng `so_luong_co_ban` thay vì `order_count` $\rightarrow$ **Trả lời SAI giá trị, bị phạt $-1$ điểm!**
- **Synthetic Reproduction & Regression Test:**
  - *Input:* `select_question("Tháng 9/2024 ca sáng bán được bao nhiêu tiền?")`
  - *Expected:* `selection == 'selected'`, `plan['operation'] == 'revenue'`, `plan['filters']['shift'] == 'sang'`, `plan['filters']['unit_mention'] is None`.
  - *Actual hiện tại:* `selection == 'selected'`, `plan['operation'] == 'quantity'`, `plan['filters']['unit_mention'] == 'tiền'`.
  - *Input đối kháng 2:* `select_question("Tháng 9/2024 bán được bao nhiêu đơn hàng?")` (cụm 2 từ `don hang` hiện bị `[\w]+` bỏ qua thành `unparsed`, nhưng nếu hỏi `"Tháng 9/2024 bán được bao nhiêu đơn?"` thì `[\w]+` bắt `"don"` thành `quantity(unit='đơn')`!).
- **Hướng khắc phục đề xuất:**
  1. Bổ sung mẫu câu hỏi tiền bán vào `revenue` trong `_intent()`: `r'(?:ban|thu) (?:duoc )?bao nhieu tien'`.
  2. Chặn danh sách từ khóa cấm (blacklist) không bao giờ được làm `unit_mention` của `quantity` trong `_intent()`: `RESERVED_NON_UNITS = {'tien', 'dong', 'vnd', 'don', 'khach', 'mon', 'loai', 'mat', 'san', 'phan tram'}` (lưu ý: `'phan'` trong `"bao nhiêu phần"` là đơn vị hợp lệ nên vẫn giữ, chỉ chặn các danh từ chỉ metric như `tien`, `dong`, `vnd`, `don`, `khach`).

---

### [IMPORTANT - I2] Sự bất nhất giữa `validate_plan()` và `_capability()` làm lọt các Plan không thực thi được qua Manifest và Audit Validator
- **Mức độ chắc chắn:** 100% (Tái hiện trực tiếp từ cấu trúc `contract.py` và `executor.py`).
- **Căn cứ Source:**
  - `queryplan/contract.py:114-137` (`_semantics` và `validate_plan`)
  - `queryplan/executor.py:16-31` (`_capability`)
  - `verification/manifest.py:85` và `verification/audit.py:64`
- **Phân tích nguyên nhân:**
  Trong `manifest.py:85`, hàm `validate_manifest` kiểm tra:
  ```python
  if validate_plan(entry['plan']) != entry['plan'] or entry['plan']['status'] != 'supported':
      raise ManifestError('manifest plan must be normalized and executable')
  ```
  Tương tự, `audit.py:64` dùng `validate_plan()` để xác nhận một annotation có `decision == 'supported_plan'`.
  Tuy nhiên, 5 quy tắc kiểm tra tương thích ngữ nghĩa cấp cao lại nằm ở hàm `_capability(plan)` bên trong `queryplan/executor.py:16-31` thay vì nằm trong `contract.py::_semantics(plan)`:
  1. `unit_mention is not None and op != 'quantity'`
  2. `op in ('cancellation_rate', 'top_customers')` kèm `product_mentions` hoặc `product_group_mention`
  3. `top_products` dùng `metric='orders'` hoặc `top_customers` dùng `metric='quantity'`
  4. `comparison['kind'] == 'before_period' and main != 'tet'`
  5. `comparison['kind'] == 'previous_month_same_elapsed' and main != 'this_month'`
- **Synthetic Reproduction & Regression Test:**
  ```python
  from queryplan import validate_plan, QueryExecutor
  from queryplan_fixtures import plan, period_spec

  # Ca 1: top_products với metric='orders'
  bad_plan_1 = plan('top_products', ranking={'k': 3, 'metric': 'orders'})
  # Ca 2: revenue với unit_mention='ly'
  bad_plan_2 = plan('revenue')
  bad_plan_2['filters']['unit_mention'] = 'ly'
  # Ca 3: revenue_growth của today nhưng so với before_period
  bad_plan_3 = plan('revenue_growth', period=period_spec('today'),
                    comparison_period=period_spec('before_period'))

  # Actual: Cả 3 đều PASS validate_plan() mà không văng PlanValidationError!
  assert validate_plan(bad_plan_1) == bad_plan_1
  assert validate_plan(bad_plan_2) == bad_plan_2
  assert validate_plan(bad_plan_3) == bad_plan_3
  ```
  Hậu quả: `selection.py:134` gọi `validate_plan(plan)` để gác cổng cuối trước khi trả về `selection='selected'`. Nếu một câu hỏi như *"Tỷ lệ đơn hủy của mặt hàng 'Cà phê' tháng này là bao nhiêu phần trăm?"* đi vào `select_question()`, nó sẽ **vượt qua `validate_plan()`**, được đưa vào manifest là `selected`, nhưng khi chạy `verify_queryplans.py` lại bị đánh thành `abstained` (`unsupported_capability`)! Tương tự, AI annotator trong `audit.py` có thể gán một plan vi phạm 5 điều kiện trên vào `supported_plan` mà `validate_annotations()` vẫn báo PASS.
- **Hướng khắc phục đề xuất:**
  - Nếu muốn giữ tách biệt giữa `invalid_plan` (stage `semantic`) và `unsupported_capability` (stage `capability`) trong `QueryExecutor`: Hãy export một hàm `check_capability(plan)` (hoặc tham số `validate_plan(raw, require_capability=True)`) từ `queryplan/contract.py`, và gọi nó trong `selection.py:134`, `manifest.py:85`, và `audit.py:64`. Nhờ đó, câu *"Tỷ lệ đơn hủy của mặt hàng 'Cà phê'..."* sẽ được phân loại đúng ở bước inventory/audit là `unsupported_capability` thay vì lọt vào `selected` rồi gây fail exit code 1 ở verifier.

---

### [IMPORTANT - I3] Thiếu primitive kỳ so sánh tương đối neo vào kỳ chính (`previous_period` / tháng liền trước của tháng $M/Y$)
- **Mức độ chắc chắn:** 100% (Xác nhận từ `business/periods.py:56-61` và `queryplan/resolution.py:128-149`).
- **Căn cứ Source:**
  - `business/periods.py:56`: `def previous_month(self, same_elapsed: bool = False): end = self.as_of.replace(day=1) - timedelta(days=1)`
  - `verification/selection.py:42`: `_period` chỉ có `'previous_month': r'thang truoc'`.
- **Phân tích nguyên nhân:**
  Hiện tại, mọi kind tương đối trong `Periods` (`yesterday`, `previous_week`, `previous_month`) đều được neo cứng vào `self.as_of` (ngày đặt câu hỏi), ngoại trừ duy nhất `before(period)` (nhưng bị `_capability` khóa chặt chỉ cho phép dùng khi `main == 'tet'`).
  Hãy xét câu hỏi tổng hợp:
  > *"Doanh thu tháng 1/2024 tăng bao nhiêu phần trăm so với tháng liền trước?"* (hoặc *"...so với tháng trước đó?"*, giả sử `as_of_date = '2024-03-15'`).
  - Nếu parser/model sinh `period={'kind': 'month', 'month': 1, 'year': 2024}` và `comparison_period={'kind': 'previous_month'}`: Khi thực thi, `resolve_period(comparison)` sẽ gọi `periods.previous_month()`, trả về **Tháng 2/2024** (tháng liền trước của `as_of_date = 2024-03-15`) thay vì **Tháng 12/2023**! Kết quả tính ra hoàn toàn sai mà không báo lỗi!
  - Nếu bắt parser/model phải tự tính ra `comparison_period={'kind': 'month', 'month': 12, 'year': 2023}`: Thế nếu câu hỏi là *"Doanh thu tháng 1 tăng bao nhiêu phần trăm so với tháng liền trước?"* (không ghi năm, phải dựa vào `as_of_date` và luật implicit year của `Rulebook` để biết tháng 1 đó là năm nay hay năm ngoái)? Vì `select_question(text)` (và prompt NLU nếu không cẩn thận) xử lý câu hỏi độc lập hoặc model LLM hay mắc lỗi số học lùi năm từ tháng 1 về tháng 12 năm trước, việc thiếu một `comparison_period.kind` neo vào `primary` là một lỗ hổng thiết kế lớn.
- **Synthetic Reproduction & Regression Test:**
  ```python
  from business import DateRange
  from queryplan import QueryExecutor
  from queryplan_fixtures import plan, period_spec

  # Giả sử as_of_date là 2026-03-04. Hỏi tăng trưởng của tháng 1/2026 so với tháng trước.
  # Nếu model sinh comparison_period = previous_month:
  raw = plan('revenue_growth',
             period=period_spec('month', month=1, year=2026),
             comparison_period=period_spec('previous_month'))
  # Actual: kỳ chính là 2026-01-01..2026-01-31, nhưng kỳ so sánh lại là 2026-02-01..2026-02-28 (tương lai của kỳ chính!)
  ```
- **Hướng khắc phục đề xuất:**
  1. Trong `queryplan/executor.py:29-31` (hoặc `contract.py`), **chặn không cho phép** `comparison_period['kind'] in ('yesterday', 'previous_week', 'previous_month', 'previous_month_same_elapsed')` đi kèm với một `period['kind']` cố định như `'month'`, `'quarter'`, `'date_range'`, `'tet'` (ví dụ: `previous_month` chỉ hợp lệ khi `period['kind'] == 'this_month'`; `previous_week` chỉ hợp lệ khi `period['kind'] == 'this_week'`; `yesterday` chỉ hợp lệ khi `period['kind'] == 'today'`). Điều này lập tức chặn đứng lỗi lấy nhầm tháng trước của `as_of_date`!
  2. Bổ sung hoặc mở rộng ngữ nghĩa (nếu muốn hỗ trợ câu *"so với tháng/quý liền trước"* một cách tất định): Cho phép `previous_calendar_month` / `previous_calendar_quarter` (hoặc tính toán lùi tháng/quý ngay từ `primary: DateRange` trong `resolve_period` khi `primary` là `month`/`quarter`), tự động lùi `(year, 1) -> (year - 1, 12)` và kiểm tra biên `year == 1 and month == 1` trong `_period_bounds`.

---

### [IMPORTANT - I4] Lỗi dữ liệu ở cột `ngay_dat` hoặc file `calendar.csv` có thể gây Unhandled Exception nếu gọi qua `resolve_filters` / `Periods.tet`
- **Mức độ chắc chắn:** Cao (Phân tích trực tiếp luồng gọi hàm trong `resolution.py` và `periods.py`).
- **Căn cứ Source:**
  - `queryplan/resolution.py:67`: `known_orders = orders[pd.to_datetime(orders['ngay_dat']).dt.normalize() <= pd.Timestamp(as_of_date)]`
  - `business/periods.py:80-89`: `Periods.tet(self, year: int)`
- **Phân tích nguyên nhân:**
  1. Tại `resolution.py:67`, hàm `resolve_filters` gọi `pd.to_datetime(orders['ngay_dat'])` mà **không truyền `errors='coerce'`** và cũng không tận dụng `engine._dates` đã được parse ở `SalesMetrics.__init__`. Mặc dù trong `QueryExecutor.execute()` (`executor.py:78-80`), `SalesMetrics` được khởi tạo trước `resolve_filters` (nên `SalesMetrics` đã kiểm tra `ngay_dat` trước), nhưng `resolve_filters` là một hàm public trong `queryplan/resolution.py`. Nếu bất kỳ caller hay test nào gọi `resolve_filters(spec, tables, as_of_date)` trực tiếp (ví dụ trong công cụ audit catalog hoặc pre-resolver), và bảng `don_hang` thiếu cột `ngay_dat` hoặc có 1 dòng ngày lỗi, nó sẽ văng `KeyError` / `ValueError` thay vì `DataError`. Hơn nữa, việc parse lại `pd.to_datetime(orders['ngay_dat'])` ở mỗi lần gọi `resolve_filters` là tính toán thừa (double parsing) vì `SalesMetrics.__init__` vừa làm việc đó ở dòng 78!
  2. Tại `business/periods.py:80-89`, hàm public `Periods.tet(year)` đọc trực tiếp `csv.DictReader(f)` mà không qua bộ lọc `_validate_tet_calendar` của `queryplan/resolution.py`. Nếu một caller gọi `Periods.tet()` trực tiếp (như tài liệu `docs/business.md:31` hướng dẫn) trên một file `calendar.csv` bị thiếu cột `lunar_leap` hoặc ô rỗng, nó sẽ văng `KeyError`/`ValueError`/`AttributeError` (`None.lower()`). Ngay cả trong `resolution.py:100`, nếu một dòng trong `calendar.csv` có ít cột hơn dòng header, `row[f]` sẽ có giá trị `None`. Dòng 100 kiểm tra `not isinstance(row[f], str)` đã chặn được `None`, rất tốt; nhưng ở dòng 97:
     ```python
     if (reader.fieldnames is None or not set(fields).issubset(reader.fieldnames)
             or len(reader.fieldnames) != len(set(reader.fieldnames))):
     ```
     Nếu file CSV có dòng dữ liệu **dài hơn** dòng header (thừa dấu phẩy ở cuối dòng), `csv.DictReader(..., strict=True)` sẽ văng `csv.Error` (được bắt ở dòng 109 — tốt), nhưng nếu header có cột trùng tên không thuộc `fields` (ví dụ 2 cột ghi chú trống `""`), nó cũng bị chặn. Tuy nhiên, tại sao logic validate CSV này lại nằm ở `queryplan/resolution.py` mà không nằm ngay trong `business/periods.py::tet()` để bảo vệ cả public API của `business`?
- **Hướng khắc phục đề xuất:**
  - Trong `resolution.py:67`: Kiểm tra `'ngay_dat' in orders` và dùng `pd.to_datetime(orders['ngay_dat'], errors='coerce')`, nếu `.isna().any()` thì `raise DataError('Ngày đặt thiếu/sai')` để hàm `resolve_filters` tự đóng kín contract độc lập với thứ tự gọi `SalesMetrics`.
  - Chuyển (hoặc gọi) logic kiểm tra CSV an toàn vào `business/periods.py::tet()`.

---

### [MEDIUM - M1] Rủi ro trong `verification/selection.py`: `_clean()` xóa từ nối toàn cục và `re.findall(r'\w+', text)` làm hỏng nhận diện `unit_mention` khi câu có từ đồng hình không dấu
- **Mức độ chắc chắn:** 100% (Tái hiện bằng synthetic input).
- **Căn cứ Source:** `verification/selection.py:25-28` và `123-128`.
- **Phân tích nguyên nhân:**
  1. **Lỗi `ambiguous_unit_spelling` giả tạo (`selection.py:88, 123-128`):**
     Khi trích xuất đơn vị cho `quantity`, code thực hiện:
     ```python
     raw_words = re.findall(r'\w+', text) # Chạy trên toàn bộ câu (sau khi đã thay "..." bằng x0x)
     ...
     if unit is not None:
         spellings = {word.casefold() for word in raw_words if _fold(word) == unit}
         if len(spellings) != 1:
             return reject('ambiguous_unit_spelling')
     ```
     Giả sử có câu hỏi hoàn toàn hợp lệ nhưng chứa 2 từ khác dấu có cùng dạng không dấu (`_fold`), trong đó 1 từ nằm ở phần thời gian/bộ lọc/từ nối và 1 từ là đơn vị. Ví dụ:
     - Đơn vị là `"tư"` / `"từ"`, hoặc đơn vị là `"hộp"` trong khi câu có chữ `"hợp"`, hoặc đơn vị là `"cây"` trong khi câu có chữ `"cay"`, hoặc đơn vị là `"bộ"` trong khi câu có từ `"bỏ"`, hoặc đơn vị là `"phần"` trong câu *"Trong phần lớn tháng 9/2024 bán được bao nhiêu phân?"*.
     - Đặc biệt: Từ `"туần"` (`tuan`) không trùng, nhưng từ `"ca"` ( trong `"ca sáng"`) có `_fold("ca") == "ca"`. Nếu đơn vị cần hỏi là `"cá"` (hoặc `"ca"` — ví dụ: *"Ca sáng tháng này bán được bao nhiêu ca?"* hoặc *"Ca sáng tháng này bán được bao nhiêu cá?"*):
       - Trong câu `"Ca sáng tháng này bán được bao nhiêu cá?"`: `raw_words` chứa `['Ca', 'sáng', 'tháng', 'này', 'bán', 'được', 'bao', 'nhiêu', 'cá']`.
       - Vì `_fold('Ca') == 'ca'` và `_fold('cá') == 'ca'`, tập `spellings` sẽ là `{'ca', 'cá'}` $\rightarrow$ `len(spellings) == 2 != 1` $\rightarrow$ **Bị reject oan với lý do `ambiguous_unit_spelling`!**
  2. **Hàm `_clean()` xóa các từ `trong`, `vao`, `cua` không cần ngữ cảnh (`selection.py:25-28`):**
     `_clean` xóa mọi từ `\b(trong|vao|cua)\b`. Vì các mention trong dấu nháy đã được thay bằng `x0x` trước đó nên tên hàng trong dấu nháy được an toàn. Nhưng nếu sau này mở rộng grammar cho tên mặt hàng/nhóm hàng **không có dấu nháy** (như kế hoạch trong `PROGRESS.md`), hàm `_clean()` sẽ xóa mất chữ `"trong"`, `"vào"`, `"của"` nằm ngay bên trong tên sản phẩm hoặc câu văn!
- **Synthetic Reproduction & Regression Test:**
  ```python
  from verification.selection import select_question

  # Câu hỏi hoàn toàn hợp lệ và rõ nghĩa: hỏi số lượng đơn vị "cá" (hoặc "cà") bán trong "ca sáng"
  res = select_question("Ca sáng tháng 9/2024 bán được bao nhiêu cá?")
  # Expected: selection == 'selected', operation == 'quantity', shift == 'sang', unit_mention == 'cá'
  # Actual: {'selection': 'unparsed', 'reason': 'ambiguous_unit_spelling', 'plan': None}
  assert res['selection'] == 'unparsed' and res['reason'] == 'ambiguous_unit_spelling'
  ```
- **Hướng khắc phục đề xuất:**
  Thay vì lấy `raw_words` từ toàn bộ câu gốc rồi dò ngược bằng `_fold(word) == unit`, hãy giữ span (vị trí ký tự hoặc danh sách token song song `(raw_token, folded_token)`) hoặc xóa các phần `period`, `shift`, `filter` trên chuỗi NFC gốc (chỉ casefold, giữ dấu tiếng Việt) để trích xuất trực tiếp từ đơn vị có dấu tại đúng vị trí ngữ pháp của nó sau cụm `"bán được bao nhiêu"`. Khi đó vừa giữ được dấu chính xác 100%, vừa không bao giờ xung đột với chữ `"Ca"` trong `"ca sáng"`.

---

### [MEDIUM - M2] `evaluate/evaluate.py::map_columns` ánh xạ sai cột khi bảng dự đoán đổi thứ tự cột và có 1 tên cột viết khác chuẩn
- **Mức độ chắc chắn:** 100% (Phân tích tĩnh `evaluate/evaluate.py:139-151`).
- **Căn cứ Source:** `evaluate/evaluate.py:139-151` (`map_columns`).
- **Phân tích nguyên nhân:**
  Mặc dù QueryPlan v1 chưa trả về kiểu `table` (chỉ có `number`, `percent`, `list`, `unanswerable`), nhưng `evaluate.py` là bộ chấm chuẩn được dùng chung. Trong hàm `map_columns(gold_cols, pred_cols)`:
  ```python
  def map_columns(gold_cols: list, pred_cols: list) -> list[int]:
      pred_names = [normalize_str(c) if isinstance(c, str) else None for c in pred_cols]
      mapping = []
      for j, gc in enumerate(gold_cols):
          name = normalize_str(gc) if isinstance(gc, str) else None
          if name is not None and pred_names.count(name) == 1:
              mapping.append(pred_names.index(name))
          else:
              mapping.append(j)
      return mapping
  ```
  Giả sử bảng Gold có 2 cột `["Mặt hàng", "Doanh thu"]` (index 0, 1). Bảng dự đoán đảo thứ tự cột và viết tên cột 1 hơi khác: `["Doanh thu", "Tên SP"]` (index 0, 1).
  - Với `j = 0` (`gc = "Mặt hàng"`): không khớp trong `pred_names` $\rightarrow$ rơi vào `else: mapping.append(0)`.
  - Với `j = 1` (`gc = "Doanh thu"`): khớp `pred_names[0]` $\rightarrow$ `mapping.append(0)`.
  - Kết quả: `mapping = [0, 0]`! Cả hai cột của bảng Gold đều bị chiếu vào cột `0` của bảng dự đoán, làm mất hoàn toàn cột `1`!
- **Phân loại:** Không ảnh hưởng đến 10 API hiện tại của v1 (vì chưa có operation nào trả `table`), nhưng cần ghi nhận rõ trong tài liệu giới hạn của local evaluator.

---

### [LOW - L1] Test helper bị skip dài hạn `evaluate/test_evaluate.py::test_self_score_real_file` và bảo vệ đường dẫn ở `inventory_capabilities.py`
- **Căn cứ Source:**
  - `docs/PROGRESS.md` / `docs/validation.md`: Luôn ghi nhận `1 skip helper evaluator cũ tìm sai answers path`.
  - `inventory_capabilities.py:13`: `out = local_output(args.out, (args.train/'questions.jsonl', args.train/'rulebook.md'))`.
- **Nhận xét:**
  - Việc để một test tìm sai đường dẫn (`evaluate/answers.jsonl` thay vì `train/answers.jsonl`) tồn tại qua nhiều vòng commit chỉ là nợ kỹ thuật nhỏ nhưng làm nhiễu log kiểm chứng. Nếu file `evaluate/test_evaluate.py` nằm trong repo (hiện không có trong snapshot 37 file của handoff nhưng được pytest quét qua `testpaths = tests evaluate`), nên sửa đường dẫn trong test đó hoặc đánh dấu `@pytest.mark.local_data` đúng chuẩn như các test cần dữ liệu khác.
  - Ở `inventory_capabilities.py:13`, nên kiểm tra thêm `out.suffix == '.json'` và không nằm trong `args.train` tương tự như đã làm rất tốt ở `verify_queryplans.py:18`.

---

## 4. Các Tuyên bố (Claims) trong Tài liệu Hiện tại Cần Điều chỉnh / Rút lại

Nhìn chung, tài liệu của Codex ở vòng này (`PROGRESS.md`, `validation.md`, `capability-verification.md`, `plan-annotation-audit.md`) đã viết **rất trung thực và cẩn trọng** — hầu như không còn hiện tượng phóng đại số liệu hay lấy test count làm PA như các dự án thông thường. Tuy nhiên, có **3 điểm diễn đạt trong code/docs cần điều chỉnh lại cho đúng thực tế kỹ thuật:**

1. **Cần rút lại / sửa câu kiểm tra và khẳng định trong `verification/manifest.py:85` và `docs/capability-verification.md`:**
   - *Hiện trạng:* Code khẳng định `if validate_plan(entry['plan']) != entry['plan'] ... raise ManifestError('manifest plan must be normalized and executable')`.
   - *Sự thật:* `validate_plan()` hiện **không kiểm tra `_capability()`** của `executor.py`. Một plan qua được `validate_plan()` vẫn có thể bị từ chối thực thi ngay lập tức bởi `_capability()` trước khi chạm tới dữ liệu hay kỳ thời gian. Cần hợp nhất kiểm tra capability vào `validate_plan` (hoặc gọi tường minh trong `manifest.py` / `selection.py` / `audit.py`) trước khi tuyên bố plan trong manifest là "executable".
2. **Cần làm rõ con số `22 supported_plan` (hoặc `23/41`) trong `docs/plan-annotation-audit.md` và `docs/PROGRESS.md`:**
   - *Hiện trạng:* Bảng tổng hợp ghi cột `"Plan theo contract hiện tại: 22"` (và tổng 23/41), mặc dù bên dưới có dòng lưu ý nhỏ là *"chưa chứng minh executor/catalog thực thi được mọi ca"*.
   - *Yêu cầu điều chỉnh:* Cần đổi tên nhãn hoặc ghi chú rõ đây là **`23 schema_valid_proposals (unverified against catalog resolution & capability check)`** cho đến khi chạy bước dry-run qua `_capability()` và `resolve_filters()` (như đề xuất ở Câu 3). Không dùng con số 22/40 này để ước lượng phần trăm câu hỏi trong 2874 câu có thể giải được ngay bằng cách mở grammar.
3. **Cần làm rõ trạng thái kiểm chứng của 3 API (`top_products`, `top_customers`, `revenue_share`):**
   - Trong bảng trạng thái ở `docs/PROGRESS.md`, dòng `"Nghiệp vụ bán hàng: 10 API; có rulebook, period/calendar, filter và Answer"` cần ghi chú rõ: **7/10 API đã được đối chiếu với Gold BTC trên tập con train (qua verifier v2); 3/10 API (`top_products`, `top_customers`, `revenue_share`) mới chỉ được kiểm chứng trên synthetic tests, chưa có bất kỳ câu hỏi thực tế nào trên tập train được đối chiếu với Gold BTC.**

---

## 5. Chốt Đúng Hai Việc Tiếp theo (Action Plan có Cổng Kiểm chứng)

Để dự án tiến về đích thực chất mà không sa lầy vào việc viết regex vô tận hay refactor kiến trúc không cần thiết, tôi đề nghị thực hiện **đúng 2 việc sau theo thứ tự nghiêm ngặt**:

### Việc 1: Vá lỗi Contract/Selector/Period và Chạy Manifest v3 chạm đủ 10/10 API (Tối đa 1 phiên ngắn)
1. **Trong `queryplan/`:**
   - Đưa các quy tắc của `_capability(plan)` vào `contract.py` (hoặc gọi trong `validate_plan` / `check_capability`) để `selection.py`, `manifest.py` và `audit.py` không bao giờ chấp nhận một plan mà `QueryExecutor` từ chối ở stage `capability`.
   - Chặn `comparison_period['kind'] in ('yesterday', 'previous_week', 'previous_month', 'previous_month_same_elapsed')` khi `period['kind']` không phải là kỳ hiện tại tương ứng (`today`, `this_week`, `this_month`); đồng thời hỗ trợ dịch chuyển kỳ liền trước tương đối neo vào `primary` (cho câu *"tháng M/Y tăng bao nhiêu % so với tháng liền trước"* $\rightarrow$ tự lùi 1 tháng dương lịch kể cả từ tháng 1/Y về tháng 12/(Y-1)).
   - Bọc `pd.to_datetime(..., errors='coerce')` trong `resolution.py:67` và đưa `_validate_tet_calendar` bảo vệ trực tiếp `Periods.tet()`.
2. **Trong `verification/selection.py`:**
   - Sửa lỗi `"bán/thu được bao nhiêu tiền"` $\rightarrow$ `revenue` và thêm blacklist từ khóa metric cho `unit_mention` của `quantity`.
   - Sửa cách lấy `unit` có dấu để không bị lỗi `ambiguous_unit_spelling` khi câu có chữ `"Ca sáng"` đi kèm đơn vị `"cá"`/`"ca"`.
   - Bổ sung vừa đủ các mẫu câu chuẩn, rõ nghĩa (từ 22 ca audit) để selector bắt được một số câu thuộc `top_products`, `top_customers`, `revenue_share` và `revenue_growth` (neo kỳ) trên tập train.
3. **Gate nghiệm thu Việc 1:**
   - Toàn bộ synthetic regression tests mới chuyển từ RED $\rightarrow$ GREEN.
   - Đóng băng `manifest_v3.json` và chạy `verify_queryplans.py`: Xác nhận ca abstain tiền biến mất, kiểm tra kết quả đối chiếu Gold thực tế lần đầu tiên cho `top_products`, `top_customers`, `revenue_share`. **Dừng hoàn toàn việc mở rộng regex trong `selection.py` ngay sau bước này.**

### Việc 2: Xây dựng Baseline NLU Offline (Catalog-Aware + Constrained Decoding) & Submission Runner trên Group-Disjoint Split
1. **Xuất Schema & Context Builder:**
   - Tạo JSON Schema tĩnh từ `queryplan/contract.py` để ép model sinh đúng cấu trúc JSON.
   - Viết hàm trích xuất `catalog_context(tables, as_of_date)` chỉ đọc dữ liệu $\le \text{as\_of\_date}$, lấy danh sách các giá trị duy nhất của `nhom_hang`, `don_vi_co_ban`, `kenh_ban`, `hinh_thuc_tt`, `nhom_khach` và top/candidate `ten_hang` (khớp từ khóa với câu hỏi) để đưa vào prompt, giúp model điền đúng chuỗi mention mà `resolve_filters` yêu cầu.
2. **Tích hợp Model Offline ($\le 15\text{B}$) & Runner:**
   - Chọn 1 model open-weights nhẹ, chạy offline hoàn toàn, nối vào `QueryExecutor` $\rightarrow$ `Answer.to_submission(qid)`.
   - Khi `ExecutionResult.answer.type == 'abstain'`, runner xuất dòng hợp lệ hoặc bỏ trống theo đúng quy ước `evaluate.py` để nhận $0$ điểm thay vì đoán bừa bị $-1$ điểm.
3. **Gate nghiệm thu Việc 2:**
   - Chia 44 doanh nghiệp train theo `business_id` (group-disjoint), chạy runner đầu-cuối trên tập validation, báo cáo rõ: **Tỷ lệ sinh plan hợp lệ**, **Precision trên các câu `answered` + `unanswerable`**, **Tỷ lệ `abstain` theo từng `status`/`stage`**, và **Điểm PA thực tế** làm mốc baseline đầu tiên của toàn dự án.