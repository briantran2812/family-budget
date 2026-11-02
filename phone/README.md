# Nhập khoản chi từ iPhone

```
iPhone: Phím tắt "Ghi chi tiêu"  ──GET──▶  Apps Script (Code.gs) trong Google của bạn  ──▶  Sheet "Hộp thư đến"
                                                                                                  ▲
MacBook: app Thu Chi Gia Đình, mỗi lần mở  ─────────────────── đọc các dòng mới ──────────────────┘
```

Trên iPhone không cài app nào. Phím tắt chạy bằng app Phím tắt có sẵn của iOS. Code thật chạy trên
máy chủ Google dưới dạng Apps Script, miễn phí và không cần máy nào bật.

Làm theo thứ tự **A → D trên máy của bạn trước**. Đạt hết mục D mới làm mục E cho vợ.

## A. Cài Apps Script (một lần, trên Mac, khoảng 5 phút)

1. Mở <https://sheets.new> bằng tài khoản Google **của bạn** và đặt tên sheet, ví dụ
   "Thu Chi Gia Đình".
2. Vào menu **Tiện ích mở rộng → Apps Script** (Extensions → Apps Script). Một tab mới mở ra, đang
   có sẵn `function myFunction() {}`.
3. Xoá hết, rồi dán toàn bộ nội dung file [`Code.gs`](Code.gs). Trong app Mac có nút
   **(sao chép Code.gs)** ở cửa sổ "Kết nối Google Sheet". Bấm 💾 **Lưu** (⌘S).
4. Ở thanh trên cùng, chọn hàm **`caiDat`** rồi bấm **▶ Chạy** (Run).
   - Google hỏi quyền: **Xem lại quyền** → chọn tài khoản.
   - Màn hình **"Google chưa xác minh ứng dụng này"** hiện ra vì đây là script của chính bạn, chưa
     gửi Google duyệt. Bấm **Nâng cao → Đi tới Thu Chi Gia Đình (không an toàn)** → **Cho phép**.
   - Script chỉ xin quyền Google Sheets. Google ghi là "xem, sửa… tất cả bảng tính" vì đó là mức quyền
     nhỏ nhất cho script mở sheet theo mã. Code chỉ mở đúng sheet tạo ở bước này. Script không có quyền
     với Gmail hay các file khác trên Drive.
   - Nhật ký thực thi ghi "Đã tạo sheet Hộp thư đến…". Quay lại tab Sheet sẽ thấy tab **Hộp thư đến**
     có 6 cột.
5. Bấm **Triển khai → Bản triển khai mới** (Deploy → New deployment) → biểu tượng ⚙️ → **Ứng dụng web**
   (Web app):
   - Thực thi với tư cách (Execute as): **Tôi** (Me)
   - Người có quyền truy cập (Who has access): **Bất kỳ ai** (Anyone)

   Rồi bấm **Triển khai**. "Bất kỳ ai" là để Phím tắt gọi được mà không cần đăng nhập Google. Mã bí
   mật ở bước 6 là thứ chặn người lạ.
6. Quay lại trình soạn code, chọn hàm **`layMaKetNoi`** → **▶ Chạy**. Nhật ký in ra một dòng dạng:

   ```
   https://script.google.com/macros/s/AKfy…/exec?k=3f9c…
   ```

   Đây là **mã kết nối**. Giữ kín như mật khẩu.

## B. Kết nối app Mac

Để test, chạy bản đang phát triển với **thư mục dữ liệu riêng**, để dữ liệu thử không lẫn vào dữ liệu
thật:

```sh
cd ~/family-budget && git switch feat/phone-inbox
BUDGET_DATA=~/family-budget/data/phone-test .venv/bin/python desktop.py
```

Vào tab **Nhập liệu → Từ iPhone → Kết nối Google Sheet**, dán mã kết nối, bấm **Kết nối**. App kiểm
tra mã với Google ngay rồi báo "✅ Đã kết nối Google Sheet".

## C. Cài Phím tắt lên iPhone của bạn

File đã ký nằm ở `phone/dist/Ghi chi tiêu.shortcut`. Tạo lại bằng
`.venv/bin/python phone/make_shortcut.py` (cần đăng nhập iCloud và có mạng).

1. Trên Mac: **Cài đặt → iPhone (Google Sheet) → 📋 Sao chép mã cho iPhone**. iPhone dùng cùng Apple
   ID nên dán thẳng được nhờ Universal Clipboard.
2. AirDrop file `Ghi chi tiêu.shortcut` sang iPhone. iPhone tự mở app Phím tắt.
3. Bấm **Thêm phím tắt**. Ô **"Dán mã kết nối"** hiện ra: chạm và giữ → **Dán** → **Thêm**.
4. Lần chạy đầu tiên, iOS hỏi **"Cho phép Ghi chi tiêu kết nối tới script.google.com?"** → **Luôn cho
   phép**. Có thể hỏi thêm một lần cho `script.googleusercontent.com`; chọn cho phép tương tự.

Cách mở cho nhanh (chọn một):

- **Chạm 2 lần vào mặt lưng iPhone:** Cài đặt → Trợ năng → Cảm ứng → Chạm vào mặt sau → Chạm hai lần
  → Ghi chi tiêu.
- **Nút Tác vụ** (iPhone 15 Pro trở lên): Cài đặt → Nút Tác vụ → Phím tắt → Ghi chi tiêu.
- **Màn hình chính:** trong app Phím tắt, giữ Ghi chi tiêu → Chia sẻ → Thêm vào MH chính.
- **Siri:** "Hey Siri, ghi chi tiêu".

## D. Kiểm thử trên máy của bạn

Đánh dấu từng dòng. Mục nào không đạt thì gửi tôi ảnh màn hình.

