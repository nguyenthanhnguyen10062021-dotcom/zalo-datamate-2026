# Agent v0: câu hỏi → spec JSON → business/ → đáp án

## Model (luật thi)

| | Model | Revision (commit Hugging Face) | Giấy phép |
|---|---|---|---|
| Chính | `Qwen/Qwen3.5-9B` (9B, phát hành 03/2026) | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | Apache-2.0 |
| Backup | `Qwen/Qwen3-14B` (đổi bằng `active` trong `config/model.yaml` hoặc biến `DATAMATE_MODEL=qwen3_14b`) | `40c069824f4251a91eefaf281ebe4c544efd3e18` | Apache-2.0 |

Chỉ dùng một model lúc suy luận (≤ 15B). Few-shot tìm bằng BM25 thuần code, không có embedding/reranker. vLLM chạy chỉ phần ngôn ngữ (`--language-model-only`), tắt thinking (`chat_template_kwargs.enable_thinking=false`, theo model card). Tái lập: `temperature=0`, `seed=0`, `--generation-config vllm`, ghim revision.

## Luồng xử lý

1. **Prompt** ([agent/prompt.py](../agent/prompt.py)):
   - system cố định (vLLM prefix-cache): vai trò, danh sách op, quy ước kỳ, 16 ví dụ **tự viết** (không lấy từ train/public);
   - 5 ví dụ train giống nhất (BM25, chỉ từ tiệm DEV);
   - thẻ dữ liệu tiệm: khoảng ngày, có mã đơn/khách, nhóm hàng, kênh, thanh toán, nhóm khách, mã nhân viên, đơn vị.
   - Prompt TB khoảng 3.000 token, tối đa khoảng 6.600 (< 32K).
2. **LLM → spec** ([agent/llm.py](../agent/llm.py)): client OpenAI-compatible; structured output `json_schema` (guided decoding) nên luôn ra JSON đúng schema; timeout, thử lại 1 lần.
   - **Quan trọng:** spec ví dụ phải viết đúng thứ tự trường của schema (`prompt.canonical`). Guided decoding sinh khoá theo thứ tự schema; ví dụ viết khác thứ tự thì model bỏ sót trường. Ví dụ `unit` viết trước `product` thì mất tên hàng: bản thử đầu sai 6/60 câu vì lỗi này.
3. **Kiểm tra spec** ([agent/spec.py](../agent/spec.py), pydantic): op trong danh sách đóng, đủ tham số, `answer_type` hợp với op. Lỗi thì đưa lỗi cho LLM sửa 1 lần, vẫn lỗi thì abstain.
4. **Hậu kỳ** (`pipeline.post_check`, v0.1):
   - xếp hạng `k=1` → string, `k>1` → list;
   - `revenue_series` cần ≥ 2 kỳ khác nhau;
   - nhãn lọc (nhóm hàng, kênh, thanh toán, nhóm khách, nhân viên) phải có mặt trong câu hỏi.
5. **Dispatcher** ([agent/dispatch.py](../agent/dispatch.py)): kỳ có cấu trúc → `business.Periods` (theo as_of_date + rulebook); kỳ so `previous_period` / `same_period_last_year` do code tính. Tên hàng/nhóm/kênh khớp với danh mục tiệm ([agent/resolve.py](../agent/resolve.py), bỏ dấu); mơ hồ/không thấy → `ambiguous` → abstain. Gọi đúng API `business/` → format §9.
6. **Abstain** (sai −1, bỏ trống 0) khi gặp một trong các trường hợp:
   - spec lỗi sau khi sửa; op `unsupported`;
   - `UnsupportedRule`; `DataError`; tên mơ hồ;
   - `Answer.confidence == 'low'`; LLM chọn `unanswerable` (mặc định abstain);
   - lỗi LLM/runtime.

## Kiểm chứng dispatcher

Bộ chọn của `verify_business.py` giờ sinh **spec** và chạy qua dispatcher + bộ khớp tên: vẫn 446/446 (tổng 855/863). Các spec này (chỉ những spec cho đáp án khớp gold) là nguồn few-shot.

## Đánh giá (`eval_agent.py`, chia theo tiệm, `config/split.json`)

