# Capability inventory và verifier độc lập legacy

Đây là công cụ **phát triển và đánh giá hồi cứu** trên câu hỏi train. Inventory kiểm kê khả năng grammar tạo QueryPlan; verifier chạy plan qua [executor v1](queryplan.md) rồi chấm bằng evaluator local. Không thêm model, không mở rộng nghiệp vụ tồn kho/công nợ, không thay `verify_business.py` hoặc dùng legacy làm điều kiện chọn/chấm.

## Chạy từ repository root

```powershell
.\.venv\Scripts\python.exe inventory_capabilities.py --out reports/capability_inventory/manifest_new.json
.\.venv\Scripts\python.exe verify_queryplans.py --manifest reports/capability_inventory/manifest_new.json --out reports/capability_inventory/verification_new.json
```

Hai CLI mặc định đọc train; verifier mặc định đọc cache đã tạo sẵn. Có `--train` và verifier có `--cache` để kiểm tra fixture/corpus local khác; không dùng public test để tuning. Output CLI bắt buộc nằm trong `reports/` ignored và không trùng input. File đã tồn tại không bị ghi đè; chọn tên output mới cho lượt mới. Verifier tạo JSON chi tiết và Markdown summary. Manifest không cần answers hoặc cache khi được tạo; lưu nguyên file đó trước khi chấm.

## Selector hỗ trợ đến đâu

`verification/selection.py::select_question(text)` chỉ nhận nội dung câu. Không nhận ID, gold/answer type, cache, kết quả tính hoặc nhãn doanh nghiệp. Dùng grammar bảo thủ tiêu thụ toàn bộ câu, chưa phải NLU production. Grammar được chốt qua câu tổng hợp trước khi chấm train; không thêm ngoại lệ cho ID hoặc bỏ câu vì mismatch.

Các dạng chuẩn minh họa (dữ liệu tổng hợp):

| API | Dạng câu |
|---|---|
| revenue | Doanh thu tháng 3/2026 bao nhiêu? |
| order_count | Có bao nhiêu đơn hôm nay? |
| cancelled_orders | Bao nhiêu đơn bị hủy tháng này? |
| cancellation_rate | Tỷ lệ đơn hủy tháng này là bao nhiêu phần trăm? |
| average_order_value | Giá trị trung bình một đơn tháng này là bao nhiêu? |
| quantity | Bán được bao nhiêu ly tháng này? |
| top_products | Top 2 mặt hàng theo doanh thu tháng này? |
| top_customers | Top 2 khách hàng theo số đơn tháng này? |
| revenue_growth | Doanh thu tháng 3/2026 tăng bao nhiêu phần trăm so với tháng 2/2026? |
| revenue_share | Tỷ trọng doanh thu nhóm hàng "Nhóm mẫu" tháng này là bao nhiêu? |

Tên/nhãn thường được nêu tường minh trong dấu nháy sau mặt hàng/sản phẩm/nhóm hàng/nhóm khách/kênh/thanh toán; ngoại lệ nhóm không nháy có ranh giới ở dưới. Giữ nguyên dấu để resolver tra catalog. Có ca sáng/chiều. Quantity có một từ đơn vị. Ranking có k và metric; grammar không bao phủ mọi cách nói top/list. Kỳ có ngày ISO/khoảng ngày, hôm nay/qua, tuần/tháng này/trước, tháng/quý có hoặc không có năm, N ngày gần nhất/qua, từ đầu năm đến nay và Tết năm Y. So tháng này với tháng trước dùng same_elapsed đúng mặc định rulebook; qualifier khác chưa được nhận sẽ bị giữ lại và không chọn.

**Mở rộng sau Argon:** intent bán/thu tiền là revenue, bán bao nhiêu đơn là order_count; danh từ metric không dùng làm unit. Unit được lấy từ capture span NFC/casefold rồi bảo vệ khỏi normalize từ nối, không dò lại toàn câu. Một số biến thể ngôn ngữ cố định (dthu, hqua, thangs, tuần rồi, hạt từ ở biên) được nhận, không fuzzy/Telex tự do. Tên/đơn vị được bảo vệ trước normalize, qualifier không hiểu vẫn giữ để reject.

Tháng/quý tường minh hoặc năm ngầm định so tháng/quý trước sinh previous_calendar_month/quarter, không tự tính năm trong selector text-only. Growth clause có thể xuất hiện sau kỳ comparison nếu toàn bộ phần còn lại đúng mẫu growth; filter ở comparison không bị chuyển sang kỳ chính. Top-k list nhận thêm “hàng bán chạy nhất ... là gì”, top-k khách vẫn cần tiêu chí rõ. Scalar/two filters/domain mới chưa hỗ trợ.

Ngoại lệ có ranh giới cho mention không nháy: chỉ **nhóm hàng/nhóm khách** có tên đứng ngay trước động từ **chiếm/đóng góp** trong share. Giữ nguyên label có dấu; label chứa kỳ thời gian, conjunction hoặc scope filter khác bị giữ lại để reject. Không tự suy “nhóm X” là nhóm hàng hay khách, không bắt mọi tên hàng trần hoặc sửa dấu theo catalog. Label chưa khớp vẫn được executor báo unresolved và giữ trong selected.

