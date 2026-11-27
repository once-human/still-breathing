import "server-only";
import { createHash } from "node:crypto";
import { exec, row, rows } from "@/lib/admin/db";
import { kv } from "@/lib/shop/kv";
import { isBotAgent, isDatacentreTown, notOurPage } from "./bots";
import { KEEP_DAYS, LIVE_SECONDS, MAX_BOT_PAGES, MAX_EVENTS, STEPS, botName, cleanPath, isTerminal, refHost, type EventRow, type PersonRow, type Step, type TrackBatch, type VisitRow } from "./shared";
import { deviceName, geoOf } from "./ua";

/**
 * The visitor log, server side: visits (one row each: where from, what device, how long) and their events (pages in
 * order with time on screen and how far down, links out, shop steps). Never an IP address. "visitor" is a random code
 * the browser makes for itself. Programs are logged from src/proxy.ts, one row a day per program. Every visit is kept
 * in full for KEEP_DAYS, then folded into daily counts and deleted.
 */
const TZ = "Asia/Kolkata";
const host = (h: unknown) => (typeof h === "string" && /^[a-z0-9._-]{1,80}$/i.test(h) ? h.toLowerCase() : null);
const screen = (s: unknown) => (s === "phone" || s === "tablet" || s === "desktop" ? s : null);
const clip = (s: unknown, n: number) => (typeof s === "string" && s.trim() ? s.trim().replace(/[\u0000-\u001f<>]/g, " ").slice(0, n) : null);
const DESIGN = /^[a-z0-9-]{1,40}$/;
const SIZE = /^[A-Z0-9]{1,4}$/;

/** The SHA-256 of a browser's code: what the admin shows (12 characters of it) to tell people apart. */
export const personHash = (code: string) => createHash("sha256").update(code, "utf8").digest("hex");

/* ---- writing ---- */

/** A batch from a browser: the visit, and whatever happened since the last batch. */
export async function record(req: Request, b: TrackBatch): Promise<boolean> {
  const ua = req.headers.get("user-agent");
  const g = geoOf(req);
  const programUA = isBotAgent(ua);
  const headers = notOurPage(req);
  const farm = isDatacentreTown(g.city);
  const kind = programUA || b.bot || !b.human || headers || farm ? "bot" : "person";
  const reason = programUA ? `says it's a program (${botName(ua)})` : b.bot ? clip(b.bot, 80) : headers ? headers : farm ? `from a cloud datacentre town (${g.city})` : !b.human ? "didn't move, scroll or tap" : null;
  const events = b.events
    .filter((e) => Number.isInteger(e.seq) && e.seq >= 0 && e.seq < MAX_EVENTS && ["page", "click", "step"].includes(e.type))
    // the admin and the API are never visits, whatever a browser sends
    .filter((e) => typeof e.path !== "string" || !/^\/(admin|api)(\/|$)/.test(e.path))
    .slice(0, 100)
    .map((e) => {
      const step = e.type === "step" && (STEPS as readonly string[]).includes(String(e.step)) ? (e.step as Step) : null;
      return {
        seq: e.seq,
        // The browser's clock can be off; never in the future.
        at: new Date(Math.min(Date.now(), Number(e.at) || Date.now())).toISOString(),
        type: e.type,
        path: cleanPath(String(e.path ?? "/")),
        detail: clip(e.detail, e.type === "step" ? 60 : 200),
        ms: Number.isFinite(e.ms) ? Math.max(0, Math.min(86_400_000, Math.round(e.ms!))) : null,
        scroll: Number.isFinite(e.scroll) ? Math.max(0, Math.min(100, Math.round(e.scroll!))) : null,
        step,
        design: step && typeof e.design === "string" && DESIGN.test(e.design) ? e.design : null,
        size: step && typeof e.size === "string" && SIZE.test(e.size) ? e.size : null,
      };
    })
    .filter((e) => e.type !== "step" || e.step);

  // A browser that just asked to be forgotten stays forgotten, even if a batch was still on its way.
  if (await kv<string | null>("GET", `track:forgot:${b.v}`).catch(() => null)) return false;
  const owner = await row<{ visitor: string | null }>(
    `INSERT INTO visits (id, visitor, kind, reason, city, region, country, device, lang, screen, referrer)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
     ON CONFLICT (id) DO UPDATE SET
       last_at = now(),
       kind = CASE WHEN visits.kind = 'person' OR EXCLUDED.kind = 'person' THEN 'person' ELSE 'bot' END,
       reason = CASE WHEN visits.kind = 'person' OR EXCLUDED.kind = 'person' THEN NULL ELSE EXCLUDED.reason END,
       referrer = coalesce(visits.referrer, EXCLUDED.referrer)
     RETURNING visitor`,
    [b.s, b.v, kind, reason, g.city, g.region, g.country, programUA ? botName(ua) : deviceName(ua), clip(b.lang, 16), screen(b.screen), host(b.ref)],
  );
  // A visit belongs to the browser that started it.
  if (!owner || owner.visitor !== b.v) return false;
  if (events.length) {
    await exec(
      `INSERT INTO visit_events (visit, seq, at, type, path, detail, ms, scroll, step, design, size)
       SELECT $1, x.seq, x.at, x.type, x.path, x.detail, x.ms, x.scroll, x.step, x.design, x.size
       FROM json_to_recordset($2::json) AS x(seq int, at timestamptz, type text, path text, detail text, ms int, scroll smallint, step text, design text, size text)
       ON CONFLICT (visit, seq) DO UPDATE SET ms = coalesce(EXCLUDED.ms, visit_events.ms), scroll = greatest(EXCLUDED.scroll, visit_events.scroll)`,
      [b.s, JSON.stringify(events)],
    );
    await exec(
      `UPDATE visits SET
         pages = (SELECT count(*) FROM visit_events WHERE visit = $1 AND type = 'page'),
         active_ms = (SELECT coalesce(sum(ms), 0) FROM visit_events WHERE visit = $1 AND type = 'page')
       WHERE id = $1`,
      [b.s],
    );
  }
  return true;
}

/** A program asking for a page (from the proxy). One row per program, per country, per day. */
export async function recordBot(req: Request, path: string): Promise<void> {
  const ua = req.headers.get("user-agent");
  const name = botName(ua);
  const g = geoOf(req);
  const day = new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date());
  const id = `bot:${day}:${name}:${g.country ?? "-"}`.slice(0, 120);
  const reason = isTerminal(name) ? "a terminal (curl and friends)" : "says it's a program";
  await exec(
    `WITH v AS (
       INSERT INTO visits (id, visitor, kind, reason, city, region, country, device, referrer, pages)
       VALUES ($1, NULL, 'bot', $2, $3, $4, $5, $6, $7, 1)
       ON CONFLICT (id) DO UPDATE SET last_at = now(), pages = visits.pages + 1
       RETURNING pages
     )
     INSERT INTO visit_events (visit, seq, at, type, path, detail)
     SELECT $1, pages - 1, now(), 'page', $8, $9 FROM v WHERE pages <= ${MAX_BOT_PAGES}
     ON CONFLICT DO NOTHING`,
    [id, reason, g.city, g.region, g.country, name, refHost(req.headers.get("referer")), cleanPath(path), req.method === "GET" ? null : req.method],
  );
}

/* ---- reading ---- */

type Raw = {
  id: string; visitor: string | null; person: string | null; kind: "person" | "bot"; reason: string | null; started_at: string; last_at: string;
  city: string | null; region: string | null; country: string | null; device: string | null; lang: string | null; screen: string | null; referrer: string | null;
  pages: number; active_ms: number; trail: string[] | null; reached: Step[] | null; shirts: string[] | null; nth: number | null;
};
const toRow = (r: Raw): VisitRow => ({
  id: r.id, visitor: r.visitor, person: r.person, kind: r.kind, reason: r.reason,
  startedAt: new Date(r.started_at).toISOString(), lastAt: new Date(r.last_at).toISOString(),
  city: r.city, region: r.region, country: r.country, device: r.device, lang: r.lang, screen: r.screen, referrer: r.referrer,
  pages: r.pages, activeMs: Number(r.active_ms), trail: r.trail ?? [], reached: r.reached ?? [], shirts: r.shirts ?? [], nth: r.nth ?? undefined,
});
const PERSON = `CASE WHEN v.visitor IS NULL THEN NULL ELSE left(encode(sha256(convert_to(v.visitor, 'UTF8')), 'hex'), 12) END AS person`;
const EXTRA = `
  LEFT JOIN LATERAL (SELECT array_agg(path ORDER BY seq) AS trail FROM (SELECT path, seq FROM visit_events e WHERE e.visit = v.id AND e.type = 'page' ORDER BY seq LIMIT 40) x) t ON true
  LEFT JOIN LATERAL (SELECT array_agg(DISTINCT step) FILTER (WHERE step IS NOT NULL) AS reached, array_agg(DISTINCT design) FILTER (WHERE design IS NOT NULL) AS shirts
    FROM visit_events e WHERE e.visit = v.id) s ON true`;

