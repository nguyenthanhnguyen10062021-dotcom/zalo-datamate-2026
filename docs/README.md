# Bản đồ tài liệu

Đọc [PROGRESS](PROGRESS.md) để tiếp tục công việc, rồi chọn đúng nhánh dưới đây. Source hiện tại và kết quả chạy mới là căn cứ; hồ sơ cũ có thể mô tả tính năng chưa áp dụng.

| Công việc | Đọc trước | Lệnh lấy ngữ cảnh |
|---|---|---|
| Làm quen repo | [README](../README.md), [kiến trúc](architecture.md) | `python scripts/harness.py map` |
| Sửa loader | [hướng dẫn loader](../loader/AGENTS.md), phần liên quan của [schema/design](../surveys/DESIGN.md) | `python scripts/harness.py context loader/build.py` |
| Nghiệp vụ/thời gian | [API](business.md), [hướng dẫn business](../business/AGENTS.md) | `python scripts/harness.py context business/sales.py` |
| Bộ chấm | [hướng dẫn evaluator](../evaluate/AGENTS.md) | `python scripts/harness.py context evaluate/evaluate.py` |
| Kiểm chứng | [bằng chứng và giới hạn](validation.md), [harness](harness-engineering.md) | `python scripts/harness.py check` |
| Inventory capability / verifier mới | [contract và lệnh](capability-verification.md), [hướng dẫn dev-only](../verification/AGENTS.md) | `python scripts/harness.py context verification/runner.py`; manifest local trước gold |
| Audit plan annotation | [phương pháp/kết luận](plan-annotation-audit.md), [task evidence](tasks/2026-10-29-plan-annotation-audit.md) | `python scripts/harness.py context verification/audit.py`; artifact từng câu chỉ reports/ |
| QueryPlan/NLU tiếp theo | [executor v1](queryplan.md), [hướng dẫn queryplan](../queryplan/AGENTS.md), [quyết định](../ai_collaboration/DECISIONS.md) | `python scripts/harness.py context queryplan/executor.py`; NLU chưa có |
| Triển khai sau Argon | [contract và evidence](tasks/2026-10-29-selector-calendar-implementation.md), [validation](validation.md) | Đã sửa intent/span/preflight/calendar/grammar; v4 396/396, chưa NLU |
| Gemini/LLM review | [workflow](../ai_collaboration/README.md), [vòng002 hiện tại](../ai_collaboration/rounds/002_capability_readiness/README.md), [hướng dẫn](../ai_collaboration/AGENTS.md) | Argon lượt02 đã review và triển khai bước tiếp; phản hồi cũ giữ nguyên |
| Tác vụ qua nhiều phiên | [mẫu task](tasks/TEMPLATE.md) hoặc kế hoạch đang làm | Giữ acceptance, evidence, next action trong cùng hồ sơ |

[Chỉ mục ngữ cảnh theo file](context-index.json) trỏ tới quyết định và bằng chứng có liên quan; lệnh `context` tự chọn các mục phù hợp. Không đọc toàn bộ GEMINI_HANDOFF hoặc rounds để bắt đầu mọi tác vụ.

Tài liệu `superpowers/specs/` và `superpowers/plans/` ghi thiết kế/kế hoạch theo ngày. Chỉ dùng kế hoạch đúng tác vụ, kiểm tra trạng thái thực thi trước khi tiếp tục. Không coi mọi checkbox cũ là việc cần làm lại.
