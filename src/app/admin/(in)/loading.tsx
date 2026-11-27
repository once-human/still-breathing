/** shown the instant a page is opened, while its numbers load: the page's outline in grey */
export default function Loading() {
  const block = "animate-pulse rounded-[22px] bg-s1";
  return (
    <div aria-busy="true" aria-label="loading">
      <div className="mb-9 h-12 w-56 animate-pulse rounded-2xl bg-s1 md:mb-12 md:h-14" />
      <div className="mb-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <div key={i} className={`${block} h-36`} />)}
      </div>
      <div className={`${block} mb-10 h-64`} />
      <div className={`${block} h-48`} />
    </div>
  );
}
