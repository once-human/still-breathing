/** The admin's two charts: people a day with the days an order came, and the way from coming in to paying. */

/** people a day as grey bars; a day an order came is drawn lighter with a dot over it */
export function DayChart({ days, mark = "a day an order came" }: { days: { day: string; people: number; orders: number }[]; mark?: string }) {
  const max = Math.max(1, ...days.map((d) => d.people));
  const fmt = (d: string) => new Date(`${d}T12:00:00+05:30`).toLocaleDateString("en-IN", { day: "numeric", month: "short" }).toLowerCase();
  if (!days.length) return null;
  return (
    <div>
      <div className="flex h-44 items-end gap-[3px] md:h-52" role="img" aria-label={`people a day, with ${mark}`}>
        {days.map((d) => (
          <div key={d.day} className="group relative flex h-full flex-1 flex-col justify-end" title={`${fmt(d.day)}: ${d.people} people${d.orders ? `, ${d.orders} order${d.orders > 1 ? "s" : ""}` : ""}`}>
            {d.orders ? <span className="absolute inset-x-0 top-0 mx-auto h-1.5 w-1.5 rounded-full bg-ink" /> : null}
            <div className={`w-full rounded-[4px] transition-colors ${d.orders ? "bg-ink/70" : "bg-s3 group-hover:bg-ink/35"}`} style={{ height: `${(d.people / max) * 88}%`, minHeight: 3 }} />
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-between text-[13px] text-quiet">
        <span>{fmt(days[0].day)}</span>
        <span className="hidden items-center gap-1.5 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-ink" />{mark}</span>
        <span>today</span>
      </div>
    </div>
  );
}

/** each step as a bar against everyone at the first, with how many went no further */
export function Funnel({ steps }: { steps: [string, number][] }) {
  const top = Math.max(1, steps[0]?.[1] ?? 0);
  return (
    <div className="grid gap-4">
      {steps.map(([label, n], i) => {
        const lost = i ? steps[i - 1][1] - n : 0;
        return (
          <div key={label}>
            <div className="flex items-baseline justify-between gap-4 text-[15px]">
              <span>{label}</span>
              <span className="tnum"><span className="font-semibold">{n}</span>{i && steps[0][1] ? <span className="ml-2 text-[13px] text-quiet">{Math.round((n / top) * 100)}%</span> : null}</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-s3"><div className="h-full rounded-full bg-ink/75" style={{ width: `${Math.max(n ? 2 : 0, (n / top) * 100)}%` }} /></div>
            {lost > 0 ? <div className="mt-1 text-[13px] text-quiet">{lost} stopped here</div> : null}
          </div>
        );
      })}
    </div>
  );
}
