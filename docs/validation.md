# Kiểm chứng bản sửa nghiệp vụ ngày 2026-10-29

## Semantic safety và prompt3 — 2026-10-29

Người dùng sau đó báo BTC chấm publicv3 **0.10400** (v1-0.20200; tăng0.30600). Hash submission tái kiểm đúng bản bàn giao. Với128non-abstain và công thức+1/-1/0 trên1000câu, suy ra116correct/12wrong và precision90,625% nếu protocol chấm đúng128phản hồi. Đây là suy luận aggregate từ score người dùng báo, không phải public gold hoặc audit từng câu; chưa biết12câu nào sai. Không dùng feedback để fit gate/threshold hoặc sửa câu theo ID.

[Task và commands/evidence](tasks/2026-10-29-semantic-safety.md), [contract](nlu.md). User báo publicv1 score-0.20200; không có public gold để gán đúng/sai từng câu. Gate chỉ kiểm question/plan, không nhận ID/score/gold, không sửa plan hoặc thay failure thành zero/unanswerable. Model, schema, sampling và business không đổi; prompt3 là nhánh thử riêng sau replay.

| Phép đo cùng evaluation632 | Correct | Wrong | Abstain | PA |
|---|---:|---:|---:|---:|
| Baseline prompt2 gốc |303|182|147|19,1456%|
| Cùng predictions + semantic gate1 |203|0|429|32,1203%|
| Fresh Modal prompt3 + cùng gate1 |233|0|399|36,8671%|

- Gate chặn182wrong nhưng mất100correct của baseline; prompt3 tăng30correct so cùng predictions+gate. Giữ632trong denominator; có prior train/source/question-only exposure nên là retrospective diagnostic, không blind holdout hay public precision guarantee. Không đổi gate sau khi nhìn public replay.
- Prompt3 evaluation:632generation/632unique,0backend errors,631stop/1length;630contract-valid. Statuses:answered229/unanswerable4/semantic_rejected333/unsupported_plan47/unsupported_capability12/unresolved_entity5/incomplete_generation1/invalid_plan1. Tất cả predictions freeze trước gold. Development90/1815:36correct/0wrong/54abstain; ngoài selection1725.
- Targeted semantic/orchestration tests xác nhận contrast intent/filter/time/ranking, không dispatch plan sai nghĩa, giữzero/unanswerable có evidence; replay kiểm hash/source/routing/raw-plan, không đọc public gold, giữ thứ tự/mẫu số và exclusive artifacts. Full mới nhất **688passed/2deselected**, gồm transport-prefix/recovery và merge CLI regression. Data profile trước các thay đổi prompt/parallel:full683passed/2deselected,local1passed/1skip helper cũ,selected409/409. Business/loader/queryplan/scorer không đổi trong đợt này.
- Public replayv2 đã có1000rows/97answers/903abstain, score ceiling0,097. Public prompt3 đã freeze trước inference, chạy10fixedshards theo chỉ thị mới; service xác nhận app`ap-TnmPVq5oX8MmV92VaAdrOA` có10tasks. App development/evaluation và app lỗi Python đều stopped/tasks0 trước public. Python3.12Modal env có sẵn; không cài dependency hoặc dùng Python3.14 serialized worker.
- Historical budget/submissionv1 hashes giữ nguyên theo task. Parallel experiment reservation17USD là envelope riêng, không phải invoice. Chưa Docker/offline packaging hoặc upload portal.
- Publicv3 hoàn tất:1000rows/1000unique/đúng thứ tự/UTF-8 noBOM/46.926byte,validator và source/cache/predictions hashesPASS. Types112number/8percent/6list/2unanswerable/872abstain; score ceiling0,128. SHA-256 `38a59d278631f91d28a4c9314b92bf63d3f196504e0feba3a81b8c153e49a58a`. Selected raw1000unique/stop,0missing; không execution_error. Hai worker primary timeout900s sau kẹt download;8GPUrecovery chỉ chạy200request chưa có output, tổng<=10. Merge816primary+184secondary,16overlap chọn primary cố định.17worker metadata có một model-file hash set. Tất cả5app của đợt đã stopped/tasks0; failure/partial receipts giữ nguyên, không che timeout bằng claim toàn-cloud error-free.

