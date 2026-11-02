# Thu Chi Gia Đình 1.4.0: ghi chi tiêu từ iPhone

**Trạng thái:** beta để dùng thử với dữ liệu thật, **chưa qua cổng QA**. Chưa cài cho máy của vợ: bản đóng gói vẫn còn
lỗi S1 (chỉ chạy trên macOS 26). Bản này gồm cả các tính năng của 1.3.0, bản chưa từng phát hành.

## Có gì mới

### 📱 Ghi khoản chi ngay trên iPhone

- Phím tắt **"Ghi chi tiêu"** hỏi bốn câu, giống form Nhập tay trong app:
  1. **Số tiền:** gõ đúng số, ví dụ 45000. Câu hỏi sau nhắc lại "45.000 ₫ — chi cho gì?" để thấy ngay khi thiếu
     số 0.
  2. **Mô tả.**
  3. **Hạng mục:** ✨ Tự động hoặc chọn hạng mục. Chọn Lương hay Thu nhập khác thì ghi thành khoản thu.
  4. **Trả bằng:** Tiền mặt, Thẻ Visa, Chuyển khoản hoặc Ví MoMo.
- Mở nhanh bằng chạm 2 lần vào lưng iPhone, icon trên màn hình chính hoặc Siri. Mỗi khoản mất khoảng 10 giây.
- Dữ liệu đi vào Google Sheet "Hộp thư đến" trong Drive của bạn. Không cần mở Mac, không cài app nào trên iPhone.
- Mất sóng thì gõ thẳng vào sheet bằng app Google Sheets. App Mac vẫn lấy về được.

### 🔄 Đồng bộ tự động

- App tự lấy khoản mới lúc mở, mỗi 5 phút, và khi bạn quay lại cửa sổ app. Trang đầu có nút **↻ Đồng bộ**.
- Gmail tự đồng bộ lúc mở app, tối đa 6 giờ một lần.
- Không nhập trùng: một khoản đã thêm từ sao kê được gộp với khoản ghi trên iPhone cùng số tiền.

### 📊 Bản sao trên Google Sheet

- Tab **Giao dịch:** mọi giao dịch trong app (Gmail, ảnh chụp, nhập tay, sao kê, iPhone).
- Tab **Tổng hợp:** mỗi tháng có thu nhập, tổng chi, còn lại, chi theo hạng mục và theo cách trả.
- Xem được trên iPhone bằng app Google Sheets. App trên Mac vẫn là dữ liệu gốc; sheet chỉ để xem.

### 💳 Theo dõi theo cách trả

- Biểu tượng theo cách trả: 💵 tiền mặt, 💳 thẻ, 🏦 chuyển khoản, 👛 ví.
- Tab Giao dịch có bộ lọc **"Mọi cách trả"**. Tổng quan có thẻ **"Chi theo cách trả"**; bấm vào một dòng để xem danh
  sách đã lọc.
- Hai ô nguồn ở Tổng quan là hai nguồn chi nhiều nhất trong tháng, ví dụ iPhone hay Nhập tay, thay vì luôn là
  Shopee/TikTok.

### ⚠️ Cảnh báo ngân sách

- Hạng mục có đặt ngân sách mà đã dùng từ **80%** trở lên thì hiện cảnh báo ở đầu Tổng quan, ví dụ "⚠️ Ăn uống & đi
  chợ đã dùng 85% ngân sách tháng (1,7 tr / 2 tr) — còn 300k". Vượt quá 100% thì hiện 🔴. Bấm vào cảnh báo để xem
  các khoản của hạng mục đó.
- macOS hiện **thông báo** khi một hạng mục vừa chạm 80% và khi vượt 100%. Mỗi mốc chỉ báo một lần trong tháng, và
  chỉ báo khi app đang mở.

### 🔔 Chuông thông báo và nhật ký thay đổi

- Chuông ở trên cùng có số thông báo chưa đọc. Có các loại: cảnh báo ngân sách, ống heo, khoản mới từ iPhone, đơn mới từ
  Gmail, phiên bản mới, lỗi ghi lên Google Sheet. Bấm vào một thông báo để mở đúng chỗ.
