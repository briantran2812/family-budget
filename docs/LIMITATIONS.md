# Giới hạn khi chạy local

App chạy hoàn toàn trên một máy Mac: không có server, không có tài khoản online. Thiết kế này giúp dữ
liệu riêng tư và không tốn chi phí, nhưng kéo theo các giới hạn dưới đây. Mỗi giới hạn kèm cách
xử lý hiện có, nếu có.

## Dữ liệu và đồng bộ giữa các máy

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Dữ liệu chỉ nằm trên **một máy** | Vợ và chồng cài trên hai máy sẽ có hai bộ số liệu riêng; không xem chung được | Dồn về một máy và thêm Gmail của cả hai vào máy đó (Cài đặt → Thêm Gmail). Hoặc mỗi người xuất CSV rồi gộp lại |
| **Không sao lưu tự động** | Mất máy, hỏng ổ cứng hay cài lại macOS thì mất dữ liệu | Định kỳ chép `~/Library/Application Support/ThuChiGiaDinh/budget.db` ra ổ ngoài hoặc iCloud Drive, hoặc dùng Time Machine |
| **Không được** đặt file `budget.db` trong thư mục iCloud hay Dropbox để hai máy cùng mở | SQLite có thể hỏng file khi hai máy ghi cùng lúc | Chỉ chép ra đó làm bản sao lưu, không mở trực tiếp |
| **Database không mã hoá** | Người dùng chung tài khoản macOS hoặc có quyền admin đọc được số liệu chi tiêu | Bật FileVault; mỗi người một tài khoản macOS riêng. Riêng mật khẩu Gmail thì nằm trong Keychain, không nằm trong database |

## Nhập từ iPhone (Google Sheet)

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Khoản ghi trên iPhone **đi qua Google** (Apps Script và Google Sheet trong Drive của người dùng) | Không còn đúng hoàn toàn câu "dữ liệu chỉ nằm trên máy này" khi bật tính năng này | Tính năng tuỳ chọn; dữ liệu nằm trong Drive của chính người dùng, không qua server nào khác |
| **Ai có mã kết nối đều ghi và đọc được** sheet | Lộ mã thì người lạ đọc được các khoản ghi từ điện thoại và ghi thêm dòng rác | Gửi mã qua AirDrop hoặc Universal Clipboard, không dán lên nhóm chat. Lộ mã thì chạy `doiMa` trong Apps Script rồi dán mã mới vào app Mac và Phím tắt |
| Phím tắt **cần mạng**. Mất sóng thì Phím tắt báo lỗi và không ghi gì | Mất khoản chi nếu người dùng không để ý thông báo lỗi | Gõ thẳng vào sheet bằng app Google Sheets (app này lưu tạm khi mất sóng); app Mac vẫn lấy về được |
| Sửa hoặc xoá dòng trong sheet **sau khi** Mac đã lấy về thì app **không** cập nhật theo | Hai bên lệch nhau | Sửa hoặc xoá thẳng trong app Mac. Sửa trong sheet chỉ có tác dụng trước lần đồng bộ |
| Danh sách hạng mục trên iPhone là **danh sách mặc định** lúc tạo Phím tắt | Hạng mục thêm hoặc đổi tên trong app không tự có trên iPhone; chọn mục không khớp thì app tự phân loại theo từ khoá | Sửa bước Danh sách trong Phím tắt cho khớp tên mới |
| Tab **Giao dịch** và **Tổng hợp** chỉ là **bản sao để xem**. Sửa trong sheet sẽ bị ghi đè ở lần đẩy sau | | Sửa trong app trên Mac |
| Hai Mac cùng bật bản sao thì mỗi khoản nhập từ iPhone **xuất hiện hai lần** trong tab Giao dịch (mỗi máy một dòng, khác cột Máy) | Cộng cả tab sẽ ra số gấp đôi | Chỉ bật "Ghi bản sao" trên một Mac làm sổ chính, hoặc lọc theo cột Máy |
| Thay đổi chỉ được đẩy **khi app đang mở** (khoảng 10 giây sau thay đổi, và mỗi lần mở app) | Tắt app ngay sau khi sửa thì lần đẩy đó bị bỏ, đến lần mở sau mới đẩy | Bấm "Đẩy ngay" trong Cài đặt trước khi tắt nếu cần |
| Ngày của khoản chi là **lúc gửi**, không chọn được ngày khác | Ghi bù khoản hôm qua sẽ vào ngày hôm nay | Sửa ngày trong app Mac, hoặc gõ ngày vào cột Thời gian trong sheet trước khi đồng bộ |
| Lần cấp quyền đầu tiên, Google cảnh báo **"Google chưa xác minh ứng dụng này"** | Người cài có thể sợ và dừng lại | Đây là script của chính người dùng; bấm Nâng cao → Đi tới… (không an toàn). Xem `phone/README.md`, mục A |
| Sửa `Code.gs` thì phải **triển khai phiên bản mới** (Quản lý bản triển khai → Sửa → Phiên bản mới) | Nếu không, iPhone vẫn chạy code cũ | Địa chỉ /exec và mã kết nối giữ nguyên khi triển khai phiên bản mới |

## Gmail

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Chỉ đồng bộ **khi app đang mở và bạn bấm "Đồng bộ ngay"** | Không có đồng bộ chạy ngầm; số liệu chỉ mới tới lần đồng bộ gần nhất | Mở app và bấm đồng bộ mỗi tuần |
| Cần **Xác minh 2 bước** và **App Password** | Bước cài đặt khó nhất với người mới (xem test case M-02) | Màn hình hướng dẫn 3 bước trong app |
| Tài khoản Google Workspace (email công ty/trường) có thể **bị quản trị viên chặn** App Password hoặc IMAP | Không kết nối được | Dùng Gmail cá nhân để nhận email đơn hàng |
| App Password **bị Google thu hồi** khi bạn đổi mật khẩu Google | Đồng bộ báo lỗi đăng nhập | Gỡ rồi thêm lại tài khoản với App Password mới |
| Đọc email bằng **mẫu cố định** (regex), không dùng AI | Khi Shopee/TikTok đổi mẫu email, có thể không đọc được số tiền; đơn có nhiều sản phẩm được xếp theo sản phẩm khớp đầu tiên | Email lỗi hiện trong "Email chưa đọc được"; sửa `parsers.py` rồi bấm "Phân tích lại". Đơn sai hạng mục thì đổi tay |
| Số tiền lấy là **tổng thanh toán của cả đơn** | Không tách được từng sản phẩm của một đơn sang các hạng mục khác nhau | Ghi rõ là giới hạn đã biết |
| Lần đầu chỉ lấy **180 ngày** gần nhất | Không có đơn cũ hơn | Sửa bộ lọc ở Cài đặt → Nâng cao (ví dụ `newer_than:2y`) |
| Chỉ hỗ trợ **Gmail** | Không đọc được Outlook, Yahoo, iCloud Mail | Chuyển tiếp email đơn hàng sang Gmail |
| **Shopee/TikTok có thể không gửi email cho từng đơn.** Khi thử với hộp thư thật (31/10/2026), 180 ngày chỉ có bản tin, khảo sát và email tuyển dụng của Shopee, không có email đơn hàng nào | Nguồn Gmail có thể trống với nhiều người | Chụp màn hình trang "Đơn mua" (nhiều đơn trên một ảnh) và thêm ở ô Ảnh chụp; sau khi đồng bộ, app tự giải thích nếu không tìm thấy email đơn hàng |
| **Không đọc Spam và Thùng rác** (chỉ đọc All Mail: Hộp thư đến, các tab Quảng cáo/Mạng xã hội/Cập nhật, thư đã lưu trữ) | Email đơn hàng bị Gmail đưa vào Spam sẽ bị bỏ sót | Đây là chủ ý: Spam hay có email giả danh Shopee/MoMo, đọc vào sẽ sinh giao dịch giả. Nếu thấy email thật nằm trong Spam, bấm "Không phải thư rác" rồi đồng bộ lại |
| Mẫu email biên lai **MoMo** mới được viết theo biên lai hiển thị trong app MoMo, **chưa kiểm chứng với email MoMo thật** | Có thể không đọc được số tiền | Email lỗi hiện trong "Email chưa đọc được" kèm nội dung; gửi một mẫu (che số tài khoản) để chỉnh bộ đọc |

## Ảnh chụp (OCR)

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| OCR có thể đọc sai ảnh mờ, ảnh chụp màn hình máy tính bằng điện thoại, hoặc chữ nằm đè lên hình nền | Sai số tiền | Màn hình duyệt kết quả bắt buộc xem trước khi lưu; số tiền sửa được |
| Ngày lấy từ ảnh (ưu tiên ngày cạnh nhãn "Thời gian", bỏ ngày trong tương lai); ảnh không có ngày, như trang Đơn mua của Shopee, thì tạm lấy **ngày hôm nay** | Giao dịch có thể rơi vào sai tháng | Ô ngày được **tô vàng** kèm lời nhắc; sửa trong màn hình duyệt |
| **Không dùng AI:** chữ do Vision của macOS đọc ngay trên máy (không cần mạng), số tiền, ngày, nơi trả lấy bằng quy tắc cố định. App không tự thêm thông tin, nhưng OCR có thể **đọc nhầm** chữ số (ví dụ "2.802.271đ" thành "2.802.2710") | Có thể sai số tiền | Ảnh gốc hiện ngay cạnh kết quả, phần chữ đọc được mở sẵn; không lưu gì khi chưa bấm Lưu |
| Màn hình lịch sử: giao dịch bị cắt ở mép ảnh, hoặc dòng đọc không ra số tiền, sẽ bị bỏ qua | Thiếu giao dịch | App báo "N giao dịch không đọc được hoặc bị cắt"; chụp tiếp phần còn lại |
| Ảnh không có dòng "Tổng": app đưa ra mọi số tiền và chọn sẵn số lớn nhất (trừ dòng khách đưa, tiền thừa, giảm giá) | Có thể chọn nhầm | Kiểm tra dòng được chọn trước khi lưu |
| Tiền vào ("+", "Nhận tiền") được ghi là **Thu**; trên màn hình lịch sử thì để bỏ chọn sẵn | | Đổi Chi/Thu ở từng dòng trong màn hình duyệt |
| Mỗi ảnh là một lần nhập thủ công | Không phù hợp để nhập hàng trăm giao dịch | Xem phần ngân hàng bên dưới: tính năng nhập sao kê sẽ giải quyết việc này |

## Ngân hàng

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| **Không kết nối trực tiếp được với ngân hàng.** Việt Nam chưa có Open Banking cho cá nhân; các dịch vụ trung gian như Casso hay SePay cần gửi dữ liệu lên server của họ | Không tự lấy được giao dịch chuyển khoản, quẹt thẻ | Chụp màn hình biên lai chuyển khoản (đã hỗ trợ và đã test với mẫu của Vietcombank, Techcombank, MB) |
| Bộ đọc sao kê nhận ra cột theo **tên cột phổ biến** (Ngày GD, Diễn giải, Ghi nợ/Ghi có, Amount…), mới được kiểm thử với file mẫu chứ chưa với file thật của từng ngân hàng | Sao kê của một số ngân hàng có thể không đọc được | App báo "không tìm thấy dòng tiêu đề" hoặc "không đọc được dòng nào"; gửi một mẫu (che số thẻ) để bổ sung |
| Không đọc được file **.xls** (Excel cũ) và **PDF dạng ảnh scan** (không có chữ thật) | | Mở .xls bằng Excel/Numbers rồi lưu thành .xlsx/.csv; với PDF dạng ảnh, dùng file Excel từ internet banking |
| Giao dịch ngoại tệ: chỉ lấy cột **VND** | Sao kê chỉ có cột ngoại tệ thì sai số tiền | Dùng sao kê có cột quy đổi VND |
| Ghép theo: **cùng số tiền (lệch ≤ 1.000đ), ngày lệch ≤ 3 ngày**. Lệch đến 15% thì chỉ **gợi ý**, không tự ghép | Hai khoản cùng số tiền trong cùng vài ngày có thể bị ghép chéo | Xem lại nhóm "Đã khớp"; bấm Bỏ ghép rồi Ghép với… để sửa |
| Kỳ sao kê lấy từ **dòng đầu đến dòng cuối** trong file, không đọc ngày chốt sao kê | Khoản ghi tay sau dòng cuối cùng không được đưa vào nhóm "không có trên sao kê" | Đúng với mục đích đối chiếu |
| Xoá sao kê **giữ lại** các giao dịch đã thêm từ sao kê đó | | Muốn bỏ thì bấm "Hoàn tác thêm" trước khi xoá sao kê |
| Chưa đọc **email/SMS biến động số dư** | Như trên | Email: làm được với ngân hàng gửi email thông báo. SMS: chỉ làm được nếu iPhone đồng bộ tin nhắn sang Mac và app được cấp quyền Full Disk Access, nên chưa làm |

## Cài đặt và cập nhật

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Chỉ chạy trên **Mac chip Apple**, **macOS 13** trở lên | Không chạy trên Mac Intel, Windows hay Linux | Build Intel cần Python bản universal2; chưa làm |
| **Không có chữ ký số của Apple** | Lần đầu mở phải bấm "Open Anyway"; một số máy công ty chặn hẳn | Có tài khoản Apple Developer (99 USD/năm) thì ký và notarize được |
| **Không tự cập nhật** | Người dùng phải nhận và cài file `.dmg` mới bằng tay | Gửi bản mới qua Zalo; cài đè lên bản cũ thì dữ liệu vẫn giữ |
| Sau khi cập nhật, macOS có thể **hỏi quyền truy cập Keychain** | Vì chữ ký ad-hoc thay đổi theo mỗi lần build | Chọn "Always Allow" |

## Cảnh báo ngân sách

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Thông báo trên Mac chỉ hiện **khi app đang mở**, ngay sau lần thêm, sửa hoặc đồng bộ làm hạng mục chạm 80% hoặc vượt 100% | Khoản ghi trên iPhone lúc app tắt chỉ gây thông báo ở lần đồng bộ sau khi mở app | Cảnh báo vẫn nằm ở đầu trang Tổng quan mỗi lần mở app |
| Thông báo hiện dưới tên **Script Editor** (gửi bằng `osascript`); nếu đã tắt thông báo của Script Editor thì không thấy gì | Bỏ lỡ thông báo | System Settings → Notifications → Script Editor → bật Allow Notifications |
| Mỗi mức chỉ báo **một lần mỗi tháng**: tăng ngân sách hay xoá bớt khoản chi rồi lại chạm mức thì không báo lại | | Cảnh báo ở Tổng quan luôn theo số liệu hiện tại |
| **iPhone chưa nhận cảnh báo** | Ghi khoản chi trên iPhone không biết hạng mục đã gần hết ngân sách | Xem Tổng quan trên Mac; tab Tổng hợp của Google Sheet có số chi theo hạng mục |

## Ống heo

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Tháng được ghi **khi app mở** vào ngày cuối tháng hoặc lần đầu mở sau đó, không phải lúc nửa đêm | Mở app vào ngày cuối tháng thì khoản chi tối hôm đó chưa có trong số đã ghi | Hiện "Số liệu tháng này đã đổi"; bấm **Cập nhật** |
| Số đã ghi là **ảnh chụp** lúc ghi; khoản thêm muộn (sao kê tháng trước, đơn Gmail về trễ) không tự cộng vào | Ống heo lệch với "Còn lại" của tháng đó | Mở ống heo, bấm **Cập nhật** ở tháng có dòng "đã đổi" |
| "Còn lại" chỉ là **thu − chi đã ghi trong app**, không phải số dư thật của tài khoản ngân hàng | Quên ghi lương hay khoản chi tiền mặt thì ống heo sai theo | Ghi đủ; đối chiếu sao kê để tìm khoản thiếu |
| Tháng **chưa có khoản thu nào** thì không ghi (thường là dữ liệu chưa đủ, ví dụ đơn Shopee 6 tháng lấy từ Gmail lúc mới kết nối) | Tháng thật sự không có thu nhập không hiện trong ống heo | Ghi khoản thu của tháng đó; lần mở app sau tháng đó được ghi |

## Khác

| Giới hạn | Ảnh hưởng |
| --- | --- |
| Chỉ hỗ trợ **VND** | Khoản chi bằng ngoại tệ phải tự quy đổi |
| Ngân sách tính **theo tháng dương lịch** | Không đặt được kỳ ngân sách theo ngày nhận lương (ví dụ từ ngày 5 tới ngày 4 tháng sau) |
| Không có quyền riêng cho từng người dùng | Ai mở được app trên máy thì thấy toàn bộ số liệu |
| Server nội bộ chạy ở `127.0.0.1` | Chặn được trang web lạ gọi vào app (nhờ kiểm tra Host và header riêng), nhưng một chương trình khác đang chạy trên chính máy đó vẫn đọc được dữ liệu. Mức này tương đương với việc chương trình đó đọc thẳng file database |
