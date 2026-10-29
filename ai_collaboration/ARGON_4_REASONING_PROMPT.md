# DATA-MATE (ZALO AI CHALLENGE 2026) — STRATEGIC REASONING PROMPT FOR ARGON 4
> **Mục tiêu:** Cung cấp toàn bộ bối cảnh kỹ thuật, dữ liệu thực nghiệm, ràng buộc cuộc thi và các nghịch lý cốt lõi của dự án DataMate để Argon 4 (Mô hình Deep Reasoning / Thinking) phân tích sâu, phản biện và đề xuất giải pháp kiến trúc đột phá, giải quyết triệt để các bế tắc hiện tại.

---

## 1. TỔNG QUAN BÀI TOÁN & CÁC RÀNG BUỘC BẤT KHẢ KHÁNG (HARD CONSTRAINTS)

### 1.1. Bản chất đề bài DataMate
* **Nhiệm vụ:** Xây dựng một AI Agent tự động trả lời các câu hỏi bằng tiếng Việt đời thường (chứa từ viết tắt, tiếng lóng, không dấu) trên dữ liệu bảng có cấu trúc thô (CSV, Excel `.xlsx`, SQLite `.sqlite`) của các hộ kinh doanh và doanh nghiệp nhỏ (SME) tại Việt Nam.
* **Gói dữ liệu đầu vào cho mỗi doanh nghiệp:**
  * Một hoặc nhiều file dữ liệu thô (độ lớn từ vài trăm đến ~300.000 dòng).
  * Một file `README.md` mô tả ngữ cảnh kinh doanh và từ điển dữ liệu (chất lượng không đồng đều: có shop rất chi tiết, có shop sơ sài hoặc gần như để trống).
  * `rulebook.md`: Sổ tay quy tắc nghiệp vụ mặc định của split (định nghĩa doanh thu, loại trừ đơn hủy/trả, bán chạy theo quantity hay revenue, giá vốn bình quân gia quyền theo lô, v.v.). **Lưu ý: `rulebook.md` có thể THAY ĐỔI giữa các split**, Agent không được hard-code.
  * `calendar.csv`: Bảng tra cứu lịch Âm – Dương (phục vụ tính Tết từ 23 tháng Chạp đến hết mùng 10 Tết, ngày lễ, rằm).
  * `questions.jsonl`: Danh sách câu hỏi, mỗi câu kèm `as_of_date` (ngày "hôm nay" giả định để làm mốc thời gian tương đối như "tháng này", "tuần rồi", "hôm qua").
* **Đầu ra quy định (`submission.jsonl`):**
  * Đúng 1 trong 9 kiểu dữ liệu: `number`, `percent`, `string`, `date`, `boolean`, `list`, `table`, `unanswerable` (khi dữ liệu không đủ để trả lời), `abstain` (Agent chủ động từ chối trả lời).
  * Khớp chính xác tuyệt đối (Exact Match / Tolerance = 0, làm tròn 2 chữ số thập phân cho số/percent, Unicode NFC + lowercase cho string).

### 1.2. Hàm mục tiêu chấm điểm: Penalized Accuracy (PA)
Điểm số bảng xếp hạng tính theo công thức:
$$\text{PA} = \frac{1}{N} \sum_{i=1}^N s_i$$
Trong đó:
* $s_i = \mathbf{+1}$: Trả lời **ĐÚNG** (cả kiểu dữ liệu và giá trị khớp hoàn toàn).
* $s_i = \mathbf{0}$: Agent chủ động **TỪ CHỐI TRẢ LỜI (`abstain`)** (hoặc bị thiếu câu hỏi trong file nộp).
* $s_i = \mathbf{-1}$: Trả lời **SAI** (kể cả việc cố trả lời một câu vốn dĩ là `unanswerable`).

> **Ý nghĩa sống còn của hàm PA:** Cứ **1 câu SAI sẽ triệt tiêu hoàn toàn điểm của 1 câu ĐÚNG**! 
> Về mặt toán học: Thà `abstain` nhận 0 điểm còn hơn đoán mò mà xác suất đúng $P(\text{đúng}) < 50\%$.

