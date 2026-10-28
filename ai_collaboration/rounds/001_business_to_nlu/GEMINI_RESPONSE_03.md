# GEMINI_RESPONSE_03 — Phản hồi kỹ thuật Vòng 001 (Lượt 03)

- **Vòng thảo luận:** `001_business_to_nlu`[cite: 1, 5, 6]
- **Lượt phản hồi:** `03`[cite: 5, 6]
- **Ngày:** 2026-10-29 (Asia/Saigon)[cite: 6, 7]
- **Các tài liệu đã đọc trong lượt này:** `GEMINI_PROMPT_03.md`[cite: 5], `CODEX_REPLY_TO_GEMINI_02.md`[cite: 6], `CODEX_REVIEW_02.md`[cite: 7] (cùng ngữ cảnh nền từ `GEMINI_HANDOFF.md`[cite: 1], `TRAIN_METADATA.md`[cite: 2], `CODEX_REPLY_TO_GEMINI.md`[cite: 3], `CODEX_REVIEW.md`[cite: 4] ở các lượt trước).
- **Trạng thái thực thi:** Chỉ phân tích từ source snapshot (`1c89252`) và kết quả 26 probe / 219 pytest / 409 verifier do Codex báo cáo[cite: 6, 7]; chưa trực tiếp chạy repo hay sửa code[cite: 5, 6]. Các đề xuất dưới đây là lựa chọn kỹ thuật để Codex kiểm chứng và triển khai theo ủy quyền tự chủ của người dùng[cite: 5, 6, 7].

---

## Tóm tắt cập nhật lập trường kỹ thuật (Giữ / Điều chỉnh / Rút)

| Hạng mục | Quyết định ở Lượt 03 | Căn cứ kỹ thuật |
|---|---|---|
| **1. Bỏ kiểm tra liên kết dòng hàng (`dong_hang.ma_don`) ngoài kỳ** | **RÚT đề xuất bỏ kiểm tra liên kết theo kỳ.** Chuyển sang kiểm tra theo **Table Dependency của từng Metric**. | Phản chứng `ORPHAN` của Codex chứng minh dòng hàng có `ma_don` mồ côi không có ngày độc lập[cite: 6, 7]: nếu thực chất nó thuộc đơn `O2` trong kỳ thì làm thay đổi tổng từ `201` lên `251`, nếu thuộc `O5` tương lai thì giữ nguyên `201`[cite: 6, 7]. Không thể chứng minh dòng mồ côi nằm ngoài kỳ nếu thiếu provenance ngày độc lập[cite: 6, 7]. |
| **2. Thêm `raw_decimal` vào `Answer` và đưa `compare_periods` (boolean) vào v1** | **RÚT `raw_decimal` trên `Answer` và HOÃN `boolean` sang v1.1.** | Phản chứng `100.51` vs `100.50` đều làm tròn thành `101` cho thấy chưa có bằng chứng gold xác nhận boolean so sánh trước hay sau làm tròn[cite: 6, 7]. Ngoài ra, `Decimal(1)/Decimal(3)` bị mất chính xác nếu chia sớm[cite: 6, 7], và toàn train chỉ có 23 câu `boolean` (0.77%)[cite: 2]. Giữ `Answer` nguyên bản và chỉ đưa các operation trực tiếp của `SalesMetrics` vào `QueryPlan v1` là lát cắt gọn, an toàn nhất[cite: 6, 7]. |
| **3. Mở rộng `revenue_share` nhận `denominator_filters` tự do ở v1** | **ĐIỀU CHỈNH: Giữ `revenue_share` v1 chỉ tính tỷ trọng trên cả shop (`denominator = Filters()`)**, nhưng sửa điều khoản `rules.require` theo đúng filter được dùng; reject plan yêu cầu mẫu số tập con ở v1. | Hai filter độc lập (`P1=90`, `T=10`) tạo ra tỷ số `900%` (ratio, không phải share)[cite: 6, 7]. Khi cần hỗ trợ parent-share ở v1.1, bắt buộc ngữ nghĩa tử số là `scope(numerator) ∩ scope(denominator)` và kiểm tra rule cho cả tử lẫn mẫu[cite: 6, 7]. |
| **4. Xóa hẳn bảng trong `tables` dict tương đương `unanswerable`** | **ĐIỀU CHỈNH.** Phân biệt rõ thiếu khóa dict (`KeyError` do lỗi truyền bảng/cache hỏng) với bảng rỗng (`len(df) == 0`) hoặc cờ capability trong `cua_hang.json`[cite: 6, 7]. | Probe của Codex xác nhận xóa key `'dong_hang'` hoặc `'mat_hang'` khỏi `tables` làm `SalesMetrics.__init__` văng `KeyError` ở dòng truy cập dict[cite: 1, 6, 7]. |
| **5. Khái niệm Split 20/10 vs Group-Disjoint** | **ĐIỀU CHỈNH thuật ngữ và tiêu chí.** | Chia 20/10 có giao nhóm `A–J` chỉ là **Stratified Business Split (In-group generalization)**; muốn đo khả năng tổng quát sang mẫu file mới phải dùng **Group-Disjoint Split (Leave-Template-Group-Out)**[cite: 6, 7]. |

---

## Mục 1: Ràng buộc liên kết dữ liệu (ORPHAN), Ma trận Dependency theo Metric & 3 Test phân định

### 1.1. Lập trường & Căn cứ
* **Rút đề xuất** chỉ kiểm tra `self.lines['ma_don'].isin(selected_orders['ma_don'])` theo kỳ hỏi[cite: 6, 7].
* **Căn cứ từ phản chứng ORPHAN**: Trong schema chuẩn hiện tại, bảng `dong_hang` chỉ lưu `ma_don`, `ma_hang`, `loai_dong`, `so_luong_co_ban`, `thanh_tien` — **không có cột ngày đặt độc lập đã được xác thực**[cite: 1, 6, 7]. Khi xuất hiện một dòng trong `dong_hang` có `ma_don = 'ORPHAN'` không khớp với bất kỳ `ma_don` nào trong `don_hang`, ta không biết dòng đó vốn thuộc về một đơn trong kỳ hỏi (nhưng bị gõ sai mã đơn khi nhập liệu) hay thuộc về một đơn ngoài kỳ[cite: 6, 7]. Bỏ qua nó sẽ vi phạm tính đúng đắn (soundness)[cite: 6, 7].
* **Điều chỉnh sang Lazy / Metric-Scoped Validation**: Thay vì kiểm tra toàn bộ 3 bảng (`don_hang`, `dong_hang`, `mat_hang`) một cách vô điều kiện trong `__init__`[cite: 1], ta kiểm tra theo **Dependency Graph của từng thao tác** và **Provenance lọc cấp đơn**[cite: 6, 7].

