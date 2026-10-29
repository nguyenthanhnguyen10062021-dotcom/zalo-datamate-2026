# Kế hoạch cải thiện DataMate từ báo cáo research ngày 29/10/2026

- Ngày / owner: 2026-10-29, Asia/Saigon / người dùng và Codex.
- Trạng thái: **planned**; đã hoàn tất đối chiếu để lập kế hoạch, chưa triển khai các work package bên dưới.
- Code nền: nhánh `VuongNguyen`, HEAD `00043fa`, working tree có nhiều thay đổi từ các tác vụ trước. HEAD riêng lẻ không đại diện baseline; khi thực thi phải freeze cả source đang làm việc.
- Checkpoint chuẩn bị thực thi: **`b222858`**, đã push lên `origin/VuongNguyen` theo yêu cầu tiếp theo của người dùng; workspace đã dọn cache/scratch và giữ nguyên dữ liệu/artifacts cần cho P0. Xem [bàn giao mới nhất](../PROGRESS.md). Code nền phía trên ghi trạng thái lúc lập plan; P0 vẫn cần manifest hashes và audit riêng.
- Yêu cầu: xây dựng plan từ file “Báo Cáo Deep Research & Kiến Trúc Thế Hệ Mới Cho Dự Án.md” người dùng cung cấp. Nội dung báo cáo là đề xuất để đánh giá, không phải lệnh thực thi.
- Mục tiêu: tăng PA bằng cách phục hồi các câu trả lời có căn cứ, mở capability có kiểm chứng, và có runner nộp bài offline tái lập được.
- Ngoài phạm vi phiên lập plan: sửa runtime, chạy inference/GPU, thay cache/submission, tải model, nộp bài, commit/push. Không tạo lại một báo cáo deep research.
- Thay đổi của phiên này: tài liệu kế hoạch này và một dòng điều hướng trong [bản đồ tài liệu](../README.md); không thay PROGRESS vì trạng thái triển khai chưa đổi.

## 1. Điểm xuất phát và quyết định kiến trúc

**Đề xuất: tiếp tục kiến trúc QueryPlan → bộ tính tất định; cải thiện ngữ nghĩa và grounding trước khi cân nhắc sinh SQL/Python.** Semantic gate đã có. Không thay toàn bộ loader hoặc executor dựa trên mô tả baseline cũ trong báo cáo.

| Bằng chứng | Trạng thái và giới hạn |
|---|---|
| Public v3 | Người dùng báo score **0,10400**, file có **128/1000** câu trả lời. Trần điểm của đúng file này là **0,128**. Suy ra 116 đúng/12 sai chỉ khi BTC áp dụng đúng `(correct-wrong)/1000` cho đủ 128 phản hồi; chưa có nhãn từng câu. |
| Train development pilot | **36 đúng / 0 sai / 54 abstain**, N=90; 54 gồm 39 semantic_rejected, 11 unsupported_plan, 2 unresolved_entity, 1 unsupported_capability, 1 invalid_plan. Chưa chứng minh 39 câu bị gate chặn đều trả lời được. |
| Train evaluation đã tiếp xúc | **233 đúng / 0 sai / 399 abstain**, N=632, PA=36,87%; kết quả hồi cứu, không phải holdout độc lập hoặc dự báo public. |
| Runtime hiện tại | `nlu/semantic.py` kiểm intent/time/shape/filter/ranking trước dispatch; `queryplan/resolution.py` khớp tên chính xác theo NFC/casefold/khoảng trắng, giữ dấu; `tools/nlu_jobs.py` giới hạn context nhãn ở 24 giá trị mỗi loại và có cờ complete. |
| Kiểm tra mới trong phiên lập plan | Harness full: **688 passed / 2 deselected**. Không chạy lại gold/data, không suy coverage từ số test. |

