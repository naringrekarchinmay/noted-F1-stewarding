// Tests for votes.js, kept outside functions/ so Pages never routes them.
// Run from the repo root: node --test cloudflare/test/votes.test.mjs (pytest runs it too)
import { test } from "node:test";
import assert from "node:assert/strict";
import { onRequestGet, onRequestPost } from "../functions/api/votes.js";

// A tiny in-memory stand-in for D1 that knows only the two statements votes.js runs,
// with D1's return shapes: all() -> { results: [...] }, run() -> { success, meta }.
function fakeD1() {
  const rows = new Map(); // "ruling|voter" -> { ruling, voter, choice, at }
  const handlers = {
    "INSERT INTO votes": (ruling, voter, choice, at) => {
      rows.set(`${ruling}|${voter}`, { ruling, voter, choice, at });
      return [];
    },
    "SELECT choice, COUNT(*)": (ruling) => {
      const n = new Map();
      for (const r of rows.values()) if (r.ruling === ruling) n.set(r.choice, (n.get(r.choice) || 0) + 1);
      return [...n].map(([choice, count]) => ({ choice, n: count }));
    },
  };
  return {
    rows,
    prepare(sql) {
      const key = Object.keys(handlers).find((k) => sql.startsWith(k));
      if (!key) throw new Error(`fake D1: unexpected SQL: ${sql}`);
      let args = [];
      const stmt = {
        bind(...a) {
          if (a.some((v) => v === undefined)) throw new Error("fake D1: undefined bind value");
          args = a;
          return stmt;
        },
        async run() { handlers[key](...args); return { success: true, meta: {} }; },
        async all() { return { success: true, results: handlers[key](...args), meta: {} }; },
        async first() { return handlers[key](...args)[0] ?? null; },
      };
      return stmt;
    },
  };
}

const URL_BASE = "https://noted.example/api/votes";
const VOTER = "abcDEF12_-xyz";

function get(env, query) {
  return onRequestGet({ request: new Request(`${URL_BASE}${query}`), env });
}

function post(env, body, headers = {}) {
  const raw = typeof body === "string" ? body : JSON.stringify(body);
  const request = new Request(URL_BASE, {
    method: "POST", body: raw, headers: { "Content-Type": "application/json", ...headers },
  });
  return onRequestPost({ request, env });
}

async function expectOk(res) {
  assert.equal(res.status, 200);
  checkHeaders(res);
  return res.json();
}

async function expectError(res, status = 400) {
  assert.equal(res.status, status);
  checkHeaders(res);
  const body = await res.json();
  assert.equal(typeof body.error, "string");
  return body;
}

function checkHeaders(res) {
  assert.equal(res.headers.get("cache-control"), "no-store");
  assert.match(res.headers.get("content-type"), /^application\/json/);
  for (const name of res.headers.keys()) assert.ok(!name.startsWith("access-control-"), `unexpected ${name}`);
}

test("GET on a ruling with no votes", async () => {
  const env = { DB: fakeD1() };
  assert.deepEqual(await expectOk(await get(env, "?ruling=100")), { ruling: 100, total: 0, counts: {} });
});

test("GET counts votes for that ruling only", async () => {
  const env = { DB: fakeD1() };
  await post(env, { ruling: 7, voter: "voter-aaaa", choice: "5 s" });
  await post(env, { ruling: 7, voter: "voter-bbbb", choice: "5 s" });
  await post(env, { ruling: 7, voter: "voter-cccc", choice: "DSQ" });
  await post(env, { ruling: 8, voter: "voter-aaaa", choice: "NFA" });
  assert.deepEqual(await expectOk(await get(env, "?ruling=7")), { ruling: 7, total: 3, counts: { "5 s": 2, "DSQ": 1 } });
});

test("POST stores a vote and returns the tally", async () => {
  const env = { DB: fakeD1() };
  const body = await expectOk(await post(env, { ruling: 100, voter: VOTER, choice: "Drive-thru" }));
  assert.deepEqual(body, { ruling: 100, total: 1, counts: { "Drive-thru": 1 } });
  const row = env.DB.rows.get(`100|${VOTER}`);
  assert.equal(row.choice, "Drive-thru");
  assert.match(row.at, /^\d{4}-\d\d-\d\dT.*Z$/);
});

test("POST again by the same voter replaces the vote", async () => {
  const env = { DB: fakeD1() };
  await post(env, { ruling: 100, voter: VOTER, choice: "Fine" });
  const body = await expectOk(await post(env, { ruling: 100, voter: VOTER, choice: "Stop-go" }));
  assert.deepEqual(body, { ruling: 100, total: 1, counts: { "Stop-go": 1 } });
  assert.equal(env.DB.rows.size, 1);
});

