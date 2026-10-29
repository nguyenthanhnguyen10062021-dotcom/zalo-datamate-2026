# Vòng 002 — Hiện trạng có đủ tin cậy để đi tiếp chưa?

Ngày 2026-10-29 (Asia/Saigon). Bên gửi: Codex, theo yêu cầu người dùng mời Gemini phản biện. Đây là review trạng thái sau QueryPlan executor, inventory/verifier độc lập và audit annotation; không phải tiếp tục áp patch ở vòng 001. Chưa có phản hồi Gemini vòng 002.

## Revision và mục tiêu

Source review: commit `d99cac2` trên nhánh `VuongNguyen`, repo `nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026`. Commit nền executor `4fd268e`. File `GEMINI_HANDOFF.md` kèm bản chụp từ Git object của revision review, SHA256 từng file và synthetic tests; không cần truy cập đường dẫn local hoặc GitHub để đọc source.

Người dùng muốn biết trạng thái hiện tại đã đủ tốt để phát triển tiếp hay đang có khoảng trống/lỗi khiến kết quả kiểm chứng thiếu tin cậy. Đề nghị review độc lập, không chỉ xác nhận lại tài liệu. Phân biệt rõ: lỗi implementation có thể tái hiện; giới hạn capability được chọn có chủ ý; điểm thiếu bằng chứng; ưu tiên sản phẩm.

## Dữ kiện và giới hạn

- Runtime hiện có loader → bảng chuẩn → business; QueryExecutor validate/resolve/capability/dispatch gọi 10 API. Không model hoặc pipeline NLU hoàn chỉnh. Inference tương lai phải offline, eligible open weights <=15B; chưa chọn model/runtime.
- Verifier mới dev-only tách khỏi legacy. Inventory chỉ dùng câu hỏi để tạo manifest toàn corpus, freeze trước scoring. Verifier kiểm fingerprints rồi execute predictions trước đọc gold; dùng evaluator local cho type/format/value, không tự viết comparator list. Không chứng nhận evaluator local tương đương BTC.
- Train: 3000 câu, manifest v2 chọn **126**, ngoài selection **2874**. Selected chạm 7 API; top_products/top_customers/revenue_share có tests synthetic nhưng chưa chọn câu train. **125 compared =125 matched+0 mismatch;1 abstained;0 execution_errors;selected vẫn126**. Lệnh trả exit1 do abstain. Đây không phải PA toàn train/model, cũng không chứng minh plan được hiểu đúng nếu đáp án tình cờ trùng.
- Baseline legacy riêng: chọn417/3000, legacy skip8, compared/matched_gold/matched_legacy409/409, errors0. Không đo giao với126 nên không cộng số câu. Đây là evidence đã chạy ở lượt trước, không chấm lại trong lượt chuẩn bị packet.
- Audit không mở answers/report gold từng câu hoặc chạy scorer trong chính lượt audit. Lấy 10 câu mỗi reason bucket (40) và unit case (1), freeze sample rồi AI annotate. Mẫu40 có22 supported_plan,14 thiếu capability,4 domain chưa hỗ trợ; cộng unit case có23 plan đề xuất/41. Không ngoại suy tỷ lệ mẫu. Annotation chưa human/independent adjudication; agent đã thấy aggregate scores và train đã được dùng phát triển, không phải blind holdout.
- Ca abstain đã audit: **intent tiền/doanh thu nhầm thành quantity(unit tiền)**; theo rulebook tiền bán là revenue. Chưa sửa grammar, chưa thêm alias hoặc đổi unanswerable. Full câu hỏi/data doanh nghiệp không nằm trong gói này; chỉ cung cấp kết luận tổng hợp và ví dụ synthetic.
- Hai lỗi trước đó (mất dấu unit, gộp filter hai vế so sánh) được review synthetic và sửa RED→GREEN. Manifest/report v1 giữ nguyên; v2 có fingerprint selector mới. Không mở grammar theo kết quả sai/đúng của train trong lượt đó.
- Kiểm tra vừa chạy trên source sắp commit d99cac2: harness full **487 passed,2 local_data deselected**, bare pytest **488 passed,1 skip helper evaluator cũ tìm sai answers path**; fast passed. Hosted CI/Linux chưa xác nhận. Data regression nêu trên thuộc lượt trước; chưa chấm thêm gold ở audit hoặc lúc chuẩn bị review.

## Năm câu hỏi cần phản biện

