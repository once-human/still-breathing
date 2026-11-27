export const dynamic = "force-dynamic";

/** The old visit counter's address. The site now logs visits at /api/track; a page still open from before is answered and ignored. */
export async function POST() {
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}
