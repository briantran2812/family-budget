// Runs phone/Code.gs against in-memory fakes of the Apps Script services. Invoked by tests/test_apps_script.py.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const SRC = fs.readFileSync(new URL('../../phone/Code.gs', import.meta.url), 'utf8');

function newTab(ss) {
  const rows = [];
  const tab = {
    rows,
    getLastRow: () => rows.length,
    appendRow: r => rows.push([...r]),
    setFrozenRows() {}, setColumnWidth() {},
    formats: {},
    getRange(a, b, n, w) {
      if (typeof a === 'string') return {setFontWeight() {}, setNumberFormat(f) { tab.formats[a] = f; }};
      return {
        setFontWeight() {}, setNumberFormat() {},
        getValues: () => rows.slice(a - 1, a - 1 + n).map(r => Array.from({length: w}, (_, i) => r[b - 1 + i] ?? '')),
        setValues: vals => vals.forEach((v, i) => {
          const r = rows[a - 1 + i] || (rows[a - 1 + i] = []);
          v.forEach((x, j) => { r[b - 1 + j] = x; });
        }),
        clearContent: () => { rows.splice(a - 1, n); },
      };
    },
    deleteRows: (start, n) => { rows.splice(start - 1, n); },
    getParent: () => ss,
  };
  return tab;
}

function fakeSheet() {
  const tabs = {};
  const ss = {
    tabs,
    getId: () => 'sheet-1', getUrl: () => 'https://docs.google.com/spreadsheets/d/sheet-1',
    getName: () => 'Thu Chi — TEST',
    getSheetByName: name => tabs[name] || null,
    insertSheet: name => (tabs[name] = newTab(ss)),
    getSpreadsheetTimeZone: () => 'Asia/Ho_Chi_Minh',
  };
  return {ss, get sheet() { return tabs['Hộp thư đến']; }};
}

/** Gmail: `threads` is a list of lists of messages; search() pages through it and records each query. */
function fakeGmail() {
  const gmail = {threads: [], queries: [], reads: 0};
  gmail.app = {
    search: (q, start, max) => {
      gmail.queries.push(q);
      return gmail.threads.slice(start, start + max).map(msgs => ({getMessages: () => msgs.map(m => message(gmail, m))}));
    },
  };
  return gmail;
}

function message(gmail, m) {
  const headers = m.headers || {};
  return {
    getId: () => m.id, getDate: () => m.date, getFrom: () => m.from ?? 'Shopee <info@mail.shopee.vn>',
    getSubject: () => m.subject ?? 'Xác nhận đơn hàng', isInTrash: () => !!m.trash,
    getPlainBody: () => { gmail.reads++; return m.plain ?? ''; },
    getBody: () => { gmail.reads++; return m.html ?? m.plain ?? ''; },
    getHeader: name => headers[name] ?? '',
  };
}

function fakeTriggers() {
  const list = [];
  return {
    list,
    getProjectTriggers: () => [...list],
    deleteTrigger: t => list.splice(list.indexOf(t), 1),
    newTrigger: fn => ({timeBased: () => ({everyMinutes: n => ({create: () => {
      const t = {fn, n, getHandlerFunction: () => fn}; list.push(t); return t;
    }})})}),
  };
}

