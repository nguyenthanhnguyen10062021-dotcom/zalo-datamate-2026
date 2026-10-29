# Tiến độ và bàn giao cuối phiên — 2026-10-29

Ngày theo Asia/Saigon. Nhánh làm việc: `VuongNguyen`.

## Kết quả BTC do người dùng báo — public v3 ngày 2026-10-29

Người dùng đã nộp v3 và báo **0.10400**, tăng **0.30600** so v1 **-0.20200**. Đã kiểm lại hash file v3 đúng bản bàn giao:1000dòng,128non-abstain/872abstain. Với công thức `(correct-wrong)/1000`, nếu BTC chấm đủ128phản hồi đúng protocol thì suy ra **116correct/12wrong**, precision trên phần trả lời **90,625%**. Đây là suy luận từ aggregate score người dùng cung cấp, không phải public gold hoặc xác nhận từng câu.

Train pilot90 có54abstain:39semantic_rejected,11unsupported_plan,2unresolved_entity,1unsupported_capability,1invalid_plan. Question/plan-only review thấy cả lỗi NLU thật (filter tự thêm, sai comparison) và false rejection do biến thể ngôn ngữ của AOV/comparison/time. Chưa mở gold để gán correct cho các ứng viên hồi phục, chưa thay gate hoặc chạy GPU mới. Next: audit/freeze reference trên development, kiểm chứng thay đổi ngôn ngữ/grounding trên train development/calibration trước khi mở coverage; giữ v3 nguyên, không suy12public errors hoặc nới gate theo leaderboard.

## Semantic safety sau public score âm — hoàn tất đợt 1 ngày 2026-10-29

Người dùng báo public v1 **-0.20200**, giao cải thiện và cho phép Modal rerun không yêu cầu trần chi phí. Đã thêm gate offline kiểm question/plan trước dispatch, tích hợp cả hai runner và replay predictions có integrity. [Task và evidence](tasks/2026-10-29-semantic-safety.md).

- Replay cùng632evaluation predictions:303correct/182wrong/147abstain → **203/0/429**, PA19,15%→**32,12%**; chặn182sai và mất100đúng. Retrospective diagnostic có prior exposure, không blind/public guarantee. Development90 v1:10/9/71→7/0/83.
- Prompt3 giữ model7B/schema/sampling/gate: development90 **36correct/0wrong/54abstain**; evaluation632 **233/0/399**, PA **36,87%**, tăng30correct so chỉ thêm gate. Có1truncated generation trong632, giữ abstain; không public guarantee hoặc holdout độc lập.
- File được chọn: **`reports/public_submission/v3/submission.jsonl`**,1000dòng/1000ID đúng thứ tự, UTF-8 khôngBOM,46.926byte, validator/integrityPASS. **128answers/872abstain** (number112/percent8/list6/unanswerable2), score ceiling0,128. SHA-256 `38a59d278631f91d28a4c9314b92bf63d3f196504e0feba3a81b8c153e49a58a`. V2 replay97answers giữ làm ablation, không chọn để nộp. Không có gold public/PA.
- Public10GPU theo chỉ thị mới;2worker kẹt download rồi timeout900s. Recovery8GPUrảnh cho200request chưa có output, tổng<=10GPU; merge816primary+184secondary,16overlap chọn primary cố định,1000unique/stop.17worker metadata cùng một bộ model-file hashes. Mọi app đã stopped/tasks0; receipts/timeouts giữ nguyên. Đã lưu mặc định max10GPU vào root/tools AGENTS.
- Full cuối **688passed/2deselected**; data profile trước prompt/parallel PASS full683/2deselected,local1passed/1skip helper cũ,selected409/409. Business/loader/queryplan/scorer không sửa; historical ledgers/submissionv1 hash không đổi. Không commit/push hoặc upload portal.
- Người dùng đã nộp **v3** và báo score0.10400 (mục mới nhất phía trên). Độ phủ public còn12,8%; đợt tiếp cần mở capability/grounding bằng train development/calibration, không chọn threshold hoặc sửa câu theo public feedback. Docker/code-generation/domain mới chưa triển khai.

## File public submission v1 — hoàn tất 2026-10-29

