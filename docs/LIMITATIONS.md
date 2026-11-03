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
| **Thống kê sử dụng** (Cài đặt, bật sẵn) chỉ tới Sheet **khi app đang mở và đã kết nối Google Sheet, bản sao đang bật**; nó đi cùng lần đẩy bản sao | Máy chưa kết nối hoặc tắt bản sao thì người cài không thấy gì; tắt app ngay sau khi mở thì "Mở app gần nhất" chờ tới lần mở sau | Xem trên máy đó: Cài đặt → Thống kê sử dụng → Xem dữ liệu sẽ gửi |
| Số đếm của thống kê sử dụng là **gần đúng**: tải lại trang tính là một lần mở, xem ống heo trong cùng một phút tính một lần, chỉ giữ 60 ngày; tắt rồi bật lại thì khoảng đã tắt không được ghi | Không dùng để đếm chính xác | Đủ để biết có dùng hay không và dùng việc gì |
| Lỗi gửi đi là **câu báo lỗi app hiện ra**: dãy từ 6 chữ số trở lên (số thẻ, số tài khoản, số tiền lớn) được thay bằng •, nhưng địa chỉ Gmail thì giữ | Ai mở được Sheet thì thấy địa chỉ Gmail trong lỗi Gmail | Tắt "Gửi thống kê sử dụng" nếu không muốn |
| Ngày của khoản chi là **lúc gửi**, không chọn được ngày khác | Ghi bù khoản hôm qua sẽ vào ngày hôm nay | Sửa ngày trong app Mac, hoặc gõ ngày vào cột Thời gian trong sheet trước khi đồng bộ |
| Lần cấp quyền đầu tiên, Google cảnh báo **"Google chưa xác minh ứng dụng này"** | Người cài có thể sợ và dừng lại | Đây là script của chính người dùng; bấm Nâng cao → Đi tới… (không an toàn). Xem `phone/README.md`, mục A |
| Sửa `Code.gs` thì phải **triển khai phiên bản mới** (Quản lý bản triển khai → Sửa → Phiên bản mới) | Nếu không, iPhone vẫn chạy code cũ | Địa chỉ /exec và mã kết nối giữ nguyên khi triển khai phiên bản mới. App Mac báo "Code.gs trên Google là bản cũ" khi `SCRIPT_VERSION` của sheet thấp hơn mức app cần |