- **📜 Nhật ký thay đổi** liệt kê mọi phiên bản. Mở từ chân danh sách thông báo hoặc Cài đặt → Về ứng dụng.

### 🌗 Giao diện Sáng / Tối

- Cài đặt → Giao diện: ☀️ Sáng, 🌙 Tối hoặc 💻 Theo máy. Nền sáng vẫn giữ nguyên khi macOS đang để chế độ Tối.

### 🐷 Ống heo

- Cuối mỗi tháng, phần **còn lại** (thu nhập − chi) được bỏ vào ống heo. App ghi vào ngày cuối tháng hoặc lần đầu mở
  app sau đó, và báo trên chuông: "🐷 Tháng 10/2026: bỏ ống heo 12,5 tr".
- Mục **🐷 Ống heo** trong menu bên trái (chỉ cần xem mỗi tháng một lần): tổng đã để dành, **3 tháng** và **6 tháng gần nhất**, và "nếu giữ nhịp này, 12 tháng
  nuôi được bao nhiêu". Bấm vào để xem từng tháng; tháng chi vượt thu hiện màu đỏ.
- Thêm khoản của tháng cũ sau khi đã ghi (ví dụ nhập sao kê tháng trước) thì hiện "Số liệu tháng này đã đổi" và nút
  **Cập nhật**.
- Tháng chưa ghi khoản thu nào thì chưa bỏ ống heo: nhớ ghi lương.

### 📸 Ảnh chụp thông minh hơn

- Đọc được **màn hình lịch sử của app ngân hàng**: tiền vào ghi là Thu và chọn sẵn; rút ATM và tiền lãi không chọn sẵn.
- Màn hình duyệt: **"Chọn tất cả"**, dòng đếm "Đã chọn n/N · Thu · Chi", nút "Lưu n dòng đã chọn", bấm ảnh để xem to.
- Thêm từ khoá phân loại món ăn, quán xá, đi lại; khoản thu từ công ty tự vào **Lương**.

- Đọc **màn hình lịch sử giao dịch** của MoMo: mỗi khoản chi thành một dòng; bỏ qua tiền lời, số dư và dòng bị cắt ở
  mép ảnh.
- **Tự nhận ra nguồn tiền** (Ví MoMo, ZaloPay, ngân hàng) và điền sẵn ô "Trả bằng". Không nhận ra thì nhắc bạn chọn.
- Khoản đã có trong app được bỏ chọn sẵn, nên chụp chồng nhiều ảnh cũng không bị nhập trùng.

### 🧾 Đối chiếu sao kê (từ 1.3.0)

- Nhập sao kê Visa hoặc tài khoản ngân hàng (Excel, CSV, PDF, kể cả PDF có mật khẩu) rồi đối chiếu với khoản đã ghi.
- Kết quả chia thành các nhóm: khớp, chưa ghi, gần khớp, ghi nhưng không có trên sao kê.

### Sửa lỗi

- Tỷ lệ "thu nhập đã chi" nhỏ hiện 0,5% thay vì 0%.
- Ảnh MoMo không còn bị đọc nhầm số dư thành khoản chi.
- Các lỗi tìm ra khi thử trên iPhone thật: mô tả bị trống, biểu tượng tiền mặt sai, quy ước số tiền gây nhầm.

## Bắt đầu dùng với dữ liệu thật

1. **Cập nhật Apps Script:**
   - Dán `phone/Code.gs` mới → ⌘S.
   - **Deploy → Manage deployments → ✏️ → Version: New version → Deploy**.
2. **Cài lại Phím tắt:** xoá bản cũ trên iPhone → AirDrop `phone/dist/Ghi chi tiêu.shortcut` → dán mã kết nối.
3. **Dọn dữ liệu thử trong sheet** "Hộp thư đến". Xoá các dòng thử (Ăn uống 45.000, Đổ xăng 100.000, Học phí 7.000)
   **trước** khi mở app thật, nếu không app thật sẽ lấy cả các dòng này. Dòng nào là chi tiêu thật thì giữ lại.
