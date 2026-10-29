# DataMate — Khảo sát dữ liệu & đề xuất thiết kế loader

Nguồn: `survey_raw.md` (sinh bởi `survey.py`, 44 tiệm, 208 file), README của mọi tiệm, `train/rulebook.md`, `public_test/rulebook.md`, `train/questions.jsonl` + `answers.jsonl`.

## 0. Năm phát hiện quan trọng nhất

| # | Phát hiện | Hệ quả thiết kế |
|---|---|---|
| 1 | **Tên cột thay đổi tuỳ tiện nhưng mô tả cột trong README dùng một bộ từ vựng cố định.** Ví dụ "thành tiền sau giảm" ứng với 15+ tên cột khác nhau (`Thanh tien`, `Trị giá`, `Amount`, `T.Tiền`, `Cộng`, `Tiền bán`…). Toàn bộ README có ~175 mô tả khác nhau, 40 mô tả phổ biến nhất phủ gần hết các cột. | Ánh xạ cột **theo mô tả README**, không theo tên cột. Đây là chìa khoá để xử lý tiệm mới (mục e). |
| 2 | Bộ test có **4 mẫu file mới**: sửa xe (dev_012), điện thoại (dev_011, dev_014), mẹ & bé (dev_013), chi tiết hoá đơn phẳng nhiều cột (dev_007, dev_008). Rulebook public test có **thêm 3 ngành** (Mẹ & bé, Sửa xe, Điện thoại) và ~12 luật mới. | Schema phải có chỗ cho phiếu dịch vụ, IMEI, trả góp, thu máy cũ, voucher/điểm, bảo hành. Luật mới (giờ cao điểm, khách sộp…) cần thêm `thoi_diem_dat` và `ma_nhan_vien`. |
| 3 | Có **dòng tổng theo ngày** xen giữa dữ liệu (`Tổng ngày 01/04`, `Cộng ngày 01/05/2025`, `TỔNG NGÀY 01/02`), có số tiền ở cột thành tiền. Có ở 10/44 tiệm. | Không lọc thì doanh thu bị tính gấp đôi. Đây là bước làm sạch bắt buộc. |
| 4 | Trạng thái đơn có ~40 cách viết. **Đã kiểm chứng bằng đáp án:** biz_124 `Không giao được` = **huỷ** (tỉ lệ huỷ 30/3237 = 0,93% khớp đáp án tháng 1/2026; 31/2933 = 1,06% khớp tháng 9/2025). | Cần bảng chuẩn hoá trạng thái dùng chung, có kiểm thử. |
| 5 | 70/3000 câu train là unanswerable, chia 3 kiểu: kỳ hỏi nằm ngoài khoảng dữ liệu; tiệm không ghi loại thông tin cần (tồn kho, giá nhập, địa chỉ/giới tính khách, lý do huỷ…); câu chủ quan ("nhân viên lễ phép không"). | Loader phải xuất **metadata năng lực** của từng tiệm: khoảng ngày có dữ liệu và loại thông tin có/không có. |

---

## a. Nhóm mẫu file

| Nhóm | Mô tả cấu trúc | Train | Test | Ngành |
|---|---|---|---|---|
| **A. POS kiểu KiotViet** | `DanhSachHoaDon` + `DanhSachHoaDonChiTiet` + `DanhSachSanPham` + `DanhSachKhachHang` + `BaoCaoTonKho` + `DanhSachNhapHang` + `DanhSachChiTietNhapHang`; tuỳ tiệm thêm `SoQuy` (thu tiền), `DanhSachDonViTinh`, `DanhSachLoHang` + `DanhSachHoaDonChiTietLo` + `DanhSachThuoc` (nhà thuốc), `DanhSachHoaDonPhongBan` (bàn). Nối qua mã. | biz_106, 108, **109** (mọi danh sách gộp vào 1 file nhiều sheet), 119, 120, 128 | — | cafe, tạp hoá, nhà thuốc, nhà hàng |
| **B. Xuất "DonHang_ChiTiet"** | `DonHang_ChiTiet` (mỗi dòng 1 sản phẩm, **không có mã hàng**, nối qua tên) + `DanhSachQuyDoi`; nhà thuốc thêm `DanhSachSanPham`, `DanhSachThuoc`, `DonNhapHang(_ChiTiet)`, `DonHang_Lo` | biz_102, 103, 104, 121 (gộp `DuLieuXuat.xlsx`), 122 | dev_002 (**mỗi tháng một file**), dev_005 (mỗi tháng một file, quy đổi nhiều cấp) | tạp hoá, cafe, nhà thuốc |
| **C. "Sổ chi tiết bán hàng" (kiểu MISA)** | `So_chi_tiet_ban_hang` (sheet theo tháng, số dạng `45,000.0000`) + `Danh sách hàng hóa`; VLXD thêm `Bảng kê phiếu giao hàng` + `Chi tiết công nợ theo hạn` | biz_112, 115, **116** (4 danh sách gộp 1 file), 118, 130 | dev_001 | cafe, VLXD, nhà hàng, tạp hoá |
| **D. Sổ tay nhiều file** | `SoBanHang` (sheet theo tháng) + `DanhMuc` (quy đổi) + `TonKho` + `SoNhapHang` + `BangGia`; VLXD thêm `SoGiaoHang`, `SoHanNo`. Trả hàng ghi **số lượng âm**. | biz_105, 117 | dev_004 | cafe, VLXD |
| **E. Sổ bán 1 sheet, không mã đơn, không tên khách** | Một file `SoBanHang.xlsx`, một sheet | biz_107, 113, 126 | — | tạp hoá, nước/gas, nhà hàng |
| **F. CSV phẳng 1 file** | `ban_hang.csv`, mỗi dòng 1 dòng hàng, có mã đơn và tên khách | biz_101, 114, 125 | — | tạp hoá, VLXD, nhà hàng |
| **G. Chỉ có danh sách hoá đơn** | `danh_sach_hoa_don.csv`, mỗi dòng một đơn, **không có dòng hàng** | biz_110 | dev_009 | ? |
| **H. CSV quan hệ** | `don_hang` + `chi_tiet_don` + `san_pham` + `khach_hang` + `thanh_toan`, nối qua mã | biz_111, 127, 129 | dev_010 (thêm phí vận chuyển, giảm giá đơn) | cafe, nhà hàng, mẹ & bé |
| **I. SQLite POS** | `pos.sqlite`, 17 bảng (`don_hang`, `chi_tiet_don`, `the_kho`, `lo_hang`, `tra_hang`, `lich_su_gia`…) | biz_123 | dev_006 | nhà thuốc |
| **J. Đa nguồn** | `BanHang_*` (phần mềm) + `SoTay_*` (sổ tay: chi phí, nhập hàng) + `ton_kho.csv` | biz_124 | dev_003 (biến thể: hoá đơn + chi tiết **gộp 1 sheet**, tách theo năm, thêm `BaoCaoCa`) | nhà thuốc, cafe |
| **K. Chi tiết hoá đơn phẳng nhiều cột** 🆕 | 1 bảng ~30 cột: đơn, khách, bàn, khu vực, kênh, NV, giảm giá đơn, phí ship, nợ lặp ở mọi dòng + `danh_muc_hang` (kèm tồn) + `chi_tiet_nhap_hang` | — | **dev_007** (csv), **dev_008** (xlsx, nợ ghi trong ô `Note`) | nhà hàng |
| **L. Sổ cửa hàng điện thoại** 🆕 | Sheet `Ghi tắt` + sổ bán (STT đơn, IMEI, Bớt, Thu máy cũ); dev_014 thêm `SoNo.xlsx` (Sổ nợ, Trả góp, Bảo hành) + `ThuMayCu.xlsx` | — | **dev_011**, **dev_014** | điện thoại |
| **M. Sổ sửa xe** 🆕 | `SoSuaXe` (sheet theo tháng: Ngày, Xe = "dòng xe + biển số", Làm gì, Thợ, Tiền) + `DanhSachTho` (hoa hồng %) | — | **dev_012** | sửa xe |
| **N. Sổ mẹ & bé** 🆕 | `BanHang_<năm>` (sheet theo tháng, **header gộp 2 dòng**, dòng `Voucher`/`Dùng n điểm`/`Phí ship`, trạng thái nằm trong ghi chú) + `QuanLy.xlsx` (DanhMuc kèm tên gọi khác, hãng, số/size; KhachHang thành viên; NhapHang; KhuyenMai) | — | **dev_013** | mẹ & bé |

