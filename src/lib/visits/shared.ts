/**
 * The visitor log, shared by the browser, the server and /admin.
 * What's kept, and why, is on /policies/privacy; each visitor can see and delete their own there.
 */

/** Every visit is kept in full this long; after that only daily counts (per country, per page) are. */
export const KEEP_DAYS = 180;
/** A visit ends after this long with nothing happening; the next page starts a new one. */
export const IDLE_MS = 30 * 60_000;
/** At most this many events per visit, and pages per program per day. */
export const MAX_EVENTS = 1500;
export const MAX_BOT_PAGES = 300;
/** the browser sends a batch every 15 s while in front: on the site "now" is a batch in the last minute */
export const LIVE_SECONDS = 60;

export const ID = /^[a-f0-9]{32}$/;

/**
 * page:  a page on screen (its time on screen and how far down grow as it's re-sent)
 * click: a link out to another site
 * step:  a shop step (what it is in `step`, the shirt and size with it; `value` is the rupees on "paid")
 * tap:   a button or link inside the site, by its label ("rage: …" when tapped again and again in a second)
 * seen:  a part of a page that was really on screen for a second (a shirt card, the size picker)
 * field: a form box someone was in: which box (never what was typed), the time in it, `value` 1 if it was left filled
 * vital: how fast the page was for them (LCP, INP, CLS, FCP, TTFB), in `value`, with its rating in `detail`
 * error: something on the page broke for them (the message and where, never anything they typed)
 */
export const EVENT_TYPES = ["page", "click", "step", "tap", "seen", "field", "vital", "error"] as const;
export type EventType = (typeof EVENT_TYPES)[number];
/** at most this many of each noisy kind in a visit, so one busy page can't fill the log */
export const CAP: Partial<Record<EventType, number>> = { tap: 200, seen: 120, field: 80, vital: 60, error: 15 };
export const VITALS = ["LCP", "INP", "CLS", "FCP", "TTFB"] as const;
export const STEPS = ["size", "look", "tryon", "bag", "unbag", "buy", "checkout", "pay", "paid", "payfail", "signin", "share"] as const;
export type Step = (typeof STEPS)[number];

/** what each step is called in the admin and in "your visit" */
export const STEP_WORD: Record<Step, string> = {
  size: "picked a size", look: "looked at", tryon: "opened try-on", bag: "put in the bag", unbag: "took out of the bag", buy: "pressed buy now",
  checkout: "opened checkout", pay: "opened the payment window", paid: "paid", payfail: "payment didn't go through", signin: "signed in", share: "shared",
};

export interface TrackEvent {
  seq: number;
  at: number;
  type: EventType;
  path: string;
  detail?: string | null;
  ms?: number | null;
  scroll?: number | null;
  step?: Step | null;
  design?: string | null;
  size?: string | null;
  value?: number | null;
}

/** a campaign link's tags (utm_*), and whose link it came through: "meta" for a link from instagram or facebook (organic or ad), "google ads" for a google ad (only that, never the click's id) */
export interface Utm {
  source?: string | null;
  medium?: string | null;
  campaign?: string | null;
  content?: string | null;
  term?: string | null;
  via?: "meta" | "google ads" | null;
}

export interface TrackBatch {
  /** The browser's own random code (kept in localStorage). */
  v: string;
  /** This visit. */
  s: string;
  /** Has a person done anything yet (moved, scrolled, tapped, typed)? */
  human: boolean;
  /** Set by the page when it can tell it's being driven by a program. */
  bot?: string | null;
  /** Where they came from: a site name only (or the link's utm_source). Sent with the first batch. */
  ref?: string | null;
  lang?: string | null;
  screen?: "phone" | "tablet" | "desktop" | null;
  utm?: Utm | null;
  /** the window's size, "390x844" */
  view?: string | null;
  /** the connection the browser reports: "4g", "3g", "4g save" (data saver on) */
  net?: string | null;
  events: TrackEvent[];
}

/** A visit, as /admin and "your visit" show it. */
export interface VisitRow {
  id: string;
  visitor: string | null;
  /** 12 characters of the SHA-256 of the browser's code: the person, without the code */
  person: string | null;
  kind: "person" | "bot";
  reason: string | null;
  startedAt: string;
  lastAt: string;
  city: string | null;
  region: string | null;
  country: string | null;
  device: string | null;
  lang: string | null;
  screen: string | null;
  referrer: string | null;
  medium: string | null;
  campaign: string | null;
  content: string | null;
  via: string | null;
  view: string | null;
  net: string | null;
  pages: number;
  activeMs: number;
  /** Pages in order, as a short trail */
  trail: string[];
  /** the shop steps reached, once each */
  reached: Step[];
  /** the shirts looked at (design ids) */
  shirts: string[];
  /** For people: which visit of theirs this is, in the kept log (1 = first). */
  nth?: number;
}