## File public submission v1 — 2026-10-29

- Artifact `reports/public_submission/v1/submission.jsonl`: **1.000 dòng / 1.000 ID duy nhất / đúng thứ tự / 64.040byte / UTF-8 không BOM**. SHA-256 `4487a9e300acd6996b621f6e195613e1e931f70246854d5a9405bf3dc8566591`; validator type/shape/fields/finite PASS. Cache/source/job fingerprints và predictions digest tái kiểm PASS; gold_opened_this_run=false.
- Generation gốc1.000/1.000; statuses: answered698, unanswerable48, unresolved_entity143, unsupported_capability24, unsupported_plan57, invalid_plan27, data_error2, incomplete_generation1. Upload types:number529/percent115/list54/unanswerable48/abstain254. Không sửa/repair lỗi hoặc rút khỏi mẫu số; không public gold/PA.
- Cache14business/0crash; jobs hash `1ecc2ee7c4cab65039d2aa70048b8a6b1a1c288deb019b930603d7f5de35321d`. Core Qwen revision/prompt/schema/sampling giữ nguyên. Local executor8process theo business; synthetic serial/parallel order test PASS. Harness cuối640passed/2deselected; data gate trướccloud409/409selected, không whole-train PA.
- App gốc `ap-EuK7RZHXJon3m4myvJvEqK` completed/stopped/tasks0. User duyệt thêm tối đa10GPU; pool bổ sung `ap-nD2iIoOkRhwcb48RCJxc3N` capped7, generated118/408 rồi chủ động stopped/tasks0 khi gốc đủ1000; output bổ sung không dùng trong file cuối. Các app lỗi SDK trước đó đều stopped/tasks0. Bound cả hai pool + allowance + margin4,843488USD trongcap5USD; không phải hóa đơn. Baseline ledger hash không đổi.
- File chưa upload, chưa Docker. Chi tiết ở [task](tasks/2026-10-29-public-submission-file.md); artifacts/receipts từng dòng chỉ reports/ ignored.

## Baseline NLU/Modal — evaluation cố định 2026-10-29

[Contract và execution record](tasks/2026-10-29-nlu-modal-baseline-plan.md). Private batch trên profile `vuonghungnguyen07`, không public endpoint; model Qwen2.5-7B-Instruct revision `a09a35458c702b33eeacc393d103063234e8bc28`, vLLM0.21.0/Python3.12.1, NVIDIAA10. Schema/prompt v2 được đóng băng trong `evaluation_jobs_v2.json` trước generation; predictions632câu được ghi trước khi local runner mở gold.

- Cloud artifact: **632/632 request ID duy nhất, 632 stop, 0 error**, 2metadata; local elapsed580,015giây, model load160,767giây. App `ap-JlVK91P8vjr6OD7v5Cbe4D` được Modal xác nhận completed rồi stopped/tasks0. Job hash `8e37b19e36a64f696196c982e17b339ae4099f5a5aa24f99684cb245853695c0`; reports/ chứa raw hashes/model-file hashes và receipt, không track row-level data.
- Contract/execution: JSON-valid **632**, plan-contract-valid **627**; statuses answered474, unanswerable11, unsupported_plan23, unresolved_entity104, unsupported_capability15, invalid_plan5. Cả5 invalid là revenue_share thiếu filter; không repair hoặc loại khỏi mẫu số.
- Score trên fixed evaluation business partition: **303 correct / 182 wrong / 147 abstain / 632 total**; penalized accuracy **19,1456%**, coverage **76,7405%**, answered precision **62,4742%**. Reference plan question-only12câu:6literal match, chưa equivalence adjudication; cùng AI/source exposure, không blind/human/fold-clean.
- Ledger đã đủ4/4call, tổng reservation24USD gồm setup và5USDmargin trong cap25USD. Maximum compute reservation của lượt cuối1,9346272USD; actual invoice/service meter còn lag/chưa quan sát, không đồng nhất reservation với chi tiêu thật. Không dispatch thêm.
- Regression: targeted NLU **40 passed**; harness full sau sửa **603 passed, 2 local_data deselected**. Không đổi business/queryplan/loader/scorer trong lượt sửa schema/prompt; cache loader revision được truyền tường minh. Chưa chạy hosted CI/Linux, public test, offline container hoặc official evaluator.