export type VisitFilter = { kind?: "person" | "bot" | "all"; referrer?: string; device?: string; place?: string; shirt?: string; reached?: string; person?: string };

/** Visits in the last `hours`, newest first, with filters. */
export async function listVisits(hours: number, f: VisitFilter = {}, limit = 400): Promise<VisitRow[]> {
  const h = Math.min(KEEP_DAYS * 24, Math.max(1, Math.floor(hours)));
  const params: (string | number)[] = [h, f.kind ?? "person"];
  const where: string[] = [];
  const add = (sql: string, v: string) => {
    params.push(v);
    where.push(sql.replaceAll("?", `$${params.length}`));
  };
  if (f.referrer) add("coalesce(v.referrer, 'direct') = ?", f.referrer);
  if (f.device) add("v.device = ?", f.device);
  if (f.place) add("(v.city = ? OR v.country = ?)", f.place);
  if (f.shirt) add("? = ANY(s.shirts)", f.shirt);
  if (f.reached) add("? = ANY(s.reached)", f.reached);
  if (f.person && /^[a-f0-9]{12}$/.test(f.person)) add("left(encode(sha256(convert_to(v.visitor, 'UTF8')), 'hex'), 12) = ?", f.person);
  const rs = await rows<Raw>(
    `SELECT v.*, ${PERSON}, t.trail, s.reached, s.shirts,
       CASE WHEN v.visitor IS NULL THEN NULL ELSE (SELECT count(*)::int FROM visits o WHERE o.visitor = v.visitor AND o.started_at <= v.started_at) END AS nth
     FROM visits v ${EXTRA}
     WHERE v.last_at > now() - make_interval(hours => $1::int) AND ($2 = 'all' OR v.kind = $2) ${where.length ? `AND ${where.join(" AND ")}` : ""}
     ORDER BY v.last_at DESC LIMIT ${Math.max(1, Math.min(1000, limit))}`,
    params,
  );
  return rs.map(toRow);
}

export type LiveVisit = VisitRow & { now: string | null; bag: { design: string; size: string | null; n: number }[]; last: { step: Step | null; detail: string | null; at: string } | null };

/** Everyone on the site now (a batch in the last minute), with the page they're on and what's in their bag. */
export async function liveNow(): Promise<LiveVisit[]> {
  const rs = await rows<Raw & { now: string | null; bag: LiveVisit["bag"] | null; last: LiveVisit["last"] }>(
    `SELECT v.*, ${PERSON}, t.trail, s.reached, s.shirts,
       (SELECT count(*)::int FROM visits o WHERE o.visitor = v.visitor AND o.started_at <= v.started_at) AS nth,
       (SELECT path FROM visit_events e WHERE e.visit = v.id AND e.type = 'page' ORDER BY seq DESC LIMIT 1) AS now,
       (SELECT json_agg(b) FROM (SELECT design, size, sum(CASE WHEN step = 'bag' THEN 1 ELSE -1 END)::int AS n FROM visit_events e
          WHERE e.visit = v.id AND step IN ('bag', 'unbag') AND design IS NOT NULL GROUP BY design, size) b WHERE b.n > 0) AS bag,
       (SELECT json_build_object('step', step, 'detail', coalesce(detail, design), 'at', at) FROM visit_events e WHERE e.visit = v.id AND e.type = 'step' ORDER BY seq DESC LIMIT 1) AS last
     FROM visits v ${EXTRA}
     WHERE v.kind = 'person' AND v.last_at > now() - make_interval(secs => ${LIVE_SECONDS})
     ORDER BY v.started_at DESC LIMIT 200`,
  );
  return rs.map((r) => ({ ...toRow(r), now: r.now, bag: r.bag ?? [], last: r.last }));
}