4. **Tắt app thử, mở app thật:** chạy lệnh dưới đây. Lệnh này không có `BUDGET_DATA`, nên app dùng dữ liệu thật trong
   `~/Library/Application Support/ThuChiGiaDinh`, nơi đang có 1 khoản nhập tay và Gmail đã kết nối.
   ```sh
   cd ~/family-budget && .venv/bin/python desktop.py
   ```
5. Trong app thật: **Nhập dữ liệu → Từ iPhone → Kết nối Google Sheet** → dán cùng mã kết nối.
6. Xoá thư mục thử `~/family-budget/data/phone-test` khi không cần nữa.

## Giới hạn cần biết

| Giới hạn | Cách xử lý |
| --- | --- |
| Phím tắt cần mạng | Gõ thẳng vào app Google Sheets |
| Ngày luôn là lúc gửi | Sửa ngày trong app |
| Sửa trong sheet sau khi Mac đã lấy về thì không có tác dụng | Sửa trong app |
| Hạng mục mới thêm trong app không tự có trên iPhone | Sửa bước Danh sách trong Phím tắt |
| Hai Mac cùng bật bản sao thì khoản từ iPhone hiện hai lần trong tab Giao dịch | Chỉ bật trên một Mac |
| Bộ đọc ảnh lịch sử mới thử với MoMo; app ngân hàng chưa thử ảnh thật | Gửi ảnh mẫu để chỉnh |
| Cảnh báo ngân sách chỉ hiện trên Mac, iPhone chưa nhận được | Xem bản sau (Telegram) |
| Ống heo chỉ tính khoản đã ghi trong app, không phải số dư tài khoản ngân hàng | Ghi đủ thu nhập và chi tiêu |
| "Phở", "bún", "cơm", "tiền chợ"… chưa tự vào Ăn uống | Chọn hạng mục trên iPhone, hoặc thêm từ khoá trong Cài đặt |

Danh sách đầy đủ: `docs/LIMITATIONS.md`.

## Thu feedback cho bản sau

Dùng ít nhất **2 tuần** với chi tiêu thật. Mỗi lần gặp chuyện thì ghi một dòng theo mẫu dưới đây; ảnh chụp màn hình
giúp sửa nhanh nhất.

| Ngày | Đang làm gì | Mong đợi | Thực tế | Ảnh |
| --- | --- | --- | --- | --- |
| | | | | |

**Nên để ý:**

- **Tốc độ ghi:** dưới 10 giây mỗi khoản không? Bước nào thừa? Có cần hỏi ngày không?
- **Phân loại:** khoản nào hay rơi vào "Khác"? Ghi lại mô tả của các khoản đó.
- **Ảnh chụp:** app ngân hàng nào đọc sai? Gửi ảnh, che số tài khoản.
- **Gmail:** đơn Shopee, TikTok, MoMo có về đủ không?
- **Sheet:** tab Tổng hợp có dùng thật không, hay chỉ cần app?
- **Cảm giác chung:** sau 2 tuần, vợ bạn có muốn dùng không?

## Dự kiến cho bản sau (chọn theo feedback)

| Ứng viên | Vì sao |
| --- | --- |
| Đọc Gmail bằng Apps Script (1.5.0) | Không cần App Password; vẫn đọc khi Mac tắt; gom được Gmail của vợ |
| Sửa S1: chạy được trên Mac cũ | Bắt buộc trước khi cài cho máy của vợ |
| Từ khoá cho món ăn và chi tiêu hằng ngày; đưa từ khoá mới tới máy đã cài | Giảm số khoản rơi vào "Khác" |
| Bot Telegram: nhập, báo cáo, cảnh báo ngân sách trên điện thoại | Phím tắt iOS không tự gửi thông báo được; dùng được cả Android |
| Tự ghi khi chạm Apple Pay (iOS 17 trở lên) | Thẻ Visa trong Wallet: không phải gõ gì |
| Hỏi ngày trên iPhone (Hôm nay / Hôm qua / Chọn ngày) | Chỉ làm nếu feedback cần |
| Một agent độc lập rà lại trước khi phát hành | Lần này 7 lỗi chỉ lộ ra khi thử trên máy thật |
