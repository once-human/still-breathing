/** The giant lowercase word. `marquee` runs it endlessly across the screen. */
export function BigWord({ word, as: Tag = "p", marquee = false, className = "" }: { word: string; as?: "p" | "h1" | "h2"; marquee?: boolean; className?: string }) {
  if (marquee) {
    const run = Array.from({ length: 6 }, () => word).join(" ");
    return (
      <Tag className={`bigword overflow-hidden ${className}`} aria-label={word}>
        <span aria-hidden className="flex w-max animate-[marquee_46s_linear_infinite]">
          <span className="pr-[0.3em]">{run}</span>
          <span className="pr-[0.3em]">{run}</span>
        </span>
      </Tag>
    );
  }
  return <Tag className={`bigword ${className}`}>{word}</Tag>;
}
