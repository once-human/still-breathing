"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Countdown } from "@/components/Countdown";
import { BagSlot } from "@/components/ShopSlots";
import { setFocusCity } from "@/lib/city";
import { NAV, BRAND } from "@/lib/site";
import { CURRENT, fmtDays, paperStill, shirtHref, shirtLabel, shirtsOf, STILL_H, STILL_W } from "@/content/lineups";
import { DESIGNS } from "@/content/tee";

const cell = "border-t pt-1.5 truncate transition-colors duration-300";
const on = (path: string, href: string) => (href === "/" ? path === "/" : path === href || path.startsWith(href + "/"));

/**
 * The header: the brand, the pages, the next show and the bag, each under its own rule; the rule over the page you're
 * on turns blue. It slides away as you read down and comes back the moment you scroll up. Over lineup 01 it opens the
 * five shirts; on a phone everything is behind menu.
 */
export function Header() {
  const path = usePathname();
  const [menu, setMenu] = useState(false);
  const [shelf, setShelf] = useState(false);
  const [hidden, setHidden] = useState(false);
  const shelfT = useRef<ReturnType<typeof setTimeout>>(undefined);
  const isShirt = path.split("/").filter(Boolean).length === 2 && path.startsWith(`/${CURRENT.slug}/`);

  // a page that isn't one shirt speaks for the show nearest the visitor (a shirt page sets its own city)
  useEffect(() => { if (!isShirt) setFocusCity(null); }, [isShirt]);
  // a new page closes whatever was open and brings the header back
  useEffect(() => { setMenu(false); setShelf(false); setHidden(false); }, [path]);
  useEffect(() => {
    if (!menu) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setMenu(false);
    document.documentElement.classList.add("menu-open");
    addEventListener("keydown", esc);
    return () => { document.documentElement.classList.remove("menu-open"); removeEventListener("keydown", esc); };
  }, [menu]);
  useEffect(() => {
    let last = scrollY, raf = 0;
    const tick = () => {
      raf = 0;
      const y = scrollY, d = y - last;
      if (Math.abs(d) > 6) { setHidden(d > 0 && y > 120); last = y; }
    };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(tick); };
    addEventListener("scroll", onScroll, { passive: true });
    return () => { removeEventListener("scroll", onScroll); cancelAnimationFrame(raf); };
  }, []);

  const openShelf = () => { clearTimeout(shelfT.current); setShelf(true); };
  const closeShelf = () => { clearTimeout(shelfT.current); shelfT.current = setTimeout(() => setShelf(false), 160); };
  const rule = (href: string) => (on(path, href) ? "border-blue" : "border-line");

  return (
    <>
      <a href="#main" className="fixed top-2 left-2 z-[70] -translate-y-20 bg-ink px-3 py-2 text-[13px] text-paper focus:translate-y-0">skip to the page</a>
      <header
        className={`fixed inset-x-0 top-0 z-50 bg-paper/95 backdrop-blur-md transition-transform duration-500 ease-[cubic-bezier(.2,.7,.2,1)] ${hidden && !menu && !shelf ? "-translate-y-full" : ""}`}
        onMouseLeave={closeShelf}
      >
        <nav aria-label="Main" className="grid grid-cols-[1fr_auto_auto] items-end gap-3 px-4 pt-3 pb-2 text-[14px] md:grid-cols-7 md:gap-4 md:text-[15px] lg:grid-cols-9">
          <Link href="/" className={`${cell} ${path === "/" ? "border-blue" : "border-line"} font-semibold`}>{BRAND}</Link>

          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              onMouseEnter={"lineup" in n ? openShelf : closeShelf}
              onFocus={"lineup" in n ? openShelf : undefined}
              aria-expanded={"lineup" in n ? shelf : undefined}
              className={`${cell} ${rule(n.href)} hidden md:block ${n.href === "/size-guide" ? "md:hidden lg:block" : ""} ${on(path, n.href) ? "text-ink" : "text-quiet hover:text-ink"}`}
            >{n.label}</Link>
          ))}

          <span className={`${cell} border-line hidden text-quiet tnum lg:col-start-8 lg:block`}><Countdown short /></span>
          <span className={`${cell} border-line text-right md:col-start-7 lg:col-start-9`}><BagSlot /></span>
          <button
            onClick={() => setMenu(!menu)}
            aria-expanded={menu}
            aria-controls="menu"
            className={`${cell} ${menu ? "border-blue" : "border-line"} hit text-right font-semibold md:hidden`}
          >{menu ? "close" : "menu"}</button>
        </nav>

        {/* lineup 01's five shirts, under the header on a wide screen */}
        <div
          onMouseEnter={openShelf}
          onMouseLeave={closeShelf}
          className={`hidden overflow-hidden transition-[max-height,opacity] duration-500 ease-[cubic-bezier(.2,.7,.2,1)] md:block ${shelf ? "max-h-[60vh] opacity-100" : "pointer-events-none max-h-0 opacity-0"}`}
        >
          <div className="grid grid-cols-7 gap-4 border-b border-line px-4 pt-4 pb-5 lg:grid-cols-9">
            <div className="col-span-2 text-[13px]">
              <p className="font-semibold">lineup {CURRENT.no} · {CURRENT.title}</p>
              <p className="text-quiet">{CURRENT.tag} · {CURRENT.when}</p>
              <ul className="mt-4 space-y-0.5 text-quiet tnum">
                {CURRENT.shows.map((s) => <li key={s.city} className="flex justify-between gap-4"><span>{s.city}</span><span>{fmtDays(s.days)}</span></li>)}
              </ul>
              <Link href={`/${CURRENT.slug}`} tabIndex={shelf ? 0 : -1} className="mt-4 inline-block text-blue hover:text-ink">the whole lineup →</Link>
            </div>
            {shirtsOf(CURRENT).map((d) => (
              <Link key={d} href={shirtHref(d)} tabIndex={shelf ? 0 : -1} className="group col-span-1 text-[13px]">
                <span className="block overflow-hidden bg-studio">
                  {shelf ? <img src={paperStill(d, "back")} alt="" width={STILL_W} height={STILL_H} className="aspect-[880/1120] w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]" /> : <span className="block aspect-[880/1120]" />}
                </span>
                <span className="mt-1.5 flex gap-1.5"><span className="text-quiet tnum">{DESIGNS[d].no}</span><span className="truncate group-hover:text-blue">{shirtLabel(d)}</span></span>
              </Link>
            ))}
          </div>
        </div>
      </header>

      {/* the phone menu: the whole screen, big words */}
      <div
        id="menu"
        role="dialog"
        aria-modal="true"
        aria-label="Menu"
        hidden={!menu}
        className="fixed inset-0 z-40 overflow-y-auto overscroll-contain bg-paper px-4 pt-16 pb-8 md:hidden"
        data-lenis-prevent
      >
        <ul className="text-[clamp(34px,11vw,56px)] leading-[1.02] font-extrabold tracking-[-0.045em]">
          {[{ href: "/", label: "home" }, ...NAV].map((n, i) => (
            <li key={n.href} className="menu-in border-t border-line" style={{ animationDelay: `${i * 40}ms` }}>
              <Link href={n.href} className={`block py-1.5 ${on(path, n.href) ? "text-blue" : ""}`}>{n.label}</Link>
            </li>
          ))}
        </ul>
        <p className="mt-10 border-t border-line pt-1.5 text-[13px] text-quiet">lineup {CURRENT.no} · the shirts</p>
        <ul className="mt-3 grid grid-cols-5 gap-2">
          {shirtsOf(CURRENT).map((d) => (
            <li key={d}>
              <Link href={shirtHref(d)} className="block text-[11px] leading-tight">
                {menu ? <img src={paperStill(d, "back")} alt="" width={STILL_W} height={STILL_H} className="aspect-[880/1120] w-full bg-studio object-cover" /> : null}
                <span className="mt-1 block text-quiet tnum">{DESIGNS[d].no}</span>
                <span className="block">{shirtLabel(d)}</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-10 flex items-center gap-2 border-t border-line pt-1.5 text-[13px]"><span className="inline-block h-1.5 w-1.5 rounded-full bg-blue" /><Countdown /></p>
      </div>
    </>
  );
}