function load() {
  const fake = fakeSheet();
  const gmail = fakeGmail();
  const triggers = fakeTriggers();
  const logs = [];
  const ss = fake.ss;
  const store = {};
  let uuid = 0;
  const pad = n => String(n).padStart(2, '0');
  const ctxLocked = {held: false};
  const ctx = {
    PropertiesService: {getScriptProperties: () => ({
      getProperty: k => store[k] ?? null, setProperty: (k, v) => { store[k] = v; } })},
    SpreadsheetApp: {getActiveSpreadsheet: () => ss, create: () => ss, openById: () => ss},
    LockService: {getScriptLock: () => ({waitLock() {}, tryLock: () => !ctxLocked.held, releaseLock() {}})},
    Utilities: {
      getUuid: () => `${String(++uuid).padStart(8, '0')}-aaaa-bbbb-cccc-dddddddddddd`,
      // Fakes run in UTC; the formatted string is what matters.
      formatDate: d => `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:00`,
    },
    ContentService: {MimeType: {TEXT: 'text', JSON: 'json'},
      createTextOutput: s => ({body: s, setMimeType(m) { this.mime = m; return this; }})},
    Logger: {log: (...a) => logs.push(a)},
    ScriptApp: {getService: () => ({getUrl: () => 'https://script.google.com/macros/s/X/exec'}), ...triggers},
    GmailApp: gmail.app,
    Date, JSON, Math, String, parseInt, parseFloat, isNaN,
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  ctx.caiDat();
  return {ctx, sheet: fake.sheet, ss, secret: store.SECRET, store, gmail, triggers, logs, lock: ctxLocked};
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
    assert.deepEqual(sheet.rows[0], ['Mã', 'Thời gian', 'Số tiền', 'Mô tả', 'Trả bằng', 'Người nhập', 'Hạng mục']);
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
    const r = ctx.doGet({parameter: {a: 'add', k: secret, so: '45000', d: ' Phở bò ', t: 'Tiền mặt', n: 'iPhone của Lan'}});
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
      {ok: true, sheet: 'https://docs.google.com/spreadsheets/d/sheet-1', name: 'Thu Chi — TEST', version: ctx.SCRIPT_VERSION});
    assert.ok(Number.isInteger(ctx.SCRIPT_VERSION) && ctx.SCRIPT_VERSION >= 2);
  },
  list_reports_sheet_name_and_script_version() {
    // The Mac re-reads these on every sync, so a Code.gs promoted later clears the "old script" warning.
    const {ctx, secret} = load();
    const body = JSON.parse(ctx.doGet({parameter: {a: 'list', k: secret}}).body);
    assert.equal(body.name, 'Thu Chi — TEST');
    assert.equal(body.version, ctx.SCRIPT_VERSION);
  },
  script_version_matches_what_the_mac_app_requires() {
    const {ctx} = load();
    const py = fs.readFileSync(new URL('../../phone_inbox.py', import.meta.url), 'utf8');
    const required = Number(py.match(/^REQUIRED_SCRIPT_VERSION = (\d+)/m)[1]);
    assert.ok(ctx.SCRIPT_VERSION >= required, `Code.gs ${ctx.SCRIPT_VERSION} < app's ${required}`);
  },
  rotate_secret_invalidates_old_code() {
    const {ctx, secret, store} = load();
    ctx.doiMa();
    assert.notEqual(store.SECRET, secret);
    assert.equal(JSON.parse(ctx.doGet({parameter: {a: 'ping', k: secret}}).body).ok, false);
  },
};

const post = (ctx, secret, body) => JSON.parse(ctx.doPost({parameter: {k: secret},
  postData: {contents: typeof body === 'string' ? body : JSON.stringify(body)}}).body);

Object.assign(tests, {
  mirror_replaces_only_that_macs_rows() {
    const {ctx, ss, secret} = load();
    const row = (d, amt, mac, id) => [d, 'Chi', amt, 'x', 'Khác', 'Tiền mặt', 'iPhone', 'Có', mac, id];
    assert.deepEqual(post(ctx, secret, {a: 'mirror', device: 'MacBook Lan', rows: [row('2026-11-01', 45000, 'MacBook Lan', 1)],
      summary: [['MacBook Lan', '2026-11', 'Tổng', 'Tổng chi', 45000, 1]]}), {ok: true, rows: 1, summary: 1});
    post(ctx, secret, {a: 'mirror', device: 'MacBook Brian', rows: [row('2026-11-02', 9000, 'MacBook Brian', 7)], summary: []});
    // Lan's Mac syncs again with two rows: her old row is replaced, Brian's stays.
    post(ctx, secret, {a: 'mirror', device: 'MacBook Lan',
      rows: [row('2026-11-03', 30000, 'MacBook Lan', 2), row('2026-11-01', 45000, 'MacBook Lan', 1)], summary: []});
    const tx = ss.tabs['Giao dịch'].rows;
    assert.equal(tx[0][0], 'Ngày');
    assert.deepEqual(tx.slice(1).map(r => [r[0], r[8]]),
      [['2026-11-03', 'MacBook Lan'], ['2026-11-02', 'MacBook Brian'], ['2026-11-01', 'MacBook Lan']]);
    assert.equal(ss.tabs['Tổng hợp'].rows.length, 1, 'Lan sent an empty summary the second time');
  },
  mirror_refuses_wrong_secret_and_bad_body() {
    const {ctx, ss, secret} = load();
    assert.equal(post(ctx, 'nope', {a: 'mirror', device: 'x', rows: []}).error, 'Mã kết nối sai');
    assert.match(post(ctx, secret, '{not json').error, /không đọc được/);
    assert.match(post(ctx, secret, {a: 'mirror', rows: []}).error, /tên máy/);
    assert.equal(ss.tabs['Giao dịch'], undefined);
  },
});