| # | Làm gì | Mong đợi | ✓ |
| --- | --- | --- | --- |
| T1 | Chạy Phím tắt: gõ `45`, "Phở bò", chọn Tiền mặt | Trong vòng 10 giây có thông báo **"✓ Đã ghi 45.000 ₫ · Phở bò"**; sheet có thêm một dòng, cột Người nhập là tên iPhone của bạn | |
| T2 | Gõ `1500000`, "Học phí tháng 11", Chuyển khoản | Thông báo ghi **1.500.000 ₫** | |
| T3 | Gõ `0` | Thông báo **"✗ Số tiền… chưa đúng"**, sheet không thêm dòng | |
| T4 | Trên Mac bấm **Đồng bộ ngay** | "Đã lấy 2 khoản mới từ iPhone". Tab Giao dịch → lọc **iPhone** thấy hai khoản; Học phí tự vào hạng mục Học phí; "Trả bằng" đúng như đã chọn | |
| T5 | Bấm **Đồng bộ ngay** lần nữa | "Đã lấy 0 khoản mới · 2 đã có", không có giao dịch trùng | |
| T6 | Ghi thêm một khoản trên iPhone → tắt app Mac → mở lại | App tự báo "📱 Đã lấy 1 khoản mới từ iPhone", không cần bấm gì | |
| T7 | Bật **Chế độ máy bay** → chạy Phím tắt | Báo lỗi không kết nối được, **không** báo "Đã ghi" | |
| T8 | Vẫn ở Chế độ máy bay: mở app **Google Sheets** → tab Hộp thư đến → gõ một dòng (bỏ trống cột Mã; cột Số tiền `30k`, Mô tả "Gửi xe"). Tắt Chế độ máy bay, đợi vài giây → Đồng bộ trên Mac | Dòng Gửi xe về Mac, **30.000 ₫**; cột Mã trong sheet được điền tự động | |
| T9 | Gán **Chạm vào mặt sau**, ghi 3 khoản liên tiếp, bấm giờ | Mỗi khoản dưới 10 giây kể từ lúc chạm | |
| T10 | Trong Phím tắt, sửa ô mã ở bước đầu (xoá 1 ký tự cuối) → chạy | **"✗ Mã kết nối sai…"**. Sửa lại cho đúng sau khi thử | |

Thử xong, xoá dữ liệu thử: xoá thư mục `~/family-budget/data/phone-test`, rồi xoá các dòng thử trong
sheet. Bản app thật của bạn không bị ảnh hưởng vì dùng thư mục dữ liệu khác.

## E. Cài cho vợ

Chỉ làm khi mục D đạt hết. Dùng **chung một sheet**, nghĩa là chung mã kết nối. Cột Người nhập cho
biết ai ghi.

1. AirDrop file `Ghi chi tiêu.shortcut` sang iPhone của vợ.
2. Gửi mã kết nối: AirDrop một ghi chú chứa mã, hoặc gõ vào iMessage rồi xoá tin nhắn sau khi dán.
   Đừng dán mã vào nhóm Zalo.
3. Trên iPhone của vợ: **Thêm phím tắt** → dán mã → bật Chạm vào mặt sau như mục C.
4. Trên MacBook của vợ (khi đã có bản app có tính năng này): Nhập liệu → Từ iPhone → dán cùng mã.

Danh sách "Trả bằng" mặc định là Tiền mặt, Thẻ Visa, Chuyển khoản, Ví MoMo. Muốn khớp với tên thẻ
khi đối chiếu sao kê (ví dụ "Visa Techcombank"): mở app Phím tắt → giữ Ghi chi tiêu → **Sửa** → bước
Danh sách → đổi tên.

## Sự cố thường gặp

| Hiện tượng | Nguyên nhân và cách sửa |
| --- | --- |
| App Mac báo "Google không trả về dữ liệu" | Bản triển khai chưa đặt **Bất kỳ ai**. Vào Triển khai → Quản lý bản triển khai → ✏️ → sửa → Triển khai |
| `layMaKetNoi` báo "Chưa thấy bản Deploy dạng Web app" | Chưa làm bước A5, hoặc chỉ mới "Kiểm thử bản triển khai". Mã = địa chỉ Web app (đuôi `/exec`) + `?k=` + mã in trong nhật ký |
| Phím tắt báo "Mã kết nối sai" sau khi chạy `doiMa` | Đúng như thiết kế. Chạy `layMaKetNoi`, rồi dán mã mới vào app Mac và vào bước đầu của Phím tắt |
| Sửa `Code.gs` mà iPhone vẫn chạy như cũ | Triển khai → Quản lý bản triển khai → ✏️ → Phiên bản: **Phiên bản mới** → Triển khai. Địa chỉ và mã giữ nguyên |
| Lộ mã kết nối | Chạy `doiMa` ngay, rồi dán mã mới vào app Mac và các iPhone |

## Cho người phát triển

- `Code.gs` được test trong Node với dịch vụ Google giả lập: `node tests/apps_script/harness.mjs`
  (chạy kèm `pytest`).
- `phone_inbox.py` (phía Mac) có test ở `tests/test_phone_inbox.py`; UX-34 đến UX-36 trong
  `tests/e2e/test_ux.py`.
- Phím tắt dùng **GET**, không dùng POST. Apps Script luôn trả 302 sang `googleusercontent.com`, và
  máy khách nào đổi POST thành GET khi đi theo chuyển hướng sẽ làm mất dữ liệu gửi đi.
- Mã kết nối không nằm trong file `.shortcut`; iOS hỏi mã lúc thêm phím tắt (`WFWorkflowImportQuestions`).
  Thư mục `phone/dist/` không được commit vì file đã ký mang danh tính iCloud của người ký.