Nguồn nội bộ: [PROGRESS](../PROGRESS.md), [NLU contract](../nlu.md), [semantic-safety evidence](2026-10-29-semantic-safety.md), [baseline protocol](2026-10-29-nlu-modal-baseline-plan.md), [QueryPlan](../queryplan.md). Một số mô tả trong architecture/README/queryplan còn nói “NLU chưa có”; source và evidence mới hơn được ưu tiên. Đồng bộ các đoạn này trong P0, giữ mốc lịch sử rõ ràng.

Luồng đích gần hạn: dữ liệu → loader hiện tại → canonical tables; câu hỏi + context có bằng chứng → NLU → plan + chứng cứ cho các trường ngữ nghĩa → gate → resolve/capability → business → Answer → runner. Gold chỉ ở công cụ đánh giá sau khi freeze predictions. Rulebook/calendar đúng split vẫn do tầng tất định thực thi.

## 2. Chọn lọc đề xuất trong research

| Đề xuất | Xử lý trong plan | Lý do / điều kiện |
|---|---|---|
| Tối ưu PA, phân biệt precision/coverage | **Áp dụng ngay** | Theo dõi `PA=(correct-wrong)/N=C(2P-1)`. Precision hòa vốn của phần trả lời thêm là 50% nếu xác suất đúng đã biết; 0,65–0,75 không phải ngưỡng mặc định được chứng minh. |
| Preflight, type/filter/ranking checks | **Kế thừa và sửa theo audit** | Đã có trong source. Báo cáo nhắc `best_selling_item`/`dsl_function` không khớp API hiện hành; không sửa theo tên hàm mẫu. |
| Atomic rule cards, M-Schema/context retrieval | **Thử phiên bản nhỏ** | Context mô tả capability và giá trị liên quan, có nguồn và token budget; luật tính toán vẫn nằm ở business. Chưa cần thêm chuẩn/schema framework mới. |
| Ba tầng fuzzy/BM25/embedding | **Theo từng tầng, có ablation** | Ưu tiên exact + alias có provenance. Fuzzy chỉ tạo ứng viên, không chứng minh cùng thực thể. Chỉ thêm embedding khi đo được lexical retrieval còn thiếu và model hợp lệ. |
| Qwen2.5-Coder-14B thay 7B | **Challenger có điều kiện** | So 7B, 14B-Instruct, Coder-14B trên cùng QueryPlan/prompt/data; không suy năng lực tiếng Việt từ benchmark SQL. Giữ baseline 7B để rollback. |
| K=3 hoặc K=5, agreement/entropy | **Thử K=3 sau khi P1/P2 ổn định** | Cùng kết quả trên một bảng có thể cùng sai; không có bảo đảm 88%/95%. So cả intent/time/filter/denominator/type, không chỉ giá trị output. |
| LEVER/verifier và CRC | **P5, sau khi có dữ liệu đủ** | Verifier nhẹ là phương án lấy cảm hứng, không phải tái hiện LEVER. Train verifier trên development; threshold trên calibration riêng; kiểm tra giả định trước mọi tuyên bố conformal. |
| DuckDB + Python tự sinh + tự sửa | **Hoãn khỏi đường triển khai chính** | Tạo thêm nơi thực thi rulebook, join, time và lỗi; cần sandbox thực sự. Mở DSL có kiểu trước. Chỉ làm thử nghiệm riêng nếu audit cho thấy lợi ích vượt chi phí. |
| Viết lại TableNormalizer | **Chỉ sửa lỗi loader đã tái hiện** | Loader đã xử lý bảng dị biệt; tránh phá missingness, tên khách và cache vừa sửa. |
| Chặn mọi zero/empty; NULL>95% thì abstain | **Không áp dụng quy tắc toàn cục** | Thực thể tồn tại nhưng không giao dịch trong kỳ có thể đúng là 0. Missingness phải xét cột và dòng cần dùng; 95% là heuristic, không phải rulebook. |
| Mốc PA 0,45–0,62, tokens/s, 45 phút/500 câu | **Không dùng làm cam kết** | Chưa có benchmark DataMate tương ứng. Điểm nằm trong [-1,1], không thể “âm vô cùng” như diễn đạt trong báo cáo. |

