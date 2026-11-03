/**
 * Thu Chi Gia Đình — hộp thư đến cho iPhone.
 *
 * Phím tắt "Ghi chi tiêu" trên iPhone gửi từng khoản chi tới đây; script ghi một dòng vào sheet
 * "Hộp thư đến". App trên Mac đọc các dòng đó khi đồng bộ. Cài đặt: phone/README.md.
 *
 *   caiDat()       chạy một lần: tạo sheet và mã bí mật
 *   layMaKetNoi()  sau khi Deploy: in ra mã kết nối để dán vào app Mac và Phím tắt
 *   doiMa()        đổi mã bí mật (mã cũ ngừng hoạt động ngay)
 *
 * App Mac còn ghi bản sao giao dịch vào tab "Giao dịch" và số tổng theo tháng vào tab "Tổng hợp" (doPost).
 *
 * Gmail qua Google Sheet (khi không tạo được App Password), docs/DEPLOY.md mục G:
 *   batQuetEmail() chạy một lần: cứ 30 phút chép email Shopee/TikTok/MoMo trong Gmail của bạn vào tab "Email"
 *   tatQuetEmail() tắt việc quét
 *
 * Bot Telegram cho nhóm gia đình (docs/DEPLOY.md mục H; token trong Script properties → TELEGRAM_TOKEN):
 *   batTelegram()    chạy một lần: mỗi phút đọc tin nhắn mới, in mã để gõ "/ketnoi <mã>" trong nhóm
 *   tatTelegram()    tắt bot
 *   doiMaTelegram()  mã /ketnoi mới, quên các nhóm đã kết nối
 *
 * Mỗi môi trường (PRODUCTION, TEST) là một Google Sheet riêng với bản Code.gs riêng: docs/DEPLOY.md.
 */

// Bump when the Mac app needs something new from this script; the app warns when the deployed copy is older
// (phone_inbox.REQUIRED_SCRIPT_VERSION). Promote Code.gs test → production like the app itself.
var SCRIPT_VERSION = 4;  // 3: tab "Email" (quetEmail) and a=emails; 4: Telegram bot, columns Kênh/Trạng thái

var SHEET = 'Hộp thư đến';
var HEADERS = ['Mã', 'Thời gian', 'Số tiền', 'Mô tả', 'Trả bằng', 'Người nhập', 'Hạng mục', 'Kênh', 'Trạng thái'];  // add columns at the end only
var props = PropertiesService.getScriptProperties();

function caiDat() {
  var ss = SpreadsheetApp.getActiveSpreadsheet() ||
      SpreadsheetApp.create('Thu Chi Gia Đình — Hộp thư đến');
  props.setProperty('SHEET_ID', ss.getId());
  var sh = ss.getSheetByName(SHEET) || ss.insertSheet(SHEET, 0);
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
    sh.getRange('B:B').setNumberFormat('dd/MM/yyyy HH:mm');
    sh.getRange('C:C').setNumberFormat('#,##0');
    sh.setColumnWidth(1, 90);
    sh.setColumnWidth(4, 260);
  }
  if (!props.getProperty('SECRET')) props.setProperty('SECRET', newSecret_());
  Logger.log('Đã tạo sheet "%s" trong: %s', SHEET, ss.getUrl());
  Logger.log('Bước tiếp: Deploy → New deployment → Web app (Execute as: Me, Who has access: Anyone), ' +
      'rồi chạy layMaKetNoi.');
}

function layMaKetNoi() {
  var url = ScriptApp.getService().getUrl();
  if (!props.getProperty('SECRET')) throw new Error('Chưa chạy caiDat.');
  if (!url || !/\/exec$/.test(url)) {
    Logger.log('Chưa thấy bản Deploy dạng Web app. Mã kết nối = địa chỉ Web app (đuôi /exec) + "?k=%s"',
        props.getProperty('SECRET'));
    return;
  }
  Logger.log('Mã kết nối (giữ kín như mật khẩu):\n%s?k=%s', url, props.getProperty('SECRET'));
}

function doiMa() {
  props.setProperty('SECRET', newSecret_());
  Logger.log('Đã đổi mã. Chạy layMaKetNoi rồi dán mã mới vào app Mac và Phím tắt.');
}

function newSecret_() {
  return Utilities.getUuid().replace(/-/g, '').slice(0, 24);
}

// ---------------------------------------------------------------- web app

function doGet(e) {
  var p = (e && e.parameter) || {};
  var action = p.a || '';
  if (!props.getProperty('SECRET') || p.k !== props.getProperty('SECRET')) {
    // The Shortcut shows the body as its notification, so the add reply is plain text.
    return action === 'add' ? text_('✗ Mã kết nối sai. Lấy mã mới trong app trên Mac.')
        : json_({ok: false, error: 'Mã kết nối sai'});
  }
  if (action === 'add') return add_(p);
  if (action === 'list') {
    var l = list_();
    return json_({ok: true, rows: l.rows, cancelled: l.cancelled, name: sheet_().getParent().getName(), version: SCRIPT_VERSION});
  }
  if (action === 'ping') {
    var ss = sheet_().getParent();
    return json_({ok: true, sheet: ss.getUrl(), name: ss.getName(), version: SCRIPT_VERSION});
  }
  if (action === 'emails') return json_(emails_(String(p.since || '')));
  return json_({ok: false, error: 'Thiếu tham số a'});
}

function add_(p) {
  var amount = parseShortcutAmount(p.so);
  if (!(amount > 0)) return text_('✗ Số tiền "' + (p.so || '') + '" chưa đúng. Gõ đủ số, ví dụ 45000.');
  if (amount < 1000) return text_('✗ ' + vnd_(amount) + ' quá nhỏ — gõ đủ các số 0, ví dụ 45000 cho 45.000 ₫.');
  if (amount >= 1e10) return text_('✗ ' + vnd_(amount) + ' quá lớn — kiểm tra lại số 0.');
  var desc = String(p.d || '').trim().slice(0, 300);
  appendInbox_([newId_(), new Date(), amount, desc, String(p.t || '').trim(), String(p.n || '').trim(),
                String(p.c || '').trim(), 'iphone', '']);
  return text_('✓ Đã ghi ' + vnd_(amount) + (desc ? ' · ' + desc : '') + (p.c ? ' · ' + String(p.c).trim() : ''));
}

function appendInbox_(row) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var sh = sheet_();
    if (!props.getProperty('ID_AS_TEXT')) {  // an all-digit or "12e45678" id would otherwise turn into a number
      sh.getRange('A:A').setNumberFormat('@');
      props.setProperty('ID_AS_TEXT', '1');
    }
    ensureHeaders_(sh);
    sh.appendRow(row);
  } finally {
    lock.releaseLock();
  }
}

/**
 * Every row as an object; rows typed straight into the sheet get an id and a time so the Mac can dedup them.
 * Rows marked "huỷ" are left out (app 1.4.0 never imports them) and listed in `cancelled` for the newer app.
 */
function list_() {
  var sh = sheet_();
  var n = sh.getLastRow() - 1;
  var now = now_();  // also the time given to rows typed without one, so they never count as newer than this read
  props.setProperty('LAST_LIST', stamp_(now, sh.getParent().getSpreadsheetTimeZone()));
  if (n < 1) return {rows: [], cancelled: []};
  var range = sh.getRange(2, 1, n, HEADERS.length);
  var values = range.getValues();
  var tz = sh.getParent().getSpreadsheetTimeZone();
  var changed = false;
  var rows = [], cancelled = [];
  for (var i = 0; i < values.length; i++) {
    var v = values[i];
    if (v[2] === '' && v[3] === '') continue;  // blank line
    if (!v[0]) { v[0] = newId_(); changed = true; }
    if (!(v[1] instanceof Date)) {
      var typed = parseDate(v[1]);
      if (!typed) { v[1] = now; changed = true; }
    }
    if (isCancelled_(v[8])) { cancelled.push(String(v[0])); continue; }
    var when = v[1] instanceof Date ? Utilities.formatDate(v[1], tz, "yyyy-MM-dd'T'HH:mm:ss") : parseDate(v[1]);
    rows.push({id: String(v[0]), time: when, amount: parseAmount(v[2]), description: String(v[3]).trim(),
               account: String(v[4]).trim(), by: String(v[5]).trim(), category: String(v[6]).trim(),
               channel: String(v[7]).trim(), row: i + 2});
  }
  if (changed) range.setValues(values);
  return {rows: rows, cancelled: cancelled};
}

