# Phản biện độc lập DataMate — Vòng 002 / Lượt 01

* **Ngày đánh giá:** 2026-10-29 (Asia/Saigon)

* **Source revision kiểm tra:** `d99cac2620927702704e8efa93cfffdf3ca14cf0` (nhánh `VuongNguyen`, repo `zalo-datamate-2026`)

* **Tình trạng gói handoff:** Tự chứa đầy đủ 36 file (SHA256 khớp bảng kê, source tree clean). Không thiếu file nào trong danh mục đã liệt kê.

* **Phạm vi đọc thực tế:** Đã đọc toàn bộ 36 file snapshot trong gói:

  * Tài liệu & Spec: `docs/PROGRESS.md`, `docs/architecture.md`, `docs/business.md`, `docs/queryplan.md`, `docs/capability-verification.md`, `docs/plan-annotation-audit.md`, `docs/validation.md`, `docs/superpowers/specs/2026-10-29-capability-verifier.md`.

  * Verification & Tools: `verification/__init__.py`, `verification/AGENTS.md`, `verification/selection.py`, `verification/manifest.py`, `verification/runner.py`, `verification/audit.py`, `inventory_capabilities.py`, `verify_queryplans.py`.

  * QueryPlan Engine: `queryplan/__init__.py`, `queryplan/contract.py`, `queryplan/resolution.py`, `queryplan/executor.py`.

  * Business Layer: `business/__init__.py`, `business/rules.py`, `business/periods.py`, `business/sales.py`.

  * Evaluator: `evaluate/evaluate.py`.

  * Harness & Scripts: `scripts/harness.py`, `requirements.txt`, `pytest.ini`.

  * Synthetic Tests: `tests/conftest.py`, `tests/test_business_sales.py`, `tests/queryplan_fixtures.py`, `tests/test_queryplan_contract.py`, `tests/test_queryplan_executor.py`, `tests/test_capability_inventory.py`, `tests/test_queryplan_verification.py`, `tests/test_plan_annotation_audit.py`, `tests/test_harness.py`.

* **Ghi chú môi trường:** Toàn bộ phân tích dựa trên kiểm tra logic mã nguồn và phản chứng tổng hợp (synthetic counterexamples); không giả lập đã chạy lệnh thực tế trên terminal hay truy cập dữ liệu private/BTC.

## I. BẢNG PHÁN QUYẾT TỔNG THỂ (VERDICTS & GATES)

| Trục đánh giá | Phán quyết | Lý do cốt lõi & Cổng kiểm soát (Gate) | 
| ----- | ----- | ----- | 
| **1. Nền tính toán / Executor** | **ĐẠT CÓ ĐIỀU KIỆN** | **Điều kiện:** Đã có executor cách ly tốt với 10 API, nhưng `queryplan/resolution.py` còn neo cứng `previous_month` vào `as_of_date` thay vì kỳ được hỏi khi so sánh tăng trưởng, và thiếu cơ chế schema validation độc lập (JSON Schema) cho constrained decoding. | 
| **2. Đánh giá / Phương pháp** | **ĐẠT CÓ ĐIỀU KIỆN** | **Điều kiện:** Tính toàn vẹn băm/mẫu số (hash/manifest/accounting) rất chặt chẽ; nhưng **tính đại diện nội dung cực kỳ thấp** (125 câu matched chỉ tương đương 4.17% corpus, 3/10 API chưa có mẫu train nào được verifier kiểm tra). Không được dùng 125/125 để suy diễn chất lượng. | 
| **3.** Mức sẵn sàng Baseline **đầu-cuối** | **CHƯA ĐẠT** | **Lý do:** Chưa có model NLU, chưa có JSON Schema / BNF grammar xuất xưởng để ép kiểu giải mã (constrained decoding), và chưa có runner nối từ câu hỏi thô ra submission hoàn chỉnh. | 

## II. TRẢ LỜI NĂM CÂU HỎI THEO REVIEW_REQUEST

### Câu 1: Implementation có thực thi đúng contract và đủ chặt để làm nền không?

**Kết luận:** Nền tảng executor và verifier được thiết kế phòng thủ tốt (bảo vệ bất biến mẫu số, kiểm tra kiểu dữ liệu trước khi unique, phân tách rõ các lỗi), nhưng còn tồn tại **hai lỗi logic quan trọng** và **một khiếm khuyết contract** cần khắc phục trước khi tích hợp NLU.

#### Finding 1.1 (Important): Intent "tiền bán" bị bắt nhầm thành `quantity` với `unit_mention='tiền'`

* **Vị trí:** `verification/selection.py:68-80`

* **Nguyên nhân:** Regex `_intent` đặt pattern `ban (?:duoc )?bao nhieu ([\w]+)` ở cuối mà không loại trừ các token chỉ tiền tệ hoặc giá trị (`tiền`, `đ`, `vnd`). Trong khi đó, mẫu hỏi doanh thu chỉ tìm từ khóa `doanh thu`. Khi gặp câu hỏi tự nhiên như *"Tháng 9/2024 ca sáng bán được bao nhiêu tiền?"*, bộ parser gom nhóm `[\w]+` = `tien`, gán thành metric `quantity` với `unit_mention='tiền'`. Khi qua `resolve_filters`, catalog không có đơn vị này, dẫn tới `unresolved_entity` (abstain).

* **Phản chứng tối thiểu (Synthetic Reproduction):**

  ```
  from verification.selection import select_question
  res = select_question("Tháng 9/2024 ca sáng bán được bao nhiêu tiền?")
  # Hiện tại: res['plan']['operation'] == 'quantity'
  #           res['plan']['filters']['unit_mention'] == 'tiền'
  # Kỳ vọng:  res['plan']['operation'] == 'revenue'
  #           res['plan']['filters']['unit_mention'] is None
  
  ```

* **Hệ quả:** Làm hỏng 1 ca trong tập train v2 và sẽ làm sai lệch intent khi mở rộng grammar hoặc dùng làm dev spec cho NLU. Theo Rulebook §1, "tiền bán" là doanh thu.

* **Độ chắc chắn:** Tuyệt đối (High - đã xác nhận qua code line 78).

#### Finding 1.2 (Important): Lỗi neo thời gian so sánh tăng trưởng (`previous_month` bị neo vào `as_of_date` thay vì kỳ chính)

* **Vị trí:** `queryplan/resolution.py:129-138` kết hợp `business/periods.py:46-51`

* **Nguyên nhân:** Trong `business/periods.py`:

  ```
  def previous_month(self, same_elapsed: bool = False):
      end = self.as_of.replace(day=1) - timedelta(days=1)
      ...
  
  ```

  Hàm `previous_month()` luôn tính tháng trước của `self.as_of`. Trong `queryplan/resolution.py`, hàm `resolve_period` khi gặp `spec['kind'] == 'previous_month'` gọi trực tiếp `periods.previous_month()`, hoàn toàn bỏ qua tham số `primary: DateRange | None`.

* **Phản chứng tối thiểu (Synthetic Reproduction):**

  * Giả sử `as_of_date = '2026-03-04'`.

  * Câu hỏi: *"Doanh thu tháng 1/2024 tăng bao nhiêu % so với tháng trước?"*

  * Plan biểu diễn: `period = {'kind': 'month', 'month': 1, 'year': 2024}`, `comparison_period = {'kind': 'previous_month'}`.

  * **Thực tế tính toán:** `period` ra `2024-01-01 -> 2024-01-31`, nhưng `comparison_period` ra `2026-02-01 -> 2026-02-28` (tháng liền trước của `as_of_date` 2026)!

  * **Kỳ vọng nghiệp vụ:** Kỳ so sánh phải là Tháng 12/2023 (`2023-12-01 -> 2023-12-31`).

