# Triển khai: TEST (máy anh) → PRODUCTION (máy vợ)

Runbook cho tối nay và cho mỗi lần sửa lỗi sau này. Làm theo thứ tự, mỗi bước có "Thấy gì" để biết đã đúng.

## Mô hình

| | TEST | PRODUCTION |
| --- | --- | --- |
| Máy Mac | MacBook của anh | MacBook của vợ |
| Google Sheet | **Thu Chi — TEST** | **Thu Chi — PRODUCTION** |
| Phím tắt iPhone | **Ghi chi tiêu TEST** (icon cam), chỉ trên iPhone của anh | **Ghi chi tiêu** (icon xanh lá), trên cả hai iPhone |
| Dấu hiệu trong app | Nhãn **TEST** màu cam cạnh "Chào …" ở thanh trên | Không có nhãn |

- **Cùng một file DMG** đi từ TEST sang PRODUCTION. Môi trường không nằm trong bản build mà nằm ở từng máy:
  mã kết nối trong Keychain (`family-budget-phone`) và dữ liệu trong `~/Library/Application Support/ThuChiGiaDinh/`.
- Mỗi Sheet có **Apps Script riêng, bản Deploy riêng, mã bí mật riêng**. Mã của sheet này không mở được sheet kia.
- App lấy **tên Sheet** khi kết nối và mỗi lần đồng bộ; tên có chữ "TEST" thì hiện nhãn TEST. Vì vậy phải đặt
  tên sheet đúng **trước** khi kết nối.
- `Code.gs` có `SCRIPT_VERSION`. App cần bản nào thì ghi ở `phone_inbox.REQUIRED_SCRIPT_VERSION`; sheet chạy bản cũ
  hơn thì app báo "Code.gs trên Google là bản cũ" ở thẻ iPhone. Code.gs cũng đi TEST → PRODUCTION như app (mục E).
  Đọc Gmail qua sheet (mục G) cần bản 3 nhưng không bắt buộc: sheet bản 2 thì iPhone vẫn chạy, mục Gmail báo cần bản 3.
  Bot Telegram (mục H) cần bản 4; bản 5 trả lời nhanh hơn và tự chọn hạng mục theo từ khoá (H6). App 1.4.0 vẫn chạy
  với bản 4 và 5 (chỉ thêm cột và trường).

Máy vợ chạy macOS 11 trở lên là được, chip Apple hay Intel đều có file cài. Đọc ảnh chụp biên lai cần macOS 13+;
máy cũ hơn vẫn nhập tay, nhận iPhone, Gmail, sao kê bình thường (`docs/LIMITATIONS.md`, mục "macOS 11/12 so với 13+").

### Thứ tự tối nay (đánh dấu khi xong)

- [ ] A. Tạo 2 Sheet + Apps Script + Deploy, lấy 2 mã kết nối (~15 phút)
- [ ] B. Cắt `release/1.4.0`, `release.py rc` (~10 phút, máy tự chạy)
- [ ] C. Cài lên máy anh = TEST, chạy các ca QA trên máy anh
- [ ] D. Cài lên máy vợ = PRODUCTION, các ca QA cần máy/người khác
- [ ] C7. Ký biên bản, `release.py final` (khi mọi ca P1 đã PASS; có thể để mai)

`release.py final` **không đổi file**: nó chỉ kiểm biên bản rồi chép đúng file RC (cùng SHA-256) vào `release/`.
Nên cài file RC lên máy vợ tối nay là cài đúng bản sẽ phát hành; final làm sau cũng không phải cài lại.

---

## A. Hai Google Sheet (một lần)

Làm trên Mac, trình duyệt đăng nhập Google **của anh**. Làm hai lần, lần 1 cho TEST, lần 2 cho PRODUCTION.

| Lần | Tên sheet (gõ đúng) | Ghi mã vào |
| --- | --- | --- |
| 1 | `Thu Chi — TEST` | Ghi chú "MÃ TEST" |
| 2 | `Thu Chi — PRODUCTION` | Ghi chú "MÃ PRODUCTION" |

> Đang có sheet cũ từ lúc phát triển (tab "Hộp thư đến" có dữ liệu thử)? Đổi tên nó thành `Thu Chi — TEST` và dùng
> làm TEST: làm từ bước 3 (dán Code.gs mới), ở bước 6 chọn **Manage deployments → ✏️ → Version: New version**
> thay vì New deployment. Mã kết nối giữ nguyên. Sheet PRODUCTION thì luôn tạo mới, sạch.

1. Mở <https://sheets.new>. Bấm vào "Untitled spreadsheet" ở góc trên trái, gõ tên theo bảng trên, Enter.
2. Menu **Extensions → Apps Script**. Tab mới mở, có sẵn `function myFunction() {}`.
3. Xoá hết, dán toàn bộ `phone/Code.gs` (trong repo, hoặc trong app: Nhập dữ liệu → Từ iPhone → Kết nối Google
   Sheet → "bấm để sao chép"). Bấm 💾 (⌘S).
   ```sh
   pbcopy < ~/family-budget/phone/Code.gs     # chép vào clipboard rồi ⌘V vào trình soạn Apps Script
   ```
   Thấy: dòng `var SCRIPT_VERSION = 5;` ở gần đầu file (bản 1.4.0 là `2`).
4. Thanh trên: chọn hàm **caiDat** → **▶ Run** → **Review permissions** → chọn tài khoản →
   "Google hasn't verified this app" → **Advanced → Go to … (unsafe)** → **Allow**. Từ bản 3 Google hỏi cả quyền
   Gmail (cho mục G); script chỉ đọc Gmail khi đã chạy `batQuetEmail`. Từ bản 4 hỏi thêm quyền "kết nối tới dịch vụ
   bên ngoài" (cho bot Telegram, mục H); script chỉ gọi Telegram khi đã chạy `batTelegram`.
   Thấy: Execution log ghi `Đã tạo sheet "Hộp thư đến"…`; tab Sheet có tab **Hộp thư đến** với 9 cột.
5. **Deploy → New deployment** → ⚙️ → **Web app**:
   - Execute as: **Me**
   - Who has access: **Anyone** ← đúng chữ "Anyone". **Không** chọn "Anyone with Google account": chọn nhầm thì
     iPhone và Mac đều bị Google đòi đăng nhập (đã mất một buổi vì lỗi này).
   - **Deploy**.
