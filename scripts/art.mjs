// The prints for the shirt cards' hover, uncropped: each shirt's whole front print area (30 x 50 cm, the chest mark in
// its real place) and whole back print area (38.1 x 50.8 cm), from the same files the 3D prints with
// (public/tee/fit/tex), at one scale (15 px per cm) so the two sides compare true. Clear background: the card lays them
// on the shirt's own colour. Written to public/tee/art/<design>-front.webp and -back.webp. Run again when a print
// changes:  node scripts/art.mjs
import sharp from "sharp";
import { mkdirSync, readFileSync, existsSync } from "node:fs";

const PX_PER_CM = 15;
const SIDES = { front: [30, 50], back: [38.1, 50.8] };
const tee = readFileSync("src/content/tee.ts", "utf8");
const shirts = [...tee.matchAll(/^\s+(\w): \{ no: "\d+", slug: "[\w-]+", name: "[^"]+", city: [^,]+, colour: "(\w+)"/gm)].map((m) => ({ d: m[1], colour: m[2] }));
mkdirSync("public/tee/art", { recursive: true });

for (const { d, colour } of shirts) {
  for (const [side, [w, h]] of Object.entries(SIDES)) {
    const src = `public/tee/fit/tex/print-${side}-${d}-${colour}.webp`;
    if (!existsSync(src)) { console.warn("no print", src); continue; }
    await sharp(src)
      .resize({ width: Math.round(w * PX_PER_CM), height: Math.round(h * PX_PER_CM), fit: "fill" })
      .webp({ quality: 74, alphaQuality: 80, effort: 6 })
      .toFile(`public/tee/art/${d}-${side}.webp`);
    console.log("art", d, side);
  }
}