**Tiệm test có mẫu mới, không có trong train:** dev_007, dev_008 (K), dev_011, dev_014 (L), dev_012 (M), dev_013 (N). Mẫu đã có trong train nhưng thêm biến thể mới: dev_002, dev_005 (dữ liệu tách mỗi tháng một file), dev_003 (hoá đơn + chi tiết gộp chung sheet), dev_010 (sản phẩm mẹ & bé, có phí ship).

---

## b. Các kiểu dữ liệu bẩn

| # | Kiểu bẩn | Ví dụ thật | Tiệm | Xử lý đề xuất |
|---|---|---|---|---|
| 1 | Header lệch dòng (dòng tiêu đề / ghi chú phía trên) | header ở dòng 1–3 | lệch 1: biz_105, 117, dev_004, 012, 013, 014 · lệch 2: biz_103, 106 (HoaDon), 118 (công nợ), 121, 122, 124 (SoTay), dev_003 (SoTay) · lệch 3: biz_112, 118 (giao hàng), 130, dev_001, 002, 005 | Tìm dòng đầu tiên mà ≥ 70% ô có giá trị là nhãn chữ (cách `survey.py` đang làm), đối chiếu với tên cột trong README |
| 2 | Header gộp 2 dòng | `BanHang_<năm>`: nhóm "Hàng hoá", "Tiền" ở dòng trên | dev_013 | Ghép 2 dòng header; lấy tên ở dòng dưới |
| 3 | **Header lặp lại giữa dữ liệu** | dòng `Mã đơn hàng \| Ngày đặt hàng \| …` lặp lại | dev_002 (25 lần/file), dev_010 `chi_tiet_don` (226 lần) | Bỏ mọi dòng giống hệt header |
| 4 | **Dòng tổng theo ngày** | `Tổng ngày 01/04` (cột khách) + `5,606,000` · `Cộng ngày 01/05/2025` · `TỔNG NGÀY 01/02` (cột tên hàng) | biz_104, 107, 110, 130, dev_001, 002, 007, 008, 009, 010 | Bỏ dòng có ô chữ khớp `^(tổng\|cộng)( ngày)?` (không phân biệt hoa thường) **và** thiếu mã đơn. Có thể dùng chính các dòng này để **kiểm tra tổng** sau khi nạp |
| 5 | Dòng tổng cuối sheet | 1 dòng `Tổng/Cộng` | biz_105, 117, dev_014 | Như trên |
| 6 | Nhiều sheet theo tháng | `T01_2025`, `04.2025`, `Thang 02 2025`, `Tháng 01-2025`, `T7-2025` | biz_102, 103, 105, 112, 115, 117, 118, 119, 120, 122, 128, dev_004, 012, 013, 014 | Nối các sheet cùng header; **giữ tên sheet** vì cần để suy ra năm |
| 7 | Nhiều file theo tháng / năm / số dòng | `BanHang_T1_2025.xlsx` (17 file) · `_1`/`_2026` · `_1` có **đúng 100.000 dòng** | theo tháng: dev_002, 005 · theo năm: biz_105, 112, 122, dev_003, 013 · theo số dòng: biz_106, 122 (Lo), 130, dev_008 | Gom theo mẫu tên file. Một đơn có thể **vắt qua 2 file** (biz_130), nên điền xuống và khử trùng sau khi nối |
| 8 | Nhiều danh sách gộp 1 file nhiều sheet | `DuLieuBanHang.xlsx` (8 sheet), `Bao_cao_ban_hang.xlsx`, `DuLieuXuat.xlsx`, `QuanLy.xlsx` | biz_109, 116, 121, dev_003, 013 | Mỗi sheet là một bảng nguồn; README ghi rõ sheet nào là danh sách nào |
| 9 | Số dạng chuỗi có dấu phân cách | `560,000` · `45,000.0000` · `129 000` (khoảng trắng) | phẩy: hầu hết · `.0000`: nhóm C · khoảng trắng: dev_007 | `parse_number`: bỏ khoảng trắng, nhận diện phân cách nghìn theo mẫu `\d{1,3}([.,  ]\d{3})+` |
| 10 | Cùng một cột lẫn số và chuỗi | `Giá sản phẩm`: 3341 ô int + 3333 ô `"38,000"` | biz_102, 103, 104, 114, 119–122, 125, 126, dev_002, 005, 009 | Parse từng ô, không suy kiểu theo cột |
| 11 | Tiền kèm đơn vị / viết tắt | `38.000đ`, `38k`, `1tr440`, `16,56tr`, `1,84tr`, `25000k`, `11,067tr`, `19tr990`, `20,1tr`, `0đ`, `-53.500đ` | biz_105, 117, 122, 124, 126, 127, 129, dev_002, 003, 004, 007, 008, 012, 013, 014 | Quy tắc: `k` = ×1.000; `tr` = ×1.000.000; `XtrYYY` = X triệu + YYY nghìn (`1tr440` = 1.440.000, `26tr220` = 26.220.000); dấu `,` trước `tr` là thập phân (`16,56tr`). **Đã kiểm** ở biz_117: `Giá × SL = Tiền` khớp 33.122/33.805 dòng (98%); 2% lệch là dòng có giảm giá (~5%), không phải lỗi parse |
| 12 | Ngày nhiều dạng **trong cùng một cột** | `01/02/2025` · số serial Excel `45689` · `1 thg 6 2025` · `2025-01-01` · datetime | serial: biz_105, 106, 107, 109, 111 (cả trong CSV), 117, 123, 124, dev_003, 006, 007, 012, 013, 014 · `thg`: biz_101, 111, 117, 123, 124, dev_003, 004, 013 | `parse_date`: datetime → giữ; số 30000–60000 → `1899-12-30 + n`; `d thg m yyyy`; `dd/mm/yyyy` (**luôn dayfirst**); ISO |
| 13 | Ngày không có năm | `1/1`, `4/1` | biz_117, dev_004, dev_013 | Lấy năm theo tên sheet (rulebook §8) |
| 14 | Số lượng kèm đơn vị | `3 chai`, `1 hộp`, `2 cái` (khoảng một nửa số ô) | biz_102, 103, 107, 111, 112, 114–117, dev_001, 002, 004, 005, 008, 010 | Lấy số đứng đầu; nếu chữ đơn vị khác cột ĐVT thì ghi cảnh báo |
| 15 | Quy đổi ghi bằng chữ / nhiều cấp | `1 thùng = 4 bịch` · `1 lốc = 4 gói; 1 thùng = 24 gói` · hệ số `2 vỉ` (theo đơn vị ngay dưới) · README liệt kê `1 lốc = 6 lon` | dev_013, dev_005; README của biz_101, 107, 111, 112, 113, 114, 119, 125, 128, dev_001, 007, 008, 010 | Parse README + bảng quy đổi về **hệ số so với đơn vị cơ bản** (nhân dồn theo cấp) |
| 16 | **Ô trống ở các dòng sau của cùng đơn** | 4 cột đầu (mã, ngày, trạng thái, khách) chỉ ghi ở dòng đầu đơn | biz_103 (60%), 121 (47%), 122 (47%), dev_004 (51%), 005 (47%), 011 (37%), 014 (sổ nợ / trả góp 50–80%) | Điền xuống (forward fill) **chỉ các cột cấp đơn**, trong phạm vi một sheet |
| 17 | Dòng trùng hoàn toàn | POS: `ORD000027 \| 1 \| SP0046 \| Topping…` x2 | trong đơn: biz_106 (2496), 119, 123, 124, 127, 128, 129, dev_003, 006, 007, 008, 009, 010 · sổ không theo đơn: biz_107 (5756), 113 (5285), 126 (5713) | §8: dòng trùng **trong cùng đơn** thì tính 1 lần; bảng **không ghi theo đơn** (nhóm E) thì giữ cả hai. Khử trùng **sau** bước điền xuống (biz_121 báo 35.380 "dòng trùng" chỉ vì ô trống chưa được điền) |
| 18 | Trạng thái nhiều cách viết | xem bảng chuẩn hoá ở mục c | mọi tiệm | Bảng ánh xạ cố định + fallback theo từ khoá |
| 19 | Trạng thái nằm trong ghi chú | `Huỷ`, `cancel` · `trả lại hàng`, `khách mang trả` | dev_013, dev_011, dev_014 | Luật public test: sổ không có cột trạng thái thì ghi chú không nhắc trạng thái nghĩa là hoàn thành |
| 20 | Trả hàng = dòng số lượng âm | `Trị giá -53.500đ`, cùng mã đơn | biz_105, 117, dev_004 | Đơn có dòng âm là đơn trả hàng; `Giờ` của dòng âm là **giờ trả**, không phải giờ đặt (README biz_105) |
| 21 | Trả hàng nằm ở bảng lô | `Số lượng trả > 0` | biz_119–124, dev_005, 006 | Đơn có lô trả > 0 là đơn trả hàng (README) |
| 22 | Khách lẻ nhiều cách viết | `Khách lẻ`, `khách lẻ`, `lẻ`, `kl` | hầu hết | Danh sách nhận diện khách lẻ |
| 23 | Tên khách kèm số điện thoại | `Nguyễn Văn A (0900000001)`, `Trần Thị B 0900000002`, `Lê Văn C - 0900 000 003` | biz_106, 108, 111, 120, dev_003, 007, 008, 010, 011, 014 | Tách SĐT ra cột riêng; giữ chuỗi gốc làm alias (đáp án nhận tên kèm SĐT) |
| 24 | Tên hàng / tên khách nhiều cách viết | `PEPSI 330ML` · `Panadol Extra Hộp 15 Vỉ X 12 Viên` · `Ca phe muoi (M)`, `Ngo Nam Dung` (mất dấu) · `Rau  muống` (2 khoảng trắng) · biz_109: 131 tên cho 60 mã | biz_109, 119, 120, 121, 124, dev_002, 003, 007, 008 | Nối theo **mã** nếu có; nếu không thì so theo khoá chuẩn hoá (hoa thường, khoảng trắng, bỏ dấu khi khớp duy nhất). **CHƯA CHẮC:** tên mất dấu có phải "chỉ khác cách viết" theo §3 không. Ở biz_101, 114, 125 không có xung đột khi bỏ dấu |
| 25 | Hàng ghi tắt | `Cáp C-L`, `IP16 128 đen`, `CL 9D` | dev_011, dev_014 | Tra sheet `Ghi tắt` |
| 26 | Topping ghép chung ô với món | `Trà sữa (M) + 2 Trân châu (10.000)` | dev_002 | Tách thành dòng topping riêng (luật public test) |
| 27 | Dòng không phải hàng trong chi tiết | `Phí phục vụ` · `Voucher`, `Dùng 50 điểm`, `Phí ship` | nhà hàng: biz_125–130, dev_007, 008 · dev_013 | Gắn `loai_dong`; tính vào doanh thu theo luật, không xếp hạng |
| 28 | Ô gộp nhiều thông tin | `future 59B6-219.16` (dòng xe + biển số) · `bdtq + vs nồi` · thợ `A.Đức` / `a Đức` / `Đức` · 2 IMEI ngăn bằng ` / ` | dev_012, dev_011 | Regex biển số; tách việc theo `+`/`,`; chuẩn hoá tên thợ về `DanhSachTho` |
| 29 | Mã có khoảng trắng thừa | `" ORD000002"` | dev_003 (PhieuThu) | Strip mọi mã |
| 30 | Ô lỗi Excel | `#VALUE!`, `#N/A` | dev_003, dev_007 | Coi là rỗng |
| 31 | Cột rỗng hoàn toàn | `Trạng thái HĐĐT`, `Giới tính`, `Email`, `CCCD` (README ghi "cột trống, không có dữ liệu") | hầu hết POS, dev_007, 008 | Không ánh xạ; đánh dấu thông tin đó là **không có** để trả lời unanswerable |
| 32 | Mã bàn nhiều dạng | `Bàn 05` / `05` / `B05` · `Bàn 12` / `B7` | dev_007, dev_008 | Chuẩn hoá về `B<số>` |
| 33 | Nợ ghi bằng chữ | `nợ 79k, khách ck đủ rồi`, `nợ 611 nghìn, khách ck đủ rồi` | dev_008 | Parse ô `Note`; **CHƯA CHẮC** về đủ các mẫu câu |
| 34 | Tồn kho chỉ có ảnh chụp cuối kỳ | `Tồn cuối kỳ` = tồn hết ngày cuối dữ liệu | mọi tiệm có tồn, trừ SQLite (có `the_kho`) | Tồn ngày D = tồn cuối − nhập sau D + bán sau D (± trả). **CHƯA CHẮC** hàng trả có về kho hay không ở tiệm không phải nhà thuốc |
| 35 | Phiếu nhập không có giá | `DonNhapHang_ChiTiet` chỉ có SL cơ bản, lô, hạn | biz_121, 122, dev_005 | `don_gia_nhap` để trống, nên câu hỏi giá nhập là unanswerable (khớp đáp án biz_122) |

