# Inventory capability và verifier QueryPlan độc lập legacy

## Phạm vi được giao

Người dùng yêu cầu thực hiện bước tiếp theo sau executor v1. Kiểm kê khả năng xử lý câu hỏi train và kiểm chứng qua QueryExecutor, không thêm nghiệp vụ, model hoặc thay đổi semantics business. Đây là công cụ phát triển/đánh giá hồi cứu; không phải NLU production hoặc holdout mới.

## Thiết kế đã chốt trước code

Codex chọn hai lệnh: `inventory_capabilities.py` tạo manifest JSON local; `verify_queryplans.py` thực thi manifest rồi chấm. Package dev-only `verification/` chứa selector và IO/runner. Cách chỉ mở rộng dispatcher legacy vẫn giữ gate cũ nên không dùng; cách gán plan từ gold không được phép. Giữ nguyên `verify_business.py` làm baseline riêng.

Selector chỉ nhận nội dung câu hỏi, không nhận ID, gold, kết quả tính hoặc cache. Grammar cố định và bảo thủ: chỉ nhận toàn bộ câu nằm trong mẫu đã định nghĩa, có thời gian tường minh và filter/metric rõ ràng. Hỗ trợ các dạng chuẩn của cả 10 operation; câu ngoài grammar được ghi unparsed, không suy domain bằng regex quota. Mention tường minh được giữ để executor resolve; không đoán alias/tên từ gold. Grammar chốt bằng fixture tổng hợp trước lần chấm train, không chỉnh theo câu đã khớp/sai.

Manifest deterministic có đúng một entry cho mỗi câu: ID để join, business_id để tìm cache, as_of_date, fingerprint câu hỏi, selection/reason và plan hoặc null. Metadata chứa version, fingerprint file questions, rulebook và source selector. Không đọc answers khi tạo inventory. Không dùng ID để quyết định capability. Manifest phải được lưu và đọc lại trước verification; reject thiếu/thừa/trùng entry, fingerprint stale, plan lỗi hoặc version không hỗ trợ. Không tự làm lại manifest khi chấm. Toàn bộ câu/manifest/report chỉ ở reports ignored.

Runner chỉ dùng QueryExecutor trên bảng chuẩn đọc từ cache, đúng rulebook/calendar/as_of của train; không import hoặc gọi legacy. Xử lý theo từng doanh nghiệp để không giữ mọi bảng trong RAM. Fingerprint các file cache dùng, rulebook, calendar nếu có và source để report có thể đối chiếu. Không sửa cache. Sau execution mới join gold theo ID và dùng nguyên `evaluate/evaluate.py::score_one` cho type/format/value, bao gồm list/alias/order và unanswerable.

Mọi câu được chọn vẫn ở mẫu số dù resolve/capability/data lỗi hoặc mismatch. Báo total, selected, outside_selection; selected được phân hoạch thành compared (matched+mismatch), abstained và execution_errors. Status/stage của executor giữ riêng. Lỗi load cache và lỗi implementation được ghi rõ và gây exit khác 0, không biến thành unanswerable/skip. Missing/duplicate gold hoặc corpus/manifest không nhất quán làm lệnh từ chối chấm; không tạo điểm thành công từ mẫu số thiếu. Không có selected/compared cũng exit khác 0. Mismatch hoặc lỗi đã phân loại là kết quả cần điều tra, không phải lý do bỏ câu hoặc sửa selector theo gold.

Inventory báo operation, period, filter, ranking metric và lý do chưa chọn; đây là độ phủ grammar/plans, không chứng minh correctness hay độ phủ mọi câu sales. Verifier báo riêng lỗi mapping câu→plan và lỗi business chưa thể phân biệt tự động; kết quả là độ đúng của pipeline grammar+executor trên manifest hồi cứu, không PA model/NLU. Regression và group-disjoint là hai mục tiêu khác nhau; chưa triển khai fold/tuning hoặc tuyên bố dữ liệu chưa từng thấy.

## Acceptance checks

- Inventory chạy không cần answers/cache, deterministic; đổi gold không đổi lựa chọn/plan, ID chỉ là khóa join. Có fixture tổng hợp cho cả 10 API và phản chứng câu chứa qualifier lạ.
- Manifest phủ toàn corpus, kiểm tra missing/duplicate/stale/modified plan; không âm thầm chọn lại khi replay.
- Verifier không import/call legacy; có ca ngoài bộ chọn legacy, mismatch và các lỗi executor vẫn giữ trong mẫu số.
- Chấm number/percent/list/unanswerable theo local evaluator; list đúng thứ tự/alias, giữ status/stage và reason. Duplicate/missing gold, cache thiếu và unexpected exception được kiểm tra.
- Test tổng hợp RED→GREEN, harness full và bare pytest; chạy inventory+verifier trên train local, báo số thực đo và mọi giới hạn/mismatch; chạy data profile baseline riêng. Không đặt mục tiêu 1000–1500 hoặc chọn câu theo đáp án.
- Không thay loader/business/queryplan/evaluator semantics, không dependency mới, không public-test tuning, không commit/push tự động.
