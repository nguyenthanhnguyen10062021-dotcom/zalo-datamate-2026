# Audit annotation từ câu hỏi, không dùng gold — 2026-10-29

Audit tiếp theo frozen manifest v2 của [capability verification](capability-verification.md). Không sửa grammar/manifest/resolver/business, không chạy scorer, không mở answers hoặc report chứa gold từng câu trong lượt audit. Annotation lưu local, không tự chuyển thành verifier selection mới.

## Kết luận ca chưa resolve đơn vị

Đã kiểm tra các quantity selected có unit, chỉ đọc câu hỏi, plan và catalog. Ca chưa resolve là **nhầm intent tiền bán thành số lượng**, không phải alias đơn vị bị thiếu. Rulebook train §1, dòng 11 quy định tiền bán/thu về là doanh thu; parser hiện gán money token làm `unit_mention`. Catalog không có đơn vị tiền là đúng.

Annotation đề xuất `revenue`, giữ nguyên tháng và ca trong câu hỏi, bỏ unit. **Chưa áp dụng sửa grammar**, nên abstain trong verifier v2 vẫn còn. Không thêm tiền vào alias/catalog, không coi đây là dữ liệu không có thông tin hoặc đáp án 0. Việc sửa sau audit phải có regression synthetic cho phân biệt tiền/đơn vị hàng, đóng băng manifest revision mới trước chấm và giữ nguyên kết quả v1/v2.

## Mẫu audit đã đóng băng

Lấy tối đa 10 câu mỗi reason bucket chưa parse: sắp theo fingerprint toàn record câu hỏi, luân phiên doanh nghiệp theo thứ tự fingerprint để tăng đa dạng. Không dùng answer type/result để lấy mẫu, không đổi mẫu sau khi đọc câu. Có 4 bucket nên mẫu là 40, thêm ca intent tiền thành 41 annotations. Mẫu có chủ đích nhỏ; không ngoại suy tỷ lệ sang 2.874 câu chưa parse hoặc cả 3.000 câu.

| Bucket | Tổng chưa parse v2 | Mẫu | Plan theo contract hiện tại | Cần capability mới | Domain chưa hỗ trợ |
|---|---:|---:|---:|---:|---:|
| missing_or_multiple_periods | 638 | 10 | 7 | 2 | 1 |
| multiple_filter_scopes | 13 | 10 | 0 | 10 | 0 |
| unrecognized_comparison | 33 | 10 | 9 | 1 | 0 |
| unrecognized_operation_or_scope | 2190 | 10 | 6 | 1 | 3 |
| **Tổng mẫu chưa parse** | **2874** | **40** | **22** | **14** | **4** |

Trong 22 plan đề xuất từ mẫu: revenue 7, order_count 2, top_products 1, revenue_growth 9, quantity 1, revenue_share 2. Thêm ca intent tiền có tổng 23 supported_plan/41 annotations. “Supported” chỉ nói plan được biểu diễn và schema hợp lệ theo nhận định annotator, chưa chứng minh executor/catalog thực thi được mọi ca hoặc đáp án khớp gold.

## Phân biệt lỗi grammar với thiếu capability

- Các biến thể thời gian, Telex/viết tắt, lời dẫn và tên hàng/nhóm không trong dấu nháy tạo khoảng trống grammar; vẫn cần giữ size, mã số trong tên và scope bộ lọc. Catalog dùng để xác nhận tên/đơn vị, không đoán theo gold hoặc tính giá trị đáp án.
- So tháng liền trước phải neo vào **kỳ được hỏi**, không mặc định tháng trước `as_of_date`. Cần test tháng 1 qua tháng 12 năm trước; so cùng kỳ năm ngoái dùng tháng đã nêu, còn tháng này so tháng trước dùng same_elapsed.
- So ca chiều với ca sáng cần hai filter scope trong cùng kỳ; mốc theo rulebook là ca sáng. QueryPlan v1 có một Filters cho cả hai kỳ growth, vì vậy nới grammar rồi gọi revenue_growth hiện tại sẽ đổi nghĩa. Mười ca của bucket multiple_filter_scopes và một ca comparison khác thuộc nhóm này trong mẫu.
- Câu hỏi một khách đứng đầu cần scalar/string; top_customers hiện trả list. Không tự đổi expected_type hoặc trả list một phần tử thay scalar khi chưa có contract.
- Giá bán theo ngày, hiệu ứng tăng giá trên lượng bán cần API/metric mới. Công nợ, nhập hàng/giá nhập bình quân và lãi gộp thuộc domain chưa triển khai; không thay bằng revenue/AOV hoặc top_products hiện có.

## Artifact và provenance

Tất cả artifact nằm dưới `reports/capability_inventory/audit_v1/` ignored:

- `packet.json`: frozen sample, câu hỏi, plan selector cũ, population counts, manifest/source fingerprints và evidence catalog của ca đơn vị.
- `annotations.json`: 41 AI annotations, decision, plan hoặc null, semantic intent, rationale, evidence, grammar gap, confidence, fingerprint packet/question/catalog và provenance.
- `annotate.py`: bản ghi quá trình tác giả gán plan thủ công bằng chỉ số trong frozen sample; không phải rule theo ID hoặc code inference. File chứa nội dung BTC nên phải giữ local.
- `summary.json`, `audit.md`: tổng hợp và bản đọc chi tiết local.
- `validation_receipt.json`: fingerprint artifact, validator hiện tại và kết quả completeness/schema; ghi rõ validator được thêm kiểm digest annotation sau khi freeze, không sửa annotation/mẫu.

Packet payload SHA256: `31440ba8da0bdf325245bb5b6d584c04fcdc2af9f07e9a85ac00756fa1a6bee4`.
Annotation payload SHA256: `34eef5cc796453f2bc1d5012274d2d4b80907182dcf584f727475abc79290861`.

Annotator là **Codex AI**, chưa có human hoặc independent reviewer adjudication. Agent đã thấy số tổng hợp chấm train của lượt trước; corpus cũng đã dùng trong phát triển trước đây. Vì vậy “độc lập gold” ở đây nghĩa là không mở gold/report gold từng câu, không tính/scorer đáp án để quyết định annotation trong lượt này; không có nghĩa blind holdout, annotation chuẩn tuyệt đối hoặc chưa từng tiếp xúc train.

`verification/audit.py` chỉ hỗ trợ sampling và kiểm integrity/completeness/schema/provenance. Validator không chứng nhận diễn giải đúng hoặc chứng minh lời khai provenance của annotator; digest không chống tác giả cố ý sửa rồi tính lại. Tests chỉ dùng fixture tổng hợp.

## Bước tiếp theo

1. Sửa intent tiền/doanh thu bằng luật tổng quát và synthetic contrast tests trước, giữ nguyên resolver/catalog. Đây là sửa lỗi đã có evidence rulebook, không dùng đáp án gold.
2. Mở grammar theo các họ ngôn ngữ được annotate: thời gian/viết tắt, comparison neo kỳ, ranking/list và nhóm hàng rõ scope. Giữ annotation sample này là dev-exposed; không gọi đánh giá trên nó là held-out, không hứa quota câu mới.
3. Đóng băng manifest revision mới trước scoring. Báo số selected/compared/abstain/error và mọi mismatch; không bỏ câu để làm report xanh. Các câu cần hai scope/scalar/metric/domain mới phải giữ unsupported cho đến khi có contract riêng.
