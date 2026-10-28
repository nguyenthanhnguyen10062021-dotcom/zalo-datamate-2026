# QueryPlan v1 Implementation Plan

> **For agentic workers:** dùng superpowers:executing-plans để thực hiện từng task, kiểm thử RED → GREEN và review toàn bộ cuối lượt.

**Goal:** thực thi QueryPlan JSON tất định trên 10 API bán hàng hiện hành.

**Architecture:** `queryplan/contract.py` kiểm tra plan; `resolution.py` tra thời gian/tên/đơn vị; `executor.py` kiểm tra capability, gọi public API và phân loại kết quả. `business/` không đổi.

**Tech Stack:** Python trong `.venv`, stdlib, pandas hiện có, pytest.

**Spec:** [thiết kế](../specs/2026-10-29-queryplan-v1.md).

## Global Constraints

- Không thêm dependency, network, gold hoặc logic theo ID.
- Giữ nguyên API/ngữ nghĩa business; không sửa dữ liệu BTC hoặc file review có sẵn.
- Theo AGENTS làm từ repository root, dùng môi trường hiện có, không auto-commit/push. Người dùng đã duyệt triển khai; không thêm vòng xin duyệt thiết kế/worktree. Thực thi inline.

## Review Focus

- Nhãn chuẩn hóa trùng và tên hàng nhiều mã: không tự chọn hoặc gộp sai.
- Dữ liệu hỏng ở nhánh không liên quan: không làm mất dependency-scoped validation.
- Nhãn chỉ có trên bản ghi tương lai: không dùng để trả 0 giả.
- Ngày thật, Tet/calendar lỗi và same_elapsed: giữ đúng thời điểm/rulebook caller.
- Unexpected exception và Answer sai type: không bị che thành abstain/unanswerable.

## Task 1: Contract + normalization

Files: tạo `queryplan/contract.py`, `queryplan/__init__.py`, `tests/test_queryplan_contract.py`.

Interfaces: `validate_plan(raw: dict) -> dict`, `PlanValidationError(stage, message)`, constants mô tả operation/period/filter fields. Bản trả về độc lập input.

- [x] Viết tests key bắt buộc/lạ, null, number normalization, ngày sai, unsupported envelope, type/ranking/filter/period semantics.
- [x] Chạy `.\.venv\Scripts\python.exe -m pytest tests/test_queryplan_contract.py -q`; RED do package chưa có (collection ModuleNotFoundError).
- [x] Viết validator theo spec, chạy lại 49 PASS. Một lỗi fixture (unhashable operation) được sửa ở test, không phải lỗi runtime.

## Task 2: Resolver + executor

Files: tạo `queryplan/resolution.py`, `queryplan/executor.py`, `tests/test_queryplan_executor.py`; xuất API trong `queryplan/__init__.py`.

Interfaces: `QueryExecutor(tables, rules, as_of_date, calendar_path=None).execute(raw_plan) -> ExecutionResult`; `ExecutionResult.answer,status,stage`; resolver trả Filters và unit tường minh. Tiêu thụ `validate_plan` của task 1 và API business.

- [x] Viết fixture tổng hợp và tests 10 API với expected literals + đối chiếu API; errors, ambiguity, missing info, period/calendar, immutability, dependency-scope, unexpected exception.
- [x] Chạy tests mới RED: fixture khẳng định QueryExecutor chưa có; triển khai rồi chạy cả contract/executor 100 PASS.

## Task 3: Guard + tài liệu + kiểm chứng

Files: sửa `scripts/harness.py`, `tests/test_harness.py`, docs kiến trúc/API/map/progress/validation/context index và DECISIONS; thêm `docs/queryplan.md`, `queryplan/AGENTS.md`.

Interfaces: mở guard AST hiện có cho runtime `queryplan`, cấm import ngược từ loader/business vào queryplan, cấm gold/network/dev imports tại queryplan.

- [x] Thêm test guard RED (2 phản chứng đầu) → sửa guard GREEN; targeted queryplan + harness 152 PASS.
- [x] Cập nhật hướng dẫn gọi API, contract/status/giới hạn và trạng thái project.
- [x] Chạy targeted, harness full, data; review diff và một fresh reviewer theo executing-plans. Không commit/push.

## Execution record