- **Chia tiệm:** trong mỗi nhóm mẫu file (DESIGN.md), khoảng 1/3 số tiệm vào HOLDOUT (seed 2026), nhóm chỉ có 1 tiệm để ở DEV.
- **HOLDOUT:** 10 tiệm, 1.027 câu; mọi nhóm có từ 2 tiệm trở lên đều có mặt ở cả hai bên.
- **Few-shot:** chỉ lấy từ kho DEV (918 ví dụ). Khi chấm DEV, few-shot bỏ ví dụ của chính tiệm đang hỏi.

| Lượt (Qwen3.5-9B, L40S trên Modal) | HOLDOUT điểm | /câu | đúng / sai / bỏ trống | DEV (tham khảo) |
|---|---|---|---|---|
| v0, (a) không self-consistency — **con số sạch** | **772** / 1027 | **0,752** | 798 / 26 / 203 | 1394 / 1973 (0,707) |
| v0, (b) self-consistency 3 mẫu (T=0,7, seed 1–3) | 745 | 0,725 | 752 / 7 / 268 | — |
| v0.1 = v0 + hậu kỳ (a) | 785 | 0,764 | 800 / 15 / 212 | 1418 (0,719) |
| v0.1 + hậu kỳ (b) | 749 | 0,729 | 756 / 7 / 264 | — |

- **Chọn (a):** self-consistency giảm sai từ 26 xuống 7 nhưng mất 46 câu đúng.
- **v0.1:** hậu kỳ rút ra từ lỗi HOLDOUT, nên điểm HOLDOUT v0.1 **không còn sạch**. DEV cũng tăng (sai 59 → 38), cho thấy luật không chỉ khớp riêng HOLDOUT. v0.1 được tính lại trên chính các spec của v0, không gọi lại LLM.
- **Lỗi 408 của Modal:** khi container thứ hai khởi động lạnh, 126 câu HOLDOUT và 86 câu DEV bị HTTP 408. Đây là lỗi hạ tầng lúc dev, lúc thi chạy vLLM local thì không gặp. Các câu này đã chạy lại riêng. Trước khi chạy lại: HOLDOUT (a) 748.
- Spec hợp lệ: 99,2% (HOLDOUT), 100% (DEV). Abstain (a) HOLDOUT 19,8%: 162 `unsupported`, 19 thực thi không được, 10 tên mơ hồ, 8 lỗi LLM, 4 LLM chọn unanswerable.

Chi tiết theo type, loại câu, op: `runs/<lượt>/report.md` tại local (git ignore: có câu hỏi train).

## Chạy

```bash
# server (dev): xem modal_app/serve_vllm.py; lúc thi: vllm serve local, cùng tham số trong config/model.yaml
set -a; . ./.env; set +a                     # DATAMATE_LLM_API_KEY (không commit)
export DATAMATE_LLM_BASE_URL=https://<workspace>--datamate-vllm-serve-dev.<region>.modal.run/v1
python -m agent.fewshot --shops dev --out artifacts/fewshot_dev.jsonl    # kho few-shot để chấm
python -m agent.fewshot --shops all --out artifacts/fewshot_all.jsonl    # kho few-shot lúc thi (cả 30 tiệm)
python eval_agent.py --split holdout --out runs/holdout                   # thêm --sc để so self-consistency
python main.py --data public_test --out out/public                       # runner định dạng BTC
```

`main.py`: nạp tiệm (loader, cache ở `<out>/cache`), chạy song song có giới hạn (`--workers`), ghi `submission.jsonl` từng dòng + `run.log`; chạy lại cùng `--out` thì bỏ qua câu đã có. Câu lỗi → abstain.

## Giới hạn đã biết

- **Thiếu API:**
  - câu hỏi 2 số với 2 bộ lọc ("đơn Zalo và đơn tại quầy mỗi loại bao nhiêu"): 8/26 câu sai v0;
  - so ca chiều với ca sáng (%): 4/26;
  - công nợ, tồn kho, nhập hàng, hạn dùng, hoạt chất/kê đơn, bảng (table): đang `unsupported`.
- **Loader:** tiệm có mã khách nhưng đơn không ghi tên → `top_customers` trả unanswerable trong khi tên có ở bảng khách hàng.
- **Hiểu sai còn lại:** "hôm nay" thành hôm qua, "tháng 1 năm 2026" thành cả năm, số đơn thành số đơn huỷ.
- Kho few-shot và `runs/` chứa câu hỏi train (dữ liệu BTC), không đẩy lên repo. Docker cần dựng kho `fewshot_all.jsonl` từ `train/` lúc build image.
