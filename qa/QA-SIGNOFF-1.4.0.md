# QA sign-off — Thu Chi Gia Đình 1.4.0

- Built: 2026-11-02

| CPU | RC file | SHA-256 |
| --- | --- | --- |
| Apple chip (M1, M2…) | `dist/ThuChiGiaDinh-1.4.0-rc-arm64.dmg` | `0bec4915c07697030c505239992344211c2c518617936fa1c333e1fbf86c558b` |
| Intel | `dist/ThuChiGiaDinh-1.4.0-rc-x86_64.dmg` | `71f4ee78b99a4f07d1f48ad71d5a1b2cc466b7f092b9616aef881107ab56d0c6` |

## Automated (filled by release.py — do not edit)

| Suite | Result |
| --- | --- |
| Unit + integration + OCR | 208 passed in 3.50s |
| End-to-end UX (WebKit) | 55 passed in 40.82s |
| Bundle compatibility arm64 | arm64: macOS ≥ 11.0 |
| Bundle compatibility x86_64 | x86_64: macOS ≥ 11.0 |
| Packaged app smoke test arm64 | 7 passed in 4.09s |
| Packaged app smoke test x86_64 | 7 passed in 9.05s |

Reports: `qa/reports/1.4.0/`

## Manual (QA fills in)

Test on **the RC files above** (M-01 on the chip of the Mac it will be delivered to), following docs/UX-TEST-CASES.md. In the Result column write
`PASS`, `FAIL`, or `WAIVED: <reason>` (P2 only). Every P1 must be PASS.

| ID | Priority | Case | Result | Notes |
| --- | --- | --- | --- | --- |
| M-01 | P1 | Cài từ DMG trên máy Mac khác | ☐ | |
| M-02 | P1 | Người mới tự kết nối Gmail | ☐ | |
| M-03 | P1 | Đồng bộ Gmail thật | ☐ | |
| M-04 | P1 | Ảnh chụp biên lai MoMo thật | ☐ | |
| M-05 | P1 | Ảnh chụp biên lai chuyển khoản ngân hàng thật | ☐ | |
| M-06 | P1 | Đóng rồi mở lại app | ☐ | |
| M-07 | P1 | Cập nhật đè lên bản cũ | ☐ | |
| M-08 | P1 | Đồng bộ khi mất mạng | ☐ | |
| M-09 | P2 | Kéo thả ảnh vào cửa sổ app | ☐ | |
| M-10 | P2 | Dán ảnh bằng ⌘V | ☐ | |
| M-11 | P2 | Xuất CSV trong cửa sổ app | ☐ | |
| M-12 | P2 | Đổi chế độ sáng/tối | ☐ | |
| M-13 | P2 | Thu hồi App Password | ☐ | |
| M-14 | P2 | Lan đọc lại toàn bộ chữ trong app | ☐ | |
| M-15 | P2 | Hai tài khoản Gmail | ☐ | |
| M-16 | P1 | Đối chiếu sao kê Visa thật | ☐ | |
| M-17 | P2 | PDF sao kê gửi qua email (có mật khẩu) | ☐ | |
| M-18 | P2 | Không tính trùng khi Gmail về sau | ☐ | |
| M-19 | P1 | Cài Apps Script và kết nối | ☐ | |
| M-20 | P1 | Ghi khoản chi trên iPhone thật | ☐ | |
| M-21 | P2 | Ghi nhanh không mở khoá | ☐ | |
| M-22 | P2 | Mất sóng | ☐ | |
| M-23 | P1 | Lan tự cài Phím tắt | ☐ | |
| M-24 | P1 | Bản sao trên sheet thật | ☐ | |
| M-25 | P2 | Ảnh lịch sử app ngân hàng | ☐ | |
| M-26 | P2 | Thông báo ngân sách trên Mac thật | ☐ | |
| M-27 | P2 | Vợ chọn giao diện Sáng | ☐ | |
| M-28 | P2 | Ống heo vào cuối tháng thật | ☐ | |

## Decision

Decision: ☐ GO  ☐ NO-GO
Approved by:
Date:
