"use client";

import { botReason, isBotAgent, whenHuman } from "./bots";
import { CAP, IDLE_MS, MAX_EVENTS, cleanPath, refHost, type EventType, type Step, type TrackBatch, type TrackEvent, type Utm } from "./shared";

/**
 * The browser's side of the visitor log: which pages, in what order, for how long (only while on screen), how far
 * down, the links out, the shop's steps (size, bag, checkout, payment), the buttons and links tapped, the parts of a
 * page that were really seen, which form boxes someone was in (never what they typed), how fast each page was, and
 * anything that broke. Where they came from: the referring site, a campaign link's tags, whether it came through a
 * meta app or a google ad. Batched and sent every 15 seconds while the page is in front, and when it's hidden or
 * closed. Nothing goes anywhere but this site.
 *
 * Nothing is sent if the visitor turned it off on the privacy page, or if their browser asks sites not to track
 * (Global Privacy Control, Do Not Track). Programs never get past whenHuman(); the server logs them apart.
 */
const VID = "sahn-vid";
const VISIT = "sahn-visit";
export const OFF = "sahn-track";

const rand = () => [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
const store = {
  get: (s: Storage, k: string) => {
    try {
      return s.getItem(k);
    } catch {
      return null;
    }
  },
  set: (s: Storage, k: string, v: string) => {
    try {
      s.setItem(k, v);
    } catch {
      /* private mode */
    }
  },
};

/** Does this browser ask not to be tracked, or has its visitor said so here? */
export function trackingOff(): boolean {
  if (typeof window === "undefined") return true;
  const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
  return store.get(localStorage, OFF) === "off" || nav.globalPrivacyControl === true || navigator.doNotTrack === "1";
}
/** off because of the browser's own setting (which this site can't turn back on) */
export function browserSaysOff(): boolean {
  if (typeof window === "undefined") return false;
  const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
  return nav.globalPrivacyControl === true || navigator.doNotTrack === "1";
}

/** This browser's own random code (made here, never derived from anything about you). */
export function visitorCode(create = true): string | null {
  let v = store.get(localStorage, VID);
  if (!v && create) {
    v = rand();
    store.set(localStorage, VID, v);
  }
  return v;
}

let started = false;
let human = false;
let bot: string | null = null;
let visit = "";
let seq = 0;
let firstBatch = true;
const queue = new Map<number, TrackEvent>();
// counted per page load, so one busy page can't fill the visit
const counts: Partial<Record<EventType, number>> = {};
// where they came from, read the moment the page loads (before any in-site link changes the address)
let arrival: Pick<TrackBatch, "ref" | "utm"> = {};
// The page on screen: its event is re-sent as its time and scroll grow.
let page: { ev: TrackEvent; shownAt: number | null; scrollMax: number } | null = null;

function visitId(): string {
  const raw = store.get(sessionStorage, VISIT);
  const now = Date.now();
  try {
    const v = raw ? (JSON.parse(raw) as { id: string; last: number; seq: number }) : null;
    if (v && now - v.last < IDLE_MS) {
      seq = v.seq;
      return v.id;
    }
  } catch {
    /* start over */
  }
  seq = 0;
  return rand();
}
const remember = () => store.set(sessionStorage, VISIT, JSON.stringify({ id: visit, last: Date.now(), seq }));

function push(e: Omit<TrackEvent, "seq" | "at">) {
  if (!started || seq >= MAX_EVENTS) return null;
  const cap = CAP[e.type];
  if (cap != null) {
    if ((counts[e.type] ?? 0) >= cap) return null;
    counts[e.type] = (counts[e.type] ?? 0) + 1;
  }
  const ev: TrackEvent = { ...e, seq: seq++, at: Date.now() };
  queue.set(ev.seq, ev);
  remember();
  return ev;
}

function settlePage() {
  if (!page) return;
  if (page.shownAt != null) {
    page.ev.ms = (page.ev.ms ?? 0) + (Date.now() - page.shownAt);
    page.shownAt = document.visibilityState === "visible" ? Date.now() : null;
  }
  page.ev.scroll = Math.round(page.scrollMax);
  queue.set(page.ev.seq, { ...page.ev });
}

function send(final = false) {
  if (!started || trackingOff()) return;
  settlePage();
  if (!queue.size || (!human && !bot && !final)) return; // nothing new, or not sure yet it's a person
  const w = window.innerWidth;
  const batch: TrackBatch = {
    v: visitorCode()!,
    s: visit,
    human,
    bot,
    events: [...queue.values()],
    ...(firstBatch
      ? { ...arrival, lang: navigator.language, screen: w < 640 ? "phone" : w < 1024 ? "tablet" : "desktop", view: `${w}x${window.innerHeight}`, net: netOf() }
      : {}),
  };
  const body = JSON.stringify(batch);
  const sent = final && navigator.sendBeacon ? navigator.sendBeacon("/api/track", body) : (void fetch("/api/track", { method: "POST", body, keepalive: true }).catch(() => {}), true);
  if (sent) {
    queue.clear();
    firstBatch = false;
  }
}

/** a campaign link's tags, and whose link it was (the click's id itself is never kept) */
function utmOf(): Utm | null {
  const q = new URLSearchParams(location.search);
  const tag = (k: string) => {
    const v = q.get(`utm_${k}`)?.trim();
    return v && /^[\w.+|: -]{1,60}$/.test(v) ? v.toLowerCase() : null;
  };
  const via = q.has("gclid") || q.has("gbraid") || q.has("wbraid") ? "google ads" : q.has("fbclid") ? "meta" : null;
  const u: Utm = { source: tag("source"), medium: tag("medium"), campaign: tag("campaign"), content: tag("content"), term: tag("term"), via };
  return Object.values(u).some(Boolean) ? u : null;
}

/** "4g", "3g save": the connection as the browser reports it, where it does */
function netOf(): string | null {
  const c = (navigator as Navigator & { connection?: { effectiveType?: string; saveData?: boolean } }).connection;
  return c?.effectiveType ? `${c.effectiveType}${c.saveData ? " save" : ""}` : null;
}

/** no email address or phone number ever leaves in a label or a message, even if one was on screen */
const scrub = (t: string) =>
  t.replace(/[^\s@]+@[^\s@]+/g, "[email]").replace(/\+?\d[\d\s-]{6,}\d/g, "[number]").replace(/\s+/g, " ").trim();
const PRIVATE = "input, textarea, select, [contenteditable], [data-private]";
const TAPPABLE = "a[href], button, [role=button], [role=tab], [role=link], [role=option], summary, label, [data-t]";

function labelOf(el: Element): string {
  const h = el as HTMLElement;
  const t = h.dataset?.t || h.getAttribute("aria-label") || h.getAttribute("title") || h.innerText || h.textContent || "";
  return scrub(t).slice(0, 50) || h.tagName.toLowerCase();
}

// the same thing tapped three times inside a second: something isn't answering
let burst: { el: Element; at: number[]; told: boolean } | null = null;
function onTap(e: MouseEvent) {
  const target = e.target as Element | null;
  if (!target?.closest || target.closest("[data-private]")) return;
  const el = target.closest(TAPPABLE);
  const hit = el ?? target;
  const now = Date.now();
  if (burst?.el !== hit) burst = { el: hit, at: [], told: false };
  burst.at = [...burst.at.filter((t) => now - t < 1000), now];
  if (burst.at.length >= 3 && !burst.told) {
    burst.told = true;
    push({ type: "tap", path: cleanPath(location.pathname), detail: `rage: ${labelOf(hit)}` });
    return;
  }
  if (!el || (el.closest(PRIVATE) && !el.matches("label"))) return;
  const a = el.closest("a[href]") as HTMLAnchorElement | null;
  let to = "";
  if (a) {
    try {
      const u = new URL(a.href, location.href);
      if (u.origin !== location.origin) return; // links out are their own kind
      to = ` → ${cleanPath(u.pathname)}`;
    } catch {
      /* not a link we can read */
    }
  }
  const h = el as HTMLElement;
  push({ type: "tap", path: cleanPath(location.pathname), detail: `${labelOf(el)}${to}`.slice(0, 120), design: h.dataset?.design ?? null });
}

// the parts of a page someone really saw: at least half on screen for a second, once per page
const seenDone = new Set<string>();
const watched = new WeakSet<Element>();
const seenTimers = new Map<Element, number>();
let seenObs: IntersectionObserver | null = null;
function watchSeen() {
  if (!started || typeof IntersectionObserver === "undefined") return;
  seenObs ??= new IntersectionObserver(
    (entries) => {
      for (const en of entries) {
        const el = en.target as HTMLElement;
        const t = seenTimers.get(el);
        if (!en.isIntersecting) {
          if (t != null) clearTimeout(t);
          seenTimers.delete(el);
          continue;
        }
        if (t != null) continue;
        seenTimers.set(
          el,
          window.setTimeout(() => {
            seenTimers.delete(el);
            if (!el.isConnected) return;
            const path = cleanPath(location.pathname);
            const key = `${path}|${el.dataset.seen}|${el.dataset.design ?? ""}`;
            seenObs?.unobserve(el);
            if (seenDone.has(key)) return;
            seenDone.add(key);
            push({ type: "seen", path, detail: (el.dataset.seen ?? "").slice(0, 60), design: el.dataset.design ?? null });
          }, 1000),
        );
      }
    },
    { threshold: 0.5 },
  );
  document.querySelectorAll("[data-seen]").forEach((el) => {
    if (watched.has(el)) return;
    watched.add(el);
    seenObs!.observe(el);
  });
}

// which form box someone was in, for how long, and whether they left it filled; never what they typed
let inField: { el: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement; at: number } | null = null;
const fieldName = (el: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement) =>
  scrub(el.dataset.t || el.name || (el.autocomplete && el.autocomplete !== "on" && el.autocomplete !== "off" ? el.autocomplete : "") || el.getAttribute("aria-label") || el.id || el.type || "box").slice(0, 40);
function onFocusIn(e: FocusEvent) {
  const el = e.target as HTMLInputElement | null;
  if (!el?.matches?.("input, select, textarea")) return;
  if (el.type === "password" || el.type === "hidden") return;
  inField = { el, at: Date.now() };
}
function onFocusOut(e: FocusEvent) {
  if (!inField || e.target !== inField.el) return;
  const { el, at } = inField;
  inField = null;
  const filled = el instanceof HTMLInputElement && (el.type === "checkbox" || el.type === "radio") ? el.checked : el.value.trim().length > 0;
  const form = el.form?.dataset.t || el.form?.getAttribute("aria-label") || "";
  push({ type: "field", path: cleanPath(location.pathname), detail: `${form ? `${scrub(form).slice(0, 20)}: ` : ""}${fieldName(el)}`, ms: Date.now() - at, value: filled ? 1 : 0 });
}

// something broke: the message and where (this site's files only), never anything typed
const fileOf = (u: string) => {
  try {
    const x = new URL(u, location.href);
    return x.origin === location.origin ? x.pathname.split("/").slice(-1)[0]!.slice(0, 50) : null;
  } catch {
    return null;
  }
};
function oops(msg: string) {
  push({ type: "error", path: cleanPath(location.pathname), detail: scrub(msg).slice(0, 200) });
}
function onError(e: Event) {
  if (e instanceof ErrorEvent) {
    const f = e.filename ? fileOf(e.filename) : "";
    if (f === null) return; // a browser extension's, not ours
    oops(`${e.message || "error"}${f ? ` @ ${f}:${e.lineno}` : ""}`);
    return;
  }
  // an image, script or stylesheet of ours that didn't load
  const t = e.target as HTMLElement | null;
  const src = (t as HTMLImageElement | null)?.currentSrc || t?.getAttribute?.("src") || t?.getAttribute?.("href");
  if (!t || t === (window as unknown as HTMLElement) || !src) return;
  try {
    const u = new URL(src, location.href);
    if (u.origin === location.origin) oops(`${t.tagName.toLowerCase()} didn't load: ${cleanPath(u.pathname)}`);
  } catch {
    /* not an address */
  }
}

/** how fast the page was for this person (from next/web-vitals) */
export function trackVital(name: string, value: number, rating?: string) {
  if (!Number.isFinite(value)) return;
  push({ type: "vital", path: cleanPath(location.pathname), detail: `${name}${rating ? `:${rating}` : ""}`.slice(0, 30), value: name === "CLS" ? Math.round(value * 1000) / 1000 : Math.round(value) });
}

/** Start logging this visit (once per page load). */
export function startTracking() {
  // A program that says so in its user agent is logged by the server (src/proxy.ts).
  if (started || typeof window === "undefined" || trackingOff() || isBotAgent(navigator.userAgent)) return;
  started = true;
  visit = visitId();
  const utm = utmOf();
  arrival = { ref: (utm?.source && /^[\w.-]{1,40}$/.test(utm.source) ? utm.source : null) ?? refHost(document.referrer, location.hostname), utm };
  bot = botReason();
  void whenHuman().then(() => {
    human = true;
    send();
  });

  const onScroll = () => {
    if (!page) return;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    page.scrollMax = Math.max(page.scrollMax, max > 0 ? (window.scrollY / max) * 100 : 100);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (!page) return;
    if (document.visibilityState === "hidden") send(true);
    else page.shownAt = Date.now();
  });
  window.addEventListener("pagehide", () => send(true));
  // Links out: which site, which link.
  document.addEventListener(
    "click",
    (e) => {
      const a = (e.target as HTMLElement | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a) return;
      try {
        const u = new URL(a.href, location.href);
        if (u.origin === location.origin || !/^https?:$/.test(u.protocol)) return;
        push({ type: "click", path: cleanPath(location.pathname), detail: `${u.hostname.replace(/^www\./, "")}${u.pathname === "/" ? "" : u.pathname}`.slice(0, 200) });
      } catch {
        /* not a link we can read */
      }
    },
    true,
  );
  document.addEventListener("click", onTap, true);
  document.addEventListener("focusin", onFocusIn, true);
  document.addEventListener("focusout", onFocusOut, true);
  window.addEventListener("error", onError, true);
  window.addEventListener("unhandledrejection", (e) => oops(`unhandled: ${String((e.reason as Error | undefined)?.message ?? e.reason)}`));
  // new parts of a page (a list that loads late, a page changed in place) are watched too
  let pending = 0;
  new MutationObserver(() => {
    if (pending) return;
    pending = window.setTimeout(() => {
      pending = 0;
      watchSeen();
    }, 400);
  }).observe(document.body, { childList: true, subtree: true });
  setInterval(() => document.visibilityState === "visible" && send(), 15_000);
}

