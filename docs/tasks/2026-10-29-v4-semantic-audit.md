# Audit ngữ nghĩa manifest v4 và khoảng trống customer/share

- Ngày / owner: 2026-10-29, Codex AI theo người dùng chấp thuận đề xuất audit.
- Trạng thái: complete (audit và hồ sơ; chưa sửa các lỗi được phát hiện).
- Nền: commit local **00043fa**, nhánh VuongNguyen; working tree sạch sau commit. Không push trong tác vụ này.
- Mục tiêu: kiểm diễn giải metric, kỳ, comparison anchor, filter scope, ranking, unit và output shape từ câu hỏi/rulebook; phân biệt answer match với plan correctness.
- Ngoài phạm vi: sửa selector/grammar/runtime/business/evaluator, LLM/model, public-test tuning, scalar/two-scope extension. Không claim human/independent review, blind holdout hoặc PA toàn train.

## Contract và acceptance trước lấy mẫu

- [x] Kiểm manifest v4 hiện hành với corpus/rulebook/selector hashes; ghi source revision, source/file hashes và old audit fingerprints. Không mở answers hoặc report chứa prediction/gold từng câu trước freeze annotation.
- [x] Selected: tối đa5 mỗi operation đang có, quantity nếu chỉ2 thì lấy cả2; dự kiến37 trên8ops. Chọn greedy đa dạng tags period-kind/comparison-kind/explicit-year/filter-fields/ranking-metric, mỗi bước ưu tiên số tags chưa thấy, rồi doanh nghiệp chưa thấy, rồi question fingerprint tăng dần. Quota cố định, không thay theo kết quả audit/score; đây là mẫu có chủ đích, không ước lượng accuracy population.
- [x] Unparsed: candidate pools chỉ từ text đã fold (NFC/casefold/bỏ dấu) của2604 câu ngoài selection. Customer: có khách và từ xếp hạng/top/nhiều tiền/nhiều đơn; share: có từ tỷ trọng/tỷ lệ/chiếm/đóng góp và doanh thu/tiền bán/tiền thu. Đây là heuristic discovery, không bao phủ hết hai API. Tối đa12/bucket, dùng stable fingerprint order + round-robin business từ sample_unparsed; dedup union, giữ mọi pool membership.
- [x] Freeze packet gồm mẫu/membership/selection/source hashes. Annotate question-only view không hiện candidate plans/results. Ghi intent, kỳ/comparison, scopes, output shape, reference plan hoặc unsupported/uncertain, rationale/evidence/confidence. Không dùng gold expected type để chọn plan; có prior aggregate/train/source exposure nên không gọi blind hoặc độc lập tác giả.
- [x] Freeze toàn bộ reference annotations/digest trước đối chiếu candidate plans, preflight/data/execution và score. Candidate khác JSON có thể tương đương theo rulebook; adjudicate khác biệt từng field, không tự gọi mismatch literal là semantic error.
- [x] Schema/capability preflight riêng; source/corpus/catalog evidence dùng khi cần resolve. Sau freeze có thể kiểm execute/score reference plans, giữ unsupported/unresolved/error trong mẫu số. Không loại ca hoặc sửa annotation gốc sau gold; nếu cần correction ghi receipt riêng.
- [x] Công bố denominator selected-audit và candidate-pool audit riêng; mọi uncertain/unsupported/mismatch/abstain/error cùng provenance. Row-level artifacts chỉ reports/capability_inventory/semantic_audit_v1/ ignored. Không sửa old manifest/annotations/cache.
- [x] Harness full, fast/staged whitespace; không chạy lại full data baseline nếu không sửa loading/business/runtime. Kiểm current runtime/selector hashes không đổi và artifacts cũ còn nguyên. Cập nhật PROGRESS, quyết định và khuyến nghị bước tiếp dựa evidence.

## Tiến độ / evidence

- Trước lấy mẫu đã chạy harness full545passed/2deselected, fast125files; commit00043fa chốt baseline code/tests/review. Thêm .gitattributes đúng3externalresponses để giữ bytes/newlines và khoảng trắng lịch sử, không sửa nội dung response. Tại mốc này chưa mở answers hoặc gold reports trong tác vụ audit; phase sau chỉ mở khi references/predictions đã freeze.

### Mẫu và provenance đã freeze