- Nền: `6dc41d7`, nhánh `VuongNguyen`; có sẵn file untracked CODEX_ARCHITECTURE_REVIEW_2026-10-29.md, giữ nguyên.
- Baseline đã chạy trong phiên: full 301 passed, 2 local_data deselected; doctor đạt, local data ready.
- Context đã chạy cho harness/tests và các file queryplan mới: file mới chưa index (đúng kỳ vọng); source business/periods và sales đã đọc.
- Pre-flight: task 2 dùng dict độc lập + PlanValidationError của task 1; task 3 chỉ mở guard và tài liệu, không đổi kết quả business. Không có xung đột interface.
- Task 1: complete — contract 49 passed; Task 2: complete — queryplan tổng 100 passed. Không commit theo AGENTS.
- Ruling: dùng validator Python nghiêm ngặt, chưa thêm JSON Schema — không thêm dependency hoặc tự xây framework schema; nếu tích hợp constrained decoding sẽ cần schema + test tương đương.
- Ruling: capability được kiểm tra trước resolve — tránh query ngoài v1 bị nhầm thành dữ liệu thiếu; business tiếp tục kiểm tra dữ liệu/rule theo dependency khi dispatch.
- Full trước review: 409 passed, 2 local_data deselected, fast/full exit 0.
- Final review độc lập: không Critical/Minor; có 2 Important: catch period quá rộng nuốt implementation exception, calendar thiếu ô gây AttributeError. Đã tái hiện 3 FAIL (KeyError/ValueError bị nuốt, missing lunar_leap) trước sửa.
- Final fixed: dùng PeriodResolutionError từ adapter calendar và kiểm tra date bounds có chứng cứ; bỏ catch chung quanh Periods. Queryplan sau sửa: **115 passed**; full sau sửa: **424 passed, 2 local_data deselected**, exit 0. Thêm 15 ca period/calendar, không đổi business.
- Final Ruling (review scope): không suy NLU/coverage/PA, không coi AST guard là sandbox dynamic imports; reviewer không đọc BTC/gold hoặc chạy data. Main chịu trách nhiệm full/data và doc diff; file review có sẵn được giữ nguyên. Không phát hiện minor cần hoãn.
- Bare pytest sau sửa: **425 passed, 1 skipped** (helper evaluator real-file cũ tìm sai vị trí answers.jsonl).
- Data profile exit 0: local_data **1 passed, 1 skipped**; selected **417/3000**, legacy skip **8**, compared/matched_gold/matched_legacy **409/409**, errors=[]; reports/harness/business_verification.{json,md} local ignored. Data khởi chạy trước 15 ca period/calendar cuối, hoàn tất sau đó; verifier chỉ gọi business/cache không đổi nên không đo executor/NLU. Full 424 và bare 425 đã kiểm tra code queryplan cuối.
- Task 3: complete. Review toàn bộ tracked diff và source file mới; AST/doc links/instruction budget/whitespace qua. Không thêm dependency, không sửa business/loader/evaluator, không sửa file review có sẵn, không commit/push.
- Trạng thái: complete; next action: inventory capability và verifier mở rộng không phụ thuộc legacy, sau đó NLU offline và runner tối thiểu. Chưa có kết quả PA/coverage của executor/NLU hoặc hosted CI/Linux cho thay đổi này.

## Xác nhận tiếp cùng tác vụ — 2026-10-29

- Khi tiếp tục, spec/plan/source/tests cùng các cập nhật tài liệu đã có trong working tree; giữ nguyên phần đã hoàn thành, không dựng lại. Đã đọc lại contract/source và chạy map/context, doctor (dependencies đạt, data ready).
- Review độc lập mới: một Important tại `_labels`, unique trên list/dict làm TypeError thay vì data_error theo contract. Không có Critical hoặc minor cần hoãn; không đọc BTC/gold/public test ở reviewer.
- Final: fixed nhãn sai kiểu — `test_non_string_labels_are_data_errors_when_resolved` có 6 ca RED (unhashable list/dict) → GREEN trên kênh/tên hàng/đơn vị; chuyển kiểm tra kiểu trước unique, không thêm catch chung. Các ca đồng thời giữ order_count không bị chặn bởi nhãn không liên quan.
- Targeted queryplan **121 passed**; harness full **430 passed, 2 deselected**, exit 0; bare pytest **431 passed, 1 skipped** (helper evaluator cũ). Không sửa business/loader/evaluator/requirements.
- Smoke JSON roundtrip tổng hợp và serialization Answer.to_submission đạt (revenue 90). Script shell dùng Unicode escapes để tránh PowerShell pipe làm mất dấu trước khi Python nhận input.
- Data profile mới hoàn tất exit 0: full 424/2 deselected và local_data 1 passed/1 skipped chạy trước sáu ca nhãn mới; verifier business chọn 417/3000, legacy bỏ 8, compared/matched_gold/matched_legacy 409/409, errors=[]. Report local ignored reports/harness/business_verification.{json,md}. Full/bare sau sửa ở trên kiểm chứng source QueryPlan cuối; business/cache không đổi, verifier không gọi QueryPlan.
- Kết luận xác nhận tiếp: complete; giữ nguyên bước kế tiếp inventory capability/verifier mở rộng. Không commit/push, không thêm LLM hoặc thay nghiệp vụ.
