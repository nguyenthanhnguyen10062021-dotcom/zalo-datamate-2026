# Quyết định và vấn đề còn mở

Tài liệu này ghi trạng thái thực tế. Đề xuất của một AI không tự trở thành quyết định của người dùng. Phản hồi Gemini vòng 001 đã được người dùng lưu; Codex kiểm chứng ngày 2026-10-29.

## Nền tảng đã có trước vòng 001

| ID | Nội dung | Trạng thái và căn cứ |
|---|---|---|
| D001 | Tách loader, thư viện nghiệp vụ và tầng hiểu câu hỏi | Loader và `business/` đã triển khai theo trao đổi với người dùng; tầng hiểu câu hỏi chưa triển khai |
| D002 | Truyền rulebook đúng split và as_of_date vào phép tính | Đã có API và test; parser rulebook có phạm vi hỗ trợ giới hạn |
| D003 | Không tự coi DataError/UnsupportedRule là bằng chứng câu hỏi unanswerable | Đã thể hiện bằng API/test và tài liệu business |
| D004 | Gemini web tham gia review phát triển, người dùng chuyển tiếp qua file | Người dùng yêu cầu; chưa có tích hợp API hoặc đồng bộ tự động |
| D005 | Codex chủ động kiểm chứng và trao đổi kỹ thuật với Gemini, không chờ người dùng duyệt từng bước | Người dùng ủy quyền trực tiếp ngày 2026-10-29; đọc phản hồi, chạy test/probe, phản biện và chuẩn bị lượt tiếp theo. Ghi rõ đề xuất và phần đã thực thi. |

## Đang thảo luận

| ID | Vấn đề | Trạng thái | Nơi trao đổi |
|---|---|---|---|
| O001 | Contract và kiến trúc NLU → phép tính; độ sẵn sàng của API hiện tại | Đã thống nhất baseline QueryPlan tối thiểu; patch nghiệp vụ và test đã áp dụng tại c567b29. Executor/NLU chưa triển khai | `rounds/001_business_to_nlu/` |
| O002 | Thứ tự mở rộng hệ thống | Ưu tiên executor QueryPlan v1 trên nghiệp vụ hiện có, mở rộng kiểm chứng rồi tích hợp NLU; chưa mở rộng kho/nợ/lãi | Vòng 001; docs/PROGRESS.md |
| O003 | Model inference offline và môi trường chạy | Chưa chọn; chưa yêu cầu quyết định trong vòng 001 | Thảo luận sau khi rõ phạm vi và ngân sách |

## Kết luận review ngày 2026-10-29

Các dòng dưới là kết luận kỹ thuật của Codex, không phải ghi nhận đã sửa code hoặc người dùng đã chốt kiến trúc.

| ID | Kết luận | Căn cứ/trạng thái |
|---|---|---|
| R001 | Không đổi kỳ so sánh giao một phần thành unanswerable chỉ vì thiếu đầu kỳ | §7 train/public quy định tính phần có dữ liệu; đã chạy probe tổng hợp, chưa chấm gold biên |
| R002 | Filters của cancellation_rate/top_customers và denominator của revenue_share cần làm rõ trước dispatch NLU | Đã tái hiện TypeError và phụ thuộc luật sai phạm vi; chưa sửa production |
| R003 | Chưa coi phản chứng khóa khách hash của Gemini là lỗi cache hiện hành | Loader dùng nk(tên), 19 doanh nghiệp không mã khách không có dòng lệch hợp đồng; vẫn cần định nghĩa tie-break rõ hơn |
| R004 | Validation chỉ được nới khi chứng minh dòng lỗi không ảnh hưởng kết quả | Status ở kênh đã loại có thể xử lý cục bộ; ngày mất/dòng hàng mất chưa đủ bằng chứng để bỏ |
| R005 | Cần contract resolver để tách nhãn không tìm thấy khỏi dữ liệu không có thông tin | Unknown ID, unknown group/channel đang có hành vi khác; chưa chốt chính sách 0/unanswerable cho mọi trường hợp |

Chi tiết và câu hỏi gửi lại Gemini: `rounds/001_business_to_nlu/CODEX_REVIEW.md`, `CODEX_REPLY_TO_GEMINI.md`. Các thay đổi mới trong lượt review chưa được commit/push.

## Kiểm chứng phản hồi 02 ngày 2026-10-29

Chi tiết ở [CODEX_REVIEW_02.md](rounds/001_business_to_nlu/CODEX_REVIEW_02.md), thư tiếp theo ở [CODEX_REPLY_TO_GEMINI_02.md](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI_02.md).

- Gemini đã rút đề xuất đổi kỳ cơ sở giao một phần thành unanswerable và điều chỉnh nhận định khóa khách/validation.
- Chấp nhận hướng QueryPlan tối thiểu làm baseline kỹ thuật; schema và API mới chưa triển khai. Chốt capability/filter/period policy trước khi mở rộng.
- Không chấp nhận bỏ dòng mồ côi chỉ vì không nối được với đơn trong kỳ: probe cho hai kết quả hợp lệ 201/251 tùy nguồn liên kết còn thiếu.
- Cần contract precision và numerator/denominator rõ hơn; chưa thêm raw_decimal hoặc denominator_filters vào production.
- Kiểm chứng chia doanh nghiệp và group-disjoint là hai mục tiêu khác nhau; số liệu quét gold chưa đủ chốt entity-not-found hay top-k rỗng trong kỳ có dữ liệu.

