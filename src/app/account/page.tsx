import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Reorder } from "@/components/shop/Reorder";
import { accountOrders, loadAccount, sessionEmail } from "@/lib/shop/account";
import { accountsOpen } from "@/lib/shop/config";
import { rupees } from "@/lib/shop/money";
import { loadOrder, view } from "@/lib/shop/orders";
import { STAGE_WORD, dayYear } from "@/lib/shop/words";
import { Addresses, Profile, SignIn, SignOut } from "./parts";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "account", robots: { index: false, follow: false } };

/** where to go after signing in: only a path on this site */
const safeNext = (v: unknown) => (typeof v === "string" && /^\/(?!\/)[\w\-/?=&.]*$/.test(v) && v.length < 200 ? v : null);

/**
 * The account: signed out, the email-code sign in; signed in, the profile, saved addresses and every order placed
 * with this email, each with where it is and a way to order it again.
 */
export default async function AccountPage({ searchParams }: { searchParams: Promise<{ next?: string | string[] }> }) {
  if (!accountsOpen()) notFound();
  const next = safeNext((await searchParams).next);
  const email = await sessionEmail().catch(() => null);
  if (!email) {
    return (
      <div className="px-4 pt-6 pb-24">
        <h1 className="page-in bigword text-[20vw] md:text-[13vw]">sign in</h1>
        <p className="page-in-2 mt-6 max-w-[44ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">
          no password: put in your email and we send you a code. you see every order you&apos;ve placed with it, and checkout fills itself in.
        </p>
        <div className="page-in-3 mt-12"><SignIn next={next} /></div>
      </div>
    );
  }

  const [a, ids] = await Promise.all([loadAccount(email), accountOrders(email).catch(() => [] as string[])]);
  const orders = (await Promise.all(ids.slice(0, 50).map((id) => loadOrder(id).catch(() => null))))
    .filter((o) => o && o.stage !== "paying" && o.contact.email === email)
    .map((o) => view(o!, true));

  return (
    <div className="grid grid-cols-1 gap-x-4 px-4 pt-6 pb-24 md:grid-cols-12">
      <div className="md:col-span-12">
        <p className="page-in border-t border-line pt-1.5 text-[13px] text-quiet">signed in as {email}</p>
        <h1 className="page-in mt-5 text-[46px] leading-[0.9] font-extrabold tracking-[-0.045em] lg:text-[72px]">{a?.name ? `hi ${a.name.split(" ")[0].toLowerCase()}.` : "your account."}</h1>
      </div>

      <section className="page-in-2 mt-12 md:col-span-7" aria-labelledby="orders">
        <h2 id="orders" className="border-t border-line pt-1.5 text-[13px] text-quiet">your orders · {orders.length}</h2>
        {orders.length === 0 ? (
          <p className="mt-4 text-[15px] text-ink/85">nothing yet. <Link href="/lineup-01" className="draw">the shirts →</Link></p>
        ) : (
          <ul className="mt-2 text-[14px]">
            {orders.map((o) => (
              <li key={o.id} className="border-b border-line py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <Link href={`/order/${o.id}`} className="draw font-semibold tnum">#{o.id}</Link>
                  <span className={o.stage === "attention" ? "text-ink" : "text-quiet"}>{STAGE_WORD[o.stage]}</span>
                </div>
                <p className="mt-1 text-quiet">{dayYear(o.placed)} · {o.lines.map((l) => `${l.name} ${l.size}${l.quantity > 1 ? ` × ${l.quantity}` : ""}`).join(", ")} · <span className="tnum">{rupees(o.total)}</span></p>
                <div className="mt-1 flex gap-4 text-[13px] text-quiet">
                  <Link href={`/order/${o.id}`} className="hit hover:text-ink">details</Link>
                  {o.tracking?.url && <a href={o.tracking.url} target="_blank" rel="noreferrer noopener" className="hit hover:text-ink">track ↗</a>}
                  <Link href={`/order/${o.id}/receipt`} className="hit hover:text-ink">receipt</Link>
                  <Reorder lines={o.lines} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="page-in-3 mt-12 md:col-span-4 md:col-start-9">
        <Profile name={a?.name ?? ""} phone={a?.phone ?? ""} />
        <div className="mt-10"><Addresses list={a?.addresses ?? []} /></div>
        <div className="mt-10 border-t border-line pt-1.5 text-[13px] text-quiet"><SignOut /></div>
      </div>
    </div>
  );
}
