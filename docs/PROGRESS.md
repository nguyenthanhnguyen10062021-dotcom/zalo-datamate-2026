# Tiến độ và bàn giao cuối phiên — 2026-10-29

Ngày theo Asia/Saigon. Nhánh làm việc: `VuongNguyen`.

## QueryPlan executor v1 — cập nhật mới nhất 2026-10-29

Người dùng duyệt triển khai executor trên 10 API sẵn có. Đã thêm package `queryplan/`: validator Python không dependency mới, resolver thời gian/tên/đơn vị, capability check và dispatcher; `ExecutionResult` giữ Answer/status/stage. Không đổi loader/business/evaluator; chưa thêm model hoặc runner submission.

- [Contract, ví dụ và giới hạn](queryplan.md); [spec](superpowers/specs/2026-10-29-queryplan-v1.md), [plan và execution record](superpowers/plans/2026-10-29-queryplan-v1.md).
- Có **121 ca queryplan tổng hợp**, cả 10 operation kiểm tra expected literals và public API. Thêm 8 ca guard cho package mới. Full sau review mới nhất: **430 passed, 2 local_data deselected**.
- Review ban đầu tìm 2 lỗi period/calendar; lượt xác nhận tiếp tìm thêm nhãn list/dict gây TypeError trước kiểm tra kiểu. Đã sửa tại resolver với 6 regression RED → GREEN, giữ lỗi dữ liệu thành data_error/abstain theo dependency. Toàn bộ pytest sau sửa mới nhất: **431 passed, 1 skip helper cũ**.
- Data profile chạy lại hoàn tất exit 0: local_data **1 passed, 1 skip cũ**; verifier mới **409/409** khớp gold và legacy, **0 lỗi**, chọn **417/3000**, legacy bỏ **8**. Full trong lượt data là 424/2 deselected trước sáu ca nhãn cuối; full 430 và bare 431 đã chạy sau sửa. Verifier không gọi queryplan, source business/cache không đổi; không suy PA/coverage của executor/NLU từ kết quả này. Xem [validation](validation.md).
- Bước kế tiếp: inventory capability và verifier mở rộng không phụ thuộc legacy gate; sau đó model offline và runner tối thiểu để đo đầu-cuối.

## Cập nhật Harness Engineering — 2026-10-29

Theo yêu cầu người dùng, đã thêm harness phát triển tham khảo OpenAI/Anthropic và Trail-Code trên nền `d3ae67b`. Hồ sơ kiểm chứng được ghi trước khi commit harness; người dùng đã yêu cầu commit và đẩy lên nhánh `VuongNguyen`. Source nghiệp vụ, loader và evaluator không thay đổi; hai test cần dữ liệu được gắn marker local_data.

- Điểm vào agent: [AGENTS](../AGENTS.md), [bản đồ tài liệu](README.md), [kiến trúc](architecture.md) và hướng dẫn theo module.
- `python scripts/harness.py map` và `context <file.py>` lấy API/import impact từ working tree hiện tại, kèm quyết định qua [context-index](context-index.json). Có tính dependency của package initializer; graph tĩnh vẫn có giới hạn với dynamic/data dependencies.
- `doctor`, `check --profile fast|full|data` và [CI Windows/Ubuntu](../.github/workflows/ci.yml). [Hướng dẫn và nghiên cứu](harness-engineering.md) ghi nguồn Trail theo revision, cơ chế đã áp dụng và giới hạn.
- Kiểm chứng mới: harness **44 passed**; full **301 passed, 2 local_data deselected**; toàn bộ `python -m pytest -q -rs` **302 passed, 1 skip cũ**. Checkout tạm không có train/public_test/cache/venv cũng full 301 passed; data profile từ chối rõ khi thiếu input.
- Review độc lập đã tái hiện và sửa guard bỏ sót báo cáo bị force-track; đã có regression test. CI hosted chưa được xác nhận trong hồ sơ kiểm chứng local này; xem GitHub Actions của commit sau khi push. Không cài Trail/package/hook toàn máy.
- Đối chiếu gold mới qua data profile: **409/409 khớp gold và legacy, 0 lỗi**, chọn 417/3000, legacy skip 8. Local-data tests: 1 passed, 1 skip helper cũ. Báo cáo local: `reports/harness/business_verification.json` và `.md`; không rebuild loader/cache vì code loader không đổi.