Đã tạo `reports/public_submission/v1/submission.jsonl` (ignored): **1.000 dòng / 1.000 ID duy nhất**, đúng thứ tự public questions, UTF-8 không BOM, validator PASS. Phân bố: number529, percent115, list54, unanswerable48, abstain254. Không có public gold/PA; file chưa upload, chưa Docker. [Task/evidence](tasks/2026-10-29-public-submission-file.md).

Cache public mới14business/0crash; frozen jobs1000, prompt/schema v2, Qwen2.5-7B revision cũ. Batch gốc đủ1000generation; người dùng duyệt tăng tốc tối đa10GPU, pool bổ sung tối đa7GPU được dừng khi batch gốc hoàn tất,118generation bổ sung không dùng để chọn đáp án. Mọi app đã stopped/tasks0; local executor chạy8CPUworker, giữ thứ tự và error sidecar. Harness cuối **640passed/2deselected**, data gate trướccloud PASS409/409selected. Baseline ledger không đổi, không commit/push. Next action: người dùng upload file để test; không dùng public feedback để fitting/tuning.

## Baseline NLU/Modal — đã chạy evaluation 2026-10-29

Người dùng đã chấp nhận [plan chi tiết](tasks/2026-10-29-nlu-modal-baseline-plan.md), giao Codex tự quyết định/triển khai; Modal profile **vuonghungnguyen07**, tối đa **25 USD** cho đợt thử đầu. Baseline private batch với Qwen2.5-7B-Instruct đã chạy xong trên Modal; đây chưa phải public endpoint hay runner nộp bài offline.

- Đã thêm core `nlu/`: strict parser, prompt, generation/plan sidecar và public executor adapter; AST guard bảo vệ nlu và cấm lower layers import nlu. Schema v2 khóa operation/expected type/ranking/filter scope và tham số theo `period.kind`; pilot v1 có57/90 invalid-plan, evaluation v2 còn5/632, đều do revenue_share thiếu filter. Không auto-repair/last-block, không Modal SDK trong core hoặc đổi business/queryplan.
- Đã freeze train protocol3000câu,18/6/6business (development1815/calibration553/evaluation632). Pilotdevelopment90, evaluation632jobs;12question-onlyevaluationreferencesfreeze trướcmodeloutputs/gold, không blind/fold-clean.
- Evaluation cố định đủ **632/632 generation, 0 backend error**, JSON-valid632, contract-valid627. Local execution/scoring: **303 correct / 182 wrong / 147 abstain**, PA phạt `(correct-wrong)/N` **19,15%**, coverage **76,74%**, precision answered **62,47%**. Reference question-only:6/12 literal plan match, chưa adjudicate equivalence; không suy semantic accuracy từ literal match.
- Worker dùng revision model `a09a35458c702b33eeacc393d103063234e8bc28`, vLLM0.21.0/Python3.12.1 trên NVIDIAA10;632 output trong580giây local elapsed, model load160,77giây. App `ap-JlVK91P8vjr6OD7v5Cbe4D` đã stopped/tasks0. Ledger đủ4/4call, reservation tổng **24/25USD** gồm setup và5USDreserve; actual invoice/service meter chưa quan sát được nên không gọi24USD là tiền đã chi.
- Targeted NLU **40 passed**; harness full cuối **603 passed, 2 deselected**. Cache sửa lỗi được dùng tường minh; gold/scorer không lên worker, predictions freeze trước mở gold. Next action: error analysis trên development/calibration, xử lý entity/label grounding và comparison compatibility; cần scope/ngân sách mới trước GPU call khác hoặc offline submission runner.

## Sửa missingness cache và tên khách — 2026-10-29

Người dùng giao trực tiếp sửa đúng hai lỗi rồi dừng báo tiến độ. Đã sửa writer dùng nullable string để bảo toàn missingness/literal strings; join bổ sung tên thiếu khi mã khách khớp danh mục duy nhất. Giữ tên trên đơn/tên gốc, định danh, khách lẻ và duplicate-key policy; không NLU hoặc thay mapping/grammar/business/evaluator.

[Task và acceptance](tasks/2026-10-29-loader-missingness-customer-name.md) đã hoàn tất: 9 ca synthetic mới RED→GREEN; targeted **165 passed**, full **554 passed / 2 local_data deselected**. Data profile PASS: local_data 1 passed / 1 skip helper cũ; baseline cache cũ 409/409.

Cache train revision riêng `reports/loader_fixes_20261029/cache`: **30 doanh nghiệp, 0 crash**. Replay v4 **396/396 compared/matched**, ngoài selection 2604/3000; baseline riêng **417 selected / 8 skipped / 409 compared/matched**, 0 lỗi. Audit giữ **61 annotation / 46 plan / 15 not_run**: nay **41 matched / 1 mismatch / 4 abstain**, một mismatch customer-ranking được sửa, không mất ca. So 150 bảng canonical chỉ thấy khôi phục missingness và bổ sung tên; 661 file được bảo vệ không đổi. Không cộng mẫu số hoặc suy PA toàn train/model.

**Đã dừng theo yêu cầu.** Giữ cache mặc định và annotations/manifests cũ; cache mới cần truyền `--cache` tường minh. Chưa promote cache, rebuild public test, triển khai NLU hoặc commit/push. Các khoảng trống mapping/label bridge còn lại ở ngoài phạm vi.

Các mốc audit/thảo luận phía dưới là trạng thái trước bản sửa hai lỗi này.

## Thảo luận ba AI — mở vòng003 ngày 2026-10-29

Đã tổ chức [workflow Codex/Gemini Web/Antigravity](../ai_collaboration/README.md) và [vòng003 mới](../ai_collaboration/rounds/003_three_ai_restart/README.md): cùng BRIEF/source packet, prompt riêng và messages theo bên/lượt. Antigravity là bên mới, không phải Argon vòng002. [Chỉ mục lưu trữ](../ai_collaboration/archive/README.md) tách hồ sơ cũ khỏi luồng hiện hành, giữ nguyên bytes và đường dẫn lịch sử. Chưa gửi ra ngoài, chưa nhận phản hồi hoặc đồng thuận; không sửa runtime/cache/model trong tác vụ tổ chức này.

Next action thảo luận: người dùng gửi hai file BRIEF/SOURCE_PACKET và prompt tương ứng sang hai phiên mới, rồi đưa phản hồi về để Codex kiểm chứng. Chủ đề ưu tiên sau audit v4 là đề xuất mở đầu, chưa giao triển khai các sửa dữ liệu. Trạng thái source/audit dưới đây được giữ nguyên.

Kiểm tác vụ tổ chức: full **545 passed, 2 local_data deselected**; liên kết7tài liệu mới và18source fingerprint đạt, lịch sử không đổi. Không chạy lại data/gold.

## Mốc bàn giao trước vòng003

Người dùng yêu cầu commit/push inventory-verifier và audit annotation, đồng thời mở vòng phản biện Gemini mới. Xác định revision bàn giao bằng git log; các ghi chú “chưa commit/push” bên dưới thuộc thời điểm kiểm chứng trước bàn giao.

Source inventory/verifier/audit đã commit tại **`d99cac2`**. Sau [Argon lượt02](../ai_collaboration/rounds/002_capability_readiness/README.md), người dùng giao triển khai bước tiếp; bản Flash và phản hồi/review cũ được giữ riêng làm lịch sử.

## Audit ngữ nghĩa v4 — mới nhất 2026-10-29

- Đã chốt code/review trước audit bằng commit local **00043fa** trên VuongNguyen, chưa push. Source runtime/selector không đổi trong lượt audit; [task contract và findings](tasks/2026-10-29-v4-semantic-audit.md).
- Freeze61câu:37selected/8ops,12unparsed từ customer candidate pool110 và12từ share pool97. Reference question-only freeze trước xem candidate/catalog/gold; cùng AI tác giả, có prior train/source/aggregate exposure, không blind/human/independent adjudication.
- Selected37: reference/candidate JSON trùng37/37, đáp án37matched. Unparsed24:9reference plans,6capability gaps,5công nợ false positives,4cần catalog xác định group-kind. Không sửa grammar hoặc cố đạt quotaAPI.
- Execution46reference plans: **42compared,40matched,2mismatch,4abstained,0execution_errors**;15annotation không plan giữ not_run. Riêng9unparsed plans:3matched,2mismatch,4abstain. CLI evaluator xác nhận40/2/4; adapter local lượt đầu sai API đã vô hiệu hóa, `scoring_v2.json` dùng lại predictions freeze là report hợp lệ.
- Phát hiện cần xử lý trước model: canonical thiếu tên khách sau join; nhóm khách chưa map còn cần bằng chứng README; canonical-label bridge thiếu; đặc biệt `load_all.to_parquet` biến pd.NA thành literal string đã tái hiện bằng fixture tổng hợp. Bốn group-kind giải thích thêm bằng catalog, hai prescription predicate cần grounding contract; giữ annotations gốc.
- Next action đề xuất: sửa serialization missingness và customer-name join bằng synthetic tests, rebuild **cache revision riêng**, replay v4 và baseline riêng; mapping group/label bridge chốt riêng theo evidence. Chưa sửa các lỗi mới, chưa LLM, chưa PA toàn train;396/396 vẫn là bằng chứng selected snapshot cũ, không phủ2API này. Full mới545passed/2deselected; chưa chạy lại whole-data baseline409 trong lượt audit.

## Triển khai sau Argon — trạng thái mới nhất 2026-10-29

- Đã sửa intent tiền/đơn và capture span đơn vị; public `check_capability` và audit preflight tạo receipt riêng, giữ nguyên 41 annotation. Thêm comparison-only `previous_calendar_month/quarter` neo kỳ chính và grammar có giới hạn. Giữ plan1.0 additive, semantics cũ và các so sánh fixed-vs-as_of-relative hợp lệ; không sửa loader/business/evaluator hoặc tích hợp LLM.
- V3 **126/126** compared/matched, không còn abstain. V4 **396 selected/3000**, **396 compared/matched**, **0 mismatch/abstain/execution_errors**, 8 operation; ngoài selection2604. Giữ toàn bộ126 ca v3, thêm270. Top_customers/share chỉ có synthetic, chưa selected train. Đây là hồi cứu grammar+executor, chưa PA model/NLU.
- Preflight: 23 plan qua capability; 18 annotation không plan không kiểm. Optional filter resolution: 4 resolved,19 không cần; không chấm đáp án hoặc chứng nhận diễn giải đúng. Packet/annotations/digests cũ không đổi.
- Kiểm chứng cuối: **58 tests mới đạt**; full **545 passed, 2 local_data deselected**; bare **546 passed, 1 skip helper cũ**. Data profile exit0, local_data1passed/1skip; baseline riêng **417 selected, 8 skipped, 409/409 compared/matched**, 0 lỗi. Giao compared v4/baseline143, hợp662; không cộng hai mẫu số hoặc suy toàn-train PA.
- [Contract, acceptance và execution record](tasks/2026-10-29-selector-calendar-implementation.md), [validation](validation.md). Code hiện trong working tree, chưa commit/push tác vụ này; chưa hosted CI/Linux. Next action: audit question-only các bucket còn lại; scalar/hai scope/domain mới cần contract riêng, model/runner chưa triển khai.

Các mục phía dưới giữ bằng chứng từng mốc trước triển khai; “chưa sửa grammar/intent” trong mốc audit/v2 mô tả thời điểm đó.

## Audit annotation trước khi mở grammar — cập nhật mới nhất 2026-10-29

Đã audit **41 ca local** không mở gold hoặc scorer trong lượt này: ca quantity chưa resolve và mẫu cố định **40 câu chưa parse**, 10 mỗi reason bucket. [Kết luận và provenance](plan-annotation-audit.md), [task/evidence](tasks/2026-10-29-plan-annotation-audit.md).

- Ca chưa resolve là **intent tiền/doanh thu bị nhầm thành quantity**, rulebook §1 quy định rõ; không phải catalog thiếu alias đơn vị. Annotation đề xuất revenue giữ tháng/ca. Chưa sửa grammar nên abstain v2 vẫn còn nguyên.
- Mẫu 40 câu: **22 supported_plan, 14 unsupported_capability, 4 unsupported_domain**. Cộng ca tiền có 23 plan đề xuất trong 41 annotations; không ngoại suy sang 2874 câu hoặc gọi schema-valid plan là chắc đúng đáp án.
- Frozen packet/annotations/digests/câu hỏi/catalog evidence chỉ ở `reports/capability_inventory/audit_v1/`. AI annotation có prior aggregate score exposure, chưa human adjudication hoặc blind holdout; chưa chạy annotation qua executor/scorer. Giữ grammar/manifest/runtime nguyên trạng.
- Utility sampling/validation: 9 synthetic tests; targeted **54 passed**, full **487 passed, 2 deselected**, bare **488 passed, 1 skip helper cũ**. Integrity kiểm đủ 41 annotations và source/catalog hashes. Không chạy data/scorer vì không đổi phép tính; không có kết quả gold mới.
- Bước kế tiếp: sửa intent tiền bằng synthetic contrast tests, rồi mở các họ grammar có annotation/dev provenance (time/paraphrase, comparison neo kỳ, ranking/list và nhóm hàng). Hai filter scope, scalar và nghiệp vụ mới cần contract riêng; không ép vào API hiện hành. Chưa commit/push.

## Capability inventory / verifier độc lập — mốc triển khai 2026-10-29

Đã thêm `inventory_capabilities.py`, `verify_queryplans.py` và package dev-only `verification/`; không thay runtime, nghiệp vụ hoặc thêm model. [Contract/lệnh](capability-verification.md), [plan/evidence](superpowers/plans/2026-10-29-capability-verifier.md).

- Frozen manifest v2 phủ **3000** câu; grammar bảo thủ chọn **126**, chưa chọn **2874**, chạm **7/10 operation**. Dạng chuẩn cả 10 API được kiểm thử tổng hợp; chưa chọn train cho top_products/top_customers/share. Không gọi 126 là toàn bộ capability hoặc coverage sales.
- Verifier mới độc lập legacy: **125/125 compared khớp**, **0 mismatch, 1 abstain quantity/unresolved_entity, 0 execution_errors**; selected vẫn **126**, exit **1** có chủ ý. Giữ v1/v2 và lý do revision; không bỏ câu lỗi hoặc tuning grammar theo gold. Không cộng với bộ 409 cũ khi chưa đo giao.
- Review synthetic độc lập tìm 2 lỗi unit mất dấu/scope filter so sánh, đã sửa với regression RED→GREEN. Targeted **100 passed**; full **478 passed, 2 deselected**; bare **479 passed, 1 skip helper cũ**. Data profile baseline riêng đạt **409/409**, chọn **417/3000**, legacy bỏ **8**, 0 lỗi.
- Bước tiếp theo: audit plan và các bucket chưa parse, ghi nguồn annotation độc lập gold để mở coverage; sau đó baseline model offline. Chưa có gold plan chuẩn, group-disjoint hoặc PA model/NLU. Chưa commit/push trong tác vụ này.

## QueryPlan executor v1 — mốc triển khai 2026-10-29

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
| Validator, resolver, dispatcher | QueryExecutor trên10API có synthetic; verifier grammar+executor v4 khớp396/396 selected train, chạm8API; chưa PA model/NLU |
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
4. Đã có verifier độc lập và frozen manifest hồi cứu; tiếp tục audit plan/grammar chưa hỗ trợ theo [capability verification](capability-verification.md), không loại/chọn theo kết quả khớp gold.
5. Chọn và tích hợp model offline sau khi executor ổn định; đo riêng độ đúng plan và kết quả đầu-cuối.
6. Hoàn thiện runner, Docker và đo PA/coverage/precision/thời gian trên phạm vi đã công bố.

## Điểm bắt đầu nhanh

> Tiếp tục từ docs/PROGRESS.md và docs/plan-annotation-audit.md. Executor có tại 4fd268e; inventory/verifier và audit mới ở working tree. Đã đóng băng 41 annotations AI độc lập gold trong lượt audit, có provenance/giới hạn. Sửa intent tiền trước rồi mở grammar theo annotation dev, không ép hai filter/scalar vào contract v1 hoặc suy PA model từ hồi cứu.

Các mục baseline nghiệp vụ/harness phía trên là lịch sử đã ghi; lượt triển khai executor và kết quả chạy mới được ghi riêng ở đầu tài liệu và validation.
