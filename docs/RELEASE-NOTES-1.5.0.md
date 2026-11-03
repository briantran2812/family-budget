# Thu Chi Gia Đình 1.5.0: ghi chi tiêu và xem báo cáo qua Telegram

**Trạng thái:** bản dùng thử. Đã chạy thử trên môi trường TEST (máy của chồng), chưa ký biên bản QA. Cập nhật từ 1.4.0:
dữ liệu và kết nối giữ nguyên, app tự sao lưu trước khi nâng cấp.

## Có gì mới

### 💬 Bot Telegram cho nhóm gia đình
- Nhắn trong nhóm: `45k phở`, `1tr5 học phí ck`, `120000 cà phê visa`.
- Bot tự xếp hạng mục theo từ khoá của app và nhớ cách trả lần trước của từng người, nên phần lớn khoản chi được ghi
  luôn. Câu trả lời có nút **✏️ Đổi hạng mục** và **↩️ Huỷ**. Không khớp từ khoá thì bot hiện nút để chọn hạng mục.
- Lệnh xem báo cáo: `/homnay`, `/tuan`, `/thang`, `/ngansach`, `/ongheo`, `/huongdan`.
- Bot tự nhắn:
  - cảnh báo khi một hạng mục chạm 80% hoặc vượt ngân sách;
  - báo cáo tuần lúc 20:00 Chủ nhật;
  - báo cáo tháng và ống heo lúc 08:00 ngày 1.
- Khoản ghi qua Telegram hiện trong app với nhãn **💬 Telegram**. Khoản bị huỷ trên Telegram cũng được huỷ trong app.

### ✉️ Đọc Gmail không cần App Password
- Apps Script trong Google Sheet của gia đình cứ 30 phút chép email Shopee, TikTok, MoMo vào tab "Email", kèm **cả nội
  dung thư**. App đọc ra **mặt hàng và số tiền** khi đồng bộ, bằng cùng bộ đọc với Gmail qua App Password. Thư quảng
  cáo bị bỏ qua, đơn huỷ được trừ ra, mỗi đơn chỉ tính một lần.
- Thư của người nhà tới bằng bộ lọc tự chuyển tiếp trong Gmail của người đó.

### 📊 Thống kê sử dụng
- Số lần mở app, tính năng hay dùng và lỗi gặp phải được ghi vào Google Sheet của gia đình (tab Tổng hợp, nhóm Hoạt
  động và Lỗi). Không gửi phím gõ, màn hình hay nội dung giao dịch. Xem chi tiết và tắt ở Cài đặt → Thống kê sử dụng.

### Sửa và cải thiện
- Ảnh lịch sử app ngân hàng: đọc được. Tiền vào được chọn sẵn, rút ATM và tiền lãi thì không.
- Màn hình duyệt ảnh: có "Chọn tất cả", dòng đếm, nút "Lưu n dòng", bấm ảnh để xem to.
- Thêm từ khoá phân loại món ăn, quán, đi lại. Máy đã cài tự nhận từ khoá mới.
- Báo lỗi bằng tiếng Việt khi Code.gs trên Google là bản cũ hoặc chưa được cấp quyền.

## Giới hạn
- Bot trả lời tin đầu tiên sau **khoảng 1 phút**. Các tin và lần bấm nút trong 2 phút sau đó được trả lời trong vài
  giây.
- Báo cáo của bot có số liệu tới lần máy Mac đồng bộ gần nhất, cộng thêm các khoản ghi qua Telegram hoặc iPhone sau đó.
  Đơn từ Gmail và ảnh chụp chỉ có trong báo cáo sau khi Mac mở và đồng bộ.
- Tin nhắn Telegram **không được mã hoá đầu-cuối**.
- Code.gs bản 5 cần quyền Gmail (toàn quyền, Google không có mức chỉ đọc) và quyền kết nối ra ngoài (Telegram).

Danh sách đầy đủ: `docs/LIMITATIONS.md`. Cài đặt: `docs/DEPLOY.md` các mục E, G, H.
