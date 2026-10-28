# Metadata train phục vụ review vòng 001

Ngày thống kê: 2026-10-29. Nguồn là `train/questions.jsonl`, `train/answers.jsonl` và catalog/cache local. Chỉ ghi số liệu tổng hợp, không sao chép câu hỏi, đáp án từng câu hoặc dữ liệu doanh nghiệp vào file này.

## Phân bố kiểu đáp án

| Type | Toàn train | Tỷ lệ toàn train | Ngoài bộ chọn 417 câu |
|---|---:|---:|---:|
| number | 1884 | 62.80% | 1471 |
| percent | 578 | 19.27% | 578 |
| list | 193 | 6.43% | 193 |
| date | 145 | 4.83% | 145 |
| string | 88 | 2.93% | 88 |
| unanswerable | 70 | 2.33% | 66 |
| boolean | 23 | 0.77% | 23 |
| table | 19 | 0.63% | 19 |
| **Tổng** | **3000** | **100%** | **2583** |

Bộ chọn cũ chọn 417 câu (413 number, 4 unanswerable), bỏ qua 8 khi tính, còn 409 đối chiếu được. 409/3000 = 13.63%; đây là tỷ lệ được đối chiếu, không phải tỷ lệ agent có thể trả lời sau NLU. Ngoài bộ chọn và ngoài tập đối chiếu là hai mẫu số khác nhau (2583 và 2591).

## Nhóm mẫu file train hiện có

Đọc bằng `generalize_check.parse_groups` từ `surveys/DESIGN.md`. Đây là nhóm thiết kế đã có, không phải kết quả phân cụm mới trong lượt review.

| Nhóm | Họ mẫu file | Số doanh nghiệp train |
|---|---|---:|
| A | POS kiểu KiotViet | 6 |
| B | Xuất "DonHang_ChiTiet" | 5 |
| C | "Sổ chi tiết bán hàng" (kiểu MISA) | 5 |
| D | Sổ tay nhiều file | 2 |
| E | Sổ bán 1 sheet, không mã đơn, không tên khách | 3 |
| F | CSV phẳng 1 file | 3 |
| G | Chỉ có danh sách hoá đơn | 1 |
| H | CSV quan hệ | 3 |
| I | SQLite POS | 1 |
| J | Đa nguồn | 1 |
| **Tổng** | | **30** |

Script `generalize_check.py` loại README nhóm giấu khi xây từ điển. Chế độ `quy_tac` vẫn sử dụng `DESC_RULES` được viết từ toàn train; bản thân script có ghi rủi ro lạc quan. Loader và các ngưỡng/quy tắc đã được phát triển với toàn train nên không thể gọi một fold mới là hoàn toàn chưa từng thấy. Cần cố định manifest và rebuild artifact theo fold cho những lần tuning tiếp theo.

## Quét từ khóa nghiệp vụ sơ bộ

**Đây là heuristic nhiều nhãn, không phải phân bố domain chuẩn.** Một câu có thể trúng nhiều regex hoặc không trúng dù vẫn là câu hỏi sales. Không dùng số liệu này để chia quota nghiệp vụ hoặc tuyên bố coverage.

| Nhóm từ khóa | Số câu trúng |
|---|---:|
| inventory_or_import | 116 |
| sales_or_customer | 1908 |
| debt | 116 |
| profit | 22 |

Có 85 câu trúng hơn một nhóm và 923 câu không trúng nhóm nào. Pattern và kết quả theo doanh nghiệp được lưu local ở `reports/gemini_round001_review.py` và `reports/gemini_round001_review.json`; chưa thực hiện gán nhãn domain thủ công.

## Kiểm tra bổ sung

- Quét cụm `ca toi`/`ca dem` sau chuẩn hóa trong train: 0 câu. Không loại trừ cách diễn đạt khác hoặc dữ liệu private.
- Gold type number cần hơn 2 chữ số thập phân: 0. Không đủ để suy ra quy tắc làm tròn mọi tổng quantity.
- Kiểm tra `khach_key` trong 19 doanh nghiệp train không mã khách: 0 dòng khác `nk(ten_khach)`. Không phát hiện hash/ID tự tăng như giả định của phản chứng Gemini.
- `RULES` fixture không giống rulebook train. Đây là bản tổng hợp rút gọn cho test; không dùng thay thế rulebook thực tế khi quyết định luật cuộc thi.
- Thống kê theo doanh nghiệp có tại local; file chia sẻ này chỉ chứa tổng hợp. Chưa chấm thêm gold biên tăng trưởng, chưa tạo verifier mở rộng và chưa huấn luyện model.
