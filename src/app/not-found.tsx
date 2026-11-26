import Link from "next/link";
import { CURRENT, shirtHref, shirtsOf } from "@/content/lineups";
import { named, shownList } from "@/lib/live";

export const metadata = { title: "not here", robots: { index: false } };

/** A wrong address: say so plainly, then give the way back in. */
export default async function NotFound() {
  const shirts = await Promise.all((await shownList()).filter((d) => shirtsOf(CURRENT).includes(d)).map(async (d) => ({ d, label: (await named(d)).label })));
  return (
    <div className="px-4 pt-6">
      <div className="page-in grid grid-cols-2 gap-4 border-t border-line pt-1.5 text-[13px] md:grid-cols-4">
        <span className="font-semibold">404</span>
        <span className="text-right text-quiet md:text-left">nothing at this address</span>
      </div>
      <h1 className="page-in-2 bigword mt-6 text-[24vw] md:text-[17vw]">not here..</h1>
      <p className="page-in-3 mt-8 max-w-[40ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">
        this page doesn&apos;t exist, or it moved when the shop got its own pages. the shirts are all still here.
      </p>
      <div className="page-in-3 mt-12 grid grid-cols-1 gap-x-4 gap-y-8 md:grid-cols-12">
        <ul className="text-[clamp(26px,3.4vw,48px)] leading-[1.05] font-extrabold tracking-[-0.045em] md:col-span-6">
          <li><Link href="/" className="hover:text-blue">home</Link></li>
          <li><Link href="/shop" className="hover:text-blue">shop</Link></li>
          <li><Link href={`/${CURRENT.slug}`} className="hover:text-blue">{CURRENT.title}</Link></li>
          <li><Link href="/help" className="hover:text-blue">help</Link></li>
        </ul>
        <ul className="space-y-1 text-[15px] md:col-span-4 md:col-start-8">
          {shirts.map(({ d, label }) => <li key={d} className="border-t border-line pt-1"><Link href={shirtHref(d)} className="hover:text-blue">{label}</Link></li>)}
        </ul>
      </div>
    </div>
  );
}
