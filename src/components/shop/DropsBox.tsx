"use client";

/** the one box for new-drop emails, the same at checkout and on joining */
export function DropsBox({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="mt-5 flex cursor-pointer items-start gap-3 border border-line p-3 text-[14px] hover:border-quiet">
      <input type="checkbox" checked={on} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--ink)]" />
      <span><span className="text-ink">tell me when a new drop comes out</span><span className="block text-[13px] text-quiet">one email per drop, nothing else. off with one tap from any of them.</span></span>
    </label>
  );
}

