# Quyết định và vấn đề còn mở

Tài liệu này ghi trạng thái thực tế. Đề xuất của một AI không tự trở thành quyết định của người dùng. Phản hồi Gemini vòng 001 đã được người dùng lưu; Codex kiểm chứng ngày 2026-10-29.

## Nền tảng đã có trước vòng 001

| ID | Nội dung | Trạng thái và căn cứ |
|---|---|---|
| D001 | Tách loader, thư viện nghiệp vụ và tầng hiểu câu hỏi | Loader, `business/` và QueryPlan executor v1 đã triển khai; model hiểu câu hỏi chưa triển khai |
| D002 | Truyền rulebook đúng split và as_of_date vào phép tính | Đã có API và test; parser rulebook có phạm vi hỗ trợ giới hạn |
| D003 | Không tự coi DataError/UnsupportedRule là bằng chứng câu hỏi unanswerable | Đã thể hiện bằng API/test và tài liệu business |
| D004 | Gemini web tham gia review phát triển, người dùng chuyển tiếp qua file | Người dùng yêu cầu; chưa có tích hợp API hoặc đồng bộ tự động |
| D005 | Codex chủ động kiểm chứng và trao đổi kỹ thuật với Gemini, không chờ người dùng duyệt từng bước | Người dùng ủy quyền trực tiếp ngày 2026-10-29; đọc phản hồi, chạy test/probe, phản biện và chuẩn bị lượt tiếp theo. Ghi rõ đề xuất và phần đã thực thi. |

## Đang thảo luận

| ID | Vấn đề | Trạng thái | Nơi trao đổi |
|---|---|---|---|
| O001 | Contract và kiến trúc NLU → phép tính; độ sẵn sàng của API hiện tại | QueryExecutor v1 đã có trong working tree, gọi 10 API; model NLU chưa triển khai | [Contract executor](../docs/queryplan.md) |
| O002 | Thứ tự mở rộng hệ thống | Đã có inventory/verifier độc lập; tiếp theo audit plan/unsupported buckets và mở coverage độc lập gold, rồi NLU offline/runner; chưa mở rộng kho/nợ/lãi | [Capability verification](../docs/capability-verification.md) |
| O003 | Model inference offline và môi trường chạy | Chưa chọn; chưa yêu cầu quyết định trong vòng 001 | Thảo luận sau khi rõ phạm vi và ngân sách |

## Kết luận review ngày 2026-10-29

Các dòng dưới là kết luận kỹ thuật của Codex, không phải ghi nhận đã sửa code hoặc người dùng đã chốt kiến trúc.

| ID | Kết luận | Căn cứ/trạng thái |
|---|---|---|
| R001 | Không đổi kỳ so sánh giao một phần thành unanswerable chỉ vì thiếu đầu kỳ | §7 train/public quy định tính phần có dữ liệu; đã chạy probe tổng hợp, chưa chấm gold biên |
| R002 | Filters của cancellation_rate/top_customers và denominator của revenue_share cần làm rõ trước dispatch NLU | Đã tái hiện TypeError và phụ thuộc luật sai phạm vi; chưa sửa production |
| R003 | Chưa coi phản chứng khóa khách hash của Gemini là lỗi cache hiện hành | Loader dùng nk(tên), 19 doanh nghiệp không mã khách không có dòng lệch hợp đồng; vẫn cần định nghĩa tie-break rõ hơn |
| R004 | Validation chỉ được nới khi chứng minh dòng lỗi không ảnh hưởng kết quả | Status ở kênh đã loại có thể xử lý cục bộ; ngày mất/dòng hàng mất chưa đủ bằng chứng để bỏ |
| R005 | Cần contract resolver để tách nhãn không tìm thấy khỏi dữ liệu không có thông tin | Unknown ID, unknown group/channel đang có hành vi khác; chưa chốt chính sách 0/unanswerable cho mọi trường hợp |

Chi tiết và câu hỏi gửi lại Gemini: `rounds/001_business_to_nlu/CODEX_REVIEW.md`, `CODEX_REPLY_TO_GEMINI.md`. Các thay đổi mới trong lượt review chưa được commit/push.

## Kiểm chứng phản hồi 02 ngày 2026-10-29

Chi tiết ở [CODEX_REVIEW_02.md](rounds/001_business_to_nlu/CODEX_REVIEW_02.md), thư tiếp theo ở [CODEX_REPLY_TO_GEMINI_02.md](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI_02.md).

