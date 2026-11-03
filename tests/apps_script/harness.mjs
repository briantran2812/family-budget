// Runs phone/Code.gs against in-memory fakes of the Apps Script services. Invoked by tests/test_apps_script.py.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// CODE_GS: another copy, e.g. Code.gs 4 from git for the compatibility test in tests/test_apps_script.py.
const SRC = fs.readFileSync(process.env.CODE_GS || new URL('../../phone/Code.gs', import.meta.url), 'utf8');

function newTab(ss) {
  const rows = [];
  const tab = {
    rows,
    getLastRow: () => rows.length,
    appendRow: r => rows.push([...r]),
    setFrozenRows() {}, setColumnWidth() {}, hidden: false, hideSheet() { tab.hidden = true; },
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

/** Moves the clock both Code.gs and the tests read. */
const setNow = t => { Date.now = () => t; };

/**
 * The Bot API: `updates` is what getUpdates serves (from `offset` on); every call is recorded in `calls`. `later` holds
 * {at, make} for updates that arrive at time `at`: a getUpdates with a timeout returns as soon as one is due (moving the
 * clock there) or after the timeout (moving the clock by it), like Telegram's long polling without real waiting.
 */
function fakeTelegram() {
  const tg = {token: '123456:TEST-token', updates: [], later: [], calls: [], nextId: 500, webhook: true, fail: null,
    me: {id: 999, is_bot: true, first_name: 'Sổ nhà mình', username: 'SoNhaMinhBot', can_read_all_group_messages: true}};
  tg.app = {fetch(url, opts) {
    const m = url.match(/^https:\/\/api\.telegram\.org\/bot([^/]+)\/(\w+)$/);
    assert.ok(m, url);
    assert.equal(opts.muteHttpExceptions, true);
    const method = m[2], params = JSON.parse(opts.payload || '{}');
    const call = {method, params};
    tg.calls.push(call);
    if (tg.fail === 'throw') throw new Error(`Address unavailable: ${url}`);
    const reply = body => ({getResponseCode: () => body.ok ? 200 : body.error_code, getContentText: () => JSON.stringify(body)});
    if (tg.fail === 'html') return {getResponseCode: () => 502, getContentText: () => '<html>Bad Gateway</html>'};
    if (m[1] !== tg.token) return reply({ok: false, error_code: 401, description: 'Unauthorized'});
    if (method === 'getMe') return reply({ok: true, result: tg.me});
    if (method === 'deleteWebhook') { tg.webhook = false; return reply({ok: true, result: true}); }
    if (method === 'getUpdates') {
      if (tg.webhook) return reply({ok: false, error_code: 409, description: 'Conflict: can\'t use getUpdates method while webhook is active'});
      const ready = () => tg.updates.filter(u => u.update_id >= (params.offset || 0));
      if (!ready().length && params.timeout > 0) {
        const end = Date.now() + params.timeout * 1000;
        tg.later.sort((a, b) => a.at - b.at);
        if (tg.later.length && tg.later[0].at <= end) {
          const next = tg.later.shift();
          setNow(Math.max(next.at, Date.now()));
          tg.updates.push(next.make());
        } else {
          setNow(end);
        }
      }
      return reply({ok: true, result: ready()});
    }
    if (method === 'sendMessage') {
      call.message = {message_id: tg.nextId++, chat: {id: params.chat_id}, text: params.text};
      return reply({ok: true, result: call.message});
    }
    if (method === 'editMessageText' || method === 'answerCallbackQuery') return reply({ok: true, result: true});
    return reply({ok: false, error_code: 404, description: 'Not Found'});
  }};
  return tg;
}

function fakeCache() {
  const items = {};
  return {items, getScriptCache: () => ({
    put: (k, v, secs) => {
      assert.ok(secs <= 21600, 'CacheService keeps at most 6 hours');
      if (String(v).length > 100000) throw new Error('Argument too large: value');
      items[k] = String(v);
    },
    get: k => items[k] ?? null, remove: k => { delete items[k]; }})};
}

/** Utilities.formatDate for the patterns Code.gs uses; the fakes run in UTC whatever zone is asked for. */
function formatDate(d, tz, pattern) {
  const pad = n => String(n).padStart(2, '0');
  const parts = {yyyy: d.getUTCFullYear(), MM: pad(d.getUTCMonth() + 1), dd: pad(d.getUTCDate()), HH: pad(d.getUTCHours()),
                 mm: pad(d.getUTCMinutes()), ss: pad(d.getUTCSeconds()), u: d.getUTCDay() || 7};
  return pattern.replace(/'([^']*)'|yyyy|MM|dd|HH|mm|ss|u/g, (t, lit) => lit !== undefined ? lit : String(parts[t]));
}

function load() {
  const fake = fakeSheet();
  const gmail = fakeGmail();
  const triggers = fakeTriggers();
  const tg = fakeTelegram();
  const cache = fakeCache();
  const logs = [];
  const ss = fake.ss;
  const store = {};
  let uuid = 0;
  const ctxLocked = {held: false, userHeld: false};
  const ctx = {
    PropertiesService: {getScriptProperties: () => ({
      getProperty: k => store[k] ?? null, setProperty: (k, v) => { store[k] = v; } })},
    SpreadsheetApp: {getActiveSpreadsheet: () => ss, create: () => ss, openById: () => ss},
    LockService: {getScriptLock: () => ({waitLock() {}, tryLock: () => !ctxLocked.held, releaseLock() {}}),
      getUserLock: () => ({tryLock: () => !ctxLocked.userHeld && (ctxLocked.userHeld = true),
                           releaseLock: () => { ctxLocked.userHeld = false; }})},
    Utilities: {
      getUuid: () => `${String(++uuid).padStart(8, '0')}-aaaa-bbbb-cccc-dddddddddddd`,
      formatDate,
    },
    UrlFetchApp: tg.app,
    CacheService: cache,
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
  return {ctx, sheet: fake.sheet, ss, secret: store.SECRET, store, gmail, triggers, logs, lock: ctxLocked, tg, cache};
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
    assert.deepEqual(sheet.rows[0], ['Mã', 'Thời gian', 'Số tiền', 'Mô tả', 'Trả bằng', 'Người nhập', 'Hạng mục', 'Kênh', 'Trạng thái']);
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

// ---------------------------------------------------------------- Telegram bot (SCRIPT_VERSION 4)

const LAN = {id: 11, is_bot: false, first_name: 'Lan'};
const HAO = {id: 22, is_bot: false, first_name: 'Hào'};
const GROUP = {id: -100777, type: 'supergroup', title: 'Nhà mình'};
const clock = iso => { Date.now = () => Date.parse(iso); };

/** A sheet with the bot set up and, unless `pair` is false, paired with the family group. */
function bot({pair = true, fast = false} = {}) {
  const env = load();
  env.store.TELEGRAM_TOKEN = env.tg.token;
  env.store.TG_FAST_MINUTES = '0';  // one quick getUpdates per run, so these tests keep their clock
  env.ctx.batTelegram();
  env.uid = 1;
  env.mid = 1;
  if (pair) say(env, `/ketnoi ${env.store.TG_PAIR_CODE}`);
  if (fast) {
    delete env.store.TG_FAST_MINUTES;
    delete env.store.TG_ACTIVE_AT;
  }
  env.tg.calls.length = 0;
  return env;
}

/** What the bot did during one run of the minute trigger, without the getUpdates call. */
function poll(env) {
  const before = env.tg.calls.length;
  env.ctx.pollTelegram();
  return env.tg.calls.slice(before).filter(c => c.method !== 'getUpdates');
}

function say(env, text, {from = LAN, chat = GROUP, reply} = {}) {
  const message = {message_id: env.mid++, from, chat, date: Math.floor(Date.now() / 1000), text};
  if (reply) message.reply_to_message = reply;
  env.tg.updates.push({update_id: env.uid++, message});
  return poll(env);
}

/** Taps a button under the bot message `msg` ({message_id, text}). */
function tap(env, msg, data, from = LAN, chat = GROUP) {
  env.tg.updates.push({update_id: env.uid++, callback_query: {id: 'q' + env.uid, from, data,
    message: {message_id: msg.message_id, chat, text: msg.text}}});
  return poll(env);
}

const only1 = (calls, method) => {
  const xs = calls.filter(c => c.method === method);
  assert.equal(xs.length, 1, `${method}: ${JSON.stringify(calls.map(c => c.method))}`);
  return xs[0];
};
const buttons = call => call.params.reply_markup.inline_keyboard.flat();
const press = (call, label) => {
  const b = buttons(call).find(x => x.text === label || x.text.endsWith(' ' + label));
  assert.ok(b, `no button ${label} in ${buttons(call).map(x => x.text)}`);
  return b.callback_data;
};

/** "45k phở" → category → (payment) → recorded. Returns the confirmation edit. */
function enter(env, text, category, account, from = LAN) {
  const ask = only1(say(env, text, {from}), 'sendMessage');
  let calls = tap(env, ask.message, press(ask, category), from);
  if (account) calls = tap(env, ask.message, press(only1(calls, 'editMessageText'), account), from);
  return Object.assign(only1(calls, 'editMessageText'), {message: ask.message});
}

const inbox = env => env.sheet.rows.slice(1);

Object.assign(tests, {
  telegram_setup_validates_the_token_and_installs_one_trigger() {
    const env = load();
    assert.throws(() => env.ctx.batTelegram(), /TELEGRAM_TOKEN/);
    env.store.TELEGRAM_TOKEN = 'wrong';
    assert.throws(() => env.ctx.batTelegram(), /không nhận token: Unauthorized/);
    assert.equal(env.triggers.list.length, 0);
    env.store.TELEGRAM_TOKEN = env.tg.token;
    env.ctx.batTelegram();
    env.ctx.batTelegram();
    assert.deepEqual(env.triggers.list.map(t => [t.fn, t.n]), [['pollTelegram', 1]]);
    assert.ok(env.tg.calls.some(c => c.method === 'deleteWebhook'));
    assert.match(env.store.TG_PAIR_CODE, /^\d{6}$/);
    const said = env.logs.filter(l => /Trong nhóm gia đình gõ: \/ketnoi %s/.test(l[0]));
    assert.deepEqual(said.map(l => [l[1], l[2]]), [['SoNhaMinhBot', env.store.TG_PAIR_CODE], ['SoNhaMinhBot', env.store.TG_PAIR_CODE]],
      'running it again keeps the code');
    assert.ok(!env.logs.some(l => /privacy mode/.test(l[0])));
    env.tg.me.can_read_all_group_messages = false;
    env.ctx.batTelegram();
    assert.ok(env.logs.some(l => /privacy mode[\s\S]*\/setprivacy[\s\S]*Disable/.test(l[0])));
    env.ctx.tatTelegram();
    assert.equal(env.triggers.list.length, 0);
  },
  telegram_pairing_and_strangers() {
    const env = bot({pair: false});
    const stranger = {id: 55, type: 'private'};
    let calls = say(env, '45k phở', {chat: stranger, from: HAO});
    assert.match(only1(calls, 'sendMessage').params.text, /^Bot riêng của gia đình/);
    assert.deepEqual(say(env, '50k bún', {chat: stranger, from: HAO}), [], 'at most once a day');
    assert.deepEqual(say(env, '/thang', {chat: stranger, from: HAO}), []);
    assert.deepEqual(Object.keys(env.cache.items), [], 'nothing pending for a stranger');
    calls = say(env, '/ketnoi 000000');
    assert.match(only1(calls, 'sendMessage').params.text, /Mã không đúng/);
    calls = say(env, `/ketnoi@SoNhaMinhBot ${env.store.TG_PAIR_CODE}`);
    assert.equal(only1(calls, 'sendMessage').params.text, '✓ Đã kết nối nhóm "Nhà mình". Thử gõ: 45k phở\n/huongdan để xem cách dùng.');
    assert.deepEqual(JSON.parse(env.store.TG_CHATS).map(c => c.id), [GROUP.id]);
    assert.match(only1(say(env, '45k phở'), 'sendMessage').params.text, /hạng mục\?$/);
    clock('2026-11-06T09:00:00Z');
    assert.match(only1(say(env, 'alo', {chat: stranger, from: HAO}), 'sendMessage').params.text, /^Bot riêng/, 'next day: once more');
    for (let i = 0; i < 10; i++) say(env, '/ketnoi 111111', {chat: stranger, from: HAO});
    assert.deepEqual(say(env, `/ketnoi ${env.store.TG_PAIR_CODE}`, {chat: stranger, from: HAO}), [],
      'after 10 wrong codes in a day even the right one is ignored');
    env.ctx.doiMaTelegram();
    assert.deepEqual(JSON.parse(env.store.TG_CHATS), []);
    assert.match(only1(say(env, '45k phở'), 'sendMessage').params.text, /^Bot riêng/, 'a new code forgets the group');
  },
  telegram_amounts() {
    const {ctx} = load();
    const cases = {'45k phở': [45000, 'Phở', ''], '45.000 phở tm': [45000, 'Phở', 'Tiền mặt'], '45,000 phở': [45000, 'Phở', ''],
      '45000 phở': [45000, 'Phở', ''], '1tr5 học phí ck': [1500000, 'Học phí', 'Chuyển khoản'],
      '1,5tr học phí': [1500000, 'Học phí', ''], '2 triệu tiền nhà': [2000000, 'Tiền nhà', ''],
      '2 tr': [2000000, '', ''], '120000 cà phê visa': [120000, 'Cà phê', 'Thẻ Visa'], '45k - phở bò': [45000, 'Phở bò', ''],
      '1.500.000 đóng học': [1500000, 'Đóng học', ''], '45000đ trà sữa': [45000, 'Trà sữa', '']};
    for (const [text, [amount, desc, account]] of Object.entries(cases)) {
      const e = ctx.parseEntry_(text);
      assert.deepEqual([e.amount, e.desc, e.account, e.small], [amount, desc, account, undefined], text);
    }
    assert.deepEqual(JSON.parse(JSON.stringify(ctx.parseEntry_('45 phở'))), {small: 45, desc: 'Phở', account: ''});
    for (const none of ['phở 45k', 'đón con chưa?', '0 phở', '', '10h đón con', '1.5 phở']) assert.equal(ctx.parseEntry_(none), null, none);
    assert.equal(ctx.parseEntry_('70000000000 x').tooBig, true);
  },
  telegram_payment_words() {
    const {ctx} = load();
    const cases = {'tm': 'Tiền mặt', 'TM': 'Tiền mặt', 'tiền mặt': 'Tiền mặt', 'Tiền Mặt': 'Tiền mặt', 'tien mat': 'Tiền mặt',
      'ck': 'Chuyển khoản', 'chuyển khoản': 'Chuyển khoản', 'chuyen khoan': 'Chuyển khoản', 'visa': 'Thẻ Visa',
      'Visa': 'Thẻ Visa', 'thẻ': 'Thẻ Visa', 'momo': 'Ví MoMo', 'MoMo': 'Ví MoMo', 'ví momo': 'Ví MoMo'};
    for (const [word, account] of Object.entries(cases)) {
      const e = ctx.parseEntry_('45k phở ' + word);
      assert.deepEqual([e.desc, e.account], ['Phở', account], word);
    }
    assert.deepEqual([ctx.parseEntry_('45k tm').desc, ctx.parseEntry_('45k tm').account], ['', 'Tiền mặt']);
    assert.equal(ctx.parseEntry_('45k mặt nạ').account, '', 'only whole trailing words');
    assert.deepEqual([...ctx.ACCOUNTS], ['Tiền mặt', 'Thẻ Visa', 'Chuyển khoản', 'Ví MoMo']);
  },
  telegram_entry_flow_appends_a_row_and_edits_the_confirmation() {
    const env = bot();
    env.sheet.rows[0] = env.sheet.rows[0].slice(0, 7);  // a sheet from Code.gs 2 or 3
    const ask = only1(say(env, '45k phở'), 'sendMessage');
    assert.equal(ask.params.chat_id, GROUP.id);
    assert.equal(ask.params.reply_parameters.message_id, env.mid - 1, 'answers the message it is about');
    assert.equal(ask.params.text, '45.000 ₫ · Phở — hạng mục?');
    const rows = ask.params.reply_markup.inline_keyboard;
    assert.equal(buttons(ask)[0].text, '✨ Tự động');
    assert.deepEqual(buttons(ask).slice(1, -1).map(b => b.text), ctx_cats(env));
    assert.ok(rows.every(r => r.length <= 3), 'compact rows');
    assert.ok(buttons(ask).every(b => Buffer.byteLength(b.callback_data) <= 64));
    assert.equal(buttons(ask).at(-1).text, '✖️ Huỷ');
    assert.equal(inbox(env).length, 0, 'nothing written before the choices');
    let calls = tap(env, ask.message, press(ask, 'Ăn uống & đi chợ'));
    only1(calls, 'answerCallbackQuery');
    const pay = only1(calls, 'editMessageText');
    assert.equal(pay.params.text, '45.000 ₫ · Phở · 🛒 Ăn uống & đi chợ — trả bằng gì?');
    assert.deepEqual(buttons(pay).map(b => b.text), ['💵 Tiền mặt', '💳 Thẻ Visa', '🏦 Chuyển khoản', '👛 Ví MoMo', '✖️ Huỷ']);
    calls = tap(env, ask.message, press(pay, 'Tiền mặt'));
    const done = only1(calls, 'editMessageText');
    assert.equal(done.params.text, '✓ Đã ghi 45.000 ₫ · Phở · 🛒 Ăn uống & đi chợ · Tiền mặt — Lan');
    assert.equal(done.params.message_id, ask.message.message_id);
    assert.equal(calls[0].method, 'answerCallbackQuery', 'answered before the Sheet is written');
    assert.equal(calls[0].params.text, undefined);
    const [row] = inbox(env);
    assert.deepEqual([row[2], row[3], row[4], row[5], row[6], row[7], row[8]],
      [45000, 'Phở', 'Tiền mặt', 'Telegram · Lan', '🛒 Ăn uống & đi chợ', 'telegram', '']);
    assert.ok(row[1] instanceof Date);
    assert.deepEqual(buttons(done), [{text: '✏️ Đổi hạng mục', callback_data: 'e|' + row[0]},
      {text: '↩️ Huỷ', callback_data: 'u|' + row[0]}]);
    assert.deepEqual(env.sheet.rows[0].slice(7), ['Kênh', 'Trạng thái'], 'old sheets get the new headers');
    calls = tap(env, ask.message, press(pay, 'Tiền mặt'), HAO);  // a late second tap
    assert.equal(only1(calls, 'answerCallbackQuery').params.text, 'Đã ghi rồi');
    assert.equal(calls.length, 1, 'no edit, no second row');
    assert.equal(inbox(env).length, 1);
    const listed = JSON.parse(env.ctx.doGet({parameter: {a: 'list', k: env.secret}}).body).rows[0];
    assert.deepEqual([listed.channel, listed.by, listed.category, listed.amount], ['telegram', 'Telegram · Lan', '🛒 Ăn uống & đi chợ', 45000]);
  },
  telegram_payment_word_skips_a_question_and_income_categories_record_money_in() {
    const env = bot();
    let done = enter(env, '1tr5 học phí ck', 'Học phí', null, HAO);
    assert.equal(done.params.text, '✓ Đã ghi 1.500.000 ₫ · Học phí · 🎓 Học phí · Chuyển khoản — Hào');
    done = enter(env, '2tr bán đồ cũ', 'Thu nhập khác', 'Chuyển khoản');
    assert.equal(done.params.text, '✓ Đã ghi khoản thu 2.000.000 ₫ · Bán đồ cũ · 💰 Thu nhập khác · Chuyển khoản — Lan');
    done = enter(env, '30k gửi xe tm', 'Tự động');
    assert.equal(done.params.text, '✓ Đã ghi 30.000 ₫ · Gửi xe · ✨ Tự động · Tiền mặt — Lan');
    assert.deepEqual(inbox(env).map(r => [r[2], r[5], r[6]]), [[1500000, 'Telegram · Hào', '🎓 Học phí'],
      [2000000, 'Telegram · Lan', '💰 Thu nhập khác'], [30000, 'Telegram · Lan', '✨ Tự động']]);
    const ask = only1(say(env, '99k nhầm'), 'sendMessage');
    const calls = tap(env, ask.message, press(ask, 'Huỷ'));
    assert.equal(only1(calls, 'editMessageText').params.text, '✖️ Bỏ qua: 99.000 ₫ · Nhầm · Tiền mặt', 'Lan paid cash last time');
    assert.equal(inbox(env).length, 3);
  },
  telegram_undo_button_and_huy_command() {
    const env = bot();
    const done = enter(env, '45k phở tm', 'Ăn uống & đi chợ');
    const id = inbox(env)[0][0];
    let calls = tap(env, {message_id: done.params.message_id, text: done.params.text}, 'u|' + id, HAO);
    assert.equal(only1(calls, 'editMessageText').params.text, '↩️ Đã huỷ: 45.000 ₫ · Phở · 🛒 Ăn uống & đi chợ · Tiền mặt — Lan (Hào huỷ)');
    assert.equal(inbox(env)[0][8], 'huỷ');
    calls = tap(env, {message_id: done.params.message_id, text: '↩️ Đã huỷ: 45.000 ₫'}, 'u|' + id);
    assert.deepEqual(calls.map(c => c.method), ['answerCallbackQuery'], 'a double tap: answered, nothing else');
    calls = tap(env, {message_id: done.params.message_id, text: done.params.text}, 'u|' + id);  // tapped before the edit arrived
    assert.equal(only1(calls, 'editMessageText').params.text, '↩️ Đã huỷ: 45.000 ₫ · Phở · 🛒 Ăn uống & đi chợ · Tiền mặt — Lan');
    calls = tap(env, {message_id: done.params.message_id, text: done.params.text}, 'u|nope');
    assert.match(only1(calls, 'editMessageText').params.text, /Không thấy dòng này/);
    enter(env, '120k cà phê visa', 'Ăn uống & đi chợ');
    assert.equal(only1(say(env, '/huy', {from: HAO}), 'sendMessage').params.text, 'Không có khoản nào bạn ghi trong 24 giờ qua.');
    calls = say(env, '/huy');
    assert.equal(only1(calls, 'sendMessage').params.text, '↩️ Đã huỷ 120.000 ₫ · Cà phê · 🛒 Ăn uống & đi chợ · Thẻ Visa');
    assert.match(only1(calls, 'editMessageText').params.text, /^↩️ Đã huỷ: 120\.000 ₫/, 'the confirmation loses its button');
    assert.deepEqual(inbox(env).map(r => r[8]), ['huỷ', 'huỷ']);
    assert.match(only1(say(env, '/huy'), 'sendMessage').params.text, /đã huỷ rồi/);
    enter(env, '50k bánh mì tm', 'Ăn uống & đi chợ');
    clock('2026-11-06T12:01:00Z');
    assert.equal(only1(say(env, '/huy'), 'sendMessage').params.text, 'Không có khoản nào bạn ghi trong 24 giờ qua.');
    assert.equal(inbox(env)[2][8], '');
  },
  telegram_small_number_asks_instead_of_guessing() {
    const env = bot();
    const ask = only1(say(env, '45 phở'), 'sendMessage');
    assert.equal(ask.params.text, 'Ý bạn là 45.000 ₫? Lần sau gõ đủ số, ví dụ 45k.');
    assert.deepEqual(buttons(ask).map(b => b.text), ['45.000 ₫', 'Huỷ']);
    let calls = tap(env, ask.message, press(ask, '45.000 ₫'));
    const cat = only1(calls, 'editMessageText');
    assert.equal(cat.params.text, '45.000 ₫ · Phở — hạng mục?');
    tap(env, ask.message, press(ask, '45.000 ₫'));  // a double tap must not make it 45 million
    calls = tap(env, ask.message, press(cat, 'Ăn uống & đi chợ'));
    tap(env, ask.message, press(only1(calls, 'editMessageText'), 'Tiền mặt'));
    assert.equal(inbox(env)[0][2], 45000);
    const chat = only1(say(env, '5 phút nữa về'), 'sendMessage');
    assert.equal(only1(tap(env, chat.message, press(chat, 'Huỷ')), 'editMessageText').params.text, '✖️ Bỏ qua: 5 ₫ · Phút nữa về · Tiền mặt');
    assert.equal(inbox(env).length, 1);
  },
  telegram_other_chat_is_ignored_unless_the_bot_is_addressed() {
    const env = bot();
    assert.deepEqual(say(env, 'đón con chưa anh?'), []);
    assert.deepEqual(say(env, '/thang@OtherBot'), []);
    const hint = 'Gõ số tiền rồi nội dung, ví dụ: 45k phở tm. /huongdan để xem thêm.';
    assert.equal(only1(say(env, '@SoNhaMinhBot giúp với'), 'sendMessage').params.text, hint);
    assert.equal(only1(say(env, 'sao vậy', {reply: {message_id: 3, from: {id: 999, is_bot: true}}}), 'sendMessage').params.text, hint);
    assert.match(only1(say(env, '@SoNhaMinhBot 45k phở'), 'sendMessage').params.text, /^45\.000 ₫ · Phở/);
    assert.deepEqual(say(env, '45k phở', {from: {id: 7, is_bot: true, first_name: 'Other'}}), [], 'other bots are ignored');
  },
  telegram_guide_explains_privacy_mode() {
    const env = bot();
    env.tg.me.can_read_all_group_messages = false;
    let text = only1(say(env, '/start'), 'sendMessage').params.text;
    assert.match(text, /45k phở/);
    assert.match(text, /\/homnay {2}\/tuan {2}\/thang/);
    assert.match(text, /privacy mode[\s\S]*\/setprivacy[\s\S]*Disable[\s\S]*thêm lại/);
    env.tg.me.can_read_all_group_messages = true;
    text = only1(say(env, '/huongdan'), 'sendMessage').params.text;
    assert.match(text, /chưa thấy tin nhắn thường nào/, 'only commands seen so far: still a hint');
    say(env, 'đi chợ chưa?');
    text = only1(say(env, '/huongdan'), 'sendMessage').params.text;
    assert.doesNotMatch(text, /privacy/);
  },
  telegram_group_upgraded_to_supergroup_stays_paired() {
    const env = bot();
    say(env, '', {});  // a service message without text is ignored
    env.tg.updates.push({update_id: env.uid++, message: {message_id: env.mid++, from: LAN, chat: GROUP, migrate_to_chat_id: -100888}});
    poll(env);
    const big = {id: -100888, type: 'supergroup', title: 'Nhà mình'};
    assert.match(only1(say(env, '45k phở', {chat: big}), 'sendMessage').params.text, /hạng mục/);
  },
});

/** The report fixture: an iPhone entry the Mac has read, its mirror and summary, then entries in the group. */
function ledgerFixture() {
  const env = bot();
  const post = (device, rows, summary) => env.ctx.doPost({parameter: {k: env.secret}, postData: {contents: JSON.stringify(
    {a: 'mirror', device, rows, summary})}});
  const tx = (d, kind, amt, desc, cat, pay, src, ok, id, mac = 'MacBook Lan') => [d, kind, amt, desc, cat, pay, src, ok, mac, id];
  clock('2026-11-05T11:00:00Z');
  post('MacBook Hào', [tx('2026-11-04', 'Chi', 9999000, 'Tivi', 'Điện tử & phụ kiện', 'Thẻ Visa', 'Nhập tay', 'Có', 1, 'MacBook Hào')], []);
  clock('2026-11-05T12:00:00Z');
  env.ctx.doGet({parameter: {a: 'add', k: env.secret, so: '30000', d: 'Gửi xe', t: 'Tiền mặt', n: 'iPhone của Lan'}});
  clock('2026-11-05T12:10:00Z');
  env.ctx.doGet({parameter: {a: 'list', k: env.secret}});  // the Mac reads the inbox…
  clock('2026-11-05T12:11:00Z');
  post('MacBook Lan', [                                     // …and pushes its mirror, Gửi xe included
    tx('2026-11-01', 'Thu', 50000000, 'Lương', 'Lương', 'Chuyển khoản', 'Nhập tay', 'Có', 1),
    tx('2026-11-02', 'Chi', 1500000, 'Học phí', 'Học phí', 'Chuyển khoản', 'Nhập tay', 'Có', 2),
    tx('2026-11-03', 'Chi', 700000, 'Đi chợ', 'Ăn uống & đi chợ', 'Tiền mặt', 'Nhập tay', 'Có', 3),
    tx('2026-11-05', 'Chi', 30000, 'Gửi xe', 'Đi lại & xăng xe', 'Tiền mặt', 'iPhone', 'Có', 4),
    tx('2026-11-04', 'Chi', 99000, 'Đơn huỷ', 'Khác', '', 'Shopee', 'Không', 5),
    tx('2026-10-20', 'Chi', 465000, 'Kem', 'Mỹ phẩm & làm đẹp', 'Thẻ Visa', 'Shopee', 'Có', 6)],
  [['MacBook Lan', '2026-11', 'Ngân sách', 'Ăn uống & đi chợ', 1000000, ''], ['MacBook Lan', '2026-11', 'Ngân sách', 'Học phí', 1500000, ''],
   ['MacBook Lan', '2026-10', 'Ngân sách', 'Học phí', 999, ''],
   ['MacBook Lan', '2026-10', 'Ống heo', 'Bỏ ống heo', 4000000, ''], ['MacBook Lan', '2026-09', 'Ống heo', 'Bỏ ống heo', -1000000, ''],
   ['MacBook Lan', '2026-08', 'Ống heo', 'Bỏ ống heo', 3000000, ''], ['MacBook Lan', '2026-07', 'Ống heo', 'Bỏ ống heo', 2000000, '']]);
  clock('2026-11-05T12:20:00Z');
  env.warning = enter(env, '100k bún chả tm', 'Ăn uống & đi chợ');
  enter(env, '50k quà ck', 'Tự động');
  const wrong = enter(env, '200k nhầm visa', 'Khác');
  tap(env, {message_id: wrong.params.message_id, text: wrong.params.text}, press(wrong, 'Huỷ'));
  return env;
}

const ask = (env, cmd) => only1(say(env, cmd), 'sendMessage').params.text;

Object.assign(tests, {
  telegram_month_report_adds_inbox_rows_the_mac_has_not_read() {
    const env = ledgerFixture();
    assert.deepEqual(JSON.parse(env.store.MIRROR_PUSHES)['MacBook Lan'], {at: '2026-11-05T12:11:00', listed: '2026-11-05T12:10:00'});
    assert.equal(ask(env, '/thang'), [
      '📅 Tháng 11/2026',
      '💸 Chi 2.380.000 ₫ · 💰 Thu 50.000.000 ₫',
      '📌 Còn lại 47.620.000 ₫',
      '',
      'Theo hạng mục:',
      '🎓 Học phí: 1,5 tr (63%)',
      '🛒 Ăn uống & đi chợ: 800k (34%)',
      '⏳ Chưa phân loại (chờ Mac): 50k (2,1%)',
      '🚗 Đi lại & xăng xe: 30k (1,3%)',
      '',
      'Theo cách trả: 🏦 Chuyển khoản 1,6 tr · 💵 Tiền mặt 830k',
      '🧾 5 khoản chi, 1 khoản thu',
      '',
      'Số liệu tới lần Mac đồng bộ 05/11 12:11 + 2 khoản ghi sau đó'].join('\n'));
    const oct = ask(env, '/thang 10');
    assert.match(oct, /^📅 Tháng 10\/2026\n💸 Chi 465\.000 ₫ · 💰 Thu 0 ₫/);
    assert.match(oct, /💄 Mỹ phẩm & làm đẹp: 465k \(100%\)/);
    assert.match(oct, /Số liệu tới lần Mac đồng bộ 05\/11 12:11$/, 'nothing newer in October');
    assert.match(ask(env, '/thang 13'), /^Gõ \/thang/);
    assert.match(ask(env, '/thang 12'), /^📅 Tháng 12\/2025\nChưa có khoản nào\./, 'a later month means last year');
  },
  telegram_today_and_week_reports() {
    const env = ledgerFixture();
    const today = ask(env, '/homnay');
    assert.match(today, /^📅 Hôm nay 05\/11\n💸 Chi 180\.000 ₫ · 💰 Thu 0 ₫/);
    assert.match(today, /🧾 3 khoản chi\n/);
    const week = ask(env, '/tuan');
    assert.match(week, /^📅 Tuần này \(02\/11 – 05\/11\)\n💸 Chi 2\.380\.000 ₫ · 💰 Thu 0 ₫/, 'Monday to today: the salary on Sunday 1/11 is last week');
    assert.doesNotMatch(week, /Tivi|9\.999/, "the other Mac's mirror is not counted");
  },
  telegram_budget_report_and_warning_once_per_threshold() {
    const env = ledgerFixture();
    assert.equal(env.warning.params.text, '✓ Đã ghi 100.000 ₫ · Bún chả · 🛒 Ăn uống & đi chợ · Tiền mặt — Lan\n' +
      '⚠️ 🛒 Ăn uống & đi chợ đã dùng 80% ngân sách tháng (800k / 1 tr) — còn 200k');
    assert.equal(ask(env, '/ngansach'), ['🎯 Ngân sách tháng 11/2026', '🎓 Học phí: 1,5 tr / 1,5 tr (100%) ⚠️',
      '🛒 Ăn uống & đi chợ: 800k / 1 tr (80%) ⚠️', '', 'Số liệu tới lần Mac đồng bộ 05/11 12:11 + 2 khoản ghi sau đó'].join('\n'));
    assert.doesNotMatch(enter(env, '50k phở tm', 'Ăn uống & đi chợ').params.text, /ngân sách/, '80% was already said');
    const over = enter(env, '200k lẩu tm', 'Ăn uống & đi chợ').params.text.split('\n')[1];
    assert.match(over, /^🔴 🛒 Ăn uống & đi chợ đã vượt ngân sách tháng 50k \(1,\d tr \/ 1 tr\)$/);
    assert.doesNotMatch(enter(env, '10k trà đá tm', 'Ăn uống & đi chợ').params.text, /ngân sách/);
    assert.doesNotMatch(enter(env, '10k kẹo tm', 'Tự động').params.text, /ngân sách/, 'uncategorised: no budget to check');
    assert.match(ask(env, '/ngansach'), /🛒 Ăn uống & đi chợ: 1,1 tr \/ 1 tr \(106%\) 🔴/);
    clock('2026-12-02T12:00:00Z');
    assert.match(enter(env, '900k đi chợ tm', 'Ăn uống & đi chợ').params.text, /⚠️ 🛒 Ăn uống & đi chợ đã dùng 90%/, 'a new month warns again');
  },
  telegram_piggy_report() {
    const env = ledgerFixture();
    assert.equal(ask(env, '/ongheo'), ['🐷 Ống heo', '3 tháng gần nhất: 6.000.000 ₫', '6 tháng gần nhất: 8.000.000 ₫',
      'Tổng 4 tháng: 8.000.000 ₫', 'Tháng 10/2026: bỏ ống heo 4 tr', '', 'Số liệu tới lần Mac đồng bộ 05/11 12:11'].join('\n'));
  },
  telegram_reports_before_any_mac_push() {
    const env = bot();
    enter(env, '45k phở tm', 'Tự động');
    const text = ask(env, '/thang');
    assert.match(text, /⏳ Chưa phân loại \(chờ Mac\): 45k \(100%\)/);
    assert.match(text, /Chưa có số liệu từ Mac[\s\S]*chỉ tính 1 khoản/);
    assert.match(ask(env, '/ngansach'), /Chưa đặt ngân sách nào/);
    assert.match(ask(env, '/ongheo'), /chưa có tháng nào/);
  },
  telegram_scheduled_reports_go_out_once() {
    const env = ledgerFixture();
    say(env, `/ketnoi ${env.store.TG_PAIR_CODE}`, {chat: {id: 11, type: 'private'}});
    const sent = calls => calls.filter(c => c.method === 'sendMessage');
    clock('2026-11-08T19:59:00Z');
    assert.deepEqual(sent(poll(env)), []);
    clock('2026-11-08T20:00:00Z');
    let out = sent(poll(env));
    assert.deepEqual(out.map(c => c.params.chat_id), [GROUP.id, 11], 'every paired chat');
    assert.match(out[0].params.text, /^📊 Báo cáo tuần 02\/11 – 08\/11\n💸 Chi 2\.380\.000 ₫/);
    clock('2026-11-08T20:01:00Z');
    assert.deepEqual(sent(poll(env)), []);
    clock('2026-11-09T20:00:00Z');
    assert.deepEqual(sent(poll(env)), [], 'Monday');
    clock('2026-12-01T07:59:00Z');
    assert.deepEqual(sent(poll(env)), []);
    clock('2026-12-01T08:00:00Z');
    out = sent(poll(env));
    assert.equal(out.length, 2);
    assert.match(out[0].params.text, /^📊 Báo cáo tháng 11\/2026\n💸 Chi 2\.380\.000 ₫[\s\S]*\n\n🐷 Ống heo\n3 tháng gần nhất/);
    clock('2026-12-01T09:00:00Z');
    assert.deepEqual(sent(poll(env)), []);
  },
  telegram_polling_advances_the_offset_and_never_overlaps() {
    const env = bot();
    say(env, 'chào cả nhà');
    const offset = Number(env.store.TG_OFFSET);
    assert.equal(offset, env.uid);
    const gets = () => env.tg.calls.filter(c => c.method === 'getUpdates');
    poll(env);
    assert.equal(gets().at(-1).params.offset, offset);
    assert.equal(gets().at(-1).params.timeout, 0);
    assert.deepEqual([...gets().at(-1).params.allowed_updates], ['message', 'callback_query']);
    env.lock.userHeld = true;  // the previous minute's run is still going
    const before = env.tg.calls.length;
    env.ctx.pollTelegram();
    assert.equal(env.tg.calls.length, before, 'skipped');
    env.lock.userHeld = false;
    const onText = env.ctx.onText_;
    env.ctx.onText_ = () => { throw new Error('boom'); };
    say(env, '45k phở');
    env.ctx.onText_ = onText;
    assert.equal(Number(env.store.TG_OFFSET), env.uid, 'a failing update is skipped, not retried forever');
    assert.match(env.store.TG_LAST_ERROR, /boom/);
    assert.match(only1(say(env, '45k phở'), 'sendMessage').params.text, /hạng mục/);
    env.tg.webhook = true;  // someone set a webhook: the next run removes it
    poll(env);
    assert.equal(env.tg.calls.at(-1).method, 'deleteWebhook');
    assert.equal(env.lock.userHeld, false, 'the lock is released');
  },
  telegram_poll_never_throws() {
    const env = bot();
    env.tg.fail = 'throw';
    env.ctx.pollTelegram();
    env.tg.fail = 'html';
    env.ctx.pollTelegram();
    env.tg.fail = null;
    const openById = env.ctx.SpreadsheetApp.openById;
    env.ctx.SpreadsheetApp.openById = () => { throw new Error('Service Spreadsheets failed'); };
    clock('2026-11-08T20:00:00Z');
    say(env, '/thang');
    env.ctx.SpreadsheetApp.openById = openById;
    assert.match(env.store.TG_LAST_ERROR, /Service Spreadsheets failed/);
    env.ctx.logError_(new Error(`Address unavailable: https://api.telegram.org/bot${env.tg.token}/getUpdates`));
    assert.ok(!env.store.TG_LAST_ERROR.includes(env.tg.token), 'the token never reaches the log');
    assert.ok(!env.logs.some(l => l.join(' ').includes(env.tg.token)));
    delete env.store.TELEGRAM_TOKEN;
    const before = env.tg.calls.length;
    env.ctx.pollTelegram();
    assert.equal(env.tg.calls.length, before, 'no token: nothing to do');
  },
  list_leaves_out_cancelled_rows_and_names_them() {
    const {ctx, sheet, secret} = load();
    ctx.doGet({parameter: {a: 'add', k: secret, so: '45000', d: 'Phở'}});
    assert.equal(sheet.rows[1][7], 'iphone');
    sheet.rows.push(['t1', new Date(), 50000, 'Bún', 'Tiền mặt', 'Telegram · Lan', '', 'telegram', 'huỷ']);
    sheet.rows.push(['t2', new Date(), 60000, 'Cơm', '', 'Telegram · Lan', '', 'telegram', 'Hủy']);
    sheet.rows.push(['', '02/11/2026', '70k', 'Gõ tay rồi huỷ', '', '', '', '', 'đã huỷ']);
    sheet.rows.push(['t4', new Date(), 80000, 'Trà', '', 'Telegram · Hào', '', 'telegram', '']);
    const body = JSON.parse(ctx.doGet({parameter: {a: 'list', k: secret}}).body);
    assert.deepEqual(body.rows.map(r => r.description), ['Phở', 'Trà']);
    assert.equal(body.cancelled.length, 3);
    assert.deepEqual(body.cancelled.slice(0, 2), ['t1', 't2']);
    assert.equal(body.cancelled[2], sheet.rows[4][0], 'a hand-typed row gets its id before it is named');
    // Everything app 1.4.0 reads is still there; the rest is additive.
    for (const k of ['id', 'time', 'amount', 'description', 'account', 'by', 'category', 'row']) assert.ok(k in body.rows[0], k);
    assert.deepEqual([body.rows[0].channel, body.rows[1].channel], ['iphone', 'telegram']);
  },
  code_gs_categories_and_accounts_match_the_mac() {
    const {ctx} = load();
    const py = fs.readFileSync(new URL('../../db.py', import.meta.url), 'utf8');
    const cats = [...py.matchAll(/^\s*\("([^"]+)", "(expense|income)", "([^"]+)"/gm)].map(m => [m[3], m[1], m[2]]);
    assert.equal(cats.length, 15);
    assert.deepEqual(Array.from(ctx.CATS, c => [...c]), cats);
    const shortcut = fs.readFileSync(new URL('../../phone/make_shortcut.py', import.meta.url), 'utf8');
    assert.deepEqual([...ctx.ACCOUNTS], JSON.parse(shortcut.match(/^ACCOUNTS = (\[.*?\])/m)[1]));
  },
});

function ctx_cats(env) {
  return Array.from(env.ctx.CATS, c => c[0] + ' ' + c[1]);
}

if (process.argv[2] === '--html-to-text') {  // used by tests/test_apps_script.py to compare with parsers.html_to_text
  const {ctx} = load();
  process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0, 'utf8')).map(h => ctx.htmlToText(h))));
  process.exit(0);
}