Hồ sơ harness: [plan và execution record](superpowers/plans/2026-10-29-harness-engineering.md). Đây là bằng chứng của lượt trước khi thêm executor; trạng thái mới nhất ở đầu tài liệu.

## Đang ở bước nào

Đã có loader, thư viện nghiệp vụ bán hàng và QueryPlan executor v1. Bản sửa sau bốn lượt phản biện Gemini và executor đã hoàn tất; người dùng yêu cầu cập nhật nhánh `VuongNguyen`. Xem git log để xác định commit bàn giao. Chưa có pipeline hoàn chỉnh từ câu hỏi tiếng Việt đến đáp án vì chưa tích hợp NLU.

| Thành phần | Trạng thái khi kết thúc phiên |
|---|---|
| Bộ chấm local | Đã có code/test; chưa được chứng nhận tương đương evaluator BTC |
| Loader và schema chuẩn | Bản đầu đã chạy 44 doanh nghiệp train/public; chưa chứng minh mọi mapping đúng |
| Nghiệp vụ bán hàng | 10 API; có rulebook, period/calendar, filter và Answer |
| Patch sau review Gemini | Đã áp dụng vào code chính, thêm 39 ca kiểm thử trong repo |
| Contract QueryPlan v1 | Đã có validator Python nghiêm ngặt; JSON Schema/helper trong hồ sơ cũ vẫn là đề xuất, chưa cung cấp schema constrained decoding |
| Validator, resolver, dispatcher | Đã tích hợp thành QueryExecutor trên 10 API, kiểm thử tổng hợp; chưa đo gold executor/NLU |
| Model câu hỏi → QueryPlan | Chưa chọn model, weights hoặc runtime inference |
| PA/coverage toàn hệ thống, Docker và runner nộp bài | Chưa hoàn thiện |

## Đã hoàn thành trong phiên

1. Đọc và kiểm chứng phản hồi Gemini đến `GEMINI_RESPONSE_04.md`, giữ nguyên các bản phản hồi để đối chiếu. Sửa lỗi tiếng Việt ở TRAIN_METADATA và kiểm tra UTF-8 của các gói gửi.
2. Kiểm tra schema bằng jsonschema trong môi trường review riêng; phân biệt structural validation và semantic validation. Không thêm jsonschema vào requirements production.
3. Tái hiện lỗi của patch Gemini: thiếu import UnsupportedRule và ba regression do loại đơn hủy/trả quá muộn.
4. Sửa và áp dụng vào `business/sales.py`: validation theo dependency, order filters cho cancellation_rate/top_customers, kiểm tra cấu trúc cache và luật revenue_share đúng scope.
5. Lưu 39 ca kiểm thử mới về catalog lỗi, ORPHAN, trạng thái/kênh chưa rõ, thứ tự lọc, tỷ lệ hủy, API filters và mẫu số share.
6. Cập nhật API/validation và đẩy code cùng hồ sơ trao đổi lên GitHub.

## Các mốc đã đẩy lên GitHub

| Commit | Nội dung |
|---|---|
| [`c567b29`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/commit/c567b29) | Bản sửa nghiệp vụ, 39 ca kiểm thử và tài liệu API/kiểm chứng |
| [`211e492`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/commit/211e492) | Hồ sơ review Gemini đến lượt 04, metadata tổng hợp và trạng thái triển khai |

Dữ liệu BTC, cache, môi trường Python và báo cáo từng câu vẫn chỉ ở local theo `.gitignore`.

## Bằng chứng kiểm chứng cuối cùng trên code chính

- `python -m pytest -q -rs`: **258 passed, 1 skipped**. Skip cũ ở helper evaluator do tìm `answers.jsonl` sai vị trí; chưa sửa trong phạm vi patch.
- `python verify_business.py --out reports/business_verification_applied04`: **409/409 khớp gold và phép tính cũ, 0 lỗi**. Chọn 417 câu, legacy bỏ qua 8.
- Trước khi áp dụng patch, một tập 19 ca mới đã tái hiện lỗi trên baseline. Sau áp dụng, toàn bộ suite qua.
- Loader: số liệu từ lượt trước là 44 doanh nghiệp, 0 crash, 236 PASS, 116 bỏ qua, 0 FAIL; không chạy lại loader trong phiên sửa nghiệp vụ.

