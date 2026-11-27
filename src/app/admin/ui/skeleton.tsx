/**
 * The outline of a page while its numbers load, shown the instant it's opened (each route's loading.tsx): the
 * page's name, then the shape of what's coming, in the cards' own grey with a slow shimmer.
 */
const B = "animate-pulse bg-s1";

function Head({ back, sub = true }: { back?: boolean; sub?: boolean }) {
  return (
    <div className="mb-9 md:mb-12">
      {back ? <div className={`${B} mb-4 h-4 w-20 rounded-[6px]`} /> : null}
      <div className={`${B} h-11 w-56 rounded-[10px] md:h-[52px] md:w-72`} />
      {sub ? <div className={`${B} mt-4 h-4 w-full max-w-md rounded-[6px]`} /> : null}
    </div>
  );
}
const Chips = ({ n = 4 }: { n?: number }) => <div className={`${B} mb-8 h-11 rounded-[12px]`} style={{ width: `${n * 92}px`, maxWidth: "100%" }} />;
const Tiles = ({ n = 4 }: { n?: number }) => (
  <div className={`mb-10 grid grid-cols-2 gap-3 md:mb-12 ${n === 3 ? "lg:grid-cols-3" : "lg:grid-cols-4"}`}>
    {Array.from({ length: n }, (_, i) => <div key={i} className={`${B} h-[148px] rounded-[14px]`} />)}
  </div>
);
const Rows = ({ n = 6 }: { n?: number }) => (
  <div className="mb-10 divide-y divide-line/50 overflow-hidden rounded-[14px] bg-s1">
    {Array.from({ length: n }, (_, i) => (
      <div key={i} className="flex min-h-[68px] items-center gap-4 px-5 py-3.5">
        <div className="h-10 w-10 shrink-0 animate-pulse rounded-full bg-s2" />
        <div className="grid flex-1 gap-2"><div className="h-3.5 w-2/5 animate-pulse rounded-[4px] bg-s2" /><div className="h-3 w-3/5 animate-pulse rounded-[4px] bg-s2" /></div>
        <div className="h-3.5 w-14 animate-pulse rounded-[4px] bg-s2" />
      </div>
    ))}
  </div>
);
const Title = () => <div className={`${B} mb-3 ml-1 h-4 w-28 rounded-[6px]`} />;
const Card = ({ h = "h-64" }: { h?: string }) => <div className={`${B} mb-10 ${h} rounded-[14px]`} />;

export type SkeletonKind = "dash" | "list" | "detail" | "form" | "cards" | "live";

export function Skeleton({ kind }: { kind: SkeletonKind }) {
  return (
    <div aria-busy="true" aria-label="loading">
      {kind === "dash" ? (
        <><Head /><Chips /><Tiles /><div className="grid gap-x-6 lg:grid-cols-[1fr_1.25fr]"><div><Title /><Card /></div><div><Title /><Card /></div></div></>
      ) : kind === "list" ? (
        <><Head /><Chips n={5} /><div className={`${B} mb-8 h-12 rounded-[10px]`} /><Rows n={8} /></>
      ) : kind === "detail" ? (
        <><Head back /><Tiles n={3} /><Title /><Rows n={3} /><div className="grid gap-x-6 lg:grid-cols-2"><div><Title /><Rows n={3} /></div><div><Title /><Rows n={3} /></div></div></>
      ) : kind === "form" ? (
        <><Head /><Title /><Rows n={3} /><Title /><Rows n={4} /></>
      ) : kind === "cards" ? (
        <><Head /><div className="grid gap-3 md:grid-cols-2">{Array.from({ length: 6 }, (_, i) => <div key={i} className={`${B} h-[150px] rounded-[14px]`} />)}</div></>
      ) : (
        <><Head /><Tiles n={3} /><Title /><Rows n={4} /></>
      )}
    </div>
  );
}