/** on now, in the last hour, today and yesterday (people) */
export async function liveCount() {
  return (
    (await row<{ now: number; hour: number; today: number; yesterday: number }>(
      `SELECT count(*) FILTER (WHERE last_at > now() - make_interval(secs => ${LIVE_SECONDS}))::int AS now,
         count(DISTINCT visitor) FILTER (WHERE last_at > now() - interval '1 hour')::int AS hour,
         count(DISTINCT visitor) FILTER (WHERE (last_at AT TIME ZONE '${TZ}')::date = (now() AT TIME ZONE '${TZ}')::date)::int AS today,
         count(DISTINCT visitor) FILTER (WHERE (last_at AT TIME ZONE '${TZ}')::date = (now() AT TIME ZONE '${TZ}')::date - 1)::int AS yesterday
       FROM visits WHERE kind = 'person' AND last_at > now() - interval '2 days'`,
    ).catch(() => null)) ?? { now: 0, hour: 0, today: 0, yesterday: 0 }
  );
}

/** People (one per browser code) seen in the last `hours`, most recent first, with their totals over the kept log. */
export async function listPeople(hours: number, limit = 300): Promise<PersonRow[]> {
  const h = Math.min(KEEP_DAYS * 24, Math.max(1, Math.floor(hours)));
  const rs = await rows<{
    id: string; first_at: string; last_at: string; visits: number; pages: number; active_ms: number; places: string[] | null; devices: string[] | null;
    lang: string | null; referrer: string | null; reached: Step[] | null;
  }>(
    `SELECT left(encode(sha256(convert_to(v.visitor, 'UTF8')), 'hex'), 12) AS id,
       min(v.started_at) AS first_at, max(v.last_at) AS last_at, count(*)::int AS visits,
       coalesce(sum(v.pages), 0)::int AS pages, coalesce(sum(v.active_ms), 0)::bigint AS active_ms,
       array_agg(DISTINCT concat_ws(', ', v.city, v.country)) FILTER (WHERE v.city IS NOT NULL OR v.country IS NOT NULL) AS places,
       array_agg(DISTINCT v.device) FILTER (WHERE v.device IS NOT NULL) AS devices,
       (array_agg(v.lang ORDER BY v.last_at DESC) FILTER (WHERE v.lang IS NOT NULL))[1] AS lang,
       (array_agg(v.referrer ORDER BY v.started_at) FILTER (WHERE v.referrer IS NOT NULL))[1] AS referrer,
       (SELECT array_agg(DISTINCT e.step) FROM visit_events e JOIN visits w ON w.id = e.visit WHERE w.visitor = v.visitor AND e.step IS NOT NULL) AS reached
     FROM visits v
     WHERE v.kind = 'person' AND v.visitor IS NOT NULL
     GROUP BY v.visitor
     HAVING max(v.last_at) > now() - make_interval(hours => $1::int)
     ORDER BY max(v.last_at) DESC LIMIT ${Math.max(1, Math.min(1000, limit))}`,
    [h],
  );
  return rs.map((r) => ({
    id: r.id, firstAt: new Date(r.first_at).toISOString(), lastAt: new Date(r.last_at).toISOString(), visits: r.visits, pages: r.pages,
    activeMs: Number(r.active_ms), places: r.places ?? [], devices: r.devices ?? [], lang: r.lang, referrer: r.referrer, reached: r.reached ?? [],
  }));
}

/** One visit with every event in order. */
export async function visitById(id: string): Promise<{ visit: VisitRow; events: EventRow[] } | null> {
  if (!/^([a-f0-9]{32}|bot:[\w :.()/-]{1,110})$/.test(id)) return null;
  const v = await row<Raw>(
    `SELECT v.*, ${PERSON}, t.trail, s.reached, s.shirts,
       CASE WHEN v.visitor IS NULL THEN NULL ELSE (SELECT count(*)::int FROM visits o WHERE o.visitor = v.visitor AND o.started_at <= v.started_at) END AS nth
     FROM visits v ${EXTRA} WHERE v.id = $1`,
    [id],
  );
  return v ? { visit: toRow(v), events: await visitEvents(id) } : null;
}

