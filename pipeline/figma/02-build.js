// Fred again.. India tour fan tee — full build. Re-runnable: wipes and rebuilds the "tee" page.
// params: maskBack, maskFront (base64 PNG), dates (array of [day, city, venue]), stage ("all")

// ---------- helpers ----------
const hex = (h) => { const n = parseInt(h.slice(1), 16); return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 }; };
const toHex = (c) => "#" + [c.r, c.g, c.b].map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
const solid = (c) => ({ type: "SOLID", color: c });
const G = { family: "Schibsted Grotesk", style: "Black" };
const M = { family: "IBM Plex Mono", style: "Medium" };
const H = { family: "Covered By Your Grace", style: "Regular" };
for (const f of [G, M, H]) await figma.loadFontAsync(f);

function rng(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function txt(parent, s, font, size, color, x, y, o = {}) {
  const t = figma.createText();
  t.fontName = font; t.fontSize = size; t.characters = s; t.fills = [solid(color)];
  if (o.ls != null) t.letterSpacing = { unit: "PERCENT", value: o.ls };
  if (o.lh != null) t.lineHeight = { unit: "PERCENT", value: o.lh };
  t.textAutoResize = "WIDTH_AND_HEIGHT";
  parent.appendChild(t);
  t.x = o.right != null ? o.right - t.width : x; t.y = y;
  if (o.rot) t.rotation = o.rot;
  t.name = o.name || s.slice(0, 40);
  return t;
}
// jittered points -> smooth cubic path (Catmull-Rom), so no two marks are identical
function handPath(pts, jitter, r) {
  const q = pts.map(([x, y]) => [x + (r() - 0.5) * 2 * jitter, y + (r() - 0.5) * 2 * jitter]);
  let d = `M${q[0][0].toFixed(1)} ${q[0][1].toFixed(1)}`;
  for (let i = 0; i < q.length - 1; i++) {
    const p0 = q[Math.max(0, i - 1)], p1 = q[i], p2 = q[i + 1], p3 = q[Math.min(q.length - 1, i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}
// draw marker strokes in the parent's own coordinate space
function marker(parent, W, Hh, paths, color, width, name) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${Hh}" viewBox="0 0 ${W} ${Hh}">` +
    paths.map((d) => `<path d="${d}" fill="none" stroke="${toHex(color)}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"/>`).join("") + `</svg>`;
  const f = figma.createNodeFromSvg(svg);
  const kids = [...f.children];
  parent.appendChild(f); f.x = 0; f.y = 0;
  const g = figma.group(kids, parent); g.name = name;
  f.remove();
  return g;
}
function wordmark(parent, width, x, y, p, name) {
  const t = txt(parent, "fred again..", G, 200, p.ink, x, y, { ls: -3, lh: 100, name });
  t.fontSize = 200 * (width / t.width);
  t.setRangeFills(10, 12, [solid(p.red)]);
  return t;
}
function wearMask(comp, w, h, b64) {
  const m = figma.createRectangle();
  m.resize(w, h); m.name = "wear (mask)";
  const img = figma.createImage(b64ToBytes(b64));
  m.fills = [{ type: "IMAGE", scaleMode: "FILL", imageHash: img.hash }];
  comp.appendChild(m);
  return m;
}

// small mono text stays out of the wear mask: wear on tiny type reads as a misprint
function keepClean(comp, art, W, Hh) {
  const clean = figma.createFrame(); clean.name = "clean (small type)"; clean.resize(W, Hh); clean.fills = []; clean.clipsContent = false;
  comp.appendChild(clean);
  for (const n of [...art.children]) if (n.type === "TEXT" && n.fontName.family === "IBM Plex Mono") clean.appendChild(n);
}
// ---------- palettes ----------
const PAL = {
  light: { key: "light", label: "light ink · black tee", tee: hex("#151515"), ink: hex("#EEE7D7"), red: hex("#E4432D"), dim: hex("#8E897F") },
  dark: { key: "dark", label: "dark ink · cream tee", tee: hex("#ECE3CE"), ink: hex("#1C1A17"), red: hex("#CF3A25"), dim: hex("#857D6D") },
};
const DATES = params.dates;

// ---------- back: 1200 x 1600 = 30 x 40 cm (export 3x ≈ 305 dpi) ----------
function buildBack(p, seed) {
  const W = 1200, Hh = 1600, L = 80, R = 1120;
  const r = rng(seed);
  const comp = figma.createComponent();
  comp.name = `PRINT / back / ${p.label}`; comp.resize(W, Hh); comp.fills = []; comp.clipsContent = true;
  const mask = wearMask(comp, W, Hh, params.maskBack);
  const art = figma.createFrame(); art.name = "art"; art.resize(W, Hh); art.fills = []; art.clipsContent = false;
  comp.appendChild(art);

  const wm = wordmark(art, R - L, L - 6, 64, p, "wordmark");
  const sub = wm.y + wm.height + 18;
  txt(art, "LIVE IN INDIA", M, 24, p.ink, L, sub, { ls: 14 });
  txt(art, "DEL / BOM / BLR", M, 24, p.dim, 0, sub, { ls: 14, right: R + 4 });

  // dates table
  const top = sub + 100, rowH = 150;
  const rule = (y) => { const l = figma.createRectangle(); l.resize(R - L, 3); l.x = L; l.y = y; l.fills = [solid(p.dim)]; l.name = "rule"; art.appendChild(l); };
  rule(top - 18);
  DATES.forEach(([day, city, venue], i) => {
    const y = top + i * rowH;
    txt(art, day, G, 132, p.ink, L - 6, y - 8, { ls: -4, lh: 100, name: `day ${day}` });
    txt(art, "DEC", M, 20, p.dim, L + 200, y + 18, { ls: 14 });
    txt(art, city, G, 62, p.ink, L + 290, y + 2, { ls: -2, lh: 100, name: `city ${city}` });
    txt(art, venue, M, 21, p.dim, L + 292, y + 84, { ls: 10 });
    rule(y + rowH - 18);
  });
  // hand ticks, one per night, each slightly different
  const ticks = DATES.map((_, i) => {
    const cy = top + i * rowH + 52;
    return handPath([[1046, cy + 2], [1062, cy + 22], [1100, cy - 30 + r() * 10]], 3.5, r);
  });
  marker(art, W, Hh, ticks, p.red, 9, "ticks");

  // marker note, crossing the last rule
  const tableEnd = top + DATES.length * rowH - 18;
  const noteY = tableEnd - 22;
  txt(art, "thank u, india", H, 92, p.red, 596, noteY, { rot: 4, name: "note" });
  marker(art, W, Hh, [handPath([[606, noteY + 112], [740, noteY + 104], [880, noteY + 94], [1010, noteY + 80]], 3, r)], p.red, 6, "underline");

  // voice memo of the crowd
  const wy = tableEnd + 134;
  const dot = figma.createEllipse(); dot.resize(16, 16); dot.x = L; dot.y = wy + 6; dot.fills = [solid(p.red)]; dot.name = "rec"; art.appendChild(dot);
  txt(art, "REC  CROWD, MAHALAXMI RACE COURSE  09.12.26", M, 20, p.ink, L + 28, wy, { ls: 10 });
  txt(art, "04:12", M, 20, p.dim, 0, wy, { ls: 10, right: R });
  const bars = 150, bw = 3.6, span = R - L, step = span / bars, mid = wy + 98, play = 0.62;
  // envelope: a few slow swells (songs, drops) plus per-bar flicker
  const sw = Array.from({ length: 6 }, () => [r() * bars, 8 + r() * 26, 0.35 + r() * 0.65]);
  const barNodes = [];
  for (let i = 0; i < bars; i++) {
    let e = 0.12;
    for (const [c, wdt, a] of sw) e += a * Math.exp(-((i - c) ** 2) / (2 * wdt * wdt));
    const h = Math.max(4, Math.min(1, e) * (0.55 + r() * 0.45) * 118);
    const b = figma.createRectangle();
    b.resize(bw, h); b.x = L + i * step; b.y = mid - h / 2; b.cornerRadius = 1.8;
    b.fills = [solid(i / bars < play ? p.ink : p.dim)];
    art.appendChild(b); barNodes.push(b);
  }
  figma.group(barNodes, art).name = "waveform";
  const ph = figma.createRectangle(); ph.resize(3, 150); ph.x = L + play * span; ph.y = mid - 75; ph.fills = [solid(p.red)]; ph.name = "playhead"; art.appendChild(ph);
  const phd = figma.createEllipse(); phd.resize(15, 15); phd.x = ph.x - 6; phd.y = ph.y - 12; phd.fills = [solid(p.red)]; art.appendChild(phd);
  txt(art, "02:36", M, 18, p.dim, L, mid + 80, { ls: 10 });
  txt(art, "-01:36", M, 18, p.dim, 0, mid + 80, { ls: 10, right: R });

  // sign-off
  txt(art, "FOR EVERYONE WHO SANG IT BACK", M, 22, p.ink, L, Hh - 74, { ls: 14 });
  txt(art, "FAN MADE", M, 22, p.dim, 0, Hh - 74, { ls: 14, right: R });

  const g = figma.group([mask, art], comp); g.name = "worn print";
  mask.isMask = true; mask.maskType = "ALPHA";
  keepClean(comp, art, W, Hh);
  return comp;
}

// ---------- front chest: 400 x 400 = 10 x 10 cm ----------
function buildFront(p, seed) {
  const W = 400, Hh = 400, r = rng(seed);
  const comp = figma.createComponent();
  comp.name = `PRINT / front / ${p.label}`; comp.resize(W, Hh); comp.fills = []; comp.clipsContent = true;
  const mask = wearMask(comp, W, Hh, params.maskFront);
  const art = figma.createFrame(); art.name = "art"; art.resize(W, Hh); art.fills = []; art.clipsContent = false;
  comp.appendChild(art);
  const wm = wordmark(art, 330, 34, 110, p, "wordmark");
  txt(art, "india '26", H, 74, p.red, 150, wm.y + wm.height - 10, { rot: 5, name: "india '26" });
  txt(art, "DEL / BOM / BLR", M, 15, p.dim, 38, wm.y - 30, { ls: 16 });
  const g = figma.group([mask, art], comp); g.name = "worn print";
  mask.isMask = true; mask.maskType = "ALPHA";
  keepClean(comp, art, W, Hh);
  return comp;
}

// ---------- tee mockup ----------
function teeSvg(color, back) {
  const neck = back ? "Q 500 92 620 62" : "Q 500 150 620 62";
  const d = `M 380 62 ${neck} L 790 100 L 968 262 L 884 400 L 796 344 L 806 1070 Q 500 1088 194 1070 L 204 344 L 116 400 L 32 262 L 210 100 Z`;
  const collar = back ? "M 380 62 Q 500 92 620 62" : "M 380 62 Q 500 150 620 62";
  const shade = { r: color.r * 0.82, g: color.g * 0.82, b: color.b * 0.82 };
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1100" viewBox="0 0 1000 1100"><path d="${d}" fill="${toHex(color)}"/>` +
    `<path d="${collar}" fill="none" stroke="${toHex(shade)}" stroke-width="22" stroke-linecap="round"/>` +
    `<path d="M 204 344 L 210 100 M 796 344 L 790 100" fill="none" stroke="${toHex(shade)}" stroke-width="3" opacity="0.6"/></svg>`;
}
function mockup(page, comp, p, back, x, y) {
  const f = figma.createFrame();
  f.name = `MOCKUP / ${back ? "back" : "front"} / ${p.label}`; f.resize(1100, 1200); f.x = x; f.y = y;
  f.fills = [solid(p.key === "light" ? hex("#E4E0D7") : hex("#B9B3A6"))];
  page.appendChild(f);
  const tee = figma.createNodeFromSvg(teeSvg(p.tee, back)); tee.name = "tee"; tee.fills = [];
  f.appendChild(tee); tee.x = 50; tee.y = 50;
  tee.effects = [{ type: "DROP_SHADOW", color: { r: 0, g: 0, b: 0, a: 0.22 }, offset: { x: 0, y: 14 }, radius: 36, spread: 0, visible: true, blendMode: "NORMAL" }];
  const inst = comp.createInstance();
  f.appendChild(inst);
  if (back) { inst.rescale(330 / 1200); inst.x = 50 + 500 - 165; inst.y = 50 + 170; }
  else { inst.rescale(118 / 400); inst.x = 50 + 548; inst.y = 50 + 215; }
  return f;
}
function proof(page, comp, p, x, y, pad) {
  const f = figma.createFrame();
  f.name = `PROOF / ${comp.name.replace("PRINT / ", "")}`; f.resize(comp.width + pad * 2, comp.height + pad * 2); f.x = x; f.y = y;
  f.fills = [solid(p.tee)];
  page.appendChild(f);
  const inst = comp.createInstance(); f.appendChild(inst); inst.x = pad; inst.y = pad;
  return f;
}

// ---------- assemble ----------
let page = figma.root.children.find((pg) => pg.name === "tee") || figma.root.children.find((pg) => pg.name === "Page 1");
page.name = "tee";
await figma.setCurrentPageAsync(page);
for (const n of [...page.children]) n.remove();

const comps = {};
let cx = -2900;
for (const p of [PAL.light, PAL.dark]) {
  const b = buildBack(p, p.key === "light" ? 11 : 11); page.appendChild(b); b.x = cx; b.y = 0;
  const fr = buildFront(p, 5); page.appendChild(fr); fr.x = cx; fr.y = 1700;
  comps[p.key] = { back: b, front: fr };
  cx += 1300;
}
let px = 0;
for (const p of [PAL.light, PAL.dark]) {
  proof(page, comps[p.key].back, p, px, 0, 50);
  proof(page, comps[p.key].front, p, px, 1760, 50);
  mockup(page, comps[p.key].back, p, true, px, 2400);
  mockup(page, comps[p.key].front, p, false, px, 3700);
  px += 1400;
}
figma.viewport.scrollAndZoomIntoView(page.children.filter((n) => n.name.startsWith("PROOF") || n.name.startsWith("MOCKUP")));
return { built: page.children.map((n) => n.name) };