### 1.2. Ma trận Dependency và Bằng chứng Provenance tối thiểu cho từng Metric

Gọi $\mathcal{F}_{order}$ là tập các bộ lọc cấp đơn (`channel`, `payment`, `customer_group`, `shift`) và $\mathcal{F}_{prod}$ là tập các bộ lọc cấp sản phẩm (`product_ids`, `product_group`, `unit`)[cite: 1].

| Metric / Method | Bảng bắt buộc phải hợp lệ khóa & liên kết | Bảng ĐƯỢC PHÉP bỏ qua lỗi (nếu $\mathcal{F}_{prod} = \emptyset$) | Bằng chứng Provenance tối thiểu để bỏ qua một bản ghi lỗi trong `don_hang` |
|---|---|---|---|
| `order_count(period, filters)`<br>`cancelled_orders(period, filters)` | - `don_hang` (nếu $\mathcal{F}_{prod} = \emptyset$)<br>- Thêm `dong_hang` (+ `mat_hang` nếu lọc sản phẩm) khi $\mathcal{F}_{prod} \neq \emptyset$ | **`mat_hang` và `dong_hang`** (khi `filters.product_ids is None` và `filters.product_group is None`)[cite: 6, 7] | Một đơn $r \in \text{don\_hang}$ có lỗi ở cột $C_i$ (VD: `trang_thai = NaN` hoặc `thoi_diem_dat = NaN`) chỉ được phép bỏ qua nếu tồn tại ít nhất một cột đã xác thực $C_j \in \{\text{ngay\_dat}\} \cup \mathcal{F}_{order}$ mà giá trị $r[C_j]$ **không phải `NaN`** và **chắc chắn loại $r$ khỏi phạm vi truy vấn** (VD: `ngay_dat` hợp lệ nằm ngoài `period`, hoặc `kenh_ban == 'tai_quan'` khi đang hỏi `channel='online'`)[cite: 6, 7]. |
| `cancellation_rate(period, filters)` | Như `order_count` | **`mat_hang` và `dong_hang`** (khi $\mathcal{F}_{prod} = \emptyset$) | Như trên. Nếu đơn nằm trong `period` và khớp $\mathcal{F}_{order}$ (hoặc có `NaN` ở chính cột đang nằm trong $\mathcal{F}_{order}$), bắt buộc phải raise `DataError`[cite: 1, 7]. |
| `revenue(period, filters)`<br>`average_order_value(...)`<br>`revenue_growth(...)`<br>`revenue_share(...)` | - Nếu `len(dong_hang) > 0`: `don_hang` + `dong_hang` (toàn bộ `dong_hang['ma_don']` phải nằm trong `don_hang['ma_don']`, trừ khi `dong_hang` có provenance chứng minh thuộc đơn ngoài kỳ) + `mat_hang` (nếu $\mathcal{F}_{prod} \neq \emptyset$).<br>- Nếu `len(dong_hang) == 0`: chỉ cần `don_hang` (khi $\mathcal{F}_{prod} = \emptyset$)[cite: 1]. | **`mat_hang`** (khi `filters.product_ids is None` và `filters.product_group is None`)[cite: 6, 7] | Không được bỏ qua bất kỳ dòng nào trong `dong_hang` có `ma_don` mồ côi[cite: 6, 7]. Chỉ bỏ qua lỗi `thanh_tien = NaN` hoặc `loai_dong` lạ của một dòng hàng $l$ nếu `l['ma_don']` nối được thành công vào một đơn $r \in \text{don\_hang}$ và đơn $r$ đã được chứng minh nằm ngoài `period` hoặc bị loại bởi $\mathcal{F}_{order}$ hoặc có `trang_thai in ('huy', 'tra_hang')`[cite: 1, 7]. |
| `quantity(period, filters, unit)`<br>`top_products(...)` | `don_hang` + `dong_hang` + `mat_hang` | Không bỏ qua bảng nào[cite: 1]. | Với `mat_hang`: nếu `unit is None` và `product_group is None`, một sản phẩm $p$ không xuất hiện trong bất kỳ dòng hàng nào của kỳ hỏi nếu bị thiếu `ten_hang`/`don_vi_co_ban` thì không ảnh hưởng kết quả; nhưng khóa `ma_hang` trong `mat_hang` vẫn không được trùng lặp để đảm bảo ánh xạ 1-1[cite: 1]. |
| `top_customers(period, k, metric, filters)` | - Khi `metric == 'orders'` và $\mathcal{F}_{prod} = \emptyset$: chỉ cần `don_hang`[cite: 1, 7].<br>- Khi `metric == 'revenue'` và `len(dong_hang) > 0`: cần `don_hang` + `dong_hang` (+ `mat_hang` nếu $\mathcal{F}_{prod} \neq \emptyset$)[cite: 1]. | **`mat_hang` và `dong_hang`** (khi `metric == 'orders'` và $\mathcal{F}_{prod} = \emptyset$)[cite: 7] | Đơn của khách lẻ (`_walkins == True`) nếu bị thiếu `ten_khach` hoặc `nhom_khach` thì không ảnh hưởng tới `top_customers` (vì khách lẻ bị loại khỏi xếp hạng theo rulebook)[cite: 1]. |

