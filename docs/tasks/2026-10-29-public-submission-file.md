# Tác vụ: tạo file public submission v1

- Ngày / owner: 2026-10-29 / Codex theo ủy quyền của người dùng
- Trạng thái: complete
- Code nền: nhánh `VuongNguyen`, HEAD `00043facd58fa47d064c4a794cc0ba0008b13fb5`, working tree đã dirty từ các tác vụ NLU/loader/audit đang làm; giữ nguyên mọi thay đổi không liên quan.
- Mục tiêu và lý do: rebuild cache cho đúng 14 business public, freeze đủ 1.000 job NLU v2, chạy đúng một batch Qwen2.5-7B trên Modal, thực thi QueryPlan local và xuất file upload thử `reports/public_submission/v1/submission.jsonl`.
- Ngoài phạm vi: Docker, upload portal, đọc hoặc suy gold public, dùng leaderboard để tuning, sửa đáp án theo ID, commit hoặc push.
- File/contract phải giữ: artifact từng dòng chỉ ở `reports/public_submission/v1/` (ignored); output đúng thứ tự public questions; mọi failure thành abstain không reason trong file nộp nhưng giữ reason ở sidecar; baseline budget ledger giữ byte-identical.
- Tài liệu liên quan: [thiết kế](../superpowers/specs/2026-10-29-public-submission-file-design.md), [kế hoạch](../superpowers/plans/2026-10-29-public-submission-file.md), [NLU](../nlu.md), [validation](../validation.md).
- Ủy quyền chi phí: người dùng duyệt thêm trần 5 USD cho đúng một batch Modal; policy riêng giữ envelope call 4 USD + margin 1 USD. Reservation không phải hóa đơn thực tế.

## Acceptance

- [x] Cache revision mới có 14 business, loader không crash; không ghi đè cache gốc/train.
- [x] `jobs.json` có đúng 1.000 ID duy nhất, 14 business, prompt `nlu-baseline-2`, sampling đã freeze và source/cache/code hash tái kiểm được.
- [x] Public budget ledger ban đầu chưa có, một reservation gốc và amendment GPU theo yêu cầu mới; baseline ledger SHA-256 giữ nguyên `B5E8D1E22600FA41EF04778445B2554B991501A8FB9148C6041AF3844175DEA9`.
- [x] `submission.jsonl` đúng 1.000 JSON object UTF-8, ID duy nhất/đúng thứ tự, không field nội bộ/alias/NaN/Infinity; tổng status/type bằng 1.000.
- [x] Targeted tests, harness full và data profile đạt; mọi Modal app stopped/tasks0.

## Tiến độ và quyết định

- Người dùng chọn luồng Native và chỉ cần file để upload test, chưa cần Docker hay tự động upload.
- Pre-cloud full gate sau Tasks 1–4: `637 passed, 2 deselected`; public output revision chưa tồn tại trước rebuild.
- 14 thư mục được phát hiện trực tiếp từ `public_test/data`: `dev_001` đến `dev_014`.
- Rebuild hoàn tất 14/14, 0 crash trong 117 giây; revision có 198 file, thiếu 0/84 file canonical. Snapshot root cache và train trước/sau không đổi.
- Frozen jobs: 1.000 ID và 1.000 request ID duy nhất, 14 business, hash `1ecc2ee7c4cab65039d2aa70048b8a6b1a1c288deb019b930603d7f5de35321d`.
- Người dùng sau đó yêu cầu tăng tốc bằng tối đa 10 GPU. Amendment thay giới hạn một GPU/batch bằng pool bổ sung tối đa 7 GPU trong lúc pool gốc còn 1 GPU; giữ model/prompt/schema/jobs/cache/sampling. Trần 5 USD được giữ bằng resource/time bounds và receipt extension riêng; ledger baseline/public gốc không reset.
- Các lần khởi tạo song song lỗi môi trường/import/generator wrapper đều giữ receipt; ba app đầu đã stopped/tasks0. SDK cần `inspect.unwrap` khi đăng ký lại generator serialized; không serialize wrapper Synchronizer Windows vào worker Linux. App song song thành công: `ap-nD2iIoOkRhwcb48RCJxc3N`; app gốc `ap-EuK7RZHXJon3m4myvJvEqK`.
- `tools/merge_public_generations.py` chỉ ghi khi union đủ toàn bộ frozen request IDs. Chặn duplicate/unknown bên trong từng source; overlap giữa hai pool chọn cố định primary, độc lập nội dung/đúng sai của plan. Synthetic regression đã PASS.

## Bằng chứng

| Lệnh / revision / ngày | Kết quả | Phạm vi và giới hạn |
|---|---|---|
| `python scripts/harness.py check` / 2026-10-29 | PASS full; 637 passed, 2 deselected | Synthetic, chưa chạy local-data profile |
| `Get-FileHash reports/nlu_baseline/v1/budget.json` / trước public batch | `B5E8D...75DEA9` | Dùng để chứng minh policy public không sửa ledger baseline |
| `python load_all.py ... --cache reports/public_submission/v1/cache` | 14 business, 0 crash, 117s | Artifact local ignored; không ghi row-level data vào hồ sơ |
| `python tools/public_jobs.py ...` | selected 1.000, businesses 14 | Source/cache/code hash tái kiểm bằng `load_public_jobs` |
| `python scripts/harness.py check --profile data` | PASS data; full 637 passed; selected regression 409/409 | 409/409 là regression chọn lọc, không phải whole-train PA |

## Lệnh vận hành đã duyệt

```powershell
python load_all.py --only dev_001,dev_002,dev_003,dev_004,dev_005,dev_006,dev_007,dev_008,dev_009,dev_010,dev_011,dev_012,dev_013,dev_014 --workers 6 --cache reports/public_submission/v1/cache --report reports/public_submission/v1/load_report.md
python tools/public_jobs.py --split public_test --cache reports/public_submission/v1/cache --out reports/public_submission/v1/jobs.json
python scripts/harness.py check --profile data
```

## Bàn giao

- Đã xong: implementation và synthetic/pre-cloud gates cho budget, freeze jobs, runner và harness guards.
- Đã hoàn tất: generation gốc1000/1000, local8workers, validator/integrity PASS. File64.040byte, SHA-256 `4487a9e300acd6996b621f6e195613e1e931f70246854d5a9405bf3dc8566591`; 698answered/48unanswerable/254abstain. Pool bổ sung118outputs không dùng vì gốc đã đủ trước; các app stopped/tasks0.
- Harness cuối640passed/2deselected; data gate409/409selected. Không mở gold public, không claim PA.
- Hành động tiếp theo: người dùng upload `reports/public_submission/v1/submission.jsonl` để test. Chưa Docker/portal upload/commit/push.