test("every one of the ten choices is accepted", async () => {
  const env = { DB: fakeD1() };
  const choices = ["NFA", "Warning", "Reprimand", "Fine", "5 s", "10 s", "Drive-thru", "Stop-go", "Grid drop", "DSQ"];
  for (const [i, choice] of choices.entries()) {
    await expectOk(await post(env, { ruling: 1, voter: `voter-${i}xxxx`, choice }));
  }
  const body = await expectOk(await get(env, "?ruling=1"));
  assert.equal(body.total, 10);
});

test("ruling boundaries: 1 and 9999999 are accepted", async () => {
  const env = { DB: fakeD1() };
  for (const ruling of [1, 9999999]) {
    await expectOk(await post(env, { ruling, voter: VOTER, choice: "NFA" }));
    assert.equal((await expectOk(await get(env, `?ruling=${ruling}`))).total, 1);
  }
});

test("GET rejects a missing or malformed ruling", async () => {
  const env = { DB: fakeD1() };
  for (const q of ["", "?ruling=", "?ruling=0", "?ruling=-1", "?ruling=1.5", "?ruling=1e3", "?ruling=10000000",
    "?ruling=%205", "?ruling=5abc", "?ruling=007", "?ruling=abc"]) {
    assert.deepEqual(await expectError(await get(env, q)), { error: "bad ruling" }, q);
  }
});

test("POST rejects a bad ruling", async () => {
  const env = { DB: fakeD1() };
  for (const ruling of [0, -1, 1.5, 1e7, "5", null, undefined, true, NaN]) {
    assert.deepEqual(await expectError(await post(env, { ruling, voter: VOTER, choice: "NFA" })), { error: "bad ruling" }, String(ruling));
  }
  assert.equal(env.DB.rows.size, 0);
});

test("POST rejects a bad voter", async () => {
  const env = { DB: fakeD1() };
  for (const voter of ["a".repeat(7), "a".repeat(65), "has space!", "voter/../x", "voter.12345", 12345678, null, undefined]) {
    assert.deepEqual(await expectError(await post(env, { ruling: 1, voter, choice: "NFA" })), { error: "bad voter" }, String(voter));
  }
  await expectOk(await post(env, { ruling: 1, voter: "a".repeat(8), choice: "NFA" }));
  await expectOk(await post(env, { ruling: 1, voter: "a".repeat(64), choice: "NFA" }));
});

test("POST rejects a bad choice", async () => {
  const env = { DB: fakeD1() };
  for (const choice of ["5 S", "nfa", "5s", " DSQ", "constructor", "toString", "", null, undefined, 5, ["NFA"]]) {
    assert.deepEqual(await expectError(await post(env, { ruling: 1, voter: VOTER, choice })), { error: "bad choice" }, String(choice));
  }
  assert.equal(env.DB.rows.size, 0);
});

test("POST rejects bad or non-object JSON", async () => {
  const env = { DB: fakeD1() };
  for (const raw of ["", "{", "not json", "null", "[]", "42", '"str"', "true"]) {
    assert.deepEqual(await expectError(await post(env, raw)), { error: "bad json" }, raw);
  }
});

test("POST rejects a body over 1 KB", async () => {
  const env = { DB: fakeD1() };
  const big = JSON.stringify({ ruling: 1, voter: VOTER, choice: "NFA", pad: "x".repeat(1100) });
  assert.deepEqual(await expectError(await post(env, big), 413), { error: "body too large" });
  // multi-byte characters: under 1024 characters but over 1024 bytes
  const wide = JSON.stringify({ ruling: 1, voter: VOTER, choice: "NFA", pad: "é".repeat(600) });
  assert.ok(wide.length < 1024);
  await expectError(await post(env, wide), 413);
  // a declared Content-Length over the limit is refused before reading
  await expectError(await post(env, { ruling: 1, voter: VOTER, choice: "NFA" }, { "Content-Length": "5000" }), 413);
  assert.equal(env.DB.rows.size, 0);
});

test("POST without a JSON content type is refused, so a cross-site form cannot vote", async () => {
  for (const type of ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x"]) {
    const res = await post({ DB: fakeD1() }, { ruling: 5, voter: VOTER, choice: "5 s" }, { "Content-Type": type });
    assert.equal(res.status, 415, type);
  }
});