6. Chọn hàm **layMaKetNoi** → **▶ Run**. Execution log in một dòng:
   ```
   https://script.google.com/macros/s/AKfy…/exec?k=3f9c…
   ```
   Chép cả dòng vào ghi chú tương ứng. Đây là **mã kết nối**, giữ kín như mật khẩu.
7. Kiểm tra nhanh trong Terminal (thay `MA` bằng mã vừa chép, giữ dấu nháy đơn):
   ```sh
   curl -sL 'MA&a=ping'
   ```
   Thấy: `{"ok":true,"sheet":"https://docs.google.com/…","name":"Thu Chi — TEST","version":4}`
   (lần 2 là `Thu Chi — PRODUCTION`). Thấy trang HTML có "Sign in" thì bước 5 chưa chọn **Anyone**: Deploy →
   Manage deployments → ✏️ → Who has access: Anyone → Deploy.

---

## B. Build bản RC

Chạy trong repo chính `~/family-budget`. Code của 1.4.0 đã được gộp vào nhánh tích hợp (hiện là `feat/phone-inbox`;
sau này là `develop`). `release.py rc` chỉ chạy trên `develop` hoặc `release/…`.

1. Môi trường build (một lần mỗi máy; không cần quyền admin, cài `uv` vào `~/.local/bin`):
   ```sh
   cd ~/family-budget
   packaging/setup_build_env.sh
   ```
   Thấy: `arm64 3.12.x` và `x86_64 3.12.x`. Nếu báo thiếu Rosetta: `softwareupdate --install-rosetta --agree-to-license`.
2. Cắt nhánh release và chạy cổng tự động:
   ```sh
   git status                                  # phải sạch
   git switch feat/phone-inbox                 # nhánh tích hợp
   git switch -c release/1.4.0
   caffeinate -i .venv/bin/python packaging/release.py rc
   ```
   Chạy khoảng 5–10 phút: test → build arm64 → build x86_64 → kiểm từng file trong app → smoke test cả hai
   (x86_64 chạy dưới Rosetta).
   Thấy ở cuối:
   ```
   ✓ RC ready: dist/ThuChiGiaDinh-1.4.0-rc-arm64.dmg, dist/ThuChiGiaDinh-1.4.0-rc-x86_64.dmg
   ```
   và trong `qa/QA-SIGNOFF-1.4.0.md` có bảng hai file kèm SHA-256, dòng `Bundle compatibility arm64 | arm64: macOS ≥ 11.0`
   và `x86_64: macOS ≥ 11.0`. Bị "RELEASE BLOCKED" thì đọc file trong `qa/reports/1.4.0/` mà nó chỉ ra.
   Nếu UX-03 trượt một lần (lỗi hiếm, ~1/20 lần chạy): chạy lại `release.py rc`.
3. Chọn file theo chip:

   | Máy | Cách xem ( → About This Mac) | File |
   | --- | --- | --- |
   | Chip Apple | Dòng **Chip**: Apple M1, M2, M3… | `…-arm64.dmg` |
   | Intel | Dòng **Processor**: … Intel Core … | `…-x86_64.dmg` |

   Máy anh là chip Apple → `arm64`. Máy vợ: xem tối nay; macOS phải từ **11** trở lên (dòng "macOS Big Sur 11…"
   hoặc mới hơn).
4. Checksum (so với bảng trong biên bản):
   ```sh
   shasum -a 256 dist/ThuChiGiaDinh-1.4.0-rc-*.dmg
   ```

---

## C. Máy anh = TEST

1. **Thoát app đang mở** (⌘Q). Mở `dist/ThuChiGiaDinh-1.4.0-rc-arm64.dmg`, kéo **Thu Chi Gia Dinh** vào
   **Applications** → **Replace**.
2. Mở app. Lần đầu bị chặn: **Done** → System Settings → Privacy & Security → kéo xuống → **Open Anyway**.
   Keychain hỏi quyền thì **Always Allow**.
   Thấy: app mở; ở thanh bên "Phiên bản 1.4.0". Có dữ liệu cũ thì app vừa tự sao lưu:
   ```sh
   ls ~/Library/Application\ Support/ThuChiGiaDinh/backups/
   ```
   Thấy: `budget-<bản cũ>-<ngày>-<giờ>.db` (đây cũng là kết quả ca M-07).
3. Kết nối **TEST**: nếu đang kết nối sheet khác thì Cài đặt → iPhone (Google Sheet) → **Ngắt**. Rồi
   **Nhập dữ liệu → Từ iPhone → Kết nối Google Sheet** → dán **MÃ TEST** → **Kết nối**.
   Thấy: "✅ Đã kết nối Google Sheet **Thu Chi — TEST**", và nhãn cam **TEST** cạnh "Chào …" ở thanh trên.
   Không thấy nhãn → tên sheet chưa có chữ TEST: đổi tên sheet, bấm ↻ Đồng bộ.
4. Phím tắt TEST cho iPhone của anh:
   ```sh
   cd ~/family-budget && .venv/bin/python phone/make_shortcut.py --env test
   open phone/dist        # AirDrop "Ghi chi tiêu TEST.shortcut" sang iPhone
   ```
   Trên Mac: Cài đặt → iPhone → **📋 Sao chép mã cho iPhone** (cùng Apple ID nên dán thẳng được). iPhone: **Thêm
   phím tắt** → dán mã → **Thêm**. Chạy thử 1000 "thử TEST" → thấy "✓ Đã ghi 1.000 ₫ · thử TEST"; trên Mac
   bấm ↻ Đồng bộ → khoản về, nằm trong sheet **TEST**.
5. Chạy các ca thủ công trong `docs/UX-TEST-CASES.md` (bảng M-xx) **trên file RC vừa cài**, ghi vào cột Result
   của `qa/QA-SIGNOFF-1.4.0.md`: `PASS`, `FAIL` hoặc (chỉ P2) `WAIVED: <lý do>`. Làm trên máy anh các ca không cần
   máy hay người khác. Các ca cần máy khác/vợ làm ở mục D:
   - **M-01** (cài trên máy Mac khác) → máy vợ, D2–D3. Máy vợ là Intel thì M-01 trên máy đó cũng là phép thử thật
     duy nhất của bản Intel (ở đây nó chỉ được thử dưới Rosetta).
   - **M-02**, **M-14**, **M-23**, **M-27** → vợ làm.
   - M-04/M-05/M-09/M-10/M-25 (đọc ảnh) làm trên máy anh; máy vợ dưới macOS 13 sẽ báo "Đọc ảnh cần macOS 13…", đúng thiết kế.