Object.assign(tests, {
  bat_telegram_explains_a_missing_scope() {
    const {ctx, store} = load();
    store.TELEGRAM_TOKEN = '123:abc';
    ctx.UrlFetchApp = {fetch() { throw new Error('You do not have permission to call UrlFetchApp.fetch. Required permissions: https://www.googleapis.com/auth/script.external_request'); }};
    assert.throws(() => ctx.batTelegram(), /chưa được cấp quyền "Connect to an external service"/);
  },
});

Object.assign(tests, {
  kiem_tra_telegram_runs_without_throwing() {
    const {ctx, store, logs} = load();
    const text = () => logs.map(a => a.join(' '));
    ctx.kiemTraTelegram();                                   // no token: says so, does not throw
    assert.ok(text().some(l => /THIẾU/.test(l)));
    store.TELEGRAM_TOKEN = '123:abc';
    ctx.UrlFetchApp = {fetch: () => ({getContentText: () => JSON.stringify({ok: false, error_code: 401, description: 'Unauthorized'})})};
    ctx.kiemTraTelegram();
    assert.ok(text().some(l => /LỖI Unauthorized/.test(l)));
    assert.match(store.TG_LAST_ERROR || '', /getUpdates: Unauthorized/);  // a failing poll is no longer silent
  },
});

