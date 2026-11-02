// Runs phone/Code.gs against in-memory fakes of the Apps Script services. Invoked by tests/test_apps_script.py.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const SRC = fs.readFileSync(new URL('../../phone/Code.gs', import.meta.url), 'utf8');

function fakeSheet() {
  const rows = [];
  const sheet = {
    rows,
    getLastRow: () => rows.length,
    appendRow: r => rows.push([...r]),
    setFrozenRows() {}, setColumnWidth() {},
    getRange(a, b, n, w) {
      if (typeof a === 'string') return {setFontWeight() {}, setNumberFormat() {}};
      return {
        getValues: () => rows.slice(a - 1, a - 1 + n).map(r => Array.from({length: w}, (_, i) => r[i] ?? '')),
        setValues: vals => vals.forEach((v, i) => { rows[a - 1 + i] = [...v]; }),
      };
    },
    getParent: () => ss,
  };
  const ss = {
    getId: () => 'sheet-1', getUrl: () => 'https://docs.google.com/spreadsheets/d/sheet-1',
    getSheetByName: name => (name === 'Hộp thư đến' && ss.created ? sheet : null),
    insertSheet: () => { ss.created = true; return sheet; },
    getSpreadsheetTimeZone: () => 'Asia/Ho_Chi_Minh',
  };
  return {sheet, ss};
}

