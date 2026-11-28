import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, isPaid, shirtName } from "@/lib/admin/data";
import { notesFor } from "@/lib/admin/log";
import { deviceCounts, linkedPeople, loadAccount, passwordSetAt, validEmail } from "@/lib/shop/account";
import { refunded } from "@/lib/shop/orders";
import { Act, NoteForm } from "../../../ui/client";
import { Empty, Group, KV, Page, Row, Section, StageBadge, Tile, ago, dateOnly, dt, inr } from "../../../ui/ui";

export const metadata = { title: "person" };
export const dynamic = "force-dynamic";

/** one person: who they are, their orders, their account and saved addresses, what you can do, your notes */
export default async function Person({ params }: { params: Promise<{ email: string }> }) {
  await requireAdmin();
  const email = decodeURIComponent((await params).email).toLowerCase();
  if (!validEmail(email)) notFound();
  const [account, orders, notes, sess, browsers, pw] = await Promise.all([
    loadAccount(email).catch(() => null), allOrders(), notesFor(`customer:${email}`),
    deviceCounts(email), linkedPeople(email), passwordSetAt(email).catch(() => null),
  ]);
  const mine = orders.filter((o) => o.contact.email === email);
  if (!account && !mine.length) notFound();
  const paid = mine.filter(isPaid);
  const spend = paid.reduce((t, o) => t + o.total - refunded(o), 0);
  const name = account?.name || mine[0]?.contact.name || email.split("@")[0];
  const phone = account?.phone || mine[0]?.contact.phone;
  const devices = sess.get(email) ?? 0;
  const shirts = paid.filter((o) => o.stage !== "cancelled").reduce((t, o) => t + o.lines.reduce((u, l) => u + l.quantity, 0), 0);

  return (
    <>
      <Page title={name.toLowerCase()} back={["/admin/people", "people"]} sub={`${email}${account ? ", has an account" : ", ordered as a guest"}`} />

      <div className="mb-10 grid grid-cols-2 gap-3 md:mb-12 lg:grid-cols-3">
        <Tile label="spent" icon="money" value={inr(spend)} sub="after refunds" />
        <Tile label="orders" icon="orders" value={paid.length} sub={`${shirts} shirt${shirts === 1 ? "" : "s"}${mine.length > paid.length ? `, ${mine.length - paid.length} not paid` : ""}`} />
        <Tile label="last order" icon="clock" value={mine[0] ? ago(mine[0].createdAt) : "–"} sub={mine.length ? `first ${dateOnly(mine[mine.length - 1].createdAt)}` : "none yet"} />
      </div>

      <Section title="orders">
        {mine.length ? (
          <Group>
            {mine.map((o) => (
              <Row key={o.id} icon="bag" href={`/admin/orders/${o.id}`}
                title={o.lines.map((l) => `${shirtName(l.design)} ${l.size}${l.quantity > 1 ? ` ×${l.quantity}` : ""}`).join(", ")}
                sub={<>{dt(o.createdAt)} · <span className="font-mono">{o.id}</span></>}
                right={<span className="grid justify-items-end gap-1.5"><span className="tnum">{inr(o.total)}</span><StageBadge stage={o.stage} /></span>} />
            ))}
          </Group>
        ) : <Empty icon="orders" title="no orders yet" sub="they made an account but haven't bought" />}
      </Section>

      <div className="grid gap-x-6 lg:grid-cols-2">
        <Section title="contact">
          <KV items={[
            ["email", <a key="e" href={`mailto:${email}`} className="underline decoration-ink/25 underline-offset-4 hover:decoration-ink">{email}</a>],
            ["phone", phone ? <a key="p" href={`tel:+91${phone}`} className="underline decoration-ink/25 underline-offset-4 hover:decoration-ink">+91 {phone}</a> : "–"],
            ["account", account ? `since ${dateOnly(account.createdAt)}` : "none"],
            ...(account ? [["signed in on", devices ? `${devices} device${devices === 1 ? "" : "s"}` : "no device now"] as [string, string]] : []),
            ...(account ? [["signs in with", ["email code", pw ? "password" : "", account.google && !account.googleOff ? "google" : ""].filter(Boolean).join(", ")] as [string, string]] : []),
          ]} />
          {browsers.size ? (
            <div className="mt-3"><Group>
              {[...browsers.keys()].map((id, i) => <Row key={id} icon="visitors" title={browsers.size > 1 ? `their visits, browser ${i + 1}` : "their visits"} sub="pages, time on each, shirts looked at" href={`/admin/visitors/person/${id}`} />)}
            </Group></div>
          ) : null}
        </Section>
        <Section title="saved addresses">
          {account?.addresses.length ? (
            <Group>
              {account.addresses.map((a) => (
                <Row key={a.id} icon="pin" title={`${a.name}, ${a.city}`} sub={`${a.address1}${a.address2 ? `, ${a.address2}` : ""}, ${a.state} ${a.pin} · +91 ${a.phone}`} />
              ))}
            </Group>
          ) : <Empty icon="pin" title="none saved" sub={account ? undefined : "guests don't keep addresses"} />}
        </Section>
      </div>

      <Section title="manage" aside="each asks first, and goes in the audit log">
        <Group>
          {account ? (
            <Act label="edit name and phone" row={{ icon: "edit", sub: "the account's own; past orders keep what was on them" }} confirm="the account's own name and phone (their past orders keep what was on them)."
              url="/api/admin/customers" body={{ action: "edit", email }}
              fields={[{ name: "name", label: "name", initial: account.name }, { name: "phone", label: "phone (10 digits)", initial: account.phone, optional: true }]} />
          ) : null}
          {account ? <Act label="sign them out everywhere" row={{ icon: "signout", sub: devices ? `ends ${devices} session${devices === 1 ? "" : "s"}` : "no sessions open now" }} confirm={`every session of ${email}, on every device, ends now. they sign in again with a code.`} url="/api/admin/customers" body={{ action: "signout", email }} /> : null}
          <Act danger label="delete this person" row={{ icon: "trash", sub: "account, addresses, sessions and unpaid orders; can't be undone" }} typeToConfirm="DELETE" url="/api/admin/customers" body={{ action: "delete", email }} goTo="/admin/people"
            confirm={`wipe ${email} for good: the account, saved addresses, sessions, and their orders that were never paid or were cancelled. a paid order still going stops it. it can't be brought back.`} />
        </Group>
      </Section>

      <Section title="notes" aside="only you see these">
        {notes.length ? (
          <Group className="mb-4">
            {notes.map((n) => <Row key={n.id} icon="note" title={n.text} sub={dt(n.at)} />)}
          </Group>
        ) : null}
        <NoteForm url="/api/admin/customers" body={{ action: "note", email }} />
      </Section>
    </>
  );
}