### 1.3. Quy tắc kiểm tra cấu trúc `tables` dict (Tránh `KeyError` ngầm)
* Trong `SalesMetrics.__init__`, phải kiểm tra sự tồn tại của các key chuẩn `('don_hang', 'dong_hang', 'mat_hang', 'cua_hang')` trong `tables`. Nếu thiếu key hoặc kiểu dữ liệu không phải `pd.DataFrame` / `dict` $\rightarrow$ raise `DataError('Cấu trúc cache thiếu bảng chuẩn')` thay vì để Python văng `KeyError` không tường minh[cite: 6, 7].

### 1.4. Đề xuất 3 Unit Tests phân định (Chấp nhận / Bác bỏ)

```python
# Test 1 (Bác bỏ dòng mồ côi khi tính doanh thu):
# Thêm dòng ORPHAN vào dong_hang -> revenue() bắt buộc raise DataError, nhưng order_count() không lọc sản phẩm vẫn chạy bình thường.
def test_orphan_line_blocks_revenue_but_allows_unfiltered_order_count(tables, rules, period):
    orphan = pd.DataFrame([['ORPHAN', 'P1', 'hang', 1, 50]], columns=tables['dong_hang'].columns)
    tables['dong_hang'] = pd.concat([tables['dong_hang'], orphan], ignore_index=True)
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.order_count(period).answer == 2
    with pytest.raises(DataError, match='Dòng hàng không nối được với đơn hàng'):
        engine.revenue(period)

# Test 2 (Chấp nhận đếm đơn khi bảng mat_hang bị lỗi khóa nhưng truy vấn không đụng tới sản phẩm):
def test_broken_product_catalog_does_not_block_order_level_metrics(tables, rules, period):
    tables['mat_hang'].loc[1, 'ma_hang'] = 'P1'  # duplicate ma_hang
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.order_count(period).answer == 2
    assert engine.cancelled_orders(period).answer == 1
    with pytest.raises(DataError, match='ma_hang'):
        engine.top_products(period)

# Test 3 (Chấp nhận lọc kênh khi đơn ở kênh khác bị hỏng trạng thái, nhưng bác bỏ nếu đơn cùng kênh hoặc đơn NaN kênh bị hỏng):
def test_corrupted_status_in_excluded_channel_is_ignored_but_nan_channel_raises(tables, rules, period):
    # O1 là 'tai_quan', hỏng trang_thai -> hỏi 'online' vẫn an toàn vì O1 chắc chắn bị loại bởi kenh_ban=='tai_quan'
    tables['don_hang'].loc[0, 'trang_thai'] = 'status_la'
    engine = SalesMetrics(tables, rules, '2026-03-04')
    assert engine.cancelled_orders(period, Filters(channel='online')).answer == 1
    # Nhưng nếu O1 có kenh_ban = None (không chứng minh được O1 nằm ngoài 'online') -> phải raise DataError
    tables['don_hang'].loc[0, 'kenh_ban'] = None
    with pytest.raises(DataError):
        SalesMetrics(tables, rules, '2026-03-04').cancelled_orders(period, Filters(channel='online'))
```

---

## Mục 2: Contract Precision & Chính sách với Boolean ở v1

### 2.1. Lựa chọn thiết kế cho v1
1. **Rút đề xuất gắn `raw_decimal: Decimal | None` lên `Answer` và hoãn `boolean` (`compare_periods`) khỏi `QueryPlan v1`**[cite: 6, 7].
   * *Lý do*: Toàn tập train 3000 câu chỉ có 23 câu `boolean` (0.77%)[cite: 2], và chưa có bằng chứng gold xác nhận khi hai kỳ có doanh thu thực `100.51` và `100.50` (cùng làm tròn thành `101` đồng) thì câu hỏi so sánh dùng giá trị trước hay sau khi làm tròn về đồng[cite: 6, 7]. Đưa `boolean` vào v1 vừa làm phình `Answer` contract vừa tiềm ẩn rủi ro đoán mò quy tắc so sánh[cite: 6, 7].
2. **Chọn hướng: Giữ `Answer(type, answer, reason)` bất biến như hiện tại cho Public API, và quy định chặt Invariant tính toán nội bộ trong `SalesMetrics`**[cite: 1, 6, 7].

### 2.2. Các Invariant cụ thể về Precision trong `SalesMetrics`

