/**
 * Timeline analytics collector — Cloudflare Worker scaffold.
 *
 * Receives the tiny JSON events the client's track() sends (round results and
 * game completions) and writes them to Workers Analytics Engine, which gives
 * per-puzzle score distributions for free-tier volumes. That distribution is
 * what tunes the decay constant and the difficulty curve (PRD §8).
 *
 * Deploy (requires a Cloudflare account; not done automatically):
 *   1. wrangler init timeline-analytics && copy this file in as src/index.js
 *   2. In wrangler.toml add:
 *        [[analytics_engine_datasets]]
 *        binding = "GAME_EVENTS"
 *   3. wrangler deploy, then set CONFIG.analyticsEndpoint in app.js to the
 *      worker URL.
 *
 * Events accepted (see track() in app.js):
 *   {e:"round",    d:"2026-07-21", n:1, r:1, err:4, pts:3567}
 *   {e:"complete", d:"2026-07-21", n:1, total:15573}
 *   {e:"share",    d:"2026-07-21", n:1}
 *
 * No cookies, no IPs stored, no user identifiers: each event is an anonymous
 * counter increment. Keep it that way — it is why this needs no consent UI.
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }
    if (request.method !== "POST") {
      return new Response("POST only", { status: 405, headers: CORS });
    }

    let ev;
    try {
      ev = await request.json();
    } catch {
      return new Response("bad json", { status: 400, headers: CORS });
    }

    const kind = String(ev.e || "");
    if (!["round", "complete", "share"].includes(kind)) {
      return new Response("unknown event", { status: 400, headers: CORS });
    }

    env.GAME_EVENTS.writeDataPoint({
      // blobs: dimensions to slice by; doubles: values to aggregate.
      blobs: [kind, String(ev.d || ""), String(ev.n || 0), String(ev.r || 0)],
      doubles: [Number(ev.err ?? -1), Number(ev.pts ?? ev.total ?? -1)],
      indexes: [String(ev.n || 0)], // sample key: the puzzle number
    });

    return new Response("ok", { headers: CORS });
  },
};