6. Lỗi S1/S2 thì dừng: ghi FAIL, sửa theo mục E, chạy lại `release.py rc` (biên bản cũ bị thay; RC mới phải thử lại).
7. **Ký và phát hành** khi mọi P1 đã PASS (kể cả các ca ở mục D). Cuối biên bản viết:
   ```
   Decision: GO
   Approved by: Brian Tran
   Date: 2026-11-02
   ```
   rồi:
   ```sh
   .venv/bin/python packaging/release.py final
   git add qa/QA-SIGNOFF-1.4.0.md && git commit -m "QA sign-off 1.4.0: GO"
   ```
   Thấy: `✓ Released release/ThuChiGiaDinh-1.4.0-arm64.dmg, release/ThuChiGiaDinh-1.4.0-x86_64.dmg`. Thư mục `release/`
   giữ mọi bản đã phát hành, **không xoá**: đó là đường lui (mục F). Nên chép thêm `release/` ra iCloud Drive/USB.
   PR `release/1.4.0` → `main` và tag `v1.4.0` theo `docs/RELEASE-PROCESS.md` bước 6, làm lúc nào cũng được.

---

## D. Máy vợ = PRODUCTION

1. Tạo thư mục giao (sau `release.py rc`; sau final thì thêm `--final`):
   ```sh
   cd ~/family-budget && caffeinate -i .venv/bin/python packaging/delivery.py
   git checkout packaging/guide/img     # script chụp lại ảnh hướng dẫn; bỏ thay đổi đó
   ```
   Thấy: `delivery/ThuChiGiaDinh-1.4.0/` và `.zip`, gồm: `1. Hướng dẫn sử dụng.pdf`, hai file `2. File cài đặt - máy chip
   Apple…dmg` / `…chip Intel…dmg`, `3. Hướng dẫn cài đặt.txt`, `4. iPhone/` (Phím tắt **production** đã ký +
   `CAI-DAT-IPHONE.txt`), `5. Cho người cài đặt/` (`Code.gs`, `SHA256.txt`). Script từ chối nếu DMG không phải đúng
   bản có SHA trong biên bản. Không có Chrome thì thêm `--no-pdf`.
2. AirDrop file `.zip` sang máy vợ, mở ra. Xem chip ( → About This Mac), mở **đúng** file `2. File cài đặt …`,
   kéo vào **Applications**.
3. Mở app → bị chặn → **Done** → mở chặn:
   - macOS 13+: System Settings → **Privacy & Security** → kéo xuống → **Open Anyway** → mật khẩu máy.
   - macOS 11/12: System Preferences → **Security & Privacy** → tab **General** → **Open Anyway**.
   Thấy: màn hình chào mừng. Ghi kết quả **M-01** (và macOS + chip của máy vào cột Notes).
   App thoát ngay khi mở → ghi FAIL, gửi `~/Library/Application Support/ThuChiGiaDinh/app.log`; tạm thời dùng
   phương án dự phòng ở cuối trang.
4. Chào mừng: nhập tên (ví dụ "Lan"). Gmail: tuỳ chọn, bỏ qua được (nếu làm thì đó là ca M-02, để vợ tự làm).
5. **Giao diện sáng**: Cài đặt → Giao diện → **☀️ Sáng** (vợ không thích nền tối). Tắt app, mở lại: vẫn sáng (M-27).
6. Tên máy cho tab Giao dịch: Cài đặt → iPhone → Tên máy, ví dụ `MacBook Lan`.
7. Kết nối **PRODUCTION**: AirDrop ghi chú **MÃ PRODUCTION** sang máy vợ (hoặc gõ vào Ghi chú), rồi
   **Nhập dữ liệu → Từ iPhone → Kết nối Google Sheet** → dán → **Kết nối**. Xoá ghi chú chứa mã sau khi dán.
   Thấy: "✅ Đã kết nối Google Sheet **Thu Chi — PRODUCTION**", **không** có nhãn TEST, không có cảnh báo Code.gs cũ.
   **Thấy nhãn TEST ở đây là dán nhầm mã: Ngắt ngay, dán lại MÃ PRODUCTION.**
8. iPhone của vợ: AirDrop `4. iPhone/Ghi chi tiêu.shortcut`. Trên Mac vợ: Cài đặt → iPhone → **📋 Sao chép mã cho
   iPhone** → dán trên iPhone (cùng Apple ID thì Universal Clipboard; khác thì AirDrop ghi chú rồi xoá).
   **Thêm phím tắt** → dán mã → **Thêm**. Để vợ tự làm theo `CAI-DAT-IPHONE.txt` = ca M-23.
9. iPhone của anh: cũng AirDrop `Ghi chi tiêu.shortcut` (icon xanh lá), dán **MÃ PRODUCTION**. iPhone anh giờ có hai
   phím tắt: **Ghi chi tiêu** (chi tiêu thật của gia đình → PRODUCTION) và **Ghi chi tiêu TEST** (chỉ để thử).
10. **Kiểm tra đầu–cuối bằng một khoản thật**: trên iPhone vợ chạy **Ghi chi tiêu**, ghi một khoản chi thật.
    Thấy: "✓ Đã ghi …". Mở sheet **Thu Chi — PRODUCTION** → tab Hộp thư đến có dòng đó, cột Người nhập là tên iPhone vợ.
    Trên Mac vợ bấm **↻ Đồng bộ** → "📱 Đã lấy 1 khoản mới từ iPhone"; tab Giao dịch có khoản đó. Khoảng 10 giây sau,
    tab **Giao dịch** của sheet PRODUCTION có dòng đó với cột Máy = `MacBook Lan`. Sheet **TEST** không có gì mới.
11. Quay lại C7 khi mọi P1 đã PASS.

**Xem vợ dùng app thế nào:** mở sheet PRODUCTION → tab **Tổng hợp** → Data → Create a filter → lọc cột **Nhóm** =
`Hoạt động` (lần mở gần nhất, số lần mở, số lần dùng từng việc trong 30 ngày, phiên bản) hoặc `Lỗi` (10 lỗi gần nhất,
chỗ vợ bị vướng), và cột **Máy** = tên máy vợ (bước 6). Các dòng này cập nhật vài giây sau mỗi lần vợ mở app; vợ tắt
"Gửi thống kê sử dụng" trong Cài đặt thì chúng biến mất ở lần đẩy sau. Không cần sửa Code.gs (vẫn `SCRIPT_VERSION` 2).

