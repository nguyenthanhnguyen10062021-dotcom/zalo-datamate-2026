# Kiểm chứng bản sửa nghiệp vụ ngày 2026-10-29

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