---

## c. Schema chuẩn

Quy ước: kiểu `str/int/float/date/datetime/bool`; **B** = bắt buộc (thiếu thì loader báo lỗi), **T** = tuỳ chọn (tiệm không có thì để `NULL`, **không suy ra**, theo §7). Tiền là số nguyên VND. Số lượng cơ bản dùng `float`.

### c.1 Metadata tiệm (dùng cho unanswerable)

| Bảng `cua_hang` | Kiểu | B/T | Ý nghĩa |
|---|---|---|---|
| business_id | str | B | |
| nganh | str | T | cafe / tap_hoa / vlxd / nha_thuoc / nha_hang / me_be / dien_thoai / sua_xe (suy từ README/danh mục; **CHƯA CHẮC** cách suy tổng quát) |
| ngay_ket_thuc_du_lieu | date | B | Dòng "Dữ liệu có đến hết dd/mm/yyyy" trong README (44/44 tiệm có dòng này) |
| ngay_bat_dau_du_lieu | date | B | Ngày nhỏ nhất trong dữ liệu bán. **CHƯA CHẮC:** lấy theo đơn bán hay theo mọi bảng (phiếu nhập đầu kỳ thường sớm hơn) |
| co_ma_khach, co_ma_hang, co_ma_don | bool | B | Quyết định cách xác định khách (§3) và cách tính số đơn |
| nang_luc | set[str] | B | Loại thông tin có thật: `dong_hang`, `gio_dat`, `thanh_toan`, `con_no`, `han_no`, `nhap_hang`, `gia_nhap`, `ton_kho`, `the_kho`, `lo_hang`, `gia_von_dong`, `bang_gia`, `chi_phi`, `giao_hang`, `kenh_ban`, `hinh_thuc_tt`, `nhom_khach`, `dia_chi_khach`, `nhan_vien`, `ban`, `ly_do_tra`… Câu hỏi cần loại thông tin không có trong tập này thì trả lời unanswerable |

### c.2 Bảng giao dịch bán

**`don_hang`** (một dòng một đơn / phiếu)

