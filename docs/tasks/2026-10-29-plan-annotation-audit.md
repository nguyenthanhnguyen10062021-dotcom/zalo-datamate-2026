# Audit plan annotation độc lập gold — 2026-10-29

- Nền: 4fd268e trên VuongNguyen; giữ toàn bộ thay đổi inventory/verifier chưa commit từ lượt trước.
- Phạm vi: audit resolver đơn vị của các quantity selected để xác định ca chưa resolve mà không đọc report chứa kết quả gold; audit mẫu cố định của từng reason bucket unparsed. Không sửa grammar, resolver hoặc business trong tác vụ này.
- Nguồn được phép: questions, manifest_v2, rulebook/calendar, catalog/README train nếu cần và source hiện hành. Không mở answers, không scorer/execution để quyết định annotation.
- Giới hạn độc lập: agent đã thấy số tổng hợp đánh giá của lượt trước. Annotation không phải blind holdout; ghi prior aggregate exposure và vai trò annotator AI, không gọi gold plan/human-reviewed.

## Contract và acceptance trước code

- Lấy tối đa 10 câu mỗi reason bucket chưa parse, deterministic SHA256 của fingerprint question, round-robin doanh nghiệp để tăng đa dạng; ID chỉ join. Không lấy theo answer type/result, không thay mẫu sau khi đọc câu. Giữ mẫu số population và sample riêng, không suy tỷ lệ toàn bucket từ mẫu chủ đích nhỏ.
- Audit các quantity plan đã có unit mention bằng resolver/cột catalog, không tính đáp án. Annotation cho ca unresolved ghi raw mention, catalog evidence và phân biệt mismatch tên đơn vị với thiếu dữ liệu. Không tự thêm alias.
- Mỗi annotation local có question fingerprint, source spans/rule sections, operation/period/filter/ranking và plan hợp lệ nếu biểu diễn được; nếu chưa đủ thông tin/ngoài contract phải null cùng lý do. Phân loại supported_plan / unsupported_capability / unsupported_domain / needs_clarification. Plan structural validity không chứng minh diễn giải đúng.
- Packet đóng băng trước ghi annotations; file annotations sau khi hoàn tất có digest riêng và validator kiểm đủ mẫu, không trùng, plan schema, provenance, rationale và decision fields. Không tự chạy annotations qua verifier hoặc mở rộng grammar.
- Câu/ID/tên/catalog/plan từng câu chỉ trong reports ignored. Tài liệu tracked chỉ phương pháp, tổng hợp, giới hạn, next action. Full harness + targeted synthetic khi thêm utility; không chạy scorer/data profile vì không đổi tính toán.

## Tiến độ và evidence

- Utility sampling/validation có 9 synthetic tests: RED thiếu module → GREEN; thêm test sửa rationale sau freeze RED (digest chưa được kiểm) → GREEN. Không tạo CLI mới hoặc đổi selector/runtime.
- Lấy mẫu 10/bucket chưa parse (4 bucket) + 1 ca unresolved unit; packet local đóng băng trước annotation. Tái resolve bằng catalog không tính answer xác định câu hỏi tiền bán bị gán quantity(unit money); rulebook train dòng 11 quy định revenue. Không sửa grammar/alias trong lượt này.
- Đã annotate đủ 41: 23 supported_plan (gồm ca tiền), 14 unsupported_capability, 4 unsupported_domain. Riêng mẫu 40: 22/14/4; không dùng tỷ lệ mẫu ước tính coverage. Các plan viết tay từ câu/rulebook/catalog, không gọi select_question hoặc QueryExecutor/scorer để chọn plan.
- Thông tin từng câu/source/plan/provenance và authoring script chỉ trong reports/capability_inventory/audit_v1/. Packet/annotation payload digest trong docs/plan-annotation-audit.md. Thêm validation_receipt riêng khi validator có thêm check digest sau annotation freeze; không sửa annotation đã đóng băng.
- Kiểm chứng: 41 annotations đủ/không trùng, plans validate, catalog/corpus/source fingerprints khớp và frozen manifest_v2 còn nguyên. Targeted 54 passed; full 487 passed/2 deselected; bare pytest 488 passed/1 skip helper cũ. Không mở gold, không chạy data/scorer, không ghi kết quả accuracy mới.
- Self-review semantic: money phải revenue, so tháng liền trước neo tháng câu hỏi (gồm ranh giới năm), same_elapsed chỉ this_month; so hai ca không ép vào một Filters; top1 scalar không tự đổi list; nhập/nợ/lãi không map sales metric. Chưa có reviewer độc lập/human, ghi rõ AI/provenance exposure. Giữ input và thay đổi của lượt trước.
- Trạng thái: complete; next action: synthetic contrast tests và sửa intent tiền, sau đó mở grammar theo họ ngôn ngữ đã annotate/dev-exposed, freeze manifest revision mới trước chấm. Các capability/domain mới để contract riêng. Chưa commit/push.