### 1.3. Ràng buộc kỹ thuật & Phần cứng
1. **Giới hạn mô hình:** Tổng số lượng tham số của TẤT CẢ các mô hình trong quá trình inference (LLM, embedding, reranker, classifier...) **$\le$ 15B tham số**. Cho phép mọi kỹ thuật quantization.
2. **Offline 100%:** Quá trình suy luận chạy hoàn toàn offline bên trong Docker container; cấm API bên ngoài, cấm kết nối mạng, cấm tải model/data trong lúc chạy.
3. **Phần cứng kiểm chứng:** Máy chủ BTC trang bị **2 × NVIDIA RTX 5090 (32GB VRAM mỗi card, tổng 64GB VRAM) và 512GB RAM**. Kiến trúc Blackwell yêu cầu CUDA $\ge$ 12.8.
4. **Giới hạn thời gian:** Tối đa **6 GIỜ** (wall-clock time) để chạy xong toàn bộ tập Private Test (~500 câu), tính cả thời gian load model.
5. **Thực thi mã lệnh:** BTC cho phép và khuyến khích Agent tự sinh code và thực thi bên trong container; thư mục `/data` mount read-only.
6. **Timeline:** Hạn nộp Docker hoàn chỉnh: **23:59 ngày 16/11/2026**. Private Test diễn ra từ 20/11 – 23/11/2026 (sẽ xuất hiện các loại hình kinh doanh mới chưa từng có trong Train/Public Test).

---

## 2. HIỆN TRẠNG DỰ ÁN & KẾT QUẢ ĐO ĐẠC THỰC NGHIỆM

### 2.1. Kiến trúc hiện tại của hệ thống (Pipeline 4 tầng)
Dự án đã triển khai một kiến trúc phân tầng rất kỷ luật nhằm tách biệt hoàn toàn giữa việc hiểu ngôn ngữ tự nhiên và tính toán số liệu:

```
[Câu hỏi + as_of_date] 
        │
        ▼
   [Tầng NLU]  ──────>  Qwen2.5-7B-Instruct (vLLM)
        │               Sinh QueryPlan v1 (JSON cấu trúc nghiêm ngặt)
        ▼
 [Tầng QueryPlan] ───>  Parser nghiêm ngặt + Validator + Resolver 
        │               (Resolve as_of_date, calendar, entity filters)
        ▼
 [Tầng Business] ────>  Thư viện Python/Pandas tính toán tất định (Deterministic)
        │               (Đã mã hóa sẵn 10 operations sales chuẩn theo Rulebook)
        ▼
  [Tầng Answer]  ────>  Emit kết quả đúng 1 trong 9 kiểu dữ liệu chuẩn
```

* **`loader/`:** Đọc dữ liệu thô (.csv, .xlsx, .sqlite) của từng shop, xử lý missingness (`pd.NA`), join tên khách hàng, lưu cache thành các bảng chuẩn (canonical tables: `don_hang`, `dong_hang`, `mat_hang`, `cua_hang`, `khach_hang`) định dạng Parquet.
* **`business/`:** Đã cài đặt 10 hàm nghiệp vụ tất định tuân thủ nghiêm ngặt `rulebook.md`:
  `revenue`, `order_count`, `average_order_value`, `cancellation_rate`, `cancelled_orders`, `revenue_growth`, `quantity`, `top_products`, `top_customers`, `revenue_share`.
* **`queryplan/`:** Đóng vai trò DSL trung gian. Nhận JSON Plan từ NLU, validate schema, resolve thời gian theo `calendar.csv` và `as_of_date`, resolve filter theo catalog của shop, rồi dispatch sang `business/`. Nếu không resolve được entity hoặc capability không hỗ trợ $\rightarrow$ trả về `abstain` hoặc `unanswerable`.
* **`nlu/`:** Sử dụng **Qwen2.5-7B-Instruct** với prompt và JSON Schema v2 ép cấu trúc output (Constrained Decoding). Vừa qua đã chạy private batch trên GPU Modal (NVIDIA A10).

### 2.2. Kết quả thực nghiệm thực tế (Mốc Baseline 29/10/2026)
Trên tập **Evaluation cố định (632 câu hỏi thuộc 6 doanh nghiệp holdout)**:
* **303 câu ĐÚNG (+303 điểm)**
* **182 câu SAI (-182 điểm)**
* **147 câu TỪ CHỐI / ABSTAIN (0 điểm)**
* **Penalized Accuracy (PA):** $(303 - 182) / 632 = \mathbf{19.15\%}$
* **Coverage:** $76.74\%$ (485 câu chịu trả lời / 632 câu)
* **Precision trên câu trả lời:** $62.47\%$ (303 đúng / 485 trả lời)

---

## 3. CÁC NGHỊCH LÝ & BẾ TẮC CỐT LÕI CẦN ARGON 4 REASONING

Dự án có kiến trúc bài bản nhưng điểm PA hiện tại chỉ đạt **19.15%**. Khoảng cách từ 19% đến mức cạnh tranh Top 2 (dự kiến cần PA $\ge$ 50% - 60%+) đang bị chặn bởi 4 vấn đề căn cơ sau:

### NGHỊCH LÝ 1: Trần giới hạn của DSL cố định (QueryPlan) vs. Rủi ro của Free-form Code Generation
* **Điểm yếu của DSL hiện tại:** 
  Tầng `business/` và `queryplan/` hiện tại chỉ hỗ trợ **10 operations (hầu như toàn bộ thuộc mảng Bán hàng / Doanh thu)**. 
  Tuy nhiên, thể lệ cuộc thi và dữ liệu thực tế bao gồm rất nhiều bài toán đa dạng khác:
  * Công nợ (*"còn ai nợ tiền chưa trả?"*),
  * Tồn kho & Hạn dùng (*"thuốc nào sắp hết hạn trong kho?"*, *"tồn kho sản phẩm X còn bao nhiêu?"*),
  * Quản lý lượt khám bệnh, chấm công nhân sự, chi phí đầu vào hợp tác xã, thống kê hộ dân xã...
  * Đặc biệt: **Private Test sẽ đưa vào các loại hình kinh doanh hoàn toàn mới**.
  $\rightarrow$ Nếu giữ nguyên kiến trúc DSL cứng, toàn bộ các câu hỏi thuộc domain mới sẽ bị `unsupported_capability` (buộc phải `abstain` $\rightarrow$ PA bị trần chặn ở mức thấp) hoặc NLU cố ép vào 10 operation sales $\rightarrow$ sinh ra đáp án SAI (-1 điểm). Nhưng nếu team cố code thêm DSL cho từng domain thì không kịp thời gian (hạn 16/11) và không thể đón đầu được schema của Private Test!
* **Rủi ro của Free-form Code Generation (Text-to-Python/Pandas/SQL):**
  Nếu chuyển sang để LLM tự viết code Python tự do để query bất kỳ bảng nào, hệ thống sẽ linh hoạt với mọi domain. Nhưng LLM 7B–14B rất dễ sinh code vi phạm các quy tắc ngầm của `rulebook.md` (ví dụ: quên trừ đơn hủy/trả hàng, tính sai VAT, join nhầm bảng, tính sai mốc thời gian relative) $\rightarrow$ sinh ra đáp án SAI và bị phạt $-1$ điểm hàng loạt!
* **👉 Câu hỏi cho Argon 4:**
  1. Đâu là kiến trúc tối ưu để giải quyết thế tiến thoái lưỡng nan này?
  2. Một kiến trúc **Hybrid (Lai)** có khả thi không: DSL Deterministic cho các mẫu câu Sales chuẩn (high precision), kết hợp với một **Code-Generation Agent có nhúng Rulebook Guardrails** cho phần long-tail / domain mới? Nếu làm Hybrid, cơ chế phân luồng (Routing) và kiểm soát rủi ro điểm phạt $-1$ phải thiết kế như thế nào?

---

### NGHỊCH LÝ 2: Giải phẫu 182 câu SAI & Chiến lược Tối ưu hóa Hàm PA (Penalized Accuracy)
* **Vấn đề cốt tử:** 182 câu trả lời SAI đã "nuốt chửng" 182 điểm của 303 câu ĐÚNG. Nếu bằng cách nào đó nhận diện được các câu có rủi ro cao và chuyển 100 câu sai thành `abstain` (0 điểm), PA sẽ lập tức tăng từ **19.15% lên 34.97%** mà không cần trả lời đúng thêm câu nào!
* **Các nguyên nhân gây SAI chính được ghi nhận trong audit:**
  1. **Entity Grounding Failure:** Người dùng hỏi tên viết tắt/từ lóng (*"xi măng hà tiên"*, *"sting dâu"*), NLU trích xuất string entity nhưng không khớp với text trong database $\rightarrow$ filter ra rỗng hoặc match sai hàng.
  2. **Implicit Rulebook Violations:** Câu hỏi không nêu rõ nhưng Rulebook quy định ngầm (ví dụ: "bán chạy" mặc định theo `quantity`, khung giờ Tết âm lịch, doanh thu không gồm VAT).
  3. **Lỗi logic Unanswerable:** Dữ liệu thực tế của shop bị thiếu cột/thiếu giá vốn, đáp án chuẩn của BTC là `unanswerable`, nhưng NLU không biết dữ liệu thiếu nên vẫn sinh plan tính ra con số 0 hoặc số ảo $\rightarrow$ Bị phạt $-1$ điểm vì cố trả lời câu unanswerable.
  4. **Time & Offset Ambiguity:** Câu hỏi hỏi *"tháng 1"* nhưng `as_of_date` ở năm 2026, câu hỏi không ghi năm $\rightarrow$ NLU tính nhầm năm 2026 thay vì năm có dữ liệu gần nhất trong quá khứ.