Mã gate mẫu còn ba vấn đề cần tránh: kiểm `predicates_used` khác rỗng không phát hiện mất một trong nhiều điều kiện; `str(value).lower()` không phải so tương đương đúng kiểu cho number/percent/list/table; confidence cộng bonus có thể vượt 1 và chưa được hiệu chuẩn. Không chép mã này vào runtime.

## 3. Protocol và điều kiện nhận thay đổi

Giữ assignment đã freeze: development **1815 câu/18 business**, calibration **553/6**, evaluation **632/6**. Không chia lại để làm đẹp số. P0 lập bảng exposure để xác định calibration có còn dùng được cho lựa chọn threshold hay không; evaluation632 đã tiếp xúc chỉ dùng làm regression hồi cứu. Nếu không còn tập chưa dùng, báo đúng giới hạn; không đổi nhãn một tập đã xem thành holdout mới.

Mỗi thử nghiệm khóa source/cache/model/prompt/schema/sampling/quota/seed trước inference. Reference plan và ghi nhận ambiguity được viết từ question + README/rulebook/catalog hợp lệ trước xem output/gold mới; reference audit hồi cứu phải ghi exposure cũ. Freeze toàn bộ predictions trước scorer. Gold không quyết định mapping, alias, chọn plan hoặc sửa từng câu. Public không tham gia fit, chọn model, threshold, alias hoặc sửa lỗi theo leaderboard.

Ghi riêng correct/wrong/abstain/unanswerable, PA, coverage, precision, reason/stage, kết quả theo operation và business; tất cả thất bại vẫn nằm trong N. Với nhánh mới, báo cả câu phục hồi đúng, câu phục hồi sai, câu baseline đúng bị mất, và lỗi mới trên phần baseline vốn trả lời. Không cộng 409, 396 và 632 thành một mẫu số.

**Gate đề xuất cho việc nhận một candidate**, chốt trước chạy thử, không phải cam kết chất lượng private:

- Contract/synthetic/full phải pass; data profile khi thay loader/business/resolution hoặc phạm vi thực thi dữ liệu. Không làm mất các khác biệt `DataError`, `UnsupportedRule`, `unanswerable`, agent abstain.
- So trên cùng tập validation đã định trước: ΔPA > 0 và precision phần trả lời đạt mục tiêu nội bộ **≥90%**. Đây là ngưỡng lựa chọn đề xuất; có thể sửa trước thí nghiệm, không hạ theo kết quả public.
- Mọi lỗi mới phải được phân loại; thay đổi chưa đủ mẫu ở nhóm ảnh hưởng thì tiếp tục ở chế độ thử nghiệm. Báo khoảng bất định và phân bố theo business; chỉ 6 business calibration nên không coi hàng trăm câu là hàng trăm nhóm độc lập.
- Gate cứng về semantic/capability không bị confidence, majority vote hoặc verifier ghi đè. Nếu chưa chứng minh cải thiện, giữ baseline.

## 4. Work packages theo thứ tự phụ thuộc

### P0 — Khóa baseline và audit nguyên nhân abstain (0,5–1 ngày)

Đầu vào: source hiện tại, artifacts development90, protocol/cache đúng revision; không mở public từng câu để chọn sửa. Đọc scoped AGENTS và `harness context <file>` trước mọi Python edit.

