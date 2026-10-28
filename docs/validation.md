# Trạng thái kiểm chứng ngày 2026-10-29 (đợt 1: thuốc + bảng giá)

Chạy trên macOS / Python 3.14, nhánh `nguyen/thuoc-banggia` (xếp trên `nguyen/agent-v0`), cache do `load_all.py` tạo lại sau khi thêm bảng `thuoc`, `bang_gia`.

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q -rs` | 276 passed, 0 skipped (test chấm điểm trên `train/answers.jsonl` đã chạy được) |
| `python -m compileall -q business verify_business.py` | Exit 0 |
| `git diff --check` | Exit 0 |
| `python verify_business.py` — bộ chọn cũ | khớp gold 409/409, khớp phép tính cũ 409/409, 0 lỗi (không đổi) |
| `python verify_business.py` — bộ chọn mở rộng C1–C9 | khớp 446/446 (không đổi) |
| `python verify_business.py` — loại mới P1 (kê đơn), P2 (hoạt chất), P3 (tăng giá) | khớp 44/44, 40/40, 38/38 |
| `python check_with_gold.py` | 263/263 + 146/146 (không đổi) |

**API hiện có phủ được 985/3000 câu train (chọn được), khớp 977** (bộ cũ 409/417, trong đó 8 câu bộ cũ bỏ qua; mở rộng 568/568).

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
| P1 | thuốc kê đơn / không kê đơn (tiền, %) | 44 | 44 | 0 | 0 |
| P2 | doanh thu theo hoạt chất | 40 | 40 | 0 | 0 |
| P3 | hiệu ứng tăng giá | 38 | 38 | 0 | 0 |

### C8: trước 35/46, sau khi sửa loader 46/46

11 câu lệch trước đây đều do `load_all.py::to_parquet` ghi `pd.NA` thành chuỗi `"<NA>"`, nên khách lẻ bị đếm thành một khách. Đã sửa ở PR #3 (ô rỗng ghi null thật); nạp lại cache thì C8 khớp 46/46, các loại khác không đổi.

### C10: luật chỉ có ở rulebook public

Verifier gọi 8 API C10 với rulebook train: cả 8 ra `UnsupportedRule`. Không có đáp án gold, nên **chỉ kiểm bằng test tổng hợp** (`tests/test_business_ext.py`).

Lượt loader trước đó trên 44 doanh nghiệp: 0 crash, 0 FAIL. Chi tiết từng câu nằm ở `reports/business_verification.{json,md}` tại local (Git ignore).