| Đại lượng / Phép tính | Biểu diễn trung gian bắt buộc | Thời điểm & Quy tắc làm tròn duy nhất | Xử lý mẫu số 0 / Kỳ rỗng / Lỗi |
|---|---|---|---|
| **Số đếm** (`order_count`, `cancelled_orders`, số đơn của khách) | `int` (Python exact integer)[cite: 1] | Không làm tròn (`int` chính xác). | Kỳ rỗng nhưng có `co_ma_don=True` $\rightarrow$ `Answer('number', 0)`[cite: 1, 6, 7]. Nếu `co_ma_don=False` $\rightarrow$ `Answer('unanswerable')`[cite: 1, 6, 7]. |
| **Tổng tiền** (`revenue`) | `Decimal` (tổng các `Decimal(str(v))` từ `_sum`, không qua `float` cộng dồn)[cite: 1] | Cuối hàm `revenue()`: `_number(val, self.rules.rounding_places('money'))` với `ROUND_HALF_UP`[cite: 1]. | Kỳ rỗng (trong khoảng dữ liệu) $\rightarrow$ `Decimal(0)` $\rightarrow$ `Answer('number', 0)`[cite: 1, 6, 7]. Thiếu `NaN` một phần $\rightarrow$ `DataError`[cite: 1]. |
| **Tổng số lượng cơ bản** (`quantity`) | `Decimal` (tổng từ `_sum(lines, 'so_luong_co_ban')`)[cite: 1] | Cuối hàm `quantity()`: `_number(val, 6)` với `ROUND_HALF_UP` (bỏ phần thập phân `.0` nếu là số nguyên nhờ `int(value) if value == value.to_integral_value() else float(value)`)[cite: 1, 3, 4]. | Kỳ rỗng (có bảng `dong_hang` và `unit` hợp lệ trong danh mục) $\rightarrow$ `Answer('number', 0)`[cite: 1, 6, 7]. Không có `dong_hang` hoặc `unit` không có trong danh mục $\rightarrow$ `Answer('unanswerable')`[cite: 1, 6, 7]. |
| **Trung bình đơn** (`average_order_value`) | Tử số `rev: Decimal` (chưa làm tròn về đồng), Mẫu số `cnt: int`[cite: 1]. | Chỉ chia và làm tròn **một lần ở bước cuối**: `_number(rev / Decimal(cnt), self.rules.rounding_places('money'))` với `ROUND_HALF_UP`[cite: 1]. | `cnt == 0` hoặc `co_ma_don == False` $\rightarrow$ `Answer('unanswerable')`[cite: 1, 6, 7]. |
| **Tỷ lệ / Tăng trưởng / Tỷ trọng** (`cancellation_rate`, `revenue_growth`, `revenue_share`) | Tử số `num: Decimal` (chưa làm tròn trung gian), Mẫu số `den: Decimal` (chưa làm tròn trung gian)[cite: 1]. Nhân `100` trước khi chia: `(num * Decimal(100)) / den` dưới `decimal.localcontext()` có `prec = 28`[cite: 1, 7]. | Chỉ quantize **một lần ở bước cuối**: `_number((num * Decimal(100)) / den, self.rules.rounding_places('percent'))` với `ROUND_HALF_UP`[cite: 1]. | - `den == 0` $\rightarrow$ `Answer('unanswerable')`[cite: 1, 6, 7].<br>- Với `revenue_growth`: nếu `current == 0` và `baseline > 0` $\rightarrow$ `Answer('percent', -100)`[cite: 6, 7].<br>- Với `revenue_share` và `cancellation_rate`: nếu `num == 0` và `den > 0` $\rightarrow$ `Answer('percent', 0)`[cite: 1, 7]. |
| **Xếp hạng** (`top_products`, `top_customers`) | So sánh trực tiếp trên `Decimal` (cho `revenue`/`quantity`) hoặc `int` (cho `orders`) **trước khi làm tròn hiển thị**[cite: 1, 4]. | Kết quả trả về là `Answer('list', names)` nên không serialize số, nhưng thứ tự hạng không bị méo bởi làm tròn đồng[cite: 1, 4]. | Tập `grouped` rỗng (không có đối tượng nào có giao dịch hợp lệ trong kỳ) $\rightarrow$ hiện trả `Answer('unanswerable')`[cite: 1, 6, 7]. |

*(Ghi chú cho v1.1 khi mở rộng sang so sánh hai tỷ số hoặc boolean: Để tránh lỗi `(Decimal(1)/Decimal(3))*3 != 1` như Codex chỉ ra[cite: 6, 7], khi cần so sánh hai phân số $\frac{A}{B}$ và $\frac{C}{D}$ với $B, D > 0$ mà chưa làm tròn, ta phải dùng phép nhân chéo chính xác $A \times D \gtrless C \times B$ trên `Decimal`/`int` thay vì chia thập phân[cite: 7]).*

---

## Mục 3: JSON Schema thực sự cho `QueryPlan v1`, Ma trận Semantic Validator & Bộ Test

### 3.1. Phạm vi `QueryPlan v1`
Để tạo lát cắt đầu tiên cực kỳ chắc chắn, `QueryPlan v1` chỉ nhận các câu hỏi ánh xạ trực tiếp vào **10 public methods hiện có của `SalesMetrics`** (3 kiểu kết quả: `number`, `percent`, `list`) và trạng thái `unsupported` (để chủ động `abstain` cho các câu `boolean`, `date`, `string`, `table` hoặc nghiệp vụ ngoài Sales)[cite: 1, 2, 6, 7].

Đặc biệt, để giải quyết triệt để sự khác biệt giữa `previous_month(same_elapsed=False)` (kết thúc 28/02) và `previous_month(same_elapsed=True)` (kết thúc 04/02 khi `as_of_date = 2026-03-04`)[cite: 1, 6, 7], đối tượng `period` và `comparison_period` tách riêng các `kind` tường minh: `"previous_month"` vs `"previous_month_same_elapsed"`, và `"before_period"` (cho phép tính kỳ liền trước cùng số ngày, như trước Tết)[cite: 1, 6, 7].

### 3.2. JSON Schema thực sự (Draft 2020-12)

