import { NextResponse } from "next/server";
import { askedFrom } from "@/lib/visits/ua";
import { requestLink, useLink } from "@/lib/admin/auth";
import { ipOf, sameOrigin } from "@/lib/shop/guard";

export const dynamic = "force-dynamic";

const answer = (body: unknown, status = 200) => NextResponse.json(body, { status, headers: { "Cache-Control": "no-store" } });

/**
 * { email }: email a sign-in link if it's the admin's address (the answer is the same either way).
 * { token }: the link's token from the confirm page → the session cookie.
 */
export async function POST(req: Request) {
  if (!sameOrigin(req)) return answer({ error: "not from this site" }, 403);
  if (!req.headers.get("content-type")?.startsWith("application/json")) return answer({ error: "json only" }, 415);
  const text = await req.text();
  if (text.length > 1000) return answer({ error: "too big" }, 413);
  let b: { email?: unknown; token?: unknown };
  try {
    b = JSON.parse(text);
  } catch {
    return answer({ error: "bad json" }, 400);
  }
  const ip = ipOf(req);
  if (typeof b.token === "string") {
    const done = await useLink(b.token, ip, req.headers.get("user-agent") ?? "", askedFrom(req)).catch((e) => {
      console.error("admin login:", e);
      return false;
    });
    return done ? answer({ ok: true }) : answer({ error: "that link is used, old or wrong: ask for a new one" }, 400);
  }
  if (typeof b.email === "string" && b.email.length <= 120) {
    await requestLink(b.email, ip, askedFrom(req)).catch((e) => console.error("admin link:", e));
    // the same answer, after about the same time, whoever asked
    await new Promise((r) => setTimeout(r, 300 + Math.random() * 300));
    return answer({ ok: true });
  }
  return answer({ error: "email needed" }, 400);
}
