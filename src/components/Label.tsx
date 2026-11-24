/** A ruled label line that starts each part of the page, with an optional note on the right. */
export function Label({ children, note, id, className = "" }: { children: React.ReactNode; note?: React.ReactNode; id?: string; className?: string }) {
  return (
    <div id={id} className={`mb-6 flex scroll-mt-16 items-baseline justify-between gap-4 border-t border-ink pt-1.5 ${className}`}>
      <h2 className="font-semibold">{children}</h2>
      {note ? <span className="text-right text-quiet">{note}</span> : null}
    </div>
  );
}