/** "huỷ", "Hủy", "huy", "đã huỷ" typed in Trạng thái all count, so an iPhone row can be cancelled in the sheet too. */
function isCancelled_(v) {
  return /^(da )?huy$/.test(unaccent_(v));
}

/** Sheets made before a column was added get its header, so the person reading the sheet knows what it is. */
function ensureHeaders_(sh) {
  var head = sh.getRange(1, 1, 1, HEADERS.length);
  var have = head.getValues()[0];
  if (HEADERS.some(function (h, i) { return have[i] !== h; })) head.setValues([HEADERS]);
}

function sheet_() {
  var id = props.getProperty('SHEET_ID');
  if (!id) throw new Error('Chưa chạy caiDat.');
  var sh = SpreadsheetApp.openById(id).getSheetByName(SHEET);
  if (!sh) throw new Error('Không thấy sheet "' + SHEET + '". Chạy lại caiDat.');
  return sh;
}

function newId_() {
  return Utilities.getUuid().slice(0, 8);
}

// ---------------------------------------------------------------- Gmail → tab "Email"

var EMAIL_SHEET = 'Email';
var EMAIL_HEADERS = ['Mã thư', 'Ngày', 'Người gửi', 'Tiêu đề', 'Nội dung', 'Ghi chú', 'Message-ID'];
// Change it in Project Settings → Script properties → EMAIL_QUERY.
var EMAIL_QUERY = 'from:(shopee OR tiktok OR momo) newer_than:30d -in:spam -in:trash';
var EMAIL_BODY_MAX = 45000;    // a Sheets cell holds at most 50 000 characters
var EMAIL_KEEP_DAYS = 90;      // older rows are deleted, and never more than EMAIL_KEEP_ROWS
var EMAIL_KEEP_ROWS = 1000;
var EMAIL_PER_RUN = 200;       // the rest waits for the next run: one execution may last 6 minutes
var EMAIL_PAGE = 100;          // a=emails returns at most this many rows…
var EMAIL_PAGE_CHARS = 2000000;  // …or about this much body text, whichever comes first

function batQuetEmail() {
  var have = ScriptApp.getProjectTriggers().filter(function (t) { return t.getHandlerFunction() === 'quetEmail'; });
  if (!have.length) ScriptApp.newTrigger('quetEmail').timeBased().everyMinutes(30).create();
  var n = quetEmail();
  Logger.log('Đã bật quét Gmail mỗi 30 phút. Lần này lưu %s email mới vào tab "%s". Tìm theo: %s',
      n, EMAIL_SHEET, props.getProperty('EMAIL_QUERY') || EMAIL_QUERY);
  Logger.log('Nhớ Deploy → Manage deployments → ✏️ → Version: New version → Deploy để app Mac lấy được email.');
}

function tatQuetEmail() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'quetEmail') ScriptApp.deleteTrigger(t);
  });
  Logger.log('Đã tắt quét Gmail. Các email đã lưu trong tab "%s" vẫn giữ.', EMAIL_SHEET);
}

/** Appends matching Gmail messages not yet in the "Email" tab, oldest first. Returns how many were added. */
function quetEmail() {
  var ss = sheet_().getParent();
  var known = {};
  var existing = ss.getSheetByName(EMAIL_SHEET);
  if (existing) emailIds_(existing).forEach(function (id) { known[id] = true; });
  var query = props.getProperty('EMAIL_QUERY') || EMAIL_QUERY;
  var cutoff = new Date(Date.now() - EMAIL_KEEP_DAYS * 864e5);  // or a wide EMAIL_QUERY re-adds what pruning removed
  var fresh = [];
  for (var start = 0; start < 500; start += 100) {
    var threads = GmailApp.search(query, start, 100);
    threads.forEach(function (t) {
      t.getMessages().forEach(function (m) {
        var id = String(m.getId());
        if (!known[id] && !m.isInTrash() && m.getDate() >= cutoff) { known[id] = true; fresh.push(m); }
      });
    });
    if (threads.length < 100) break;
  }
  fresh.sort(function (a, b) { return a.getDate() - b.getDate(); });
  var rows = fresh.slice(0, EMAIL_PER_RUN).map(emailRow_);
  // Gmail is read without the lock: the iPhone's add_ waits on the same lock, and a scan can take minutes.
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sh = emailSheet_();
    var have = {};
    emailIds_(sh).forEach(function (id) { have[id] = true; });
    rows = rows.filter(function (r) { return !have[r[0]]; });  // a run started by hand meanwhile stored them
    if (rows.length) sh.getRange(sh.getLastRow() + 1, 1, rows.length, EMAIL_HEADERS.length).setValues(rows);
    pruneEmails_(sh);
    props.setProperty('EMAIL_LAST_RUN', Utilities.formatDate(new Date(), ss.getSpreadsheetTimeZone(),
        "yyyy-MM-dd'T'HH:mm:ss"));
  } finally {
    lock.releaseLock();
  }
  return rows.length;
}

function emailRow_(m) {
  var html = m.getBody() || '';
  // Same text the Mac's IMAP path gets (it prefers the HTML part): Gmail's own plain version lays tables out differently.
  var body = /<(html|body|div|table|p|br|td|span)\b/i.test(html) ? htmlToText(html) : '';
  if (!body.trim()) body = String(m.getPlainBody() || '');
  var fwd = String(m.getHeader('X-Forwarded-For') || '').trim();
  var note = fwd ? 'chuyển tiếp từ ' + fwd.split(/\s+/)[0] : /^(fwd?|tt)\s*:/i.test(m.getSubject()) ? 'chuyển tiếp' : '';
  // The RFC Message-ID lets the Mac count an order email without an order number once, whether it came by IMAP or here.
  return [String(m.getId()), m.getDate(), textCell_(m.getFrom()), textCell_(m.getSubject()),
          textCell_(body.slice(0, EMAIL_BODY_MAX)), note, String(m.getHeader('Message-ID') || '').trim()];
}

/** setValues reads a string starting with "=" as a formula even in a plain-text column. */
function textCell_(s) {
  s = String(s === undefined || s === null ? '' : s);
  return s[0] === '=' ? "'" + s : s;
}

function emailSheet_() {
  var ss = sheet_().getParent();
  var sh = ss.getSheetByName(EMAIL_SHEET);
  if (!sh) {
    sh = ss.insertSheet(EMAIL_SHEET);
    sh.appendRow(EMAIL_HEADERS);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, EMAIL_HEADERS.length).setFontWeight('bold');
    sh.getRange('A:A').setNumberFormat('@');  // an all-digit Gmail id would otherwise turn into a rounded number
    sh.getRange('B:B').setNumberFormat('dd/MM/yyyy HH:mm');
    sh.getRange('C:G').setNumberFormat('@');
    sh.setColumnWidth(4, 260);
  }
  return sh;
}

function emailIds_(sh) {
  var n = sh.getLastRow() - 1;
  return n > 0 ? sh.getRange(2, 1, n, 1).getValues().map(function (r) { return String(r[0]); }) : [];
}

function pruneEmails_(sh) {
  var n = sh.getLastRow() - 1;
  if (n < 1) return;
  var cutoff = new Date(Date.now() - EMAIL_KEEP_DAYS * 864e5);
  var dates = sh.getRange(2, 2, n, 1).getValues();
  var old = 0;
  while (old < n && dates[old][0] instanceof Date && dates[old][0] < cutoff) old++;
  var drop = Math.max(old, n - EMAIL_KEEP_ROWS);
  if (drop > 0) sh.deleteRows(2, drop);
}

/** Rows after the one whose id is `since` (from the top if it is empty or was pruned; the Mac skips ids it has). */
function emails_(since) {
  var reply = {ok: true, rows: [], next: since, more: false, scanned: props.getProperty('EMAIL_LAST_RUN') || '',
               version: SCRIPT_VERSION};
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return reply;  // quetEmail is deleting old rows, which shifts row numbers; the Mac asks again later
  try {
    var ss = sheet_().getParent();
    var sh = ss.getSheetByName(EMAIL_SHEET);
    if (!sh) return reply;
    var ids = emailIds_(sh);
    var start = since ? ids.indexOf(since) + 1 : 0;
    var count = Math.min(EMAIL_PAGE, ids.length - start);
    if (count <= 0) return reply;
    var values = sh.getRange(start + 2, 1, count, EMAIL_HEADERS.length).getValues();
    var tz = ss.getSpreadsheetTimeZone();
    var chars = 0, i;
    for (i = 0; i < values.length && (i === 0 || chars < EMAIL_PAGE_CHARS); i++) {
      var v = values[i];
      if (!v[0]) continue;
      var when = v[1] instanceof Date ? Utilities.formatDate(v[1], tz, "yyyy-MM-dd'T'HH:mm:ss") : String(v[1]);
      chars += String(v[4]).length;
      reply.rows.push({id: String(v[0]), date: when, from: String(v[2]), subject: String(v[3]), body: String(v[4]),
                       note: String(v[5]), mid: String(v[6]), row: start + i + 2});
      reply.next = String(v[0]);
    }
    reply.more = start + i < ids.length;
    reply.total = ids.length;
    return reply;
  } finally {
    lock.releaseLock();
  }
}

// ---------------------------------------------------------------- mirror from the Mac app

var TX_SHEET = 'Giao dịch';
var TX_HEADERS = ['Ngày', 'Loại', 'Số tiền', 'Mô tả', 'Hạng mục', 'Trả bằng', 'Nguồn', 'Tính vào tổng', 'Máy', 'Mã'];
var SUM_SHEET = 'Tổng hợp';
var SUM_HEADERS = ['Máy', 'Tháng', 'Nhóm', 'Tên', 'Số tiền', '% tổng chi'];

/** Body {a: "mirror", device, rows, summary}: replaces that Mac's rows in both tabs, leaves other Macs' rows alone. */
function doPost(e) {
  var p = (e && e.parameter) || {};
  if (!props.getProperty('SECRET') || p.k !== props.getProperty('SECRET')) return json_({ok: false, error: 'Mã kết nối sai'});
  var body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return json_({ok: false, error: 'Dữ liệu gửi lên không đọc được'});
  }
  if (body.a !== 'mirror') return json_({ok: false, error: 'Thiếu tham số a'});
  var device = String(body.device || '').trim();
  if (!device) return json_({ok: false, error: 'Thiếu tên máy'});
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var ss = sheet_().getParent();
    replaceRows_(ss, TX_SHEET, TX_HEADERS, 8, device, body.rows || [], 0, {A: 'dd/MM/yyyy', C: '#,##0'});
    replaceRows_(ss, SUM_SHEET, SUM_HEADERS, 0, device, body.summary || [], 1, {B: '@', E: '#,##0', F: '0.0%'});
    // The bot's reports add inbox rows newer than `listed`: the Mac's last a=list, so its mirror holds everything older.
    var tz = ss.getSpreadsheetTimeZone();
    var pushes = jsonProp_('MIRROR_PUSHES', {});
    pushes[device] = {at: stamp_(now_(), tz), listed: props.getProperty('LAST_LIST') || ''};
    setJson_('MIRROR_PUSHES', pushes);
    props.setProperty('SHEET_TZ', tz);
  } finally {
    lock.releaseLock();
  }
  return json_({ok: true, rows: (body.rows || []).length, summary: (body.summary || []).length});
}

function replaceRows_(ss, name, headers, deviceCol, device, rows, sortCol, formats) {
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sh.getLastRow() === 0) {
    sh.appendRow(headers);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, headers.length).setFontWeight('bold');
  }
  for (var col in formats) sh.getRange(col + ':' + col).setNumberFormat(formats[col]);  // '@' keeps "2026-11" as text
  var n = sh.getLastRow() - 1;
  var keep = n > 0 ? sh.getRange(2, 1, n, headers.length).getValues().filter(function (r) {
    return String(r[deviceCol]) !== device;
  }) : [];
  var mine = rows.map(function (r) {
    return headers.map(function (_, i) { return r[i] === undefined || r[i] === null ? '' : r[i]; });
  });
  var all = keep.concat(mine);
  var key = function (v) { return v instanceof Date ? Utilities.formatDate(v, 'UTC', 'yyyy-MM-dd') : String(v); };
  all.sort(function (a, b) { var x = key(a[sortCol]), y = key(b[sortCol]); return x < y ? 1 : x > y ? -1 : 0; });
  if (n > 0) sh.getRange(2, 1, n, headers.length).clearContent();
  if (all.length) sh.getRange(2, 1, all.length, headers.length).setValues(all);
}

// ---------------------------------------------------------------- Telegram bot for the family group

// Same names, icons and order as db.DEFAULT_CATEGORIES (a test compares them); income last, as on the iPhone.
var CATS = [['🎓', 'Học phí', 'expense'], ['💡', 'Điện nước', 'expense'], ['📶', 'Internet & điện thoại', 'expense'],
            ['💄', 'Mỹ phẩm & làm đẹp', 'expense'], ['🛒', 'Ăn uống & đi chợ', 'expense'], ['🏠', 'Đồ gia dụng', 'expense'],
            ['👗', 'Quần áo & giày dép', 'expense'], ['🍼', 'Mẹ & bé', 'expense'], ['💊', 'Sức khoẻ & thuốc', 'expense'],
            ['🚗', 'Đi lại & xăng xe', 'expense'], ['🎬', 'Giải trí & du lịch', 'expense'],
            ['📱', 'Điện tử & phụ kiện', 'expense'], ['📦', 'Khác', 'expense'], ['💼', 'Lương', 'income'],
            ['💰', 'Thu nhập khác', 'income']];
var AUTO = '✨ Tự động';  // not a category name: the Mac falls back to its keywords, as for the iPhone Shortcut
var WAITING = 'Chưa phân loại (chờ Mac)';
var ACCOUNTS = ['Tiền mặt', 'Thẻ Visa', 'Chuyển khoản', 'Ví MoMo'];  // phone/make_shortcut.py ACCOUNTS
var PAY_WORDS = {'tm': 'Tiền mặt', 'tien mat': 'Tiền mặt', 'ck': 'Chuyển khoản', 'chuyen khoan': 'Chuyển khoản',
                 'visa': 'Thẻ Visa', 'the': 'Thẻ Visa', 'the visa': 'Thẻ Visa', 'momo': 'Ví MoMo', 'vi momo': 'Ví MoMo'};
var TG_PENDING_SECONDS = 21600;  // CacheService keeps at most 6 hours
var TG_UNDO_MS = 24 * 3600e3;    // /huy reaches back this far
var TG_PAIR_TRIES = 10;          // wrong /ketnoi codes accepted per day, across all chats

function batTelegram() {
  if (!props.getProperty('TELEGRAM_TOKEN')) {
    throw new Error('Chưa có token. Project Settings (⚙️) → Script properties → Add script property: ' +
        'TELEGRAM_TOKEN = token @BotFather đưa (dạng 123456789:AA…), Save, rồi chạy lại batTelegram.');
  }
  var me = tg_('getMe', {});
  if (!me.ok) throw new Error('Telegram không nhận token: ' + (me.description || 'không rõ') + '. Kiểm tra TELEGRAM_TOKEN.');
  setJson_('TG_BOT', {id: me.result.id, username: me.result.username});
  tg_('deleteWebhook', {});  // getUpdates answers 409 while a webhook is set
  var have = ScriptApp.getProjectTriggers().filter(function (t) { return t.getHandlerFunction() === 'pollTelegram'; });
  if (!have.length) ScriptApp.newTrigger('pollTelegram').timeBased().everyMinutes(1).create();
  if (!props.getProperty('TG_PAIR_CODE')) props.setProperty('TG_PAIR_CODE', newPairCode_());
  props.setProperty('SHEET_TZ', sheet_().getParent().getSpreadsheetTimeZone());
  Logger.log('Bot @%s đang chạy (đọc tin nhắn mỗi phút). Trong nhóm gia đình gõ: /ketnoi %s',
      me.result.username, props.getProperty('TG_PAIR_CODE'));
  if (!me.result.can_read_all_group_messages) {
    Logger.log('⚠️ Bot còn bật privacy mode nên trong nhóm chỉ thấy lệnh /…, không thấy "45k phở". @BotFather → ' +
        '/setprivacy → chọn bot → Disable, rồi xoá bot khỏi nhóm và thêm lại.');
  }
  Logger.log('Nhớ Deploy → Manage deployments → ✏️ → Version: New version → Deploy (app Mac cần a=list mới).');
}

function tatTelegram() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'pollTelegram') ScriptApp.deleteTrigger(t);
  });
  Logger.log('Đã tắt bot Telegram. Các khoản đã ghi vẫn ở tab "%s". Bật lại: batTelegram.', SHEET);
}

function doiMaTelegram() {
  props.setProperty('TG_PAIR_CODE', newPairCode_());
  setJson_('TG_CHATS', []);
  Logger.log('Mã mới: trong nhóm gia đình gõ /ketnoi %s. Các nhóm kết nối trước đây không dùng được nữa.',
      props.getProperty('TG_PAIR_CODE'));
}

function newPairCode_() {
  return ('00000' + parseInt(Utilities.getUuid().replace(/-/g, '').slice(0, 12), 16) % 1000000).slice(-6);
}

/** The minute trigger: reads new messages and button taps, then sends the weekly/monthly report when due. Never throws. */
function pollTelegram() {
  var lock;
  try {
    // A user lock, not the script lock: holding that through Telegram calls would make the iPhone's add_ wait.
    lock = LockService.getUserLock();
    if (!lock.tryLock(0)) return;
  } catch (e) {
    return;
  }
  try {
    if (!props.getProperty('TELEGRAM_TOKEN')) return;
    var r = tg_('getUpdates', {offset: Number(props.getProperty('TG_OFFSET') || 0), timeout: 0,
                               allowed_updates: ['message', 'callback_query']});
    if (r.ok && r.result) {
      r.result.forEach(function (u) {
        try {
          handleUpdate_(u);
        } catch (e) {
          logError_(e);
        }
        props.setProperty('TG_OFFSET', String(u.update_id + 1));  // one bad update must not block the rest forever
      });
    } else if (r.error_code === 409) {
      tg_('deleteWebhook', {});
    }
    sendScheduled_();
  } catch (e) {
    logError_(e);
  } finally {
    lock.releaseLock();
  }
}

function handleUpdate_(u) {
  if (u.callback_query) return onButton_(u.callback_query);
  var m = u.message;
  if (!m || !m.chat || !m.from || m.from.is_bot) return;
  if (m.migrate_to_chat_id) return migrateChat_(m.chat.id, m.migrate_to_chat_id);  // a group became a supergroup
  var text = String(m.text || '').trim();
  if (!text) return;
  var cmd = command_(text);
  if (cmd && cmd.other) return;  // "/thang@SomeOtherBot"
  if (cmd && cmd.name === 'ketnoi') return pair_(m, cmd.arg);
  var chat = chat_(m.chat.id);
  if (!chat) return stranger_(m.chat.id);
  if (cmd) return onCommand_(m, chat, cmd);
  if (!chat.text) { chat.text = true; saveChat_(chat); }  // privacy mode is off: /huongdan stops warning
  onText_(m, text);
}

/** "/thang@FamilyBot 10" → {name: 'thang', arg: '10'}; {other: true} when addressed to another bot. */
function command_(text) {
  var m = text.match(/^\/([a-z_]+)(?:@(\w+))?(?:\s+([\s\S]*))?$/i);
  if (!m) return null;
  var bot = jsonProp_('TG_BOT', {});
  if (m[2] && bot.username && m[2].toLowerCase() !== String(bot.username).toLowerCase()) return {other: true};
  return {name: m[1].toLowerCase(), arg: String(m[3] || '').trim()};
}

function onCommand_(m, chat, cmd) {
  var today = today_();
  switch (cmd.name) {
    case 'start': case 'huongdan': case 'help': return reply_(m, guide_(chat));
    case 'homnay': return reply_(m, report_('📅 Hôm nay ' + dm_(today), today, today));
    case 'tuan': return reply_(m, report_('📅 Tuần này (' + dm_(monday_(today)) + ' – ' + dm_(today) + ')',
        monday_(today), today));
    case 'thang':
      var month = monthArg_(cmd.arg, today);
      if (!month) return reply_(m, 'Gõ /thang hoặc /thang 10 (tháng 10), /thang 10/2026.');
      return reply_(m, report_('📅 Tháng ' + monthLabel_(month), month + '-01', month + '-31'));
    case 'ngansach': return reply_(m, budgetReport_(today.slice(0, 7)));
    case 'ongheo': return reply_(m, piggyReport_());
    case 'huy': return undoLast_(m);
  }
}

function guide_(chat) {
  var lines = ['📒 Ghi khoản chi: gõ số tiền, nội dung, rồi cách trả nếu muốn',
    '  45k phở', '  45.000 phở tm', '  1tr5 học phí ck', '  120000 cà phê visa',
    'Cách trả: tm (tiền mặt), ck (chuyển khoản), visa hoặc thẻ, momo. Không gõ thì bot hỏi.',
    'Bot hỏi hạng mục bằng nút; 💼 Lương, 💰 Thu nhập khác ghi thành khoản thu. Gõ đủ số: "45" thì bot hỏi lại.',
    '↩️ Bấm Huỷ dưới tin "Đã ghi", hoặc /huy để huỷ khoản bạn ghi gần nhất (trong 24 giờ).',
    '', '📊 Báo cáo: /homnay  /tuan  /thang (hoặc /thang 10)  /ngansach  /ongheo',
    'Số liệu tính tới lần app trên Mac đồng bộ gần nhất, cộng các khoản ghi qua Telegram/iPhone sau đó.',
    'Tối Chủ nhật 20:00 có báo cáo tuần; ngày 1 lúc 8:00 có báo cáo tháng trước.',
    'Bot trả lời chậm tối đa khoảng 1 phút.'];
  if (chat.type === 'group' || chat.type === 'supergroup') {
    var me = tg_('getMe', {});
    if ((me.ok && !me.result.can_read_all_group_messages) || !chat.text) {
      lines.push('', '⚠️ Bot chưa thấy tin nhắn thường nào trong nhóm này. Gõ "45k phở" mà bot im lặng là privacy mode ' +
          'còn bật: @BotFather → /setprivacy → chọn bot → Disable, rồi xoá bot khỏi nhóm và thêm lại.');
    }
  }
  return lines.join('\n');
}

// ---- pairing

function chats_() {
  return jsonProp_('TG_CHATS', []);
}

function chat_(id) {
  return chats_().filter(function (c) { return String(c.id) === String(id); })[0] || null;
}

function saveChat_(chat) {
  setJson_('TG_CHATS', chats_().map(function (c) { return String(c.id) === String(chat.id) ? chat : c; }));
}

function migrateChat_(from, to) {
  var chat = chat_(from);
  if (!chat) return;
  chat.id = to;
  setJson_('TG_CHATS', chats_().filter(function (c) { return String(c.id) !== String(from); }).concat([chat]));
}

function pair_(m, arg) {
  if (chat_(m.chat.id)) return reply_(m, 'Cuộc trò chuyện này đã kết nối rồi. /huongdan để xem cách dùng.');
  var today = today_();
  var fails = jsonProp_('TG_PAIR_FAILS', {});
  if (fails.day !== today) fails = {day: today, n: 0};
  if (fails.n >= TG_PAIR_TRIES) return;  // someone is guessing: stay silent until tomorrow
  var code = props.getProperty('TG_PAIR_CODE');
  if (!code || arg.replace(/\s+/g, '') !== code) {
    fails.n++;
    setJson_('TG_PAIR_FAILS', fails);
    return reply_(m, '✗ Mã không đúng. Mã 6 số in trong Apps Script khi chạy batTelegram.');
  }
  var group = m.chat.type === 'group' || m.chat.type === 'supergroup';
  setJson_('TG_CHATS', chats_().concat([{id: m.chat.id, type: m.chat.type, title: m.chat.title || m.from.first_name || ''}]));
  reply_(m, '✓ Đã kết nối ' + (group ? 'nhóm "' + (m.chat.title || '') + '"' : 'cuộc trò chuyện này') +
      '. Thử gõ: 45k phở\n/huongdan để xem cách dùng.');
}