| Cột | Kiểu | B/T | Ý nghĩa · luật dùng |
|---|---|---|---|
| ma_don | str | B* | *Nhóm E không có mã đơn: tự sinh mã mỗi dòng, `co_ma_don = false`, câu hỏi theo đơn coi là không trả lời được (**CHƯA CHẮC**, train không có câu "số đơn" cho biz_107, 113, 126) |
| ngay_dat | date | B | §1 kỳ theo ngày đặt |
| thoi_diem_dat | datetime | T | Ca sáng/chiều, giờ cao điểm. **Không lấy** giờ của dòng trả hàng |
| trang_thai | enum{hoan_thanh, huy, tra_hang, dang_giao} | B | Chuẩn hoá từ `trang_thai_goc` |
| trang_thai_goc | str | B | Giữ để debug |
| ma_khach | str | T | §3 "Shop có mã khách" |
| ten_khach | str | T | Tên đã bỏ SĐT; chỉ lấp tên thiếu từ danh mục khi mã khách khớp duy nhất. Giữ tên trên đơn, `ten_khach_goc`, định danh và phân loại khách lẻ; không suy tên khi thiếu mã hoặc khóa danh mục trùng |
| ten_khach_goc | str | T | Chuỗi nguyên văn, dùng làm alias đáp án |
| la_khach_le | bool | B | |
| nhom_khach | str | T | Lấy từ đơn hoặc từ `khach_hang` |
| kenh_ban | str | T | store / zalo_oa / phone / Tại tiệm / Zalo / Sàn TMĐT |
| hinh_thuc_tt | enum{tien_mat, chuyen_khoan, vi_dien_tu, cod, ghi_no} | T | §1, §4 (COD không phải nợ) |
| ma_nhan_vien | str | T | Nhân viên bán / thợ |
| tong_tien_hang | int | T | Trước giảm giá đơn (dùng để kiểm tra chéo) |
| giam_gia_don | int | T | Không trừ vào doanh thu (§1) |
| phi_giao | int | T | Không tính doanh thu; có tính vào nợ (§4) |
| tong_phai_tra | int | T | Số khách phải trả cả đơn (§4) |
| con_no_cuoi_du_lieu | int | T | Khi tiệm chỉ ghi số còn nợ, không có lịch sử thanh toán (biz_108, 110, 119, 120, 128, dev_007, 008, 009). Train **không có** câu hỏi nợ nào cho 5 tiệm train này, nên chưa có bằng chứng. **CHƯA CHẮC:** đề xuất chỉ dùng khi ngày hỏi là ngày cuối dữ liệu, ngày khác thì trả lời unanswerable |
| ma_ban, khu_vuc, so_khach | str/str/int | T | Nhà hàng |
| ma_khuyen_mai, ghi_chu | str | T | |
| thu_may_cu | int | T | Điện thoại; không trừ doanh thu |
| la_bao_hanh | bool | T | Sửa xe: phiếu bảo hành (tiền = 0) |
| nguon | str | B | file / sheet / dòng, để truy vết |

**`dong_hang`** (một dòng một mặt hàng trong đơn)

| Cột | Kiểu | B/T | Ý nghĩa · luật |
|---|---|---|---|
| ma_don, stt_dong | str, int | B | stt tự sinh nếu nguồn không có |
| ma_hang | str | B | Nếu nguồn chỉ có tên: nối sang `mat_hang` qua khoá tên chuẩn hoá |
| ten_hang_goc | str | B | |
| loai_dong | enum{hang, phi_phuc_vu, voucher, dung_diem, phi_ship, topping} | B | §3 "Phí phục vụ không phải mặt hàng" |
| so_luong | float | B | Theo đơn vị của dòng; âm nếu là dòng trả |
| don_vi | str | B | |
| so_luong_co_ban | float | B | Lấy từ nguồn nếu có (`Số lượng quy đổi`, `Quy ra ĐV lẻ`, `SLQuyDoi`…), nếu không thì tính `so_luong × hệ số` |
| don_gia | int | B | Giá bán ngày D (§5): `don_gia / hệ số` ra giá một đơn vị cơ bản |
| giam_gia_dong | int | T | |
| thanh_tien | int | B | Đã trừ giảm giá dòng, là cơ sở doanh thu |
| gia_von_dong | int | T | Giá vốn **một đơn vị bán** (§5 lãi gộp) |
| imei | str | T | Điện thoại |

**Chuẩn hoá trạng thái** (mọi giá trị đã thấy trong survey):

| Chuẩn | Giá trị gốc |
|---|---|
| hoan_thanh | Xong, xong, ok, đã lấy, đã xong, Đã hoàn thành, Hoàn thành, Thành công, Đã giao, completed |
| huy | Đã hủy, Đã huỷ, hủy, Hủy, hủy đơn, Đã hủy đơn, khách hủy, Huỷ đơn, cancel, cancelled, **Không giao được** (đã kiểm chứng ở biz_124) |
| tra_hang | Đổi trả, Trả hàng, trả hàng, hàng trả về, Hoàn trả, trả lại, Đã hoàn hàng, Đã trả hàng, Khách trả, returned |
| dang_giao | Đang giao, Đang giao hàng, Đang vận chuyển, đang gửi, Chờ giao, shipping, Đang giao dịch, Đang xử lý (**CHƯA CHẮC** cho 2 giá trị cuối: không thấy câu hỏi nào phân biệt) |

### c.3 Danh mục

| Bảng | Cột (B/T) | Ghi chú |
|---|---|---|
| `mat_hang` | ma_hang B, ten_hang B, ten_khac T (list), nhom_hang T, don_vi_co_ban B, gia_ban_hien_tai T, gia_von T, hang T, so_size T, loai T (máy mới/cũ/phụ kiện), con_kinh_doanh T, la_hang_che_bien T | `gia_von` dùng cho §5 giá trị tồn kho. `la_hang_che_bien` (món pha chế, món nấu) cần cho luật "hết hàng". **CHƯA CHẮC** cách suy tổng quát (dữ liệu cafe vẫn có phiếu nhập "Cà phê đen (M)") |
| `thuoc` | ma_hang B, hoat_chat T, ke_don B | Nhà thuốc (§6) |
| `quy_doi_don_vi` | ma_hang B, don_vi B, he_so_co_ban B | Nguồn: bảng quy đổi **hoặc README**. Đơn vị không có dòng quy đổi thì hệ số = 1 (§10). Quy đổi nhiều cấp thì nhân dồn |
| `khach_hang` | ma_khach B, ten B, sdt T, nhom T, dia_chi T, ngay_sinh T, gioi_tinh T (luôn rỗng trong dữ liệu đã xem), ngay_dang_ky T, diem T, ten_be T | |
| `nhan_vien` | ma_nv B, ten T, chuc_vu T, ngay_vao_lam T, hoa_hong_pct T | Thợ sửa xe dùng chung bảng này |
| `nha_cung_cap` | ma_ncc B, ten T | Nếu nguồn chỉ có tên thì dùng tên làm mã |
| `bang_gia` | ma_hang B, ngay_ap_dung B, gia_co_ban B | §5 hiệu ứng tăng giá |
| `khuyen_mai` | ten B, hang_ap_dung T, tu_ngay B, den_ngay B | dev_013 |

### c.4 Tiền, kho, nhập