## Sửa missingness cache và tên khách theo mã — 2026-10-29

[Task contract/evidence](tasks/2026-10-29-loader-missingness-customer-name.md) theo yêu cầu người dùng, chỉ hai sửa dữ liệu. Writer chuyển object sang nullable string trực tiếp thay vì stringify missing scalars; join chỉ bổ sung tên thiếu bằng mã duy nhất. Không đổi business/selector/queryplan/scorer hoặc thêm dependency.

- 9 ca synthetic mới: RED6failed/3passed trên source cũ; GREEN9passed. Có roundtrip None/NaN/pd.NA/NaT, literal strings/zero đầu, số/bool/date/mixed/nested và input immutability; tên có sẵn/tên gốc/key/walk-in/duplicate/no-code giữ contract, customer ranking qua cache thật có expected literals.
- Targeted loader/parsers/infer **165 passed**; harness full **554 passed, 2 local_data deselected**. Doctor đúng 5 pinned packages. Data profile PASS, local_data **1 passed / 1 skip** helper evaluator cũ; baseline cache mặc định **409/409**, riêng với cache mới dưới đây.
- Rebuild train revision riêng `reports/loader_fixes_20261029/cache`: **30 doanh nghiệp / 0 crash**. `verify_queryplans.py --manifest reports/capability_inventory/manifest_v4.json --cache reports/loader_fixes_20261029/cache --out reports/loader_fixes_20261029/verification_v4.json`: **396 selected/compared/matched**, 2604 outside / 3000 total, 0 mismatch/abstain/execution_errors. Baseline mới qua `verify_business.py --cache reports/loader_fixes_20261029/cache --out reports/loader_fixes_20261029/business_verification`: **417 selected / 8 skipped / 409 compared**, 409 khớp gold và legacy, 0 errors. Hai CLI exit0; không cộng mẫu số.
- Audit replay nguyên 46 reference plans, giữ 15 not_run trong tổng61: **42 compared = 41 matched + 1 mismatch, 4 abstain, 0 execution_errors**. Một mismatch customer-ranking→matched; mọi kết quả khác giữ outcome. CLI evaluator trên cùng predictions freeze xác nhận **41 correct / 1 wrong / 4 abstain**. Không sửa frozen annotation hoặc tính thêm bare-group plans sau gold.
- So **150 bảng canonical** cũ/mới không thấy thay đổi shape/schema hoặc giá trị ngoài khôi phục missingness và bổ sung tên. Receipt kiểm **661 protected files không đổi**, gồm cache mặc định, old manifests/annotations và source/corpus liên quan; hash 423 cache files mới. Report chi tiết/dự đoán/errors chỉ reports/ ignored. Cache mặc định chưa promote; không rebuild public test hoặc claim hosted CI/model PA.

Các số audit bên dưới giữ nguyên snapshot trước sửa; không cộng mẫu số hoặc suy toàn-train/model PA.

## Audit semantic v4 — kiểm mới nhất, chưa sửa source

Nền commit local00043fa. [Task/acceptance/findings](tasks/2026-10-29-v4-semantic-audit.md) được chốt trước lấy mẫu. Freeze61câu và annotation trước candidate comparison/catalog/gold; không blind hoặc independent/human adjudication. Candidate pools lexical customer110/share97, mẫu12mỗi pool; selected37 phân tầng8ops, không suy population accuracy.

