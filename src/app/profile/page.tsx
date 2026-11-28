import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Reorder } from "@/components/shop/Reorder";
import { paperStill, shirtHref } from "@/content/lineups";
import { ShirtCard } from "@/components/ShirtCard";
import { OPERATOR } from "@/content/policies";
import { WAY_WORD, accountOrders, activity, devices, loadAccount, lookedAt, passwordSetAt, prefs, sessionEmail } from "@/lib/shop/account";
import { accountsOpen, googleKeys } from "@/lib/shop/config";
import { rupees } from "@/lib/shop/money";
import { loadOrder, view, type OrderView, type Stage } from "@/lib/shop/orders";
import { EVENT_WORD, STAGE_WORD, dayYear, when } from "@/lib/shop/words";
import { Addresses, Devices, Drops, GoogleSwitch, Hello, Leave, Password, Profile, ProfileTabs, SignIn, SizePick, Unsave } from "./parts";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "profile", robots: { index: false, follow: false } };

/** where to go after signing in: only a path on this site */
const safeNext = (v: unknown) => (typeof v === "string" && /^\/(?!\/)[\w\-/?=&.]*$/.test(v) && v.length < 200 ? v : null);
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

/** what an ?e= from the Google round trip means, in a line */
const SAY: Record<string, string> = {
  google: "google sign-in isn't open yet. use your email for now.",
  "google-cancelled": "google sign-in was stopped. try again, or use your email.",
  "google-failed": "google didn't give us a verified email. try again, or use your email.",
  "google-off": "google sign-in is turned off for this email. sign in with a code, then turn it on in sign-in.",
  slow: "too many tries: wait a few minutes.",
};

/** an order's way from paid to the door */
const STEPS: Stage[][] = [["paid"], ["printing"], ["shipped", "out"], ["delivered"]];
const STEP_WORD = ["in", "being made", "on its way", "with you"];
const stepOf = (s: Stage) => STEPS.findIndex((x) => x.includes(s));
const going = (o: OrderView) => ["paid", "printing", "shipped", "out", "attention"].includes(o.stage);
const monthYear = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { month: "short", year: "numeric", timeZone: "Asia/Kolkata" }).toLowerCase();
/** the order steps worth showing in a person's own activity */
const SHOWN = new Set(["placed", "paid", "address", "shipped", "delivered", "cancelled", "refunded"]);

/**
 * The profile. Signed out: one sign-in that also makes the profile, by Google, an email code or a password.
 * Signed in: the person, then tabs: orders, saved (and looked at), addresses, details (with size and drop emails), sign-in (ways in, password, devices), privacy
 * (visit counting, their data, deleting) and activity (everything they and their orders did).
 */
