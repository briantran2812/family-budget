# Test case trải nghiệm người dùng (UX)

**Nhân vật chính:** Lan, người dùng không rành công nghệ. Lan dùng Gmail và mua sắm trên Shopee,
TikTok; thanh toán qua MoMo và app ngân hàng. Lan nhận app qua file `.dmg`, không có ai ngồi cạnh
hướng dẫn.

**Mục tiêu:** Lan tự cài app, kết nối Gmail và biết tháng này nhà mình chi bao nhiêu % cho từng việc,
tất cả trong vòng **10 phút** mà không cần hỏi ai.

Có hai loại test case:

- **Tự động (UX-xx):** chạy bằng `pytest tests/e2e` trên WebKit, đúng loại engine mà cửa sổ app dùng.
  Mỗi test cũng tự fail nếu trang có bất kỳ lỗi JavaScript nào.
- **Thủ công (M-xx):** cần người thật, máy thật hoặc tài khoản thật. QA chạy các ca này trên file
  **RC `.dmg`** rồi ghi kết quả vào `qa/QA-SIGNOFF-<phiên bản>.md`. Mọi ca **P1** phải đạt PASS thì
  mới được release.

## Tự động

| ID | Tình huống | Kiểm tra |
| --- | --- | --- |
| UX-01 | Mở app lần đầu | Hiện màn hình chào mừng; nhập tên xong thì app chào "Chào Lan 👋" và mở hướng dẫn Gmail |
| UX-01b | Bỏ qua phần chào mừng | Mở lại app không bị hỏi lại |
| UX-02 | Hướng dẫn Gmail: các bước và báo lỗi | Đi tới/lùi được giữa các bước; link đúng trang Google; mật khẩu thiếu ký tự hoặc sai đều có thông báo rõ ràng |
| UX-03 | Kết nối Gmail xong rồi đồng bộ | Hiện "Đã kết nối!"; bấm Đồng bộ thì đơn Shopee xuất hiện trong ô Shopee ở trang Tổng quan |
| UX-04 | Thêm khoản chi, gõ "1,5tr" | Ô số tiền hiện "= 1.500.000 ₫"; tự xếp vào hạng mục Học phí; hiện ngay ở Tổng quan và mục Gần đây |
| UX-05 | Gõ số tiền sai | Có thông báo lỗi, cửa sổ nhập không bị đóng (không mất dữ liệu đã gõ) |
| UX-06 | Thêm thu nhập, lưu bằng phím Enter | Vòng tròn hiện đúng % thu nhập đã chi |
| UX-07 | Đổi hạng mục và bật Ghi nhớ | App đề xuất từ khoá; giao dịch tương tự được xếp lại; có thông báo đã xếp lại bao nhiêu giao dịch |
| UX-08 | Đánh dấu Không tính, rồi Tính lại | Tổng tiền cập nhật ngay; giao dịch bị gạch ngang |
| UX-09 | Xoá giao dịch | App hỏi xác nhận trước; bấm Huỷ thì không xoá |
| UX-10 | Chuyển tháng | Nút ‹ › đổi tháng; nút "Tháng này" chỉ hiện khi đang xem tháng khác |
| UX-11 | Bấm vào một hạng mục ở Tổng quan | Chuyển sang tab Giao dịch, đã lọc sẵn theo hạng mục đó |
| UX-12 | Tìm kiếm và lọc theo nguồn | Số giao dịch và tổng chi hiển thị khớp với bộ lọc |
| UX-13 | Nhập ảnh biên lai, sửa số tiền rồi lưu | OCR điền sẵn số tiền, mô tả và hạng mục; số đã sửa được lưu đúng |
| UX-14 | Đặt ngân sách "1tr" | Ở Tổng quan hiện cảnh báo "Vượt ngân sách 200k" |
| UX-15 | Mở app khi chưa có dữ liệu | Hiện thẻ "Bắt đầu thôi!" với 3 lựa chọn; nút Đồng bộ ẩn khi chưa kết nối Gmail |
| UX-16 | Đóng cửa sổ nhập liệu | Đóng được bằng phím Esc và bằng cách bấm ra ngoài |
| UX-17 | Màn hình rộng 390px (cỡ điện thoại) | Không tab nào bị tràn ngang; thanh điều hướng chuyển xuống đáy |
| UX-18 | Máy để chế độ tối | Giao diện tự chuyển sang màu tối |
| UX-21 | Email không đọc được | Hiện trong danh sách riêng; bấm "Ẩn" là xong |
| UX-22 | Xuất CSV | Tải về file đúng tên; mở bằng Excel thấy đúng tiếng Việt (file có BOM) |
| UX-23 | Gỡ tài khoản Gmail | App hỏi xác nhận trước; danh sách tài khoản cập nhật |
| UX-24 | Đi qua mọi tab | Không có lỗi JavaScript nào |
| UX-25 | 3.000 giao dịch | Tổng quan và danh sách tải xong dưới 3 giây |
| UX-26 | Nhập sao kê CSV | Hiện 4 ô kết quả: Khớp, Chưa ghi trong app (tổng tiền và số gần khớp), Ghi Visa nhưng không có trên sao kê, Bỏ qua (thanh toán thẻ tự động) |
| UX-27 | Thêm khoản quẹt thẻ bị quên | Bấm ＋ Thêm vào app thì dòng chuyển sang Khớp; giao dịch mới hiện ở tab Giao dịch với nhãn "Sao kê" và 💳 tên thẻ |
| UX-28 | Gần khớp vì tiền tip | Bấm "Ghép, sửa thành số sao kê" thì số tiền trong app được sửa theo sao kê |
| UX-29 | PDF có mật khẩu | Hiện ô mật khẩu; nhập sai có báo lỗi; nhập đúng thì nhập được và ô mật khẩu ẩn đi |
| UX-30 | Ghép tay, Bỏ qua | Chọn được giao dịch cần ghép (không mở nhầm cửa sổ sửa); bỏ qua hết thì hiện "Mọi dòng… đều đã có" |
| UX-31 | Trường "Trả bằng" | Hiện trên giao dịch; lần nhập sau tự điền sẵn thẻ đã dùng lần trước |
| UX-32 | Bấm ô Shopee / TikTok / Số giao dịch | Mở tab Giao dịch, đã lọc đúng nguồn |
| UX-33 | Khoản ghi Visa mà không có trên sao kê | Bấm vào thì mở cửa sổ sửa, kể cả khi giao dịch thuộc tháng khác tháng đang xem |
| UX-34 | Kết nối iPhone | Mã sai thì báo ngay trong cửa sổ; mã đúng thì kết nối, tự lấy khoản chi về và lọc được theo nguồn "iPhone" |
| UX-35 | Mở app khi đã kết nối iPhone | Tự lấy khoản mới, báo bằng thông báo nhỏ; bấm Đồng bộ khi không có gì mới thì vẫn báo kết quả |
| UX-36 | Cài đặt → iPhone | Sao chép được mã cho iPhone; Ngắt kết nối có hỏi lại |
| UX-37 | Cách trả | Biểu tượng theo cách trả (💵 tiền mặt, 💳 thẻ, 🏦 chuyển khoản, 👛 ví); lọc được theo cách trả và theo "Chưa ghi cách trả" |
| UX-38 | Tổng quan: cách trả và nguồn | Thẻ "Chi theo cách trả" có số tiền và % từng cách trả, bấm vào mở danh sách đã lọc; hai ô nguồn là hai nguồn chi nhiều nhất trong tháng |
| UX-39 | Bản sao lên Google Sheet | Đẩy ngay báo số giao dịch đã đẩy, ghi giờ đẩy; tắt thì nút Đẩy ngay bị khoá |
| UX-40 | Nút ↻ Đồng bộ ở trang đầu | Ẩn khi chưa kết nối gì; bấm thì báo có gì mới hoặc "không có gì mới" |
| UX-41 | Tỷ lệ thu nhập đã chi | Dưới 10% hiện một chữ số lẻ (0,5%), không làm tròn thành 0% |
| UX-42 | Có gì mới | Hiện một lần sau khi cập nhật phiên bản; mở lại được từ thanh bên và Cài đặt; nút Xem → mở đúng tab; người dùng mới thấy màn chào thay vì Có gì mới |
| UX-43 | Cảnh báo ngân sách | Dưới 80% thì không có cảnh báo; từ 80% hiện "đã dùng 85% ngân sách tháng … — còn 300k", vượt thì "đã vượt ngân sách tháng 250k" (nặng nhất lên trước); hạng mục 80–100% có nhãn "Đã dùng …%"; bấm cảnh báo mở danh sách đã lọc theo hạng mục; không tràn ngang ở 390px |
| UX-44 | Chưa đặt ngân sách | Thẻ hạng mục có lối tắt "Đặt ngân sách…" tới Cài đặt; đặt xong thì lối tắt ẩn và cảnh báo hiện ở Tổng quan |
| UX-45 | Chuông thông báo | Số chưa đọc trên chuông; cảnh báo ngân sách và phiên bản mới có trong danh sách; bấm mở đúng chỗ và đánh dấu đã đọc; mở được Nhật ký thay đổi với mọi phiên bản |
| UX-46 | Giao diện Sáng / Tối / Theo máy | Chọn Sáng khi macOS để Tối (và ngược lại) thì đổi ngay, giữ sau khi mở lại |

Bản đóng gói còn được kiểm tra tự động bằng `tests/test_packaged.py`: cửa sổ tải được giao diện,
Keychain hoạt động, OCR chạy bên trong bundle, và kết nối TLS tới Gmail thành công.

## Thủ công

Chuẩn bị: file RC `.dmg`, **một máy Mac khác** (lý tưởng nhất là máy của Lan), một tài khoản Gmail
có ít nhất một đơn Shopee hoặc TikTok trong 6 tháng gần nhất, và điện thoại có app MoMo hoặc app ngân
hàng.

| ID | Ưu tiên | Tên | Các bước | Kết quả mong đợi |
| --- | --- | --- | --- | --- |
| M-01 | P1 | Cài từ DMG trên máy Mac khác | Gửi RC qua AirDrop hoặc Zalo → mở `.dmg` → kéo vào Applications → mở app | Bị chặn lần đầu; làm theo "Hướng dẫn cài đặt.txt" (Open Anyway) thì mở được; không cần cài thêm gì |
| M-02 | P1 | Người mới tự kết nối Gmail | Đưa máy cho Lan, **không giúp**; bấm giờ từ màn hình chào mừng tới lúc "Đã kết nối!" | Xong trong ≤ 10 phút; Lan hiểu App Password là gì; ghi lại chỗ nào Lan bị vướng |
| M-03 | P1 | Đồng bộ Gmail thật | Bấm Đồng bộ ngay; so số đơn và tổng tiền với lịch sử "Đơn mua" trên app Shopee/TikTok và lịch sử giao dịch MoMo của tháng gần nhất. Nếu không có đơn nào, đọc thông báo app đưa ra | Mỗi đơn chỉ tính một lần; số tiền khớp; đơn huỷ không bị tính; mục "Email chưa đọc được" chỉ còn email giao hàng |
| M-04 | P1 | Ảnh chụp biên lai MoMo thật | Chụp màn hình biên lai MoMo (điện, học phí…) trên iPhone → AirDrop sang Mac → kéo vào app | Số tiền và ngày đúng; mô tả đọc được; hạng mục hợp lý hoặc sửa được dễ dàng |
| M-05 | P1 | Ảnh chụp biên lai chuyển khoản ngân hàng thật | Như M-04, nhưng với biên lai chuyển khoản của app ngân hàng | Như M-04 |
| M-06 | P1 | Đóng rồi mở lại app | Thêm 1 giao dịch → đóng cửa sổ (⌘Q) → mở lại | App thoát hẳn khi đóng; dữ liệu và tài khoản Gmail còn nguyên |
| M-07 | P1 | Cập nhật đè lên bản cũ | Đang có dữ liệu, cài bản RC đè lên bản trước | Dữ liệu còn; tài khoản Gmail còn; nếu Keychain hỏi quyền thì chọn "Always Allow" và chỉ bị hỏi một lần |
| M-08 | P1 | Đồng bộ khi mất mạng | Tắt Wi-Fi → bấm Đồng bộ ngay | Thông báo bằng tiếng Việt dễ hiểu, app không treo; bật lại Wi-Fi thì đồng bộ được |
| M-09 | P2 | Kéo thả ảnh vào cửa sổ app | Kéo một file ảnh từ Finder vào ô "Kéo thả ảnh" | Ảnh được đọc như khi bấm chọn file |
| M-10 | P2 | Dán ảnh bằng ⌘V | Chụp màn hình bằng ⌘⇧4 (giữ Control để chụp vào clipboard) → ⌘V trong app | Ảnh được đọc |
| M-11 | P2 | Xuất CSV trong cửa sổ app | Cài đặt → Xuất CSV → mở file bằng Numbers hoặc Excel | File nằm trong Downloads; tiếng Việt hiển thị đúng |
| M-12 | P2 | Đổi chế độ sáng/tối | System Settings → Appearance → Light rồi Dark | Giao diện đổi theo; chữ dễ đọc ở cả hai chế độ |
| M-13 | P2 | Thu hồi App Password | Xoá App Password trên trang Google → bấm Đồng bộ | Báo lỗi đúng tài khoản, gợi ý gỡ rồi thêm lại tài khoản |
| M-14 | P2 | Lan đọc lại toàn bộ chữ trong app | Lan đọc mọi màn hình và đánh dấu chữ nào khó hiểu hoặc sai chính tả | Không có thuật ngữ kỹ thuật nào khó hiểu; không sai chính tả |
| M-15 | P2 | Hai tài khoản Gmail | Thêm Gmail của cả hai vợ chồng → Đồng bộ | Đơn của cả hai đều được nhập; một tài khoản lỗi không làm hỏng tài khoản kia |
| M-16 | P1 | Đối chiếu sao kê Visa thật | Ghi tay các khoản quẹt Visa trong 1 tháng → tải sao kê tháng đó từ internet banking (Excel hoặc PDF) → Đối chiếu → nhập sao kê | Mọi dòng trên sao kê đều được đọc (đếm tay để so); khoản đã ghi được ghép đúng; khoản quên ghi nằm trong "Chưa ghi trong app"; thanh toán thẻ được tự bỏ qua |
| M-17 | P2 | PDF sao kê gửi qua email (có mật khẩu) | Lưu file PDF đính kèm email sao kê → nhập kèm mật khẩu của ngân hàng | Đọc được; nếu không đọc được thì thông báo gợi ý dùng file Excel/CSV |
| M-18 | P2 | Không tính trùng khi Gmail về sau | Thêm một dòng sao kê là đơn Shopee vào app → sau đó Đồng bộ Gmail | Vẫn chỉ có một giao dịch, mang tên sản phẩm từ email |
| M-19 | P1 | Cài Apps Script và kết nối | Làm theo `phone/README.md` phần A trên tài khoản Google thật | Không bước nào cần hỏi người khác ngoài cảnh báo "chưa xác minh" đã có trong hướng dẫn; app Mac báo Đã kết nối |
| M-20 | P1 | Ghi khoản chi trên iPhone thật | Thêm Phím tắt từ file đã ký → dán mã → ghi 45 "Phở" Tiền mặt | Thông báo "✓ Đã ghi 45.000 ₫ · Phở" trong vòng 10 giây; có dòng mới trong sheet; Mac đồng bộ thì có giao dịch, đúng hạng mục, nguồn iPhone |
| M-21 | P2 | Ghi nhanh không mở khoá | Gán Phím tắt cho Chạm vào mặt sau (hoặc nút Tác vụ) → ghi 3 khoản liên tiếp, đếm giây | Mỗi khoản dưới 10 giây kể từ lúc chạm |
| M-22 | P2 | Mất sóng | Bật Chế độ máy bay → chạy Phím tắt → gõ một dòng vào app Google Sheets → tắt Chế độ máy bay → đồng bộ trên Mac | Phím tắt báo lỗi rõ ràng (không báo "Đã ghi"); dòng gõ trong Google Sheets về được Mac |
| M-23 | P1 | Lan tự cài Phím tắt | Gửi Lan file Phím tắt qua AirDrop và mã kết nối; không hướng dẫn thêm | Lan tự thêm được Phím tắt và ghi được một khoản |
| M-24 | P1 | Bản sao trên sheet thật | Cập nhật Code.gs (Deploy → New version) → Cài đặt → Đẩy ngay → mở sheet trên iPhone | Tab Giao dịch có đủ giao dịch của tháng, đúng ngày và số tiền; tab Tổng hợp có Tổng chi, hạng mục và cách trả khớp với Tổng quan trong app |
| M-25 | P2 | Ảnh lịch sử app ngân hàng | Chụp màn hình lịch sử giao dịch của app ngân hàng hay dùng → dán vào app | Đọc đúng từng khoản chi; ô Trả bằng là tên ngân hàng; khoản tiền vào bị bỏ qua |
| M-26 | P2 | Thông báo ngân sách trên Mac thật | Đặt ngân sách 1tr cho một hạng mục → thêm khoản 800k tháng này → thêm 50k → thêm 200k. Thêm một khoản 2tr vào tháng trước | Thông báo "… đã dùng 80% ngân sách tháng" hiện đúng một lần sau khoản 800k (không hiện lại sau khoản 50k); thông báo "đã vượt" hiện một lần sau khoản 200k; khoản tháng trước không gây thông báo. Nếu macOS hỏi quyền thông báo thì ghi lại tên app trong câu hỏi |
| M-27 | P2 | Vợ chọn giao diện Sáng | Trên máy để chế độ Tối, Lan vào Cài đặt → Giao diện → Sáng, tắt rồi mở lại app | App mở bằng nền sáng, không nháy tối lúc mở |

## Mức độ lỗi

| Mức | Định nghĩa | Ảnh hưởng tới release |
| --- | --- | --- |
| **S1 — Nghiêm trọng** | Mất hoặc sai dữ liệu tiền; không mở được app; lộ mật khẩu | Chặn release |
| **S2 — Cao** | Một luồng P1 không làm được, hoặc phải có người hướng dẫn mới làm được | Chặn release |
| **S3 — Trung bình** | Có cách khác để làm; hiển thị sai nhưng dữ liệu vẫn đúng | Được release nếu ghi rõ trong biên bản QA |
| **S4 — Thấp** | Chính tả, căn lề | Được release |