* **👉 Câu hỏi cho Argon 4:**
  1. Làm thế nào để xây dựng một cơ chế **Confidence Estimation / Preflight Verification** đáng tin cậy để Agent tự lượng giá rủi ro trước khi xuất kết quả? Tiêu chí định lượng nào để quyết định: `Answer` vs `Abstain`?
  2. Làm sao Agent biết được một câu hỏi là `unanswerable` (do thiếu thông tin trong data thô) trước khi cố sinh query tính toán?

---

### NGHỊCH LÝ 3: Khả năng Tổng quát hóa Schema trên Unseen Businesses (Zero-Shot Schema Grounding)
* **Thực tế dữ liệu:** 
  Tập Private Test hoàn toàn bí mật, có 10–20 doanh nghiệp mới với các file CSV/Excel/SQLite có cấu trúc cột, tên bảng và chất lượng README hoàn toàn không đoán trước được.
  Hệ thống phải chạy tự động 100% ("No human in the loop"), không ai can thiệp để viết code mapper bằng tay như lúc chuẩn bị tập Train.
* **👉 Câu hỏi cho Argon 4:**
  1. Làm thế nào để hệ thống tự động hóa khâu **Schema Profiling & Normalization** khi container khởi động trên một thư mục `/data/<business_id>/` hoàn toàn mới?
  2. Phương pháp **Entity Retrieval / Linking (Grounding)** nào vừa nhẹ, chạy cực nhanh offline, không vượt quá giới hạn 15B tham số, nhưng xử lý tốt tiếng Việt viết tắt/không dấu/từ lóng để nối câu hỏi với bảng dữ liệu?

---

### NGHỊCH LÝ 4: Tối ưu Hạ tầng Offline Docker & Tận dụng 2 × RTX 5090 trong Giới hạn 6 Giờ
* **Hiện trạng:** Code NLU vừa qua chạy batch trên Modal Cloud (A10). Nhưng hạn nộp bài là **Docker Image chạy Offline hoàn toàn**, nộp trước ngày 16/11.
* **Tài nguyên BTC cấp:** 2 × NVIDIA RTX 5090 (64GB VRAM tổng, Blackwell architecture, yêu cầu CUDA $\ge$ 12.8, 512GB RAM). Số câu test: ~500 câu. Thời gian tối đa: 6 giờ (~43 giây/câu).
* **👉 Câu hỏi cho Argon 4:**
  1. Với 64GB VRAM và ngân sách tham số $\le$ 15B, cấu hình mô hình nào là tối ưu nhất? (Ví dụ: Qwen2.5-14B-Instruct Quantized AWQ/GPTQ hay Qwen2.5-7B nguyên bản? Có nên dùng 1 SLM 1.5B/3B phụ trách Routing/Classification + 1 LLM 7B/14B phụ trách Reasoning/Code Generation không?)
  2. Inference engine nào tối ưu và tương thích tốt nhất với GPU RTX 5090 Blackwell trong môi trường Docker offline (vLLM, TensorRT-LLM, hay SGLang)? Cần lưu ý gì về build CUDA 12.8 và PyTorch?
  3. Kiến trúc pipeline thực thi trong `predict.sh` nên được thiết kế như thế nào để đảm bảo tính tái lập (Reproducibility: $|\text{PA}_{\text{upload}} - \text{PA}_{\text{rerun}}| \le 0.03$) và ghi đầy đủ bằng chứng suy luận vào `/result/logs/` theo yêu cầu của thể lệ?

---

## 4. YÊU CẦU ĐẦU RA DÀNH CHO ARGON 4 (OUTPUT CONTRACT)

Khi phản biện và lập luận, yêu cầu Argon 4:
1. **Không đưa ra lời khuyên chung chung kiểu giáo khoa** (như "cần thu thập thêm dữ liệu", "cần fine-tune mô hình", "cần làm RAG"). Phải bám sát từng dòng mã, số liệu thực nghiệm và ràng buộc của DataMate.
2. **Cung cấp giải pháp kiến trúc cụ thể:** Vẽ luồng dữ liệu (Dataflow / Architecture diagram), đặc tả logic của các thành phần, cấu trúc prompt hoặc pseudo-code nếu cần.
3. **Phân tích Đánh đổi (Trade-off Matrix):** So sánh rõ ràng ưu điểm, nhược điểm, độ phức tạp cài đặt và rủi ro điểm phạt PA của từng phương án đề xuất.
4. **Kế hoạch hành động cụ thể từ nay đến 16/11:** Chia thành các bước ưu tiên theo thứ tự tác động lớn nhất đến điểm số PA (What to build first, What to reject).

