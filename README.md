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
| `python verify_business.py` | Kiểm chứng thư viện nghiệp vụ trên tập câu train được bộ kiểm tra cũ chọn → `reports/business_verification.*` |
| `python eval_agent.py --split holdout --out runs/holdout` | Đánh giá agent trên tiệm HOLDOUT, điểm thật bằng luật chấm BTC (cần server LLM, xem [docs/agent.md](docs/agent.md)) |
| `python main.py --data <dir> --out <dir>` | Runner định dạng BTC → `<out>/submission.jsonl` + `run.log` |
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
business/          API nghiệp vụ bán hàng, rulebook và thời gian
verify_business.py kiểm chứng thư viện nghiệp vụ trên tập câu chọn lọc
ai_collaboration/  gói bàn giao và các vòng thảo luận với Gemini web
agent/             câu hỏi -> spec JSON (LLM) -> business/ -> đáp án: spec, prompt, few-shot BM25, khớp tên, dispatcher
config/            model.yaml (model, revision, sampling, Modal), split.json (tiệm DEV/HOLDOUT)
modal_app/         server vLLM trên Modal (chỉ lúc dev)
main.py            runner định dạng BTC
eval_agent.py      đánh giá agent theo tiệm
```

Hàm chính: `from loader import load_business; res = load_business("train/data/biz_101", "train/rulebook.md")`.

## Tiến độ

Trao đổi với Gemini web hoặc LLM khác: xem [ai_collaboration/README.md](ai_collaboration/README.md). Gói bàn giao có bối cảnh, source snapshot, yêu cầu thảo luận và chỗ lưu phản hồi để Codex kiểm chứng.

Kiểm chứng mới nhất ngày 2026-10-29: **276 test đạt**; thư viện nghiệp vụ phủ **985/3000 câu train** (bộ chọn regex trong verifier), khớp gold **977**. Đây là tập chọn lọc, chưa phải PA toàn bộ train. Xem [phạm vi và bằng chứng](docs/validation.md).

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 1 | `evaluate.py`: chấm điểm theo luật BTC | ✅ |
| 2 | Loader về schema chuẩn (v0 + 2c: viết tắt, suy từ giá trị) | ✅ 409/409 câu khớp đáp án train (263 doanh thu/huỷ + 146 số lượng/ca) |
| 3 | Thư viện hàm nghiệp vụ theo rulebook trên schema chuẩn | Thời gian/lịch Tết, doanh thu, số đơn, số lượng, tỷ lệ, xếp hạng; mở rộng: ngày/tháng cao nhất, chuỗi tháng, giá bán, hàng ế, lãi gộp, đếm khách, nhân viên, size, luật public; xem [API và giới hạn](docs/business.md) |
| 4 | LLM hiểu câu hỏi → spec JSON → business/ | v0: HOLDOUT **772/1027 (0,752/câu)**, v0.1 hậu kỳ 785; xem [docs/agent.md](docs/agent.md) |
| 5 | Dự phòng + chiến lược abstain | v0: abstain khi spec lỗi / unsupported / luật thiếu / dữ liệu lỗi / tên mơ hồ / độ tin cậy thấp |
| 6 | Đóng gói Docker | |

## Model (khai báo theo luật thi)

- Chính: **`Qwen/Qwen3.5-9B`**, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (Apache-2.0, phát hành 03/2026).
- Backup: `Qwen/Qwen3-14B`, revision `40c069824f4251a91eefaf281ebe4c544efd3e18` (Apache-2.0). Đổi qua `config/model.yaml`, không đổi code.
- Chỉ một model lúc suy luận; few-shot bằng BM25 thuần code. Serve bằng vLLM, `temperature=0`, `seed=0`, tắt thinking.

## Luật thi quan trọng

- Chỉ dùng model **open-weight ≤ 15B**, chạy **offline** (không gọi API ngoài).
- **Cấm** logic theo `business_id` hay theo câu hỏi cụ thể. Code phải tổng quát, vì private test có ngành và mẫu file chưa gặp.
  Từ điển ánh xạ chỉ xây từ README của **train**.
- **Không train / tinh chỉnh trên public test**: chỉ được dùng để kiểm tra.
- Không đẩy dữ liệu BTC lên repo (xem `.gitignore`).