## Kiểm chứng phản hồi 03 ngày 2026-10-29

Chi tiết ở [CODEX_REVIEW_03.md](rounds/001_business_to_nlu/CODEX_REVIEW_03.md), thư tiếp theo ở [CODEX_REPLY_TO_GEMINI_03.md](rounds/001_business_to_nlu/CODEX_REPLY_TO_GEMINI_03.md).

- Thống nhất v1 dùng public API trực tiếp, hoãn boolean/raw_decimal/parent-share; giữ share trên cả shop. Validation theo dependency nhưng không bỏ ORPHAN khi metric cần dòng hàng.
- Hai API cancellation_rate/top_customers cần patch order filters trước khi dùng bảng dispatch mới. V1 reject product filter cho cả hai API; chưa có patch production.
- Tách structural validator khỏi semantic validator/resolver. Chuẩn hóa số nguyên toán học hữu hạn trước dispatch, bool không được coi là int; parse ngày thật; [] thành null và reject mention rỗng. Đây là contract triển khai, chưa phải tính năng đã có.
- URI schema phải thuần; bỏ bảo đảm precision tuyệt đối chỉ dựa prec=28. Giữ nguyên bản phản hồi Gemini để truy vết.
- Đã chạy 19 trường hợp schema, 3 test dependency đích và 2 phản chứng chữ ký API; full suite 219 passed, 1 skipped. Không chạy lại verifier 409 khi code không đổi.

## Kiểm chứng phản hồi 04 ngày 2026-10-29

Chi tiết ở [CODEX_REVIEW_04.md](rounds/001_business_to_nlu/CODEX_REVIEW_04.md), artifact là [CODEX_BUSINESS_PATCH_04.diff](rounds/001_business_to_nlu/CODEX_BUSINESS_PATCH_04.diff). Production chưa thay đổi.

- Không áp dụng nguyên patch Gemini: thiếu import UnsupportedRule, và dời loại hủy/trả quá muộn gây ba regression trên doanh thu có filter.
- Với metric chỉ tính đơn hợp lệ, loại hủy/trả đã biết trước filter; giữ trạng thái chưa biết để kiểm tra sau filter. Với tỷ lệ hủy/đếm hủy, vẫn giữ mọi trạng thái cần thiết. Bản ứng viên Codex qua sáu test Gemini và giữ đúng ba phản chứng mới.
- Full suite trên baseline và ứng viên đều 219 passed, 1 skipped. Verifier chạy mới trên ứng viên đạt 409/409 khớp gold và phép tính cũ, 0 lỗi. Giữ tách biệt trạng thái ứng viên thử nghiệm và source đã áp dụng.
- Resolver cần output unit tường minh và policy ambiguity nhiều mã. `$schema` vẫn cần URI thuần; helper/schema chưa thành pipeline end-to-end.
- Khi câu hỏi không nói khác, tháng này so tháng trước dùng same_elapsed theo rulebook; không tự gọi là ambiguous chỉ vì câu hỏi không nhắc lại mặc định.

## Áp dụng patch nghiệp vụ sau lượt 04

Người dùng yêu cầu trực tiếp đưa bản sửa đã kiểm chứng vào code chính, chuyển phản chứng thành test và chạy lại kiểm tra. Đã áp dụng `CODEX_BUSINESS_PATCH_04.diff` vào `business/sales.py`, thêm 39 ca kiểm thử trong repo; full suite 258 passed, 1 skipped. Verifier chạy mới trên code chính đạt 409/409 khớp gold và phép tính cũ, 0 lỗi. Code và test đã commit tại `c567b29`; chi tiết ở [CODEX_IMPLEMENTATION_04.md](rounds/001_business_to_nlu/CODEX_IMPLEMENTATION_04.md). Các nhận định “chưa sửa production” trong review trước là trạng thái lịch sử.

## Bàn giao cuối phiên 2026-10-29

Code/test đã đẩy tại `c567b29`; hồ sơ trao đổi đã đẩy tại `211e492` trên nhánh `VuongNguyen`. Dừng phiên sau khi hoàn tất cập nhật tài liệu; không triển khai thêm executor trong lượt tổng kết. Tiến độ, giới hạn kiểm chứng, vấn đề còn mở và thứ tự tiếp tục nằm ở [docs/PROGRESS.md](../docs/PROGRESS.md).

## Mẫu ghi quyết định mới

- ID và ngày:
- Vấn đề/vòng thảo luận:
- Đề xuất của Codex:
- Ý kiến Gemini hoặc LLM khác:
- Bằng chứng đã kiểm tra và giới hạn:
- Quyết định, ai quyết định, phạm vi được giao:
- Lý do và đánh đổi:
- File thay đổi/test đã chạy nếu có:
- Điều kiện cần xem lại:
