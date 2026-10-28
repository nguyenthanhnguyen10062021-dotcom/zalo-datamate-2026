# Trạng thái kiểm chứng ngày 2026-10-29

Chạy trên macOS / Python 3.14, nhánh `nguyen/business-ext`, cache do `load_all.py` tạo (loader không đổi so với `main`).

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q -rs` | 244 passed, 0 skipped (test chấm điểm trên `train/answers.jsonl` đã chạy được) |
| `python -m compileall -q business verify_business.py` | Exit 0 |
| `git diff --check` | Exit 0 |
| `python verify_business.py` — bộ chọn cũ | khớp gold 409/409, khớp phép tính cũ 409/409, 0 lỗi (không đổi) |
| `python verify_business.py` — bộ chọn mở rộng C1–C9 | khớp 435/446 |

**API hiện có phủ được 863/3000 câu train (chọn được), khớp 844** (bộ cũ 409/417, trong đó 8 câu bộ cũ bỏ qua; mở rộng 435/446).

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
| C8 | đếm khách / mặt hàng theo số đơn | 46 | 35 | 11 | 0 |
| C9 | nhân viên (doanh thu theo mã, bán giỏi nhất) | 13 | 13 | 0 | 0 |

### C8 lệch 11 câu: lỗi ghi cache của loader, không phải luật

Cả 11 câu đều thừa đúng 1 khách. Nguyên nhân: `load_all.py::to_parquet` đổi `pd.NA` của cột chuỗi thành chuỗi `"<NA>"`. Ở 13 tiệm có mã khách, các đơn khách lẻ vì vậy mang `ma_khach = "<NA>"` và bị đếm thành một khách. Giả lập trong bộ nhớ việc coi `"<NA>"` là rỗng thì C8 khớp 46/46, các loại khác không đổi. Chưa sửa vì phần này không được sửa loader. Cách sửa đề xuất là một dòng trong `to_parquet`: dùng `pd.isna(v)` thay cho kiểm tra `None`/`float NaN`, rồi chạy lại `load_all.py`.

### C10: luật chỉ có ở rulebook public

Verifier gọi 8 API C10 với rulebook train: cả 8 ra `UnsupportedRule`. Không có đáp án gold, nên **chỉ kiểm bằng test tổng hợp** (`tests/test_business_ext.py`).

Lượt loader trước đó trên 44 doanh nghiệp: 0 crash, 0 FAIL. Chi tiết từng câu nằm ở `reports/business_verification.{json,md}` tại local (Git ignore).