Mỗi câu có selection/reason và plan hoặc null. Inventory thống kê operation, period, filter, ranking metric, lý do chưa chọn; operation không xuất hiện trong histogram có số câu chọn bằng 0, không có nghĩa API chưa triển khai. Một plan được chọn vẫn có thể bị executor từ chối capability, không resolve được, hoặc thiếu dữ liệu. Không gọi số câu được chọn là số câu chắc chắn trả lời đúng.

## Frozen manifest và integrity

Manifest có đúng một entry cho mỗi câu của corpus, gồm id/business_id/as_of_date, fingerprint toàn record câu hỏi, selection/reason/plan. Metadata có version, fingerprint bytes file questions/rulebook và source selector; payload có fingerprint riêng. ID chỉ để join và tìm cache, không quyết định operation.

Verifier kiểm tra version, digest, corpus đầy đủ, ID trùng/lạ, ngày, plan contract và source fingerprint. Thay câu hỏi, rulebook hoặc selector làm manifest stale; lệnh từ chối chấm, không tự chọn lại. Hash giúp phát hiện thay đổi và replay, không chứng nhận plan được diễn giải đúng hoặc chống được người cố ý sửa rồi tính hash lại. Lưu mọi revision cùng lý do thay đổi; không rebuild để loại câu sau khi đã nhìn gold.

## Execution, scoring và mẫu số

Đọc đầy đủ ba bảng don_hang/dong_hang/mat_hang và cua_hang.json của từng doanh nghiệp trong cache; giữ tối đa một doanh nghiệp trong RAM. Caller truyền rulebook/calendar/as_of_date cho QueryExecutor. File cache dùng, source tính toán/scorer, corpus, manifest và gold có fingerprint trong report; không rebuild hoặc sửa cache.

Hoàn tất predictions trước khi mở answers. Gold phải có đúng tập ID toàn corpus, không trùng/mất/thừa, type/format cơ bản hợp lệ. So đáp án bằng chính `evaluate/evaluate.py::score_one`, gồm type, number/percent, list order/alias và unanswerable. Evaluator local chưa được chứng nhận tương đương BTC.

Các đẳng thức phải giữ:

```text
total = selected + outside_selection
selected = compared + abstained + execution_errors
compared = matched + mismatch
```

Status/stage/reason của executor được giữ nguyên. DataError/UnsupportedRule/resolve/capability tạo abstain có phân loại; business unanswerable vẫn được chấm như đáp án. Lỗi đọc cache và exception implementation thành execution_errors tường minh, không đổi thành unanswerable hoặc loại khỏi selected. Câu chưa parse vẫn nằm trong manifest/outside_selection. Lỗi integrity/reference khiến lệnh từ chối chấm; không có báo cáo thành công với mẫu số không đầy đủ.

Exit 0 chỉ khi selected/compared đều khác 0 và không mismatch, abstain hoặc execution error. Exit 1 từ một report có lỗi là kết quả chẩn đoán cần giữ và điều tra; không sửa selector để làm báo cáo xanh theo gold. Báo cáo không thể tự phân biệt mọi lỗi grammar→plan với lỗi executor/business, cần audit riêng trước khi sửa semantics.

## Kiểm chứng và giới hạn

Tests tổng hợp: `python -m pytest tests/test_capability_inventory.py tests/test_queryplan_verification.py tests/test_harness.py -q`, rồi harness full, bare pytest và data profile cho baseline cũ. Xem số liệu thực đo tại [validation](validation.md) và [execution record](superpowers/plans/2026-10-29-capability-verifier.md).

Độ phủ grammar không bằng độ phủ domain/API. Kết quả verifier là grammar + resolver + executor trên manifest train hồi cứu, không phải PA model/NLU, không phải chứng cứ holdout mới. Bộ legacy 417 chọn / 8 bỏ / 409 đối chiếu là baseline riêng, không cộng vào mẫu số mới khi chưa tính giao/khác. Group-disjoint/fold artifacts, gold plan được audit thủ công, model và runner submission chưa có trong tác vụ này.

Đã có [audit annotation AI trước mở grammar](plan-annotation-audit.md): 40 mẫu chưa parse và ca unit chưa resolve; artifact/digests local. Đây là annotation đề xuất có provenance, chưa gold plan chuẩn/human adjudication. Không sửa manifest v2 hoặc chạy scorer trong lượt audit.

`verification.audit.preflight_annotations(packet, annotations)` tạo receipt mới: schema_status, capability_status, resolution_status=not_checked và execution_status=not_run, không answer/scorer/data access hoặc sửa annotation. Receipt có digest riêng; metadata bổ sung của caller nên được bọc trong envelope có hash thay vì append vào payload đã hash. Optional resolution/dry-run là bằng chứng riêng và không chứng minh diễn giải đúng; giữ input/receipt/source fingerprints. Xem [task triển khai](tasks/2026-10-29-selector-calendar-implementation.md) cho acceptance và evidence v3/v4.
