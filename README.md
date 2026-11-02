# Thu chi gia đình

Ứng dụng quản lý thu chi chạy trên máy Mac. Không dùng AI và không có server riêng: chữ trong ảnh do macOS đọc
ngay trên máy, phần còn lại là quy tắc cố định. Dữ liệu nằm trên máy của từng người; nếu bật nhập từ iPhone, một
bản sao nằm trong Google Sheet của chính bạn.

- **Gmail:** tự đọc email xác nhận đơn **Shopee** và **TikTok Shop**. Kết nối được nhiều tài khoản
  (vợ + chồng). Mỗi đơn chỉ tính một lần; đơn huỷ tự bỏ ra.
- **Ảnh chụp:** biên lai MoMo, trang "Đơn mua", hoá đơn điện nước… được đọc bằng OCR của macOS.
- **Nhập tay:** học phí, lương, đi chợ. Gõ `1.500.000`, `1,5tr` hay `200k` đều được.
- **Tổng quan:** % theo hạng mục, so với tháng trước, ngân sách từng hạng mục, xu hướng 12 tháng.
- **🐷 Ống heo:** cuối mỗi tháng, phần còn lại (thu − chi) được ghi lại để xem 3, 6 tháng để dành được bao nhiêu.
- **Tự phân loại bằng từ khoá.** Khi bạn đổi hạng mục, app hỏi có muốn ghi nhớ không.

## Cài cho người dùng (gửi cho người nhà)

Triển khai thật (máy TEST của bạn, rồi máy PRODUCTION của vợ, hai Google Sheet riêng): **[docs/DEPLOY.md](docs/DEPLOY.md)**.

Gửi file **`release/ThuChiGiaDinh-<phiên bản>-<arm64|x86_64>.dmg`** (đúng chip của máy nhận) qua AirDrop, Zalo
hoặc Google Drive. Người nhận làm như sau:

1. Mở file `.dmg` và kéo **Thu Chi Gia Dinh** vào **Applications**.
2. Lần đầu mở, macOS sẽ chặn vì app không có chữ ký của Apple. Bấm **Done**, rồi vào
   **System Settings → Privacy & Security**, kéo xuống và bấm **Open Anyway**. Chỉ cần làm một lần.
3. Làm theo màn hình chào mừng. App hướng dẫn từng bước cách tạo **Mật khẩu ứng dụng** của Google
   để kết nối Gmail.

Trong file `.dmg` có sẵn `Hướng dẫn cài đặt.txt` ghi đúng các bước này.

Yêu cầu: **macOS 11** trở lên; `-arm64.dmg` cho máy chip Apple, `-x86_64.dmg` cho máy chip Intel. Đọc ảnh
chụp cần macOS 13 trở lên (xem `docs/LIMITATIONS.md`).

**Dữ liệu** của mỗi người nằm ở `~/Library/Application Support/ThuChiGiaDinh/`:

| File | Nội dung |
| --- | --- |
| `budget.db` | Toàn bộ dữ liệu. Chép file này đi là đã sao lưu. |
| `app.log` | Log, để xem khi có lỗi. |
| `backups/` | Bản sao `budget.db` app tự chép trước mỗi lần nâng cấp phiên bản (giữ 10 bản). |

App Password nằm trong **Keychain** (tên mục `family-budget-gmail`).

## Phát triển

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller
.venv/bin/python desktop.py          # chạy trong cửa sổ riêng (giống bản đóng gói)
.venv/bin/python app.py              # hoặc trong trình duyệt: http://127.0.0.1:8765
packaging/setup_build_env.sh         # một lần: Python cho macOS 11+, venv .venv-build-arm64/-x86_64
packaging/build.sh arm64             # → dist/arm64/Thu Chi Gia Dinh.app + dist/ThuChiGiaDinh-<ver>-arm64.dmg
packaging/build.sh x86_64            # bản Intel, build dưới Rosetta
.venv/bin/python packaging/release.py check   # mọi file trong app có chạy được trên macOS/CPU đã khai báo?
```

Bản build không dùng Python của Homebrew: Python đó chỉ chạy trên đúng phiên bản macOS của máy build (lỗi S1
của 1.3.0). Muốn ra phiên bản mới: theo `docs/RELEASE-PROCESS.md` và `docs/DEPLOY.md` mục E.

### Dữ liệu mẫu (mockup)

```sh
.venv/bin/python demo_data.py                       # → ./demo-data
BUDGET_DATA=demo-data .venv/bin/python desktop.py   # mở app với dữ liệu mẫu
```

Dữ liệu mẫu gồm 6 tháng: lương 50 triệu/tháng, đơn Shopee/TikTok ngẫu nhiên, và biên lai MoMo
(học phí, điện, nước, internet). Dữ liệu này được tạo qua đúng đường xử lý thật:

- Đơn hàng được viết thành email giả rồi cho qua bộ đọc email.
- Biên lai được vẽ thành ảnh PNG (lưu trong `demo-data/momo/`) rồi cho OCR đọc.

Biến `BUDGET_DATA` chọn thư mục dữ liệu, nên dữ liệu mẫu không lẫn với dữ liệu thật.

### Khi email Shopee/TikTok không đọc được

Shopee và TikTok thỉnh thoảng đổi mẫu email. Email nào không lấy được số tiền sẽ hiện ở
**Nhập dữ liệu → Email chưa đọc được số tiền**. Cách xử lý:

1. Sửa `TOTAL_LABELS` trong `parsers.py`.
2. Bấm **Phân tích lại**. App đọc lại từ bản email đã lưu, không tải lại từ Gmail.

### Cấu trúc

| File | Vai trò |
| --- | --- |
| `desktop.py` | Điểm vào của bản đóng gói: chạy server nội bộ và mở cửa sổ (pywebview) |
| `app.py` | API (Flask), chỉ nhận kết nối từ chính máy này |
| `db.py` | Database, hạng mục, từ khoá và biểu tượng mặc định |
| `rules.py` | Phân loại theo từ khoá (không phân biệt dấu, từ khoá dài nhất thắng) |
| `parsers.py` | Đọc số tiền, mã đơn, tên sản phẩm từ email và từ chữ OCR |
| `gmail_sync.py` | Đọc Gmail qua IMAP, hỗ trợ nhiều tài khoản |
| `ocr.py` | OCR bằng Vision framework của macOS |
| `alerts.py` | Cảnh báo hạng mục chạm 80% ngân sách tháng, thông báo macOS một lần mỗi mức |
| `piggy.py` | Ống heo: ghi phần còn lại (thu − chi) của mỗi tháng đã qua |
| `static/index.html` | Toàn bộ giao diện |
| `demo_data.py` | Tạo dữ liệu mẫu |
| `packaging/` | Icon, script build, hướng dẫn cài đặt đi kèm file `.dmg` |
