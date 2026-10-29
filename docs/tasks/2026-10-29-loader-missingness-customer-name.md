# Sửa missingness cache và bổ sung tên khách theo mã

- Ngày: 2026-10-29, Asia/Saigon; owner: Codex theo yêu cầu trực tiếp của người dùng.
- Trạng thái: **complete**. Nền `00043fa`, VuongNguyen; có sẵn thay đổi tài liệu/audit/vòng003, giữ nguyên ngoài phần cập nhật trạng thái liên quan.
- Phạm vi: `load_all.to_parquet`, `_join_customers` và synthetic regressions. Không NLU, đổi mapping/grammar/business/evaluator, fuzzy, dependency, commit/push hoặc tiếp tục tranh luận.
- Nguồn: [audit v4](2026-10-29-v4-semantic-audit.md), [loader guidance](../../loader/AGENTS.md), [architecture](../architecture.md), train rulebook §3.

## Acceptance chốt trước sửa

- Writer roundtrip giữ missingness None/NaN/pd.NA/NaT, mã chuỗi có zero đầu và literal strings; giữ semantics số/bool/date, không mutate input. Không sửa cache cũ bằng thay sentinel hàng loạt.
- Chỉ bổ sung tên thiếu bằng catalog khi join theo mã duy nhất. Giữ tên có sẵn, tên gốc, khóa, walk-in, duplicate-key policy và no-code matching hiện hành; không fallback sang tên nếu mã không khớp.
- Fixture tích hợp writer→cache→SalesMetrics.top_customers chứng minh tên có thể dùng và khách lẻ không được xếp hạng; lỗi vẫn phân loại theo contract cũ.
- Targeted tests RED→GREEN, harness full và data nếu đầu vào sẵn. Rebuild train vào revision dưới reports/ ignored, giữ cache mặc định và frozen manifests/annotations; replay v4/baseline riêng, audit references nếu integrity cho phép. Không ngoại suy PA.
- Review diff, cập nhật PROGRESS/validation và **dừng báo người dùng sau hai sửa**.

## Evidence và bàn giao

Trước sửa đã chạy map/context writer/build; context cho test mới chưa indexed (file chưa tồn tại). Không sửa Python ngoài phạm vi trên.

- RED trên baseline: test mới **6 failed, 3 passed**, lỗi ở missingness và customer-name enrichment/consumer.
- GREEN: `python -m pytest tests/test_loader_data_integrity.py tests/test_parsers.py tests/test_abbrev_infer.py -q`: **165 passed** (9 ca mới).
- `python scripts/harness.py check`: **554 passed, 2 local_data deselected**, PASS full. Doctor đúng5pinned dependencies; local data ready.
- Đã dựng cache train mới bằng `load_all.py --only <tất cả thư mục train/data> --workers 6 --cache reports/loader_fixes_20261029/cache --report reports/loader_fixes_20261029/load_report.md`. Danh sách `--only` lấy bằng `(Get-ChildItem -LiteralPath train/data -Directory).Name -join ','`, không lọc theo câu hỏi/gold. Không rebuild public test/cache mặc định.
- `reports/loader_fixes_20261029/before.json` freeze661file được bảo vệ (cache cũ, manifest/report audit và source/corpus liên quan) và hai hash source đã sửa trước rebuild. Không chứa bản sao rows trong tài liệu tracked.
- Data profile mặc định kiểm cache cũ; replay với `--cache` mới ghi riêng sau khi build hoàn tất như bên dưới. Chưa chuyển default cache.

### Rebuild và replay đã hoàn tất

- Train30doanh nghiệp,0crash,258giây; output mới dưới reports/, không rebuild public test.
- So150bảng canonical cũ/mới (`cache_diff.json`): chỉ khôi phục missing ở `ma_khach`190492ô, `khach_key`190492ô, `nhom_khach`78246ô, `dia_chi_khach`96500ô; bổ sung103573ô `ten_khach`. Không thấy chênh lệch giá trị/shape/schema khác trong150bảng đã so; không kiểm raw tables bằng phép so này.
- Replay audit nguyên61annotation:46reference plans,15not_run,42compared=41matched+1mismatch,4abstain,0execution_errors. Một mismatch customer-ranking→matched;40matched cũ giữ matched,1mismatch và4abstain cũ giữ kết quả. Selected37 vẫn37matched; riêng9unparsed plans nay4matched/1mismatch/4abstain. Không sửa annotations/plans hoặc dùng số này làm modelPA.
- Predictions mới freeze trước mở gold trong replay. `audit_predictions.json` SHA256 `3d45291e6a50543c48d11a9b337a638fe2ad5423d3b991753ae6b7ed8fa77804`; report `audit_scoring.json` dùng API `score_one(gold,pred)`, kiểm3synthetic adapter cases. Không chạy adapter cũ sai trong semantic_audit_v1.
- Cross-check CLI evaluator trên46predictions đã freeze và cùng old audit gold subset: **41correct/1wrong/4abstain**, exit0; xuất error local mới riêng. Giữ15not_run ngoài execution, không báo PA toàn train/model từ mẫu này.
- `verify_queryplans.py --manifest reports/capability_inventory/manifest_v4.json --cache reports/loader_fixes_20261029/cache --out reports/loader_fixes_20261029/verification_v4.json`: exit0, **3000 total / 396 selected / 2604 outside**, **396 compared/matched**, 0 mismatch/abstain/execution_errors, 8 operation. Giữ manifest và selector cũ.
- `verify_business.py --cache reports/loader_fixes_20261029/cache --out reports/loader_fixes_20261029/business_verification`: exit0, **417 selected / 8 legacy skipped / 409 compared**, **409 matched gold và legacy**, 0 errors. Baseline riêng; không cộng với396 hoặc audit46.
- `harness.py check --profile data` đã PASS: full554passed/2deselected; local_data1passed/1skip helper evaluator cũ (không tìm thấy answers theo path của helper); baseline mặc định cache cũ417selected/8skipped/409compared/409matched,0errors. Kiểm này không thay thế replay cache mới.
- `integrity.json`:661protected files không đổi, hai patched source không drift trong rebuild,423filecache mới được hash. Cache mặc định/old manifests/annotations giữ nguyên.

## Bàn giao và dừng

- Đã hoàn tất hai sửa source, 9 regression tổng hợp, full/data checks, rebuild train revision riêng, replay v4/baseline/audit và đối chiếu 150 bảng canonical. Final diff được review; không đổi API hoặc trạng thái lỗi nghiệp vụ.
- Cache train mới để dùng tường minh: `reports/loader_fixes_20261029/cache`. Cache mặc định vẫn là snapshot cũ; chưa promote hoặc rebuild public test. Report từng câu và dữ liệu chỉ nằm dưới reports/ ignored.
- Một mismatch và bốn abstain của audit vẫn còn, thuộc các khoảng trống group mapping/label resolution đã biết; không sửa trong tác vụ này. Không có PA model/toàn train, holdout độc lập hoặc hosted CI mới.
- **Dừng theo yêu cầu người dùng.** Không NLU, không tiếp tục tranh luận hoặc tự mở tác vụ khác. Chưa commit/push.