export default async function ProfilePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  if (!accountsOpen()) notFound();
  const sp = await searchParams;
  const next = safeNext(one(sp.next));
  const said = SAY[one(sp.e) ?? ""] ?? null;
  const google = !!googleKeys();
  const email = await sessionEmail().catch(() => null);

  if (!email) {
    return (
      <div className="grid grid-cols-1 gap-x-4 px-4 pt-6 pb-24 md:grid-cols-12">
        <div className="md:col-span-7">
          <h1 className="page-in bigword text-[22vw] md:text-[11vw]">sign in</h1>
          <p className="page-in-2 mt-6 max-w-[40ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">
            or make your profile: it&apos;s the same step. any way you like, and you can always order without one.
          </p>
          <ul className="page-in-2 mt-10 hidden max-w-[44ch] text-[14px] md:block">
            {[
              ["every order in one place", "even the ones you placed before, with the same email"],
              ["checkout fills itself in", "your name, mobile and the places you send shirts to"],
              ["yours to run", "your devices, a password if you want one, your data, and deleting it all"],
            ].map(([t, s]) => (
              <li key={t} className="border-t border-line py-3"><span className="text-ink">{t}</span><span className="block text-quiet">{s}</span></li>
            ))}
          </ul>
        </div>
        <div className="page-in-3 mt-12 md:col-span-4 md:col-start-9 md:mt-[min(12vw,190px)]"><SignIn next={next} google={google} said={said} /></div>
      </div>
    );
  }

  const [a, ids, list, pwAt, events, my, looked] = await Promise.all([
    loadAccount(email), accountOrders(email).catch(() => [] as string[]), devices(email).catch(() => []), passwordSetAt(email), activity(email).catch(() => []),
    prefs(email), lookedAt(email).catch(() => []),
  ]);
  const lately = looked.filter((d) => !my.saved.includes(d));
  if (one(sp.hello) === "1" && !a?.name) return <div className="px-4 pt-6 pb-24"><div className="mx-auto max-w-[420px] pt-10"><Hello next={next} /></div></div>;

  const orders = (await Promise.all(ids.slice(0, 50).map((id) => loadOrder(id).catch(() => null))))
    .filter((o) => o && o.stage !== "paying" && o.contact.email === email)
    .map((o) => view(o!, true));
  const now = orders.filter(going), before = orders.filter((o) => !going(o));
  const shirts = orders.filter((o) => o.stage !== "cancelled").reduce((n, o) => n + o.lines.reduce((m, l) => m + l.quantity, 0), 0);
  const name = a?.name?.trim() ?? "";
  const first = name.split(" ")[0]?.toLowerCase();
  // orders placed as a guest before the profile existed, found by the email, the first couple of days after
  const created = a?.createdAt ? Date.parse(a.createdAt) : Date.now();
  const found = Date.now() - created < 3 * 86400_000 ? orders.filter((o) => Date.parse(o.placed) < created).length : 0;

  // everything, newest first: what they did, and what happened to their orders
  const feed = [
    ...events.map((e) => ({ at: e.at, what: e.what, detail: e.detail, href: null as string | null })),
    ...orders.flatMap((o) => o.events.filter((e) => SHOWN.has(e.kind)).map((e) => ({ at: e.at, what: `${EVENT_WORD[e.kind]}: #${o.id}`, detail: e.kind === "placed" ? rupees(o.total) : undefined, href: `/order/${o.id}` }))),
  ].sort((x, y) => Date.parse(y.at) - Date.parse(x.at)).slice(0, 300);

  const orderList = orders.length === 0 ? (
    <Blank title="nothing yet." sub={`each order placed with ${email} shows here, from print to your door, even ones placed without signing in.`}>
      <Link href="/shop" className="mt-6 inline-flex h-12 items-center gap-6 bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90">see the shirts <span aria-hidden>→</span></Link>
    </Blank>
  ) : (
    <div className="grid gap-12">
      {found ? (
        <p className="border border-line p-4 text-[14px] leading-snug">
          <span className="font-semibold">we found {found === 1 ? "an order" : `${found} orders`} you placed with this email before you made your profile.</span>{" "}
          <span className="text-quiet">{found === 1 ? "it's" : "they're"} all here now, with tracking and receipts.</span>
        </p>
      ) : null}
      {now.length ? <OrderGroup title="on the way" list={now} /> : null}
      {before.length ? <OrderGroup title={now.length ? "earlier" : "your orders"} list={before} /> : null}
    </div>
  );

  return (
    <div className="px-4 pt-6 pb-24">
      <header className="page-in flex items-center gap-5 md:gap-7">
        <span aria-hidden className="grid h-[72px] w-[72px] shrink-0 place-items-center rounded-full bg-ink text-[32px] font-extrabold tracking-[-0.04em] text-paper md:h-[104px] md:w-[104px] md:text-[46px]">
          {(name || email)[0].toLowerCase()}
        </span>
        <div className="min-w-0">
          <h1 className="truncate text-[40px] leading-[0.95] font-extrabold tracking-[-0.045em] md:text-[64px]">{first ? `hi ${first}.` : "your profile."}</h1>
          <p className="mt-2 truncate text-[14px] text-quiet">{email}</p>
        </div>
      </header>
      <dl className="page-in-2 mt-8 grid max-w-[560px] grid-cols-3 border-t border-line pt-3 text-[13px] text-quiet">
        <div><dt>orders</dt><dd className="tnum text-[22px] font-semibold text-ink">{orders.length}</dd></div>
        <div><dt>shirts</dt><dd className="tnum text-[22px] font-semibold text-ink">{shirts}</dd></div>
        <div><dt>here since</dt><dd className="text-[22px] font-semibold text-ink">{monthYear(a?.createdAt ?? new Date().toISOString())}</dd></div>
      </dl>
      {!name ? <p className="page-in-2 mt-6 max-w-[560px] text-[14px] text-quiet">add your name in <a href="#details" className="draw text-ink">details</a>, so we know what to call you and checkout fills it in.</p> : null}

      <div className="page-in-3 mt-12">
        <ProfileTabs counts={{ orders: orders.length, saved: my.saved.length, addresses: a?.addresses.length ?? 0, "sign-in": list.length }}
          panes={{
            orders: orderList,
            saved: (
              <div className="grid gap-14">
                {my.saved.length ? (
                  <section>
                    <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">saved for later · {my.saved.length}</h2>
                    <ul className="mt-4 grid grid-cols-2 gap-x-3 gap-y-8 md:grid-cols-4">
                      {my.saved.map((d) => <li key={d}><ShirtCard d={d} /><Unsave design={d} /></li>)}
                    </ul>
                  </section>
                ) : <Blank title="nothing saved yet." sub="tap save for later on any shirt and it waits here, in your size." ><Link href="/shop" className="mt-6 inline-flex h-12 items-center gap-6 bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90">see the shirts <span aria-hidden>→</span></Link></Blank>}
                {lately.length ? (
                  <section>
                    <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">you looked at</h2>
                    <ul className="mt-4 grid grid-cols-2 gap-x-3 gap-y-8 md:grid-cols-4">
                      {lately.slice(0, 4).map((d) => <li key={d}><ShirtCard d={d} /></li>)}
                    </ul>
                  </section>
                ) : null}
              </div>
            ),
            addresses: <Addresses list={a?.addresses ?? []} />,
            details: (
              <div className="grid max-w-[560px] gap-14">
                <Profile name={name} phone={a?.phone ?? ""} email={email} />
                <SizePick size={my.size} />
                <Drops on={my.drops} />
              </div>
            ),
            "sign-in": (
              <div className="grid max-w-[720px] gap-14">
                <section>
                  <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">ways in</h2>
                  <ul className="mt-2 text-[14px]">
                    <li className="flex items-start justify-between gap-4 border-b border-line py-3">
                      <span><span className="text-ink">email code</span><span className="block text-quiet">a 6-digit code to {email}. always on: it&apos;s how you get back in if anything else goes.</span></span>
                      <span className="shrink-0 text-[13px] text-quiet">on</span>
                    </li>
                    <li className="flex items-start justify-between gap-4 border-b border-line py-3">
                      <span><span className="text-ink">password</span><span className="block text-quiet">{pwAt ? `set ${dayYear(pwAt)}. change or remove it below.` : "none. set one below if you'd rather type a password."}</span></span>
                      <span className="shrink-0 text-[13px] text-quiet">{pwAt ? "on" : "off"}</span>
                    </li>
                    <li className="flex items-start justify-between gap-4 border-b border-line py-3">
                      <span><span className="text-ink">google</span><span className="block text-quiet">{a?.googleOff ? "turned off: signing in with google won't open this profile." : a?.google ? `used first ${dayYear(a.google)}.` : `the google account for ${email} can sign in.`}{!google ? " (opening soon on sahn.)" : ""}</span></span>
                      <GoogleSwitch on={!a?.googleOff} />
                    </li>
                  </ul>
                </section>
                <Password has={!!pwAt} email={email} />
                <Devices list={list.map((d) => ({ ...d, how: WAY_WORD[d.way] }))} />
              </div>
            ),
            privacy: (
              <div className="grid max-w-[720px] gap-14">
                <section>
                  <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">your data</h2>
                  <p className="mt-3 max-w-[52ch] text-[14px] text-quiet">everything sahn keeps about you: your details, addresses, ways in, devices, orders and activity, in one file.</p>
                  <a href="/api/shop/account?export=1" download className="mt-4 inline-flex h-12 items-center gap-6 border border-line px-4 text-[15px] hover:border-ink">download my data <span aria-hidden>↓</span></a>
                  <p className="mt-6 max-w-[52ch] text-[13px] text-quiet">payments are handled by razorpay: we never see or keep your card or upi details. razorpay can remember them for you, by your mobile, across every shop that uses it. emails from us are only about your orders. the <Link href="/policies/privacy" className="draw text-ink">privacy policy</Link> has the rest.</p>
                </section>
                <section>
                  <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">visits</h2>
                  <p className="mt-3 max-w-[52ch] text-[14px] text-quiet">we count visits to see which shirts and pages people like. while you&apos;re signed in, your visits are kept with your profile, so we can see what you looked at and help if an order goes wrong. no ip addresses; deleting your profile unlinks them.</p>
                </section>
                <Leave email={email} />
              </div>
            ),
            activity: feed.length ? (
              <ol className="max-w-[720px] text-[14px]">
                {feed.map((f, i) => (
                  <li key={i} className="grid grid-cols-[110px_1fr] gap-4 border-b border-line py-3 md:grid-cols-[150px_1fr]">
                    <span className="text-[13px] text-quiet">{when(f.at)}</span>
                    <span>{f.href ? <Link href={f.href} className="draw text-ink">{f.what}</Link> : <span className="text-ink">{f.what}</span>}{f.detail ? <span className="block text-quiet">{f.detail}</span> : null}</span>
                  </li>
                ))}
              </ol>
            ) : <Blank title="nothing yet." sub="every sign-in, change and order shows here, newest first." />,
          }}
        />
      </div>
    </div>
  );
}

