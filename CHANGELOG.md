# Changelog

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