// ---------------------------------------------------------------- Code.gs 5: keywords from the Mac, fast replies

// As phone_inbox.keyword_rules sends them: longest keyword first.
const RULES = [['grabfood', 'Ăn uống & đi chợ', 'expense', '🛒'], ['pate meo', 'Nuôi mèo', 'expense', '🐱'],
  ['bun cha', 'Ăn uống & đi chợ', 'expense', '🛒'], ['cong ty', 'Lương', 'income', '💼'], ['pho bo', 'Ăn uống & đi chợ', 'expense', '🛒'],
  ['an trua', 'Ăn uống & đi chợ', 'expense', '🛒'], ['luong', 'Lương', 'income', '💼'], ['grab', 'Đi lại & xăng xe', 'expense', '🚗']];

function pushRules(env, rules = RULES, device = 'MacBook Lan', extra = {}) {
  return JSON.parse(env.ctx.doPost({parameter: {k: env.secret}, postData: {contents: JSON.stringify(
    {a: 'mirror', device, rows: [], summary: [], rules, ...extra})}}).body);
}

const advance = ms => setNow(Date.now() + ms);
const gets = (calls, from = 0) => calls.slice(from).filter(c => c.method === 'getUpdates');

/** An update that arrives `secs` after now, made when it arrives (so it can tap a message the bot sends meanwhile). */
function later(env, secs, make) {
  env.tg.later.push({at: Date.now() + secs * 1000, make: () => ({update_id: env.uid++, ...make()})});
}

const tapOn = (env, msg, data, from = LAN) => ({callback_query: {id: 'q' + env.uid, from, data,
  message: {message_id: msg.message_id, chat: GROUP, text: msg.text}}});
const lastSent = env => env.tg.calls.filter(c => c.method === 'sendMessage').at(-1).message;

Object.assign(tests, {
  telegram_keyword_and_known_payment_record_in_the_same_poll() {
    const env = bot();
    pushRules(env);
    let calls = say(env, '45k phở bò tm');
    const done = only1(calls, 'sendMessage');
    assert.deepEqual(calls.map(c => c.method), ['sendMessage'], 'no question, no edit');
    assert.equal(done.params.text, '✓ Đã ghi 45.000 ₫ · Phở bò · 🛒 Ăn uống & đi chợ · Tiền mặt — Lan');
    assert.equal(done.params.reply_parameters.message_id, env.mid - 1);
    const [row] = inbox(env);
    assert.deepEqual([row[2], row[3], row[4], row[5], row[6], row[7]],
      [45000, 'Phở bò', 'Tiền mặt', 'Telegram · Lan', '🛒 Ăn uống & đi chợ', 'telegram']);
    assert.deepEqual(buttons(done).map(b => [b.text, b.callback_data]),
      [['✏️ Đổi hạng mục', 'e|' + row[0]], ['↩️ Huỷ', 'u|' + row[0]]]);
    // No payment word: Lan's last one. Hào has none yet, so he is asked once.
    assert.match(only1(say(env, '30k bún chả'), 'sendMessage').params.text, /^✓ Đã ghi 30\.000 ₫ · Bún chả · 🛒 Ăn uống & đi chợ · Tiền mặt — Lan$/);
    const ask = only1(say(env, '50k phở bò', {from: HAO}), 'sendMessage');
    assert.equal(ask.params.text, '50.000 ₫ · Phở bò · 🛒 Ăn uống & đi chợ — trả bằng gì?');
    assert.equal(only1(tap(env, ask.message, press(ask, 'Chuyển khoản'), HAO), 'editMessageText').params.text,
      '✓ Đã ghi 50.000 ₫ · Phở bò · 🛒 Ăn uống & đi chợ · Chuyển khoản — Hào');
    assert.match(only1(say(env, '20k phở bò', {from: HAO}), 'sendMessage').params.text, /Chuyển khoản — Hào$/);
    assert.match(only1(say(env, '25k phở bò visa'), 'sendMessage').params.text, /Thẻ Visa — Lan$/);
    assert.match(only1(say(env, '26k phở bò'), 'sendMessage').params.text, /Thẻ Visa — Lan$/, 'the word becomes the new default');
    assert.deepEqual(JSON.parse(env.store.TG_PAY), {11: 'Thẻ Visa', 22: 'Chuyển khoản'});
    assert.equal(inbox(env).length, 6);
    assert.match(only1(say(env, '/huy'), 'sendMessage').params.text, /^↩️ Đã huỷ 26\.000 ₫ · Phở bò/, '/huy finds a direct entry');
  },
  telegram_no_keyword_shows_the_grid_then_one_tap_records() {
    const env = bot();
    pushRules(env);
    say(env, '45k phở bò tm');
    const ask = only1(say(env, '99k quà sinh nhật'), 'sendMessage');
    assert.equal(ask.params.text, '99.000 ₫ · Quà sinh nhật · Tiền mặt — hạng mục?');
    assert.equal(inbox(env).length, 1, 'nothing written before the tap');
    const calls = tap(env, ask.message, press(ask, 'Mẹ & bé'));
    assert.equal(calls[0].method, 'answerCallbackQuery');
    assert.equal(only1(calls, 'editMessageText').params.text, '✓ Đã ghi 99.000 ₫ · Quà sinh nhật · 🍼 Mẹ & bé · Tiền mặt — Lan');
    assert.deepEqual(inbox(env)[1].slice(2, 7), [99000, 'Quà sinh nhật', 'Tiền mặt', 'Telegram · Lan', '🍼 Mẹ & bé']);
    // Before the Mac sends keywords the bot asks, as Code.gs 4 did.
    const fresh = bot();
    assert.match(only1(say(fresh, '45k phở bò tm'), 'sendMessage').params.text, /hạng mục\?$/);
  },
  telegram_income_keyword_and_mac_categories() {
    const env = bot();
    pushRules(env);
    advance(1000);  // the reports count inbox rows newer than the last push
    assert.equal(only1(say(env, '15tr lương tháng 10 ck'), 'sendMessage').params.text,
      '✓ Đã ghi khoản thu 15.000.000 ₫ · Lương tháng 10 · 💼 Lương · Chuyển khoản — Lan');
    assert.match(only1(say(env, '45k ăn trưa công ty tm'), 'sendMessage').params.text, /· 🛒 Ăn uống & đi chợ ·/,
      'an expense keyword wins over a longer income one');
    assert.match(only1(say(env, '120k pate mèo'), 'sendMessage').params.text, /^✓ Đã ghi 120\.000 ₫ · Pate mèo · 🐱 Nuôi mèo · Tiền mặt/);
    assert.match(only1(say(env, '80k grabfood'), 'sendMessage').params.text, /🛒 Ăn uống/, 'longest keyword first');
    assert.match(only1(say(env, '80k grab về nhà'), 'sendMessage').params.text, /🚗 Đi lại/);
    assert.match(only1(say(env, '80k grabbike'), 'sendMessage').params.text, /hạng mục\?$/, 'whole words only');
    assert.deepEqual(inbox(env).map(r => r[6]), ['💼 Lương', '🛒 Ăn uống & đi chợ', '🐱 Nuôi mèo', '🛒 Ăn uống & đi chợ',
      '🚗 Đi lại & xăng xe']);
    const listed = JSON.parse(env.ctx.doGet({parameter: {a: 'list', k: env.secret}}).body).rows;
    assert.equal(listed[2].category, '🐱 Nuôi mèo', 'the Mac matches the name');
    assert.match(ask(env, '/homnay'), /🐱 Nuôi mèo: 120k/, 'reports know categories made on the Mac');
    assert.match(ask(env, '/homnay'), /💰 Thu 15\.000\.000 ₫/);
  },
  telegram_change_category_before_and_after_the_mac_imports() {
    const env = bot();
    pushRules(env);
    const done = only1(say(env, '45k phở bò tm'), 'sendMessage');
    const msg = {message_id: done.message.message_id, text: done.params.text};
    const id = inbox(env)[0][0];
    let calls = tap(env, msg, 'e|' + id);
    assert.equal(calls[0].method, 'answerCallbackQuery');
    let edit = only1(calls, 'editMessageText');
    assert.equal(edit.params.text, done.params.text + '\nĐổi sang hạng mục nào?');
    assert.equal(buttons(edit).at(-1).text, 'Giữ nguyên');
    assert.ok(buttons(edit).every(b => Buffer.byteLength(b.callback_data) <= 64));
    assert.deepEqual(buttons(only1(tap(env, msg, 'g|' + id), 'editMessageText')).map(b => b.text), ['✏️ Đổi hạng mục', '↩️ Huỷ']);
    calls = tap(env, msg, press(edit, 'Mẹ & bé'));
    edit = only1(calls, 'editMessageText');
    assert.equal(edit.params.text, '✓ Đã ghi 45.000 ₫ · Phở bò · 🍼 Mẹ & bé · Tiền mặt — Lan');
    assert.equal(inbox(env)[0][6], '🍼 Mẹ & bé');
    tap(env, msg, 'r|' + id + '|13');
    assert.equal(inbox(env)[0][6], '💼 Lương');
    assert.match(only1(say(env, '/huy'), 'sendMessage').params.text, /^↩️ Đã huỷ 45\.000 ₫ · Phở bò · 💼 Lương/);
    // A second entry, then the Mac reads the inbox: the row is in the Mac now and the Sheet's copy is never read again.
    const two = only1(say(env, '30k bún chả'), 'sendMessage');
    const msg2 = {message_id: two.message.message_id, text: two.params.text};
    const id2 = inbox(env)[1][0];
    advance(60e3);
    env.ctx.doGet({parameter: {a: 'list', k: env.secret}});
    edit = only1(tap(env, msg2, 'e|' + id2), 'editMessageText');
    assert.equal(edit.params.text, two.params.text + '\nMac đã lấy khoản này rồi: đổi hạng mục trong app trên Mac.');
    assert.deepEqual(buttons(edit).map(b => b.text), ['↩️ Huỷ']);
    tap(env, msg2, 'r|' + id2 + '|7');  // from a grid opened before the Mac read it
    assert.equal(inbox(env)[1][6], '🛒 Ăn uống & đi chợ', 'unchanged');
    const c = only1(tap(env, msg, 'e|' + id), 'editMessageText');
    assert.equal(c.params.text, '↩️ Đã huỷ: khoản thu 45.000 ₫ · Phở bò · 💼 Lương · Tiền mặt — Lan', 'a cancelled row');
  },
  telegram_button_taps_are_answered_once_and_never_record_twice() {
    const env = bot();
    let ask1 = only1(say(env, '45k phở'), 'sendMessage');
    // Two taps waiting for the same poll: the first is acted on, the second only answered.
    env.tg.updates.push({update_id: env.uid++, ...tapOn(env, ask1.message, press(ask1, 'Ăn uống & đi chợ'))});
    env.tg.updates.push({update_id: env.uid++, ...tapOn(env, ask1.message, press(ask1, 'Ăn uống & đi chợ'))});
    let calls = poll(env);
    assert.deepEqual(calls.map(c => [c.method, c.params.text]), [['answerCallbackQuery', undefined],
      ['editMessageText', '45.000 ₫ · Phở · 🛒 Ăn uống & đi chợ — trả bằng gì?'], ['answerCallbackQuery', undefined],
      ['editMessageText', '45.000 ₫ · Phở · 🛒 Ăn uống & đi chợ — trả bằng gì?']]);
    const pay = calls[1];
    env.tg.updates.push({update_id: env.uid++, ...tapOn(env, ask1.message, press(pay, 'Tiền mặt'))});
    env.tg.updates.push({update_id: env.uid++, ...tapOn(env, ask1.message, press(pay, 'Tiền mặt'))});
    calls = poll(env);
    assert.deepEqual(calls.map(c => c.method), ['answerCallbackQuery', 'editMessageText', 'answerCallbackQuery']);
    assert.equal(calls[2].params.text, 'Đã ghi rồi');
    assert.equal(inbox(env).length, 1);
    // ✖️ Huỷ, then a late tap on the same question.
    const ask2 = only1(say(env, '99k nhầm'), 'sendMessage');
    tap(env, ask2.message, press(ask2, 'Huỷ'));
    assert.equal(only1(tap(env, ask2.message, press(ask2, 'Khác')), 'answerCallbackQuery').params.text, 'Đã bỏ qua rồi');
    // The question outlived CacheService (6 hours, or evicted earlier): say so instead of ignoring the tap.
    const ask3 = only1(say(env, '70k bún'), 'sendMessage');
    for (const k of Object.keys(env.cache.items)) if (k.startsWith('tg:')) delete env.cache.items[k];
    calls = tap(env, ask3.message, press(ask3, 'Khác'));
    assert.equal(calls[0].method, 'answerCallbackQuery');
    assert.match(calls[0].params.text, /chưa ghi.*6 giờ/);
    assert.equal(only1(calls, 'editMessageText').params.text,
      '⌛ Chưa ghi: 70.000 ₫ · Bún · Tiền mặt\nBot chỉ nhớ câu hỏi trong 6 giờ. Gõ lại nếu cần.');
    assert.equal(only1(calls, 'editMessageText').params.reply_markup, undefined, 'the stale buttons go away');
    assert.equal(inbox(env).length, 1);
  },
  telegram_active_conversation_is_answered_within_the_same_run() {
    const env = bot({fast: true});
    const start = Date.now();
    const before = env.tg.calls.length;
    env.tg.updates.push({update_id: env.uid++, message: {message_id: env.mid++, from: LAN, chat: GROUP, date: 0, text: '45k phở'}});
    // Lan taps a category 10 s after the question, then cash 4 s later, then taps cash again: all in this one run.
    later(env, 10, () => tapOn(env, lastSent(env), 'c|' + (env.mid - 1) + '|4'));
    later(env, 14, () => tapOn(env, lastSent(env), 'p|' + (env.mid - 1) + '|0'));
    later(env, 15, () => tapOn(env, lastSent(env), 'p|' + (env.mid - 1) + '|0'));
    env.ctx.pollTelegram();
    const calls = env.tg.calls.slice(before);
    // Each long poll returns when a tap arrives (at 10, 14, 15 s), then waits out the run: 15 → 40 s, 40 → 50 s.
    assert.deepEqual(gets(calls).map(c => c.params.timeout), [0, 25, 25, 25, 25, 10]);
    assert.equal(inbox(env).length, 1, 'recorded in the run that saw the message');
    assert.equal(inbox(env)[0][6], '🛒 Ăn uống & đi chợ');
    const answers = calls.filter(c => c.method === 'answerCallbackQuery');
    assert.deepEqual(answers.map(c => c.params.text), [undefined, undefined, 'Đã ghi rồi']);
    assert.equal(Date.now() - start, 50e3, 'stops at 50 s, before the next minute');
    assert.equal(JSON.parse(env.store.TG_FAST).ms, 50e3);
    assert.equal(env.lock.userHeld, false);
  },
  telegram_idle_runs_make_one_quick_call_and_the_window_closes() {
    const env = bot({fast: true});
    const start = Date.now();
    let n = env.tg.calls.length;
    env.ctx.pollTelegram();
    assert.deepEqual(gets(env.tg.calls, n).map(c => c.params.timeout), [0]);
    assert.equal(Date.now(), start);
    env.store.TG_ACTIVE_AT = String(Date.now() - 100e3);  // the last message came 100 s ago: 20 s of window left
    n = env.tg.calls.length;
    env.ctx.pollTelegram();
    assert.deepEqual(gets(env.tg.calls, n).map(c => c.params.timeout), [0, 20]);
    assert.equal(Date.now(), start + 20e3);
    n = env.tg.calls.length;
    env.ctx.pollTelegram();
    assert.deepEqual(gets(env.tg.calls, n).map(c => c.params.timeout), [0], 'closed');
    // A message in a quiet minute opens it again for the rest of the run.
    say(env, 'chào cả nhà');
    assert.equal(Date.now(), start + 20e3 + 50e3);
    advance(10e3);
    n = env.tg.calls.length;
    env.ctx.pollTelegram();
    assert.deepEqual(gets(env.tg.calls, n).map(c => c.params.timeout), [0, 25, 25], 'the next minute, 60 s after it');
    advance(10e3);
    n = env.tg.calls.length;
    env.ctx.pollTelegram();
    assert.deepEqual(gets(env.tg.calls, n).map(c => c.params.timeout), [0], '120 s after it');
  },
  telegram_fast_replies_stop_at_the_daily_cap_and_start_again_tomorrow() {
    const env = bot({fast: true});
    env.store.TG_FAST = JSON.stringify({day: '2026-11-05', ms: 40 * 60e3 - 10e3});
    const start = Date.now();
    say(env, 'chào');
    assert.equal(Date.now() - start, 10e3, 'only the 10 s left today');
    assert.deepEqual(JSON.parse(env.store.TG_FAST), {day: '2026-11-05', ms: 40 * 60e3});
    let n = env.tg.calls.length;
    say(env, 'chào nữa');
    assert.deepEqual(gets(env.tg.calls, n).map(c => c.params.timeout), [0], 'one quick call a minute, as Code.gs 4');
    env.ctx.kiemTraTelegram();
    assert.ok(env.logs.some(l => /Trả lời nhanh hôm nay: 40\/40 phút · hết hạn mức/.test(l.join(' '))));
    clock('2026-11-06T00:05:00Z');
    say(env, 'sáng rồi');
    assert.deepEqual(JSON.parse(env.store.TG_FAST), {day: '2026-11-06', ms: 50e3});
    env.store.TG_FAST_MINUTES = '0';
    n = env.tg.calls.length;
    say(env, 'tắt');
    assert.deepEqual(gets(env.tg.calls, n).map(c => c.params.timeout), [0]);
  },
  telegram_long_poll_network_error_ends_the_run_quietly() {
    const env = bot({fast: true});
    const fetch = env.tg.app.fetch;
    env.tg.app.fetch = (url, opts) => {
      if (/getUpdates/.test(url) && JSON.parse(opts.payload).timeout > 0) throw new Error(`Timeout: ${url}`);
      return fetch(url, opts);
    };
    const n = env.tg.calls.length;
    say(env, '45k phở');
    env.tg.app.fetch = fetch;
    assert.equal(gets(env.tg.calls, n).length, 1, 'the throwing call is not recorded by the fake');
    assert.match(env.store.TG_LAST_ERROR, /getUpdates: Timeout/);
    assert.ok(!env.store.TG_LAST_ERROR.includes(env.tg.token));
    assert.equal(env.lock.userHeld, false);
  },
  mirror_stores_the_keywords_of_the_last_pushing_mac() {
    const env = bot();
    assert.deepEqual(pushRules(env), {ok: true, rows: 0, summary: 0});
    const tab = env.ss.tabs['Từ khoá'];
    assert.ok(tab.hidden);
    assert.deepEqual(tab.rows[0], ['Từ khoá', 'Hạng mục', 'Loại', 'Biểu tượng']);
    assert.deepEqual(tab.rows.slice(1), RULES);
    assert.equal(JSON.parse(env.store.TG_RULES).n, RULES.length);
    tab.rows[1][0] = 'sửa tay';
    pushRules(env);
    assert.equal(tab.rows[1][0], 'sửa tay', 'unchanged keywords: the tab is not rewritten');
    pushRules(env, RULES, 'MacBook Lan', {rules: undefined});
    assert.equal(JSON.parse(env.store.TG_RULES).n, RULES.length, 'a push without keywords (app 1.4.0) keeps them');
    pushRules(env, [['tra sua', 'Ăn uống & đi chợ', 'expense', '🛒']], 'MacBook Hào');
    assert.deepEqual(tab.rows.slice(1), [['tra sua', 'Ăn uống & đi chợ', 'expense', '🛒']]);
    assert.equal(JSON.parse(env.store.TG_RULES).device, 'MacBook Hào');
    assert.match(only1(say(env, '45k phở bò tm'), 'sendMessage').params.text, /hạng mục\?$/, "the last Mac's keywords");
    delete env.cache.items.rules;  // CacheService forgot: read the tab
    env.ctx.rulesMemo_ = null;
    assert.match(only1(say(env, '30k trà sữa tm'), 'sendMessage').params.text, /^✓ Đã ghi/);
    const many = Array.from({length: 3000}, (_, i) => ['tu khoa so ' + i, 'Khác', 'expense', '📦']);
    pushRules(env, many);
    assert.equal(env.cache.items.rules, undefined, 'over 100 KB: not cached');
    env.ctx.rulesMemo_ = null;
    assert.match(only1(say(env, '30k tu khoa so 2999 tm'), 'sendMessage').params.text, /📦 Khác/);
  },
  kiem_tra_telegram_reports_keywords_and_fast_mode() {
    const env = bot({fast: true});
    env.ctx.kiemTraTelegram();
    const text = () => env.logs.map(a => a.join(' ')).join('\n');
    assert.match(text(), /Từ khoá từ Mac: %s chưa có/);
    assert.match(text(), /Trả lời nhanh hôm nay: 0\/40 phút · chờ/);
    env.logs.length = 0;
    pushRules(env);
    say(env, 'chào');
    env.ctx.kiemTraTelegram();
    assert.match(text(), /Từ khoá từ Mac: %s 8 \(máy MacBook Lan, /);
    assert.match(text(), /Trả lời nhanh hôm nay: 1\/40 phút · nhanh/);
  },
});

if (process.argv[2] === '--categorize') {  // tests/test_apps_script.py: the port against rules.categorize
  const {ctx} = load();
  const {rules, texts} = JSON.parse(fs.readFileSync(0, 'utf8'));
  process.stdout.write(JSON.stringify(texts.map(t => [ctx.normalize_(t),
    ...['expense', 'income'].map(k => (ctx.categorize_(t, k, rules) || [null, null])[1])])));
  process.exit(0);
}
if (process.argv[2] === '--mirror') {  // tests/test_apps_script.py: the Mac's real payload against this Code.gs (CODE_GS)
  const {ctx, secret, ss} = load();
  const reply = JSON.parse(ctx.doPost({parameter: {k: secret}, postData: {contents: fs.readFileSync(0, 'utf8')}}).body);
  const tab = ss.tabs['Từ khoá'];
  process.stdout.write(JSON.stringify({reply, version: ctx.SCRIPT_VERSION, tx: ss.tabs['Giao dịch'].rows.length - 1,
    keywords: tab ? tab.rows.length - 1 : null, rules: typeof ctx.rules_ === 'function' ? ctx.rules_() : null}));
  process.exit(0);
}

const only = process.argv[2];
const NOW = Date.now;  // Telegram tests move the clock; each test starts from the same instant
let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  if (only && name !== only) continue;
  Date.now = NOW;
  try { fn(); console.log('ok', name); } catch (e) { failed++; console.log('FAIL', name, e.message); }
}
Date.now = NOW;
process.exit(failed ? 1 : 0);