* **Khuyến nghị & Sửa đổi:** Contract của QueryPlan v1 không được cho phép `comparison_period.kind = 'previous_month'` đi kèm với một kỳ chính cố định trong quá khứ (`month`, `quarter`, `date_range`) trừ khi kỳ chính là `this_month`. Đối với kỳ lịch sử, NLU hoặc resolver bắt buộc phải điền tường minh `month=12, year=2023` hoặc thêm contract `kind='before_period'` cho mọi loại period (hiện tại `executor.py:27` chỉ cho phép `before_period` khi `main == 'tet'`).

* **Độ chắc chắn:** Tuyệt đối (High).

#### Finding 1.3 (Medium/Contract Gap): Thiếu contract cho truy vấn giá trị đơn lẻ (Scalar / Top-1 String)

* **Vị trí:** `queryplan/contract.py:10-14` & `business/sales.py:228-232`

* **Nguyên nhân:**

  * `top_products` và `top_customers` có `expected_type = 'list'`, hàm trả về luôn là `Answer('list', [...])`.

  * Nếu câu hỏi yêu cầu: *"Trong tháng 9/2024, khách nào mua nhiều đơn nhất?"* (chỉ đích danh 1 khách, kỳ vọng chuỗi tên khách `string`), evaluator của BTC nếu khai báo `type: 'string'` sẽ chấm `WRONG_TYPE` do hệ thống trả về `list` một phần tử `['Nguyễn Văn A']`.

* **Khẳng định:** Hiện tại verifier/executor reject dạng câu này là **đúng đắn theo thiết kế bảo thủ**; không được tự tiện ép `list` 1 phần tử thành `string` khi chưa có contract schema rõ ràng.

### Câu 2: Mức tin cậy của đánh giá hiện tại là gì?

**Kết luận:** Đánh giá hiện tại có **độ tin cậy kỹ thuật (technical integrity) cao**, nhưng có **độ tin cậy thống kê và năng lực tổng quát hóa (generalization validity) rất thấp**.

1. Ý nghĩa thực sự của **125/125 compared và 409/409 legacy:**

   * **409/409 legacy:** Chứng minh tầng tính toán cốt lõi (`business/sales.py`) tái hiện 100% kết quả của pipeline cũ trên tập con 3 nghiệp vụ cơ bản (doanh thu, số lượng, đơn hủy). Không chứng minh được gì về NLU hay 7 API còn lại.

   * **125/125 compared v2:** Chỉ chứng minh được: *Khi câu hỏi tiếng Việt khớp hoàn toàn 100% với mẫu câu ngữ pháp regex được viết cứng (hardcoded), executor ánh xạ tham số chuẩn xác và gọi business API ra kết quả trùng khớp với gold.*

2. **Những khoảng trống gây ngộ nhận cần chặn đứng:**

   * **Mẫu số quá nhỏ (Coverage = 4.17%):** 126/3000 câu được chọn. 2874 câu (95.83%) nằm ngoài vùng xử lý. Tự hào về 125/125 là rơi vào bẫy "chính xác trên tập siêu chọn lọc" (selection bias cực đoan).

   * Thiếu hụt **hoàn toàn 3 API chính trên tập train:** Trong 126 câu chọn, phân bố như sau:

     * `revenue`: 62 câu

     * `cancellation_rate`: 22 câu

     * `cancelled_orders`: 14 câu

     * `average_order_value`: 14 câu

     * `order_count`: 7 câu

     * `revenue_growth`: 4 câu

     * `quantity`: 3 câu

     * `top_products`: **0 câu**

     * `top_customers`: **0 câu**

     * `revenue_share`: **0 câu** Ba API phức tạp nhất về ranking và tính tỷ trọng chưa hề được đối chiếu với bất kỳ câu gold train thực tế nào trong verifier v2!

   * **Rủi ro trùng khớp ngẫu nhiên (Accidental Agreement):** Với các câu hỏi kỳ trống không có đơn hàng (doanh thu = 0, số đơn = 0), nhiều cách hiểu sai về bộ lọc hoặc ngày tháng vẫn có thể vô tình trả về `0` trùng với gold.

   * **Tính toàn vẹn mẫu số:** Điểm sáng duy nhất là `verification/runner.py` tu