---

## E. Vòng sửa lỗi: sửa → TEST → PRODUCTION

1. Nhánh mới từ nhánh tích hợp, viết test tái hiện lỗi trước:
   ```sh
   cd ~/family-budget && git switch feat/phone-inbox && git switch -c fix/<mô-tả-ngắn>
   ```
2. Sửa, chạy test:
   ```sh
   caffeinate -i .venv/bin/python -m pytest -q -p no:cacheprovider tests --ignore=tests/test_packaged.py
   ```
3. Tăng `VERSION` trong `app.py` (sửa lỗi: PATCH, ví dụ `1.4.1`), thêm mục trong `CHANGELOG.md`. Commit, gộp vào
   nhánh tích hợp (`git switch feat/phone-inbox && git merge --no-ff fix/<…>`).
4. RC mới: `git switch -c release/1.4.1` → `caffeinate -i .venv/bin/python packaging/release.py rc`.
5. **TEST trước**: cài `dist/ThuChiGiaDinh-1.4.1-rc-arm64.dmg` lên máy anh (thoát app, kéo đè, Replace). Thấy:
   "Phiên bản 1.4.1" và một file mới trong `backups/`. Thử đúng lỗi vừa sửa bằng **Ghi chi tiêu TEST**, rồi các ca
   P1 (hotfix: P2 không liên quan ghi `WAIVED: hotfix`). Ký biên bản → `release.py final`.
6. **PRODUCTION sau**: AirDrop `release/ThuChiGiaDinh-1.4.1-<chip>.dmg` sang máy vợ → thoát app (⌘Q) → kéo đè vào
   Applications → **Replace** → mở. Dữ liệu và mã kết nối (Keychain) giữ nguyên; app tự chép `budget.db` vào
   `backups/budget-1.4.0-<ngày>-<giờ>.db` trước khi nâng cấp (giữ 10 bản gần nhất). Có thể phải Open Anyway và
   "Always Allow" Keychain lại, vì mỗi bản build có chữ ký ad-hoc khác.
   Kiểm: bấm ↻ Đồng bộ, ghi một khoản bằng Phím tắt như D10.

**Khi `Code.gs` thay đổi** (diff có `phone/Code.gs`; nếu app cần bản mới thì `SCRIPT_VERSION` và
`REQUIRED_SCRIPT_VERSION` đã được tăng cùng nhau, có test giữ hai số này khớp):

1. **TEST trước**: mở sheet **Thu Chi — TEST** → Extensions → Apps Script → xoá hết, dán `phone/Code.gs` mới → ⌘S →
   **Deploy → Manage deployments → ✏️ (Edit) → Version: New version → Deploy**. **Không** bấm New deployment: nó tạo
   địa chỉ mới và mọi mã kết nối cũ ngừng hoạt động. Bản cần quyền mới (bản 3: Gmail; bản 4: dịch vụ bên
   ngoài cho Telegram; bản 5 không cần quyền mới) thì chạy `batQuetEmail` hoặc `batTelegram` → Allow **trước** khi Deploy (mục G1, H3). Kiểm: `curl -sL 'MÃ TEST&a=ping'` ra `"version":<số mới>`;
   trên máy anh bấm ↻ Đồng bộ → cảnh báo "Code.gs … bản cũ" (nếu có) biến mất; Phím tắt TEST ghi được.
2. **PRODUCTION sau**, chỉ khi TEST ổn và **trước hoặc cùng lúc** cài app mới lên máy vợ: làm y hệt trên sheet
   **Thu Chi — PRODUCTION**. Kiểm bằng `curl` với MÃ PRODUCTION và một khoản thật trên iPhone.
3. Code.gs mới phải chạy được với app cũ (chỉ thêm, không đổi tên trường), để đổi Code.gs trước khi cập nhật app
   không làm hỏng máy vợ.

---

## F. Quay về bản trước (rollback)

**1. Cài lại DMG cũ** (thường là đủ). Mọi bản đã phát hành nằm trong `release/` trên máy anh.
1. Máy vợ: thoát app (⌘Q).
2. AirDrop `release/ThuChiGiaDinh-<bản trước>-<chip>.dmg` → kéo vào Applications → **Replace** → mở.
3. Dữ liệu vẫn giữ. Thay đổi database giữa các bản chỉ **thêm** cột/bảng, nên bản cũ đọc được database mới
   (app cũng chép thêm một bản sao lưu khi phát hiện phiên bản đổi).

**2. Khôi phục dữ liệu** — chỉ khi dữ liệu thật sự hỏng (số liệu sai hàng loạt, app báo lỗi database):
```sh
osascript -e 'quit app "Thu Chi Gia Dinh"'
cd ~/Library/Application\ Support/ThuChiGiaDinh
ls -lt backups/                                   # chọn bản ngay trước lần nâng cấp gây lỗi
mv budget.db "budget.db.hong-$(date +%Y%m%d-%H%M)"   # giữ lại bản hỏng, không xoá
cp backups/budget-1.4.0-20261102-2130.db budget.db   # ← thay bằng tên file đã chọn
open -a "Thu Chi Gia Dinh"
```
- Mất những gì nhập **trên Mac** sau thời điểm sao lưu (nhập tay, ảnh chụp, Gmail đồng bộ lại được).
- Khoản ghi **từ iPhone** không mất: chúng vẫn nằm trong tab Hộp thư đến của sheet; bấm ↻ Đồng bộ là về lại, không trùng.
- Tab Giao dịch/Tổng hợp của sheet sẽ được ghi đè theo dữ liệu vừa khôi phục ở lần đẩy kế tiếp.

**3. Code.gs**: Deploy → Manage deployments → ✏️ → Version: chọn **phiên bản cũ** trong danh sách → Deploy. Địa chỉ và
mã giữ nguyên. Dán lại Code.gs bản 2 vào trình soạn thì chạy `tatQuetEmail` (và `tatTelegram`) **trước** (lịch 30 phút chạy code đã lưu chứ không
theo bản Deploy; mất hàm `quetEmail` thì Google gửi thư báo lỗi mỗi lần). App 1.5.0 thấy bản 2 thì ngừng lấy email và
báo trong mục Gmail; Phím tắt iPhone không bị ảnh hưởng.

---

## G. Gmail qua Google Sheet (không cần App Password)

