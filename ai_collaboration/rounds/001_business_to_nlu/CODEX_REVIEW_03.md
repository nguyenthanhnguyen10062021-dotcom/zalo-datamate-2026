# Codex kiểm chứng Gemini lượt 03

- Ngày: 2026-10-29, Asia/Saigon.
- Đầu vào: `GEMINI_RESPONSE_03.md`; giữ nguyên bản gốc, SHA256 `e6283020e3002f40de6d4534f3f189324c32befab132883d5b1935195d5b55f0`.
- HEAD `2085afa`, code nghiệp vụ `1c89252`. Chưa sửa production, requirements hoặc tạo tầng NLU.

## Kết luận và quyết định kỹ thuật

Phản hồi 03 đủ để thống nhất phạm vi baseline: public API trực tiếp; hoãn boolean/raw result và parent-share; giữ nguyên mặc định mẫu số cả shop; validation theo dependency nhưng không bỏ dòng mồ côi khi metric cần dòng hàng. Không cần hỏi lại người dùng các lựa chọn này.

Chưa thể dùng nguyên schema và bảng dispatch để triển khai. Cần sửa URI, chốt bước kiểm tra ngữ nghĩa, đồng bộ chữ ký API và bỏ bảo đảm precision quá mức. Các lỗi dưới đây đã được phân biệt với những phần Gemini chủ ý giao cho semantic validator.

## Kiểm chứng đã chạy

- `python reports/gemini_round001_review_03.py`: **19 trường hợp schema**, **3 test dependency lấy từ phản hồi Gemini**, **2 lời gọi API trong bảng dispatch**, và các phản chứng precision. Output ở `reports/gemini_round001_review_03.json`, chỉ lưu local.
- Validator thật: **jsonschema 4.26.0**, cài riêng ở `reports/.review_tools`; không thêm dependency production. Thư viện tạm ban đầu nằm trong thư mục pytest có thể quét, khiến thu nhầm test của thư viện; đã chuyển sang thư mục ẩn để cô lập.
- Sau khi cô lập thư viện, `python -m pytest -q -rs`: **219 passed, 1 skipped**. Skip vẫn là helper evaluator tìm gold dưới sai thư mục.
- Không chạy lại verifier 409 câu trong lượt này: production không thay đổi. Lượt 02 đã chạy mới và khớp 409/409; không trình bày con số đó như một lượt chạy mới của lượt 03.
- Sáu test validator/dispatcher trong phản hồi là bản đặc tả: repo chưa có các hàm/fixture tương ứng, nên chưa có căn cứ nói chúng pass end-to-end.

## 1. Schema: kết quả thực tế, không chỉ đọc bằng mắt

### URI trong bản gốc

JSON parse được, nhưng `$schema` và `$id` đang có dạng `[https://...](https://...)` bên trong chuỗi. Đây là cú pháp Markdown, không phải URI tuyệt đối cần dùng ở các trường đó.

Điểm cần mô tả chính xác: **`Draft202012Validator.check_schema` không bác bản gốc trong môi trường kiểm tra này**. Tuy nhiên `validator_for(schema)` cảnh báo không tìm thấy metaschema đã khai báo và fallback sang draft mới nhất; cảnh báo cho biết hành vi đó sẽ thành lỗi trong tương lai. Không được gọi đây là xác nhận `$schema` gốc đã được nhận diện đúng draft.

Để chẩn đoán phần còn lại, harness chỉ đổi hai chuỗi sang URI thuần trong một bản sao local, giữ nguyên bản phản hồi. `$id` không phải bằng chứng có endpoint chính thức của dự án; có thể dùng một URN nội bộ thay vì ngụ ý domain đang phục vụ schema.

### Những gì schema cấu trúc bắt và chưa bắt

| Trường hợp | Kết quả với bản sao đã sửa URI | Ý nghĩa |
|---|---|---|
| revenue hợp lệ; unsupported hợp lệ | Nhận | Mới đúng cấu trúc, chưa chứng minh thực thi đúng. |
| Field lạ ở gốc/lồng nhau; thiếu required | Bác | `additionalProperties` và `required` hoạt động. |
| `ranking.k=true`; `k=0` | Bác | Đề xuất loại bool là đúng. |
| `ranking.k=1.0` | **Nhận** | JSON Schema coi số có phần lẻ bằng 0 là integer; public `_rank` yêu cầu `type(k) is int`, nên phải thống nhất reject hoặc canonicalize trước dispatch. Không âm thầm ép 1.2 thành 1. |
| unit trên revenue; expected_type sai; supported nhưng operation=null hoặc reason khác null | Nhận | Gemini đã giao các điều kiện này cho semantic validator. Đây là bằng chứng cần triển khai tầng đó, không phải phản chứng rằng toàn bộ thiết kế không thể bắt lỗi. |
| `today/this_month` mang n không dùng | Nhận | Cần semantic validator kiểm tra field không dùng. |
| `2026-02-31`; start sau end | Nhận | Regex chỉ kiểm tra hình thức ngày. Phải parse ngày thực và tạo DateRange; so sánh hai chuỗi ngày không đủ. |
| product_mentions=[]; mention chỉ có khoảng trắng | Nhận | Cần contract resolver rõ: v1 chọn canonicalize [] về null, trim và reject mention rỗng; không tạo Filters(product_ids=()) rồi trả 0 ngầm. |

Tổng số trường hợp chạy là 19, bao gồm case current-month so full previous-month. Case cuối chỉ đúng theo ý câu hỏi khi có yêu cầu rõ; mặc định rulebook cho so tháng này/tháng trước là cùng số ngày. Có hai kind khác nhau là tiến bộ nhưng không tự chứng minh NLU chọn đúng. Khi thiếu bằng chứng chọn kỳ, trả abstain thay vì tự suy thành cả tháng trước.

`before_period` cũng cần giới hạn: `Periods.before()` hiện kiểm tra điều khoản **trước Tết**. Với v1, chỉ dùng kind đó cho period=Tết; các khoảng ngày liền trước khác phải có chính sách riêng hoặc date_range đã có căn cứ, không viện điều khoản Tết cho mọi kỳ.

## 2. Dependency và public API

Đã thực thi nguyên ba test ở mục 1.4 bằng fixture hiện hành và rulebook train:

1. ORPHAN vẫn làm constructor DataError trước khi order_count chạy được.
2. Khóa sản phẩm trùng vẫn làm constructor DataError trước khi metric cấp đơn chạy được.
3. Trạng thái lỗi của đơn ở kênh khác vẫn làm cancelled_orders DataError trước khi lọc được kênh.

Đây là **ba test mô tả hành vi đích chưa đạt trên baseline**, không phải ba lỗi trong ý tưởng test. Hướng lazy validation có cơ sở; khi sửa phải giữ việc ORPHAN chặn revenue và catalog hỏng chặn metric phụ thuộc catalog. Kiểm tra cấu trúc cache vẫn thuộc adapter/constructor; lỗi cấu trúc không được đổi thành unanswerable.

Bảng dispatch chưa khớp code:

- `cancellation_rate(p, f)` → **TypeError**; hiện chỉ nhận period.
- `top_customers(..., filters=f)` → **TypeError**; hiện chưa có tham số filters.

Cần đánh dấu đây là **API dự kiến sau patch**, không phải 10 operation đều gọi được ngay. Trong v1, chỉ hỗ trợ filter cấp đơn cho hai API đó; reject filter sản phẩm cho đến khi có contract riêng. Với `top_customers(metric='revenue')`, ý nghĩa filter sản phẩm vẫn cần phân định “doanh thu của khách từ sản phẩm đó” với “toàn bộ doanh thu của khách từng mua sản phẩm đó”; v1 không suy luận thay câu hỏi.

## 3. Precision: thu hẹp thay đổi là đúng, prec=28 không phải định lý

Đồng ý hoãn raw_decimal/boolean; giữ Answer hiện hành và làm tròn tại đầu ra. Sáu chữ số quantity là hành vi đang có, chưa được biến thành khẳng định rằng rulebook bắt mọi tổng quantity phải có sáu chữ số.