| Bảng | Cột (B/T) | Luật dùng |
|---|---|---|
| `thanh_toan` | ma_phieu T, ma_don B, thoi_diem B, so_tien B, hinh_thuc T, loai T{thu_ban, tra_no, gop} | §4 nợ, thu nợ. Sinh thêm từ Sổ nợ / Trả góp (dev_014) và từ `Khách trả` khi không có bảng thu riêng |
| `han_no` | ma_don B, so_ngay_duoc_no T, han_thanh_toan T | VLXD |
| `tra_gop` | ma_don B, gia B, tra_truoc B, so_ky B, gop_thang B, han_gop_ngay B | Luật điện thoại (public test) |
| `phieu_nhap` | ma_phieu B, ngay_nhap B, ma_ncc T, tong_tien T, trang_thai T, ghi_chu T | §5; bỏ phiếu huỷ; giữ phiếu "nhập đầu kỳ" |
| `dong_nhap` | ma_phieu B, ma_hang B, don_vi_nhap T, so_luong B, so_luong_co_ban T, don_gia_nhap T, thanh_tien T, ma_lo T, han_su_dung T | Giá nhập bình quân (§5) |
| `lo_hang` | ma_lo B, ma_hang B, ma_phieu T, han_su_dung B, sl_nhap_co_ban B, don_gia_nhap_co_ban T | §6 nhà thuốc |
| `ban_theo_lo` | ma_don B, stt_dong T, ma_lo B, sl_co_ban B, sl_tra_co_ban T | Tồn theo lô; xác định đơn trả hàng |
| `ton_kho_cuoi` | ma_hang B, ngay B (= ngày cuối dữ liệu), ton_co_ban B | |
| `the_kho` | ma_hang B, thoi_diem B, loai B, sl_co_ban B, ton_sau B | Chỉ có ở SQLite |
| `chi_phi` | ngay B, muc B, so_tien B, ghi_chu T | §5 lãi ròng |
| `giao_hang` | ma_don B, dot B, ngay_giao B, ma_hang B, sl_co_ban T, bien_so T, tai_xe T | §6 VLXD |
| `tra_hang` | ma_don B, thoi_diem T, ly_do T, tien_hoan T | SQLite; lý do trả chỉ có ở đây |
| `bao_cao_ca` | ngay B, ca B, ma_nv T, tien_mat_thu B, tien_mat_hoan T | dev_003 (luật public test) |

### c.5 Bảng cho ngành mới

| Bảng | Cột | Nguồn |
|---|---|---|
| `phieu_dich_vu` | ma_don (tự sinh) B, ngay B, dong_xe T, bien_so B, viec (list[str] chuẩn hoá) B, ma_tho B, tien B, la_bao_hanh B | dev_012. **Đồng thời** sinh `don_hang` (1 phiếu = 1 đơn, `tong_phai_tra = tien`) để luật doanh thu chung vẫn chạy được |
| `bao_hanh_may` | ngay_nhan B, khach T, sdt T, may B, imei B, ngay_mua T, loi T, xu_ly T | dev_014 |
| `thu_may_cu` | ngay B, khach T, sdt T, may_thu B, imei T, gia_thu B, ma_don_tru B | dev_014 |

### c.6 Đối chiếu rulebook → cột cần có

| Luật | Cột / bảng cần |
|---|---|
| §1 doanh thu, số đơn, tỉ lệ huỷ | `dong_hang.thanh_tien`, `loai_dong`, `don_hang.trang_thai`, `ngay_dat` |
| §1 theo hình thức thanh toán / kênh / nhóm khách | `don_hang.hinh_thuc_tt`, `kenh_ban`, `nhom_khach` |
| §2 ca sáng/chiều, giờ cao điểm*, Tết | `don_hang.thoi_diem_dat`, `calendar.csv` |
| §3 bán chạy, bán được bao nhiêu <đơn vị> | `dong_hang.so_luong_co_ban`, `mat_hang.don_vi_co_ban`, `quy_doi_don_vi` |
| §3 xác định khách | `cua_hang.co_ma_khach`, `don_hang.ma_khach` / `ten_khach`, `la_khach_le` |
| §3 nhân viên giỏi nhất / chăm chỉ nhất* | `don_hang.ma_nhan_vien`, `ngay_dat` |
| §4 nợ tại ngày X, tuổi nợ, thu nợ, nợ thêm | `don_hang.tong_phai_tra`, `hinh_thuc_tt`, `kenh_ban` (sàn TMĐT), `thanh_toan.thoi_diem`, `so_tien`; nếu không có thì `con_no_cuoi_du_lieu` |
| §5 tiền nhập, nhà cung cấp, giá nhập bình quân | `phieu_nhap.*`, `dong_nhap.don_gia_nhap`, `so_luong`, `don_vi_nhap` |
| §5 tồn kho, giá trị tồn, hết hàng | `ton_kho_cuoi` / `the_kho`, `dong_nhap`, `dong_hang`, `mat_hang.gia_von`, `la_hang_che_bien` |
| §5 giá bán ngày D, hiệu ứng tăng giá | `dong_hang.don_gia`, `so_luong`, `so_luong_co_ban`; `bang_gia` |
| §5 lãi gộp, lãi ròng | `dong_hang.gia_von_dong`; `chi_phi` |
| §6 cafe size M/L | `dong_hang.ten_hang_goc` / `mat_hang.ten_hang` |
| §6 nhà thuốc | `thuoc.*`, `lo_hang.*`, `ban_theo_lo.*` |
| §6 VLXD giao nhiều đợt | `giao_hang.*` |
| §6* mẹ & bé | `dong_hang.loai_dong` (voucher, điểm, ship), `mat_hang.so_size`, `hang`, `khach_hang.ngay_dang_ky` |
| §6* sửa xe | `phieu_dich_vu.*`, `nhan_vien.hoa_hong_pct` |
| §6* điện thoại | `thu_may_cu`, `tra_gop`, `bao_hanh_may`, `dong_hang.imei`, `mat_hang.loai` |
| §7 không trả lời được | `cua_hang.ngay_bat_dau/ket_thuc_du_lieu`, `nang_luc` |
| §8 điền xuống, dòng trùng, năm của sheet, trạng thái trong ghi chú | Xử lý trong loader; giữ `nguon` (file / sheet) |

`*` = luật chỉ có trong rulebook public test.

---

## d. Bảng ánh xạ theo nhóm

Biến đổi chung cho mọi nhóm (gọi là **T0**): strip + NFC; bỏ ô lỗi (`#N/A`…); bỏ dòng trống, dòng header lặp, dòng tổng; `parse_number` / `parse_money` / `parse_date` từng ô; chuẩn hoá trạng thái; nhận diện khách lẻ; tách SĐT khỏi tên.