1. Freeze manifest hashes của source đang dirty, cache, protocol, model revision, prompt/schema/gate và v3. Giữ nguyên ledger/artifacts cũ.
2. Audit đủ 54 abstain development: tách plan đúng bị gate chặn, plan thực sự sai, thiếu grounding, thiếu capability, thiếu dữ liệu, câu mơ hồ. Không coi “pass parser” hoặc “output trùng gold” là đúng ngữ nghĩa.
3. Lấy thêm mẫu development đại diện ngoài pilot, đề xuất 120 câu theo business/nhóm intent bằng seed/quota trước output; ghi N thật nếu bucket thiếu. Gồm cả nhóm baseline đã trả lời để đo hồi quy; không chỉ lấy câu dễ phục hồi.
4. Với mỗi họ lỗi, viết reference và synthetic contrast: đổi đúng một điều kiện về time, phủ định, đơn vị, metric, scope hoặc kiểu đáp án. Giữ BTC text/row-level audit trong ignored reports.
5. Kiểm tra quy định BTC hiện hành: cách đếm tổng tham số, giấy phép/model được phép, I/O Docker, phần cứng/thời gian/hạn nộp. Các thông số 2×5090, 512GB, 6h/500 và 16/11 trong research hiện là giả định chưa được phiên này xác nhận.

**Đầu ra/acceptance:** một audit manifest + bảng tổng hợp nguyên nhân; danh sách 2–3 họ sửa ưu tiên theo số câu có căn cứ và chi phí; exposure ledger; protocol thí nghiệm; baseline smoke offline được đặc tả. Đồng bộ trạng thái NLU/runner trong docs hiện hành, không xóa lịch sử.

### P1 — Phục hồi cách diễn đạt hợp lệ trong capability hiện có (1–2 ngày; sau P0)

Ưu tiên kiểm chứng AOV, thời gian/comparison, ranking và cách nói tương đương đã thấy trong development. Sửa `nlu/semantic.py`/prompt bằng nhận diện cấu trúc có chứng cứ; không chỉ mở rộng `_FILLER` để bỏ qua từ chưa hiểu. Giữ literal mention và dấu vết span; gate phải phát hiện cả điều kiện thiếu lẫn điều kiện tự thêm.

Mỗi họ có positive/negative contrast: tiền so số lượng, “bán chạy” so doanh thu, month neo kỳ chính so relative neo as_of, same_elapsed so cả tháng, singular entity so list, phủ định/threshold/hai scope. Việc tính ngày vẫn ở Periods. Không mở operation mới trong P1.

**Acceptance:** các ca ngữ nghĩa mới được test độc lập với câu BTC; baseline contrast vẫn reject đúng; paired replay chỉ dùng công cụ có integrity đã hỗ trợ. Nếu thay prompt/context phải tạo jobs/generations mới; không sửa hash để tái sử dụng jobs cũ. Report phần phục hồi đúng/sai sau freeze predictions, theo gate mục 3.

### P2 — Entity/label grounding có bằng chứng (2–3 ngày; sau P0, tích hợp sau P1)

1. Phân biệt mention gốc, trường/cột đích, raw label/canonical ID, nguồn alias, ứng viên và trạng thái ambiguous. Đặc tả contract mới trước khi sửa resolver; backward compatibility cho plan1.0. Có thể dùng sidecar có kiểu cho chứng cứ, không nhét key tự do vào JSON plan strict.
2. Bridge canonical/raw và alias nghiệp vụ lấy từ train README; exact NFC là bước đầu. Không áp bỏ dấu toàn bộ resolver. Candidate thiếu dấu/viết tắt cần tránh collision, giữ số/dung tích/size; nhiều ứng viên hợp lý thì abstain.
3. Thay context lấy 24 nhãn đầu bằng retrieval có giới hạn theo câu hỏi khi audit chứng minh truncation là vấn đề; giữ `complete`, provenance, token budget và eligibility theo as_of. Không có trong context cắt cụt không có nghĩa không tồn tại trong catalog.
4. Gate kiểm mention nguyên văn; resolver kiểm evidence liên kết. Không thay mention trong plan thành nhãn catalog rồi vô hiệu hóa kiểm tra `filter_not_in_question`.
5. Đo lần lượt exact baseline → README bridge → lexical candidates. Chỉ thêm RapidFuzz/BM25/embedding bằng dependency quyết định riêng nếu tăng recall an toàn; không cài cả ba tầng ngay.

