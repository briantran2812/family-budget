# Quy trình phát triển và phát hành

Không có bản nào được gửi cho người dùng nếu chưa qua cổng QA. Từng bước triển khai TEST → PRODUCTION: [DEPLOY.md](DEPLOY.md). Script `packaging/release.py`
**chặn** release nếu bất kỳ điều kiện nào dưới đây chưa đạt; không thể bỏ qua bằng tay.

## Nhánh git

| Nhánh | Chứa gì | Cách code đi vào |
| --- | --- | --- |
| `main` | Chỉ code của bản **đã phát hành** (QA kết luận GO), mỗi bản có tag `vX.Y.Z` | PR từ `develop` sau khi `release.py final` đạt |
| `develop` | Code đã xong, đạt test tự động, chờ QA | PR từ nhánh việc |
| `feat/…`, `fix/…`, `chore/…` | Một việc mỗi nhánh, tách ra từ `develop` | Commit thường |

- Không commit thẳng vào `main` hay `develop`.
- `release.py rc` và `release.py final` chỉ chạy trên `develop` hoặc `release/…`. Nhờ vậy QA luôn thử code đã được gộp, không phải code của một nhánh lẻ.
- Tag RC (`vX.Y.Z-rc.N`) gắn trên `develop`; tag phát hành (`vX.Y.Z`) gắn trên `main`.

## Các giai đoạn

| # | Giai đoạn | Đầu ra | Ai làm |
| --- | --- | --- | --- |
| 1 | **Yêu cầu** | Một mục trong `CHANGELOG.md` (mục "Chưa phát hành") nêu thay đổi gì và vì sao | Chủ sản phẩm |
| 2 | **Thiết kế** | Với thay đổi lớn: ghi chú trong PR/commit, cập nhật `docs/LIMITATIONS.md` nếu thêm hoặc bớt giới hạn | Dev |
| 3 | **Code + test tự động** | Code kèm test: unit hoặc integration cho logic, E2E (`tests/e2e`) cho mọi thay đổi giao diện | Dev |
| 4 | **Kiểm thử tự động** (cổng 1) | `release.py rc`: unit + integration + OCR, E2E UX trên WebKit, build arm64 và x86_64, kiểm tra từng file trong app (CPU, macOS tối thiểu), smoke test bản đóng gói (x86_64 dưới Rosetta). **Fail một test là dừng** | Script |
| 5 | **QA thủ công** (cổng 2) | Chạy các ca M-xx trong `docs/UX-TEST-CASES.md` **trên đúng file RC**; ghi kết quả vào `qa/QA-SIGNOFF-<ver>.md`; kết luận GO hoặc NO-GO | QA (người không viết code) |
| 6 | **Phát hành** | `release.py final`: kiểm tra biên bản rồi đưa file vào `release/`. Mở PR `develop` → `main`, merge, gắn tag `vX.Y.Z` trên `main`. Gửi file trong `release/` cho người dùng | Người duyệt |
| 7 | **Bảo trì** | Ghi nhận phản hồi và email không đọc được; lỗi S1/S2 xử lý theo luồng hotfix | Dev |

## Cổng QA: `release.py final` chỉ chạy khi đủ cả 5 điều kiện

1. Có cả hai file `dist/ThuChiGiaDinh-<ver>-rc-arm64.dmg` và `dist/ThuChiGiaDinh-<ver>-rc-x86_64.dmg`.
2. **SHA-256 của cả hai file RC khớp với mã ghi trong biên bản.** QA đã thử đúng các file này; build lại
   thì phải thử lại.
3. Mọi ca thủ công **P1** có kết quả `PASS`.
4. Mọi ca **P2** có kết quả `PASS` hoặc `WAIVED: <lý do>`.
5. Biên bản ghi `Decision: GO` và có tên người duyệt ở dòng `Approved by:`.

## Lệnh

```sh
# 0. Cài môi trường (một lần)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller pytest playwright
.venv/bin/python -m playwright install webkit
packaging/setup_build_env.sh      # Python cho bản đóng gói (macOS 11+, arm64 và x86_64); không cần quyền admin

# Trong lúc code
.venv/bin/python -m pytest tests --ignore=tests/e2e      # nhanh, khoảng 5 giây
.venv/bin/python -m pytest tests/e2e                      # UX, khoảng 15 giây

# Release
#   tăng VERSION trong app.py, cập nhật CHANGELOG.md
.venv/bin/python packaging/release.py rc                  # → dist/…-rc.dmg + qa/QA-SIGNOFF-<ver>.md
#   QA chạy các ca M-xx trên file RC, điền biên bản
.venv/bin/python packaging/release.py final               # → release/ThuChiGiaDinh-<ver>-{arm64,x86_64}.dmg
```

## Đánh số phiên bản

Dùng `MAJOR.MINOR.PATCH`:

- **PATCH:** sửa lỗi, cập nhật mẫu email.
- **MINOR:** thêm tính năng.
- **MAJOR:** thay đổi database mà không chuyển dữ liệu cũ tự động được (nên tránh).

Mọi thay đổi cấu trúc database phải kèm migration trong `db.init()` và một test giống
`test_schema_migration_from_v1`.

## Hotfix (lỗi S1/S2 sau khi đã phát hành)

1. Viết test tái hiện lỗi trước, rồi mới sửa.
2. Tăng PATCH và chạy `release.py rc`.
3. QA chạy lại các ca **P1** cùng những ca liên quan tới lỗi. Các ca P2 không liên quan được ghi
   `WAIVED: hotfix`.
4. Chạy `release.py final`.