| Nhóm | Bảng nguồn → bảng chuẩn | Ánh xạ cột chính (gốc → chuẩn) | Biến đổi riêng |
|---|---|---|---|
| **A** | `DanhSachHoaDon` → don_hang | Mã hóa đơn → ma_don · Thời gian → ngay_dat · Thời gian tạo → thoi_diem_dat · Mã KH → ma_khach · Khách hàng → ten_khach · Tổng tiền hàng / Giảm giá / Tổng sau giảm giá → tong_tien_hang / giam_gia_don / tong_phai_tra · Phương thức thanh toán → hinh_thuc_tt · Trạng thái → trang_thai · Còn nợ → con_no_cuoi_du_lieu · Kênh bán → kenh_ban · Người bán → ma_nhan_vien | Header lệch 2 dòng (biz_106); sheet theo tháng (119, 120, 128); ngày dmy lẫn serial |
| | `DanhSachHoaDonChiTiet` → dong_hang | Mã hóa đơn, STT, Mã hàng, Tên hàng, Đơn vị tính, Số lượng, Đơn giá, Giảm giá, Thành tiền · Số lượng quy đổi → so_luong_co_ban · Giá vốn → gia_von_dong | Khử dòng trùng trong đơn; nối `_1` + `_2` |
| | `SoQuy` → thanh_toan | Mã phiếu, Thời gian, Mã hóa đơn, Phương thức thanh toán, Giá trị (`90.000đ`) | |
| | Sản phẩm / khách / tồn / nhập / ĐVT / lô / thuốc / phòng bàn | Mã hàng, Tên hàng, Nhóm hàng(3 Cấp), ĐVT, Giá bán, Giá vốn · Mã KH, Tên (kèm SĐT), Nhóm khách hàng, Địa chỉ · Tồn cuối kỳ · Mã nhập hàng, Thời gian, Mã NCC, Cần trả NCC, Trạng thái, Ghi chú · Đơn giá, Lô, Hạn sử dụng · Quy đổi · Số lượng (ĐVT cơ bản), Số lượng trả · Hoạt chất, Thuốc kê đơn · Phòng/Bàn, Khu vực, Số khách | biz_109: tất cả là sheet của `DuLieuBanHang.xlsx` |
| **B** | `DonHang_ChiTiet` → don_hang + dong_hang | Mã đơn hàng, Ngày đặt hàng, Trạng thái đơn hàng, Tên khách hàng (cấp đơn) · Tên sản phẩm → ten_hang_goc · Số lượng sản phẩm → so_luong · Giá sản phẩm → don_gia · Tổng tiền → thanh_tien · Đơn vị tính | **Điền xuống 4 cột cấp đơn** (103, 121, 122, dev_005); `"3 chai"` → 3; ma_hang = nối qua tên sang `DanhSachSanPham` / `DanhSachQuyDoi`; so_luong_co_ban = SL × hệ số; dev_002, 005: nối 17 file tháng |
| | `DanhSachQuyDoi` → quy_doi_don_vi | Tên sản phẩm, Đơn vị quy đổi, Tỉ lệ quy đổi, Đơn vị cơ bản | dev_005: hệ số theo đơn vị ngay dưới (`2 vỉ`), cần nhân dồn |
| | `DonNhapHang(_ChiTiet)`, `DonHang_Lo`, `DanhSachThuoc` | Mã đơn nhập, Ngày nhập, Mã nhà cung cấp · Mã SKU, Mã lô, Hạn sử dụng, Số lượng nhập (cơ bản) · Mã đơn hàng, Mã lô, Số lượng, Số lượng trả | **Không có giá nhập** nên `nang_luc` không có `gia_nhap` |
| **C** | `So_chi_tiet_ban_hang` → don_hang + dong_hang | Ngày, Mã đơn hàng, Tên hàng hóa, Đơn vị tính, Số lượng, Đơn giá (`45,000.0000`), Thành tiền, Trạng thái, Số lượng quy đổi, Khách hàng (nếu có) | Header lệch 3 (112, 118, 130, dev_001); dòng tổng ngày (130, dev_001); nối tên sang `Danh sách hàng hóa` |
| | `Danh sách hàng hóa`, `Bảng kê phiếu giao hàng`, `Chi tiết công nợ theo hạn` | Mã hàng hóa, Tên, Nhóm, ĐVT, Giá bán, Giá vốn · Ngày giao hàng, Mã đơn hàng, Lần giao, Số lượng giao (cơ bản), Biển số xe, Người giao hàng · Số ngày được nợ, Hạn thanh toán | Nhóm C **không có bảng thu tiền / còn nợ**. Bằng chứng: câu hỏi nợ ở biz_112 (nhóm C), biz_105 và 117 (nhóm D) đều có đáp án unanswerable; biz_115, 116, 118 không có câu hỏi nợ nào. Vậy không có `thanh_toan` thì câu hỏi nợ là unanswerable |
| **D** | `SoBanHang` → don_hang + dong_hang | Hàng / Hàng bán / Tên SP · so_luong / SL bán / Số lượng hàng · Unit / DonVi / dvt · Trị giá / Tiền / Amount · Status / Ghi chú TT / Trạng thái xử lý · Giá lẻ / Giá / Giá 1 đv · Giờ → thoi_diem_dat · Mã hóa đơn / Mã phiếu / Ma don · Ngày giao dịch / Ngày lập / Thời gian · Khách / TenKH / Khách hàng (tên) · Tổng phiếu (dev_004) → tong_phai_tra | Tiền `38k` / `1tr440`; ngày không năm lấy năm theo tên sheet; dòng âm là trả hàng; điền xuống (dev_004); 1 dòng tổng cuối sheet |
| | `DanhMuc`, `TonKho`, `SoNhapHang`, `BangGia`, `SoGiaoHang`, `SoHanNo` | Tên, ĐV gốc, ĐV lớn, Hệ số · Tồn cuối / Tồn thực · Số phiếu, Ngày nhập, Ghi chú, Thành tiền, Nhà cung cấp, Giá nhập, ĐVT, SL nhập · Ngày áp dụng, Giá mới, Giá cũ · … | Nối qua **tên hàng** (không có mã) |
| **E** | `SoBanHang` → dong_hang (+ don_hang 1 đơn / dòng) | Nội dung / Mặt hàng / Ten hang · Số lượng / SL bán · Số lượng lẻ / SL lẻ → so_luong_co_ban · don_gia / Đơn giá bán / Price · Tổng tiền / thanh_tien / Thành tiền (đ) · Trạng thái · ngay_ban / Ngày mua / Ngày tháng | **Không khử dòng trùng** (§8 bảng không ghi theo đơn); không có khách, không có mã đơn |
| **F** | `ban_hang.csv` → don_hang + dong_hang | Mã hóa đơn / Mã GD / Số phiếu · Ngày tháng / Ngày / Ngày bán · Kết quả / trang_thai / Trạng thái xử lý · Đối tác / Tên khách / Khách hàng (tên) · Nội dung / Sản phẩm / Hàng bán · so_luong / Sluong / SL bán · Quy ra ĐV lẻ / Số lượng lẻ · Giá bán / Giá bán lẻ / Giá 1 đv · Thanh tien / Tổng / Amount | Quy đổi lấy từ README; ngày `1 thg 6 2025` (biz_101) |
| **G** | `danh_sach_hoa_don.csv` → don_hang | Mã bill / Mã hóa đơn · Ngày giao dịch / Ngày tháng · Status / Trạng thái đơn · Bên mua / Đối tác · Tien hang / Giá trị hàng → tong_tien_hang (**chính là doanh thu đơn**) · TongTien → tong_phai_tra · Da tra / Đã thu · Chưa trả / Nợ → con_no_cuoi_du_lieu | Không có `dong_hang`: câu hỏi theo mặt hàng là unanswerable; dòng `Cộng ngày` |
| **H** | `don_hang`, `chi_tiet_don`, `san_pham`, `khach_hang`, `thanh_toan` | Mã chứng từ / Số phiếu / Số CT · NgayBan / Ngày / Date · Xử lý / Tình trạng (completed…) · Số KH / Customer ID / Mã khách mua / Mã thẻ · Tổng bill / Tổng đơn / Phải thu / Thành tiền · Khách trả · Còn lại / Dư nợ / Con no · Phương thức TT / Trả bằng / Hình thức thanh toán (cash, transfer, ewallet, cod, debt) · Bán qua / Loại bán / Kênh đặt · Phí vận chuyển, Tiền giảm (dev_010) · chi tiết: Ma don, ID SP / Mã mặt hàng, SL, SL quy đổi, Giá đơn vị, T.Tiền / Amount / Tiền bán / Cộng, CK | dev_010: header lặp + dòng tổng trong CSV; biz_127 `Amount` dạng `10.000đ` |
| **I** | SQLite: `don_hang`, `chi_tiet_don`, `thanh_toan`, `tra_hang`, `the_kho`, `lo_hang`, `chi_tiet_don_lo`, `lich_su_gia`, `thong_tin_thuoc`, `don_vi_sp`, `phieu_nhap`, `chi_tiet_nhap`, `khach_hang`, `nhan_vien`, `nha_cung_cap` | gần như 1–1: MaHoaDon, NgayLap (dmy / serial / `thg` lẫn lộn!), ThoiGianLap, TinhTrang, MaKhachHang, MaNhanVien, KenhBanHang, PhuongThucTT, TongThanhToan, ChietKhau, PhiVanChuyen · SLQuyDoi, TriGia, GiaVonLucBan · SoTienThu · TonCuoi · BanTheoDon (0/1) | Lọc theo `IDCuaHang`; khử dòng trùng `chi_tiet_don` |
| **J** | `BanHang_HoaDon` + `ChiTietHoaDon` (biz_124) hoặc sheet `BanHang` gộp (dev_003) | Order ID / Đơn số · Ngày bán / Ngày HĐ · Giờ tạo đơn · Trạng thái / Trạng thái giao · Mã KH mua / Mã khách · Tong tien / Tổng thanh toán · Còn nợ / Công nợ · Phương thức TT · Nguồn đơn / Nguồn · Mã NV bán · chi tiết: Ma hang / Barcode, Slg / S.L, SL cơ bản, Giá niêm yết / Giá 1 đv, Khuyến mãi / Giảm (đ), Thanh tien / Thành tiền (đ), Giá vốn lúc bán | dev_003: tách đơn ra khỏi sheet phẳng (cột cấp đơn lặp lại); `SoTay_*`: header lệch 2, tiền `25000k` / `396k`, nối qua **tên** hàng |
| **K** 🆕 | `chi_tiet_hoa_don` / `ChiTietHoaDon_*` → don_hang + dong_hang | Mã bill / Bill · Ngày giao dịch / Ngày xuất · Giờ bán · Tiến độ / TT đơn · Mã khách mua / Mã người mua · Họ tên khách / Khách · Nhóm khách hàng · Nguồn / Kênh bán · Nhân viên bán · Bàn, Khu vực, Số khách · Tổng tiền hàng, Giảm giá HĐ, Phi ship, Tong tien, Khách trả, Còn nợ / Note · Mặt hàng / Tên hàng, Mã vạch / Ma hang, Sluong / SLg, Số lượng lẻ / SL lẻ, Đơn giá (đ), Tiền giảm / Giảm (đ), Thành tiền, Phân loại / Nhóm hàng | Tách cột cấp đơn (lấy giá trị đầu mỗi đơn); số `129 000`; chuẩn hoá mã bàn; parse nợ trong `Note` (dev_008); dòng tổng ngày |
| **L** 🆕 | `Sổ bán hàng` / sheet tháng → don_hang + dong_hang | STT → ma_don (theo tháng/sheet, **CHƯA CHẮC** STT có reset mỗi tháng không) · Ngày · Khách · Hàng → tra `Ghi tắt` · IMEI · SL · Giá · Thành tiền · Bớt → giam_gia_don · Thu máy cũ · Khách trả → tong_phai_tra · Ghi chú → trạng thái | Điền xuống cột cấp đơn; tiền `19tr990`; `Sổ nợ` / `Trả góp` sinh `thanh_toan` + `tra_gop`; nối với sổ bán qua `STT 26` trong ghi chú |
| **M** 🆕 | `SoSuaXe` → phieu_dich_vu + don_hang | Ngày · Xe → dong_xe + bien_so (regex `\d{2}[A-Z]\d?-\d{3}\.\d{2}`) · Làm gì → viec[] · Thợ → ma_tho (khớp `DanhSachTho` theo tên gọi) · Tiền · Ghi chú "bảo hành" → la_bao_hanh | Từ điển việc (`bdtq` = bảo dưỡng tổng quát, `vs nồi`…): **CHƯA CHẮC**, cần xây từ dữ liệu + luật "Nhớt ghi trơn là nhớt máy" |
| **N** 🆕 | `BanHang_<năm>` → don_hang + dong_hang | HĐ → ma_don · Ngày · Khách · Kênh · Tên hàng · SL · ĐVT · ĐG · TT · Ghi chú → trạng thái | Header 2 dòng; dòng Voucher / Dùng điểm / Phí ship → `loai_dong`; `QuanLy.DanhMuc.Tên gọi khác` → alias; `Quy đổi` dạng chữ |

