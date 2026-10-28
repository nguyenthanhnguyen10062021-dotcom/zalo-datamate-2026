# Codex kiểm chứng phản hồi vòng 001

Ngày review: **2026-10-29**. Code nghiệp vụ: `1c89252`, nằm trong HEAD `2085afa`. Đã đọc thêm loader, rulebook thực tế, evaluator, generalize_check và metadata train local.

**Kết luận:** nên thử baseline QueryPlan có schema + resolver + runtime kiểm chứng. Gemini nêu được khoảng trống API thật, nhưng không nên áp dụng nguyên mọi đề xuất sửa. Đặc biệt, đổi kỳ giao một phần thành unanswerable trái rulebook hiện tại; bỏ validation khi mất ngày/mất dòng hàng có thể làm sai số liệu.

Lượt này chỉ review và chuẩn bị phản hồi: **chưa sửa production code, chưa chốt QueryPlan, chưa mở rộng verifier, chưa commit/push các file review**.

## Bằng chứng đã chạy

- `python -m pytest -q -rs`: **219 passed, 1 skipped**. Skip cũ là helper evaluator tìm gold sai vị trí, không phải thiếu dữ liệu train.
- 18 probe tổng hợp tái hiện hành vi trên code hiện tại; thống kê 3000 câu train và kiểm tra khóa khách trong 19 doanh nghiệp train không có mã khách.
- Script và output local: `reports/gemini_round001_review.py`, `reports/gemini_round001_review.json` (Git ignored). Số liệu tổng hợp chia sẻ: [TRAIN_METADATA.md](TRAIN_METADATA.md).
- Không chạy lại 409 câu trong lượt này vì production code không đổi. Báo cáo chạy trước push vẫn ghi 409/409 khớp gold và phép tính cũ; không trình bày đó là một lượt chạy mới.

## Kiểm chứng từng nhận xét

| Nhận xét | Kiểm chứng và kết luận | Hướng xử lý đề xuất |
|---|---|---|
| A4: thiếu filters ở cancellation_rate/top_customers | **Đúng, ưu tiên cao.** Truyền `filters=` vào cả hai đều TypeError. [sales.py:226](../../../business/sales.py#L226), [sales.py:303](../../../business/sales.py#L303). | Thêm filter và test tử/mẫu đúng cùng phạm vi; dispatcher reject tham số chưa hỗ trợ, không bỏ qua. |
| Q3: giá trị lọc không thấy xử lý khác nhau | **Đã tái hiện, cần chốt contract trước NLU.** Product ID lạ → unanswerable; nhóm/kênh lạ → number 0; mã có trong danh mục nhưng kỳ không bán → 0. [sales.py:155](../../../business/sales.py#L155). Chưa có gold đủ để chốt mọi nhãn không tồn tại. | Tách resolved/ambiguous/not-found khỏi tính toán. ID LLM bịa không được tự biến thành kết luận unanswerable. |
| A6: share phụ thuộc luật nhóm khách và mẫu số cả shop | **Đúng về giới hạn API.** Xóa luật nhóm khách làm tỷ trọng nhóm hàng UnsupportedRule; mẫu số một nhóm cha chưa biểu diễn được. [sales.py:340](../../../business/sales.py#L340). | Tách luật mẫu số đúng phạm vi; cân nhắc denominator_filters/ratio. Nếu giữ v1 nhỏ, mô tả rõ chỉ share cả shop. |
| A5: validation quá rộng | **Đúng một phần.** Status lỗi ở đơn thuộc kênh chắc chắn bị loại vẫn chặn kênh đang hỏi. Tuy nhiên mất ngày hoặc toàn bộ chi tiết đơn thì chưa biết bản ghi có ảnh hưởng kết quả hay không. [sales.py:81](../../../business/sales.py#L81), [sales.py:118](../../../business/sales.py#L118). | Thu hẹp theo bằng chứng an toàn; không bỏ mọi kiểm tra để tăng độ phủ. |
| A2: quarter có năm vẫn kiểm tra nhãn không ghi năm | **Giới hạn parser, chưa phải sai kết quả hiện tại.** quarter(1,2026) trả 01/01–31/03; đổi nhãn chứa định nghĩa quý làm UnsupportedRule. [periods.py:76](../../../business/periods.py#L76). | Có thể tách định nghĩa quý dương lịch khỏi suy năm; không bỏ kiểm tra luật để giả định mọi split giống nhau. |
| A1: tie-break khách không mã | **Phản chứng chỉ xác nhận khi dùng khóa giả định khác loader.** CUST_2/CUST_1 cho kết quả Gemini nêu, nhưng khóa loader thật từ tên cho Anh Dũng đứng trước Bình. 19 doanh nghiệp train không mã khách: 0 dòng lệch hợp đồng khóa này. | Làm rõ mã thật/khóa gom nhóm/tên hiển thị và collator. Không sửa `_rank` chung dựa co_ma_khach vì còn xếp hạng sản phẩm. |
| A3: kỳ so sánh giao một phần cần unanswerable | **Không đồng ý sửa theo đề xuất này.** §7 của cả train/public quy định tính trên phần dữ liệu có. Probe baseline 100 ở phần giao, current 200 trả 100%, phù hợp điều khoản đó. | Giữ logic phần giao; bổ sung log kỳ hiệu dụng và test/gold biên, không tự đặt luật mới. |

## Giải thích các điểm không nên sửa máy móc

### Kỳ cơ sở giao một phần

`train/rulebook.md:101` và `public_test/rulebook.md:134` cùng ghi:

> Kỳ chỉ có một phần nằm trong khoảng ngày có dữ liệu thì tính trên phần có dữ liệu.

Không có ngoại lệ được ghi cho kỳ cơ sở tăng trưởng. Dữ liệu tự tạo bắt đầu 15/02, baseline 01–20/02 có doanh thu 100, current 01–20/03 có doanh thu 200 → 100%. Độ dài hai phần dữ liệu khác nhau không đủ căn cứ đổi thành unanswerable. Chưa tìm/chấm gold các câu biên đó trong lượt này; nên bổ sung kiểm chứng nhưng không khẳng định đã xác nhận gold.

### Khóa khách và thứ tự hòa

[loader/build.py:825](../../../loader/build.py#L825) tạo `khach_key = ten_khach.map(nk)` khi không có mã khách. [name_key/nk](../../../loader/parsers.py#L46) bỏ dấu, chữ thường và chuẩn hóa dấu câu/khoảng trắng; không sinh hash hay ID tự tăng. Vì vậy ví dụ hash của Gemini không chứng minh lỗi trên cache đang dùng. Vẫn cần làm rõ thứ tự tên có dấu và hợp đồng khi nhận schema từ nguồn khác.

`_rank()` dùng chung cho sản phẩm và khách: sửa nó theo `co_ma_khach` sẽ làm thứ tự sản phẩm phụ thuộc vào việc shop có mã khách, điều không được phép. Nếu sửa, truyền tie-break riêng cho từng đối tượng, kiểm thử mã thật/tên có dấu/biến thể cách viết.

### Dòng thiếu dữ liệu có thể vẫn ảnh hưởng truy vấn

- Ngày đã lỗi thì chưa biết chắc đơn thuộc năm 2024 hay tháng đang hỏi; chỉ loại được nếu còn bằng chứng độc lập đáng tin cậy.
- Đơn O2 thiếu toàn bộ dòng hàng thì chưa biết O2 có mua Cà phê/P2 hay không. Lọc sản phẩm trước rồi bỏ O2 có thể trả tổng thấp hơn thực tế. Probe hiện DataError, phù hợp giữ an toàn.
- Có thể giảm validation không liên quan theo metric: chẳng hạn số đơn không nhất thiết cần danh mục sản phẩm hợp lệ. Nhưng phải chứng minh lỗi bị bỏ không thể thay đổi kết quả.

## Các giả thuyết phụ

| Vấn đề | Kết quả và giới hạn |
|---|---|
| Quantity 6 chữ số | Probe 0.3333333 trả 0.333333. Không gold number nào trong train cần hơn 2 chữ số, nhưng §9 chỉ ghi 2 chữ số cho phần trăm và **số trung bình khác**, không trực tiếp cho mọi tổng quantity. Chưa đủ căn cứ đổi toàn bộ về 2. |
| Ca tối/đêm | Rulebook thực tế chỉ có ca sáng/chiều; quét cụm `ca toi`/`ca dem` sau chuẩn hóa trong train cho 0 câu. Không chứng minh private không hỏi hoặc không có cách nói khác. Ca lạ phải đi nhánh chưa hỗ trợ. |
| Tên khách đầu tiên trên đơn | §9 nhận mọi cách viết tên có trong file và mã. Tên xuất hiện hợp lệ không mặc nhiên sai. Canonical name giúp ổn định nhưng chưa phải điều kiện bắt buộc để đúng. |

## Sửa cách mô tả độ kiểm chứng

- Có **10** metric SalesMetrics; bộ 409 chạm **3** phương thức revenue/cancelled_orders/quantity. Ca sáng/chiều vẫn là revenue. Vậy **7/10** phương thức chưa có đối chiếu gold trong verifier, không phải 6/10; danh sách Gemini nêu thực ra có 7.
- Các phương thức đó có test tổng hợp và smoke trên cache thật; “chưa được verifier gold chạm tới” khác “chưa hề chạy dữ liệu thật”. 219 là toàn suite, không phải tất cả business/synthetic.
- `tests/conftest.py::RULES` là bản tổng hợp rút gọn, **không giống 100% rulebook train**.
- Answer đóng gói được boolean/string/date/table; phần thiếu là producer/composer/validator cho những type này, không phải không có kiểu biểu diễn.

## Điểm thống nhất

Nên làm baseline QueryPlan có schema → resolver → kiểm tra luật/khả năng → API nghiệp vụ → composer/format validator → log. Giữ riêng unsupported, ambiguous, entity-not-found, data-error, known-unanswerable và runtime-error. Mở rộng kiểm chứng trước khi tuyên bố độ phủ tổng quát; đánh giá theo nhóm mẫu file.

## Điểm còn khác nhau

Ngoài các phản biện ở trên, thiết kế JSON của Gemini cần bổ sung:

1. Whitelist **API công khai**, không dispatch private `_revenue`, `_count`, không bắt `_Unavailable` trực tiếp: public API đã đổi nó thành Answer. Nếu cần số chưa làm tròn, thiết kế primitive/typed result công khai phù hợp cho composer.
2. Có version, ràng buộc tổ hợp metric/operation/type/filter/ranking/kỳ so, reject field thừa hoặc field không dùng. Ví dụ chuỗi `A | B | null` là mô tả, chưa phải enum/null thật của JSON Schema.
3. Khoảng ngày tường minh, ngưỡng, mẫu số đã lọc, nhiều metric, date/table phải có biểu diễn hoặc bị đánh dấu ngoài phạm vi v1. Không để model chọn rồi runtime bỏ qua.
4. Domain customer có một phần API đã hỗ trợ; không dùng quy tắc máy móc `domain != sales → abstain`. Câu “bán tốt hơn” chưa đủ để tự chọn doanh thu nếu không có quy ước rõ.
5. Evidence spans giúp truy vết chứ không chứng minh hiểu đúng. Làm tròn sau phép tính phù hợp, không lấy các số đã làm tròn trung gian để tính lại tỷ lệ/xếp hạng nếu luật không cho phép.

Nhận định về tokens, tốc độ, “100% đúng cú pháp”, mức chính xác model ≤15B/codegen chưa có benchmark của repo. Hai ví dụ PA 0.30/0.546 tính đúng nhưng coverage/precision là giả định. Đề xuất chưa dùng codegen fallback ở baseline đầu hợp lý; chưa có căn cứ cấm vĩnh viễn mọi codegen.

## Trả lời 5 câu hỏi gửi Codex

1. Đã thống kê type của 3000 câu và 2583 câu ngoài bộ chọn, theo doanh nghiệp tại local. [TRAIN_METADATA.md](TRAIN_METADATA.md) ghi tổng hợp. Keyword domain có chồng lấn và nhiều câu bỏ sót, chưa phải nhãn Sales/Kho/Nợ/Lãi chính xác.
2. Kỳ cơ sở cắt biên: giữ phần giao theo §7; bổ sung test/gold biên sau, không sửa dựa trực giác.
3. 0/unanswerable: thực thể đã resolve nhưng kỳ không phát sinh khác thực thể chưa resolve, thiếu loại thông tin hoặc top-k tập rỗng. Chưa kết luận mọi nhãn vắng phải trả cùng một type.
4. Bộ 409 là baseline hồi quy khi tách thư viện khỏi checker cũ, không phải verifier tổng quát. Nên mở rộng theo thao tác/kỳ, ghi mẫu chọn/bỏ/lỗi/chênh. Không ép 10–30 gold cho mọi tổ hợp nếu train không có; không viết bộ chọn theo đáp án hay chỉ giữ câu đã khớp.
5. generalize_check đọc nhóm A–J từ DESIGN, loại README nhóm giấu khi xây từ điển; chế độ DESC_RULES vẫn có ảnh hưởng toàn train, chính script thừa nhận lạc quan. Cần rebuild artifact theo fold và cố định manifest trước khi tune tiếp. Train đã dùng xây loader/khảo sát nên holdout mới là kiểm chứng hồi cứu, không phải tập hoàn toàn chưa thấy.

## Yêu cầu tiếp theo gửi Gemini

Đã chuẩn bị [CODEX_REPLY_TO_GEMINI.md](CODEX_REPLY_TO_GEMINI.md) để chuyển lại Gemini. Không có nội dung nào được gửi tự động lên web.

## Quyết định và thay đổi

Chưa có quyết định triển khai mới của người dùng. Đề xuất thứ tự: chốt entity/filter/denominator contract có test → mở rộng kiểm chứng trên dev theo thao tác/kỳ → cố định fold hồi cứu → thử QueryPlan v1 nhỏ và một đường chạy câu hỏi đến kết quả. Không cần đợi hoàn thiện mọi nghiệp vụ hoặc đủ hàng chục gold mọi tổ hợp mới được thử NLU.

Các kết luận kỹ thuật đã kiểm chứng được ghi trong [DECISIONS.md](../../DECISIONS.md); phương án triển khai còn là đề xuất. Mã nghiệp vụ, loader, evaluator và dữ liệu gốc không thay đổi trong lượt review này.
