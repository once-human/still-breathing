import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Label } from "@/components/Label";
import { POLICIES, POLICIES_READY, POLICIES_UPDATED, POLICY_ORDER, type PolicySlug } from "@/content/policies";
import { pageMeta } from "@/lib/site";
import { shopOpen } from "@/lib/shop/config";

type Params = { params: Promise<{ slug: string }> };

export const dynamicParams = false;
export const generateStaticParams = () => POLICY_ORDER.map((slug) => ({ slug }));

/** a policy only while the shop's words are complete (who runs it, where, how to write): until then, no page */
const find = async (params: Params["params"]) => {
  const slug = (await params).slug as PolicySlug;
  return POLICIES_READY && POLICY_ORDER.includes(slug) ? POLICIES[slug] : null;
};

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const p = await find(params);
  if (!p) return {};
  return pageMeta({ title: p.title, description: p.summary.charAt(0).toUpperCase() + p.summary.slice(1), path: `/policies/${p.slug}` });
}

/** The words are plain text: an email address becomes a link, and the /order path too while the shop is open (closed, it's a 404). */
const LINKY = /([\w.+-]+@[\w-]+(?:\.[\w-]+)+|\/order\b)/g;
function linked(text: string) {
  return text.split(LINKY).map((part, i) =>
    i % 2 === 0 ? part
      : part.startsWith("/") ? (shopOpen() ? <Link key={i} href={part}>{part}</Link> : part)
      : <a key={i} href={`mailto:${part.replace(/\.$/, "")}`}>{part}</a>,
  );
}

const day = (iso: string) => new Date(`${iso}T12:00:00+05:30`).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Kolkata" }).toLowerCase();

export default async function PolicyPage({ params }: Params) {
  const p = await find(params);
  if (!p) notFound();
  return (
    <div className="px-4 pt-6">
      <div className="page-in grid grid-cols-2 gap-4 border-t border-line pt-1.5 text-[13px] md:grid-cols-4">
        <span className="font-semibold">policies</span>
        <span className="text-right text-quiet md:text-left">updated {day(POLICIES_UPDATED)}</span>
      </div>
      <h1 className="page-in-2 bigword mt-6 text-[clamp(56px,13vw,220px)] leading-[0.85] whitespace-normal">{p.title}</h1>
      <p className="page-in-3 mt-8 max-w-[34ch] text-[clamp(20px,2.2vw,30px)] leading-[1.18] font-semibold tracking-[-0.02em]">{p.summary}</p>

      <div className="page-in-3 mt-20 grid grid-cols-1 gap-x-4 gap-y-14 md:grid-cols-12">
        <nav aria-label="Policies" className="text-[14px] md:sticky md:top-28 md:col-span-3 md:self-start lg:col-span-2 lg:col-start-2">
          <p className="border-t border-line pt-1.5 text-quiet">the small print</p>
          <ul className="mt-3 space-y-1">
            {POLICY_ORDER.map((s) => (
              <li key={s}>
                <Link href={`/policies/${s}`} aria-current={s === p.slug ? "page" : undefined} className={s === p.slug ? "font-semibold text-ink" : "draw text-quiet hover:text-ink"}>{POLICIES[s].title}</Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="space-y-14 md:col-span-9 lg:col-span-6 lg:col-start-5">
          {p.sections.map((s) => (
            <section key={s.heading}>
              <Label>{s.heading}</Label>
              <div className="prose-sb text-[15px] leading-relaxed">{s.body.map((b) => <p key={b.slice(0, 32)}>{linked(b)}</p>)}</div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