/** Unpaired chats get one polite line a day and nothing else. */
function stranger_(chatId) {
  var today = today_();
  var seen = jsonProp_('TG_STRANGERS', {});
  if (seen[chatId] === today) return;
  for (var k in seen) if (seen[k] !== today) delete seen[k];
  seen[chatId] = today;
  setJson_('TG_STRANGERS', seen);
  send_(chatId, 'Bot riêng của gia đình, chưa kết nối với cuộc trò chuyện này. Người nhà thì gõ /ketnoi <mã 6 số> ' +
      '(mã in trong Apps Script khi chạy batTelegram).');
}

// ---- recording an entry

/** "45k phở tm" → {amount: 45000, desc: 'Phở', account: 'Tiền mặt'}; "45 phở" → {small: 45, …}; null if no amount. */
function parseEntry_(text) {
  var words = String(text || '').trim().split(/\s+/);
  var raw = words.shift() || '';
  if (!/^\d/.test(raw)) return null;
  if (words.length && /^\d+([.,]\d+)?$/.test(raw) && /^(k|nghìn|nghin|ngàn|ngan|tr|triệu|trieu)$/i.test(words[0])) {
    raw += words.shift();  // "2 triệu"
  }
  var account = '';
  [2, 1].some(function (n) {  // "tiền mặt" before "mặt"
    var tail = words.length >= n ? unaccent_(words.slice(-n).join(' ')) : '';
    if (!PAY_WORDS[tail]) return false;
    account = PAY_WORDS[tail];
    words = words.slice(0, -n);
    return true;
  });
  var desc = words.join(' ').replace(/^[-–:·,.\s]+/, '').slice(0, 300);
  desc = desc.charAt(0).toUpperCase() + desc.slice(1);
  if (/^\d{1,3}$/.test(raw)) {  // "45" could mean 45.000 ₫ or a typo: ask, never guess
    return +raw > 0 ? {small: +raw, desc: desc, account: account} : null;
  }
  var amount = parseShortcutAmount(raw);
  if (!(amount > 0)) return null;
  return {amount: amount, desc: desc, account: account, tooBig: amount >= 1e10};
}

function onText_(m, text) {
  var bot = jsonProp_('TG_BOT', {});
  if (bot.username) text = text.replace(new RegExp('@' + bot.username, 'ig'), ' ').trim();
  var e = parseEntry_(text);
  if (!e) {
    if (addressed_(m, bot)) reply_(m, 'Gõ số tiền rồi nội dung, ví dụ: 45k phở tm. /huongdan để xem thêm.');
    return;
  }
  if (e.tooBig) return reply_(m, '✗ ' + vnd_(e.amount) + ' quá lớn — kiểm tra lại số 0.');
  var p = {a: e.amount || e.small, d: e.desc, t: e.account, small: !!e.small, by: m.from.first_name || '',
           uid: m.from.id};
  var key = String(m.message_id);
  putPending_(m.chat.id, key, p);
  var ask = step_(p, key);
  send_(m.chat.id, ask.text, ask.keyboard, m.message_id);
}

function addressed_(m, bot) {
  if (m.chat.type === 'private') return true;
  var r = m.reply_to_message;
  if (r && r.from && bot.id && r.from.id === bot.id) return true;
  return !!bot.username && String(m.text || '').toLowerCase().indexOf('@' + String(bot.username).toLowerCase()) >= 0;
}

/** The next question for a pending entry: the amount (small number), the category, then how it was paid. */
function step_(p, key) {
  if (p.small) {
    return {text: 'Ý bạn là ' + vnd_(p.a * 1000) + '? Lần sau gõ đủ số, ví dụ ' + p.a + 'k.',
            keyboard: [[button_(vnd_(p.a * 1000), 'k|' + key), button_('Huỷ', 'x|' + key)]]};
  }
  if (p.c === undefined) {
    var all = [button_(AUTO, 'c|' + key + '|a')].concat(CATS.map(function (c, i) {
      return button_(c[0] + ' ' + c[1], 'c|' + key + '|' + i);
    }));
    return {text: summary_(p) + ' — hạng mục?', keyboard: rows_(all, 2).concat([[button_('✖️ Huỷ', 'x|' + key)]])};
  }
  var income = p.c !== 'a' && CATS[p.c][2] === 'income';
  return {text: summary_(p) + (income ? ' — nhận vào đâu?' : ' — trả bằng gì?'),
          keyboard: rows_(ACCOUNTS.map(function (a, i) { return button_(payIcon_(a) + ' ' + a, 'p|' + key + '|' + i); }), 2)
              .concat([[button_('✖️ Huỷ', 'x|' + key)]])};
}

function summary_(p) {
  var parts = [vnd_(p.a)];
  if (p.d) parts.push(p.d);
  if (p.c !== undefined) parts.push(catLabel_(p.c));
  if (p.t) parts.push(p.t);
  return parts.join(' · ');
}

function catLabel_(c) {
  return c === 'a' ? AUTO : CATS[c][0] + ' ' + CATS[c][1];
}

function onButton_(q) {
  var chatId = q.message && q.message.chat && q.message.chat.id;
  var msgId = q.message && q.message.message_id;
  if (!chat_(chatId)) return answer_(q, '');
  var part = String(q.data || '').split('|');
  if (part[0] === 'u') return undoButton_(q, chatId, msgId, part[1]);
  var key = part[1];
  var p = getPending_(chatId, key);
  if (!p) return answer_(q, 'Khoản này đã ghi, đã huỷ hoặc quá 6 giờ. Chưa ghi thì gõ lại.');
  if (part[0] === 'x') {
    dropPending_(chatId, key);
    edit_(chatId, msgId, '✖️ Bỏ qua: ' + summary_(p));
    return answer_(q, 'Đã bỏ qua');
  }
  if (part[0] === 'k' && p.small) { p.a *= 1000; p.small = false; }
  if (part[0] === 'c' && !p.small) p.c = part[2] === 'a' ? 'a' : Math.min(Math.max(+part[2] || 0, 0), CATS.length - 1);
  if (part[0] === 'p' && !p.small) p.t = ACCOUNTS[+part[2]] || ACCOUNTS[0];
  if (p.small || p.c === undefined || !p.t) {
    putPending_(chatId, key, p);
    var ask = step_(p, key);
    edit_(chatId, msgId, ask.text, ask.keyboard);
    return answer_(q, '');
  }
  record_(q, chatId, msgId, key, p);
}

function record_(q, chatId, msgId, key, p) {
  var id = newId_();
  appendInbox_([id, now_(), p.a, p.d, p.t, 'Telegram · ' + p.by, catLabel_(p.c), 'telegram', '']);
  dropPending_(chatId, key);
  var income = p.c !== 'a' && CATS[p.c][2] === 'income';
  var done = '✓ Đã ghi ' + (income ? 'khoản thu ' : '') + summary_(p) + (p.by ? ' — ' + p.by : '');
  setJson_('TG_LAST_' + p.uid, {id: id, at: Date.now(), chat: chatId, msg: msgId, text: summary_(p)});
  var warning = !income && p.c !== 'a' ? budgetWarning_(CATS[p.c][1]) : '';
  edit_(chatId, msgId, done + (warning ? '\n' + warning : ''), [[button_('↩️ Huỷ', 'u|' + id)]]);
  answer_(q, 'Đã ghi');
}

/** Anyone in a paired chat may undo an entry from its button: it is the family's shared book, and the reply says who. */
function undoButton_(q, chatId, msgId, id) {
  var r = cancelRow_(id);
  if (r === 'missing') return answer_(q, 'Không thấy dòng này trong sheet (đã xoá?).');
  if (r === 'already') return answer_(q, 'Khoản này đã huỷ rồi.');
  var text = String(q.message.text || '').split('\n')[0].replace(/^✓ Đã ghi /, '');
  edit_(chatId, msgId, '↩️ Đã huỷ: ' + text + (q.from && q.from.first_name ? ' (' + q.from.first_name + ' huỷ)' : ''));
  answer_(q, 'Đã huỷ');
}