- Thực tế61 câu/22doanh nghiệp: selected37/21doanh nghiệp, cộng12/customer-ranking pool110 và12/share pool97. Hai pool không giao trong mẫu; đây là lexical candidate counts, không số câu thực sự thuộc API. Giữ5 false positives công nợ của pool khách, không thay mẫu sau khi đọc.
- Selected gồm5 mỗi op AOV/cancellation_rate/cancelled_orders/order_count/revenue/revenue_growth/top_products và2quantity. Primary periods: month22,previous_week5,yesterday4,quarter2,this_month1,today1,this_week1,last_days1. Comparison: previous_calendar_month3,month2;32không comparison. Filters: shift2,unit2. Chưa audit implicit-year hoặc previous_calendar_quarter trong mẫu này; synthetic cũ không thay thế semantic audit train.
- Packet payload SHA256 `fdbe95be7b6aee1f4144f3c7c5ec2a6b2097f4caa16b1e8ed14492a25e17709c`; annotations payload SHA256 `7ed3341c1f7a9674c90677d3eb6ed95df5518c9680e76de33a74263ada56e8f3`.
- Reference chỉ đọc question-only view và rulebook, không mở candidate plans/catalog/gold trong phase annotation. Sau freeze mới đối chiếu candidate và đọc dữ liệu. Annotator vẫn là Codex AI/tác giả triển khai, có prior aggregate/train/source exposure; không independent/human adjudication, blind holdout hoặc gold plan chuẩn.

### Kết quả semantic, capability và execution tách biệt

| Tập audit | Số câu | Reference plan v1 | Không chạy | Compared | Matched | Mismatch | Abstain | Execution error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Selected v4 sample | 37 | 37 | 0 | 37 | 37 | 0 | 0 | 0 |
| Unparsed customer pool sample | 12 | 3 | 9 | 3 | 2 | 1 | 0 | 0 |
| Unparsed share pool sample | 12 | 6 | 6 | 2 | 1 | 1 | 4 | 0 |
| **Tổng mẫu audit** | **61** | **46** | **15** | **42** | **40** | **2** | **4** | **0** |

- Selected37: candidate và reference normalized JSON trùng37/37; same-author question-only review chưa thấy khác nghĩa trong mẫu. Không suy toàn396 plans đều đúng từ37 hoặc từ answer-match.
- Unparsed24 trước catalog:9supported_plan,6unsupported_capability (4scalar,2prescription predicate),5unsupported_domain công nợ,4needs_clarification bare group-kind. Preflight46supported/15not_checked; schema/capability không chứng minh dữ liệu đầy đủ.
- Execution46:39answered,3unanswerable,4unresolved_entity;15không plan giữ not_run. Có1unanswerable khớp gold trong selected;2unanswerable còn lại sai type so gold. Không chuyển chúng thành abstain để đổi điểm hoặc loại khỏi mẫu số.
- Local adapter đầu tiên gọi đảo arguments `score_one` và kiểm numeric1 trong khi evaluator trả string. `scoring.json` **vô hiệu**, giữ hash và lý do superseded trong `scoring_v2.json`. Đã chấm lại **cùng predictions đã freeze**, không tái thực thi hoặc sửa references; adapter mới kiểm3synthetic cases correct/wrong-type/abstain.
- CLI evaluator chính thức cross-check trên đúng46 predictions/reference subset: **40correct/2wrong/4abstain**, exit0 (CLI exit0 chỉ có nghĩa chấm chạy xong, không all-correct). `scoring_v2.json` là report hợp lệ; giữ2mismatch và4abstain. Không dùng score/accuracy này làm PA model hoặc ước lượng population.

### Phát hiện và kiểm nguồn sau freeze/scoring

1. **Thiếu tên khách sau join:** danh mục canonical có tên và mã duy nhất, đơn có mã nhưng toàn cột tên thiếu. `_join_customers` chỉ lấp group/phone/address, không tên; `top_customers` yêu cầu tên nên trả unanswerable. Đây là mất thông tin trong canonical pipeline, không lỗi diễn giải list/top-k. Cần join có validation uniqueness/conflict, giữ tên gốc và walk-in semantics; chưa sửa code hoặc cache.
2. **Nhóm khách chưa map:** raw có một cột chứa các nhãn nhóm, mapping ghi unmapped và canonical không còn group. README của nguồn đó chưa định nghĩa cột; profile là bằng chứng điều tra, chưa đủ phép thêm mapping dựa gold. Cần căn cứ train README phù hợp hoặc ghi ambiguity/provenance rõ, không hardcode theo shop/câu.
3. **Missingness bị hỏng khi ghi cache:** phát hiện literal `"<NA>"` ở canonical ID/label. Đã tái hiện tổng quát bằng fixture tổng hợp với source hiện tại: `_as_key` cho object column có `pd.NA`, rồi `load_all.to_parquet` stringifies thành `"<NA>"`; số missing từ1thành0 sau round-trip. Đây là bug serialization độc lập gold, có thể làm walk-in bị coi là khách có mã. Chưa đo toàn cache hoặc tự sửa literal strings trong cache.
4. **Bốn unresolved:**2label không dấu chưa khớp exact;1payment và1channel dùng nhãn tự nhiên trong khi cache đã canonical hóa. Cần contract bridge từ cách nói/metadata sang canonical label, giữ ambiguity; không tự thêm fuzzy hoặc bỏ dấu toàn cục, không import loader vào queryplan.
5. **Bốn bare group:** catalog hiện tại xác định được label thuộc nhóm hàng trong các ca mẫu. Receipt bổ sung ghi kết luận phụ thuộc catalog; annotation needs_clarification gốc giữ nguyên, không execute/score thêm4plan để nâng số đẹp.
6. **Hai prescription cases:** catalog có thuộc tính kê đơn, nên đây không phải thiếu toàn metric share/domain. Question-only contract chưa có predicate hoặc bước materialize filter từ catalog. Có thể biểu diễn tập sản phẩm nonempty/unique bằng product_mentions khi có grounding được kiểm; phải chốt missing/duplicate/empty-set semantics vì `[]` hiện normalize về null. Không tự coi attribute là tên nhóm.

Synthetic serialization reproduction (dùng path output mới trong reports/, không cache):

```python
import pandas as pd
from pathlib import Path
from loader.build import _as_key
from load_all import to_parquet
keys = _as_key(pd.Series(['C001', pd.NA], dtype='string'))
to_parquet(pd.DataFrame({'ma_khach': keys}), Path('reports/missingness_probe.parquet'))
# Hiện tại: pd.read_parquet(...).ma_khach.iloc[1] == '<NA>', thay vì missing.
```

### Artifact local ignored và kiểm integrity

`reports/capability_inventory/semantic_audit_v1/` giữ sampler/script fingerprints, packet, question_only, annotations, plan_comparison, preflight, predictions, scoring_v2, catalog_evidence và missingness_repro. CLI subset/predictions/errors chỉ local. `scoring.json` sai adapter là evidence bị supersede, không kết quả kiểm chứng. Không chỉnh old annotations/manifests hoặc cache, không copy BTC question/answer/catalog rows vào Git.

Runtime/selector/loader/business/evaluator source giữ nguyên00043fa; compare37 trước mở gold. Toàn bộ predictions46 freeze trước đọc answers; packet/annotation/source/cache hashes kiểm lại ở receipt cuối. Harness full mới trong tác vụ545passed/2local_data deselected; không rerun whole-data baseline hoặc báo409là phép chấm mới. Fast cuối kiểm links/budgets/boundaries/staged/unstaged whitespace.

Integrity cuối **PASS**: digest packet/annotations/predictions/reports, used cache files, old manifests/annotations và source không đổi; bytes3response lưu trong Git bằng working tree. `integrity_receipt.json` payload SHA256 `fb3fcb2bae4ed991de9d057ce86bf15cc8ead0eddd0eb94e2b09b2f57e5b18be`. Fast cuối exit0,126repository files inspected. Artifact audit từng câu không tracked; hồ sơ audit mới ở working tree, commit00043fa chỉ là mốc baseline trước audit.

## Bàn giao

- Đã xong: commit baseline00043fa local; audit61, refs freeze, comparison37, preflight46, execution/CLI cross-check và chẩn đoán dữ liệu. Hồ sơ audit là thay đổi tài liệu mới; chưa push.
- Việc kế tiếp được đề xuất: sửa **serialization missingness và customer-name join** bằng synthetic regression trước, giữ API/semantics, rebuild vào cache revision riêng rồi replay v4 và baseline riêng. Mapping group cần evidence riêng; label bridge/predicate cần contract tiếp. Chưa triển khai các sửa này hoặc model/grammar.
- Mốc396/396 cũ vẫn giữ nguyên giá trị trên selected v4 và cache snapshot cũ; audit mới cho thấy khoảng trống của2API ngoài selection. Chưa đủ căn cứ tuyên bố10API đã kiểm chứng train hoặc bắt đầu tuning NLU trên một baseline được gọi là hoàn thiện.
