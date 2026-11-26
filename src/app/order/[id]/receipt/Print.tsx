"use client";

export function Print() {
  return <button type="button" onClick={() => window.print()} className="hit hover:text-ink print:hidden">print or save as pdf</button>;
}
