# QA sign-off — Thu Chi Gia Đình 1.2.0

- RC file: `dist/ThuChiGiaDinh-1.2.0-rc.dmg`
- SHA-256: `c048bfbd1fa0d70a95dea4532156f8980adf0e0e6031c743b7a4700a9632723f`
- Built: 2026-10-31

## Automated (filled by release.py — do not edit)

| Suite | Result |
| --- | --- |
| Unit + integration + OCR | 69 passed in 2.69s |
| End-to-end UX (WebKit) | 24 passed in 12.92s |
| Packaged app smoke test | 5 passed in 5.69s |

Reports: `qa/reports/1.2.0/`

## Manual (QA fills in)

Test on **the RC file above**, following docs/UX-TEST-CASES.md. In the Result column write
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

## Known issues (accepted for this RC)

| Severity | Issue |
| --- | --- |
| S4 | Link-style buttons ("Mở trang Mật khẩu ứng dụng ↗", "Mở trang Xác minh 2 bước ↗") show the browser's default blue text instead of the app text colour. Cosmetic; fix in the next build. |

## Field test

The RC was handed to the first real user for M-01/M-02 via `delivery/ThuChiGiaDinh-1.2.0/`
(user guide + this exact RC file, SHA-256 above). Her answers to the guide's last page feed M-02 and M-14.

## Decision

Decision: ☐ GO  ☐ NO-GO
Approved by:
Date:
