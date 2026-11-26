import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, isPaid, shirtName } from "@/lib/admin/data";
import { notesFor } from "@/lib/admin/log";
import { loadAccount, validEmail } from "@/lib/shop/account";
import { refunded } from "@/lib/shop/orders";
import { NoteForm } from "../../../ui/client";
import { A, KV, PageHead, Section, StageBadge, Table, dateOnly, dt, inr } from "../../../ui/ui";

export const metadata = { title: "customer" };

export default async function Customer({ params }: { params: Promise<{ email: string }> }) {
  await requireAdmin();
  const email = decodeURIComponent((await params).email).toLowerCase();
  if (!validEmail(email)) notFound();
  const [account, orders, notes] = await Promise.all([loadAccount(email).catch(() => null), allOrders(), notesFor(`customer:${email}`)]);
  const mine = orders.filter((o) => o.contact.email === email);
  if (!account && !mine.length) notFound();
  const paid = mine.filter(isPaid);
  const spend = paid.reduce((t, o) => t + o.total - refunded(o), 0);
  const name = account?.name || mine[0]?.contact.name || email;

  return (
    <>
      <PageHead title={name} sub={`${paid.length} paid order${paid.length === 1 ? "" : "s"} · ${inr(spend)} lifetime`} />
      <div className="grid gap-x-12 lg:grid-cols-2">
        <Section title="contact">
          <KV items={[
            ["email", <a key="e" href={`mailto:${email}`} className="underline decoration-line">{email}</a>],
            ["phone", account?.phone || mine[0]?.contact.phone ? `+91 ${account?.phone || mine[0]?.contact.phone}` : "–"],
            ["account", account ? `since ${dateOnly(account.createdAt)}` : "no account (ordered as a guest)"],
            ["first order", mine.length ? dt(mine[mine.length - 1].createdAt) : "–"],
          ]} />
        </Section>
        <Section title="saved addresses">
          {account?.addresses.length ? (
            <ul className="grid gap-3 text-[13px]">
              {account.addresses.map((a) => <li key={a.id}>{a.name}, {a.address1}{a.address2 ? `, ${a.address2}` : ""}, {a.city}, {a.state} {a.pin} <span className="text-quiet">· +91 {a.phone}</span></li>)}
            </ul>
          ) : <p className="text-[13px] text-quiet">none saved</p>}
        </Section>
      </div>
      <Section title="orders">
        <Table head={["order", "placed", "shirts", "total", "stage"]} empty="no orders">
          {mine.map((o) => (
            <tr key={o.id}>
              <td><A href={`/admin/orders/${o.id}`} className="font-mono">{o.id}</A></td>
              <td className="text-quiet">{dt(o.createdAt)}</td>
              <td>{o.lines.map((l) => `${shirtName(l.design)} ${l.size}${l.quantity > 1 ? ` ×${l.quantity}` : ""}`).join(", ")}</td>
              <td className="tnum">{inr(o.total)}</td>
              <td><StageBadge stage={o.stage} /></td>
            </tr>
          ))}
        </Table>
      </Section>
      <Section title="notes">
        {notes.length ? <ul className="mb-4 grid gap-2 text-[13px]">{notes.map((n) => <li key={n.id}><span className="text-quiet">{dt(n.at)}</span> · {n.text}</li>)}</ul> : null}
        <NoteForm url="/api/admin/customers" body={{ email }} />
      </Section>
    </>
  );
}