```json
{
  "$schema": "[https://json-schema.org/draft/2020-12/schema](https://json-schema.org/draft/2020-12/schema)",
  "$id": "[https://datamate.zalo.ai/schemas/query_plan_v1.json](https://datamate.zalo.ai/schemas/query_plan_v1.json)",
  "title": "DataMateQueryPlanV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "version",
    "status",
    "unsupported_reason",
    "operation",
    "expected_type",
    "period",
    "comparison_period",
    "filters",
    "ranking"
  ],
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0"
    },
    "status": {
      "type": "string",
      "enum": ["supported", "unsupported"]
    },
    "unsupported_reason": {
      "type": ["string", "null"],
      "enum": [
        "unsupported_domain",
        "unsupported_answer_type",
        "unsupported_comparison_or_denominator",
        "ambiguous_question",
        "unparseable_time",
        null
      ]
    },
    "operation": {
      "type": ["string", "null"],
      "enum": [
        "revenue",
        "order_count",
        "cancelled_orders",
        "cancellation_rate",
        "average_order_value",
        "quantity",
        "top_products",
        "top_customers",
        "revenue_growth",
        "revenue_share",
        null
      ]
    },
    "expected_type": {
      "type": ["string", "null"],
      "enum": ["number", "percent", "list", null]
    },
    "period": {
      "oneOf": [
        { "type": "null" },
        { "$ref": "#/$defs/periodSpec" }
      ]
    },
    "comparison_period": {
      "oneOf": [
        { "type": "null" },
        { "$ref": "#/$defs/comparisonPeriodSpec" }
      ]
    },
    "filters": {
      "oneOf": [
        { "type": "null" },
        { "$ref": "#/$defs/filterSpec" }
      ]
    },
    "ranking": {
      "oneOf": [
        { "type": "null" },
        { "$ref": "#/$defs/rankingSpec" }
      ]
    }
  },
  "$defs": {
    "periodSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "n", "month", "quarter", "year", "start_date", "end_date"],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "today",
            "yesterday",
            "last_days",
            "this_week",
            "previous_week",
            "this_month",
            "previous_month",
            "previous_month_same_elapsed",
            "month",
            "quarter",
            "year_to_date",
            "tet",
            "date_range"
          ]
        },
        "n": { "type": ["integer", "null"], "minimum": 1 },
        "month": { "type": ["integer", "null"], "minimum": 1, "maximum": 12 },
        "quarter": { "type": ["integer", "null"], "minimum": 1, "maximum": 4 },
        "year": { "type": ["integer", "null"], "minimum": 1900, "maximum": 2100 },
        "start_date": { "type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
        "end_date": { "type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}-\\d{2}$" }
      }
    },
    "comparisonPeriodSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "n", "month", "quarter", "year", "start_date", "end_date"],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "previous_month",
            "previous_month_same_elapsed",
            "previous_week",
            "yesterday",
            "before_period",
            "month",
            "quarter",
            "tet",
            "date_range"
          ]
        },
        "n": { "type": ["integer", "null"], "minimum": 1 },
        "month": { "type": ["integer", "null"], "minimum": 1, "maximum": 12 },
        "quarter": { "type": ["integer", "null"], "minimum": 1, "maximum": 4 },
        "year": { "type": ["integer", "null"], "minimum": 1900, "maximum": 2100 },
        "start_date": { "type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
        "end_date": { "type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}-\\d{2}$" }
      }
    },
    "filterSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "product_mentions",
        "product_group_mention",
        "channel_mention",
        "payment_mention",
        "customer_group_mention",
        "shift",
        "unit_mention"
      ],
      "properties": {
        "product_mentions": {
          "type": ["array", "null"],
          "items": { "type": "string", "minLength": 1 }
        },
        "product_group_mention": { "type": ["string", "null"], "minLength": 1 },
        "channel_mention": { "type": ["string", "null"], "minLength": 1 },
        "payment_mention": { "type": ["string", "null"], "minLength": 1 },
        "customer_group_mention": { "type": ["string", "null"], "minLength": 1 },
        "shift": { "type": ["string", "null"], "enum": ["sang", "chieu", null] },
        "unit_mention": { "type": ["string", "null"], "minLength": 1 }
      }
    },
    "rankingSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": ["k", "metric"],
      "properties": {
        "k": { "type": "integer", "minimum": 1 },
        "metric": { "type": "string", "enum": ["quantity", "revenue", "orders"] }
      }
    }
  }
}
```

### 3.3. Phân tầng: Điều gì JSON Schema bắt được vs Điều gì cần Python Semantic Validator?

1. **JSON Schema bắt trực tiếp**:
   * Mọi field lạ ở gốc hoặc trong `period`, `filters`, `ranking` (`additionalProperties: false`)[cite: 6, 7].
   * Thiếu bất kỳ required key nào[cite: 6, 7].
   * Giá trị ngoài `enum`[cite: 6, 7].
   * **Lưu ý đặc biệt về `bool` và `int` trong Python**: Trong chuẩn JSON (và thư viện `jsonschema` của Python), `true`/`false` là kiểu `boolean`, **không phải** `integer` (nên `jsonschema` tự động reject `ranking.k = true`). Tuy nhiên, nếu viết validator bằng Python thuần mà dùng `isinstance(k, int)`, `isinstance(True, int)` sẽ trả về `True`[cite: 7]! Do đó, trong Python Validator bắt buộc phải dùng `type(val) is int` (giống cách `business/periods.py` và `sales.py` đã làm ở `if type(k) is not int or k <= 0`)[cite: 1, 7].

2. **Python Semantic Validator bắt buộc kiểm tra (Cross-field invariants)**:
   * **Ràng buộc `status`**:
     * Nếu `status == "unsupported"`: `unsupported_reason` phải khác `null`; đồng thời `operation`, `expected_type`, `period`, `comparison_period`, `filters`, `ranking` đều phải là `null` $\rightarrow$ Dispatcher trả ngay `Answer('abstain', reason=plan.unsupported_reason)`.
     * Nếu `status == "supported"`: `unsupported_reason` phải là `null`; `operation`, `expected_type`, `period`, `filters` phải khác `null`.
   * **Ràng buộc tham số của `period` / `comparison_period` theo `kind`**:
     * `kind in ("today", "yesterday", "this_week", "previous_week", "this_month", "previous_month", "previous_month_same_elapsed", "year_to_date", "before_period")`: tất cả `n`, `month`, `quarter`, `year`, `start_date`, `end_date` phải là `null`[cite: 1, 7].
     * `kind == "last_days"`: chỉ `n` (kiểu `type(n) is int and n >= 1`) khác `null`; các trường còn lại phải `null`[cite: 1].
     * `kind == "month"`: `month` (`1..12`) bắt buộc khác `null`, `year` có thể `int` hoặc `null`; các trường còn lại `null`[cite: 1].
     * `kind == "quarter"`: `quarter` (`1..4`) bắt buộc khác `null`, `year` có thể `int` hoặc `null`; các trường còn lại `null`[cite: 1].
     * `kind == "tet"`: `year` (`int`) bắt buộc khác `null`; các trường còn lại `null`[cite: 1].
     * `kind == "date_range"`: chỉ `start_date` và `end_date` khác `null` và `start_date <= end_date`[cite: 1, 7].
     * Nếu `comparison_period.kind == "previous_month_same_elapsed"`: chỉ cho phép khi `period.kind == "this_month"`[cite: 1, 6, 7]. Nếu `comparison_period.kind == "before_period"`: ánh xạ thành `periods.before(resolved_period)`[cite: 1].

### 3.4. Bảng Ma trận Dispatch & Ràng buộc Tổ hợp cho 10 Operations (`status == "supported"`)