**Acceptance:** synthetic cases về trùng tên/mã, khác dấu, alias mơ hồ, literal NA/null, tên có số, nhãn tương lai, đơn vị, cùng thực thể không phát sinh giao dịch trong kỳ. Đo candidate recall tách khỏi tỷ lệ resolve đúng; unknown/ambiguous/missing vẫn riêng. Chạy data profile với cache sửa lỗi được chỉ định tường minh.

### P3 — Mở capability có chọn lọc (2–4 ngày; sau P0, ổn định P1/P2)

Ưu tiên giả thuyết để audit: trả tên đơn lẻ từ ranking; chênh lệch tuyệt đối; so sánh hai scope; đếm distinct theo ngữ nghĩa rõ. Chỉ chọn **1–2 họ** có nhiều reference development hợp lệ và canonical data đủ; chưa kết luận họ nào lớn nhất từ 90 câu.

Với mỗi họ: đọc rulebook đúng split, chốt expected type, tie-break, empty/missing, kỳ, filter/denominator và units; mở public API business tất định nếu cần; cập nhật QueryPlan version/capability/schema/prompt/gate/serializer đồng bộ. Không biến list một phần tử thành string để lách contract. Công nợ/kho/giá vốn/hoa hồng chỉ mở khi canonical inputs và luật có bằng chứng; không đoán từ doanh thu.

**Acceptance:** reference có provenance; synthetic expected values độc lập, boundary/tie/missing/zero; API cũ giữ được; full + data; đóng góp PA báo riêng từng capability. Nếu chưa có semantics rõ, giữ unsupported và chuyển thời gian sang P6.

### P4 — Benchmark model và nhiều ứng viên (1–2 ngày thử nghiệm; sau P1/P2)

Thí nghiệm tuần tự để biết thay đổi nào có ích:

| Nhánh | Giữ cố định | Thay đổi |
|---|---|---|
| A | Source/QueryPlan/data/gate | 7B hiện tại + K=1, mốc đối chiếu |
| B/C | Cùng input/prompt/schema/capability và tiêu chí chọn | 14B-Instruct hoặc Coder-14B, mỗi lần chỉ một model; xác minh eligibility trước tải |
| D | Model thắng đã freeze | K=3: greedy + hai candidate theo config cố định; raw attempts đều lưu |

Pilot synthetic → development trước; chỉ đưa cấu hình shortlist đã freeze sang calibration. Không dùng evaluation632 để lặp chọn model. So PA cùng coverage/precision, cold/warm latency, token count, peak memory và GPU-hours. Pin revision/tokenizer/template/image; ghi tổng tham số thực và mọi model phụ, không lấy nhãn “14B” làm chứng nhận.

Consensus chỉ là tín hiệu: loại plan sai gate trước, giữ cả số candidate invalid; gom kết quả theo kiểu/rounding/list semantics, và so semantic signature. Thêm fixture nhiều plan cùng trả 0 nhưng khác filter để chứng minh agreement không đủ. Không majority vote vượt gate; chưa cần SQL/Pandas hai engine.

Modal thực hiện theo tools/AGENTS: Python3.12 env có sẵn; tối đa10 GPU tổng sau khi kiểm active jobs, tối đa10 shard không rỗng; ledger/reservation cho từng thí nghiệm, bounded retry và stop app sở hữu. Planning không phát sinh GPU call. Không áp lại cap25USD lịch sử như giới hạn mới; ghi estimate riêng trước run.

### P5 — Hiệu chuẩn chọn trả lời (1–2 ngày; sau P1–P4 và đủ mẫu)

Ưu tiên threshold đơn giản trên tín hiệu có nghĩa trước một verifier học máy: mức chắc chắn của grounding, completeness của context, semantic evidence, agreement, lỗi thực thi. Logprob không mặc nhiên là xác suất đúng; không hardcode 0,72 hoặc 25 features.

Nếu cần verifier, fit trên development với tách theo business/out-of-fold; chọn threshold trên calibration còn hợp lệ; evaluation đã tiếp xúc chỉ báo hồi cứu. Thiếu số mẫu đúng/sai hoặc calibration sạch thì hoãn mô hình học. Các ca missing-column synthetic dùng test robustness riêng, không trộn tỷ lệ 100/400 giả tạo vào phân phối dùng để chứng nhận chất lượng thực.