- Selected37 reference/candidate JSON trùng37/37 và đáp án37matched. Unparsed24:9plan hiện có,6capability gaps,5debt-domain false positives,4cần catalog phân loại group. Giữ denominator và không thay sample sau đọc.
- Reference46plans: **42compared=40matched+2mismatch**, **4abstain**, **0execution_errors**;15annotation không chạy vì không plan. Riêng9plan từ unparsed:3matched/2mismatch/4abstain. Cả2mismatch trả unanswerable dù gold có đáp án; không thay bằng abstain sau chấm.
- Local scoring adapter lượt đầu sai thứ tự arguments và kiểu kết quả, report `scoring.json` vô hiệu. `scoring_v2.json` chấm cùng predictions đã freeze bằng API đúng, có3synthetic adapter assertions; CLI evaluator chính thức xác nhận **40correct/2wrong/4abstain** trên46câu, exit0. Exit0 ở CLI không có nghĩa all-correct. Không lấy tỷ lệ này làm modelPA.
- Chẩn đoán nguồn: customer-name join thiếu tên; customer-group mapping thiếu nhưng căn cứ README còn chưa đủ;2unaccented labels và2canonical vocabulary bridges unresolved.4baregroup có catalog evidence bổ sung,2prescription predicates cần grounded filter contract. Không sửa originals hoặc execute thêm4baregroup sau gold để đổi mẫu số.
- Tái hiện **lỗi source hiện tại** bằng data tổng hợp: missing key pd.NA → literal string khi ghi parquet, missing1→0. Fixture/output/receipt ở reports/ ignored, source/cache không đổi. Chưa đo ảnh hưởng toàn cache, chưa rebuild hoặc tự suy lỗi chỉ do cache cũ.
- Harness full mới **545passed/2local_data deselected** trước audit; source/tests không đổi sau đó. Fast cuối và integrity receipts kiểm source/cache/old manifests/annotations. Không chạy lại data baseline409 hoặc toàn396; số của các lượt trước giữ snapshot riêng. Chưa hostedCI/Linux, model hoặc toàn-trainPA.

## Sau Argon: intent/span, preflight, calendar và grammar — mới nhất

[Task contract/evidence](tasks/2026-10-29-selector-calendar-implementation.md) được chốt trước sửa code. Bốn file tests tổng hợp mới có **58 ca đạt**, có RED→GREEN cho intent/span, preflight, calendar và grammar, negative contrasts và compatibility. Không đổi loader/business/evaluator/requirements; không LLM.

- `doctor`: Python3.14.10, cả5 pinned packages khớp, local data ready. `harness.py check --profile data`: exit0, full **545 passed, 2 deselected**; local_data **1 passed, 1 skipped** helper evaluator cũ. Bare `pytest -q -rs`: **546 passed, 1 skipped** cùng helper. Chưa hosted CI/Linux.
- Freeze v3 sau Task1 trước scoring: **126 selected/compared/matched**, 0 mismatch/abstain/execution_errors,7 operation, exit0. V3 giữ hash selector Task1; hiện stale với selector Task2, không tự rebuild/replay. V1/v2 và ca abstain lịch sử được giữ nguyên.
- Freeze v4 sau Task2 synthetic checks trước scoring: total3000, **selected396, outside_selection2604, compared396, matched396**, 0 mismatch/abstain/execution_errors, exit0. Status answered395/unanswerable1. Phân bố: revenue242, order_count39, revenue_growth32, cancellation_rate26, average_order_value25, cancelled_orders20, top_products10, quantity2. Top_customers/share chưa selected train; synthetic không thay thế kiểm chứng train.
- V4 giữ126 selected v3 và thêm270. Baseline legacy chạy riêng: selected417, skipped8, compared409, matched_gold409, matched_legacy409,errors=[]. Giao compared v4/baseline143, hợp662; không cộng396+409 hoặc gọi662 là một lần đo PA thống nhất.
- Preflight envelope v2 mới: 23 supported capability,18 not_checked; optional filter resolution4resolved/19not_required, không answer/scorer. Kiểm receipt/envelope/source hashes và original input hashes; giữ nguyên packet/annotations41. Đây không phải annotation accuracy, period validation hoặc execution evidence.
- Report v4 source hashes khớp runtime cuối; source không sửa sau lượt kiểm cuối. Sau scoring chỉ cập nhật tài liệu. Review diff do chính agent triển khai, không có independent adjudication mới. Grammar không tuning theo mismatch hoặc public test. Toàn bộ rows/manifests/receipts ở reports/ ignored; đây là retrospective dev evidence, chưa blind holdout, model PA hoặc toàn-train coverage.

