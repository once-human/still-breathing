import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Reorder } from "@/components/shop/Reorder";
import { paperStill, shirtHref } from "@/content/lineups";
import { accountOrders, loadAccount, sessionEmail } from "@/lib/shop/account";
import { accountsOpen } from "@/lib/shop/config";
import { rupees } from "@/lib/shop/money";
import { loadOrder, view, type OrderView, type Stage } from "@/lib/shop/orders";
import { STAGE_WORD, dayYear } from "@/lib/shop/words";
import { AccountTabs, Addresses, Leave, Profile, SignIn } from "./parts";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "account", robots: { index: false, follow: false } };

/** where to go after signing in: only a path on this site */
const safeNext = (v: unknown) => (typeof v === "string" && /^\/(?!\/)[\w\-/?=&.]*$/.test(v) && v.length < 200 ? v : null);

/** an order's way from paid to the door, for the little line under it */
const STEPS: Stage[][] = [["paid"], ["printing"], ["shipped", "out"], ["delivered"]];
const STEP_WORD = ["in", "being made", "on its way", "with you"];
const stepOf = (s: Stage) => STEPS.findIndex((x) => x.includes(s));
const going = (o: OrderView) => ["paid", "printing", "shipped", "out", "attention"].includes(o.stage);

const monthYear = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { month: "short", year: "numeric", timeZone: "Asia/Kolkata" }).toLowerCase();

/**
 * The account: signed out, one sign-in that also makes an account (email, then a code); signed in, a profile with
 * the orders, the saved addresses and the details, each a tab, and every order placed with this email.
 */
export default async function AccountPage({ searchParams }: { searchParams: Promise<{ next?: string | string[] }> }) {
  if (!accountsOpen()) notFound();
  const next = safeNext((await searchParams).next);
  const email = await sessionEmail().catch(() => null);
  if (!email) {
    return (
      <div className="grid grid-cols-1 gap-x-4 px-4 pt-6 pb-24 md:grid-cols-12">
        <div className="md:col-span-7">
          <h1 className="page-in bigword text-[22vw] md:text-[11vw]">sign in</h1>
          <p className="page-in-2 mt-6 max-w-[40ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">
            or make an account: it&apos;s the same thing. your email, then a code we send to it. no password to remember.
          </p>
          <ul className="page-in-2 mt-10 hidden max-w-[44ch] text-[14px] md:block">
            {[
              ["every order in one place", "where each one is, its tracking, its receipt, and order it again in a tap"],
              ["checkout fills itself in", "your name, mobile and the places you send shirts to"],
              ["stays signed in", "on this device for as long as you keep coming back"],
            ].map(([t, s]) => (
              <li key={t} className="border-t border-line py-3"><span className="text-ink">{t}</span><span className="block text-quiet">{s}</span></li>
            ))}
          </ul>
        </div>
        <div className="page-in-3 mt-12 md:col-span-4 md:col-start-9 md:mt-[min(12vw,190px)]"><SignIn next={next} /></div>
      </div>
    );
  }

  const [a, ids] = await Promise.all([loadAccount(email), accountOrders(email).catch(() => [] as string[])]);
  const orders = (await Promise.all(ids.slice(0, 50).map((id) => loadOrder(id).catch(() => null))))
    .filter((o) => o && o.stage !== "paying" && o.contact.email === email)
    .map((o) => view(o!, true));
  const now = orders.filter(going), before = orders.filter((o) => !going(o));
  const shirts = orders.filter((o) => o.stage !== "cancelled").reduce((n, o) => n + o.lines.reduce((m, l) => m + l.quantity, 0), 0);
  const name = a?.name?.trim() ?? "";
  const first = name.split(" ")[0]?.toLowerCase();

  const orderList = orders.length === 0 ? (
    <div className="border-t border-line pt-6">
      <p className="text-[22px] leading-tight font-semibold tracking-[-0.02em]">nothing yet.</p>
      <p className="mt-2 max-w-[40ch] text-[15px] text-quiet">each order you place with {email} shows here, from print to your door.</p>
      <Link href="/shop" className="mt-6 inline-flex h-12 items-center gap-6 bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90">see the shirts <span aria-hidden>→</span></Link>
    </div>
  ) : (
    <div className="grid gap-12">
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
          <h1 className="truncate text-[40px] leading-[0.95] font-extrabold tracking-[-0.045em] md:text-[64px]">{first ? `hi ${first}.` : "your account."}</h1>
          <p className="mt-2 truncate text-[14px] text-quiet">{email}</p>
        </div>
      </header>
      <dl className="page-in-2 mt-8 grid max-w-[560px] grid-cols-3 border-t border-line pt-3 text-[13px] text-quiet">
        <div><dt>orders</dt><dd className="tnum text-[22px] font-semibold text-ink">{orders.length}</dd></div>
        <div><dt>shirts</dt><dd className="tnum text-[22px] font-semibold text-ink">{shirts}</dd></div>
        <div><dt>here since</dt><dd className="text-[22px] font-semibold text-ink">{a?.createdAt ? monthYear(a.createdAt) : "today"}</dd></div>
      </dl>

      <div className="page-in-3 mt-12">
        <AccountTabs
          counts={{ orders: orders.length, addresses: a?.addresses.length ?? 0 }}
          orders={orderList}
          addresses={<Addresses list={a?.addresses ?? []} />}
          details={<div className="grid max-w-[560px] gap-14"><Profile name={name} phone={a?.phone ?? ""} email={email} /><Leave email={email} /></div>}
        />
      </div>
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
      </div>
    </li>
  );
}