---

## e. Xử lý tiệm có mẫu mới

**Nguyên tắc:** mọi logic theo rulebook chỉ đọc **schema chuẩn**. Phần riêng cho từng tiệm chỉ là một **file mapping JSON** được sinh tự động, không có code `if business_id == …`.

### Pipeline đề xuất

| Bước | Việc | Tất định / LLM |
|---|---|---|
| 1 | **Mở file** tổng quát (như `survey.py`): mọi sheet, tìm header, gom sheet và file cùng header, nhận diện năm và tháng trong tên sheet hoặc tên file | tất định |
| 2 | **Parse README**: danh sách file, cặp `**Cột**: mô tả`, khối "Quy ước" (ngày cuối dữ liệu, quy đổi, công nợ, tồn…), câu "sheet `X` của file `Y`" | tất định |
| 3 | **Ánh xạ cột theo từ điển mô tả**: `"thành tiền sau giảm" → dong_hang.thanh_tien`, `"tên khách (Khách lẻ nếu không lưu)" → don_hang.ten_khach`… (~175 mô tả đã thấy) | tất định |
| 4 | **Fallback cho cột hoặc file chưa có trong từ điển** (POS không mô tả cột như biz_106, 109; sổ mới như dev_012): đưa cho LLM schema chuẩn + README + header + 10 dòng mẫu + kết quả profile cột (mẫu giá trị, % trống), yêu cầu xuất **mapping JSON** | LLM, chạy 1 lần mỗi tiệm, **cache** lại |
| 5 | **Áp mapping** và chạy các bước làm sạch chung T0 | tất định |
| 6 | **Kiểm tra tự động** (sai thì quay lại bước 4 với thông báo lỗi) | tất định |
| 7 | Xuất `nang_luc` + khoảng ngày cho tầng trả lời | tất định |

### Ví dụ mapping JSON (LLM xuất, loader kiểm tra)

```json
{
  "business_id": "dev_012",
  "tables": [{
    "source": {"file": "SoSuaXe.xlsx", "sheets": "*", "header_row": "auto"},
    "target": "phieu_dich_vu",
    "row_filter": {"drop_if_matches": ["^(tổng|cộng)"]},
    "columns": {
      "ngay":   {"from": "Ngày", "parse": "date", "year_from": "sheet_name"},
      "bien_so": {"from": "Xe", "parse": "regex", "pattern": "(\\d{2}[A-Z]\\d?-\\d{3}\\.\\d{2})"},
      "dong_xe": {"from": "Xe", "parse": "regex_remainder"},
      "viec":   {"from": "Làm gì", "parse": "split", "sep": ["+", ","]},
      "ma_tho": {"from": "Thợ", "parse": "lookup", "table": "nhan_vien", "fuzzy": true},
      "tien":   {"from": "Tiền", "parse": "money"},
      "la_bao_hanh": {"from": "Ghi chú", "parse": "contains", "value": "bảo hành"}
    },
    "fill_down": [],
    "dedupe": false
  }],
  "status_map_extra": {},
  "unit_conversions_from_readme": true
}
```

### Kiểm tra tự động sau khi nạp (bắt lỗi mapping)

| Kiểm tra | Ngưỡng |
|---|---|
| `max(ngay_dat)` ≤ ngày cuối trong README, và gần ngày đó | trong vòng 7 ngày |
| Mọi `trang_thai_goc` đều ánh xạ được | 100% |
| `Σ thanh_tien` của đơn ≈ `tong_tien_hang` (nếu có) | ≥ 99% số đơn khớp |
| Nếu có dòng tổng theo ngày: tổng theo ngày tính ra = số trên dòng tổng | ≥ 99% số ngày |
| `don_gia × so_luong − giam_gia_dong = thanh_tien` (tiệm không có cột giảm giá: cho phép `thanh_tien` ≤ `don_gia × so_luong`) | ≥ 99% số dòng không vượt quá (bắt sai parse `k` / `tr`; biz_117: 98% khớp đúng, phần còn lại là giảm giá dòng) |
| `so_luong_co_ban / so_luong` ∈ hệ số của (mặt hàng, đơn vị) | ≥ 99% |
| Tỉ lệ dòng hàng không nối được sang `mat_hang` | ≤ 1% |
| Tỉ lệ ô số parse lỗi | ≤ 0,1% |

**Rủi ro / CHƯA CHẮC:** LLM dễ ánh xạ sai các cột cùng nghĩa gần (`Tổng tiền` có thể là thành tiền **dòng**, như biz_102, hoặc tổng **đơn**, như biz_107 hay dev_010 `Thành tiền`), nên phải có bước kiểm tra chéo ở bảng trên. Từ điển việc sửa xe và tên gọi khác (mẹ & bé) cần thêm luật hoặc LLM ở **tầng hiểu câu hỏi**, không chỉ ở loader.

---

## f. Thống kê câu hỏi

Phân loại bằng từ khoá (bỏ dấu, sửa teencode và lỗi gõ Telex như `dthu`, `bnhiu`, `toongr`, `tieenf`). Đây là con số **xấp xỉ**: 17/3000 câu train và 39/1000 câu public không phân loại được. Public test chỉ có câu hỏi, không có đáp án.

| Loại câu hỏi | Train | % | Public | Type đáp án chính | Bảng / cột cần |
|---|---|---|---|---|---|
| Doanh thu tổng theo kỳ | 529 | 17,6 | 145 | number | don_hang(ngay_dat, trang_thai), dong_hang.thanh_tien |
| Huỷ đơn (số / tỉ lệ) | 241 | 8,0 | 42 | percent, number | don_hang.trang_thai |
| Tăng trưởng % so kỳ trước | 200 | 6,7 | 84 | percent | như doanh thu |
| Số đơn (kể cả "đơn ≥ X đồng") | 190 | 6,3 | 76 | number | don_hang, cua_hang.co_ma_don |
| Giá trị trung bình một đơn | 168 | 5,6 | 46 | number | don_hang + dong_hang |
| Số lượng bán theo đơn vị / mặt hàng | 157 | 5,2 | 42 | number | dong_hang.so_luong_co_ban, mat_hang.don_vi_co_ban, quy_doi |
| Tỉ trọng % (nhóm, kênh, khách…) | 146 | 4,9 | 55 | percent | + mat_hang.nhom_hang / don_hang.kenh_ban / nhom_khach |
| Ngày / tháng có doanh thu cao nhất | 126 | 4,2 | 20 | date | don_hang.ngay_dat |
| Doanh thu theo mặt hàng | 125 | 4,2 | 58 | number | dong_hang.ma_hang, alias tên |
| Nhà thuốc: kê đơn / hoạt chất | 90 | 3,0 | 15 | number, percent | thuoc.ke_don, hoat_chat |
| Giá bán ngày D | 89 | 3,0 | 3 | number | dong_hang.don_gia, so_luong_co_ban |
| Bán chạy / top k | 88 | 2,9 | 24 | list, string | dong_hang.so_luong_co_ban, loai_dong |
| Khách top (nhiều tiền / nhiều đơn…) | 85 | 2,8 | 30 | list, string | don_hang.ma_khach / ten_khach, la_khach_le |
| Hiệu ứng tăng giá | 84 | 2,8 | 18 | percent | bang_gia, dong_hang.so_luong_co_ban |
| Công nợ (tổng, số khách nợ, top nợ) | 65 | 2,2 | 25 | number, **table** | don_hang.tong_phai_tra, hinh_thuc_tt, thanh_toan |
| Doanh thu nhiều kỳ (chuỗi tháng, tăng liên tục?) | 58 | 1,9 | 28 | list, boolean, date | như doanh thu |
| Ca sáng / chiều | 53 | 1,8 | 9 | number | don_hang.thoi_diem_dat |
| Tồn kho (cả đơn vị lớn) | 50 | 1,7 | 4 | number, list | ton_kho_cuoi / the_kho, dong_nhap, dong_hang |
| Doanh thu nhóm hàng | 49 | 1,6 | 20 | number | mat_hang.nhom_hang |
| Thu nợ / nợ thêm | 47 | 1,6 | 11 | number, list | thanh_toan.thoi_diem, so_tien |
| Size M/L (cafe) | 46 | 1,5 | 4 | number | mat_hang.ten_hang |
| Tiền nhập hàng | 41 | 1,4 | 5 | number | phieu_nhap, dong_nhap |
| Doanh thu theo kênh / hình thức TT | 37 | 1,2 | 14 | list, number | don_hang.kenh_ban, hinh_thuc_tt |
| Giá nhập bình quân | 36 | 1,2 | — | number | dong_nhap.don_gia_nhap, so_luong |
| Hàng ế | 31 | 1,0 | 6 | number | dong_hang (trước kỳ / trong kỳ) |
| Lãi gộp / hàng lời nhất | 26 | 0,9 | 19 | number, string | dong_hang.gia_von_dong |
| Số khách (mua ≥ N đơn…) | 25 | 0,8 | 19 | number | don_hang.ma_khach |
| Hạn dùng / lô | 22 | 0,7 | 11 | number, date, list | lo_hang, ban_theo_lo |
| Doanh thu nhóm khách | 19 | 0,6 | 6 | number | don_hang.nhom_khach |
| Nhân viên | 17 | 0,6 | 13 | number, string | don_hang.ma_nhan_vien |
| Đợt giao hàng (VLXD) | 16 | 0,5 | 3 | number | giao_hang |
| Mặt hàng có mặt trong ≥ N đơn | 7 | 0,2 | 5 | number | dong_hang |
| Nhà cung cấp | 7 | 0,2 | 6 | string | phieu_nhap.ma_ncc |
| Tuổi nợ (3 nhóm) | 5 | 0,2 | 7 | list | don_hang.ngay_dat, thanh_toan |
| Nhập trừ bán, lãi ròng, chênh lệch | 8 | 0,3 | 7 | number | dong_nhap, chi_phi |
| 🆕 Điện thoại (thu máy cũ, trả góp, dòng máy…) | — | — | 34 | ? | thu_may_cu, tra_gop, mat_hang.loai |
| 🆕 Sửa xe (lượt xe, thợ, hoa hồng, việc) | — | — | 26 | ? | phieu_dich_vu, nhan_vien.hoa_hong_pct |
| 🆕 Bảo hành (xe, điện thoại) | — | — | 9 | ? | phieu_dich_vu.la_bao_hanh, bao_hanh_may |
| 🆕 Mẹ & bé (voucher, điểm, số sữa, size bỉm, thành viên mới) | — | — | 12 | ? | dong_hang.loai_dong, mat_hang.so_size / hang, khach_hang.ngay_dang_ky |

**Phân bố type đáp án (train):** number 62,8% · percent 19,3% · list 6,4% · date 4,8% · string 2,9% · unanswerable 2,3% · boolean 0,8% · table 0,6%.

**Câu unanswerable (70 câu train), theo nguyên nhân:**

| Nguyên nhân | Ví dụ | Loader cần cung cấp |
|---|---|---|
| Kỳ hỏi nằm hoàn toàn ngoài khoảng dữ liệu | biz_103 "doanh thu tháng 2/2025" (dữ liệu bắt đầu 04/2025) | `ngay_bat_dau_du_lieu` |
| Tiệm không ghi loại thông tin | tồn kho (biz_103, 112, 118, 130), giá nhập (biz_112, 118, 121, 122), tiền nhập (biz_103), công nợ (biz_103, 105, 112, 117: không có lịch sử thanh toán), nhóm khách (biz_106), kênh / HTTT (biz_105, 121, 130) | `nang_luc` |
| Thuộc tính không có trong dữ liệu | địa chỉ khách theo đường, giới tính khách, lý do huỷ / trả (biz_118, 121) | `nang_luc` (cột rỗng = không có) |
| Chủ quan / cần kiến thức ngoài | "nhân viên lễ phép?", "liều dùng thuốc" | Tầng hiểu câu hỏi (không phải loader) |

**Ghi chú về public test:** câu hỏi viết tắt nhiều hơn train (`th3/26`, `cko mik bít`, `đơng`, `wán`), nên tầng hiểu câu hỏi phải chịu được lỗi gõ nặng hơn.

---

## Phụ lục: chạy lại khảo sát

```
pip install pandas openpyxl        # máy hiện chưa có hai thư viện này
python survey.py                   # → survey_raw.md (~5 phút, ~750 KB), chỉ đọc dữ liệu gốc
python survey.py --only dev_012 --out /tmp/x.md --full-readme
```