Các mục bên dưới là snapshot kiểm chứng các mốc trước đó.

## Audit plan annotation — 2026-10-29

- Nền 4fd268e cộng working tree inventory/verifier đã có; thêm utility `verification/audit.py` và synthetic tests. Không sửa selector/manifest/resolver/business/evaluator. [Phương pháp và kết luận](plan-annotation-audit.md), [task record](tasks/2026-10-29-plan-annotation-audit.md).
- Audit không mở answers hoặc report gold từng câu, không chạy scorer/answer computation. Re-resolve unit qua catalog xác định intent tiền bị phân loại quantity; 40 unparsed samples deterministic, 10/bucket, đóng băng trước annotation. Cả 41 đều có rationale, evidence, fingerprint và decision; 23 plan schema-valid gồm ca intent tiền + 22 trong mẫu. 14 cần capability mới, 4 domain chưa hỗ trợ.
- Annotation/packet digests và corpus/catalog fingerprints kiểm tra qua; file frozen v2 còn hợp lệ với selector cũ. Artifact reports/capability_inventory/audit_v1/ ignored. Source utility thêm check annotation digest sau freeze được ghi bằng receipt riêng, không ghi đè annotations.
- 9 tests utility (RED thiếu module, rồi RED chỉnh rationale sau digest không bị phát hiện → GREEN); targeted audit+inventory+verifier **54 passed**. Full **487 passed, 2 local_data deselected**; bare pytest **488 passed, 1 skip helper evaluator cũ**. Fast cuối kiểm doc links/whitespace/source boundary.
- Không chạy data profile/gold verifier lần này vì không đổi tính toán. Kết quả 125 matched/1 abstain và baseline 409/409 phía dưới thuộc lượt trước, không phải đo mới hoặc annotation accuracy. Chưa sửa ca intent tiền.
- Review semantic bởi chính AI annotator, không có human/independent adjudication. Prior aggregate score exposure và train đã dùng trước đây được ghi rõ; không gọi đây là blind/held-out, không ngoại suy 22/40 cho toàn bucket. Không LLM inference integration, dependency mới, commit/push.

## Capability inventory / verifier độc lập — 2026-10-29

Nền `4fd268e` cộng working tree; không sửa loader/business/queryplan/evaluator hoặc requirements. Grammar dev bảo thủ, kiểm chứng hồi cứu, không tuning public test. [Contract và lệnh](capability-verification.md); [plan/evidence](superpowers/plans/2026-10-29-capability-verifier.md).