## Gmail

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Chỉ đồng bộ **khi app đang mở và bạn bấm "Đồng bộ ngay"** | Không có đồng bộ chạy ngầm; số liệu chỉ mới tới lần đồng bộ gần nhất | Mở app và bấm đồng bộ mỗi tuần |
| Cần **Xác minh 2 bước** và **App Password** | Bước cài đặt khó nhất với người mới (xem test case M-02). Google không cho tạo App Password với tài khoản chỉ dùng passkey/khoá bảo mật hay Advanced Protection | Màn hình hướng dẫn 3 bước trong app; không tạo được thì dùng "Gmail qua Google Sheet" (mục dưới) |
| Tài khoản Google Workspace (email công ty/trường) có thể **bị quản trị viên chặn** App Password hoặc IMAP | Không kết nối được | Dùng Gmail cá nhân để nhận email đơn hàng |
| App Password **bị Google thu hồi** khi bạn đổi mật khẩu Google | Đồng bộ báo lỗi đăng nhập | Gỡ rồi thêm lại tài khoản với App Password mới |
| Đọc email bằng **mẫu cố định** (regex), không dùng AI | Khi Shopee/TikTok đổi mẫu email, có thể không đọc được số tiền; đơn có nhiều sản phẩm được xếp theo sản phẩm khớp đầu tiên | Email lỗi hiện trong "Email chưa đọc được"; sửa `parsers.py` rồi bấm "Phân tích lại". Đơn sai hạng mục thì đổi tay |
| Số tiền lấy là **tổng thanh toán của cả đơn** | Không tách được từng sản phẩm của một đơn sang các hạng mục khác nhau | Ghi rõ là giới hạn đã biết |
| Lần đầu chỉ lấy **180 ngày** gần nhất | Không có đơn cũ hơn | Sửa bộ lọc ở Cài đặt → Nâng cao (ví dụ `newer_than:2y`) |
| Chỉ hỗ trợ **Gmail** | Không đọc được Outlook, Yahoo, iCloud Mail | Chuyển tiếp email đơn hàng sang Gmail |
| **Shopee/TikTok có thể không gửi email cho từng đơn.** Khi thử với hộp thư thật (31/10/2026), 180 ngày chỉ có bản tin, khảo sát và email tuyển dụng của Shopee, không có email đơn hàng nào | Nguồn Gmail có thể trống với nhiều người | Chụp màn hình trang "Đơn mua" (nhiều đơn trên một ảnh) và thêm ở ô Ảnh chụp; sau khi đồng bộ, app tự giải thích nếu không tìm thấy email đơn hàng |
| **Không đọc Spam và Thùng rác** (chỉ đọc All Mail: Hộp thư đến, các tab Quảng cáo/Mạng xã hội/Cập nhật, thư đã lưu trữ) | Email đơn hàng bị Gmail đưa vào Spam sẽ bị bỏ sót | Đây là chủ ý: Spam hay có email giả danh Shopee/MoMo, đọc vào sẽ sinh giao dịch giả. Nếu thấy email thật nằm trong Spam, bấm "Không phải thư rác" rồi đồng bộ lại |
| Mẫu email biên lai **MoMo** mới được viết theo biên lai hiển thị trong app MoMo, **chưa kiểm chứng với email MoMo thật** | Có thể không đọc được số tiền | Email lỗi hiện trong "Email chưa đọc được" kèm nội dung; gửi một mẫu (che số tài khoản) để chỉnh bộ đọc |

## Gmail qua Google Sheet (không cần App Password)

Cách cài: `docs/DEPLOY.md` mục G.

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Apps Script quét Gmail **mỗi 30 phút** | Đơn mới đến app chậm tối đa khoảng 30 phút (cộng thời gian tới lần đồng bộ kế tiếp của app) | Chạy `quetEmail` bằng tay trong Apps Script nếu cần ngay |
| Chỉ đọc **Gmail của chủ sheet**; thư của người khác chỉ có khi **bộ lọc chuyển tiếp** trong Gmail của họ gửi sang | Thư không khớp bộ lọc (người gửi khác, đã có trước khi tạo bộ lọc) không bao giờ tới app | Bộ lọc `from:(shopee OR tiktok OR momo)`; thư cũ chuyển tiếp tay (app nhận ra thư "Fwd:") |
| Google bắt cấp **toàn quyền Gmail** (`https://mail.google.com/`) cho `GmailApp`, không có mức chỉ đọc | Màn hình xin quyền đáng sợ; script về lý thuyết gửi/xoá được thư | Code chỉ tìm và đọc thư, chạy trong tài khoản của chủ sheet. Chỉ đọc thì phải chuyển sang Gmail API (chưa làm, xem DEPLOY mục G) |
| Từ Code.gs bản 3, **mọi** sheet dùng bản này đều được hỏi quyền Gmail, kể cả khi chỉ dùng iPhone | Deploy bản 3 khi chưa Allow có thể làm Google trả "Authorization is required" cho cả Phím tắt | Chạy `batQuetEmail` (hoặc `caiDat`) → Allow trước khi Deploy → New version |
| Nội dung email bị **cắt ở 45.000 ký tự** (ô Sheets tối đa 50.000) | Email rất dài có thể mất phần tổng tiền ở cuối | Hiện trong "Email chưa đọc được"; email đơn hàng thường dưới 10.000 ký tự |
| Tab Email chỉ giữ **90 ngày / 1000 dòng**; câu tìm mặc định chỉ lấy **30 ngày** | Lần bật đầu tiên không có đơn cũ hơn 30 ngày | Sửa `EMAIL_QUERY` trong Script properties (tối đa 90 ngày còn ý nghĩa) |
| Email đi qua **Google Sheet trong Drive** của chủ sheet | Ai được chia sẻ sheet đọc được nội dung email đơn hàng | Không chia sẻ sheet; tab Email chỉ có thư khớp câu tìm |
| **Shopee/TikTok có thể không gửi email cho từng đơn** (như mục Gmail ở trên) | Tab Email chỉ có bản tin, khảo sát | Chụp màn hình trang "Đơn mua" |

## Bot Telegram (nhóm gia đình)

Cách cài: `docs/DEPLOY.md` mục H.

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| Bot đọc tin nhắn **mỗi phút** (Apps Script không nhận webhook được); Code.gs 5 chờ tin tiếp theo (long polling) trong **khoảng 2 phút** sau mỗi tin | Tin **đầu tiên** sau lúc im lặng vẫn chậm tới khoảng 1 phút; sau đó trả lời và nút bấm gần như ngay (giữa hai lượt chạy có thể trễ vài giây) | Bấm một lần rồi đợi; bấm lại chỉ hiện "Đã ghi rồi", không ghi trùng |
| Trả lời nhanh tối đa **40 phút/ngày** (`TG_FAST_MINUTES`), tính vào quota trigger 90 phút/ngày | Ngày nhắn rất nhiều: hết 40 phút thì về chế độ mỗi phút như Code.gs 4 tới 0 giờ | `kiemTraTelegram` in số phút đã dùng và chế độ hiện tại |
| Bot tự chọn hạng mục theo **từ khoá app Mac gửi lên** (máy đẩy bản sao gần nhất) | Sửa từ khoá trên Mac chỉ có hiệu lực với bot sau lần đẩy kế tiếp; Mac 1.4.0 không gửi từ khoá nên bot luôn hỏi bằng nút | Mở app 1.5.0 trên Mac (tự đẩy khi có thay đổi) |
| Không gõ cách trả thì bot dùng **cách trả lần trước** của người gõ | Lần này trả khác mà quên gõ thì ghi sai cách trả; tin "Đã ghi" chỉ có nút đổi hạng mục | Gõ cách trả ở cuối (`tm`, `ck`, `visa`, `momo`), hoặc ↩️ Huỷ rồi gõ lại; sửa trên Mac |
| **✏️ Đổi hạng mục** chỉ được khi Mac **chưa lấy** khoản đó | Mac đã đồng bộ thì bot báo "đổi trong app trên Mac" | Đổi trong app trên Mac |
| Báo cáo tính tới **lần Mac đồng bộ gần nhất**, cộng các khoản ghi qua Telegram/iPhone sau đó (dòng "Số liệu tới…") | Khoản nhập tay trên Mac, sao kê, sửa/xoá trên Mac chỉ vào báo cáo sau khi Mac mở và đẩy bản sao | Mở app trên Mac (tự đẩy khi mở) |
| **Đơn Gmail, ảnh chụp** chỉ vào app khi **một Mac mở** | Không thấy trong báo cáo Telegram cho tới lúc đó, kể cả khi tab Email đã có thư | Mở app trên Mac |
| Khoản chọn ✨ Tự động nằm ở **"Chưa phân loại (chờ Mac)"** cho tới khi Mac phân loại | % theo hạng mục lệch trong lúc chờ | Chọn hạng mục cụ thể bằng nút |
| Bấm **↩️ Huỷ** sau khi Mac đã lấy khoản đó: báo cáo vẫn tính nó cho tới lần Mac đồng bộ kế tiếp; app **1.4.0** không biết huỷ | Số tạm thời cao hơn | App 1.5.0 tự đánh dấu "Không tính" khi đồng bộ; app 1.4.0 thì xoá tay |
| Tin nhắn Telegram **không mã hoá đầu cuối** (nhóm và bot đi qua máy chủ Telegram) | Telegram đọc được số tiền, nội dung các khoản và báo cáo | Không gõ số thẻ, số tài khoản vào nhóm. Không dùng thì `tatTelegram` |
| Token bot nằm trong **Script properties** của sheet | Ai sửa được script của sheet thì lấy được token và điều khiển bot | Không chia sẻ quyền sửa sheet; lộ thì @BotFather → `/revoke`, đặt token mới, chạy `batTelegram` |
| Ai đã ở trong nhóm đã kết nối đều **ghi, huỷ và xem báo cáo** được | Thêm người lạ vào nhóm là cho họ xem số liệu | Nhóm chỉ có hai vợ chồng; lộ mã `/ketnoi` thì `doiMaTelegram` |
| Privacy mode của bot phải **tắt** (`/setprivacy` → Disable) | Quên bước này thì trong nhóm bot chỉ thấy lệnh, gõ "45k phở" không có gì xảy ra | `batTelegram` và `/huongdan` báo khi còn bật; tắt xong phải xoá bot khỏi nhóm và thêm lại |
| Lịch mỗi phút dùng khoảng **8–25 phút/ngày**, cộng phần trả lời nhanh (thường 20–30, tối đa 40 phút) trong quota trigger **90 phút/ngày** của tài khoản Gmail thường (cùng quota với quét Gmail mục G) | Hết quota thì bot im tới khi quota hồi lại | Xem Executions; hạ `TG_FAST_MINUTES`; `tatTelegram` khi không dùng |
| Tắt bot (hoặc hết quota) **quá 24 giờ** thì Telegram xoá các tin chưa đọc | Khoản gõ trong lúc đó bị mất, bot không trả lời | Gõ lại sau khi bật |
| Số tiền đọc theo **mẫu cố định**: phải bắt đầu bằng số (`45k phở`, không phải `phở 45k`); số trần dưới 1.000 thì bot hỏi lại; tin nhắn thường bắt đầu bằng số ("5 phút nữa về") cũng bị hỏi | Phải bấm Huỷ cho những câu đó | Không có gì được ghi khi chưa bấm hạng mục |
| Chỉ có **hạng mục mặc định** trên nút (như Phím tắt iPhone); không gửi ảnh hoá đơn qua bot | Hạng mục tự tạo trên Mac không có nút (nhưng từ khoá của nó vẫn được bot dùng); ảnh gửi vào nhóm bị bỏ qua | Thêm từ khoá cho hạng mục đó trên Mac, hoặc chọn ✨ Tự động rồi đổi trên Mac; ảnh thì thêm trên Mac |
| Mỗi sheet cần **một bot riêng**; hai Mac cùng đẩy bản sao thì báo cáo chỉ dùng **máy đẩy gần nhất** | Bot dùng chung giữa TEST và PRODUCTION sẽ mất tin | Tạo bot TEST riêng |

