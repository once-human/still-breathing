import { SHOP } from "@/content/shop";
import { rupees } from "@/lib/shop/money";

/** Three plain facts in a row, under a rule each: what it costs, how it gets to you, what it is. */
export function Facts({ className = "" }: { className?: string }) {
  const facts = [
    { k: `${rupees(SHOP.price)} a shirt`, v: "tax included, nothing added at checkout" },
    { k: "free delivery", v: "anywhere in india, with tracking" },
    { k: "made to order", v: "made for you, with you in about 10 days" },
    { k: "heavy cotton", v: "240 gsm, cut loose, pre-shrunk" },
  ];
  return (
    <ul className={`grid grid-cols-2 gap-x-4 gap-y-6 text-[14px] md:grid-cols-4 ${className}`}>
      {facts.map((f) => (
        <li key={f.k} className="border-t border-line pt-1.5">
          <span className="block font-semibold">{f.k}</span>
          <span className="block text-quiet">{f.v}</span>
        </li>
      ))}
    </ul>
  );
}