- Targeted inventory/verifier/guard: **100 passed**; gồm mẫu chuẩn cả 10 API, frozen manifest integrity, evaluator list alias/order, giữ lỗi/mismatch trong mẫu số, cache lỗi và exception implementation. Smoke hai CLI trên corpus tổng hợp giữ 1 mismatch và 1 abstain, exit 1 đúng contract.
- Full sau sửa review: **478 passed, 2 local_data deselected**, fast/full exit 0. Bare pytest: **479 passed, 1 skip helper evaluator cũ**.
- Inventory v2 chạy trên **3000** câu train: **126 selected, 2874 outside_selection**, 7 operation. Phân bố selected: revenue 62, cancellation_rate 22, cancelled_orders 14, quantity 3, order_count 7, average_order_value 14, revenue_growth 4. Top products/customers và share chưa được grammar chọn câu train nào; chỉ có synthetic coverage.
- Verifier v2: **125 compared, 125 matched, 0 mismatch, 1 abstained (unresolved_entity ở quantity), 0 execution_errors**. Selected vẫn là 126; exit **1** theo contract vì còn abstain, không loại câu đó để trình bày 126/126. Report không chứng minh độ phủ sales/API hoặc PA model/NLU.
- Trước khi sửa review đã đóng băng/chấm v1: cùng selected 126, compared/matched 125, abstained 1, mismatch/execution_errors 0. Review độc lập chỉ dùng synthetic tìm 2 Important: unit mất dấu và filter scope bị gộp giữa các vế; 3 regression RED→GREEN. Giữ nguyên v1, tạo v2 với selector fingerprint mới; đã xác nhận v1 bị từ chối replay âm thầm sau thay source. Không mở rộng grammar hoặc loại câu theo gold.
- Reports local ignored: `reports/capability_inventory/manifest_v1.json`, `verification_v1.json`, `manifest_v2.json`, `verification_v2.json` và Markdown summaries. Các fingerprints question/rulebook/selector/scorer/runtime/cache/gold được giữ trong manifest/report; không sao chép rows vào tài liệu hoặc CI.
- Data profile baseline riêng: **exit 0**, full 474/2 deselected trước 4 ca cuối, local_data **1 passed, 1 skip cũ**; legacy chọn **417/3000**, bỏ **8**, **409/409** khớp gold và legacy, **0 lỗi**. Source business/cache không đổi; lượt này không gọi verifier mới. Full 478/bare 479 ở trên chạy sau sửa. Chưa đo giao giữa hai tập, không cộng mẫu số.
- Chưa chạy hosted CI/Linux. Chưa có audit gold plans, group-disjoint hoặc đánh giá dữ liệu chưa từng tiếp xúc. Next action: audit plan/unsupported buckets theo manifest, ghi annotation provenance độc lập gold rồi mở coverage; sau đó baseline model offline.

## QueryPlan executor v1 — lượt triển khai mới nhất 2026-10-29

Nền `6dc41d7` cộng thay đổi working tree chưa commit. Thêm `queryplan/`, không đổi source loader/business/evaluator hoặc requirements; fixture chỉ dùng dữ liệu/plan/calendar tổng hợp.

### Lượt xác nhận tiếp cùng tác vụ

Working tree đã có spec/plan/source khi tiếp tục; không tạo lại executor hoặc ghi đè phần việc đang có. Chạy lại doctor: interpreter/dependencies đạt, local data sẵn. Review độc lập mới tìm một lỗi Important: `_labels` gọi unique trước kiểm tra kiểu nên list/dict gây TypeError. Sáu regression trên kênh/tên hàng/đơn vị đã thất bại trước sửa, qua sau khi chuyển kiểm tra kiểu lên trước unique; order_count không phụ thuộc nhãn đó vẫn chạy. Không bắt chung TypeError hoặc đổi ngữ nghĩa business.

- Targeted queryplan: **121 passed**.
- Harness full sau sửa: **430 passed, 2 local_data deselected**, exit 0.
- Bare pytest sau sửa: **431 passed, 1 skipped**; cùng skip helper cũ dưới đây.
- Smoke JSON tổng hợp qua json.dumps/json.loads với tên hàng tiếng Việt và Answer.to_submission: trả đúng revenue 90, JSON number hợp lệ.
- Data profile chạy lại **exit 0**: full 424/2 deselected và local_data **1 passed, 1 skipped** trước sáu ca nhãn cuối; verifier mới chọn **417/3000**, legacy bỏ **8**, đối chiếu **409/409** khớp gold và legacy, **0 lỗi**. Report local ignored `reports/harness/business_verification.json` và `.md`, cùng rulebook SHA256 ghi bên dưới. Full 430/bare 431 đã chạy sau sửa resolver; business/cache không đổi, không rebuild cache. Verifier này không gọi executor và không đo PA/coverage NLU.

### Bằng chứng lượt triển khai trước khi xác nhận tiếp

