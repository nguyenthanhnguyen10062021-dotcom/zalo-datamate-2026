# Zalo AI Challenge 2026 — DataMate

Hỏi đáp tiếng Việt trên dữ liệu bán hàng của các tiệm nhỏ (csv / xlsx / sqlite, mỗi tiệm một kiểu ghi sổ).
Mỗi câu hỏi có `as_of_date` ("hôm nay"); đáp án thuộc một trong các type: `number`, `percent`, `date`, `boolean`,
`string`, `list`, `table`, `unanswerable`. Luật nghiệp vụ nằm trong `rulebook.md` của từng bộ dữ liệu.

**Chấm điểm:** mỗi câu đúng **+1**, sai **−1**, bỏ trống (`{"type": "abstain"}` hoặc không có dòng) **0**.
Sai type hoặc sai format = sai. Vì vậy chỉ trả lời khi chắc, còn lại abstain.

## Dữ liệu (KHÔNG có trong repo)

Tải `train.zip` và `public_test.zip` từ portal BTC, giải nén vào thư mục gốc của repo:

```
zalo-datamate-2026/
├── train/          # data/<business_id>/, questions.jsonl, answers.jsonl, rulebook.md, calendar.csv
└── public_test/    # data/<business_id>/, questions.jsonl, rulebook.md, calendar.csv
```

## Cài đặt

```bash
python3 -m venv .venv && source .venv/bin/activate      # Python 3.10+ (đã chạy thử 3.14)
pip install -r requirements.txt
```

## Cách chạy (từ thư mục gốc)

| Lệnh | Việc làm |
|---|---|
| `python evaluate/evaluate.py --pred submission.jsonl --gold train/answers.jsonl --questions train/questions.jsonl` | Chấm submission theo luật BTC, ghi `errors.jsonl` |
| `python surveys/survey.py --out surveys/survey_raw.md` | Khảo sát cấu trúc mọi file của mọi tiệm (~5 phút) |
| `python load_all.py` | Nạp mọi tiệm về schema chuẩn → `cache/<business_id>/`, ghi `load_report.md` (~1,5 phút) |
| `python check_with_gold.py` | Đối chiếu bảng chuẩn với đáp án train → `gold_report.md` (cần chạy `load_all.py` trước) |
| `python generalize_check.py` | Leave-one-group-out + tiệm mẫu file mới → `generalize_report.md` (~3 phút) |
| `pytest tests/ evaluate/` | Unit test |

## Cấu trúc thư mục

```
evaluate/          evaluate.py (chấm điểm, chỉ thư viện chuẩn), test_evaluate.py
surveys/           survey.py (khảo sát dữ liệu), DESIGN.md (nhóm mẫu file, kiểu dữ liệu bẩn, schema chuẩn)
loader/            loader đưa mọi tiệm về schema chuẩn
  io.py            mở csv/xlsx/sqlite (chỉ đọc), tìm header
  readme.py        đọc README của tiệm (mô tả cột, quy ước, ngày cuối dữ liệu, quy đổi)
  parsers.py       parse số / tiền / ngày / trạng thái / khách / topping
  mapping.py       từ điển mô tả cột + tên cột (xây từ README train)
  abbrev.py        tách token, bung viết tắt (SL, ĐVT, HĐ, PTTT...)
  infer.py         suy vai trò cột từ giá trị (SL×giá≈tiền, mã đơn, giảm giá...) kèm bằng chứng
  raw.py           bảng thô sạch cho mọi file/sheet
  build.py         dựng bảng chuẩn: cua_hang, don_hang, dong_hang, mat_hang, quy_doi_don_vi, khach_hang
  checks.py        kiểm tra tự động sau khi nạp
load_all.py        nạp mọi tiệm -> cache/
check_with_gold.py kiểm tra bằng đáp án train
generalize_check.py kiểm tra khả năng tổng quát
tests/             unit test parser, viết tắt, suy luận từ giá trị
```

Hàm chính: `from loader import load_business; res = load_business("train/data/biz_101", "train/rulebook.md")`.

## Tiến độ

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 1 | `evaluate.py`: chấm điểm theo luật BTC | ✅ |
| 2 | Loader về schema chuẩn (v0 + 2c: viết tắt, suy từ giá trị) | ✅ 409/409 câu khớp đáp án train (263 doanh thu/huỷ + 146 số lượng/ca) |
| 3 | Thư viện hàm nghiệp vụ theo rulebook trên schema chuẩn | ⏭ tiếp theo |
| 4 | LLM (hiểu câu hỏi, sinh mapping cho mẫu file lạ) | |
| 5 | Dự phòng + chiến lược abstain | |
| 6 | Đóng gói Docker | |

## Luật thi quan trọng

- Chỉ dùng model **open-weight ≤ 15B**, chạy **offline** (không gọi API ngoài).
- **Cấm** logic theo `business_id` hay theo câu hỏi cụ thể. Code phải tổng quát, vì private test có ngành và mẫu file chưa gặp.
  Từ điển ánh xạ chỉ xây từ README của **train**.
- **Không train / tinh chỉnh trên public test**: chỉ được dùng để kiểm tra.
- Không đẩy dữ liệu BTC lên repo (xem `.gitignore`).