| `operation` | `expected_type` | `comparison_period` | `ranking` | `filters.unit_mention` | `filters.product_mentions` / `product_group_mention` | Lệnh gọi `SalesMetrics` sau khi Resolver tạo `f: Filters` |
|---|---|---|---|---|---|---|
| `revenue` | `"number"` | `null` | `null` | Bắt buộc `null` | Cho phép | `sales.revenue(p, f)`[cite: 1] |
| `order_count` | `"number"` | `null` | `null` | Bắt buộc `null` | Cho phép | `sales.order_count(p, f)`[cite: 1] |
| `cancelled_orders` | `"number"` | `null` | `null` | Bắt buộc `null` | Cho phép | `sales.cancelled_orders(p, f)`[cite: 1] |
| `cancellation_rate` | `"percent"` | `null` | `null` | Bắt buộc `null` | **Bắt buộc `null` ở v1** *(Xem ghi chú dưới)* | `sales.cancellation_rate(p, f)` *(chỉ nhận filter cấp đơn)* |
| `average_order_value` | `"number"` | `null` | `null` | Bắt buộc `null` | Cho phép | `sales.average_order_value(p, f)`[cite: 1] |
| `quantity` | `"number"` | `null` | `null` | Cho phép (`str` hoặc `null`) | Cho phép | `sales.quantity(p, f, unit=resolved_unit)`[cite: 1] |
| `top_products` | `"list"` | `null` | `metric in ("quantity", "revenue")`, `k >= 1` | Bắt buộc `null` | Cho phép | `sales.top_products(p, k=r.k, metric=r.metric, filters=f)`[cite: 1] |
| `top_customers` | `"list"` | `null` | `metric in ("revenue", "orders")`, `k >= 1` | Bắt buộc `null` | **Bắt buộc `null` khi `metric == "orders"`** | `sales.top_customers(p, k=r.k, metric=r.metric, filters=f)` |
| `revenue_growth` | `"percent"` | Bắt buộc khác `null` | `null` | Bắt buộc `null` | Cho phép | `sales.revenue_growth(p, comp_p, f)`[cite: 1] |
| `revenue_share` | `"percent"` | `null` | `null` | Bắt buộc `null` | Yêu cầu ít nhất 1 trường trong `filters` khác `null` | `sales.revenue_share(p, f)`[cite: 1] |

*(Giải thích ràng buộc product filter cho `cancellation_rate` và `top_customers(metric="orders")`[cite: 7]: Nếu lọc sản phẩm trên `cancellation_rate`, mẫu số là "mọi đơn trong kỳ" hay "mọi đơn trong kỳ có chứa sản phẩm đó"? Vì chưa có điều khoản rulebook xác nhận mẫu số tỷ lệ hủy theo mặt hàng, v1 chủ động reject `product_mentions`/`product_group_mention` trên `cancellation_rate` và chỉ cho phép filter cấp đơn `channel`, `payment`, `customer_group`, `shift` — nơi cả tử số và mẫu số đều cùng là tập đơn thuộc kênh/ca đó. Tương tự với `top_customers(metric="orders")`[cite: 7]).*

### 3.5. Sáu Unit Tests bắt buộc cho Validator & Dispatcher (Theo yêu cầu Mục 3 của Codex)

```python
# 1. Test k=True (Python bool subclass of int trap) -> Phải bị Validator bác bỏ
def test_validator_rejects_boolean_as_ranking_k(base_top_products_plan):
    base_top_products_plan["ranking"]["k"] = True
    assert validate_plan(base_top_products_plan).is_valid is False

# 2. Test field lạ (additionalProperties: false) -> Phải bị Validator bác bỏ
def test_validator_rejects_unknown_field(base_revenue_plan):
    base_revenue_plan["denominator_filters"] = None
    assert validate_plan(base_revenue_plan).is_valid is False

# 3. Test unit_mention khác null trên metric không phải quantity -> Phải bị bác bỏ, không được phớt lờ
def test_validator_rejects_unit_on_revenue(base_revenue_plan):
    base_revenue_plan["filters"]["unit_mention"] = "ly"
    assert validate_plan(base_revenue_plan).is_valid is False

# 4. Test phân biệt previous_month (28/02) vs previous_month_same_elapsed (04/02) tại as_of 2026-03-04
def test_dispatcher_distinguishes_full_previous_month_and_same_elapsed(rules):
    p = Periods(rules, "2026-03-04")
    assert resolve_period(p, {"kind": "previous_month", "n": None, "month": None, "quarter": None, "year": None, "start_date": None, "end_date": None}) == DateRange("2026-02-01", "2026-02-28")
    assert resolve_period(p, {"kind": "previous_month_same_elapsed", "n": None, "month": None, "quarter": None, "year": None, "start_date": None, "end_date": None}) == DateRange("2026-02-01", "2026-02-04")

# 5. Test plan unsupported -> Trả về Answer('abstain'), không chạm vào SalesMetrics
def test_dispatcher_returns_abstain_for_unsupported_plan(tables, rules):
    plan = {
        "version": "1.0", "status": "unsupported", "unsupported_reason": "unsupported_domain",
        "operation": None, "expected_type": None, "period": None, "comparison_period": None,
        "filters": None, "ranking": None
    }
    ans = dispatch_plan(plan, tables, rules, "2026-03-04")
    assert ans.type == "abstain"

# 6. Test thực thể trong filters không resolve được vào danh mục shop -> Resolver chặn lại, không ném mã giả vào SalesMetrics
def test_unresolved_entity_does_not_masquerade_as_valid_filter(tables, rules, base_revenue_plan):
    base_revenue_plan["filters"]["product_mentions"] = ["Món không tồn tại XYZ"]
    ans = dispatch_plan(base_revenue_plan, tables, rules, "2026-03-04")
    # Tùy policy chốt cho unresolved mention (abstain ở v1 khi chưa có bằng chứng gold), không được trả 0 ngầm như channel lạ
    assert ans.type == "abstain"
```

---

## Mục 4: Chốt Semantics cho `revenue_share` (Tử số, Mẫu số, Kiểm tra Luật & Chính sách v1)

