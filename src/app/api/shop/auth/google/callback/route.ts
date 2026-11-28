import { NextResponse } from "next/server";
import { loadAccount, openSession, validEmail } from "@/lib/shop/account";
import { accountsOpen } from "@/lib/shop/config";
import { googleFinish } from "@/lib/shop/google";
import { clientIp, limited } from "@/lib/shop/guard";
import { askedFrom } from "@/lib/visits/ua";

export const dynamic = "force-dynamic";

/** back from Google: a verified email signs in (making the account if it's new), unless its owner turned Google off */
export async function GET(req: Request) {
  const u = new URL(req.url);
  const back = (path: string) => NextResponse.redirect(new URL(path, u), { headers: { "Cache-Control": "no-store" } });
  if (!accountsOpen() || u.searchParams.get("error")) return back("/profile?e=google-cancelled");
  if (await limited(`acct-google:${clientIp(req.headers) ?? "?"}`, 20, 900_000)) return back("/profile?e=slow");
  const g = await googleFinish(u.searchParams).catch((e) => { console.error("google sign-in:", e); return null; });
  if (!g || !validEmail(g.email)) return back("/profile?e=google-failed");
  if ((await loadAccount(g.email))?.googleOff) return back("/profile?e=google-off");
  const v = await openSession(g.email, "google", askedFrom(req), g.name);
  return back(v.fresh ? `/profile?hello=1${g.next ? `&next=${encodeURIComponent(g.next)}` : ""}` : g.next ?? "/profile");
}