Bộ 409 chỉ đối chiếu revenue/cancelled_orders/quantity theo bộ chọn cũ, tương đương khoảng 13,6% train. Đây không phải PA toàn bộ 3000 câu, không chứng minh NLU hoạt động hoặc cả 10 API đã khớp gold.

Chi tiết: [validation](validation.md), [API](business.md), [hồ sơ triển khai](../ai_collaboration/rounds/001_business_to_nlu/CODEX_IMPLEMENTATION_04.md). Báo cáo chi tiết local: `reports/business_verification_applied04.json` và `.md`.

## Quyết định kỹ thuật giữ cho phiên sau

- V1 dùng QueryPlan có kiểm tra, resolver và public API nghiệp vụ; hoãn boolean/raw_decimal và parent-share.
- Cancellation_rate/top_customers chỉ nhận filter cấp đơn ở v1; product filter bị reject rõ ràng. Share mặc định có mẫu số cả shop, gồm doanh thu khách vãng lai.
- Không bỏ ORPHAN khi phép tính cần dòng hàng. Không biến DataError/UnsupportedRule hoặc lỗi resolve thành đáp án unanswerable tự động.
- Khi câu hỏi không nói khác, tháng này so tháng trước dùng cùng số ngày theo rulebook; kỳ giao một phần vẫn tính phần có dữ liệu.
- Schema phải có URI thuần. Resolver cần trả unit tường minh và xử lý nhập nhằng nhiều mã cùng tên; helper hiện tại chưa hoàn thiện hai phần này.
- Mọi split trên train hiện tại là đánh giá hồi cứu. Chia doanh nghiệp có giao nhóm khác với group-disjoint; artifact học từ dữ liệu phải rebuild theo phía dev.
- Người dùng đã giao Codex tự kiểm chứng, phản biện và chuẩn bị các lượt trao đổi, không chờ duyệt từng chi tiết kỹ thuật. Việc chuyển nội dung sang Gemini hiện vẫn qua file, chưa có cầu nối tự động.

## Thứ tự tiếp tục ở phiên sau

1. Đọc báo cáo này, PROJECT_CONTEXT, DECISIONS và source tại commit code mới; kiểm tra nhánh/worktree trước khi sửa.
2. Nếu có `GEMINI_RESPONSE_05.md`, tự kiểm chứng các phản chứng mới. Hiện **chưa có file phản hồi 05** trong repo. Gói prompt 05 đã chuẩn bị, cần kèm cập nhật code đã áp dụng khi gửi; không lấy snapshot `1c89252` làm source hiện hành.
3. Executor JSON v1 đã triển khai và kiểm thử; tiếp tục bằng [API hiện hành](queryplan.md), không áp dụng lại schema/helper lịch sử. Executor trả status/stage để caller ghi log local, chưa tự ghi file.
4. Mở rộng verifier sang các thao tác/kỳ còn thiếu, báo chọn/bỏ/lỗi/chênh; không chọn câu theo việc đã khớp gold. Cố định manifest đánh giá hồi cứu.
5. Chọn và tích hợp model offline sau khi executor ổn định; đo riêng độ đúng plan và kết quả đầu-cuối.
6. Hoàn thiện runner, Docker và đo PA/coverage/precision/thời gian trên phạm vi đã công bố.

## Điểm bắt đầu nhanh

> Tiếp tục từ docs/PROGRESS.md và docs/queryplan.md. Executor v1 đã có trong source; kiểm tra git status, git log và execution record trước khi sửa. Ưu tiên inventory capability/verifier mở rộng rồi tích hợp model offline; không suy PA đầu-cuối từ verifier business chọn lọc.

Các mục baseline nghiệp vụ/harness phía trên là lịch sử đã ghi; lượt triển khai executor và kết quả chạy mới được ghi riêng ở đầu tài liệu và validation.
