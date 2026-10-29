# Capability inventory and independent verifier Implementation Plan

> **For agentic workers:** dùng superpowers:executing-plans, thực thi inline và review độc lập cuối lượt. Không commit/push trong tác vụ này.

**Goal:** đóng băng capability manifest độc lập gold/legacy rồi kiểm chứng QueryExecutor trên train local.

**Architecture:** dev-only verification/selection.py tạo plan bảo thủ; verification/manifest.py kiểm tra corpus/fingerprint; verification/runner.py đọc cache, thực thi và chấm. Hai CLI root tách build inventory khỏi replay/score. Giữ verifier legacy riêng.

**Tech Stack:** Python .venv, stdlib/pandas/pytest hiện có, evaluator local hiện hành.

**Spec:** [contract/acceptance](../specs/2026-10-29-capability-verifier.md).

## Global Constraints

- Không gold/result/ID trong selector; không legacy gate; không tuning public test.
- Không sửa runtime semantics/dependencies; dữ liệu từng câu và output chỉ ở reports ignored.
- Đánh giá hồi cứu, không gọi kết quả PA model hoặc holdout mới. Không commit/push tự động.

## Review Focus

- Câu nhiều metric hoặc qualifier lạ không bị parse mất scope.
- Corpus/manifest thiếu/trùng/stale không làm co mẫu số.
- Mismatch/resolve/data/implementation error không biến thành skip hoặc unanswerable.
- List alias/order và serialization dùng evaluator thật, không comparator tự viết lại.
- Toàn bộ cache lớn không giữ trong RAM cùng lúc; file input/manifest không bị ghi đè bởi output.

## Task 1 — Selector và frozen manifest

Files: verification/{__init__,selection,manifest}.py, inventory_capabilities.py, tests/test_capability_inventory.py.

Interfaces: `select_question(text) -> dict` với selection/reason/plan; `build_manifest(questions_path, rulebook_path) -> dict`; `validate_manifest(manifest, questions_path, rulebook_path) -> list[dict]`; CLI ghi manifest và summary.

- [x] Tests RED: 10 operation dạng chuẩn, mention/filter/period, qualifier lạ, không có gold/cache, deterministic, fingerprint và corpus integrity.
- [x] Implement selector/manifest/CLI tối thiểu và chạy GREEN.

## Task 2 — Independent execution/scoring

Files: verification/runner.py, verify_queryplans.py, tests/test_queryplan_verification.py.

Interfaces: `verify_manifest(manifest_path, train_dir, cache_dir) -> dict`; report rows + summary, exit status kiểm tra được; reader cache độc lập legacy; dùng scorer local qua importlib vì evaluator cũng được pytest import như top-level module.

- [x] Tests RED: 10 operation plan, score list/order/alias, missing/duplicate gold, selected errors/abstains, stale manifest, cache và implementation failures; không import legacy.
- [x] Implement và chạy targeted GREEN; smoke hai CLI trên synthetic corpus.

## Task 3 — Guard, documentation, local evidence

Files: scripts/harness.py, tests/test_harness.py, verification/AGENTS.md, docs/capability-verification.md, README/docs map/progress/validation/context index/DECISIONS.

- [x] Guard RED→GREEN chặn dev package/CLI import vào runtime.
- [x] Full và bare pytest; build frozen train manifest trước đọc gold; verify train và lưu cả mismatch/error vào reports local; chạy data profile baseline riêng.
- [x] Fresh review độc lập theo requesting-code-review; sửa Important bằng regression RED→GREEN; review diff và cập nhật số liệu thực đo/giới hạn/next action trong hồ sơ này và PROGRESS.

## Execution record

- Nền: 4fd268e, nhánh VuongNguyen, working tree sạch (git warning .pytest_tmp permission, không chỉnh/xóa thư mục đó).
- Pre-flight: Task 2 tiêu thụ validated manifest/plan từ Task 1, Task 3 chỉ guard và docs; không thay public API executor/business. Ruling: selector là grammar dev bảo thủ, không NLU production; mọi kết quả chọn ghi trước chấm, không chỉnh grammar theo mismatches train.
- Task 1: 30 test synthetic ban đầu, RED package chưa tồn tại → GREEN. Task 2: 11 test ban đầu RED module chưa tồn tại → GREEN. Guard: 3 test imports dev mới RED→GREEN. Không sửa verify_business hoặc runtime.
- Ruling: không đặt quota 1000–1500; grammar bảo thủ chốt bằng test trước chấm train, báo bucket chưa parse. Manifest builder không nhận cache/gold; runner đọc gold sau khi có predictions. Chi phí: nhiều cách diễn đạt hợp lệ vẫn chưa được chọn, không suy capability doanh nghiệp từ số selected.
- Đóng băng manifest_v1 trước gold; selected 126/3000, chạm 7 API; verifier_v1 exit 1, matched/compared 125, mismatch 0, abstained 1, execution_errors 0. Không dùng kết quả để mở grammar hoặc bỏ câu.
- Fresh reviewer không đọc BTC/gold/cache/reports; tìm 2 Important, không Critical: mất dấu unit và gộp filter ở vế comparison sang cả hai kỳ. Ba ca synthetic tái hiện RED (sau sửa thiếu import fixture ở lần đầu), sửa `_fold`-unit bằng bảo toàn nhãn và split comparison trước extract filter → GREEN. Không sửa ngữ nghĩa business. Tên test unanswerable được chỉnh cho đúng phạm vi; thêm test data_error giữ selected.
- Ruling: giữ nguyên v1 và tạo manifest_v2 do bugfix từ review synthetic, không phải tuning theo gold. Fingerprint selector thay đổi; v1 bị từ chối replay âm thầm trên source mới. v2 vẫn chọn 126, chưa chọn 2874; reason buckets có thay đổi do giữ filter vế comparison thay vì gộp.
- verifier_v2 exit **1**: matched/compared **125**, mismatch **0**, abstained **1** (quantity/unresolved_entity), execution_errors **0**. Giữ mẫu số selected=126; không chuyển câu này thành skip/0/unanswerable. Nguồn local: reports/capability_inventory/manifest_v{1,2}.json và verification_v{1,2}.{json,md}.
- Targeted cuối **100 passed**; full cuối **478 passed, 2 local_data deselected**, exit 0; bare pytest **479 passed, 1 skipped** (helper evaluator cũ). Smoke hai CLI synthetic: selected 11, matched 9, mismatch 1, abstained 1, exit 1 đúng thiết kế. Không giữ/nhúng BTC rows vào tracked files.
- Data baseline riêng exit 0: full của lượt data **474 passed, 2 deselected** trước 4 ca cuối; local_data **1 passed, 1 skipped**; selected **417/3000**, legacy skip **8**, compared/matched_gold/matched_legacy **409/409**, errors=[]. Full/bare cuối kiểm tra source mới; business/cache không đổi. Không đo giao hoặc cộng mẫu số với manifest mới.
- Không có minor cần hoãn từ reviewer. Chưa có hosted CI/Linux, audit gold plans, group-disjoint/fold artifacts hoặc PA model/NLU. Chưa thêm dependency, không public-test fitting, không commit/push.
- Trạng thái: complete; next action: audit plans và unsupported buckets theo frozen manifest, ghi provenance annotation độc lập gold trước khi mở grammar; sau đó baseline model offline. Một unresolved quantity vẫn cần audit riêng, không coi là lỗi đã sửa.