function undoLast_(m) {
  var last = jsonProp_('TG_LAST_' + m.from.id, null);
  if (!last || Date.now() - last.at > TG_UNDO_MS) return reply_(m, 'Không có khoản nào bạn ghi trong 24 giờ qua.');
  var r = cancelRow_(last.id);
  if (r === 'missing') return reply_(m, 'Không thấy khoản ' + last.text + ' trong sheet (đã xoá?).');
  if (r === 'already') return reply_(m, 'Khoản gần nhất của bạn (' + last.text + ') đã huỷ rồi.');
  if (last.chat && last.msg) edit_(last.chat, last.msg, '↩️ Đã huỷ: ' + last.text + ' (/huy)');
  reply_(m, '↩️ Đã huỷ ' + last.text);
}

/** Marks the row "huỷ" in Trạng thái. Returns ok | already | missing. */
function cancelRow_(id) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var sh = sheet_();
    var n = sh.getLastRow() - 1;
    var ids = n > 0 ? sh.getRange(2, 1, n, 1).getValues() : [];
    for (var i = 0; i < ids.length; i++) {
      if (String(ids[i][0]) !== String(id)) continue;
      var cell = sh.getRange(i + 2, HEADERS.length, 1, 1);
      if (isCancelled_(cell.getValues()[0][0])) return 'already';
      ensureHeaders_(sh);
      cell.setValues([['huỷ']]);
      return 'ok';
    }
    return 'missing';
  } finally {
    lock.releaseLock();
  }
}

function putPending_(chatId, key, p) {
  CacheService.getScriptCache().put('tg:' + chatId + ':' + key, JSON.stringify(p), TG_PENDING_SECONDS);
}

function getPending_(chatId, key) {
  var v = CacheService.getScriptCache().get('tg:' + chatId + ':' + key);
  return v ? JSON.parse(v) : null;
}

function dropPending_(chatId, key) {
  CacheService.getScriptCache().remove('tg:' + chatId + ':' + key);
}

// ---- reports

/**
 * Entries for the reports: the "Giao dịch" mirror of the Mac that pushed last, plus inbox rows it had not read yet.
 * Other Macs' mirror rows are ignored; they would count iPhone and Telegram entries twice.
 */
function ledger_() {
  var ss = sheet_().getParent();
  var tz = ss.getSpreadsheetTimeZone();
  var last = lastPush_(), device = last.device;
  var out = {device: device, at: last.at, entries: []};
  var tx = ss.getSheetByName(TX_SHEET);
  if (device && tx && tx.getLastRow() > 1) {
    tx.getRange(2, 1, tx.getLastRow() - 1, TX_HEADERS.length).getValues().forEach(function (r) {
      if (String(r[8]) !== device || String(r[7]) !== 'Có') return;
      out.entries.push({day: day_(r[0], tz), kind: r[1] === 'Thu' ? 'income' : 'expense', amount: Number(r[2]) || 0,
                        cat: String(r[4] || 'Chưa phân loại'), pay: String(r[5] || ''), late: false});
    });
  }
  var cutoff = last.listed && last.listed <= last.at ? last.listed : last.at;
  var sh = sheet_();
  var n = sh.getLastRow() - 1;
  var rows = n > 0 ? sh.getRange(2, 1, n, HEADERS.length).getValues() : [];
  rows.forEach(function (v) {
    var amount = parseAmount(v[2]);
    if (!(amount > 0) || isCancelled_(v[8])) return;
    var when = v[1] instanceof Date ? stamp_(v[1], tz) : parseDate(v[1]);
    if (!when || when <= cutoff) return;  // already in the Mac's mirror
    var name = String(v[6]).replace(/^[^\wÀ-ỹ]+/, '').trim();
    var cat = catByName_(name);
    out.entries.push({day: when.slice(0, 10), kind: cat && cat[2] === 'income' ? 'income' : 'expense', amount: amount,
                      cat: cat ? cat[1] : !name || unaccent_(name) === 'tu dong' ? WAITING : name,
                      pay: String(v[4]).trim(), late: true});
  });
  return out;
}

/** The Mac that pushed its mirror last: {device, at, listed}, all '' before any push since Code.gs 4. */
function lastPush_() {
  var pushes = jsonProp_('MIRROR_PUSHES', {});
  var last = {device: '', at: '', listed: ''};
  for (var d in pushes) {
    if (pushes[d].at > last.at) last = {device: d, at: pushes[d].at, listed: pushes[d].listed || ''};
  }
  return last;
}

function catByName_(name) {
  var k = unaccent_(name);
  return CATS.filter(function (c) { return unaccent_(c[1]) === k; })[0] || null;
}

function catIcon_(name) {
  var c = catByName_(name);
  return c ? c[0] : name === WAITING ? '⏳' : name === 'Chưa phân loại' ? '❔' : '▫️';
}

function freshness_(L, entries) {
  var late = entries.filter(function (e) { return e.late; }).length;
  if (!L.at) {
    return 'Chưa có số liệu từ Mac: mở app trên Mac (đã bật Bản sao trên Google Sheet) để gửi. Đang chỉ tính ' + late +
        ' khoản ghi qua Telegram/iPhone.';
  }
  return 'Số liệu tới lần Mac đồng bộ ' + dmhm_(L.at) + (late ? ' + ' + late + ' khoản ghi sau đó' : '');
}

function report_(title, from, to) {
  var L = ledger_();
  var xs = L.entries.filter(function (e) { return e.day >= from && e.day <= to; });
  var income = 0, expense = 0, nIn = 0, nOut = 0, cats = {}, pays = {};
  xs.forEach(function (e) {
    if (e.kind === 'income') { income += e.amount; nIn++; return; }
    expense += e.amount; nOut++;
    cats[e.cat] = (cats[e.cat] || 0) + e.amount;
    var pay = e.pay || 'Chưa ghi cách trả';
    pays[pay] = (pays[pay] || 0) + e.amount;
  });
  var lines = [title];
  if (!xs.length) {
    lines.push('Chưa có khoản nào.');
  } else {
    lines.push('💸 Chi ' + vnd_(expense) + ' · 💰 Thu ' + vnd_(income), '📌 Còn lại ' + signed_(income - expense));
    var top = sorted_(cats);
    if (top.length) {
      lines.push('', 'Theo hạng mục:');
      top.slice(0, 6).forEach(function (c) {
        lines.push(catIcon_(c[0]) + ' ' + c[0] + ': ' + short_(c[1]) + ' (' + pct_(c[1], expense) + ')');
      });
      if (top.length > 6) {
        var rest = top.slice(6).reduce(function (s, c) { return s + c[1]; }, 0);
        lines.push('… và ' + (top.length - 6) + ' mục khác: ' + short_(rest) + ' (' + pct_(rest, expense) + ')');
      }
      lines.push('', 'Theo cách trả: ' + sorted_(pays).map(function (p) {
        return payIcon_(p[0]) + ' ' + p[0] + ' ' + short_(p[1]);
      }).join(' · '));
    }
    lines.push('🧾 ' + nOut + ' khoản chi' + (nIn ? ', ' + nIn + ' khoản thu' : ''));
  }
  lines.push('', freshness_(L, xs));
  return lines.join('\n');
}

/** Budgets the Mac sends in "Tổng hợp" (group "Ngân sách"), from the newest month it sent them for. */
function budgets_(device) {
  var sh = sheet_().getParent().getSheetByName(SUM_SHEET);
  if (!device || !sh || sh.getLastRow() < 2) return {};
  var rows = sh.getRange(2, 1, sh.getLastRow() - 1, SUM_HEADERS.length).getValues().filter(function (r) {
    return String(r[0]) === device && r[2] === 'Ngân sách' && Number(r[4]) > 0;
  });
  var newest = rows.reduce(function (m, r) { return String(r[1]) > m ? String(r[1]) : m; }, '');
  var out = {};
  rows.forEach(function (r) { if (String(r[1]) === newest) out[String(r[3])] = Number(r[4]); });
  return out;
}

function spentBy_(L, month) {
  var spent = {};
  L.entries.forEach(function (e) {
    if (e.kind === 'expense' && e.day.slice(0, 7) === month) spent[unaccent_(e.cat)] = (spent[unaccent_(e.cat)] || 0) + e.amount;
  });
  return spent;
}