export async function visitEvents(id: string): Promise<EventRow[]> {
  const rs = await rows<EventRow>(`SELECT seq, at, type, path, detail, ms, scroll, step, design, size FROM visit_events WHERE visit = $1 ORDER BY seq LIMIT ${MAX_EVENTS}`, [id]);
  return rs.map((r) => ({ ...r, at: new Date(r.at).toISOString() }));
}

export type Count = { key: string; visits: number; people: number };
export type ShirtFunnel = { design: string; saw: number; size: number; look: number; tryon: number; bag: number; buy: number; checkout: number; pay: number; paid: number };

/** The numbers for the activity page, over the last `days` (people only). */
export async function summary(days: number) {
  const d = Math.max(1, Math.min(KEEP_DAYS, Math.floor(days)));
  const W = `v.kind = 'person' AND v.started_at > now() - make_interval(days => ${d})`;
  const top = (expr: string, n = 15) =>
    rows<Count>(`SELECT coalesce(${expr}, '?') AS key, count(*)::int AS visits, count(DISTINCT v.visitor)::int AS people FROM visits v WHERE ${W} GROUP BY 1 ORDER BY people DESC, visits DESC LIMIT ${n}`);
  const [perDay, totals, pages, referrers, devices, places, screens, langs, funnel, bag, bots, folded] = await Promise.all([
    rows<{ day: string; people: number; visits: number; pages: number; bag: number; checkout: number; paid: number }>(
      `SELECT (v.started_at AT TIME ZONE '${TZ}')::date::text AS day, count(DISTINCT v.visitor)::int AS people, count(*)::int AS visits, coalesce(sum(v.pages), 0)::int AS pages,
         count(DISTINCT v.visitor) FILTER (WHERE EXISTS (SELECT 1 FROM visit_events e WHERE e.visit = v.id AND e.step = 'bag'))::int AS bag,
         count(DISTINCT v.visitor) FILTER (WHERE EXISTS (SELECT 1 FROM visit_events e WHERE e.visit = v.id AND e.step IN ('checkout', 'pay')))::int AS checkout,
         count(DISTINCT v.visitor) FILTER (WHERE EXISTS (SELECT 1 FROM visit_events e WHERE e.visit = v.id AND e.step = 'paid'))::int AS paid
       FROM visits v WHERE ${W} GROUP BY 1 ORDER BY 1`,
    ),
    row<{ people: number; visits: number; pages: number; active: number; returning: number; shirt: number; bag: number; checkout: number; pay: number; paid: number }>(
      `WITH s AS (SELECT v.visitor, v.id, v.pages, v.active_ms,
           EXISTS (SELECT 1 FROM visits o WHERE o.visitor = v.visitor AND o.started_at < v.started_at) AS back,
           (SELECT array_agg(DISTINCT coalesce(step, CASE WHEN design IS NOT NULL OR path LIKE '/fred-again-india/%' THEN 'shirt' END)) FROM visit_events e WHERE e.visit = v.id) AS got
         FROM visits v WHERE ${W})
       SELECT count(DISTINCT visitor)::int AS people, count(*)::int AS visits, coalesce(sum(pages), 0)::int AS pages, coalesce(avg(active_ms), 0)::int AS active,
         count(DISTINCT visitor) FILTER (WHERE back)::int AS returning,
         count(DISTINCT visitor) FILTER (WHERE 'shirt' = ANY(got))::int AS shirt, count(DISTINCT visitor) FILTER (WHERE 'bag' = ANY(got))::int AS bag,
         count(DISTINCT visitor) FILTER (WHERE 'checkout' = ANY(got))::int AS checkout, count(DISTINCT visitor) FILTER (WHERE 'pay' = ANY(got))::int AS pay,
         count(DISTINCT visitor) FILTER (WHERE 'paid' = ANY(got))::int AS paid FROM s`,
    ),
    rows<{ key: string; views: number; people: number; ms: number; scroll: number }>(
      `SELECT e.path AS key, count(*)::int AS views, count(DISTINCT v.visitor)::int AS people, coalesce(avg(e.ms), 0)::int AS ms, coalesce(avg(e.scroll), 0)::int AS scroll
       FROM visit_events e JOIN visits v ON v.id = e.visit WHERE ${W} AND e.type = 'page' GROUP BY e.path ORDER BY views DESC LIMIT 25`,
    ),
    top("v.referrer", 20).then((r) => r.map((x) => ({ ...x, key: x.key === "?" ? "direct" : x.key }))),
    top("v.device"),
    top("concat_ws(', ', v.city, v.country)", 20),
    top("v.screen", 5),
    top("v.lang", 10),
    rows<ShirtFunnel>(
      `WITH d AS (SELECT DISTINCT v.visitor, e.design, coalesce(e.step, 'saw') AS step
         FROM visit_events e JOIN visits v ON v.id = e.visit WHERE ${W} AND e.design IS NOT NULL),
       money AS (SELECT DISTINCT v.visitor, e.step FROM visit_events e JOIN visits v ON v.id = e.visit WHERE ${W} AND e.step IN ('checkout', 'pay', 'paid'))
       SELECT design, count(DISTINCT visitor) FILTER (WHERE step IN ('saw', 'look', 'size'))::int AS saw, count(DISTINCT visitor) FILTER (WHERE step = 'size')::int AS size,
         count(DISTINCT visitor) FILTER (WHERE step = 'look')::int AS look, count(DISTINCT visitor) FILTER (WHERE step = 'tryon')::int AS tryon,
         count(DISTINCT visitor) FILTER (WHERE step = 'bag')::int AS bag, count(DISTINCT visitor) FILTER (WHERE step = 'buy')::int AS buy,
         count(DISTINCT visitor) FILTER (WHERE step IN ('bag', 'buy') AND visitor IN (SELECT visitor FROM money WHERE step = 'checkout'))::int AS checkout,
         count(DISTINCT visitor) FILTER (WHERE step IN ('bag', 'buy') AND visitor IN (SELECT visitor FROM money WHERE step = 'pay'))::int AS pay,
         count(DISTINCT visitor) FILTER (WHERE step IN ('bag', 'buy') AND visitor IN (SELECT visitor FROM money WHERE step = 'paid'))::int AS paid
       FROM d GROUP BY design ORDER BY saw DESC`,
    ),
    rows<{ design: string; size: string | null; n: number }>(
      `SELECT e.design, e.size, count(*)::int AS n FROM visit_events e JOIN visits v ON v.id = e.visit WHERE ${W} AND e.step = 'bag' AND e.design IS NOT NULL GROUP BY 1, 2 ORDER BY n DESC`,
    ),
    rows<{ name: string; pages: number; days: number; last: string }>(
      `SELECT coalesce(device, 'Unknown') AS name, sum(pages)::int AS pages, count(DISTINCT (started_at AT TIME ZONE '${TZ}')::date)::int AS days, max(last_at) AS last
       FROM visits v WHERE v.kind = 'bot' AND v.started_at > now() - make_interval(days => ${d}) GROUP BY 1 ORDER BY pages DESC LIMIT 25`,
    ),
    rows<{ day: string; people: number }>(
      `SELECT day::text, sum(visitors)::int AS people FROM visit_days WHERE kind = 'person' AND day > (now() AT TIME ZONE '${TZ}')::date - ${d} GROUP BY 1 ORDER BY 1`,
    ),
  ]);
  return {
    perDay, pages, referrers, devices, places, screens, langs, funnel, bag, bots, folded,
    totals: totals ?? { people: 0, visits: 0, pages: 0, active: 0, returning: 0, shirt: 0, bag: 0, checkout: 0, pay: 0, paid: 0 },
  };
}