function Blank({ title, sub, children }: { title: string; sub: string; children?: React.ReactNode }) {
  return (
    <div className="border-t border-line pt-6">
      <p className="text-[22px] leading-tight font-semibold tracking-[-0.02em]">{title}</p>
      <p className="mt-2 max-w-[44ch] text-[15px] text-quiet">{sub}</p>
      {children}
    </div>
  );
}

function OrderGroup({ title, list }: { title: string; list: OrderView[] }) {
  return (
    <section>
      <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">{title} · {list.length}</h2>
      <ul className="mt-3 grid gap-3 md:grid-cols-2">
        {list.map((o) => <OrderCard key={o.id} o={o} />)}
      </ul>
    </section>
  );
}

function OrderCard({ o }: { o: OrderView }) {
  const step = stepOf(o.stage);
  const n = o.lines.reduce((m, l) => m + l.quantity, 0);
  return (
    <li className="flex flex-col bg-s1 p-4">
      <div className="flex items-start gap-4">
        <div className="flex shrink-0 -space-x-6">
          {o.lines.slice(0, 3).map((l, i) => (
            <Link key={`${l.design}-${l.size}`} href={shirtHref(l.design)} className="relative block h-[84px] w-[66px] overflow-hidden bg-s2 ring-2 ring-s1" style={{ zIndex: 3 - i }}>
              <img src={paperStill(l.design, "back")} alt={l.name} width={66} height={84} loading="lazy" decoding="async" className="h-full w-full object-cover" />
            </Link>
          ))}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <Link href={`/order/${o.id}`} className="draw text-[15px] font-semibold tnum">#{o.id}</Link>
            <span className="tnum text-[15px]">{rupees(o.total)}</span>
          </div>
          <p className={`mt-0.5 text-[14px] ${o.stage === "attention" ? "text-ink" : "text-quiet"}`}>{STAGE_WORD[o.stage]}{o.stage === "delivered" && o.deliveredAt ? `, ${dayYear(o.deliveredAt)}` : ""}</p>
          <p className="mt-1 truncate text-[13px] text-quiet">{o.lines.map((l) => `${l.name} ${l.size}${l.quantity > 1 ? ` × ${l.quantity}` : ""}`).join(", ")}</p>
          <p className="text-[13px] text-quiet">{dayYear(o.placed)} · {n} shirt{n === 1 ? "" : "s"}</p>
        </div>
      </div>
      {step >= 0 && o.stage !== "delivered" ? (
        <div className="mt-4" aria-label={`step ${step + 1} of 4: ${STEP_WORD[step]}`}>
          <div className="grid grid-cols-4 gap-1">
            {STEP_WORD.map((w, i) => <span key={w} className={`h-[3px] ${i <= step ? "bg-ink" : "bg-line"}`} />)}
          </div>
          <div className="mt-1.5 grid grid-cols-4 gap-1 text-[12px] text-quiet">
            {STEP_WORD.map((w, i) => <span key={w} className={i === step ? "text-ink" : ""}>{w}</span>)}
          </div>
        </div>
      ) : null}
      <div className="mt-auto flex flex-wrap gap-x-5 gap-y-1 pt-4 text-[13px] text-quiet">
        <Link href={`/order/${o.id}`} className="hit hover:text-ink">details</Link>
        {o.tracking?.url && <a href={o.tracking.url} target="_blank" rel="noreferrer noopener" className="hit hover:text-ink">track ↗</a>}
        <Link href={`/order/${o.id}/receipt`} className="hit hover:text-ink">receipt</Link>
        <Reorder lines={o.lines} />
        {OPERATOR.email ? <a href={`mailto:${OPERATOR.email}?subject=${encodeURIComponent(`order #${o.id}`)}`} className="hit hover:text-ink">get help</a> : null}
      </div>
    </li>
  );
}
