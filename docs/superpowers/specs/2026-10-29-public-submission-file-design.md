# File public submission DataMate v1

Ngày: 2026-10-29, Asia/Saigon. Người dùng chọn phương án chạy Qwen2.5-7B trên Modal và cấp thêm trần 5 USD cho đúng một batch public test.

## Mục tiêu

Tạo một file `submission.jsonl` có thể upload thử lên mục Submission của Zalo AI Challenge 2026. File phải phủ đúng 1.000 ID trong `public_test/questions.jsonl`, giữ thứ tự đầu vào, dùng pipeline NLU v2 đã kiểm chứng và cache public được rebuild từ source hiện hành. Đây là phép chạy kiểm tra public; không dùng public test để huấn luyện, tuning prompt/schema/model, chọn threshold hoặc sửa đáp án thủ công.

## Ngoài phạm vi

Không tạo Docker, `predict.sh`, offline model bundle hoặc logs theo chuẩn vòng cuối. Không upload file lên portal, không đọc public score sau upload, không thay business/queryplan/rulebook, không mở rộng capability, không commit/push. Không dùng ID doanh nghiệp/câu hỏi làm feature hoặc logic đặc biệt.

## Các cách tiếp cận

1. Grammar bảo thủ rồi abstain phần còn lại: không tốn GPU nhưng coverage thấp; không phù hợp mục tiêu thử baseline NLU thực.
2. Qwen2.5-7B v2 trên Modal rồi QueryExecutor local: người dùng đã chọn. Giữ cùng model revision, prompt/schema/sampling đã freeze ở evaluation; chỉ đổi corpus/cache/rulebook/calendar sang public split.
3. Hybrid grammar ghi đè model: có thể cải thiện precision nhưng chưa được đánh giá độc lập và tạo thêm logic chọn đáp án; hoãn khỏi lần nộp thử đầu.

## Thiết kế

- Rebuild 14 doanh nghiệp public vào revision riêng dưới `reports/public_submission/v1/cache`; không ghi đè `cache/` hoặc cache train. Loader dùng `public_test/rulebook.md` và chỉ lấy mapping train theo contract hiện hành.
- Thêm tooling public-only để freeze jobs từ đúng bytes của `public_test/questions.jsonl`, `rulebook.md`, `calendar.csv`, cache và source NLU. Job chứa question/as-of/context cần thiết nhưng không gold, answer type, portal score hoặc routing ID trong prompt. Model config giữ Qwen2.5-7B-Instruct revision `a09a35458c702b33eeacc393d103063234e8bc28`, temperature0, seed20261029 và schema/prompt v2.
- Dùng private Modal batch hiện có với một GPU, tối đa một container, không endpoint/warm pool. Budget ledger mới ghi rõ authorization public-v1: limit5USD, tối đa1call, envelope4USD và margin1USD. Ledger baseline24USD cũ bất biến; không reset hoặc tái sử dụng nó để lách cap.
- Raw generations được exclusive-write và bind bằng job hash. Missing/duplicate/unknown request ID, backend error và truncated output giữ trạng thái riêng; không retry semantic hoặc repair JSON.
- Runner public local kiểm source/corpus/cache/job/generation hashes, load từng business, gọi strict parser/capability/QueryExecutor với `public_test/rulebook.md` và `public_test/calendar.csv`, rồi ghi prediction sidecar trước file nộp. Không mở gold vì public test không có gold.
- `submission.jsonl` có đúng một object cho mỗi câu theo thứ tự questions. Answer thành công giữ type/value; unanswerable giữ type/reason; mọi generation/plan/capability/resolve/data/execution failure thành `{"id":...,"type":"abstain"}` trong file nộp, với reason chỉ ở sidecar. JSON phải UTF-8, hữu hạn, không alias, không field nội bộ.
- Artifact cuối ở `reports/public_submission/v1/submission.jsonl`; reports chứa manifest, raw generation, receipt, sidecar và aggregate counts. Xác nhận app Modal completed rồi stopped/tasks0. Không coi reservation là hóa đơn thực.

## Rủi ro và kiểm soát

- Baseline evaluation chỉ đạt PA19,15%; file này là lượt test, không có bảo đảm điểm public. Không xem leaderboard để thay đổi chính file trong tác vụ này.
- Cache public hiện có được tạo trước hai loader fix; bắt buộc rebuild revision riêng trước inference.
- Public có1.000câu/14business, lớn hơn evaluation632; timeout3600s và envelope một call vẫn đủ theo batch632 mất580s, nhưng mọi partial output vẫn được giữ và phần thiếu trở thành abstain.
- Lượt Modal trước đã dùng hết authorization25USD; ledger mới tách biệt và hard-stop ở5USD theo phê duyệt mới.

## Acceptance

- Synthetic tests chứng minh prepare không đọc answers, prompt không chứa ID/gold, integrity reject corpus/cache/source/job/generation drift, và submission giữ đủ ID/thứ tự kể cả missing/error/truncated output.
- Rebuild public cache:14business,0crash; artifact mới không ghi đè cache cũ.
- Modal:1.000/1.000 output hoặc partial được đếm minh bạch; không quá1call/5USD; app stopped/tasks0.
- Submission validator xác nhận đúng1.000dòng,1.000ID duy nhất trùng questions, đúng thứ tự, chỉ field/type hợp lệ và JSON parse được. Sidecar báo distribution status/type, timings, model/source/data hashes; không tuyên bố PA khi không có gold.
- Targeted tests và `python scripts/harness.py check` đạt. Cập nhật docs/validation.md và docs/PROGRESS.md với bằng chứng và giới hạn.
