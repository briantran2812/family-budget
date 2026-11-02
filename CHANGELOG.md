# Changelog

## Chưa phát hành — nhập từ iPhone

- **Ghi khoản chi trên iPhone, không cần mở Mac:** Phím tắt "Ghi chi tiêu" hỏi số tiền, nội dung và cách trả, rồi
  gửi tới Apps Script trong tài khoản Google của người dùng. Script ghi một dòng vào sheet "Hộp thư đến". App trên Mac
  tự lấy các dòng mới mỗi lần mở (tab Nhập liệu → Từ iPhone), tự phân loại, không nhập trùng, và gộp với khoản đã
  thêm từ sao kê nếu có. Dòng gõ thẳng vào sheet bằng app Google Sheets (dùng được khi mất sóng) cũng được lấy về.
- Trên iPhone gõ đúng số tiền (45000); câu hỏi kế tiếp hiện lại số đã định dạng ("45.000 ₫ — chi cho gì?") để thấy ngay khi thiếu số 0. Dưới 1.000 ₫ bị từ chối. Dòng gõ tay trong sheet vẫn nhận 45k, 1tr5, 1,5tr, 1.500.000.
- **Bản sao trên Google Sheet:** app Mac ghi mọi giao dịch vào tab "Giao dịch" và số tổng theo tháng (theo hạng mục,
  theo cách trả) vào tab "Tổng hợp", vài giây sau mỗi thay đổi. Mỗi Mac ghi đè phần của mình (cột Máy). Sheet chỉ để
  xem; app trên Mac vẫn là dữ liệu gốc.
- **Cách trả:** biểu tượng theo cách trả (💵 💳 🏦 👛), lọc theo cách trả, thẻ "Chi theo cách trả" ở Tổng quan; hai ô
  nguồn ở Tổng quan là hai nguồn chi nhiều nhất trong tháng.
- **Ảnh chụp:** đọc màn hình lịch sử giao dịch (MoMo, app ngân hàng); tự nhận ra nguồn tiền (ví, ngân hàng) và có ô
  "Trả bằng" ở màn hình duyệt; khoản đã có trong app được bỏ chọn sẵn.
- Mã kết nối nằm trong Keychain. Đổi mã bằng hàm `doiMa`; mã cũ ngừng hoạt động ngay.
- Code: `phone/Code.gs` (Apps Script), `phone/make_shortcut.py` (tạo và ký file Phím tắt), `phone_inbox.py`.
  Hướng dẫn cài và test: `phone/README.md`.

## 1.3.0 — đối chiếu sao kê

- **Tab Đối chiếu (góp ý của người dùng):** nhập sao kê thẻ Visa hoặc tài khoản ngân hàng (CSV, Excel, PDF, kể cả
  PDF có mật khẩu) rồi đối chiếu với khoản ghi tay, Gmail và ảnh chụp. Kết quả chia thành:
  - Khớp;
  - Chưa ghi trong app (bấm "Thêm vào app");
  - Gần khớp (ghép và sửa số tiền theo sao kê);
  - Ghi là trả bằng thẻ này nhưng không có trên sao kê;
  - Bỏ qua (thanh toán thẻ được bỏ qua tự động).
  Lựa chọn của người dùng được giữ qua các lần đối chiếu.
- **Trường "Trả bằng"** trên giao dịch; lần nhập sau tự điền sẵn thẻ đã dùng lần trước.
- **Không tính trùng:** đơn Gmail về sau được gộp vào giao dịch đã thêm từ sao kê.
- **Ô Shopee / TikTok / Số giao dịch bấm được:** mở danh sách giao dịch đã lọc sẵn (góp ý của người dùng).
- **Sửa lỗi:**
  - Đọc PDF theo vị trí dòng: PDFKit tách bảng thành các khối cột khi mô tả ngắn (test UX phát hiện).
  - Dấu CR trên sao kê thẻ không còn bị hiểu là dấu trừ.
  - Màu chữ của nút dạng link (lỗi S4 của bản 1.2.0).
- Thêm từ khoá ăn uống và quần áo; dữ liệu mẫu có thêm khoản quẹt Visa và sao kê Visa tháng 10.

## 1.2.0 — bản đầu tiên qua cổng QA

- **Quy trình:** có test tự động (unit, integration, OCR, E2E UX trên WebKit, smoke test bản đóng
  gói), bộ test case UX, tài liệu giới hạn, và script release có cổng QA.
- **Sửa lỗi (bắt được nhờ dữ liệu mẫu và test):**
  - Email "đang giao" đến cùng ngày với email đặt hàng có thể tạo giao dịch mang tiêu đề email thay
    vì tên sản phẩm. Giờ email được sắp theo đầy đủ ngày giờ.
  - Tên sản phẩm có chữ như "tổng hợp" bị lọc nhầm là dòng tổng tiền.
  - Ở màn hình hẹp (cỡ điện thoại), tab Cài đặt bị tràn ngang vì đường dẫn thư mục dữ liệu quá dài.
  - Khi mất mạng, đồng bộ Gmail báo lỗi kỹ thuật; giờ là thông báo tiếng Việt dễ hiểu.
- **Biên lai chuyển khoản ngân hàng:** đã kiểm thử OCR với mẫu Vietcombank, Techcombank, MB.
- **Email MoMo:** bộ lọc mặc định giờ gồm `momo`; đọc biên lai MoMo (số tiền, dịch vụ hoặc lời nhắn, mã giao
  dịch); khoản "nhận tiền" được ghi là khoản thu. Email ưu đãi/khuyến mãi bị bỏ qua để không sinh giao dịch giả.
- **Sau khi đồng bộ**, nếu không nhập được giao dịch nào, app giải thích lý do và gợi ý dùng ảnh chụp "Đơn mua".
- Phát hiện khi thử với Gmail thật: 180 ngày không có email đơn hàng Shopee nào (đã ghi trong LIMITATIONS).

## 1.1 — chưa qua QA, không phát hành

- Ứng dụng Mac độc lập (pywebview + PyInstaller), file `.dmg`, màn hình hướng dẫn kết nối Gmail,
  nhiều tài khoản Gmail, ngân sách, biểu tượng cho hạng mục.

## 1.0

- Bản web chạy local đầu tiên.