1. **Implementation có thực thi đúng contract và đủ chặt để làm nền không?** Rà selector, manifest, runner, annotation utility, executor và đường IO. Tìm phản chứng tổng hợp về mất scope/qualifier, thời gian neo sai, nhãn/đơn vị, selection theo gold/legacy, input snapshot/fingerprint, mẫu số lỗi/abstain, comparator type/list/alias. Với lỗi Important/Critical hãy chỉ source line, input tối thiểu, expected/actual và regression test. Chỉ ra phần không thể kết luận nếu thiếu dữ liệu.
2. **Mức tin cậy của đánh giá hiện tại là gì?** 125/125 compared và 409/409 legacy chứng minh được gì? Có selection bias, accidental-answer agreement, stale/mixed input, thiếu coverage API/period/filter hoặc denominator chưa được test nào cần chặn trước bước kế? Phân biệt integrity do hash với correctness của plan và khả năng tổng quát hóa.
3. **Audit annotation có đủ dùng làm dev specification không?** Với AI annotations đã tiếp xúc aggregate/train, mẫu nhỏ theo reason/business và không có human adjudication: đề xuất validation/adjudication tối thiểu để tránh tự xác nhận hoặc lexical overfit. Không yêu cầu BTC rows/gold upload; hãy dùng synthetic contrast tests hoặc quy trình local có provenance. Có nên giữ nhóm plan-valid nhưng không execute trong một loại trạng thái khác?
4. **Nên ưu tiên điều gì trong hai bước tiếp theo?** Codex đang nghiêng về sửa intent tiền bằng regression tổng hợp, rồi mở các họ grammar có annotation; nhưng phương án khác là dừng đầu tư grammar ở baseline dev và tích hợp model offline sớm. Hãy phản biện lựa chọn này, nêu tradeoff, điều kiện dừng và acceptance checks đo được. Đừng đề xuất một roadmap dài không có cổng kiểm chứng.
5. **Ranh giới tối thiểu trước NLU/runner là gì?** Có cần thêm scalar/top1, growth đa metric hoặc hai filter scope ngay, hay tiếp tục reject rõ? Phân biệt bug cần sửa với capability mới. Đưa ra gate rõ cho baseline đầu-cuối đầu tiên; tránh refactor business hoặc chuyển SQL chỉ vì thích kiến trúc khác khi chưa có phản chứng/benchmark.

## Một số ca tổng hợp để thử phản chứng

Các câu dưới đây được viết làm minh họa synthetic, không phải bản sao rows train; không có nhãn gold BTC:

- `Tháng 9/2024 ca sáng bán được bao nhiêu tiền?` — cần phân biệt revenue với quantity.
- `Bán được bao nhiêu phần trong tháng 9/2024?` — giữ dấu đơn vị; không gán mọi “bao nhiêu X” là tiền.
- `Doanh thu tháng 1/2024 tăng bao nhiêu phần trăm so với tháng liền trước?` — kỳ trước là tháng12/2023, không phải trước as_of.
- `Doanh thu kênh "A" tuần này thay đổi bao nhiêu % so với tuần trước thanh toán "B"?` — hai filter scope không tự gộp vào một Filters.
- `Trong tháng 9/2024, khách nào mua nhiều đơn nhất?` — thiếu contract scalar; không tự coi list một phần tử là string.
- Đổi raw label thành list/dict; thiếu cache; duplicate/missing gold; thay corpus/plan rồi replay manifest; đổi thứ tự list/alias; thử output symlink/trùng input, file bị thay trong lúc replay. Đề nghị phân loại theo contract và mức ưu tiên, không mặc định mọi hạn chế là bug.

## Định dạng kết quả

Trả lời bằng tiếng Việt. Mở đầu với verdict riêng cho **nền tính toán/executor**, **đánh giá/phương pháp**, **sẵn sàng baseline đầu-cuối**: đạt / đạt có điều kiện / chưa đạt / chưa đủ bằng chứng, kèm gate cụ thể. Sau đó findings theo mức ảnh hưởng, căn cứ file:line, synthetic reproduction/test, độ chắc chắn; cuối cùng chọn đúng hai việc tiếp theo và các claims dự án cần rút lại nếu có. Nếu không tìm thấy lỗi hãy ghi đúng phạm vi đã kiểm, không chứng nhận toàn hệ thống hoặc tự tuyên bố đã chạy test.

Hãy tạo và đính kèm toàn bộ phản hồi dưới dạng file Markdown UTF-8 tải xuống được, tên **`GEMINI_RESPONSE_01.md`** cho **vòng002**, lượt01. Ghi ngày, revision, file đã thực sự đọc; chỉ ghi model nếu biết chắc. Không tạo placeholder hoặc bịa kết quả chạy. Nếu không đính kèm file được, xuất toàn bộ nội dung trong **một khối code bốn backtick nhãn markdown**, các code block bên trong dùng ba backtick. Không tuyên bố đã tạo file tải xuống nếu chỉ có text.