/* ---- the visitor's own record ---- */

/** Everything kept about one browser, for "your visit" on the privacy page. */
export async function mine(visitor: string) {
  const rs = await rows<Raw>(`SELECT v.*, NULL AS person, NULL::text[] AS trail, NULL::text[] AS reached, NULL::text[] AS shirts, NULL::int AS nth FROM visits v WHERE v.visitor = $1 ORDER BY started_at DESC LIMIT 50`, [visitor]);
  return { visits: await Promise.all(rs.map(async (r) => ({ ...toRow(r), events: await visitEvents(r.id) }))) };
}

/** "Forget me": every visit from this browser, gone, and nothing more accepted from its code for two days. */
export async function forget(visitor: string): Promise<number> {
  await kv("SET", `track:forgot:${visitor}`, "1", "EX", 2 * 86400);
  return (await rows<{ id: string }>("DELETE FROM visits WHERE visitor = $1 RETURNING id", [visitor])).length;
}

/** The admin wipes one person's whole log (12-character id from the admin). */
export async function forgetPerson(person: string): Promise<number> {
  if (!/^[a-f0-9]{12}$/.test(person)) return 0;
  return (await rows<{ id: string }>("DELETE FROM visits WHERE visitor IS NOT NULL AND left(encode(sha256(convert_to(visitor, 'UTF8')), 'hex'), 12) = $1 RETURNING id", [person])).length;
}