Dùng khi Google không cho tạo App Password (tài khoản chỉ dùng passkey/khoá bảo mật, Advanced Protection, tài khoản
công ty…). Apps Script trong sheet đọc Gmail **của chủ sheet** (anh) mỗi 30 phút và chép email Shopee/TikTok/MoMo,
**cả nội dung**, vào tab **Email**. App Mac lấy các dòng đó mỗi lần đồng bộ và đọc như email IMAP (cùng bộ đọc, cùng
cách bỏ quảng cáo, mỗi đơn tính một lần). Thư của vợ đi vào Gmail của anh bằng bộ lọc chuyển tiếp trong Gmail của vợ.

```
Gmail vợ ──bộ lọc chuyển tiếp──▶ Gmail anh ──quetEmail mỗi 30 phút──▶ tab "Email" ──a=emails──▶ app Mac (máy vợ)
```

Cần `Code.gs` bản 3 và app 1.5.0. App cũ không đọc tab Email nhưng vẫn chạy bình thường với Code.gs bản 3.

### G1. Bật trên sheet (làm TEST trước, rồi PRODUCTION)

1. Mở sheet (**Thu Chi — TEST**, sau đó **Thu Chi — PRODUCTION**) → **Extensions → Apps Script** → xoá hết, dán
   `phone/Code.gs` mới → ⌘S. Thấy `var SCRIPT_VERSION = 3;` (hoặc số lớn hơn).
2. Chọn hàm **batQuetEmail** → **▶ Run** → **Review permissions** → chọn **tài khoản Google của anh** (chủ sheet) →
   Advanced → Go to … (unsafe) → **Allow**. Google ghi "Read, compose, send, and permanently delete all your email":
   đó là quyền duy nhất Google cho `GmailApp` (xem "Vì sao không chỉ đọc" bên dưới). Code chỉ tìm và đọc thư.
   Thấy trong Execution log: `Đã bật quét Gmail mỗi 30 phút. Lần này lưu N email mới vào tab "Email"…`; trong sheet
   có tab **Email** (Mã thư, Ngày, Người gửi, Tiêu đề, Nội dung, Ghi chú, Message-ID).
3. **Bước 2 phải xong trước bước này.** **Deploy → Manage deployments → ✏️ → Version: New version → Deploy**.
   Bản mới cần quyền Gmail; nếu Deploy khi chưa Allow, Google có thể trả "Authorization is required…" cho mọi lời
   gọi, kể cả Phím tắt iPhone (app Mac sẽ báo "Code.gs mới cần thêm quyền…"). Sửa: làm bước 2 rồi Deploy lại.
4. Kiểm:
   ```sh
   curl -sL 'MÃ&a=ping'          # "version":3 (hoặc lớn hơn)
   curl -sL 'MÃ&a=emails' | head -c 400
   ```
   Thấy `{"ok":true,"rows":[{"id":"18…","date":"2026-…","from":"Shopee <…>",…}],"next":"…","more":false,"scanned":"…"}`.
   Phím tắt iPhone vẫn ghi được (thử một khoản).
5. Trong app (1.5.0): bấm **↻ Đồng bộ**. Nhập dữ liệu → Gmail → mục **"Không tạo được App Password? Đọc Gmail qua
   Google Sheet"** hiện `Code.gs bản 3 · N email, mới nhất … · lấy về …` và "Google quét Gmail lần cuối …". Có đơn
   mới thì chuông có "✉️ N đơn mới từ Gmail (qua Google Sheet)".

Tắt: chạy **tatQuetEmail** (xoá lịch 30 phút; tab Email giữ nguyên). Đổi câu tìm: Project Settings (⚙️) →
**Script properties** → thêm `EMAIL_QUERY`, ví dụ `from:(shopee OR tiktok OR momo OR lazada) newer_than:30d -in:spam -in:trash`.
Chạy `batQuetEmail` lần nữa không tạo lịch thứ hai.

### G2. Chuyển tiếp thư của vợ sang Gmail của anh

Trên máy tính, đăng nhập **Gmail của vợ** (giao diện tiếng Anh; tiếng Việt ghi trong ngoặc):

1. ⚙️ → **See all settings** (Xem tất cả chế độ cài đặt) → tab **Forwarding and POP/IMAP** (Chuyển tiếp và POP/IMAP)
   → **Add a forwarding address** (Thêm địa chỉ chuyển tiếp) → gõ Gmail của anh → Next → Proceed → OK.
2. Gmail gửi thư xác nhận tới **hộp thư của anh**: mở thư "Gmail Forwarding Confirmation" và bấm link (hoặc gõ mã
   xác nhận vào ô ở trang của vợ → Verify). **Không** bật "Forward a copy of incoming mail" cho mọi thư: để
   "Disable forwarding", chỉ bộ lọc ở bước 3 mới chuyển.
3. Ô tìm kiếm của Gmail vợ → biểu tượng bộ lọc (Show search options) → **From**: `shopee OR tiktok OR momo` →
   **Create filter** → tick **Forward it to** (Chuyển tiếp tới) → chọn Gmail của anh → **Create filter**.
4. Gmail giữ nguyên **người gửi gốc** (Shopee, TikTok, MoMo) khi tự chuyển tiếp, nên câu tìm `from:(shopee OR tiktok OR momo)`
   của script vẫn bắt được, và cột Ghi chú ghi "chuyển tiếp từ <gmail vợ>". Bộ lọc chỉ áp cho thư **đến sau khi tạo**;
   thư cũ cần thì chuyển tiếp tay (app vẫn nhận ra Shopee/TikTok/MoMo trong thư "Fwd:").
5. Kiểm: nhờ vợ đặt một đơn (hoặc chuyển tiếp tay một email đơn hàng cũ). Trong ≤ 30 phút dòng đó có ở tab Email;
   bấm ↻ Đồng bộ trên Mac vợ → giao dịch có số tiền và tên sản phẩm (ca **M-29**).

### Vì sao không chỉ đọc (gmail.readonly)

