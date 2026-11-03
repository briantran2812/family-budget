# QA sign-off — Thu Chi Gia Đình 1.5.0

- Built: 2026-11-03

| CPU | RC file | SHA-256 |
| --- | --- | --- |
| Apple chip (M1, M2…) | `dist/ThuChiGiaDinh-1.5.0-rc-arm64.dmg` | `e663e1cc60b0ed2be9827b4d2165babc6246dab011259c427452de62faa27509` |
| Intel | `dist/ThuChiGiaDinh-1.5.0-rc-x86_64.dmg` | `539ec8d99be4ee4a03d965032474c5c56878409f2516e38dbcd224d4da5263cd` |

## Automated (filled by release.py — do not edit)

| Suite | Result |
| --- | --- |
| Unit + integration + OCR | 241 passed in 4.63s |
| End-to-end UX (WebKit) | 58 passed in 44.21s |
| Bundle compatibility arm64 | arm64: macOS ≥ 11.0 |
| Bundle compatibility x86_64 | x86_64: macOS ≥ 11.0 |
| Packaged app smoke test arm64 | 7 passed in 3.88s |
| Packaged app smoke test x86_64 | 7 passed in 8.47s |

Reports: `qa/reports/1.5.0/`

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
| M-29 | P1 | Đơn của vợ qua Gmail chuyển tiếp | ☐ | |
| M-31 | P1 | Vợ ghi khoản chi trong nhóm Telegram và đọc /thang | ☐ | |
| M-32 | P2 | Báo cáo tuần tự đến tối Chủ nhật | ☐ | |
| M-30 | P2 | Vợ hiểu thẻ Thống kê sử dụng | ☐ | |

## Decision

Decision: ☐ GO  ☐ NO-GO
Approved by:
Date:
