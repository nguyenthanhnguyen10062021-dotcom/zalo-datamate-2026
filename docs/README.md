# Bản đồ tài liệu

Đọc [PROGRESS](PROGRESS.md) để tiếp tục công việc, rồi chọn đúng nhánh dưới đây. Source hiện tại và kết quả chạy mới là căn cứ; hồ sơ cũ có thể mô tả tính năng chưa áp dụng.

| Công việc | Đọc trước | Lệnh lấy ngữ cảnh |
|---|---|---|
| Làm quen repo | [README](../README.md), [kiến trúc](architecture.md) | `python scripts/harness.py map` |
| Sửa loader | [hướng dẫn loader](../loader/AGENTS.md), phần liên quan của [schema/design](../surveys/DESIGN.md) | `python scripts/harness.py context loader/build.py` |
| Missingness cache / tên khách | [task sửa và kiểm chứng](tasks/2026-10-29-loader-missingness-customer-name.md) | Writer nullable string; bổ sung tên thiếu theo mã duy nhất; cache revision riêng |
| Nghiệp vụ/thời gian | [API](business.md), [hướng dẫn business](../business/AGENTS.md) | `python scripts/harness.py context business/sales.py` |
| Bộ chấm | [hướng dẫn evaluator](../evaluate/AGENTS.md) | `python scripts/harness.py context evaluate/evaluate.py` |
| Kiểm chứng | [bằng chứng và giới hạn](validation.md), [harness](harness-engineering.md) | `python scripts/harness.py check` |
| Inventory capability / verifier mới | [contract và lệnh](capability-verification.md), [hướng dẫn dev-only](../verification/AGENTS.md) | `python scripts/harness.py context verification/runner.py`; manifest local trước gold |
| Audit plan annotation | [phương pháp/kết luận](plan-annotation-audit.md), [task evidence](tasks/2026-10-29-plan-annotation-audit.md) | `python scripts/harness.py context verification/audit.py`; artifact từng câu chỉ reports/ |
| Audit semantic v4 / customer-share | [contract, findings và next action](tasks/2026-10-29-v4-semantic-audit.md), [validation](validation.md) | Đã audit61; ưu tiên missingness serialization/customer join trước model |
| QueryPlan/NLU tiếp theo | [executor v1](queryplan.md), [hướng dẫn queryplan](../queryplan/AGENTS.md), [quyết định](../ai_collaboration/DECISIONS.md) | `python scripts/harness.py context queryplan/executor.py`; NLU chưa có |
| Baseline NLU/Modal | [contract](nlu.md), [plan và execution record](tasks/2026-10-29-nlu-modal-baseline-plan.md), [hướng dẫn NLU](../nlu/AGENTS.md) | Core đã có strict parser/prompt/schema; real model smoke đang chạy; Modal dev-only, cap25USD |
| File public submission | [thiết kế đã duyệt](superpowers/specs/2026-10-29-public-submission-file-design.md), [kế hoạch thực thi](superpowers/plans/2026-10-29-public-submission-file.md), [contract NLU](nlu.md) | Prepare: `python tools/public_jobs.py --split public_test --cache reports/public_submission/v1/cache --out reports/public_submission/v1/jobs.json`; run/validate: `python run_public_submission.py --jobs reports/public_submission/v1/jobs.json --generations reports/public_submission/v1/generations.jsonl --out reports/public_submission/v1`; chỉ tạo file test, không Docker/không upload |
| Cải thiện sau public score âm | [semantic safety/task](tasks/2026-10-29-semantic-safety.md), [contract NLU](nlu.md) | Gate trước dispatch; replay nguyên predictions bằng `tools/replay_semantic.py`; jobs mới cho prompt3, không nới source-integrity checks |
| Kế hoạch cải thiện từ research | [plan ưu tiên và acceptance](tasks/2026-10-29-research-improvement-plan.md) | Planned: audit abstain → semantic/grounding → capability/model có kiểm chứng; runner offline bắt đầu sớm, không rewrite theo research cũ |
| Triển khai sau Argon | [contract và evidence](tasks/2026-10-29-selector-calendar-implementation.md), [validation](validation.md) | Đã sửa intent/span/preflight/calendar/grammar; v4 396/396, chưa NLU |
| Thảo luận Codex/Gemini/Antigravity | [workflow](../ai_collaboration/README.md), [vòng003 mới](../ai_collaboration/rounds/003_three_ai_restart/README.md), [hướng dẫn](../ai_collaboration/AGENTS.md) | Đề bài chung + prompt riêng; vòng001/002 là lịch sử, chưa nhận phản hồi vòng003 |
| Tác vụ qua nhiều phiên | [mẫu task](tasks/TEMPLATE.md) hoặc kế hoạch đang làm | Giữ acceptance, evidence, next action trong cùng hồ sơ |

[Chỉ mục ngữ cảnh theo file](context-index.json) trỏ tới quyết định và bằng chứng có liên quan; lệnh `context` tự chọn các mục phù hợp. Không đọc toàn bộ GEMINI_HANDOFF hoặc rounds để bắt đầu mọi tác vụ.

Tài liệu `superpowers/specs/` và `superpowers/plans/` ghi thiết kế/kế hoạch theo ngày. Chỉ dùng kế hoạch đúng tác vụ, kiểm tra trạng thái thực thi trước khi tiếp tục. Không coi mọi checkbox cũ là việc cần làm lại.
