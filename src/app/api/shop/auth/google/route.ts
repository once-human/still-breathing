import { NextResponse } from "next/server";
import { accountsOpen } from "@/lib/shop/config";
import { googleStart } from "@/lib/shop/google";

export const dynamic = "force-dynamic";

const safeNext = (v: string | null) => (v && /^\/(?!\/)[\w\-/?=&.]*$/.test(v) && v.length < 200 ? v : null);

/** off to Google to pick an account; back at /profile with a word if Google sign-in isn't set up */
export async function GET(req: Request) {
  const u = new URL(req.url);
  const to = accountsOpen() ? await googleStart(safeNext(u.searchParams.get("next"))) : null;
  return NextResponse.redirect(to ?? new URL("/profile?e=google", u), { headers: { "Cache-Control": "no-store" } });
}
