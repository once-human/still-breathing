/** while a page's numbers load: a thin line along the top, and only if it's taking more than a moment */
export default function Loading() {
  return (
    <div aria-busy="true" aria-label="loading" className="a-loading fixed inset-x-0 top-0 z-50 h-[2px] overflow-hidden md:left-60">
      <span className="block h-full w-2/5 bg-ink/70" />
    </div>
  );
}
