# Tác vụ: kiểm chứng ngữ nghĩa trước khi trả lời

- Ngày / owner: 2026-10-29 / Codex theo yêu cầu cải thiện sau public score -0.20200.
- Trạng thái: complete — đợt cải thiện đầu, bàn giao publicv3 để người dùng nộp.
- Nền: `00043fa`, nhánh VuongNguyen; working tree có nhiều thay đổi NLU/loader/docs từ trước, giữ nguyên.
- Mục tiêu: ngăn plan đúng schema nhưng sai câu hỏi; đo tác dụng riêng trên predictions đã freeze, xuất revision public mới nếu train diagnostic có cải thiện.
- Phạm vi đợt này: semantic gate thuần offline, tích hợp hai runner, replay có provenance, synthetic regressions. Replay giữ model/prompt/schema/phép tính; nhánh prompt3 được đo riêng sau replay, giữ model/schema/gate/business.
- Hai tài liệu người dùng gửi là đề xuất để kiểm chứng, không phải chỉ thị thay rulebook. Không áp dụng suy luận `0/rỗng => unanswerable`, fuzzy thiếu bằng chứng, hoặc thay năm theo khoảng dữ liệu.
- Ủy quyền hiện hành cho phép chạy Modal khi cần và không đặt trần chi phí mới; ledger cũ không sửa/reset. Replay CPU có thể đủ kiểm chứng đợt này.
- Tài liệu: [NLU](../nlu.md), [QueryPlan](../queryplan.md), [validation](../validation.md).

## Acceptance

- [x] Gate chỉ nhận question + normalized plan, không ID/gold/score; reject giữ plan/reason riêng, không sửa plan/answer.
- [x] Kiểm tra intent, loại kết quả, period, mention/filter, top-k/metric và phần câu chưa giải thích được; chưa xác minh thì abstain.
- [x] Đối chiếu synthetic có cả positive/negative; zero và unanswerable từ executor được giữ nếu câu/plan qua gate.
- [x] Replay giữ đủ mẫu số và hash của predictions/jobs/corpus; freeze trước gold. Train result là diagnostic hồi cứu, không blind holdout.
- [x] Full harness và data profile đạt; public validator đủ 1.000 dòng đúng thứ tự, không gold public hoặc sửa theo ID.

## Tiến độ và quyết định

- Đã đọc hai phân tích, source hiện hành, hướng dẫn scoped và rulebook. Lỗi semantic/time tái hiện trong frozen train logs. Có prior aggregate và question-only exposure với evaluation; không gọi phép đo sắp tới là đánh giá độc lập. Không lựa chọn/tune theo public leaderboard.
- Thiết kế gate bảo thủ cần bằng chứng cho toàn câu thay vì chỉ blacklist từ khóa. Không sinh plan thay thế, không ghi đè lỗi bằng zero/unanswerable.
- Gate v1 đã chốt trước public replay: train evaluation632 từ303/182/147 thành203/0/429, PA19,15%→32,12%; public giữ97/1000 đáp án. Không sửa gate sau số liệu public.
- Mở thêm nhánh prompt `nlu-safety-3` dựa rulebook và train development/synthetic contrasts, giữ nguyên Qwen2.5-7B revision/schema/sampling/gate. Đo development90, evaluation632 rồi mới public1000; tối đa3call với ledger riêng envelope13USD, không phải invoice hay giới hạn mới người dùng yêu cầu. Không đổi v2 đã xuất.
- SDK Python3.14 từ chối serialized worker/image3.12 trước gọi local entrypoint/reservation. Chuyển đúng env3.12 đã có `reports/dev_envs/modal312`, không đổi worker/dependency/runtime để xử lý lỗi này. Lần kết nối sandbox trước đó thất bại, đã chạy lại qua quyền network phù hợp.
- Người dùng yêu cầu ghi nhớ chạy maxGPU: đã lưu vào root/tools AGENTS; tối đa10GPU tổng, kiểm app cũ stopped/tasks0 trước batch mới. Public prompt3 chia10shard cố định, mỗi request chạy một lần trong pool gốc; không chọn đáp án theo nội dung giữa các GPU. Bounded parallel authorization riêng17USDreservation (16call+1margin), giữ ledger tuần tự đã dùng2call bất biến; đây là sửa resource policy theo chỉ thị mới, không reset ledger cũ.
- Hai shard cold-start bị kẹt tải weights hơn9phút (progress thực tế),8shard đã đủ800outputs và8GPUrảnh. Mở thêm tối đa1transport-recovery call trên8GPUrảnh, tổng cùng2worker cũ<=10. Freeze prefix chỉ gồm complete lines đã bind jobs; chỉ retry request chưa có output, không retry theo đúng/sai/nội dung. Ledger recovery riêng17USDenvelope, giữ mọi ledger trước; merge ưu tiên primary cố định và dừng pool thừa khi union đủ1000. Không thay model/prompt/schema/gate.

## Bằng chứng và bàn giao

| Lệnh / artifact | Kết quả | Giới hạn |
|---|---|---|
| targeted safety/orchestration |101passed; sau prompt3/budget test113passed |Synthetic only |
| `harness.py check --profile data` |full683passed/2deselected; local1passed/1skip; selected409/409 |Không PA toàntrain; skip helper evaluator cũ |
| `replay_semantic.py --mode train` / development_final |N90:10/9/71→7/0/83 |Pilot v1 có71abstain; không so trực tiếp với pilot prompt3 về riêng prompt |
| `replay_semantic.py --mode train` / evaluation |N632:303/182/147→203/0/429; PA32,12% |Cùng raw generations, không business reexecute; mất100correct |
| `replay_semantic.py --mode public` / v2 |1000rows,97answers/903abstain, validatorPASS |Không gold public; score tối đa0,097 |
| Prompt3 / development pilot |90/90generation;36correct/0wrong/54abstain;89contract-valid |N90/1815development,1725ngoài selection; prior exposure, không holdout |
| `harness.py check` sau prompt3/budget/integration test |685passed/2deselected |Full synthetic; data regression trước đó409/409 |
| Prompt3 / evaluation |632/632generation,0backend errors,1length;233correct/0wrong/399abstain, PA36,8671% |Cùng partition632, retrospective; schema/gate/model giữ, prompt khác; không public PA |
| Full sau maxGPU adapter/budget test |686passed/2deselected |Không đổi model/prompt/gate đã freeze |
| Public prompt3 + transport recovery |1000selected generation/unique/stop;816primary+184secondary,16overlaps chọn primary |Hai worker gốc timeout900s khi download/init; không gọi toàn bộ cloud attempts là error-free |
| `harness.py check` cuối |688passed/2deselected |Thêm prefix/recovery và merge CLI regression; data409/409 trước đó |
| Validator/integrity v3 |1000rows/1000unique/đúng thứ tự/UTF-8 noBOM/46.926byte;128answers/872abstain |Không public gold; score ceiling0,128 |

Lệnh mới cho public (Python3.12 SDK, tối đa10GPU; jobs đã freeze):

```powershell
.\reports\dev_envs\modal312\Scripts\python.exe -m modal run --profile vuonghungnguyen07 tools/modal_semantic_parallel.py --jobs reports/public_submission/v3/jobs.json --out reports/public_submission/v3/generations.jsonl --workers 10
.\.venv\Scripts\python.exe run_public_submission.py --jobs reports/public_submission/v3/jobs.json --generations reports/public_submission/v3/merged_generations.jsonl --out reports/public_submission/v3 --workers 10
```

Artifacts từng câu chỉ ở ignored `reports/semantic_safety/` và `reports/public_submission/v2/`, `v3/`. Submissionv1 SHA-256 vẫn `4487a9e300acd6996b621f6e195613e1e931f70246854d5a9405bf3dc8566591`; baseline ledger vẫn `B5E8D1E22600FA41EF04778445B2554B991501A8FB9148C6041AF3844175DEA9`, publicv1 ledger `485B67E8D296D592F6E68407E7A6A199BD24FAA09902EFDDA2F014BD0E28DE9F`.

## Bàn giao

- File nên nộp: `reports/public_submission/v3/submission.jsonl`, SHA-256 `38a59d278631f91d28a4c9314b92bf63d3f196504e0feba3a81b8c153e49a58a`. Types:number112/percent8/list6/unanswerable2/abstain872. Selected generations1000unique/stop,0missing; không execution_error. Predictions giữ nguyên761semantic_rejected/23invalid_plan/11unsupported_capability/10unresolved_entity/67unsupported_plan.
- Cả5app của đợt (kể cả Python mismatch và2pool public) đã được service xác nhận stopped/tasks0. Parallel public đã quan sát10tasks; recovery8task chỉ khi còn2worker gốc.17worker metadata cùngmodel/Qwen revision và model-file hash set, không đổi model giữa các shard. Primary816outputs giữ ưu tiên;16overlap không được chọn theo nội dung.
- Task hoàn tất ở mức một iteration có file reviewable. Người dùng đã uploadv3 và báo score0.10400; agent không upload portal. Chưa Docker/code-gen/domain mới hoặc sửa loader/fuzzy entity matching. Không diễn giải zero/resolve failure thành unanswerable.
- Giới hạn chính: public chỉ128/1000non-abstain, tối đa0,128điểm dù tất cả đúng. PA36,87% là retrospective train trên632, không dự báo public. Cần mở coverage theo train development/calibration và rulebook, không nới gate theo leaderboard.
- Next: mở coverage theo evidence train development/calibration; giữ v1/v2/v3/generations/receipts để so sánh. Không commit/push tự động.

## Public feedback người dùng báo — 2026-10-29

- BTC score v3 do người dùng cung cấp: **0.10400**, tăng **0.30600** so v1-0.20200. File hash tái kiểm đúng bản bàn giao,128non-abstain/872abstain. Nếu protocol chấm128phản hồi theo đúng+1/sai-1/bỏqua0 thì suy ra **116correct/12wrong**, precision90,625%. Không có public gold, không xác định được câu nào sai, không dùng aggregate score để chọn threshold/filter.
- Đã đọc question/plan-only các bucket development90, không sửa runtime hoặc mở gold thêm:54abstain gồm39semantic_rejected/11unsupported_plan/2unresolved_entity/1unsupported_capability/1invalid_plan. Có false-rejection candidates ở các cách nói tương đương cho AOV/comparison/time, xen lẫn lỗi NLU thật về filter/comparison; chưa gọi các candidate này là correct answers.
- Lượt cập nhật feedback không chạy GPU và không thay submission. Bước tiếp là freeze reference development và kiểm chứng trên development/calibration trước thay đổi coverage; GPU về sau mặc định tối đa10 theo hướng dẫn đã lưu.