/* ---- keeping it small ---- */

/**
 * Visits older than KEEP_DAYS are folded into per-day, per-country counts (and per-page views), then deleted with all
 * their detail. Whole days only, so a day is never counted twice. Safe to run as often as the sync job runs.
 */
export async function foldOld(): Promise<{ folded: number }> {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date());
  const cutoff = new Date(Date.parse(`${today}T00:00:00Z`) - KEEP_DAYS * 86400_000).toISOString().slice(0, 10);
  const old = `(started_at AT TIME ZONE '${TZ}')::date < $1::date`;
  await exec(
    `INSERT INTO visit_days (day, country, kind, visitors, visits, pages)
     SELECT (started_at AT TIME ZONE '${TZ}')::date, coalesce(country, ''), kind, count(DISTINCT coalesce(visitor, device)), count(*), coalesce(sum(pages), 0)
     FROM visits WHERE ${old} GROUP BY 1, 2, 3
     ON CONFLICT (day, country, kind) DO UPDATE SET visitors = visit_days.visitors + EXCLUDED.visitors, visits = visit_days.visits + EXCLUDED.visits, pages = visit_days.pages + EXCLUDED.pages`,
    [cutoff],
  );
  await exec(
    `INSERT INTO visit_day_pages (day, path, kind, views)
     SELECT (v.started_at AT TIME ZONE '${TZ}')::date, e.path, v.kind, count(*) FROM visits v JOIN visit_events e ON e.visit = v.id AND e.type = 'page'
     WHERE (v.started_at AT TIME ZONE '${TZ}')::date < $1::date GROUP BY 1, 2, 3
     ON CONFLICT (day, path, kind) DO UPDATE SET views = visit_day_pages.views + EXCLUDED.views`,
    [cutoff],
  );
  return { folded: (await rows<{ id: string }>(`DELETE FROM visits WHERE ${old} RETURNING id`, [cutoff])).length };
}

/* ---- the old counter's visits ---- */

/**
 * Before this log, the site counted visits in the `events` table (one row a page view, bag or checkout, a visitor
 * known only for one day). Each old (day, visitor) becomes a visit here with its pages and steps in order, so the
 * past shows in the admin. Safe to run again: the ids are fixed and nothing is added twice. The old table is left
 * as it is.
 */
export async function importOld(): Promise<number> {
  if (await kv<string | null>("GET", "visits:old-in").catch(() => null)) return 0;
  const has = await row<{ t: string | null }>("SELECT to_regclass('public.events')::text AS t").catch(() => null);
  if (!has?.t) {
    await kv("SET", "visits:old-in", "none").catch(() => {});
    return 0;
  }
  const id = `md5('old:' || e.day::text || ':' || e.visitor)`;
  const made = await rows<{ id: string }>(
    `INSERT INTO visits (id, visitor, kind, started_at, last_at, country, region, device, referrer, pages, active_ms)
     SELECT ${id}, 'old:' || e.day::text || ':' || e.visitor, 'person', min(e.at), max(e.at),
       nullif(split_part(min(e.region), '-', 1), ''), nullif(split_part(min(e.region), '-', 2), ''),
       initcap(min(e.device)), min(e.source), count(*) FILTER (WHERE e.kind = 'view')::int, 0
     FROM events e WHERE e.visitor IS NOT NULL GROUP BY e.day, e.visitor
     ON CONFLICT (id) DO NOTHING RETURNING id`,
  );
  await exec(
    `INSERT INTO visit_events (visit, seq, at, type, path, step, design, size)
     SELECT ${id}, (row_number() OVER (PARTITION BY e.day, e.visitor ORDER BY e.at, e.id) - 1)::int, e.at,
       CASE WHEN e.kind = 'view' THEN 'page' ELSE 'step' END, coalesce(e.path, '/'),
       CASE e.kind WHEN 'bag' THEN 'bag' WHEN 'checkout' THEN 'checkout' END, e.design, e.size
     FROM events e WHERE e.visitor IS NOT NULL
     ON CONFLICT DO NOTHING`,
  );
  await kv("SET", "visits:old-in", new Date().toISOString());
  return made.length;
}