Tài liệu Google cho `GmailApp.search`, `getMessageById` và các hàm đọc thư (`getPlainBody`, `getBody`, `getHeader`…)
chỉ liệt kê một quyền là `https://mail.google.com/` (toàn quyền) —
<https://developers.google.com/apps-script/reference/gmail/gmail-app>,
<https://developers.google.com/apps-script/reference/gmail/gmail-message>. Ghi `gmail.readonly` vào `oauthScopes` của
manifest thì GmailApp không được Google bảo đảm chạy. Muốn chỉ đọc phải chuyển sang Advanced Gmail service (Gmail API),
bật thêm dịch vụ và tự giải mã MIME/base64 của từng thư: nhiều bước cài và nhiều code hơn cho một script gia đình, nên
chưa làm. Script chạy trong tài khoản của anh, không gửi thư đi đâu ngoài tab Email của chính sheet đó.

### Giữ bao nhiêu

- Mỗi lần quét: tối đa 500 luồng thư khớp câu tìm, lưu tối đa 200 thư mới (phần còn lại lần sau), cũ nhất trước.
- Tab Email giữ thư **90 ngày** gần nhất và tối đa **1000 dòng**; dòng cũ hơn bị xoá. Thư cũ hơn 90 ngày không được
  chép lại.
- Nội dung cắt ở **45.000 ký tự** (một ô Sheets chứa tối đa 50.000). Email đơn hàng thường dưới 10.000.
- App nhớ dòng cuối đã lấy (con trỏ = Mã thư) và mỗi lần lấy tối đa 100 dòng một trang. Con trỏ bị xoá (Mac tắt
  hơn 90 ngày) thì script gửi lại từ đầu, app bỏ qua thư đã có. **Đừng sắp xếp hay sửa tab Email** bằng tay.

---

## H. Bot Telegram cho nhóm gia đình

Vợ ghi khoản chi và xem báo cáo ngay trong một **nhóm Telegram** (anh + vợ + bot), không cần mở Mac. Bot chạy trong
Apps Script của **sheet PRODUCTION** (không thêm tài khoản, máy chủ nào): cứ mỗi phút script đọc tin nhắn mới trong
nhóm, nên tin **đầu tiên** chậm **tối đa khoảng 1 phút**; từ Code.gs bản 5, trong khoảng 2 phút sau đó bot trả lời và
nhận nút bấm **gần như ngay** (H6). Không có AI: số tiền và hạng mục đọc theo quy tắc (từ khoá của app Mac), còn lại là
bấm nút.

```
Nhóm Telegram ──"45k phở tm"──▶ Telegram ◀──getUpdates mỗi phút── Apps Script (pollTelegram) ──▶ tab "Hộp thư đến"
                                                                              │                        (Kênh = telegram)
                         ◀── nút hạng mục, "✓ Đã ghi…", báo cáo ───────────────┘                          │
app Mac (máy vợ) ◀──────────────────────────── a=list mỗi lần đồng bộ, như khoản từ iPhone ─────────────────┘
```

Cần `Code.gs` bản 4, nên dùng bản 5 (app 1.4.0 vẫn chạy với cả hai; app 1.5.0 thêm nhãn 💬 Telegram, bỏ ra khoản đã huỷ
và gửi từ khoá cho bot). Làm trên
sheet **TEST** trước với một nhóm thử, rồi làm lại trên **PRODUCTION** với nhóm gia đình. Mỗi sheet cần **một bot
riêng** (hai sheet cùng đọc một bot thì mỗi tin nhắn chỉ đến một bên).

### H1. Tạo bot (trên điện thoại hoặc Telegram Desktop, khoảng 3 phút)

1. Mở Telegram, tìm **@BotFather** (có dấu tích xanh) → **Start**.
2. Gõ `/newbot`. Đặt tên hiện thị, ví dụ `Sổ thu chi nhà mình`, rồi tên đăng nhập kết thúc bằng `bot`, ví dụ
   `sothuchi_nhaminh_bot` (TEST: `sothuchi_nhaminh_test_bot`).
3. BotFather trả về **token** dạng `123456789:AAH…`. Đây là chìa khoá điều khiển bot: giữ kín như mật khẩu, không
   dán vào nhóm chat, không ghi vào Code.gs.
4. **Bắt buộc — tắt privacy mode:** gõ `/setprivacy` → chọn bot vừa tạo → **Disable**. BotFather trả lời
   "Privacy mode is disabled". Bỏ bước này thì trong nhóm bot **chỉ thấy lệnh** `/…`, không thấy `45k phở`, và im lặng
   như hỏng. Đã thêm bot vào nhóm rồi mới tắt thì phải **xoá bot khỏi nhóm và thêm lại** mới có tác dụng. `batTelegram`
   và `/huongdan` đều báo nếu privacy mode còn bật.

### H2. Cất token vào sheet

1. Mở sheet → **Extensions → Apps Script** → ⚙️ **Project Settings** (thanh trái) → kéo xuống **Script properties** →
   **Add script property**.
2. Property: `TELEGRAM_TOKEN` · Value: token ở H1 bước 3 → **Save script properties**.

Token chỉ nằm trong Script properties của sheet đó (người được chia sẻ sheet với quyền sửa script mới xem được).

### H3. Bật bot (thứ tự này quan trọng)

1. Trình soạn code: xoá hết, dán `phone/Code.gs` mới → ⌘S. Thấy `var SCRIPT_VERSION = 5;`.
2. Chọn hàm **batTelegram** → **▶ Run** → **Review permissions** → tài khoản của anh → Advanced → Go to … (unsafe) →
   **Allow**. Google hỏi thêm quyền **"Connect to an external service"** (`UrlFetchApp`, để gọi api.telegram.org).
   Thấy trong Execution log:
   ```
   Bot @sothuchi_nhaminh_bot đang chạy (đọc tin nhắn mỗi phút). Trong nhóm gia đình gõ: /ketnoi 123456
   ```
   Chép mã 6 số. Trong **Triggers** (biểu tượng đồng hồ, thanh trái) có một dòng `pollTelegram` · Time-based · Every
   minute. Chạy `batTelegram` lần nữa không tạo lịch thứ hai và giữ nguyên mã.
3. **Bước 2 phải xong trước bước này.** **Deploy → Manage deployments → ✏️ → Version: New version → Deploy**. Giống
   mục G: Deploy khi chưa Allow thì Google có thể trả "Authorization is required" cho mọi lời gọi, kể cả Phím tắt iPhone.
   Bot tự nó chạy theo lịch (dùng code đã lưu), nhưng `a=list` mới cho app Mac (cột Kênh, khoản đã huỷ) cần New version.
4. Kiểm: `curl -sL 'MÃ&a=ping'` ra `"version":5`.

### H4. Nhóm gia đình

1. Telegram → ✏️ → **New Group** → thêm vợ → đặt tên, ví dụ `Thu chi nhà mình` → Create.
2. Trong nhóm: tên nhóm → **Add members** → tìm tên đăng nhập của bot → Add.
3. Gõ trong nhóm: `/ketnoi 123456` (mã ở H3). Đợi tối đa 1 phút. Thấy:
   `✓ Đã kết nối nhóm "Thu chi nhà mình". Thử gõ: 45k phở`.
   Nhóm (hay chat riêng) chưa kết nối thì bot bỏ qua mọi tin nhắn, chỉ trả lời một câu "Bot riêng của gia đình…" mỗi
   ngày. Lộ mã: chạy `doiMaTelegram` (mã mới, mọi nhóm phải `/ketnoi` lại). Chat riêng với bot cũng kết nối được
   bằng cùng lệnh.

### H5. Thử

1. Gõ `45k quà sinh nhật` (không có từ khoá nào). Trong ≤ 1 phút bot trả lời `45.000 ₫ · Quà sinh nhật — hạng mục?` với
   các nút: **✨ Tự động**, các hạng mục chi như trong app, rồi 💼 Lương, 💰 Thu nhập khác (chọn hai nút này thì ghi
   thành **khoản thu**).
2. Bấm **🍼 Mẹ & bé** → lần đầu bot hỏi "trả bằng gì?" → bấm **💵 Tiền mặt**. Tin nhắn của bot đổi thành
   `✓ Đã ghi 45.000 ₫ · Quà sinh nhật · 🍼 Mẹ & bé · Tiền mặt — Lan` kèm nút **✏️ Đổi hạng mục** và **↩️ Huỷ**. Tab Hộp
   thư đến có dòng mới: Người nhập `Telegram · Lan`, Kênh `telegram`. Từ lần sau bot nhớ cách trả của từng người.
3. Bản 5, sau khi Mac đã đẩy bản sao một lần: gõ `45k phở bò` → bot **ghi ngay**, không hỏi:
   `✓ Đã ghi 45.000 ₫ · Phở bò · 🛒 Ăn uống & đi chợ · Tiền mặt — Lan`. Hạng mục lấy theo từ khoá của app Mac (Cài đặt →
   Hạng mục & ngân sách), cách trả là cách gõ ở cuối tin hoặc cách trả lần trước của người gõ. `15tr lương ck` ghi
   **khoản thu** 💼 Lương. Sai hạng mục thì bấm **✏️ Đổi hạng mục** → chọn hạng mục khác (chỉ khi Mac chưa lấy khoản
   đó; đã lấy thì bot nói đổi trong app trên Mac).
4. Gõ cách trả ở cuối thì bot dùng cách đó và nhớ nó cho lần sau: `45.000 phở tm`, `1tr5 học phí ck`,
   `120000 cà phê visa`, `200k đi chợ momo`. Gõ thiếu số 0 (`45 phở`) thì bot hỏi lại "Ý bạn là 45.000 ₫?" chứ không
   tự đoán.
5. Bấm **↩️ Huỷ** (ai trong nhóm cũng bấm được; tin nhắn ghi tên người huỷ) hoặc gõ `/huy` (huỷ khoản **chính mình** ghi
   gần nhất, trong 24 giờ). Cột Trạng thái thành `huỷ`. Mac chưa lấy thì không bao giờ lấy; Mac đã lấy thì lần đồng bộ
   sau app 1.5.0 đánh dấu "Không tính" (app 1.4.0 thì không: xoá tay trong app).
6. Gõ `/thang`: chi, thu, còn lại, hạng mục và %, cách trả, số khoản, và dòng
   `Số liệu tới lần Mac đồng bộ 05/11 21:30 + 2 khoản ghi sau đó`. Các lệnh khác: `/homnay`, `/tuan` (thứ Hai → hôm nay),
   `/thang 10`, `/ngansach`, `/ongheo`, `/huongdan`.
7. Trên Mac vợ bấm ↻ Đồng bộ → khoản vừa ghi có nhãn **Telegram**; Giao dịch → lọc **Telegram** (ca **M-31**).

**Báo cáo tự gửi** vào mọi nhóm đã kết nối: tối **Chủ nhật 20:00** báo cáo tuần (thứ Hai → Chủ nhật), **ngày 1 lúc 8:00**
báo cáo tháng trước kèm ống heo; mỗi báo cáo một lần (giờ theo múi giờ của sheet: File → Settings → Time zone). Chậm
tối đa 1 phút như mọi tin khác (ca **M-32**).

### H6. Code.gs bản 5: trả lời nhanh và tự chọn hạng mục

Bản 4 chỉ đọc tin mỗi phút, nên mỗi lần bấm nút cũng phải đợi lượt đọc kế tiếp: một khoản (tin → hạng mục → cách trả)
mất 2–3 phút. Bản 5:

- **Ít bước hơn:** có từ khoá và biết cách trả thì ghi ngay trong lượt đọc đầu tiên (0 lần bấm); không có từ khoá thì
  bấm một nút hạng mục. App 1.5.0 gửi **mọi từ khoá** kèm mỗi lần đẩy bản sao; script lưu vào tab ẩn **Từ khoá** (chỉ
  ghi lại khi danh sách đổi) và dùng từ khoá của **máy đẩy gần nhất**. Cách so khớp giống hệt app (bỏ dấu, nguyên từ,
  từ khoá dài nhất thắng; có test so hai bên). Khớp cả hạng mục chi lẫn thu thì chọn hạng mục chi.
- **Trả lời nhanh khi đang trò chuyện:** sau mỗi tin hay nút bấm, lượt chạy đó không dừng ngay mà chờ tin kế tiếp
  (`getUpdates` long polling 25 giây, Telegram trả về ngay khi có tin) tới khoảng giây thứ 50; cửa sổ này kéo dài
  **2 phút** sau tin cuối. Nút bấm được trả lời (hết vòng xoay) trước khi script ghi sheet. Lúc không ai nhắn, mỗi phút
  vẫn chỉ một lời gọi nhanh như bản 4.
- **Hạn mức mỗi ngày:** thời gian chờ như vậy cộng lại tối đa **40 phút/ngày** (Script property `TG_FAST_MINUTES` để
  đổi, `0` để tắt); quá mức thì về chế độ mỗi phút tới 0 giờ. `kiemTraTelegram` in số phút đã dùng hôm nay, chế độ
  hiện tại và số từ khoá đã nhận.

Nâng cấp (TEST trước, rồi PRODUCTION như mục E):

1. Apps Script của sheet → xoá hết, dán `phone/Code.gs` → ⌘S. Thấy `var SCRIPT_VERSION = 5;`. Lịch `pollTelegram` dùng
   code mới từ lượt chạy kế tiếp; **không cần** chạy lại `batTelegram` (bản 5 không xin thêm quyền). Chỉ khi Google hiện
   "Authorization required" (Executions báo lỗi quyền) thì chạy `batTelegram` → Allow.
2. **Deploy → Manage deployments → ✏️ → Version: New version → Deploy** (để `doPost` nhận từ khoá từ Mac).
3. Trên Mac (app 1.5.0) bấm **↻ Đồng bộ** (hoặc sửa một giao dịch, một từ khoá) để app **đẩy bản sao một lần**; từ
   khoá đi kèm lần đẩy đó, và mỗi lần sửa từ khoá sau này app tự đẩy lại. Kiểm: chạy `kiemTraTelegram` → dòng `7. Từ khoá từ Mac: <số> (máy …)`; tab ẩn **Từ khoá** (View →
   Hidden sheets) có danh sách. Trước lần đẩy đó bot vẫn hỏi hạng mục bằng nút như bản 4.
4. Thử: `45k phở bò` → "✓ Đã ghi …" trong vài giây nếu vừa có tin khác, hoặc ≤ 1 phút nếu nhóm đang im.

### Số liệu báo cáo lấy từ đâu

- Tab **Giao dịch** (bản sao app Mac đẩy lên) của **máy đẩy gần nhất**: mỗi lần đẩy, script ghi giờ đẩy và giờ máy đó
  đọc Hộp thư đến lần cuối. Máy khác bị bỏ qua để khoản iPhone/Telegram không bị đếm hai lần.
- Cộng các dòng **Hộp thư đến** ghi **sau** lần đọc đó (Telegram, iPhone, gõ tay), trừ dòng `huỷ`. Dòng chọn
  ✨ Tự động hoặc không có hạng mục tính vào **"Chưa phân loại (chờ Mac)"** cho tới khi Mac phân loại.
- **Ngân sách**: app 1.5.0 gửi kèm các dòng nhóm `Ngân sách` trong tab Tổng hợp. Ghi một khoản chi vào hạng mục có ngân sách
  mà tháng này đã dùng ≥ 80% hoặc vượt 100% thì tin "Đã ghi" có thêm một dòng ⚠️/🔴, mỗi hạng mục mỗi mức một lần mỗi tháng.
- **Ống heo**: nhóm `Ống heo` trong tab Tổng hợp (tháng đã khép sổ trên Mac).
- Mac chưa đẩy lần nào từ khi lên bản 4 thì báo cáo nói rõ "Chưa có số liệu từ Mac" và chỉ tính các khoản trong Hộp thư
  đến: mở app trên Mac một lần là có.

### Tắt, đổi, gỡ

- `tatTelegram`: xoá lịch mỗi phút (bot im). `batTelegram` bật lại, giữ mã và nhóm.
- Script property `TG_FAST_MINUTES`: số phút trả lời nhanh mỗi ngày (mặc định 40, `0` = chỉ đọc mỗi phút như bản 4).
- `doiMaTelegram`: mã `/ketnoi` mới và quên mọi nhóm đã kết nối.
- Đổi token (lộ token): @BotFather → `/revoke` → chọn bot → sửa `TELEGRAM_TOKEN` trong Script properties → chạy `batTelegram`.
- Lỗi gần nhất của bot (nếu có) nằm ở Script properties → `TG_LAST_ERROR` (không bao giờ chứa token). Từng lần chạy
  xem ở **Executions** (thanh trái).

### Quota Apps Script

Tài khoản Gmail thường: trigger chạy tối đa **90 phút/ngày** cộng lại, gọi URL tối đa 20.000 lần/ngày. Lịch mỗi phút
là 1.440 lần chạy/ngày; lúc không có tin nhắn mỗi lần là một lời gọi `getUpdates` (khoảng 0,3–1 giây) → khoảng
**8–25 phút/ngày** (10–30% quota); mỗi khoản ghi thêm khoảng 1–2 giây. Bản 5: mỗi lần trò chuyện (một tin, vài nút bấm)
giữ 2–3 lượt chạy chờ khoảng 50 giây, tức **2–3 phút**; 10 lần trò chuyện rải rác trong ngày ≈ 20–30 phút, và **không
quá 40 phút/ngày** (`TG_FAST_MINUTES`). Lời gọi URL thêm khoảng 2 lần/phút khi đang chờ, không đáng kể. Quét Gmail
30 phút/lần (mục G) thêm khoảng 2–8 phút. Trường hợp xấu nhất 25 + 40 + 8 ≈ 73 phút, vẫn dưới 90; dùng thêm Apps
Script khác trong cùng tài khoản thì hạ `TG_FAST_MINUTES`. Hết quota thì Google tạm dừng các trigger tới khi quota ngày hồi lại và gửi thư báo lỗi: bot im, Phím tắt iPhone
và app Mac vẫn chạy. Xem thời gian thật ở **Executions** (cột Duration).

---

## Phương án dự phòng: app không mở được trên máy vợ

Nếu DMG đúng chip không mở được (M-01 FAIL), chạy từ mã nguồn trên máy vợ; không cần quyền admin. Trên máy anh:
```sh
cd ~/family-budget && git archive --format=zip -o ~/Desktop/thuchi-src.zip release/1.4.0
```
AirDrop `thuchi-src.zip` sang máy vợ, rồi trên máy vợ (Terminal):
```sh
mkdir -p ~/thuchi && cd ~/thuchi && unzip -q ~/Downloads/thuchi-src.zip
curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
~/.local/bin/uv venv --python 3.12 .venv && ~/.local/bin/uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python desktop.py
```
Dùng cùng thư mục dữ liệu và Keychain như bản đóng gói, nên sau này chuyển sang DMG không mất gì. Gửi `app.log`
của lần DMG không mở để sửa.

## Liên quan

- `docs/RELEASE-PROCESS.md`: cổng QA, nhánh git.
- `docs/LIMITATIONS.md`: macOS 11/12 so với 13+, bản Intel chỉ được thử dưới Rosetta.
- `phone/README.md`: Apps Script và Phím tắt chi tiết, sự cố thường gặp.
