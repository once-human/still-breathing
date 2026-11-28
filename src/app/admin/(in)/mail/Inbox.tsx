import Link from "next/link";
import { BOXES } from "@/content/mail";
import { inboxCounts, threads } from "@/lib/shop/inbox";
import { FIELD } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Avatar, Empty, Group, Row, ago, dt } from "../../ui/ui";

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
const VIEWS = [["", "inbox"], ["unread", "unread"], ["archived", "archived"], ["all", "everything"]] as const;

/** every email to any @sahn.in address, as conversations, newest first, by address, unread or archived, and searchable */
export async function Inbox({ sp }: { sp: Record<string, string | string[] | undefined> }) {
  const box = one(sp.box).toLowerCase().replace(/[^a-z0-9._-]/g, "").slice(0, 40);
  const view = (VIEWS.find(([k]) => k === one(sp.view))?.[0] ?? "") as "" | "unread" | "archived" | "all";
  const q = one(sp.q).trim().slice(0, 100);
  const [list, counts] = await Promise.all([threads({ box: box || undefined, view: view || "inbox", q: q || undefined }), inboxCounts()]);
  const qs = (o: Record<string, string>) => "?" + new URLSearchParams(Object.entries({ k: "inbox", box, view, q, ...o }).filter(([, v]) => v)).toString();
  const boxes = [...new Set([...Object.keys(BOXES), ...counts.map((c) => c.box)])];
  const unread = counts.reduce((t, c) => t + c.unread, 0);
  const of = (b: string) => counts.find((c) => c.box === b);

  return (
    <>
      <div className="-mx-4 mb-3 flex gap-2 overflow-x-auto px-4 text-[14px] [scrollbar-width:none] md:mx-0 md:flex-wrap md:px-0">
        {["", ...boxes].map((b) => {
          const n = b ? of(b)?.unread : unread;
          return (
            <Link key={b || "all"} href={qs({ box: b })} className={`shrink-0 rounded-full px-4 py-1.5 ${box === b ? "bg-ink font-semibold text-paper" : "bg-s1 text-ink/80 hover:bg-s2"}`}>
              {b ? `${b}@` : "every address"}{n ? <span className="tnum ml-1.5 opacity-70">{n}</span> : null}
            </Link>
          );
        })}
      </div>
      <div className="mb-6 flex flex-wrap items-center gap-2 text-[13px]">
        {VIEWS.map(([k, label]) => (
          <Link key={k} href={qs({ view: k })} className={`rounded-full px-3 py-1 ${view === k ? "bg-s3 font-semibold text-ink" : "text-quiet hover:text-ink"}`}>{label}</Link>
        ))}
      </div>
      <form method="get" className="relative mb-8">
        <input type="hidden" name="k" value="inbox" />
        {box ? <input type="hidden" name="box" value={box} /> : null}
        {view ? <input type="hidden" name="view" value={view} /> : null}
        <Icon name="search" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-quiet" />
        <input name="q" defaultValue={q} placeholder="search who, a subject or words" className={`${FIELD} !pl-12`} />
      </form>
      {list.length ? (
        <Group>
          {list.map((t) => (
            <Row key={t.id} href={`/admin/mail/${t.id}`}
              title={<span className="flex items-center gap-4"><Avatar name={t.name || t.email} tone={t.unread ? "blue" : "quiet"} />
                <span className="min-w-0">
                  <span className={`block truncate ${t.unread ? "font-semibold" : ""}`}>{t.name || t.email}{t.count > 1 ? <span className="text-quiet"> · {t.count}</span> : null}</span>
                  <span className="block truncate text-[14px]">{t.subject || "(no subject)"}</span>
                  <span className="block truncate text-[13px] text-quiet">{t.snippet}</span>
                </span></span>}
              right={<span className="grid justify-items-end gap-1 text-[13px] text-quiet">
                <span title={dt(t.at)} className={t.unread ? "font-semibold text-ink" : ""}>{ago(t.at)}</span>
                <span>{t.box}@</span>
              </span>} />
          ))}
        </Group>
      ) : <Empty icon="mail" title={q ? "nothing matches" : view === "unread" ? "nothing unread" : "no emails here yet"} sub={q || view ? undefined : "once sahn.in's mail comes through resend, every email to any address lands here."} />}
    </>
  );
}
