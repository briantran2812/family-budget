/**
 * Thu Chi Gia Đình — hộp thư đến cho iPhone.
 *
 * Phím tắt "Ghi chi tiêu" trên iPhone gửi từng khoản chi tới đây; script ghi một dòng vào sheet
 * "Hộp thư đến". App trên Mac đọc các dòng đó khi đồng bộ. Cài đặt: phone/README.md.
 *
 *   caiDat()       chạy một lần: tạo sheet và mã bí mật
 *   layMaKetNoi()  sau khi Deploy: in ra mã kết nối để dán vào app Mac và Phím tắt
 *   doiMa()        đổi mã bí mật (mã cũ ngừng hoạt động ngay)
 */

var SHEET = 'Hộp thư đến';
var HEADERS = ['Mã', 'Thời gian', 'Số tiền', 'Mô tả', 'Trả bằng', 'Người nhập'];
var props = PropertiesService.getScriptProperties();

function caiDat() {
  var ss = SpreadsheetApp.getActiveSpreadsheet() ||
      SpreadsheetApp.create('Thu Chi Gia Đình — Hộp thư đến');
  props.setProperty('SHEET_ID', ss.getId());
  var sh = ss.getSheetByName(SHEET) || ss.insertSheet(SHEET, 0);
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
    sh.getRange('A1:F1').setFontWeight('bold');
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
  if (action === 'list') return json_({ok: true, rows: list_()});
  if (action === 'ping') return json_({ok: true, sheet: sheet_().getParent().getUrl()});
  return json_({ok: false, error: 'Thiếu tham số a'});
}

function add_(p) {
  var amount = parseAmount(p.so);
  if (!(amount > 0)) return text_('✗ Số tiền "' + (p.so || '') + '" chưa đúng. Ví dụ: 45 (= 45.000 ₫) hoặc 1500000.');
  var desc = String(p.d || '').trim().slice(0, 300);
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    sheet_().appendRow([newId_(), new Date(), amount, desc, String(p.t || '').trim(), String(p.n || '').trim()]);
  } finally {
    lock.releaseLock();
  }
  return text_('✓ Đã ghi ' + vnd_(amount) + (desc ? ' · ' + desc : ''));
}

/** Every row as an object. Rows typed straight into the sheet get an id and a time so the Mac can dedup them. */
function list_() {
  var sh = sheet_();
  var n = sh.getLastRow() - 1;
  if (n < 1) return [];
  var range = sh.getRange(2, 1, n, HEADERS.length);
  var values = range.getValues();
  var tz = sh.getParent().getSpreadsheetTimeZone();
  var changed = false;
  var rows = [];
  for (var i = 0; i < values.length; i++) {
    var v = values[i];
    if (v[2] === '' && v[3] === '') continue;  // blank line
    if (!v[0]) { v[0] = newId_(); changed = true; }
    if (!(v[1] instanceof Date)) {
      var typed = parseDate(v[1]);
      if (!typed) { v[1] = new Date(); changed = true; }
    }
    var when = v[1] instanceof Date ? Utilities.formatDate(v[1], tz, "yyyy-MM-dd'T'HH:mm:ss") : parseDate(v[1]);
    rows.push({id: String(v[0]), time: when, amount: parseAmount(v[2]), description: String(v[3]).trim(),
               account: String(v[4]).trim(), by: String(v[5]).trim(), row: i + 2});
  }
  if (changed) range.setValues(values);
  return rows;
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

// ---------------------------------------------------------------- parsing (shared with the tests)

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

function iso_(y, mo, d) {
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  return y + '-' + ('0' + mo).slice(-2) + '-' + ('0' + d).slice(-2) + 'T00:00:00';
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
