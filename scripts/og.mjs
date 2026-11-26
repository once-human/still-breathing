// Open Graph pictures (1200 x 630) from the studio renders in public/tee/still, written to public/og as JPEG
// (WhatsApp, iMessage and the rest all read JPEG). Each shirt: its front and back on the studio paper, then worn at
// the show. A lineup (and the home page): every shirt's back side by side. Run again after the stills are re-rendered:
//   node scripts/og.mjs
import sharp from "sharp";
import { mkdirSync, readFileSync } from "node:fs";

const W = 1200, H = 630, BG = { r: 13, g: 13, b: 12 };
// the lineups and their shirts, read straight from the content so a new shirt needs no edit here
const tee = readFileSync("src/content/tee.ts", "utf8");
const slugs = Object.fromEntries([...tee.matchAll(/^\s+(\w): \{ no: "\d+", slug: "([\w-]+)"/gm)].map((m) => [m[1], m[2]]));
const lineups = readFileSync("src/content/lineups.ts", "utf8");
const groups = [...lineups.matchAll(/slug: "(lineup-\d+)"[\s\S]*?groups: \[([\s\S]*?)\n {4}\]/g)].map((m) => ({
  slug: m[1], shirts: [...m[2].matchAll(/shirts: \[([^\]]*)\]/g)].flatMap((g) => [...g[1].matchAll(/"(\w)"/g)].map((x) => x[1])),
}));

/** a still, scaled to the full height and cut to `w` wide around its middle */
const panel = async (file, w) => {
  const scaled = await sharp(file).resize({ height: H }).toBuffer({ resolveWithObject: true });
  const left = Math.max(0, Math.round((scaled.info.width - w) / 2));
  return sharp(scaled.data).extract({ left, top: 0, width: Math.min(w, scaled.info.width), height: H }).toBuffer();
};

const strip = async (files, out) => {
  const gap = 4, w = Math.floor((W - gap * (files.length - 1)) / files.length);
  const parts = await Promise.all(files.map((f) => panel(f, w)));
  await sharp({ create: { width: W, height: H, channels: 3, background: BG } })
    .composite(parts.map((input, i) => ({ input, left: i * (w + gap) + Math.floor((W - (w * files.length + gap * (files.length - 1))) / 2), top: 0 })))
    .jpeg({ quality: 86, mozjpeg: true })
    .toFile(out);
  console.log("og", out);
};

mkdirSync("public/og", { recursive: true });
const S = (d, p) => `public/tee/still/${d}/${p}.webp`;
for (const [d, slug] of Object.entries(slugs)) await strip([S(d, "tee/front"), S(d, "tee/back"), S(d, "a180")], `public/og/${slug}.jpg`);
for (const l of groups) await strip(l.shirts.map((d) => S(d, "tee/back")), `public/og/${l.slug}.jpg`);
if (groups[0]) await strip([S(groups[0].shirts[0], "a180"), ...groups[0].shirts.slice(1).map((d) => S(d, "tee/back"))], "public/og/home.jpg");