/** One person (one browser's code). */
export interface PersonRow {
  id: string;
  firstAt: string;
  lastAt: string;
  visits: number;
  pages: number;
  activeMs: number;
  places: string[];
  devices: string[];
  lang: string | null;
  referrer: string | null;
  reached: Step[];
}

export interface EventRow {
  seq: number;
  at: string;
  type: EventType;
  path: string;
  detail: string | null;
  ms: number | null;
  scroll: number | null;
  step: Step | null;
  design: string | null;
  size: string | null;
  value: number | null;
}

/** "Googlebot", "ChatGPT", "curl"… from a program's user agent. */
export function botName(ua: string | null | undefined): string {
  const s = ua ?? "";
  if (!s) return "No user agent";
  const known: [RegExp, string][] = [
    [/Googlebot/i, "Googlebot"],
    [/Google-InspectionTool/i, "Google Search Console"],
    [/GoogleOther|Google-Extended/i, "Google (other)"],
    [/bingbot/i, "Bingbot"],
    [/DuckDuckBot/i, "DuckDuckGo"],
    [/YandexBot/i, "Yandex"],
    [/Baiduspider/i, "Baidu"],
    [/Applebot/i, "Applebot"],
    [/GPTBot|ChatGPT-User|OAI-SearchBot/i, "OpenAI"],
    [/ClaudeBot|Claude-User|Claude-SearchBot|anthropic/i, "Anthropic"],
    [/PerplexityBot|Perplexity-User/i, "Perplexity"],
    [/CCBot/i, "Common Crawl"],
    [/Bytespider/i, "ByteDance"],
    [/AhrefsBot/i, "Ahrefs"],
    [/SemrushBot/i, "Semrush"],
    [/MJ12bot/i, "Majestic"],
    [/DotBot/i, "Moz"],
    [/PetalBot/i, "Petal (Huawei)"],
    [/facebookexternalhit|meta-externalagent|facebookcatalog/i, "Facebook / Instagram preview"],
    [/Twitterbot/i, "X preview"],
    [/LinkedInBot/i, "LinkedIn preview"],
    [/Slackbot/i, "Slack preview"],
    [/Discordbot/i, "Discord preview"],
    [/TelegramBot/i, "Telegram preview"],
    [/WhatsApp/i, "WhatsApp preview"],
    [/SkypeUriPreview/i, "Skype preview"],
    [/Pinterestbot|Pinterest\//i, "Pinterest"],
    [/redditbot/i, "Reddit preview"],
    [/Lighthouse|PageSpeed|Chrome-Lighthouse/i, "Lighthouse"],
    [/vercel/i, "Vercel"],
    [/UptimeRobot|Pingdom|uptime/i, "Uptime check"],
    [/HeadlessChrome/i, "Headless Chrome"],
    [/Puppeteer|Playwright|Selenium|PhantomJS/i, "Automated browser"],
    [/curl\//i, "curl"],
    [/Wget/i, "Wget"],
    [/HTTPie|xh\//i, "HTTPie"],
    [/python|aiohttp/i, "Python script"],
    [/node-fetch|axios|undici|node\//i, "Node script"],
    [/Go-http-client/i, "Go program"],
    [/okhttp|Java\//i, "Java program"],
  ];
  for (const [re, name] of known) if (re.test(s)) return name;
  const first = s.split(/[\s;(]/)[0]?.split("/")[0];
  return first ? first.slice(0, 40) : "Unknown program";
}

/** Terminal tools are people at a keyboard, really; they're shown apart from crawlers. */
export const isTerminal = (name: string) => ["curl", "Wget", "HTTPie"].includes(name);

/** "/shop", without the query string or anything after #, capped. */
export const cleanPath = (p: string) => (p.split(/[?#]/)[0] || "/").slice(0, 200);

/** A site name from a referrer: "instagram.com", never the full address. */
export function refHost(ref: string | null | undefined, self?: string): string | null {
  if (!ref) return null;
  try {
    const h = new URL(ref).hostname.replace(/^(www|m|l|lm)\./, "");
    if (self && h === self.replace(/^www\./, "")) return null;
    return h.slice(0, 80) || null;
  } catch {
    return null;
  }
}

/** "4 min", "40 s" */
export const span = (ms: number) => (ms < 60_000 ? `${Math.round(ms / 1000)} s` : ms < 3600_000 ? `${Math.round(ms / 60_000)} min` : `${(ms / 3600_000).toFixed(1)} h`);