- Gemini đã rút đề xuất đổi kỳ cơ sở giao một phần thành unanswerable và điều chỉnh nhận định khóa khách/validation.
- Chấp nhận hướng QueryPlan tối thiểu làm baseline kỹ thuật; schema và API mới chưa triển khai. Chốt capability/filter/period policy trước khi mở rộng.
- Không chấp nhận bỏ dòng mồ côi chỉ vì không nối được với đơn trong kỳ: probe cho hai kết quả hợp lệ 201/251 tùy nguồn liên kết còn thiếu.
- Cần contract precision và numerator/denominator rõ hơn; chưa thêm raw_decimal hoặc denominator_filters vào production.
- Kiểm chứng chia doanh nghiệp và group-disjoint là hai mục tiêu khác nhau; số liệu quét gold chưa đủ chốt entity-not-found hay top-k rỗng trong kỳ có dữ liệu.

## Kiểm chứng phản hồi 03 ngày 2026-10-29

Chi tiết ở [CODEX_REVIEW_03.md](rounds/001_business_to_nlu/CODEX_REVIEW_03.md), thư tiếp theo ở [CODEX_REPLY_TO_GEMINI_03.md](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI_03.md).

- Thống nhất v1 dùng public API trực tiếp, hoãn boolean/raw_decimal/parent-share; giữ share trên cả shop. Validation theo dependency nhưng không bỏ ORPHAN khi metric cần dòng hàng.
- Hai API cancellation_rate/top_customers cần patch order filters trước khi dùng bảng dispatch mới. V1 reject product filter cho cả hai API; chưa có patch production.
- Tách structural validator khỏi semantic validator/resolver. Chuẩn hóa số nguyên toán học hữu hạn trước dispatch, bool không được coi là int; parse ngày thật; [] thành null và reject mention rỗng. Đây là contract triển khai, chưa phải tính năng đã có.
- URI schema phải thuần; bỏ bảo đảm precision tuyệt đối chỉ dựa prec=28. Giữ nguyên bản phản hồi Gemini để truy vết.
- Đã chạy 19 trường hợp schema, 3 test dependency đích và 2 phản chứng chữ ký API; full suite 219 passed, 1 skipped. Không chạy lại verifier 409 khi code không đổi.

## Kiểm chứng phản hồi 04 ngày 2026-10-29

Chi tiết ở [CODEX_REVIEW_04.md](rounds/001_business_to_nlu/CODEX_REVIEW_04.md), artifact là [CODEX_BUSINESS_PATCH_04.diff](rounds/001_business_to_nlu/CODEX_BUSINESS_PATCH_04.diff). Production chưa thay đổi.

- Không áp dụng nguyên patch Gemini: thiếu import UnsupportedRule, và dời loại hủy/trả quá muộn gây ba regression trên doanh thu có filter.
- Với metric chỉ tính đơn hợp lệ, loại hủy/trả đã biết trước filter; giữ trạng thái chưa biết để kiểm tra sau filter. Với tỷ lệ hủy/đếm hủy, vẫn giữ mọi trạng thái cần thiết. Bản ứng viên Codex qua sáu test Gemini và giữ đúng ba phản chứng mới.
- Full suite trên baseline và ứng viên đều 219 passed, 1 skipped. Verifier chạy mới trên ứng viên đạt 409/409 khớp gold và phép tính cũ, 0 lỗi. Giữ tách biệt trạng thái ứng viên thử nghiệm và source đã áp dụng.
- Resolver cần output unit tường minh và policy ambiguity nhiều mã. `$schema` vẫn cần URI thuần; helper/schema chưa thành pipeline end-to-end.
- Khi câu hỏi không nói khác, tháng này so tháng trước dùng same_elapsed theo rulebook; không tự gọi là ambiguous chỉ vì câu hỏi không nhắc lại mặc định.

## Áp dụng patch nghiệp vụ sau lượt 04

Người dùng yêu cầu trực tiếp đưa bản sửa đã kiểm chứng vào code chính, chuyển phản chứng thành test và chạy lại kiểm tra. Đã áp dụng `CODEX_BUSINESS_PATCH_04.diff` vào `business/sales.py`, thêm 39 ca kiểm thử trong repo; full suite 258 passed, 1 skipped. Verifier chạy mới trên code chính đạt 409/409 khớp gold và phép tính cũ, 0 lỗi. Code và test đã commit tại `c567b29`; chi tiết ở [CODEX_IMPLEMENTATION_04.md](rounds/001_business_to_nlu/CODEX_IMPLEMENTATION_04.md). Các nhận định “chưa sửa production” trong review trước là trạng thái lịch sử.

## Bàn giao cuối phiên 2026-10-29

Code/test đã đẩy tại `c567b29`; hồ sơ trao đổi đã đẩy tại `211e492` trên nhánh `VuongNguyen`. Dừng phiên sau khi hoàn tất cập nhật tài liệu; không triển khai thêm executor trong lượt tổng kết. Tiến độ, giới hạn kiểm chứng, vấn đề còn mở và thứ tự tiếp tục nằm ở [docs/PROGRESS.md](../docs/PROGRESS.md).