CRC chỉ là nhánh có điều kiện: định nghĩa loss, hướng đơn điệu, B, alpha, đơn vị lấy mẫu và giả định exchangeability trước. Với `L=I(answer AND wrong)`, rủi ro là **wrong/N**, không phải **wrong/answered**; alpha=0,15 không chứng minh precision≥85%. Chọn threshold tối đa PA và bảo đảm CRC là hai yêu cầu khác nhau. Không tuyên bố distribution-free trước domain shift/business clustering chưa xử lý.

**Acceptance:** risk–coverage và PA–threshold curves trên đúng tập, policy frozen, uncertainty và exposure được công bố; không làm nhòe các outcome nghiệp vụ. Nếu không có lợi ích rõ, giữ hard gate đã cải thiện ở P1/P2.

### P6 — Runner Docker offline và kiểm chứng nộp bài (khởi động từ P0; 2–3 ngày hoàn thiện)

Bắt đầu sớm bằng baseline7B: runner hiện tại tiêu thụ generations đã tạo trước, chưa chứng nhận inference offline trọn luồng. Chốt I/O theo BTC; đóng gói weights/tokenizer/template/calendar/dependencies được phép, không BTC gold/questions/cache phát triển. Có smoke synthetic end-to-end ngay đầu dự án, trước tối ưu model.

1. Build/pin image được kiểm thử trên phần cứng mục tiêu. Benchmark TP=1/TP=2 và prefix caching bằng đo thực; không lấy `vLLM>=0.7.3`, “PyTorch2.6+” hoặc tốc độ trong research làm cấu hình đã chứng minh.
2. Chạy với `--network none`; biến HF offline là bổ trợ, không thay network isolation. Đo cold start, loading/indexing, generation, execution, output; kiểm memory, disk, timeout, thứ tự đủ ID và định dạng.
3. Timeout phải cưỡng chế được bằng worker/process và có cleanup. Outer runner có thể cô lập lỗi từng câu theo protocol, nhưng sidecar giữ error class/stage; lỗi hệ thống lặp lại phải làm validation fail, không âm thầm xuất toàn abstain rồi báo thành công.
4. Đặt budget dựa giới hạn BTC được xác minh, có margin đề xuất20%. Nếu thực sự6h/500 thì 43,2s/câu chỉ là bình quân tổng ngân sách trước overhead, không tự suy timeout25s. Không preload mọi bảng vào RAM khi chưa đo.
5. Sau freeze, public chỉ dùng kiểm I/O/resources/smoke theo quy định; không thay policy theo score. Lưu image digest, hashes, logs, và một cấu hình baseline fallback đã chạy offline.

**Acceptance:** chạy đầy đủ không mạng trên môi trường mục tiêu, đủ record/ID, không runtime download, đạt memory/time budget và error protocol; input bất biến; artifact tái lập được. Có file submission không đồng nghĩa pass P6. Nộp/upload là thao tác riêng khi được giao.

## 5. Lịch dự kiến và quy tắc cắt phạm vi

Ước lượng công việc kỹ thuật, không phải hạn chót đã được xác minh. Nếu bắt đầu30/10 và tạm dùng mốc16/11 trong research để lập lịch:

| Khoảng dự kiến | Việc chính | Mốc ra quyết định |
|---|---|---|
| 30/10 | P0 + đặc tả/smoke runner P6 | Freeze baseline, exposure, audit, quy định |
| 31/10–03/11 | P1/P2, hoàn thiện offline baseline | Giữ hoặc rollback từng họ sửa theo paired report |
| 04–07/11 | P3 có giới hạn + P4 sau khi dependency sẵn sàng | Chọn capability/model dựa train protocol |
| 08–10/11 | P5 nếu đủ điều kiện; tích hợp P6 | Freeze policy/cấu hình cuối |
| 11–14/11 | Offline full run, kiểm hồi quy và sửa lỗi đóng gói | Không thêm engine/domain/model mới |
| 15–16/11 | Buffer, artifact cuối theo hạn BTC thực | Bản fallback sẵn sàng |

Nếu trễ: giữ P0/P1/P2 và P6; cắt theo thứ tự SQL/Python sandbox → embedding → learned verifier/CRC → K>1 → capability thứ hai. P4 lớn hơn chỉ được giữ nếu có gain đo được. Không trì hoãn runner để chạy thêm thí nghiệm model.

DuckDB chỉ quay lại backlog sau khi extended DSL có số đo giới hạn rõ: prototype read-only trên canonical views, không file/network/extensions ngoài allowlist; SQL AST allowlist, resource isolation và differential/metamorphic tests. Python tự sinh cần sandbox OS riêng; AST filter hoặc try/except không đủ. Hai engine đồng ý không chứng minh diễn giải đúng câu hỏi.

## 6. Acceptance tổng và bàn giao

- [x] Đọc research, current progress/map, source NLU/resolver/executor và hướng dẫn scoped; phân biệt đề xuất cũ với tính năng đã có.
- [x] Chạy full harness baseline: 688 passed / 2 deselected; không sửa Python.
- [x] Kế hoạch có dependency, scope/file dự kiến, acceptance, protocol, rollback, offline gate và giới hạn số liệu.
- [ ] P0: audit/provenance/protocol/exposure và xác nhận quy định BTC.
- [ ] P1/P2: phục hồi semantic/grounding có paired evidence và checks.
- [ ] P3/P4/P5: thực hiện hoặc ghi quyết định hoãn dựa evidence.
- [ ] P6: inference end-to-end offline và artifact đã kiểm trên môi trường mục tiêu.

Lệnh chuẩn trong các lượt thực thi: `.\.venv\Scripts\python.exe scripts/harness.py context <file.py>` trước edit; targeted tests liên quan; `.\.venv\Scripts\python.exe scripts/harness.py check`; thêm `check --profile data` khi thay correctness theo mục trên. Ghi rõ cache revision, N selected/compared/skipped và lý do skip; không suy PA toàn train từ selected verifier.

**Hành động tiếp theo cụ thể:** bắt đầu P0 bằng freeze working-tree baseline và audit54abstain development90, mở rộng mẫu development theo protocol đã khóa; chưa sửa gate, chưa mở public từng câu, chưa chạy GPU. P0 kết thúc bằng danh sách họ lỗi đủ bằng chứng để triển khai P1/P2. Kế hoạch không tự biến thành quyết định đã duyệt cho một cuộc viết lại kiến trúc.

## 7. Nguồn research đã đối chiếu và giới hạn

- [Conformal Risk Control — bài gốc](https://arxiv.org/abs/2208.02814): kiểm soát kỳ vọng bounded monotone loss; áp dụng vào DataMate cần định nghĩa đúng loss và giả định. Mã confidence có trọng số trong tài liệu đính kèm chưa phải triển khai CRC.
- [Qwen2.5-Coder-14B-Instruct — model card chính thức](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct): model card nêu số tham số làm tròn14,7B; không đủ chứng nhận tổng hệ thống chính xác14,90B hoặc eligibility BTC. Cần manifest/count thực trước chọn.
- [Reliable Text-to-SQL with Adaptive Abstention](https://arxiv.org/abs/2501.10858) và [LatentRefusal](https://arxiv.org/abs/2601.10398): đã kiểm tên/ID nguồn. Tên bài đúng không xác nhận mọi diễn giải, số benchmark hoặc cách triển khai trong báo cáo áp dụng được cho DataMate.
- Chưa kiểm toán toàn bộ12paper, leaderboard, hardware stack hay deadline. Những khẳng định chưa xác minh không được dùng làm acceptance hoặc bảo đảm điểm. Báo cáo đính kèm được giữ tại đường dẫn local người dùng, không sao chép vào repo.