function load() {
  const {sheet, ss} = fakeSheet();
  const store = {};
  let uuid = 0;
  const pad = n => String(n).padStart(2, '0');
  const ctx = {
    PropertiesService: {getScriptProperties: () => ({
      getProperty: k => store[k] ?? null, setProperty: (k, v) => { store[k] = v; } })},
    SpreadsheetApp: {getActiveSpreadsheet: () => ss, create: () => ss, openById: () => ss},
    LockService: {getScriptLock: () => ({waitLock() {}, releaseLock() {}})},
    Utilities: {
      getUuid: () => `${String(++uuid).padStart(8, '0')}-aaaa-bbbb-cccc-dddddddddddd`,
      // Fakes run in UTC; the formatted string is what matters.
      formatDate: d => `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:00`,
    },
    ContentService: {MimeType: {TEXT: 'text', JSON: 'json'},
      createTextOutput: s => ({body: s, setMimeType(m) { this.mime = m; return this; }})},
    Logger: {log() {}},
    ScriptApp: {getService: () => ({getUrl: () => 'https://script.google.com/macros/s/X/exec'})},
    Date, JSON, Math, String, parseInt, parseFloat, isNaN,
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  ctx.caiDat();
  return {ctx, sheet, secret: store.SECRET, store};
}

const tests = {
  parse_amount() {
    const {ctx} = load();
    const cases = {'45': 45000, '45k': 45000, '1,5tr': 1500000, '1tr5': 1500000, '1tr25': 1250000,
      '1.500.000': 1500000, '1500000': 1500000, '120.000đ': 120000, '2 triệu': 2000000, '999': 999000,
      '1000': 1000};
    for (const [raw, want] of Object.entries(cases)) assert.equal(ctx.parseAmount(raw), want, raw);
    assert.equal(ctx.parseAmount(45), 45000);
    assert.equal(ctx.parseAmount(250000), 250000);
    for (const bad of ['', 'abc', '1.5', '-5']) assert.ok(Number.isNaN(ctx.parseAmount(bad)), bad);
  },
  parse_date() {
    const {ctx} = load();
    assert.equal(ctx.parseDate('2026-11-02'), '2026-11-02T00:00:00');
    assert.equal(ctx.parseDate('02/11/2026'), '2026-11-02T00:00:00');
    assert.equal(ctx.parseDate('2/11/26'), '2026-11-02T00:00:00');
    assert.equal(ctx.parseDate('hôm qua'), null);
    assert.equal(ctx.parseDate('32/1/2026'), null);
  },
  setup_creates_header_and_secret() {
    const {sheet, secret} = load();
    assert.deepEqual(sheet.rows[0], ['Mã', 'Thời gian', 'Số tiền', 'Mô tả', 'Trả bằng', 'Người nhập']);
    assert.match(secret, /^[0-9a-f]{24}$/);
  },
  wrong_secret_is_refused() {
    const {ctx, sheet} = load();
    const r = ctx.doGet({parameter: {a: 'add', k: 'nope', so: '45', d: 'Phở'}});
    assert.match(r.body, /^✗ Mã kết nối sai/);
    assert.equal(sheet.rows.length, 1);
    const l = ctx.doGet({parameter: {a: 'list'}});
    assert.equal(JSON.parse(l.body).ok, false);
  },
  add_appends_row_and_replies_in_text() {
    const {ctx, sheet, secret} = load();
    const r = ctx.doGet({parameter: {a: 'add', k: secret, so: '45', d: ' Phở bò ', t: 'Tiền mặt', n: 'iPhone của Lan'}});
    assert.equal(r.body, '✓ Đã ghi 45.000 ₫ · Phở bò');
    assert.equal(r.mime, 'text');
    const row = sheet.rows[1];
    assert.equal(row[2], 45000);
    assert.equal(row[3], 'Phở bò');
    assert.equal(row[4], 'Tiền mặt');
    assert.equal(row[5], 'iPhone của Lan');
    assert.ok(row[1] instanceof Date);
  },
  add_rejects_bad_amount_without_writing() {
    const {ctx, sheet, secret} = load();
    const r = ctx.doGet({parameter: {a: 'add', k: secret, so: 'abc'}});
    assert.match(r.body, /^✗ Số tiền "abc" chưa đúng/);
    assert.equal(sheet.rows.length, 1);
  },
  list_returns_rows_and_fills_hand_typed_ones() {
    const {ctx, sheet, secret} = load();
    ctx.doGet({parameter: {a: 'add', k: secret, so: '1tr5', d: 'Học phí', t: 'Chuyển khoản'}});
    sheet.rows.push(['', '01/11/2026', '30k', 'Gửi xe', '', '']);  // typed in the Sheets app
    sheet.rows.push(['', '', '', '', '', '']);                      // blank line
    sheet.rows.push(['', '', 50000, 'Trà sữa', 'Visa', '']);         // no time typed
    const body = JSON.parse(ctx.doGet({parameter: {a: 'list', k: secret}}).body);
    assert.equal(body.ok, true);
    assert.equal(body.rows.length, 3);
    const [a, b, c] = body.rows;
    assert.equal(a.amount, 1500000);
    assert.equal(a.account, 'Chuyển khoản');
    assert.equal(b.time, '2026-11-01T00:00:00');
    assert.equal(b.amount, 30000);
    assert.ok(b.id, 'hand-typed row got an id');
    assert.equal(sheet.rows[2][0], b.id, 'id written back so the next sync sees the same one');
    assert.ok(sheet.rows[4][1] instanceof Date, 'missing time filled in');
    assert.match(c.time, /^\d{4}-\d\d-\d\dT/);
    const again = JSON.parse(ctx.doGet({parameter: {a: 'list', k: secret}}).body);
    assert.deepEqual(again.rows.map(r => r.id), body.rows.map(r => r.id), 'ids are stable');
  },
  ping() {
    const {ctx, secret} = load();
    assert.deepEqual(JSON.parse(ctx.doGet({parameter: {a: 'ping', k: secret}}).body),
      {ok: true, sheet: 'https://docs.google.com/spreadsheets/d/sheet-1'});
  },
  rotate_secret_invalidates_old_code() {
    const {ctx, secret, store} = load();
    ctx.doiMa();
    assert.notEqual(store.SECRET, secret);
    assert.equal(JSON.parse(ctx.doGet({parameter: {a: 'ping', k: secret}}).body).ok, false);
  },
};

const only = process.argv[2];
let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  if (only && name !== only) continue;
  try { fn(); console.log('ok', name); } catch (e) { failed++; console.log('FAIL', name, e.message); }
}
process.exit(failed ? 1 : 0);
