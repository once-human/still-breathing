import { NextResponse } from "next/server";
import { askedFrom } from "@/lib/visits/ua";
import { signInWithKey } from "@/lib/admin/auth";
import { ipOf, sameOrigin } from "@/lib/shop/guard";

export const dynamic = "force-dynamic";

const answer = (body: unknown, status = 200) => NextResponse.json(body, { status, headers: { "Cache-Control": "no-store" } });

const SAY = {
  closed: ["the admin isn't set up on this deployment yet", 503],
  slow: ["too many wrong keys: sign-in is paused. try again later", 429],
  wrong: ["that isn't the key", 401],
} as const;

/** { key }: the site key → the session cookie */
export async function POST(req: Request) {
  if (!sameOrigin(req)) return answer({ error: "not from this site" }, 403);
  if (!req.headers.get("content-type")?.startsWith("application/json")) return answer({ error: "json only" }, 415);
  const text = await req.text();
  if (text.length > 1000) return answer({ error: "too big" }, 413);
  let b: { key?: unknown };
  try {
    b = JSON.parse(text);
  } catch {
    return answer({ error: "bad json" }, 400);
  }
  if (typeof b.key !== "string" || !b.key) return answer({ error: "the key is needed" }, 400);
  const r = await signInWithKey(b.key.trim(), ipOf(req), req.headers.get("user-agent") ?? "", askedFrom(req)).catch((e) => {
    console.error("admin login:", e);
    return "error" as const;
  });
  if (r === "ok") return answer({ ok: true });
  if (r === "error") return answer({ error: "that didn't go through: try again" }, 500);
  // a wrong key waits a moment, so guessing is slow as well as limited
  if (r === "wrong") await new Promise((res) => setTimeout(res, 400 + Math.random() * 300));
  return answer({ error: SAY[r][0] }, SAY[r][1]);
}