### 4.1. Phân biệt "Tỷ trọng (Share)" và "Tỷ số độc lập (Ratio)"
* Phản chứng của Codex rất xác đáng: nếu cho phép truyền `filters = Filters(product_ids=('P1',))` (doanh thu 90) và `denominator_filters = Filters(product_ids=('T',))` (doanh thu 10) một cách độc lập, phép tính sẽ trả về `900%`[cite: 6, 7]. Đó là **tỷ số giữa hai tập rời nhau (Ratio)**, không phải là **tỷ trọng (Share)** ($0\% \le \text{Share} \le 100\%$ khi doanh thu dòng không âm)[cite: 6, 7].

### 4.2. Chốt Semantics chuẩn cho `revenue_share`
1. **Chính sách cho `QueryPlan v1` (Hoãn parent-share sang v1.1, giữ v1 nhỏ và chặt)**[cite: 6, 7]:
   * Ở `QueryPlan v1`, `revenue_share` **luôn có mẫu số mặc định là toàn bộ cửa hàng trong cùng kỳ (`Filters()`)**[cite: 1, 6, 7].
   * Nếu câu hỏi yêu cầu tính tỷ trọng trong một tập con cha (VD: *"Doanh thu Cà phê chiếm bao nhiêu % doanh thu nhóm Đồ uống?"*) hoặc tỷ số giữa hai thực thể độc lập, tầng NLU ở v1 phải đánh dấu `status: "unsupported"`, `unsupported_reason: "unsupported_comparison_or_denominator"` $\rightarrow$ runtime trả **`Answer('abstain')`**[cite: 6, 7]. Schema v1 cố tình **không có trường `denominator_filters`** để ngăn chặn hoàn toàn việc LLM tự điền mẫu số sai[cite: 6, 7].
2. **Sửa lỗi kiểm tra Rulebook trong `SalesMetrics.revenue_share` ngay ở v1**:
   * Hiện tại `sales.py:340` luôn gọi `self.rules.require('Doanh thu theo nhóm khách', 'doanh thu ca shop')` cho mọi lời gọi `revenue_share`, khiến việc tính tỷ trọng nhóm hàng (`Filters(product_group='Đồ uống')`) bị phụ thuộc sai vào dòng luật của nhóm khách[cite: 1, 6, 7].
   * **Cách sửa chính xác**:
     * Khi `filters.customer_group is not None`: bắt buộc kiểm tra `self.rules.require('Doanh thu theo nhóm khách', 'cot nhom khach', 'khong thuoc nhom nao', 'doanh thu ca shop')`[cite: 1, 7].
     * Khi `filters.customer_group is None`: kiểm tra quy tắc doanh thu chung (`self._revenue_rule()`) và các rule tương ứng với bộ lọc đang bật trong `filters` (được kiểm tra tự động trong `_orders` và `_line_sales` như `'Nhóm hàng'`, `'Doanh thu theo hình thức thanh toán'`, `'Ca sáng, ca chiều'`)[cite: 1, 7].
3. **Định nghĩa sẵn Invariant cho `v1.1` (khi mở rộng hỗ trợ `parent_filters` trong tương lai)**[cite: 6, 7]:
   * Nếu bổ sung tham số `denominator_filters: Filters = Filters()`, hàm `revenue_share` bắt buộc định nghĩa **Tử số thực sự là giao của hai phạm vi**:
     $$\text{Scope}_{\text{num}} = \text{Scope}(\text{filters}) \cap \text{Scope}(\text{denominator\_filters})$$
   * Với mọi trường $f \in \{\text{channel}, \text{payment}, \text{customer\_group}, \text{shift}, \text{product\_group}\}$: nếu `denominator_filters.f` khác `None`, thì `filters.f` phải hoặc bằng `None` (tức kế thừa từ mẫu số) hoặc bằng chính `denominator_filters.f`. Nếu xung đột (VD: tử lọc `channel='online'`, mẫu lọc `channel='tai_quan'`), hoặc nếu tập sản phẩm của tử không phải là tập con của nhóm hàng ở mẫu (`not set(num_products).issubset(set(den_products))`), hàm phải **raise `ValueError('Numerator filter must be a subset of denominator filter for share calculation')`**[cite: 6, 7].
   * Khi kiểm tra luật (`rules.require`), phải kiểm tra cho **cả `filters` lẫn `denominator_filters`** (vì cả hai đều đi qua `self._revenue(period, ...)` nên mọi điều khoản của `customer_group`, `payment`, `product_group`, `shift` ở cả tử số và mẫu số đều được kích hoạt đầy đủ)[cite: 6, 7].

---

## Mục 5: Phân biệt các chiến lược Split & Tiêu chí nghiệm thu (Plan Execution vs NLU)

### 5.1. Phân biệt rõ 2 loại Split hồi cứu trên tập Train (30 doanh nghiệp, 10 nhóm mẫu file A–J)

Vì toàn bộ 30 doanh nghiệp train đã được khảo sát khi xây dựng `loader/` và `DESC_RULES`[cite: 2, 4, 7], mọi cách chia trên 30 doanh nghiệp này đều là **kiểm chứng hồi cứu (retrospective evaluation)**, nhưng phục vụ hai mục đích hoàn toàn khác nhau[cite: 6, 7]:

| Loại Split | Định nghĩa cấu trúc | Đo lường được điều gì? | KHÔNG đo lường được điều gì? |
|---|---|---|---|
| **1. Stratified Business Split (In-group Generalization)** | Chia 30 doanh nghiệp thành Dev / Eval sao cho các nhóm mẫu file nhiều doanh nghiệp (`A`: 6, `B`: 5, `C`: 5, `E`: 3, `F`: 3, `H`: 3)[cite: 2] có mặt ở cả Dev và Eval. | Đo xem với **cùng một họ phần mềm/mẫu file đã biết** (VD: KiotViet nhóm A, MISA nhóm C), hệ thống xử lý tốt thế nào khi gặp danh mục mặt hàng mới, tên khách mới, khoảng ngày mới và cách hỏi mới. | **Không đo được** khả năng tổng quát hóa của `loader/` và NLU khi gặp một định dạng file/cấu trúc bảng hoàn toàn mới chưa từng có trong Dev[cite: 6, 7]. |
| **2. Group-Disjoint Split (Leave-Template-Group-Out)** | Giữ nguyên cả cụm nhóm mẫu file ở một phía (không có bất kỳ nhóm nào xuất hiện ở cả Dev và Eval; tương tự triết lý của `generalize_check.py`)[cite: 2, 6, 7]. Mọi từ điển/rule học từ dữ liệu phải được rebuild chỉ từ các nhóm trong Dev[cite: 2, 6, 7]. | Đo sát nhất rủi ro khi chạy trên `public_test` / `private_test` có mẫu sổ bán hàng mới[cite: 6, 7]. | Do các nhóm `D` (2), `G` (1), `I` (1), `J` (1) có rất ít doanh nghiệp[cite: 2], một fold đơn lẻ sẽ nhỏ; cần đánh giá theo cơ chế Leave-One-Group-Out (LOGO) hoặc giữ cố định 2–3 nhóm đại diện làm Group-Disjoint Eval[cite: 2, 7]. |

### 5.2. Tách biệt Tiêu chí nghiệm thu của "Plan Execution Engine" và "NLU (Question -> Plan)"

Đồng thuận hoàn toàn với Codex: không cần chọn cố định 20/10 doanh nghiệp ngay lúc này để nghiệm thu phần Deterministic Engine, và phải tách bạch **"0 câu bộ chọn hiện tại bắt được"** khỏi **"0 câu tồn tại trong dữ liệu train"**[cite: 6, 7].

#### Giai đoạn A: Nghiệm thu Deterministic Plan Execution (`QueryPlan v1` $\rightarrow$ `Validator` $\rightarrow$ `Resolver` $\rightarrow$ `SalesMetrics` $\rightarrow$ `Answer`)
* **Đầu vào kiểm thử**: Các `QueryPlan v1` được tạo tất định (từ unit test tổng hợp và từ bộ chọn câu hỏi bảo thủ trên train, không dùng LLM)[cite: 6, 7].
* **Tiêu chí nghiệm thu (Acceptance Criteria)**:
  1. **Schema & Semantic Validator**: Pass 100% bộ unit test biên (bao gồm 6 test ở Mục 3.5 và 3 test dependency ở Mục 1.4). Không một plan bất hợp lệ nào (như `k=True`, field lạ, `unit` gắn vào `revenue`) lọt qua được Validator[cite: 6, 7].
  2. **Hồi quy 409 câu chuẩn**: Khi chuyển đổi 417 câu của `verify_business.py` sang định dạng `QueryPlan v1` JSON và chạy qua `Resolver` + `Dispatcher`, kết quả đạt đúng **409/409 khớp gold và khớp gọi trực tiếp Python API, 8 câu legacy skipped, 0 lỗi phát sinh**[cite: 1, 6, 7].
  3. **Mở rộng bộ chọn bảo thủ cho 7 hàm còn lại của `SalesMetrics`**:
     * Viết các bộ chọn dựa thuần túy trên cấu trúc câu hỏi (strict regex/pattern, **tuyệt đối không lọc theo đáp án gold hay lọc bỏ câu tính sai**)[cite: 4, 7].
     * Báo cáo minh bạch cho từng hàm trong 10 hàm của `SalesMetrics` theo đúng 5 con số:
       * `selector_matched`: Số câu trong 3000 câu train mà bộ chọn bảo thủ bắt được (nếu bằng 0 thì ghi rõ là **"0 câu bộ chọn hiện tại hỗ trợ"**, không kết luận là train không có câu hỏi loại đó)[cite: 6, 7].
       * `executed`: Số câu chạy ra `Answer` hoàn chỉnh.
       * `abstained_or_error`: Số câu bị `DataError`, `UnsupportedRule`, hoặc `AmbiguousEntity`.
       * `matched_gold`: Số câu khớp `train/answers.jsonl` (cả `type` và `answer`).
       * `mismatched_gold`: Số câu lệch `type` hoặc lệch giá trị (kèm phân tích nguyên nhân: do bộ chọn bắt nhầm câu hỏi khác nghĩa, do lỗi mapping của `loader`, hay do bug trong `business/`)[cite: 7].

#### Giai đoạn B: Nghiệm thu tầng NLU (Câu hỏi tự nhiên $\rightarrow$ `QueryPlan v1`)
* **Đầu vào kiểm thử**: Câu hỏi tiếng Việt tự nhiên + metadata schema cửa hàng (không được nhìn gold)[cite: 1, 7].
* **Tiêu chí nghiệm thu (Acceptance Criteria)**:
  1. **Đánh giá trung gian (Plan-level accuracy)**: Xây dựng một tập nhỏ (ví dụ 50–100 câu hỏi đa dạng được gán nhãn `QueryPlan v1` chuẩn một cách độc lập dựa trên câu hỏi, trước khi chạy model) để đo tỷ lệ LLM sinh đúng `operation`, `period`, `comparison_period`, `filters`[cite: 7].
  2. **Đánh giá đầu-cuối (End-to-End Metrics) trên cả Stratified Split và Group-Disjoint Split**:
     * Báo cáo đầy đủ: **PA Score** ($\frac{\text{Correct} - \text{Wrong}}{N}$), **Coverage** ($\frac{\text{Answered}}{N}$), **Precision trên các câu đã trả lời** ($\frac{\text{Correct}}{\text{Answered}}$), tỷ lệ lỗi phân rã theo nguyên nhân (Wrong Type, Wrong Period, Entity Resolution Error, Loader Error, Runtime Abstain), và **Thời gian chạy trung bình / câu**[cite: 1, 7].
     * Mọi trường hợp `status == "unsupported"`, lỗi schema, lỗi resolve thực thể hoặc `DataError` đều phải kết thúc ở `type: "abstain"` (0 điểm), không được tự ý biến thành `type: "unanswerable"` trừ khi `SalesMetrics` xác nhận `_Unavailable` trên thực thể và bảng đã được kiểm chứng[cite: 1, 6, 7].