/** A new page on screen (called on every route change). */
export function trackPage(path: string) {
  if (!started) return;
  const p = cleanPath(path);
  if (page && page.ev.path === p) return;
  settlePage();
  const ev = push({ type: "page", path: p, ms: 0, scroll: 0 });
  page = ev ? { ev, shownAt: document.visibilityState === "visible" ? Date.now() : null, scrollMax: 0 } : null;
  for (const k of ["tap", "seen", "field"] as EventType[]) counts[k] = 0;
  window.setTimeout(watchSeen, 300);
  send();
}

/** A shop step: the shirt and size where there is one, and a short word for which (a view of the 3D, say). */
export function trackStep(step: Step, design?: string | null, size?: string | null, detail?: string | null, value?: number | null) {
  const ev = push({ type: "step", path: cleanPath(location.pathname), step, design: design ?? null, size: size ?? null, detail: detail?.slice(0, 60) ?? null, value: value ?? null });
  // money steps go at once, so the admin's live view has them as they happen
  if (ev && (step === "checkout" || step === "pay" || step === "paid" || step === "payfail" || step === "bag")) send(step === "paid");
}

/**
 * Start over: forget this browser's code and the visit in progress, and drop anything not yet sent, so nothing
 * deleted can come back with the next batch.
 */
export function resetTracking() {
  queue.clear();
  page = null;
  seq = 0;
  firstBatch = true;
  visit = rand();
  try {
    localStorage.removeItem(VID);
    sessionStorage.removeItem(VISIT);
  } catch {
    /* nothing kept */
  }
}

/** Turn it off (or back on) for this browser. Off also forgets the code. */
export function setTracking(on: boolean) {
  store.set(localStorage, OFF, on ? "on" : "off");
  if (!on) resetTracking();
}
