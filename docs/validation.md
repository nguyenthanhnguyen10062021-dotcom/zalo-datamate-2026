# Trạng thái kiểm chứng ngày 2026-10-29 (sau khi gộp sửa loader #3)

Chạy trên macOS / Python 3.14, nhánh `nguyen/business-ext`, cache do `load_all.py` tạo (loader không đổi so với `main`).

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q -rs` | 255 passed, 0 skipped (test chấm điểm trên `train/answers.jsonl` đã chạy được) |
| `python -m compileall -q business verify_business.py` | Exit 0 |
| `git diff --check` | Exit 0 |
| `python verify_business.py` — bộ chọn cũ | khớp gold 409/409, khớp phép tính cũ 409/409, 0 lỗi (không đổi) |
| `python verify_business.py` — bộ chọn mở rộng C1–C9 | khớp 446/446 |

**API hiện có phủ được 863/3000 câu train (chọn được), khớp 855** (bộ cũ 409/417, trong đó 8 câu bộ cũ bỏ qua; mở rộng 446/446).

## Bộ chọn mở rộng theo loại

Bộ chọn là regex bảo thủ, chỉ nằm trong `verify_business.py` để đo; không phải tầng hiểu câu hỏi lúc thi. Câu bộ cũ đã chọn không chọn lại. So khớp bằng `evaluate.score_one` (cùng luật chấm của BTC, có alias).

| Loại | Nội dung | Chọn | Khớp | Lệch | Lỗi |
|---|---|---|---|---|---|
| C1 | ngày/tháng doanh thu cao nhất | 142 | 142 | 0 | 0 |
| C2 | doanh thu một mặt hàng | 77 | 77 | 0 | 0 |
| C3 | giá bán mặt hàng ngày D | 51 | 51 | 0 | 0 |
| C4 | doanh thu nhiều tháng / tăng liên tục | 39 | 39 | 0 | 0 |
| C5 | số ly size M/L | 46 | 46 | 0 | 0 |
| C6 | số mặt hàng ế | 20 | 20 | 0 | 0 |
| C7 | lãi gộp (cửa hàng, hàng lời nhất) | 12 | 12 | 0 | 0 |
| C8 | đếm khách / mặt hàng theo số đơn | 46 | 46 | 0 | 0 |
| C9 | nhân viên (doanh thu theo mã, bán giỏi nhất) | 13 | 13 | 0 | 0 |

### C8: trước 35/46, sau khi sửa loader 46/46

11 câu lệch trước đây đều do `load_all.py::to_parquet` ghi `pd.NA` thành chuỗi `"<NA>"`, nên khách lẻ bị đếm thành một khách. Đã sửa ở PR #3 (ô rỗng ghi null thật); nạp lại cache thì C8 khớp 46/46, các loại khác không đổi.

### C10: luật chỉ có ở rulebook public

Verifier gọi 8 API C10 với rulebook train: cả 8 ra `UnsupportedRule`. Không có đáp án gold, nên **chỉ kiểm bằng test tổng hợp** (`tests/test_business_ext.py`).

Lượt loader trước đó trên 44 doanh nghiệp: 0 crash, 0 FAIL. Chi tiết từng câu nằm ở `reports/business_verification.{json,md}` tại local (Git ignore).
