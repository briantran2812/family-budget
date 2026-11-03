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
   Thấy: dòng `var SCRIPT_VERSION = 2;` ở gần đầu file.
4. Thanh trên: chọn hàm **caiDat** → **▶ Run** → **Review permissions** → chọn tài khoản →
   "Google hasn't verified this app" → **Advanced → Go to … (unsafe)** → **Allow**.
   Thấy: Execution log ghi `Đã tạo sheet "Hộp thư đến"…`; tab Sheet có tab **Hộp thư đến** với 7 cột.
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
   Thấy: `{"ok":true,"sheet":"https://docs.google.com/…","name":"Thu Chi — TEST","version":2}`
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
   địa chỉ mới và mọi mã kết nối cũ ngừng hoạt động. Kiểm: `curl -sL 'MÃ TEST&a=ping'` ra `"version":<số mới>`;
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
mã giữ nguyên.

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
