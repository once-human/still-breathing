import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { box, type Box } from "@/content/mail";
import { OPERATOR } from "@/content/policies";
import { loadAccount, sessionEmail } from "@/lib/shop/account";
import { shopOpen } from "@/lib/shop/config";
import { pageMeta } from "@/lib/site";
import { MakerForm } from "./MakerForm";

export const metadata: Metadata = pageMeta({
  title: "contact",
  description: "Write to sahn: a size, an order, your data, or straight to the person who makes it. A person reads every email.",
  path: "/contact",
});
export const dynamic = "force-dynamic";

/** where to write, in the order people need it; drops@ only sends, so it isn't here */
const WRITE: { b: Box; what: string }[] = [
  { b: "hello", what: "a size, a question, press or stockists, anything at all." },
  { b: "orders", what: "an order: put its number in. a delivery, a fault, a return, a change." },
  { b: "privacy", what: "what we keep about you, a copy of it, fixing it or erasing it." },
  { b: "security", what: "a sign-in or a change to your profile that wasn't you." },
];

export default async function Contact() {
  const me = await sessionEmail().catch(() => null);
  const a = me ? await loadAccount(me).catch(() => null) : null;
  return (
    <div className="pt-6">
      <div className="px-4">
        <h1 className="page-in bigword text-[22vw] md:text-[15vw]">contact</h1>
        <p className="page-in-2 mt-8 max-w-[34ch] text-[18px] leading-snug md:text-[22px]">a person reads every email, and answers within 2 working days, usually sooner.</p>
      </div>
      <div className="page-in-3 mt-20 space-y-16 px-4">
        <section className="grid grid-cols-1 gap-x-4 md:grid-cols-12">
          <div className="md:col-span-8 lg:col-span-6 lg:col-start-2">
            <Label>write to us</Label>
            <ul className="divide-y divide-line border-b border-line">
              {WRITE.map(({ b, what }) => (
                <li key={b} className="grid gap-1 py-4 sm:grid-cols-[14rem_1fr] sm:gap-4">
                  <a href={`mailto:${box(b)}`} className="draw w-fit text-[16px] text-ink hover:text-blue">{box(b)}</a>
                  <span className="text-[15px] leading-relaxed text-quiet">{what}</span>
                </li>
              ))}
            </ul>
            {OPERATOR.phone ? <p className="mt-4 text-[15px]">or call {OPERATOR.phone}, 11 am – 7 pm, monday to saturday.</p> : null}
            <p className="mt-4 text-[15px] leading-relaxed text-quiet">
              {shopOpen() ? <>your order&apos;s page has where it is right now: open it from any order email, <Link href="/order" className="draw text-ink">find it here</Link>, or </> : null}
              sign in to <Link href="/profile" className="draw text-ink">your profile</Link> to see every order. how <Link href="/policies/refunds" className="draw text-ink">returns and refunds</Link> work.
            </p>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-x-4 md:grid-cols-12">
          <div className="md:col-span-8 lg:col-span-6 lg:col-start-2">
            <Label id="maker" note="one person makes sahn">write to the maker</Label>
            <div className="prose-sb mb-8 text-[15px] leading-relaxed">
              <p>if something&apos;s gone wrong and writing to us hasn&apos;t put it right, or it can&apos;t wait, write here. it goes straight to the person who draws, makes and sends every sahn shirt, nobody else reads it, and they write back themselves.</p>
              <p className="text-quiet">or email <a href={`mailto:${box("maker")}`}>{box("maker")}</a>.</p>
            </div>
            <MakerForm name={a?.name ?? ""} email={me ?? ""} />
          </div>
        </section>
      </div>
    </div>
  );
}

