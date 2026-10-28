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

Làm việc với AI coding agent: bắt đầu tại [AGENTS.md](AGENTS.md), [bản đồ tài liệu](docs/README.md) và [hướng dẫn Harness Engineering](docs/harness-engineering.md). Bản triển khai tham khảo OpenAI/Anthropic và Trail-Code: ngữ cảnh theo file, import impact từ code hiện tại, kiểm tra tự động và bàn giao có bằng chứng.

Trên Windows chưa activate venv, thay `python` bằng `.\.venv\Scripts\python.exe`.

| Lệnh | Việc làm |
|---|---|
| `python evaluate/evaluate.py --pred submission.jsonl --gold train/answers.jsonl --questions train/questions.jsonl` | Chấm submission theo luật BTC, ghi `errors.jsonl` |
| `python surveys/survey.py --out surveys/survey_raw.md` | Khảo sát cấu trúc mọi file của mọi tiệm (~5 phút) |
| `python load_all.py` | Nạp mọi tiệm về schema chuẩn → `cache/<business_id>/`, ghi `load_report.md` (~1,5 phút) |
| `python check_with_gold.py` | Đối chiếu bảng chuẩn với đáp án train → `gold_report.md` (cần chạy `load_all.py` trước) |
| `python generalize_check.py` | Leave-one-group-out + tiệm mẫu file mới → `generalize_report.md` (~3 phút) |
| `python verify_business.py` | Kiểm chứng thư viện nghiệp vụ trên tập câu train được bộ kiểm tra cũ chọn → `reports/business_verification.*` |
| `pytest tests/ evaluate/` | Unit test |
| `python scripts/harness.py doctor` | Kiểm tra môi trường và dữ liệu local tùy chọn |
| `python scripts/harness.py map` | Bản đồ import Python hiện tại, không cần model/cache |
| `python scripts/harness.py context business/sales.py` | API, module phụ thuộc và quyết định liên quan trước khi sửa file |
| `python scripts/harness.py check` | Guard + test tổng hợp, giống CI, không cần dữ liệu BTC |
| `python scripts/harness.py check --profile data` | Thêm test cần dữ liệu và hồi quy gold tập chọn lọc trên local |

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
business/          API nghiệp vụ bán hàng, rulebook và thời gian
verify_business.py kiểm chứng thư viện nghiệp vụ trên tập câu chọn lọc
ai_collaboration/  gói bàn giao và các vòng thảo luận với Gemini web
```

Hàm chính: `from loader import load_business; res = load_business("train/data/biz_101", "train/rulebook.md")`.

## Tiến độ

**Kết thúc phiên 2026-10-29:** xem [tiến độ và điểm tiếp tục](docs/PROGRESS.md). Bản sửa nghiệp vụ đã áp dụng vào code chính tại [`c567b29`](https://github.com/nguyenthanhnguyen10062021-dotcom/zalo-datamate-2026/commit/c567b29); hồ sơ review đã đẩy tại `211e492`. Giai đoạn tiếp theo là executor QueryPlan v1 tất định, sau đó mới tích hợp model hiểu câu hỏi.

Trao đổi với Gemini web hoặc LLM khác: xem [ai_collaboration/README.md](ai_collaboration/README.md). Gói bàn giao có bối cảnh, source snapshot, yêu cầu thảo luận và chỗ lưu phản hồi để Codex kiểm chứng.

Kiểm chứng harness ngày 2026-10-29: toàn bộ suite **302 test đạt, 1 test cũ bỏ qua**; full profile dùng cho CI chạy local **301 đạt, 2 ca cần dữ liệu bị loại**. Lượt verifier mới khớp gold **409/409 câu đối chiếu được**, 0 lỗi, trên tập chọn lọc. Bộ 409 chạm 3/10 API, chưa phải PA toàn bộ train hoặc kết quả của tầng NLU. Xem [phạm vi và bằng chứng](docs/validation.md).

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 1 | Bộ chấm local | Đã có code/test; chưa được chứng nhận là evaluator BTC |
| 2 | Loader về schema chuẩn | Bản đầu đã chạy 44 doanh nghiệp; chưa chứng minh mọi mapping đúng |
| 3 | Thư viện nghiệp vụ và patch sau review Gemini | Đã áp dụng patch, thêm 39 ca kiểm thử; xem [API và giới hạn](docs/business.md) |
| 4 | Executor QueryPlan: validator, resolver, dispatcher | Đã thống nhất phạm vi v1; chưa tích hợp thành module production |
| 5 | Model câu hỏi → QueryPlan | Chưa chọn/tích hợp model |
| 6 | Mở rộng đánh giá, confidence và abstain toàn hệ thống | Chưa có kết quả đầu-cuối; verifier hiện tại là tập con |
| 7 | Runner offline và Docker | Chưa hoàn thiện |

## Luật thi quan trọng

- Chỉ dùng model **open-weight ≤ 15B**, chạy **offline** (không gọi API ngoài).
- **Cấm** logic theo `business_id` hay theo câu hỏi cụ thể. Code phải tổng quát, vì private test có ngành và mẫu file chưa gặp.
  Từ điển ánh xạ chỉ xây từ README của **train**.
- **Không train / tinh chỉnh trên public test**: chỉ được dùng để kiểm tra.
- Không đẩy dữ liệu BTC lên repo (xem `.gitignore`).