Object.assign(tests, {
  shortcut_amounts_are_exact() {
    const {ctx, sheet, secret} = load();
    for (const [so, want] of [['45000', 45000], ['7000000', 7000000], ['7.000.000', 7000000], ['1tr5', 1500000], ['45k', 45000]]) {
      const r = ctx.doGet({parameter: {a: 'add', k: secret, so, d: 'x'}});
      assert.match(r.body, /^✓/, so);
      assert.equal(sheet.rows.at(-1)[2], want, so);
    }
    assert.match(ctx.doGet({parameter: {a: 'add', k: secret, so: '45', d: 'x'}}).body, /quá nhỏ — gõ đủ các số 0/);
    assert.match(ctx.doGet({parameter: {a: 'add', k: secret, so: '70000000000', d: 'x'}}).body, /quá lớn/);
    assert.equal(sheet.rows.length, 6);
  },
});

Object.assign(tests, {
  category_column_round_trips_and_old_sheets_get_the_header() {
    const {ctx, sheet, secret} = load();
    sheet.rows[0] = sheet.rows[0].slice(0, 6);  // a sheet set up before the column existed
    const r = ctx.doGet({parameter: {a: 'add', k: secret, so: '45000', d: 'Phở', t: 'Tiền mặt', c: '🛒 Ăn uống & đi chợ'}});
    assert.equal(r.body, '✓ Đã ghi 45.000 ₫ · Phở · 🛒 Ăn uống & đi chợ');
    assert.equal(sheet.rows[0][6], 'Hạng mục');
    const [row] = JSON.parse(ctx.doGet({parameter: {a: 'list', k: secret}}).body).rows;
    assert.equal(row.category, '🛒 Ăn uống & đi chợ');
  },
});

// ---------------------------------------------------------------- Gmail → tab "Email" (SCRIPT_VERSION 3)

const SHOPEE_HTML = '<html><head><style>td{color:red}</style></head><body><table>' +
  '<tr><td>Đơn hàng #261101ABCD1234 của bạn đã được đặt thành công.</td></tr>' +
  '<tr><td>Kem chống nắng Anessa</td><td>x1</td><td>₫465.000</td></tr>' +
  '<tr><td>Tổng&nbsp;thanh toán</td><td>&#8363;465.000</td></tr></table></body></html>';
Date.now = () => Date.UTC(2026, 10, 5, 12);  // retention counts from Date.now; fixed so the November dates below never age out
const day = (d, h = 9) => new Date(Date.UTC(2026, 10, d, h, 0, 0));
const msg = (id, d, extra = {}) => ({id, date: day(d), html: SHOPEE_HTML, ...extra});
const emailTab = ss => ss.tabs['Email'];
const getEmails = (ctx, secret, since) => JSON.parse(ctx.doGet({parameter: {a: 'emails', k: secret, since}}).body);

