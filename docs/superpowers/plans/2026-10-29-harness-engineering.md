# Harness Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agent có ngữ cảnh đúng, lệnh kiểm chứng thống nhất và kiểm tra ranh giới chạy được ở local/CI.

**Architecture:** Hướng dẫn ngắn trỏ tới tài liệu hiện hành; một CLI stdlib dùng chung cho người và agent. Tách test tổng hợp khỏi kiểm chứng cần dữ liệu BTC; giữ nguyên runtime nghiệp vụ.

**Tech Stack:** Python >=3.10, Git, pytest hiện có, GitHub Actions Python 3.14.

**Spec:** [Thiết kế](../specs/2026-10-29-harness-engineering-design.md).

## Global Constraints

- Không thay production dependency hoặc code tính toán nghiệp vụ/evaluator.
- Không tải/track/đưa dữ liệu BTC hoặc môi trường vào Git/CI.
- Root AGENTS <=6000 bytes, scoped AGENTS <=3000 bytes.
- Profile full không cần dữ liệu BTC; profile data phải từ chối báo cáo rỗng.
- Làm tại workspace người dùng giao trên nhánh VuongNguyen; giữ diff để review, không tự commit/push.

## Review Focus

- File BTC đã bị git add -f vẫn phải bị phát hiện dù .gitignore chặn file mới.
- Import tuyệt đối, tương đối, nhiều alias và gold filename nhúng trong path đều phải bị kiểm tra.
- Checkout không có dataset vẫn chạy full; thiếu input của data phải báo rõ trước khi chạy.
- Link UTF-8/đường dẫn có khoảng trắng và link ngoài không gây false positive.
- Verifier exit 0 nhưng compared=0 hoặc matched_gold thiếu vẫn phải fail.

### Task 1: Ngữ cảnh và quy trình

**Files:** AGENTS.md; loader/AGENTS.md; business/AGENTS.md; evaluate/AGENTS.md; ai_collaboration/AGENTS.md; docs/README.md; docs/architecture.md; docs/harness-engineering.md; docs/tasks/TEMPLATE.md; README.md.

**Interfaces:** CLI được tài liệu hóa là `python scripts/harness.py doctor` và `python scripts/harness.py check --profile fast|full|data`.

- [x] Viết bản đồ, ranh giới, workflow và tổng hợp nguồn chính đã đọc.
- [x] Giữ trạng thái ở PROGRESS; giữ snapshot lịch sử nguyên vẹn.
- [x] Kiểm tra link tài liệu bằng CLI ở task 2 và review nội dung.

### Task 2: Guard và lệnh kiểm chứng

**Files:** scripts/harness.py; tests/test_harness.py; pytest.ini; marker trong tests/test_parsers.py và evaluate/test_evaluate.py.

**Interfaces:** `check_source(path: str, source: str) -> list[str]`, `check_paths(root: Path, paths: list[str]) -> list[str]`, `validate_verification(result: dict) -> list[str]`; CLI exit 0/1.

**Steering Trail-Code:** thêm `build_code_map(root, paths) -> dict`, `file_context(graph, name, limit) -> dict`, `related_knowledge(root, name) -> list[dict]`; CLI map/context và docs/context-index.json. Tests pin import tương đối, dependents bắc cầu, bỏ dataset, đọc edit chưa commit, giới hạn output và evidence link bị mất.

- [x] Viết và chạy test để thấy thất bại trước implementation: import tầng/mạng, gold path, syntax error, ignored-but-tracked data, doc links/budget, kết quả verifier rỗng/lệch.
- [x] Triển khai CLI stdlib; subprocess dùng sys.executable và cwd root, không shell.
- [x] Thêm marker local_data cho hai test vốn phụ thuộc dữ liệu BTC; giữ nguyên logic chúng.
- [x] Chạy test harness và full suite; thử CLI từ cwd khác và data preflight trong repo tạm.

### Task 3: CI và bàn giao

**Files:** .github/workflows/ci.yml; docs/PROGRESS.md; docs/validation.md; task record của tác vụ này.

- [x] Cấu hình CI Windows/Ubuntu chạy `python scripts/harness.py check --profile full`.
- [x] Chạy doctor, fast, full, data tại local và kiểm tra diff; ghi kết quả thực tế và phần chưa chạy trên hosted CI.
- [x] Fresh reviewer kiểm tra diff/spec, sửa lỗi quan trọng bằng regression test nếu có.
- [x] Cập nhật task record và PROGRESS với đường dẫn/lệnh tiếp tục.

## Execution record — 2026-10-29

Task 1 complete: root/scoped instructions, documentation routing, architecture, research synthesis and file-scoped context-index implemented; fast validates links/budgets. No historical Gemini files changed.

Task 2 complete: 44 harness test cases; `python -m pytest -q -rs` -> 302 passed, 1 historical skip; `python scripts/harness.py check` -> 301 passed, 2 local_data deselected. doctor confirms all five pinned packages under Python 3.14.10. Final clean temporary checkout without train/public_test/cache/venv also passed full 301 and rejected data with missing-input messages.

Final review: independent read-only reviewer checked spec/plan/code/docs. Important finding reproduced then fixed: force-tracked survey/raw report artifacts now rejected; direct and actual git add -f cases RED -> GREEN (17 focused tests passed).

Final: Ruling: package initializer dependency was graded Minor by reviewer; treated as Important because ordinary static `import pkg.engine` executes pkg/__init__.py and context should expose that effect. Added a failing synthetic case, then initializer edges; harness 44/44 and full suite passed. Cost if wrong is over-including a package dependency in navigation, never skipping checks.

Final review set aside dynamic dispatch and arbitrary secret scanning as explicitly documented limits, historical doc links as archived evidence, and the pre-existing self-score skip as out of runtime scope. Those remain review/test responsibilities; no claims of sandboxing, official evaluator equivalence or hosted CI success.

Task 3 complete: CI workflow authored (hosted execution not run); data profile exit 0, selected regression 409/409 matched gold and legacy, no errors, selected 417/3000, legacy skipped 8. Local_data tests 1 passed/1 historical skip. Full 301 and entire suite 302 are final post-review runs; data profile began before the final guard/navigation fixes and completed on unchanged business code/cache. PROGRESS/validation/README updated with scope and limits. No commits/push or global installation performed.

Publication follow-up: người dùng sau đó yêu cầu trực tiếp commit và đẩy harness lên nhánh VuongNguyen. Full harness chạy lại trước khi commit: 301 passed, 2 local_data deselected; không chạy lại gold vì runtime/cache không đổi. Giữ các con số hosted CI là chưa xác nhận cho tới khi GitHub Actions trả kết quả.