- Queryplan tests: **115 passed**; cả 10 operation có expected values độc lập và đối chiếu public API, thêm normalize/semantic/resolution/capability/error/period/input immutability.
- Harness full sau sửa review: **424 passed, 2 local_data deselected**, fast/full exit 0.
- Toàn bộ `.\.venv\Scripts\python.exe -m pytest -q -rs`: **425 passed, 1 skipped**; skip cũ `evaluate/test_evaluate.py::test_self_score_real_file` do helper tìm answers.jsonl sai vị trí. Không sửa helper trong tác vụ này.
- Review độc lập chạy lại 100 tests trước sửa, tìm 2 Important: catch lỗi period quá rộng và calendar thiếu ô làm crash. Main tái hiện bằng 3 ca thất bại, sửa ở boundary input hẹp, thêm tổng 15 ca period/calendar. Unexpected KeyError/ValueError/RuntimeError từ Periods nay được propagate.
- `.\.venv\Scripts\python.exe scripts/harness.py check --profile data`: exit 0; local_data **1 passed, 1 skipped**, skip helper cũ nêu trên; verifier mới chọn **417/3000**, legacy bỏ **8**, đối chiếu **409/409** khớp gold và legacy, **0 lỗi**. Report local ignored: `reports/harness/business_verification.json` và `.md`. Rulebook SHA256 `740267bccba29df70f745bc39968bbec5b3e62dada2c858c45314f3ec723d113`.
- Data profile bắt đầu trước các sửa period/calendar và 15 ca cuối (full của riêng lượt data là 409 passed/2 deselected). Full 424 và bare pytest 425 ở trên chạy sau sửa; source business/cache không đổi trong toàn lượt verifier. Không rebuild loader/cache hoặc chạy lại phép đối chiếu đắt tiền vì verifier không gọi queryplan. Không suy PA hoặc coverage của executor/NLU từ hồi quy business này.

Xem [contract executor](queryplan.md) và [plan/evidence](superpowers/plans/2026-10-29-queryplan-v1.md). Chưa chạy hosted CI/Linux; chưa đo model hoặc pipeline đầu-cuối.

## Kiểm chứng harness ngày 2026-10-29

Code nền `d3ae67b` cộng bản triển khai harness; bằng chứng bên dưới được chạy trước khi commit trên Windows/Python 3.14.10. Không đổi runtime loader/business/evaluator hoặc dependencies; chỉ thêm marker local_data cho hai ca vốn cần download BTC.

| Kiểm tra đã chạy mới | Kết quả / phạm vi |
|---|---|
| `python scripts/harness.py doctor` | Python/Git sẵn; cả 5 package khớp requirements pin |
| `python -m pytest tests/test_harness.py -q` | 44 passed; có RED -> GREEN cho guard, ngữ cảnh, force-track report và package initializer |
| `python scripts/harness.py check` | 301 passed, 2 local_data deselected; guard/link/budget/whitespace qua |
| `python -m pytest -q -rs` | 302 passed, 1 skip helper real-file evaluator cũ |
| Full trong checkout tạm không có train/public_test/cache/venv | 301 passed, 2 deselected, exit 0; dùng cùng interpreter đã cài dependencies |
| Data profile trong checkout không có dữ liệu | Exit 1, chỉ rõ rulebook/questions/answers/cache còn thiếu |
| `python scripts/harness.py check --profile data` tại workspace thật | Exit 0; local_data 1 passed, 1 skip cũ; verifier mới 409/409 khớp gold và legacy, errors=[]; chọn 417/3000, legacy bỏ 8 |

Một reviewer độc lập đã đọc spec/plan/code/docs, tái hiện lỗ hổng force-track report; các ca hồi quy đã được chạy thất bại trước khi sửa và qua sau sửa. Bổ sung import initializer để navigation phản ánh việc Python thực thi package. Full suite vẫn bắt buộc; graph không phải proof về mọi dependency.

Data profile được bắt đầu trước hai sửa guard/navigation cuối; full 301 và toàn bộ suite 302 bên trên là lượt sau hai sửa đó. Verifier hoàn tất trên cùng code nghiệp vụ/cache không đổi; không chạy lại phép đối chiếu đắt tiền vì các sửa cuối không chạm dữ liệu hoặc phép tính. Report mới nằm local tại `reports/harness/business_verification.json` và `.md`. Rulebook SHA256: `740267bccba29df70f745bc39968bbec5b3e62dada2c858c45314f3ec723d113`. Không rebuild cache trong tác vụ harness; 409 vẫn là tập chọn lọc chạm 3/10 API, không phải PA toàn train/NLU.

