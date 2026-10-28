# QueryPlan executor v1

Người dùng đã duyệt triển khai phạm vi executor JSON → API trong cuộc trao đổi ngày 2026-10-29. Chưa triển khai model, verifier mở rộng, runner nộp bài hoặc nghiệp vụ mới.

## Thiết kế

Thêm `queryplan/` phía trên `business/`, nhận bảng chuẩn, Rulebook, as_of_date và calendar_path do caller cung cấp. Không import loader/evaluator/gold/network. Không thêm dependency. Giữ nguyên API và ngữ nghĩa business.

Contract JSON giữ baseline vòng review 001: version="1.0", status=supported|unsupported, unsupported_reason, operation, expected_type, period, comparison_period, filters, ranking. Tất cả key bắt buộc, không chấp nhận key lạ ở mọi object. Các trường không dùng phải null. Validator Python tách normalize, structure, semantic; chưa cung cấp JSON Schema cho constrained decoding.

Period có kind,n,month,quarter,year,start_date,end_date. Hỗ trợ các kind của Periods; before_period chỉ ở comparison và chỉ khi kỳ chính là tet. previous_month_same_elapsed trong comparison chỉ dùng với this_month. Growth this_month thiếu comparison mặc định same_elapsed theo rulebook; growth khác phải có comparison. previous_month tường minh nghĩa cả tháng trước.

Filters có product_mentions,product_group_mention,channel_mention,payment_mention,customer_group_mention,shift,unit_mention. Ranking có k,metric. Chuẩn hóa số nguyên hữu hạn 1.0 → 1; reject bool/chuỗi/số lẻ. [] → null, mention trống reject; không sửa input. Parse ngày lịch thật. Year 1..9999; không thêm giới hạn năm 1900..2100 thiếu căn cứ.

Resolver dùng NFC/casefold/gộp khoảng trắng, giữ dấu và dấu câu; không fuzzy, không alias học từ gold, không hardcode ID. Product mention tra tên trong catalog, nhiều mã cùng tên là ambiguous (không tự hợp nhất). Các nhãn cấp đơn chỉ tra trong đơn đã xảy ra đến as_of_date; tên hợp lệ ngoài kỳ hỏi vẫn được resolve. Nhãn raw khác nhau nhưng cùng khóa chuẩn hóa bị báo ambiguous vì business lọc bằng nhãn raw. Unit trả riêng, dùng quy tắc chuẩn hóa giống quantity. Không có cột/không có thông tin để resolve là MissingInformation (unanswerable có bằng chứng); có dữ liệu nhưng không khớp là ResolutionError; không biến nhãn lạ thành số 0. Catalog key hỏng khi thực sự dùng catalog là DataError.

Capability v1 giới hạn 10 API hiện hành. Unit chỉ cho quantity; ranking chỉ cho top_* và metric đúng API; product filters không hỗ trợ cancellation_rate/top_customers; share phải có filter thực sau normalize và mẫu số cả shop. Không refactor business.

ExecutionResult giữ Answer, status và stage để caller ghi log local. Lỗi plan/resolve/capability/data/rule/period tạo abstain với status riêng; không tự biến lỗi thành unanswerable. Thiếu thông tin ở resolver và unanswerable từ business giữ lý do riêng. Lỗi implementation bất ngờ và sai expected_type phải phát sinh exception, không bị nuốt. Result không tự ghi file hoặc gửi dịch vụ.

Calendar được kiểm tra input tại adapter hẹp (header, ô bắt buộc, leap, mốc Tết). Không dùng catch chung ValueError/KeyError quanh Periods để đoán đó là input lỗi. Kỳ không biểu diễn được trong date được kiểm tra tường minh. Hai yêu cầu này đã được làm rõ bằng phản chứng ở lượt review cuối.

## Cách tiếp cận

Hướng người dùng đã duyệt: executor gọi public API. Codex chọn validator Python thay vì thêm jsonschema để không đổi dependency; nếu sau này cần constrained decoding, bổ sung schema với kiểm chứng tương đương contract. Chưa cần compiler SQL hoặc tổng quát hóa growth/share.

## Acceptance

- Cả 10 operation đi từ JSON qua kiểm tra/resolve đến Answer đúng giá trị fixture và bằng gọi API trực tiếp.
- Ngày lỗi, field dư/thiếu, bool/số lẻ, mention lạ/trùng, unit, kỳ so sánh, unsupported filter và status unsupported được kiểm tra.
- Giữ kỳ giao một phần, mẫu số share, lỗi ORPHAN theo dependency, rulebook đúng caller và percent âm/>100.
- Input bất biến; unexpected exceptions không bị đổi thành đáp án.
- Harness bảo vệ ranh giới package mới; full/data chạy qua, giữ mẫu số gold cũ, không tuyên bố PA của executor/NLU từ verifier cũ.