## Ảnh chụp (OCR)

| Giới hạn | Ảnh hưởng | Cách xử lý |
| --- | --- | --- |
| OCR có thể đọc sai ảnh mờ, ảnh chụp màn hình máy tính bằng điện thoại, hoặc chữ nằm đè lên hình nền | Sai số tiền | Màn hình duyệt kết quả bắt buộc xem trước khi lưu; số tiền sửa được |
| Ngày lấy từ ảnh (ưu tiên ngày cạnh nhãn "Thời gian", bỏ ngày trong tương lai); ảnh không có ngày, như trang Đơn mua của Shopee, thì tạm lấy **ngày hôm nay** | Giao dịch có thể rơi vào sai tháng | Ô ngày được **tô vàng** kèm lời nhắc; sửa trong màn hình duyệt |
| **Không dùng AI:** chữ do Vision của macOS đọc ngay trên máy (không cần mạng), số tiền, ngày, nơi trả lấy bằng quy tắc cố định. App không tự thêm thông tin, nhưng OCR có thể **đọc nhầm** chữ số (ví dụ "2.802.271đ" thành "2.802.2710") | Có thể sai số tiền | Ảnh gốc hiện ngay cạnh kết quả, phần chữ đọc được mở sẵn; không lưu gì khi chưa bấm Lưu |
| Màn hình lịch sử: giao dịch bị cắt ở mép ảnh, hoặc dòng đọc không ra số tiền, sẽ bị bỏ qua | Thiếu giao dịch | App báo "N giao dịch không đọc được hoặc bị cắt"; chụp tiếp phần còn lại |
| Ảnh không có dòng "Tổng": app đưa ra mọi số tiền và chọn sẵn số lớn nhất (trừ dòng khách đưa, tiền thừa, giảm giá) | Có thể chọn nhầm | Kiểm tra dòng được chọn trước khi lưu |
| Tiền vào ("+", "Nhận tiền") được ghi là **Thu** và chọn sẵn (trừ tiền lãi); khoản đã có trong app (cùng số tiền, lệch ≤ 1 ngày) được bỏ chọn. **Rút tiền ATM** không chọn sẵn vì chỉ là chuyển sang tiền mặt | Hai khoản thu khác nhau nhưng trùng số tiền trong 1 ngày sẽ bị bỏ chọn nhầm | Đổi Chi/Thu và tick lại ở từng dòng trong màn hình duyệt |
| Màn hình lịch sử app ngân hàng thường **không ghi tên ngân hàng** | Ô Trả bằng để trống | App nhắc chọn; chọn một lần cho cả ảnh |
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
| Chạy trên **macOS 11** (Big Sur) trở lên, có **hai file cài đặt**: chip Apple (`-arm64.dmg`) và chip Intel (`-x86_64.dmg`) | Chọn nhầm file thì app không mở. Không chạy trên Windows hay Linux | Xem chip ở  → About This Mac. Xem bảng "macOS 11/12 so với 13+" bên dưới |
| Bản Intel được build và smoke test **dưới Rosetta** trên Mac chip Apple, chưa thử trên Mac Intel thật trước khi giao | Lỗi chỉ có trên CPU Intel thật sẽ chỉ lộ ra ở máy người dùng | Ca M-01 trên đúng máy Intel trước khi kết luận GO |
| **Không có chữ ký số của Apple** | Lần đầu mở phải bấm "Open Anyway"; một số máy công ty chặn hẳn | Có tài khoản Apple Developer (99 USD/năm) thì ký và notarize được |
| **Không tự cập nhật** | Người dùng phải nhận và cài file `.dmg` mới bằng tay | Gửi bản mới qua Zalo; cài đè lên bản cũ thì dữ liệu vẫn giữ. Lần mở đầu tiên của bản mới tự chép `budget.db` vào `backups/` (giữ 10 bản gần nhất); quay về bản cũ xem `docs/DEPLOY.md` mục F |
| Sau khi cập nhật, macOS có thể **hỏi quyền truy cập Keychain** | Vì chữ ký ad-hoc thay đổi theo mỗi lần build | Chọn "Always Allow" |

### macOS 11/12 so với 13+

| Tính năng | macOS 11, 12 | macOS 13+ |
| --- | --- | --- |
| Nhập tay, Tổng quan, ngân sách, cảnh báo, xuất CSV | Có | Có |
| Nhập từ iPhone (Google Sheet), bản sao lên Sheet | Có | Có |
| Gmail (Shopee/TikTok), sao kê Excel/CSV/PDF, đối chiếu | Có | Có |
| **Đọc ảnh chụp** (biên lai MoMo, chuyển khoản, "Đơn mua") | **Không**: Vision của macOS chỉ đọc tiếng Việt từ macOS 13. App báo "Đọc ảnh cần macOS 13 trở lên…" thay vì treo | Có |
| Giao diện | Cửa sổ app dùng WebKit của hệ điều hành (macOS 11 ≈ Safari 14). Trang đã bỏ các tính năng mới hơn Safari 14 (`tests/test_webkit_compat.py`). Trên macOS 11.0–11.2 (Safari 14.0) khoảng cách giữa một số nút có thể sát hơn và ô ngày là ô gõ chữ (YYYY-MM-DD): cập nhật Big Sur lên bản mới nhất | Đầy đủ |
| "Open Anyway" lần đầu | System Preferences → Security & Privacy → General | System Settings → Privacy & Security |

Chưa có máy macOS 11/12 thật để thử: các dòng trên dựa trên `minos` của từng file trong app (`release.py check`), phiên bản WebKit và tài liệu Vision. Ca M-01 trên máy cũ là phép thử thật.

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