Hai phản chứng tổng hợp với công thức đề xuất:

- Gọi `num = 1005*10**30 - 1`, `den = 100000*10**30`. Tính phần trăm bằng Decimal prec=28 rồi half-up hai chữ số cho **1.01**; đối chiếu số hữu tỷ chính xác cho **1.00**. Việc nhân 100 trước chia không tự bảo đảm chỉ làm tròn một lần: nhân/chia/cộng Decimal cũng chịu context.
- Nhân chéo bằng Decimal cũng chịu context: với A=`10**30+1`, C=`10**30`, B=D=1, ở prec=28 thì A*D và C*B bị coi bằng nhau. Dùng số nguyên chính xác thì A>C.

Đây là số tổng hợp cực lớn, **chưa phải lỗi đã quan sát trên train**. Không đề nghị đổi toàn bộ numeric engine chỉ vì phản chứng này. Quyết định v1: giữ baseline đang kiểm chứng; không thêm recipe “prec=28 bảo đảm chính xác” vào contract. Nếu mở rộng miền dữ liệu, phải đặt giới hạn được kiểm tra hoặc dùng scaled integer/rational cho bước làm tròn cuối. Không đổi cách tính tỷ lệ production nếu chưa có test và lý do cụ thể.

## 4. Share, unanswerable và nguồn chứng cứ

Chấp nhận v1 chỉ share cả shop, reject mẫu số tập con. Kiểm tra luật nhóm khách khi filter đó được dùng; phần service fee trong mẫu số cả shop vẫn phải được giữ. Không biến thiếu field denominator thành bằng chứng model đã hiểu đúng câu hỏi: câu hỏi đòi parent-share phải thành unsupported.

Phần v1.1 hiện nói cả “giao hai scope” lẫn “reject khi không subset” là hai chính sách khác nhau: giao hai tập xung đột có thể là rỗng, không nhất thiết lỗi. Có thể chọn reject như một giới hạn, nhưng phải gọi đúng tên; hoãn khỏi v1 nên không cần tiếp tục mở rộng nó lúc này.

Public API chuyển `_Unavailable` thành `Answer('unanswerable')` để đóng gói, nhưng **không tự chứng minh mọi unanswerable là đáp án đúng**. Ví dụ mã sản phẩm bịa từ model cũng có thể dẫn tới Answer đó trên baseline. Pipeline chỉ giữ known-unanswerable sau khi đã kiểm tra thực thể/capability; lỗi schema, resolver, luật chưa hỗ trợ hoặc dữ liệu chuẩn hỏng phải có trạng thái lỗi riêng và kết thúc abstain. Không bắt exception private từ dispatcher.

Các `[cite: n]` trong phản hồi là ký hiệu từ giao diện Gemini, không phải liên kết nguồn có thể mở trong repo. Giữ nguyên bản gốc, nhưng lượt sau đề nghị dùng `file:section` hoặc permalink source thực và ghi rõ nội dung nào chỉ là kết quả Codex báo cáo.

## 5. Bước tiếp theo đã chọn

Không cần tiếp tục mở rộng v1 hoặc chờ người dùng chọn lại. Thứ tự kỹ thuật:

1. Chốt contract tối thiểu theo các giới hạn trên; chuẩn hóa numeric/mention/date và phân biệt cấu trúc với ngữ nghĩa.
2. Sửa dependency validation và hai API thiếu order filters bằng các test đích; sửa require của share đúng scope. Chưa tuyên bố đã thực hiện các patch này trong lượt review.
3. Dựng deterministic plan executor và chạy corpus schema + semantic + integration độc lập, rồi verifier hiện có. Không gọi lời gọi API tương đương là thành công của NLU.

Lượt gửi Gemini tiếp tập trung rà contract và test cần thiết cho patch nhỏ, không hỏi lại kiến trúc hay chọn model. Gói mới ở `CODEX_REPLY_TO_GEMINI_03.md` và `GEMINI_PROMPT_04.md`.