Workflow CI đã được tạo cho Ubuntu/Windows, Python 3.14, chỉ full/synthetic. Chưa chạy hosted CI hoặc kiểm chứng Linux trong tác vụ này. AST offline/gold guards là kiểm tra tĩnh hỗ trợ review, không phải sandbox hoặc chứng minh không leakage theo mọi cách. Không suy kết quả PA/NLU từ các test này. Xem [harness guide](harness-engineering.md).

## Baseline nghiệp vụ trước khi thêm harness

Đã áp dụng bản sửa sau review Gemini lượt 04 vào `business/sales.py`, chuyển các phản chứng thành 39 ca kiểm thử mới trong `tests/test_business_sales.py` và cập nhật tài liệu API.

Tiến độ khi kết thúc phiên và điểm tiếp tục: [PROGRESS.md](PROGRESS.md). Lượt tổng kết cuối phiên chỉ cập nhật tài liệu, không chạy lại test/verifier.

- `python -m pytest -q -rs`: **258 passed, 1 skipped**.
- `python verify_business.py --out reports/business_verification_applied04`: exit 0, **409/409 khớp gold và phép tính cũ, 0 lỗi**. Chọn 417 câu, legacy bỏ qua 8. Đây là lượt chạy mới trên code chính sau khi áp dụng patch.
- `git diff --check`: qua; code chính khớp đúng bản ứng viên đã kiểm chứng. Báo cáo từng câu chỉ lưu local trong `reports/`.
- Chi tiết thay đổi và phạm vi kiểm chứng: [CODEX_IMPLEMENTATION_04.md](../ai_collaboration/rounds/001_business_to_nlu/CODEX_IMPLEMENTATION_04.md).

Các kết quả trên được chạy trên code và test trước khi commit bản sửa; xem lịch sử nhánh để xác định commit áp dụng. Snapshot kiểm chứng trước khi thay đổi được giữ dưới đây.

## Trạng thái kiểm chứng ngày 2026-10-28

Đã chạy lại trên workspace Windows/Python 3.14.10 trước khi đưa bản thư viện nghiệp vụ và gói trao đổi Gemini lên nhánh `VuongNguyen`.

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q -rs` | 219 passed, 1 skipped |
| `python -m compileall -q business verify_business.py` | Exit 0 |
| `git diff --check` | Exit 0 |
| `python verify_business.py` | Exit 0, khớp gold 409/409 và phép tính cũ 409/409, 0 lỗi |

Verifier chọn 417 trong 3000 câu train; 8 câu bị bộ kiểm tra cũ bỏ qua, còn 409 câu đối chiếu được: 187 doanh thu tháng, 76 số đơn hủy, 130 số lượng, 8 ca sáng và 8 ca chiều. Đây là kiểm chứng hồi quy trên tập con, không phải PA toàn bộ train. Các API khác được kiểm thử bằng dữ liệu tổng hợp; không suy rộng kết quả 409/409 cho toàn bộ agent.

Test bỏ qua là `evaluate/test_evaluate.py::test_self_score_real_file`: helper hiện tìm gold dưới `evaluate/`, không tìm `train/answers.jsonl` ở gốc repo. Dữ liệu train thực tế đã có tại local. Chưa sửa evaluator trong phạm vi triển khai này.

Lượt loader đã chạy trước đó trên 44 doanh nghiệp: 0 crash, 236 PASS, 116 kiểm tra bỏ qua, 0 FAIL. Không chạy lại loader trong lượt chuẩn bị GitHub này vì không sửa loader hoặc dữ liệu.

Chi tiết đối chiếu từng câu và báo cáo loader ở `reports/business_verification.*`, `reports/gold_before_business.md`, `load_report.md` tại local, được Git ignore. File này chỉ ghi số liệu tổng hợp để người đọc GitHub thấy bằng chứng và giới hạn kiểm chứng.