## E001 — Triển khai QueryPlan executor v1 (2026-10-29)

- Người dùng duyệt trực tiếp đề xuất executor JSON → 10 API, validator/resolver/capability và test tổng hợp. Codex chọn package `queryplan/` và validator Python không thêm dependency; không đổi API business.
- Resolver dùng khớp NFC/casefold/khoảng trắng có dấu; nhiều mã cùng tên hoặc nhãn raw trùng sau normalize gây ambiguous. Thiếu loại thông tin có bằng chứng là unanswerable; unknown mention là unresolved/abstain. Không fuzzy hoặc logic theo ID.
- ExecutionResult giữ Answer/status/stage; không tự ghi log, không nuốt lỗi implementation. Growth this_month mặc định so cùng số ngày tháng trước theo rulebook; share giữ mẫu số cả shop.
- Chưa cung cấp JSON Schema constrained decoding, model, verifier mở rộng hoặc runner. Hồ sơ/bằng chứng: [plan executor](../docs/superpowers/plans/2026-10-29-queryplan-v1.md), [validation](../docs/validation.md). Schema/helper ở các phản hồi cũ vẫn là snapshot.

## E002 — Frozen capability inventory / verifier độc lập (2026-10-29)

- Người dùng yêu cầu thực hiện bước kế tiếp sau executor. Codex chọn hai CLI dev-only: inventory tạo manifest toàn corpus bằng grammar chỉ nhận nội dung câu, verifier replay manifest qua QueryExecutor rồi mới đọc gold và gọi evaluator local. Không mở nghiệp vụ kho/nợ, không thêm model/dependency, không dùng legacy gate.
- Manifest có fingerprints/version/entry cho mọi câu; từ chối stale/missing/duplicate/modified payload. Giữ total/selected/outside_selection và selected=compared+abstained+execution_errors. Reference thiếu/trùng/lạ hoặc format lỗi làm từ chối chấm. File từng câu chỉ ở reports ignored.
- Grammar có fixture cho 10 API, train hiện chỉ chọn 126/3000 chạm 7 API. Revision v2 chấm 125 khớp/125 compared, 1 unresolved quantity vẫn nằm trong selected, 0 mismatch/execution error; exit 1 có chủ ý. Không cộng với 409 legacy khi chưa đo giao/khác.
- Review tổng hợp độc lập tìm mất dấu unit và scope filter hai vế so sánh; đã sửa RED→GREEN. Giữ nguyên manifest/report v1; v2 là revision sửa lỗi có fingerprint mới, không loại câu theo gold. Không mở rộng grammar theo các câu train sai/đúng trong lượt này.
- Chưa có gold plans audit thủ công, group-disjoint/fold artifacts, holdout mới hoặc PA model. [Contract/lệnh](../docs/capability-verification.md), [execution record](../docs/superpowers/plans/2026-10-29-capability-verifier.md).

## E003 — Audit annotation trước mở grammar (2026-10-29)

- Người dùng giao audit unit unresolved và bucket chưa parse, ghi annotation độc lập gold trước mở grammar. Chốt mẫu deterministic tối đa 10/reason, luân phiên doanh nghiệp; 40 mẫu + 1 unit case, artifacts chỉ reports ignored. Không mở answers/report gold từng câu trong audit; có prior aggregate exposure, không gọi blind holdout.
- Unit case là intent tiền/doanh thu sai thành quantity, rulebook §1 rõ; không sửa catalog/alias. Đã ghi plan revenue giữ kỳ/ca, chưa áp dụng grammar. 40 unparsed samples có 22 plan đề xuất, 14 thiếu capability, 4 domain khác; không ngoại suy population.
- Các annotation là AI-reviewed, chưa human/independent adjudication hoặc gold plan chuẩn. Freeze packet/annotations+digests trước mở grammar; validator kiểm integrity/schema, không chứng minh semantics đúng. [Audit và giới hạn](../docs/plan-annotation-audit.md), [task/evidence](../docs/tasks/2026-10-29-plan-annotation-audit.md).
- Bước kế tiếp sửa intent tiền bằng synthetic tests rồi mở họ grammar ngôn ngữ và comparison neo kỳ. Hai Filters/scalar/domain mới cần contract riêng; không ép vào v1 hoặc loại câu theo gold. Không đổi source grammar/runtime/manifest hoặc chạy chấm trong lượt này.

## Review Argon vòng002 — nhận phản hồi, chưa áp dụng sửa (2026-10-29)

- Người dùng đính chính bản cũ là Flash, bản mới là Argon/đối tượng phản biện chính. Giữ nguyên hai file; attribution theo người dùng dù header bản mới tự ghi Flash. Xem [routing và provenance](rounds/002_capability_readiness/README.md).
- [Codex review Argon](rounds/002_capability_readiness/CODEX_ARGON_REVIEW_01.md) chấp nhận bug intent và neo kỳ ở selector, tái hiện thêm va chạm dấu unit; giữ phân biệt schema/capability và helper-direct/executor. Direct API robustness và table scorer là giới hạn riêng, không tự thành blocker tất cả v1. Chưa áp patch hoặc thêm primitive vào contract.
- Kế hoạch split34/10 trên44 train của Argon không hợp lệ với30 train; business-disjoint khác file-family-disjoint, không gọi split hồi cứu là blind và không đưa public test vào tuning. Gate10/10API/30dòngregex không tự bảo đảm correctness.
- Thư tiếp theo cho **Argon** ở CODEX_REPLY_TO_ARGON_01.md; không dùng thư yêu cầu phần thiếu của Flash. Chưa gửi tự động, chưa có phản hồi02.

## Review Argon vòng002/lượt02 — đồng thuận kỹ thuật, chưa triển khai (2026-10-29)

- Đã nhận và lưu nguyên response02,31250bytes. Argon rút I2 là bug Important, hạ I4 không chặn, chỉnh dataset/split/bucket/hash claims. [Review Codex02](rounds/002_capability_readiness/CODEX_ARGON_REVIEW_02.md) ghi nhận đủ căn cứ chuẩn bị task intent/span/preflight trước, spec neo kỳ sau. Đây là kết luận review, không ghi người dùng đã duyệt primitive/patch.
- Không áp blanket guard fixed-period vs as_of-relative trong I3-A: probe date_range2026-03-01 so yesterday (as_of2026-03-04) là plan hợp lệ hiện có nhưng guard sẽ reject. Chỉ ràng buộc main-kind cho comparison kinds mới khi có spec; giữ semantics cũ.
- Chưa sửa runtime/selector/manifest/annotations.18 targeted tests mới đạt, fast qua, không gold/cache/public-test hay commit/push. “Ready” chỉ đủ cho dev/baseline trong phạm vi review, không chứng nhận không còn lỗi. Chưa cần thêm vòng phản biện cho Task1 nếu không có phản chứng mới.

## E004 — Triển khai sau Argon theo ủy quyền người dùng (2026-10-29)

- Người dùng giao “triển khai tiếp theo thứ tự bạn thấy hợp lí”. Chốt [task contract/acceptance](../docs/tasks/2026-10-29-selector-calendar-implementation.md) trước code: intent/span và preflight trước, calendar comparison/grammar có giới hạn sau. Không LLM, domain mới, dependency, business/evaluator patch hoặc commit/push trong tác vụ này.
- Public check_capability giữ riêng schema/capability, không data/mutation. Receipt preflight mới không sửa41 annotation hoặc chứng nhận semantics. Optional filter resolution do caller kiểm riêng, không answer/scorer;23 plan capability supported,4 cần nhãn resolve được.
- Plan1.0 thêm comparison-only previous_calendar_month/quarter với main-kind tương ứng; resolve năm kỳ chính trước, lùi trọn kỳ lịch. Giữ old previous_month theo as_of, same_elapsed và fixed-vs-relative hợp lệ. Validator cũ reject new kinds an toàn; phải xem versioning lại khi phát hành consumer/schema/model.
- Intent tiền/đơn và unit span bảo toàn NFC/casefold; grammar chỉ thêm các họ audit với synthetic contrasts, không ID/catalog/gold trong selector. Hai filter scopes/scalar/domain mới vẫn unsupported. Không chỉnh grammar sau khi thấy scoring v3/v4.
- Full545/bare546 đạt, skip helper cũ;58 tests mới đạt. V4 selected/compared/matched396/3000,0mismatch/abstain/execution_errors,8operation; top_customers/share synthetic-only. Baseline riêng409/409; giao143/hợp662, không cộng mẫu số hoặc suy PA toàn train/model. Review cuối do chính agent triển khai; chưa độc lập/human adjudication, holdout mới hoặc hosted CI/Linux. [Validation](../docs/validation.md).

## Mẫu ghi quyết định mới

- ID và ngày:
- Vấn đề/vòng thảo luận:
- Đề xuất của Codex:
- Ý kiến Gemini hoặc LLM khác:
- Bằng chứng đã kiểm tra và giới hạn:
- Quyết định, ai quyết định, phạm vi được giao:
- Lý do và đánh đổi:
- File thay đổi/test đã chạy nếu có:
- Điều kiện cần xem lại:
