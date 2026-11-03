# Chống ghi trùng

Một khoản chi có thể vào app nhiều lần: email của MoMo/Shopee/TikTok, một người ghi qua iPhone hoặc Telegram, người kia
ghi trên Mac. `dedupe.py` là quy tắc duy nhất, gọi ở mọi đường nhập (`gmail_sync.process`, `phone_inbox.apply_row`,
`POST /api/transactions`). Code.gs 6 cảnh báo cùng quy tắc trong nhóm Telegram (`twin_`).

## Email và khoản ghi tay: gộp

Một email và một khoản ghi tay (nguồn `manual`, `phone`, `telegram`, `screenshot`) là **cùng một khoản** khi đủ cả:

| Điều kiện | Vì sao |
| --- | --- |
| cùng loại (chi/thu), số tiền **khớp từng đồng** | email ghi đúng số đã trả |
| ngày ghi tay từ **1 ngày trước** tới **3 ngày sau** ngày trong email | email về lúc trả; người ta ghi sau, hiếm khi trước (trừ khi trả lúc nửa đêm) |
| cách trả không mâu thuẫn: email MoMo chỉ khớp khoản "Ví MoMo" hoặc chưa ghi cách trả | hai tô phở 45k trả tiền mặt không phải email MoMo 45k |
| khoản ghi tay chưa gộp với email nào, chưa được người dùng tách ra | |

- **Đúng một khoản khớp** → gộp. Khoản ghi tay được giữ (mô tả, hạng mục của người dùng), có `link_ref = "momo:<mã>"` và
  học cách trả từ email nếu chưa có. Dòng email giữ lại với `status = 'merged'` và `dup_with` trỏ sang: không tính, không
  hiện, không lên bản sao Sheet, nhưng email lặp lại hay email huỷ đơn vẫn tìm thấy nó (huỷ đơn huỷ luôn khoản ghi tay).
- **Từ hai khoản trở lên** → không đoán: dòng mới vào `cancelled` + `dup_state = 'open'`, chuông 🔔, người dùng chọn.
- **Tách ra** (`split`): cả hai tính riêng, `dup_state = 'kept'`, không bao giờ gộp lại với nhau.
- Xoá khoản ghi tay đã gộp → dòng email tính lại.

## Hai khoản do người ghi: chỉ hỏi

Cùng loại, cùng số tiền, **cùng ngày**, khác người ghi (`entered_by`) **hoặc** khác kênh → cả hai `dup_state = 'open'`,
vẫn tính, có 🔔. Hai bữa trưa 45k là chuyện thường, nên không bao giờ tự gộp. Cùng người, cùng kênh thì không hỏi.

Trả lời: **keep** (giữ cả hai), **drop** (khoản này là bản trùng → `cancelled`); cả hai thành `kept`. Bấm **✔ Khác
khoản** trong Telegram ghi `khác` vào Trạng thái; Mac nhận trong `kept` của `a=list` và đóng câu hỏi.

## Telegram (Code.gs 6)

- Cùng người, cùng số tiền, nội dung, ngày trong **3 phút** → hỏi "➕ Vẫn ghi" (gửi lại vì bot chậm).
- Khoản mới trùng số tiền và ngày chi với dòng Hộp thư đến của người/kênh khác, hoặc với khoản "Nhập tay"/"Ảnh chụp" trong
  tab Giao dịch của Mac đẩy gần nhất → tin "Đã ghi" có ⚠️ và nút **↩️ Trùng — huỷ khoản này / ✔ Khác khoản**.
