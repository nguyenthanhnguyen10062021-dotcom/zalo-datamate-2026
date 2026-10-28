# Codex kiểm chứng Gemini lượt 04

Ngày: 2026-10-29, Asia/Saigon. Đầu vào `GEMINI_RESPONSE_04.md`, SHA256 `82f93bbf8aebe97af9dcd1b3bbfacdd8763605ac52f882f78cf24404f2dca737`. Giữ nguyên bản gốc. HEAD `2085afa`, nghiệp vụ `1c89252`; production không thay đổi.

## Kết luận

Chấp nhận hướng lazy validation, order filters cho hai API và kiểm tra luật share đúng scope. **Không áp dụng nguyên patch Gemini**: thiếu import exception và có regression do thứ tự lọc. Codex đã tạo [CODEX_BUSINESS_PATCH_04.diff](CODEX_BUSINESS_PATCH_04.diff), sửa các điểm đó trong bản sao tách biệt, giữ baseline để đối chiếu.

Không cần mở lại kiến trúc v1 hoặc chờ người dùng chọn thứ tự thực hiện. Bước tiếp theo là rà bản diff đã chạy, rồi triển khai lát cắt deterministic; chưa coi helper minh họa là NLU hoàn chỉnh.

## Các phiên bản và kiểm chứng mới

Chạy `reports/gemini_round001_review_04.py`: trích đúng 10 hunk từ diff, ghép theo context vào bản sao source; thực thi sáu hàm test từ phản hồi với fixture/rulebook tổng hợp hiện có. Không sửa source baseline hoặc nội dung phản hồi.

| Phiên bản | Sáu test Gemini | Kết quả đáng chú ý |
|---|---:|---|
| Baseline hiện tại | 1/6 pass | Test helper normalize/semantic pass; các test API mô tả phần chưa triển khai. |
| Patch nguyên văn | 5/6 pass | Test reject product filter phát sinh NameError vì chưa import UnsupportedRule. |
| Patch chỉ thêm import | 6/6 pass | Chưa đủ an toàn: ba phản chứng bổ sung đều regression. |
| Bản Codex sửa import, type check và thứ tự lọc | 6/6 pass | Giữ kết quả của ba phản chứng, không bỏ kiểm tra liên quan. |

- Full suite baseline chạy mới: **219 passed, 1 skipped**.
- Full suite chạy mới trên bản Codex sửa, bằng cách nạp module ứng viên trong process kiểm thử riêng: **219 passed, 1 skipped**. Không thay file `business/sales.py`.
- `python reports/.run_reviewed_candidate_tests.py verify`: verifier chạy mới trên ứng viên đạt **409/409 khớp gold và phép tính cũ, 0 lỗi**; chọn 417 câu, legacy bỏ qua 8. Output ở `reports/business_verification_review04_candidate.json`.
- Bộ 409 chỉ đối chiếu revenue/cancelled_orders/quantity theo bộ chọn cũ; không chứng minh filters mới của cancellation_rate/top_customers đúng trên gold hoặc NLU hiểu đúng câu hỏi.
- `git apply --check CODEX_BUSINESS_PATCH_04.diff`: qua. Diff Gemini cũng qua kiểm tra sau `--recount`; không gọi việc chỉnh lại số dòng hunk là lỗi thuật toán.
- Output chi tiết ở `reports/gemini_round001_review_04.json`, verifier và runner nằm trong `reports/`, không gửi dữ liệu train hoặc log từng câu cho Gemini.

## 1. Hai lỗi trong patch

### Thiếu import UnsupportedRule

Baseline `sales.py` chỉ import Rulebook từ `.rules`. Patch thêm hai nhánh `raise UnsupportedRule(...)` nhưng không thêm import. Thực thi nhánh reject product filter gây NameError, không phải UnsupportedRule. Bản Codex sửa import tường minh; không đổi cấu trúc Answer hay thứ tự tham số cũ.

### Thứ tự lọc gây regression

Patch Gemini dời cả loại đơn hủy/trả xuống sau bước kiểm tra channel/payment/customer_group/shift. Nhưng với revenue và các metric chỉ tính đơn hợp lệ, **trạng thái hủy/trả đã xác định là bằng chứng độc lập loại đơn khỏi kết quả**. Không cần biết kênh/thanh toán/nhóm của đơn đó nữa.

| Phản chứng tổng hợp | Baseline | Patch chỉ sửa import | Bản Codex sửa |
|---|---:|---|---:|
| Đơn trả hàng thiếu kênh, hỏi doanh thu online | 100 | DataError | 100 |
| Đơn hủy thiếu thanh toán, hỏi doanh thu COD | 100 | DataError | 100 |
| Đơn trả hàng có khách định danh nhưng thiếu nhóm, hỏi doanh thu VIP | 201 | DataError | 201 |

Thứ tự trong bản Codex:

1. Khi `valid=True`, kiểm tra luật doanh thu và loại ngay các trạng thái **đã biết** là hủy/trả. Trạng thái chưa biết vẫn giữ lại.
2. Lọc các trường cấp đơn, vẫn chặn giá trị thiếu có khả năng ảnh hưởng.
3. Kiểm tra trạng thái trên tập còn lại. Vì vậy đơn kênh khác có trạng thái lỗi được bỏ qua, còn đơn cùng kênh hoặc chưa biết kênh vẫn bị chặn.

Khi `valid=False` (cancellation_rate, cancelled_orders), không áp dụng bước loại hủy/trả. Đã thêm phản chứng: đơn hủy thiếu payment vẫn chặn cancellation_rate theo payment, vì mẫu số tính mọi trạng thái. Không dùng sửa lỗi doanh thu để bỏ đơn khỏi tỷ lệ hủy.

## 2. Kiểm tra cấu trúc còn thiếu

Patch gốc chỉ kiểm tra các key của dict. `tables['mat_hang']=None` vẫn gây TypeError khi gọi metric sản phẩm. Bản Codex kiểm tra cả ba bảng là DataFrame và `cua_hang` là dict, đưa lỗi cấu trúc về DataError rõ ràng. Không biến lỗi cache thành unanswerable.

Lazy validation chỉ bỏ kiểm tra nội dung bảng không phụ thuộc metric; vẫn yêu cầu cấu trúc chuẩn tồn tại. ORPHAN không chặn đếm đơn thuần nhưng chặn metric đọc dòng hàng; catalog trùng khóa không chặn đếm đơn thuần nhưng chặn các phép tra cứu sản phẩm.

## 3. Schema và pipeline helper: tiến bộ nhưng chưa end-to-end

- `$id` đã là URN, nhưng **`$schema` vẫn bị bọc `[https://...](https://...)` trong JSON**, trái với phần mô tả đã sửa. Validator vẫn cảnh báo không nhận diện metaschema và fallback. Bản phản hồi gốc được giữ nguyên; dùng URI thuần trong implementation.
- `product_mentions` có minItems=1 là phù hợp **sau normalize**: [] trở thành null trước structural validation. Đã kiểm tra raw [] bị schema bác, normalized plan được nhận.
- `strict_int` xử lý đúng các ca thử bool, float có phần lẻ, chuỗi số và float nguyên. Helpers không thay thế JSON Schema: chúng dựa vào structural validation đã chạy; gọi riêng không phải API validator hoàn chỉnh.
- `resolve_filters_strict` trả Filters nhưng không resolve/trả lại `unit_mention`. Nếu dispatcher chỉ dùng output helper thì fixture quantity trả **3**; giữ unit='ly' đúng nơi gọi thì trả **2**. Đây là **dependency chưa thể hiện trong helper/dispatcher**, không phải tuyên bố repo đã có một dispatcher trả sai.
- Resolver gộp mọi ID có cùng tên, chưa kiểm tra nhập nhằng theo contract. Fixture hai mã cùng tên nhưng khác đơn vị ly/kg đều được đưa vào product_ids. V1 cần policy rõ để abstain khi không xác định được ý nghĩa gộp; không coi mọi tên trùng là alias chắc chắn.
- Có semantic validator cho tổ hợp operation/type/period là tiến bộ; vẫn chưa có đầy đủ period resolver, capability adapter, dispatcher và log trạng thái để chạy sáu bước end-to-end.

## 4. Cần làm rõ câu về tháng này/tháng trước

Rulebook train §2 có mặc định rõ: so tháng này với tháng trước lấy **cùng số ngày**. Không nên gọi câu thiếu chữ “cùng số ngày” là ambiguous rồi abstain. Khi câu hỏi không ghi khác, áp mặc định đó. Chỉ dùng whole previous_month khi có override rõ, hoặc abstain khi câu hỏi thực sự mâu thuẫn/không xác định được phạm vi.

Đây cũng là chỗ cần sửa cách diễn đạt của các thư Codex trước: “không có căn cứ dùng cả tháng trước” không đồng nghĩa với “không có căn cứ chọn kỳ nào”. Rulebook đã là căn cứ chọn cùng số ngày.

## Trạng thái bàn giao

Patch Codex là artifact review đã chạy trong môi trường tách biệt; chưa áp dụng vào production, chưa commit/push. Nội dung số học/precision không thay đổi. Chưa thêm model, schema production hoặc toàn bộ NLU.

Lazy validation có thể quét lại quan hệ dòng hàng qua nhiều lần gọi; bản diff còn kiểm tra ở cả `_revenue` và `_line_sales`. Chưa benchmark latency inference và chưa dùng cache validation vì các DataFrame đầu vào có thể bị sửa. Không tuyên bố patch cải thiện tốc độ.

Gửi Gemini [CODEX_REPLY_TO_GEMINI_04.md](CODEX_REPLY_TO_GEMINI_04.md), review này và diff; dùng [GEMINI_PROMPT_05.md](GEMINI_PROMPT_05.md). Lượt sau tập trung phản chứng cho bản đã sửa và contract resolver còn thiếu, không lặp lại patch nguyên bản.
