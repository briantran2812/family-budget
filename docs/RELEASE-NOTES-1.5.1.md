# Thu Chi Gia Đình 1.5.1: không tính một khoản hai lần

**Trạng thái:** bản dùng thử, chạy trên máy của chồng (TEST) trước. Cập nhật từ 1.5.0: dữ liệu và kết nối giữ nguyên,
app tự sao lưu trước khi nâng cấp. Phím tắt iPhone **không** phải cài lại.

## Có gì mới

### 🔗 Email và khoản đã ghi chỉ tính một lần
- Bạn ghi "Tiền điện 746.855 ₫, Ví MoMo" qua iPhone, sau đó email "Thanh toán thành công" của MoMo về: app hiểu đây là
  **cùng một khoản**, chỉ tính một lần. Mô tả và hạng mục bạn chọn được giữ, giao dịch có nhãn **🔗 Email MoMo**.
- Gộp khi số tiền khớp từng đồng, cách trả không mâu thuẫn (email MoMo không gộp với khoản "Tiền mặt") và ngày ghi gần
  ngày trong email (ghi trễ tới 3 ngày vẫn nhận ra). Email về trước hay ghi tay trước đều được.
- Gộp nhầm: mở giao dịch, bấm **Tách ra**, hai khoản được tính riêng.

### ⚠️ Hai người cùng ghi một khoản
- Chồng đi làm, vợ ở nhà, cả hai cùng ghi khoản đi chợ 127.000 ₫: app và bot Telegram báo **"Có thể trùng"**.
- App **không tự xoá**. Trong Telegram bấm **↩️ Trùng — huỷ khoản này** hoặc **✔ Khác khoản**; trên Mac mở giao dịch
  có nhãn ⚠️ (hoặc bấm 🔔) và chọn.
- Một người ghi hai khoản giống nhau (hai bữa trưa 45k) thì không bị hỏi. Lỡ gửi một tin hai lần trong 3 phút thì bot hỏi
  lại trước khi ghi.
- Khoản ghi qua phím tắt iPhone cũng hiện trong nhóm Telegram, để cả nhà nhìn cùng một sổ.
- Quy ước nên có: **ai trả tiền thì người đó ghi**.

### 🗓 Ghi khoản của hôm qua
- Thêm `hôm qua`, `hôm kia` hoặc ngày vào nội dung: `45k phở hôm qua`, `500k học phí 01/11`. Dùng được trên Telegram và
  phím tắt iPhone. Tin "Đã ghi" có nút **📅 Đổi ngày**.

### Khác
- Chip **MoMo** (và Shopee, TikTok) ở trang Giao dịch nay gồm cả khoản **trả bằng ví đó**, không chỉ khoản lấy từ email.
- Khoản lấy từ email MoMo tự ghi cách trả **Ví MoMo**.

## Cần làm khi cập nhật
1. Google Sheet: dán **Code.gs bản 6**, rồi **Deploy → Manage deployments → ✏️ → New version** (không tạo deployment mới).
2. Mac: cài bản 1.5.1, bấm **↻ Đồng bộ** một lần.