function budgetReport_(month) {
  var L = ledger_();
  var budgets = budgets_(L.device);
  var names = Object.keys(budgets);
  if (!names.length) {
    return '🎯 Chưa đặt ngân sách nào (hoặc Mac chưa gửi). Đặt trong app trên Mac: Cài đặt → Hạng mục & ngân sách.\n\n' +
        freshness_(L, []);
  }
  var spent = spentBy_(L, month);
  var lines = ['🎯 Ngân sách tháng ' + monthLabel_(month)];
  names.map(function (n) { return [n, spent[unaccent_(n)] || 0, budgets[n]]; })
      .sort(function (a, b) { return b[1] / b[2] - a[1] / a[2]; })
      .forEach(function (x) {
        var mark = x[1] > x[2] ? ' 🔴' : x[1] * 100 >= x[2] * 80 ? ' ⚠️' : '';
        lines.push(catIcon_(x[0]) + ' ' + x[0] + ': ' + short_(x[1]) + ' / ' + short_(x[2]) + ' (' +
            Math.floor(x[1] * 100 / x[2]) + '%)' + mark);
      });
  lines.push('', freshness_(L, L.entries.filter(function (e) { return e.day.slice(0, 7) === month; })));
  return lines.join('\n');
}

/** After an expense is recorded: one line at 80% and one above 100% of the category's budget, once each a month. */
function budgetWarning_(name) {
  var budgets = budgets_(lastPush_().device);
  var budget = budgets[Object.keys(budgets).filter(function (k) { return unaccent_(k) === unaccent_(name); })[0]];
  if (!budget) return '';  // before reading the ledger: most categories have no budget
  var month = today_().slice(0, 7);
  var spent = spentBy_(ledger_(), month)[unaccent_(name)] || 0;
  var level = spent > budget ? 100 : spent * 100 >= budget * 80 ? 80 : 0;
  if (!level) return '';
  var warned = jsonProp_('TG_WARNED', {});
  if (warned.month !== month) warned = {month: month, keys: {}};
  if (warned.keys[name + ':' + level]) return '';
  warned.keys[name + ':80'] = 1;  // jumping straight past 100% sends only the "over" line
  if (level === 100) warned.keys[name + ':100'] = 1;
  setJson_('TG_WARNED', warned);
  var icon = catIcon_(name);
  if (level === 100) {
    return '🔴 ' + icon + ' ' + name + ' đã vượt ngân sách tháng ' + short_(spent - budget) + ' (' + short_(spent) + ' / ' +
        short_(budget) + ')';
  }
  return '⚠️ ' + icon + ' ' + name + ' đã dùng ' + Math.floor(spent * 100 / budget) + '% ngân sách tháng (' + short_(spent) +
      ' / ' + short_(budget) + ') — còn ' + short_(budget - spent);
}

function piggyReport_() {
  var L = ledger_();
  var sh = sheet_().getParent().getSheetByName(SUM_SHEET);
  var months = !L.device || !sh || sh.getLastRow() < 2 ? [] :
      sh.getRange(2, 1, sh.getLastRow() - 1, SUM_HEADERS.length).getValues().filter(function (r) {
        return String(r[0]) === L.device && r[2] === 'Ống heo';
      }).map(function (r) { return [String(r[1]), Number(r[4]) || 0]; })
        .sort(function (a, b) { return a[0] < b[0] ? 1 : -1; });
  if (!months.length) {
    return '🐷 Ống heo chưa có tháng nào. App trên Mac bỏ phần còn lại (thu − chi) vào ống heo khi hết tháng.\n\n' +
        freshness_(L, []);
  }
  var sum = function (k) { return months.slice(0, k).reduce(function (s, m) { return s + m[1]; }, 0); };
  var latest = months[0];
  return ['🐷 Ống heo',
    '3 tháng gần nhất: ' + signed_(sum(3)), '6 tháng gần nhất: ' + signed_(sum(6)),
    'Tổng ' + months.length + ' tháng: ' + signed_(sum(months.length)),
    'Tháng ' + monthLabel_(latest[0]) + ': ' + (latest[1] >= 0 ? 'bỏ ống heo ' + short_(latest[1])
        : 'chi vượt thu ' + short_(-latest[1])),
    '', freshness_(L, [])].join('\n');
}

/** Weekly report on Sunday from 20:00 and last month's on the 1st from 08:00, each sent once, to every paired chat. */
function sendScheduled_() {
  var chats = chats_();
  if (!chats.length) return;
  var tz = props.getProperty('SHEET_TZ') || sheet_().getParent().getSpreadsheetTimeZone();  // no Sheet open each minute
  var now = now_();
  var today = Utilities.formatDate(now, tz, 'yyyy-MM-dd');
  var hour = Number(Utilities.formatDate(now, tz, 'HH'));
  var text = '';
  if (Utilities.formatDate(now, tz, 'u') === '7' && hour >= 20 && props.getProperty('TG_SENT_WEEK') !== today) {
    props.setProperty('TG_SENT_WEEK', today);  // first: a send that fails must not repeat every minute
    text = report_('📊 Báo cáo tuần ' + dm_(monday_(today)) + ' – ' + dm_(today), monday_(today), today);
  }
  var month = today.slice(0, 7);
  if (today.slice(8) === '01' && hour >= 8 && props.getProperty('TG_SENT_MONTH') !== month) {
    props.setProperty('TG_SENT_MONTH', month);
    var prev = prevMonth_(month);
    text = (text ? text + '\n\n' : '') + report_('📊 Báo cáo tháng ' + monthLabel_(prev), prev + '-01', prev + '-31') +
        '\n\n' + piggyReport_();
  }
  if (text) chats.forEach(function (c) { send_(c.id, text); });
}

// ---- Telegram API

/** POST to the Bot API. Never throws; a network failure comes back as {ok: false, description}. */
function tg_(method, params) {
  var token = String(props.getProperty('TELEGRAM_TOKEN') || '').trim();
  if (!token) return {ok: false, description: 'Chưa có TELEGRAM_TOKEN'};
  try {
    var res = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/' + method, {
      method: 'post', contentType: 'application/json', payload: JSON.stringify(params || {}), muteHttpExceptions: true});
    var body = JSON.parse(res.getContentText());
    return body && typeof body === 'object' ? body : {ok: false, description: 'Telegram trả về dữ liệu lạ'};
  } catch (e) {
    return {ok: false, description: masked_(e)};
  }
}

function send_(chatId, text, keyboard, replyTo) {
  var p = {chat_id: chatId, text: text};
  if (keyboard) p.reply_markup = {inline_keyboard: keyboard};
  if (replyTo) p.reply_parameters = {message_id: replyTo, allow_sending_without_reply: true};
  return tg_('sendMessage', p);
}

function reply_(m, text) {
  return send_(m.chat.id, text, null, m.message_id);
}

function edit_(chatId, msgId, text, keyboard) {
  var p = {chat_id: chatId, message_id: msgId, text: text};
  if (keyboard) p.reply_markup = {inline_keyboard: keyboard};
  return tg_('editMessageText', p);
}

function answer_(q, text) {
  return tg_('answerCallbackQuery', text ? {callback_query_id: q.id, text: text} : {callback_query_id: q.id});
}

function button_(text, data) {
  return {text: text, callback_data: data};
}

function rows_(items, per) {
  var out = [];
  for (var i = 0; i < items.length; i += per) out.push(items.slice(i, i + per));
  return out;
}

/** UrlFetch errors quote the URL, and the URL holds the bot token. */
function masked_(e) {
  var token = String(props.getProperty('TELEGRAM_TOKEN') || '').trim();
  var s = String(e && e.message || e);
  return token ? s.split(token).join('…') : s;
}

function logError_(e) {
  var s = masked_(e);
  Logger.log('Bot Telegram lỗi: %s', s);
  try {
    props.setProperty('TG_LAST_ERROR', new Date(Date.now()).toISOString() + ' ' + s.slice(0, 500));
  } catch (ignored) {
  }
}

// ---- dates and numbers for the bot

function today_() {
  return Utilities.formatDate(now_(), props.getProperty('SHEET_TZ') || sheet_().getParent().getSpreadsheetTimeZone(),
      'yyyy-MM-dd');
}

function day_(v, tz) {
  if (v instanceof Date) return Utilities.formatDate(v, tz, 'yyyy-MM-dd');
  var s = String(v);
  return /^\d{4}-\d\d-\d\d/.test(s) ? s.slice(0, 10) : String(parseDate(s) || '').slice(0, 10);
}

function addDays_(day, n) {
  return new Date(Date.UTC(+day.slice(0, 4), +day.slice(5, 7) - 1, +day.slice(8, 10) + n)).toISOString().slice(0, 10);
}

function monday_(day) {
  var dow = new Date(Date.UTC(+day.slice(0, 4), +day.slice(5, 7) - 1, +day.slice(8, 10))).getUTCDay();
  return addDays_(day, -((dow + 6) % 7));
}

function prevMonth_(month) {
  return addDays_(month + '-01', -1).slice(0, 7);
}

/** "/thang 10" in January means October of last year; "10/2026" and "2026-10" are exact. */
function monthArg_(arg, today) {
  var y = +today.slice(0, 4), mo;
  var s = String(arg || '').trim();
  if (!s) return today.slice(0, 7);
  var m = s.match(/^(\d{1,2})(?:[\/.-](\d{4}))?$/);
  if (m) {
    mo = +m[1];
    if (m[2]) y = +m[2]; else if (mo > +today.slice(5, 7)) y--;
  } else if ((m = s.match(/^(\d{4})-(\d{1,2})$/))) {
    y = +m[1];
    mo = +m[2];
  }
  return mo >= 1 && mo <= 12 ? y + '-' + ('0' + mo).slice(-2) : null;
}

function monthLabel_(month) {
  return +month.slice(5, 7) + '/' + month.slice(0, 4);
}

function dm_(day) {
  return day.slice(8, 10) + '/' + day.slice(5, 7);
}

function dmhm_(stamp) {
  return dm_(stamp) + ' ' + stamp.slice(11, 16);
}

/** Same as `short` in the app: 1700000 → "1,7 tr", 300000 → "300k". */
function short_(n) {
  if (n < 0) return '-' + short_(-n);
  if (n >= 1e9) return (n / 1e9).toFixed(1).replace('.', ',').replace(',0', '') + ' tỷ';
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace('.', ',').replace(',0', '') + ' tr';
  return n >= 1e3 ? Math.round(n / 1e3) + 'k' : String(n);
}

function signed_(n) {
  return n < 0 ? '-' + vnd_(-n) : vnd_(n);
}

function pct_(part, whole) {
  var x = whole ? part * 100 / whole : 0;
  return (x > 0 && x < 10 ? x.toFixed(1).replace('.', ',') : String(Math.round(x))) + '%';
}

function sorted_(map) {
  return Object.keys(map).map(function (k) { return [k, map[k]]; }).sort(function (a, b) { return b[1] - a[1]; });
}

/** Same as payIcon in the app: the label is free text ("Tiền mặt", "Visa Techcombank", "Ví MoMo"…). */
function payIcon_(name) {
  var n = unaccent_(name);
  if (/\b(tien mat|cash)\b/.test(n)) return '💵';
  if (/\b(momo|vi|zalopay|shopeepay|vnpay|viettel ?money)\b/.test(n)) return '👛';
  if (/\b(chuyen khoan|ck|transfer|bank)\b/.test(n)) return '🏦';
  if (n === 'chua ghi cach tra') return '❔';
  return '💳';
}

// ---------------------------------------------------------------- parsing (shared with the tests)

/** From the Shortcut's number pad: the amount as typed, in đồng ("7000000", or "7.000.000" if the phone groups digits). */
function parseShortcutAmount(raw) {
  var s = String(raw === undefined || raw === null ? '' : raw).replace(/\s+/g, '');
  if (/^\d{1,3}([.,]\d{3})+$/.test(s)) s = s.replace(/[.,]/g, '');
  if (/^\d+$/.test(s)) return parseInt(s, 10);
  return parseAmount(raw);  // "45k", "1tr5" if typed as text
}

/** "45" → 45000 (under 1000 means thousands), "45k", "1,5tr", "1tr5", "1.500.000" → VND. NaN if unreadable. */
function parseAmount(raw) {
  if (typeof raw === 'number') return raw > 0 && raw < 1000 ? Math.round(raw * 1000) : Math.round(raw);
  var s = String(raw === undefined || raw === null ? '' : raw).toLowerCase().replace(/\s+/g, '').replace(/(₫|đ|vnd|d)$/, '');
  var m = s.match(/^(\d+)tr(\d{1,3})$/);  // 1tr5 = 1.500.000
  if (m) return parseInt(m[1], 10) * 1e6 + parseInt((m[2] + '00').slice(0, 3), 10) * 1e3;
  m = s.match(/^([\d.,]+)(k|nghin|ngan|nghìn|ngàn|tr|trieu|triệu|m)?$/);
  if (!m) return NaN;
  var unit = {k: 1e3, nghin: 1e3, ngan: 1e3, 'nghìn': 1e3, 'ngàn': 1e3, tr: 1e6, trieu: 1e6, 'triệu': 1e6, m: 1e6}[m[2]];
  var num;
  if (unit) {
    num = parseFloat(m[1].replace(',', '.'));
  } else if (/^\d{1,3}([.,]\d{3})+$/.test(m[1])) {
    num = parseInt(m[1].replace(/[.,]/g, ''), 10);  // thousands separators
  } else if (/^\d+$/.test(m[1])) {
    num = parseInt(m[1], 10);
    if (num < 1000) unit = 1e3;
  } else {
    return NaN;
  }
  return Math.round(num * (unit || 1));
}

/** A date typed by hand: "2/11", "02/11/2026", "2026-11-02" → "YYYY-MM-DDT00:00:00"; null if unreadable. */
function parseDate(raw) {
  var s = String(raw === undefined || raw === null ? '' : raw).trim();
  var m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (m) return iso_(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})[\/.-](\d{1,2})(?:[\/.-](\d{2,4}))?$/);
  if (!m) return null;
  var y = m[3] ? (m[3].length === 2 ? 2000 + +m[3] : +m[3]) : new Date().getFullYear();
  return iso_(y, +m[2], +m[1]);
}

/** Port of parsers.html_to_text on the Mac: block tags become line breaks, style/script/head are dropped. */
function htmlToText(html) {
  var s = String(html || '').replace(/<!--[\s\S]*?-->/g, '')
      .replace(/<(style|script|head)\b[\s\S]*?<\/\1\s*>/gi, '')
      .replace(/<\/?(p|div|tr|br|li|h1|h2|h3|h4|table|td|th)\b[^>]*>/gi, '\n')
      .replace(/<[^>]*>/g, '');
  var named = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: '\u00a0'};
  s = s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, function (all, e) {
    if (e[0] === '#') {
      var c = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return c > 0 && c < 0x110000 ? String.fromCodePoint(c) : all;
    }
    return named[e.toLowerCase()] !== undefined ? named[e.toLowerCase()] : all;
  });
  return s.split(/\r\n|\r|\n/).map(function (ln) { return ln.replace(/[ \t\u00a0]+/g, ' ').trim(); })
      .filter(function (ln) { return ln; }).join('\n');
}

function iso_(y, mo, d) {
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  return y + '-' + ('0' + mo).slice(-2) + '-' + ('0' + d).slice(-2) + 'T00:00:00';
}

function now_() {
  return new Date(Date.now());  // the tests move the clock through Date.now
}

function stamp_(d, tz) {
  return Utilities.formatDate(d, tz, "yyyy-MM-dd'T'HH:mm:ss");
}

function jsonProp_(key, fallback) {
  try {
    var v = props.getProperty(key);
    return v ? JSON.parse(v) : fallback;
  } catch (e) {
    return fallback;
  }
}

function setJson_(key, value) {
  props.setProperty(key, JSON.stringify(value));
}

function unaccent_(s) {
  return String(s === undefined || s === null ? '' : s).normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase().trim();
}

function vnd_(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' ₫';
}

function text_(s) {
  return ContentService.createTextOutput(s).setMimeType(ContentService.MimeType.TEXT);
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