Object.assign(tests, {
  quet_email_copies_new_messages_oldest_first() {
    const {ctx, ss, gmail} = load();
    gmail.threads = [
      [msg('18c2', 2, {headers: {'Message-ID': '<a@shopee>'}}),
       msg('18c3', 3, {subject: 'Đơn hàng đang được giao', html: '', plain: 'Đơn hàng #261101ABCD1234\nđang giao'})],
      [msg('18c1', 1, {from: 'MoMo <no-reply@momo.vn>', headers: {'X-Forwarded-For': 'lan@gmail.com hao@gmail.com'}})],
      [msg('18c0', 1, {trash: true})],
    ];
    assert.equal(ctx.quetEmail(), 3);
    const rows = emailTab(ss).rows;
    assert.deepEqual(rows[0], ['Mã thư', 'Ngày', 'Người gửi', 'Tiêu đề', 'Nội dung', 'Ghi chú', 'Message-ID']);
    assert.deepEqual(rows.slice(1).map(r => r[0]), ['18c1', '18c2', '18c3']);
    assert.ok(rows[1][1] instanceof Date);
    assert.equal(rows[1][2], 'MoMo <no-reply@momo.vn>');
    assert.equal(rows[1][5], 'chuyển tiếp từ lan@gmail.com');
    assert.equal(rows[2][4], 'Đơn hàng #261101ABCD1234 của bạn đã được đặt thành công.\nKem chống nắng Anessa\nx1\n₫465.000\nTổng thanh toán\n₫465.000');
    assert.equal(rows[2][6], '<a@shopee>');
    assert.equal(rows[3][4], 'Đơn hàng #261101ABCD1234\nđang giao', 'no HTML part: the plain body');
    assert.equal(emailTab(ss).formats['A:A'], '@', 'ids stay text');
    assert.match(gmail.queries[0], /^from:\(shopee OR tiktok OR momo\) newer_than:30d -in:spam -in:trash$/);
  },
  quet_email_skips_ids_already_stored() {
    const {ctx, ss, gmail} = load();
    gmail.threads = [[msg('a1', 1), msg('a2', 2)]];
    ctx.quetEmail();
    const reads = gmail.reads;
    assert.equal(ctx.quetEmail(), 0);
    assert.equal(gmail.reads, reads, 'bodies of known messages are not read again');
    gmail.threads.push([msg('a3', 3)]);
    assert.equal(ctx.quetEmail(), 1);
    assert.deepEqual(emailTab(ss).rows.slice(1).map(r => r[0]), ['a1', 'a2', 'a3']);
  },
  quet_email_truncates_long_bodies_and_guards_formulas() {
    const {ctx, ss, gmail} = load();
    gmail.threads = [[msg('b1', 1, {html: '', plain: 'x'.repeat(60000), subject: '=HYPERLINK("http://x")'})]];
    ctx.quetEmail();
    const row = emailTab(ss).rows[1];
    assert.equal(row[4].length, 45000);
    assert.equal(row[3], `'=HYPERLINK("http://x")`);
  },
  quet_email_uses_the_query_property_and_caps_each_run() {
    const {ctx, ss, gmail, store} = load();
    store.EMAIL_QUERY = 'from:shopee newer_than:7d';
    gmail.threads = Array.from({length: 250}, (_, i) => [msg('c' + String(i).padStart(3, '0'), 1 + (i % 20))]);
    assert.equal(ctx.quetEmail(), 200);
    assert.equal(ctx.quetEmail(), 50, 'the rest on the next run');
    assert.equal(emailTab(ss).rows.length, 251);
    assert.ok(gmail.queries.every(q => q === 'from:shopee newer_than:7d'));
  },
  quet_email_keeps_90_days_and_1000_rows() {
    const {ctx, ss, gmail} = load();
    const old = new Date(Date.now() - 100 * 864e5), recent = new Date(Date.now() - 864e5);
    gmail.threads = [[{id: 'old1', date: old, plain: 'a'}, {id: 'old2', date: old, plain: 'a'}, {id: 'new1', date: recent, plain: 'a'}]];
    ctx.quetEmail();
    assert.deepEqual(emailTab(ss).rows.slice(1).map(r => r[0]), ['new1']);
    for (let i = 0; i < 1005; i++) emailTab(ss).rows.push(['f' + i, recent, '', '', '', '', '']);
    ctx.quetEmail();
    assert.equal(emailTab(ss).rows.length, 1001);
    assert.equal(emailTab(ss).rows.at(-1)[0], 'f1004', 'the newest rows stay');
  },
  quet_email_does_not_store_what_a_concurrent_run_stored() {
    const {ctx, ss, gmail} = load();
    gmail.threads = [[msg('d1', 1), msg('d2', 2)]];
    const search = gmail.app.search;
    gmail.app.search = (...a) => {  // a run started by hand finishes while this one reads Gmail
      emailTab(ss) || ctx.emailSheet_();
      emailTab(ss).rows.push(['d1', day(1), '', '', '', '', '']);
      return search(...a);
    };
    assert.equal(ctx.quetEmail(), 1);
    assert.deepEqual(emailTab(ss).rows.slice(1).map(r => r[0]), ['d1', 'd2']);
  },
  emails_answers_empty_while_a_scan_holds_the_lock() {
    const {ctx, gmail, secret, lock} = load();
    gmail.threads = [[msg('h1', 1)]];
    ctx.quetEmail();
    lock.held = true;
    const r = getEmails(ctx, secret, 'x');
    assert.deepEqual([r.ok, r.rows.length, r.next, r.more], [true, 0, 'x', false]);
  },
  bat_quet_email_installs_one_trigger_and_tat_removes_it() {
    const {ctx, gmail, triggers, logs} = load();
    gmail.threads = [[msg('e1', 1), msg('e2', 2)]];
    ctx.batQuetEmail();
    ctx.batQuetEmail();
    assert.deepEqual(triggers.list.map(t => [t.fn, t.n]), [['quetEmail', 30]]);
    const done = logs.filter(l => /Lần này lưu %s email/.test(l[0]));
    assert.deepEqual(done.map(l => l[1]), [2, 0]);
    ctx.tatQuetEmail();
    assert.equal(triggers.list.length, 0);
  },
  emails_pages_through_the_tab_with_a_cursor() {
    const {ctx, gmail, secret} = load();
    gmail.threads = Array.from({length: 230}, (_, i) => [msg('m' + String(i).padStart(3, '0'), 1, {plain: 'b', html: ''})]);
    ctx.quetEmail();
    ctx.quetEmail();
    let r = getEmails(ctx, secret);
    assert.equal(r.ok, true);
    assert.equal(r.version, ctx.SCRIPT_VERSION);
    assert.equal(r.rows.length, 100);
    assert.equal(r.more, true);
    assert.equal(r.next, 'm099');
    assert.deepEqual(Object.keys(r.rows[0]).sort(), ['body', 'date', 'from', 'id', 'mid', 'note', 'row', 'subject']);
    assert.equal(r.rows[0].date, '2026-11-01T09:00:00');
    assert.equal(r.rows[0].row, 2);
    assert.match(r.scanned, /^\d{4}-\d\d-\d\dT/);
    r = getEmails(ctx, secret, r.next);
    assert.equal(r.rows[0].id, 'm100');
    r = getEmails(ctx, secret, r.next);
    assert.deepEqual([r.rows.length, r.more, r.next], [30, false, 'm229']);
    r = getEmails(ctx, secret, 'm229');
    assert.deepEqual([r.rows.length, r.more, r.next], [0, false, 'm229'], 'nothing new: the cursor stays');
    r = getEmails(ctx, secret, 'pruned-long-ago');
    assert.equal(r.rows[0].id, 'm000', 'an unknown cursor starts over; the Mac skips ids it has');
  },
  emails_page_stops_at_the_character_budget() {
    const {ctx, gmail, secret} = load();
    gmail.threads = [[msg('n1', 1, {html: '', plain: 'x'.repeat(3000)}), msg('n2', 2, {html: '', plain: 'y'}),
                      msg('n3', 3, {html: '', plain: 'z'})]];
    ctx.quetEmail();
    ctx.EMAIL_PAGE_CHARS = 1000;
    let r = getEmails(ctx, secret);
    assert.deepEqual([r.rows.map(x => x.id), r.more], [['n1'], true], 'one big row still goes alone');
    ctx.EMAIL_PAGE_CHARS = 2;
    r = getEmails(ctx, secret, r.next);
    assert.deepEqual([r.rows.map(x => x.id), r.more], [['n2', 'n3'], false]);
  },
  emails_before_any_scan_and_with_a_wrong_secret() {
    const {ctx, secret} = load();
    assert.deepEqual(getEmails(ctx, secret), {ok: true, rows: [], next: '', more: false, scanned: '', version: ctx.SCRIPT_VERSION});
    assert.deepEqual(getEmails(ctx, 'nope'), {ok: false, error: 'Mã kết nối sai'});
  },
  email_script_version_matches_the_mac_app() {
    const {ctx} = load();
    const py = fs.readFileSync(new URL('../../sheet_email.py', import.meta.url), 'utf8');
    const needed = Number(py.match(/^EMAIL_SCRIPT_VERSION = (\d+)/m)[1]);
    assert.ok(ctx.SCRIPT_VERSION >= needed, `Code.gs ${ctx.SCRIPT_VERSION} < ${needed} needed for email`);
  },
});

if (process.argv[2] === '--html-to-text') {  // used by tests/test_apps_script.py to compare with parsers.html_to_text
  const {ctx} = load();
  process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0, 'utf8')).map(h => ctx.htmlToText(h))));
  process.exit(0);
}

const only = process.argv[2];
let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  if (only && name !== only) continue;
  try { fn(); console.log('ok', name); } catch (e) { failed++; console.log('FAIL', name, e.message); }
}
process.exit(failed ? 1 : 0);