/** people a day over the last `days` (India's days), for the home page's chart */
export async function dailyPeople(days = 30): Promise<Map<string, number>> {
  const d = Math.max(1, Math.min(KEEP_DAYS, Math.floor(days)));
  const r = await rows<{ day: string; people: number }>(
    `SELECT (started_at AT TIME ZONE '${TZ}')::date::text AS day, count(DISTINCT visitor)::int AS people FROM visits
     WHERE kind = 'person' AND started_at > now() - make_interval(days => ${d + 1}) GROUP BY 1`,
  ).catch(() => []);
  return new Map(r.map((x) => [x.day, x.people]));
}

export type Funnel = { people: number; visits: number; returning: number; shirt: number; bag: number; checkout: number; pay: number; paid: number };

/** how far people got between two times (people, each counted once): the overview's way to a sale */
export async function funnelBetween(from: number, to: number): Promise<Funnel> {
  const r = await row<Funnel>(
    `WITH v AS (SELECT id, visitor, started_at FROM visits WHERE kind = 'person' AND started_at >= $1::timestamptz AND started_at < $2::timestamptz),
       s AS (SELECT v.visitor, array_agg(DISTINCT coalesce(e.step, CASE WHEN e.design IS NOT NULL THEN 'shirt' END)) AS got
             FROM v LEFT JOIN visit_events e ON e.visit = v.id GROUP BY v.visitor)
     SELECT (SELECT count(DISTINCT visitor) FROM v)::int AS people, (SELECT count(*) FROM v)::int AS visits,
       (SELECT count(DISTINCT v.visitor) FROM v WHERE EXISTS (SELECT 1 FROM visits o WHERE o.visitor = v.visitor AND o.started_at < v.started_at))::int AS returning,
       count(*) FILTER (WHERE 'shirt' = ANY(got) OR 'size' = ANY(got) OR 'look' = ANY(got) OR 'bag' = ANY(got))::int AS shirt,
       count(*) FILTER (WHERE 'bag' = ANY(got) OR 'buy' = ANY(got))::int AS bag,
       count(*) FILTER (WHERE 'checkout' = ANY(got) OR 'pay' = ANY(got) OR 'paid' = ANY(got))::int AS checkout,
       count(*) FILTER (WHERE 'pay' = ANY(got) OR 'paid' = ANY(got))::int AS pay,
       count(*) FILTER (WHERE 'paid' = ANY(got))::int AS paid
     FROM s`,
    [new Date(from).toISOString(), new Date(to).toISOString()],
  ).catch(() => null);
  return r ?? { people: 0, visits: 0, returning: 0, shirt: 0, bag: 0, checkout: 0, pay: 0, paid: 0 };
}

/** people a day between two times (India's days) */
export async function peoplePerDay(from: number, to: number): Promise<Map<string, number>> {
  const r = await rows<{ day: string; people: number }>(
    `SELECT (started_at AT TIME ZONE '${TZ}')::date::text AS day, count(DISTINCT visitor)::int AS people FROM visits
     WHERE kind = 'person' AND started_at >= $1::timestamptz AND started_at < $2::timestamptz GROUP BY 1`,
    [new Date(from).toISOString(), new Date(to).toISOString()],
  ).catch(() => []);
  return new Map(r.map((x) => [x.day, x.people]));
}

/** since a time: people, bags, checkouts (for "since you last looked") */
export async function sinceThen(at: number) {
  const r = await row<{ people: number; bags: number }>(
    `SELECT count(DISTINCT v.visitor)::int AS people,
       (SELECT count(*) FROM visit_events e JOIN visits w ON w.id = e.visit WHERE w.kind = 'person' AND e.step = 'bag' AND e.at >= $1::timestamptz)::int AS bags
     FROM visits v WHERE v.kind = 'person' AND v.last_at >= $1::timestamptz`,
    [new Date(at).toISOString()],
  ).catch(() => null);
  return r ?? { people: 0, bags: 0 };
}
