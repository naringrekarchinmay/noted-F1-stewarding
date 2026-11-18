// Noted: friends' steward-mode votes. Cloudflare Pages Function at /api/votes, D1 binding env.DB.
//   GET  /api/votes?ruling=<int>                 -> {"ruling", "total", "counts"}
//   POST {"ruling": int, "voter": str, "choice": str}  (upsert, then the same shape as GET)
// Same-origin only: no CORS headers are ever sent, and a POST must be JSON, which a plain
// cross-site form cannot send, so another site cannot cast votes from a visitor's browser.

const CHOICES = [
  "NFA", "Warning", "Reprimand", "Fine", "5 s", "10 s",
  "Drive-thru", "Stop-go", "Grid drop", "DSQ",
];
const MAX_BODY = 1024; // bytes
const VOTER = /^[A-Za-z0-9_-]{8,64}$/;
const RULING_PARAM = /^[1-9][0-9]{0,6}$/; // 1 .. 9999999

const UPSERT =
  "INSERT INTO votes (ruling, voter, choice, at) VALUES (?1, ?2, ?3, ?4) " +
  "ON CONFLICT (ruling, voter) DO UPDATE SET choice = excluded.choice, at = excluded.at";
const COUNT = "SELECT choice, COUNT(*) AS n FROM votes WHERE ruling = ?1 GROUP BY choice";

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

const bad = (error, status = 400) => json({ error }, status);

function validRuling(n) {
  return typeof n === "number" && Number.isInteger(n) && n > 0 && n < 1e7;
}

async function tally(db, ruling) {
  const { results } = await db.prepare(COUNT).bind(ruling).all();
  const counts = {};
  let total = 0;
  for (const row of results || []) {
    counts[row.choice] = row.n;
    total += row.n;
  }
  return { ruling, total, counts };
}

export async function onRequestGet({ request, env }) {
  const raw = new URL(request.url).searchParams.get("ruling");
  if (raw === null || !RULING_PARAM.test(raw)) return bad("bad ruling");
  return json(await tally(env.DB, Number(raw)));
}

export async function onRequestPost({ request, env }) {
  if (!/^application\/json\b/i.test(request.headers.get("Content-Type") || "")) return bad("json only", 415);
  const declared = Number(request.headers.get("Content-Length"));
  if (declared > MAX_BODY) return bad("body too large", 413);
  const bytes = await request.arrayBuffer();
  if (bytes.byteLength > MAX_BODY) return bad("body too large", 413);

  let body;
  try {
    body = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return bad("bad json");
  }
  if (body === null || typeof body !== "object" || Array.isArray(body)) return bad("bad json");

  const { ruling, voter, choice } = body;
  if (!validRuling(ruling)) return bad("bad ruling");
  if (typeof voter !== "string" || !VOTER.test(voter)) return bad("bad voter");
  if (typeof choice !== "string" || !CHOICES.includes(choice)) return bad("bad choice");

  await env.DB.prepare(UPSERT).bind(ruling, voter, choice, new Date().toISOString()).run();
  return json(await tally(env.DB, ruling));
}
