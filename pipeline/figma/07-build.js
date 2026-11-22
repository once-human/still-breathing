// Fred again.. India tour fan tee — v2 after critique. Re-runnable: wipes and rebuilds the "tee" page.
// params: rows [{days:[..], city, venue}], circled ("09"), note, memo {name, when, length, elapsed, remaining}

// ---------- helpers ----------
const hex = (h) => { const n = parseInt(h.slice(1), 16); return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 }; };
const toHex = (c) => "#" + [c.r, c.g, c.b].map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
const solid = (c) => ({ type: "SOLID", color: c });
const G = { family: "Schibsted Grotesk", style: "Black" };
const H = { family: "Covered By Your Grace", style: "Regular" };
let M = { family: "IBM Plex Mono", style: "SemiBold" };
for (const f of [G, H]) await figma.loadFontAsync(f);
try { await figma.loadFontAsync(M); } catch (e) { M = { family: "IBM Plex Mono", style: "Medium" }; await figma.loadFontAsync(M); }

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
// handwriting: every letter its own node with its own size, tilt and baseline, so no two glyphs match
function handText(parent, s, size, color, x, y, rot, r, name) {
  const nodes = [];
  let cx = 0;
  for (const ch of s) {
    if (ch === " ") { cx += size * (0.24 + r() * 0.08); continue; }
    const t = figma.createText();
    t.fontName = H; t.fontSize = size * (0.95 + r() * 0.1); t.characters = ch; t.fills = [solid(color)];
    t.textAutoResize = "WIDTH_AND_HEIGHT";
    parent.appendChild(t);
    t.x = x + cx; t.y = y + (r() - 0.5) * size * 0.09 + (size - t.fontSize) * 0.6;
    t.rotation = (r() - 0.5) * 9;
    cx += t.width * (0.9 + r() * 0.08);
    nodes.push(t);
  }
  const g = figma.group(nodes, parent); g.name = name;
  g.rotation = rot;
  return g;
}
// sample a smooth (Catmull-Rom) curve through jittered points
function curve(pts, jitter, r, perSeg = 16) {
  const q = pts.map(([x, y]) => [x + (r() - 0.5) * 2 * jitter, y + (r() - 0.5) * 2 * jitter]);
  const out = [];
  for (let i = 0; i < q.length - 1; i++) {
    const p0 = q[Math.max(0, i - 1)], p1 = q[i], p2 = q[i + 1], p3 = q[Math.min(q.length - 1, i + 2)];
    for (let k = 0; k < perSeg; k++) {
      const t = k / perSeg, t2 = t * t, t3 = t2 * t;
      out.push([0, 1].map((a) => 0.5 * (2 * p1[a] + (-p0[a] + p2[a]) * t + (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t2 + (-p0[a] + 3 * p1[a] - 3 * p2[a] + p3[a]) * t3)));
    }
  }
  out.push(q[q.length - 1]);
  return out;
}
// marker stroke as a filled outline whose width swells and tapers like a real nib
function brushPath(pts, wMax, r, taperIn = 0.15, taperOut = 0.35) {
  const n = pts.length, L = [], R = [];
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
    const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1;
    const t = i / (n - 1);
    let w = wMax * (0.82 + r() * 0.18);
    if (t < taperIn) w *= 0.45 + 0.55 * (t / taperIn);
    if (t > 1 - taperOut) w *= 0.25 + 0.75 * ((1 - t) / taperOut);
    const nx = (-dy / len) * w / 2, ny = (dx / len) * w / 2;
    L.push([a[0] + (b[0] - a[0]) / 2 + nx, a[1] + (b[1] - a[1]) / 2 + ny]);
    R.push([a[0] + (b[0] - a[0]) / 2 - nx, a[1] + (b[1] - a[1]) / 2 - ny]);
  }
  const ring = L.concat(R.reverse());
  return "M" + ring.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(" L") + " Z";
}
function ink(parent, W, Hh, paths, color, name) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${Hh}" viewBox="0 0 ${W} ${Hh}">` +
    paths.map((d) => `<path d="${d}" fill="${toHex(color)}"/>`).join("") + `</svg>`;
  const f = figma.createNodeFromSvg(svg);
  parent.appendChild(f); f.x = 0; f.y = 0;
  const kids = [...f.children];
  const g = figma.group(kids, parent); g.name = name;
  f.remove();
  return g;
}
function wordmark(parent, width, x, y, p, ls, name) {
  const t = txt(parent, "fred again..", G, 200, p.ink, x, y, { ls, lh: 100, name });
  t.fontSize = 200 * (width / t.width);
  t.setRangeFills(10, 12, [solid(p.red)]);
  return t;
}
function rule(parent, p, x, y, w) {
  const l = figma.createRectangle(); l.resize(w, 5); l.x = x; l.y = y; l.fills = [solid(p.ink)]; l.name = "rule"; parent.appendChild(l);
}

// ---------- palettes: two inks + red; grey only for the unplayed part of the recording ----------
const PAL = {
  light: { key: "light", label: "light ink · black tee", tee: hex("#151515"), ink: hex("#EEE7D7"), red: hex("#E4432D"), dim: hex("#8E897F") },
  dark: { key: "dark", label: "dark ink · cream tee", tee: hex("#ECE3CE"), ink: hex("#1C1A17"), red: hex("#D8381F"), dim: hex("#857D6D") },
};

// ---------- back: 1200 x 1600 units = 30 x 40 cm ----------
function buildBack(p) {
  const W = 1200, Hh = 1600, L = 80, R = 1120;
  const r = rng(909);
  const comp = figma.createComponent();
  comp.name = `PRINT / back / ${p.label}`; comp.resize(W, Hh); comp.fills = []; comp.clipsContent = false;

  const wm = wordmark(comp, R - L, L - 6, 64, p, -3, "wordmark");
  const sub = wm.y + wm.height + 20;
  txt(comp, "DEC 2026", M, 24, p.ink, L, sub, { ls: 14 });
  txt(comp, "5 NIGHTS / 3 CITIES", M, 24, p.ink, 0, sub, { ls: 14, right: R + 4 });

  // dates: one row per city, paired nights stacked
  let y = sub + 86;
  rule(comp, p, L, y - 20, R - L);
  let circled = null;
  for (const row of params.rows) {
    const two = row.days.length > 1;
    const rowH = two ? 238 : 160;
    if (two) {
      row.days.forEach((d, k) => {
        const t = txt(comp, d, G, 114, p.ink, L - 5, y - 6 + k * 104, { ls: -4, lh: 100, name: `day ${d}` });
        if (d === params.circled) circled = t;
      });
    } else {
      const t = txt(comp, row.days[0], G, 132, p.ink, L - 6, y - 8, { ls: -4, lh: 100, name: `day ${row.days[0]}` });
      if (row.days[0] === params.circled) circled = t;
    }
    const cityY = y + rowH / 2 - 66;
    txt(comp, row.city, G, 70, p.ink, L + 262, cityY, { ls: 0, lh: 100, name: `city ${row.city}` });
    txt(comp, row.venue, M, 24, p.ink, L + 265, cityY + 86, { ls: 10 });
    y += rowH;
    rule(comp, p, L, y - 20, R - L);
  }
  const tableEnd = y - 20;

  // one night circled by hand: uneven loop that doesn't quite close
  if (circled) {
    const cx = circled.x + circled.width / 2 + 2, cy = circled.y + circled.height / 2 + 4;
    const rx = circled.width / 2 + 30, ry = circled.height / 2 + 6, start = -2.0, turns = 1.1, n = 15;
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const a = start + (i / n) * turns * 2 * Math.PI, grow = 1 + 0.07 * (i / n);
      pts.push([cx + Math.cos(a) * rx * grow * (0.97 + r() * 0.06), cy + Math.sin(a) * ry * grow * (0.95 + r() * 0.1)]);
    }
    ink(comp, W, Hh, [brushPath(curve(pts, 4, r, 10), 10, r, 0.06, 0.25)], p.red, "circle (hand)");
  }

  // the note, in its own space under the table
  const noteY = tableEnd + 34;
  const note = handText(comp, params.note, 92, p.red, 548, noteY, -4, r, "note (hand)");
  const ux0 = note.x + 10, ux1 = note.x + note.width + 34, uy = note.y + note.height + 4;
  ink(comp, W, Hh, [brushPath(curve([[ux0, uy + 10], [(ux0 + ux1) / 2, uy - 2], [ux1, uy - 22]], 3, r, 18), 8, r, 0.1, 0.55)], p.red, "underline (hand)");

  // voice memo, named the way a phone names it
  const wy = uy + 70;
  const dot = figma.createEllipse(); dot.resize(18, 18); dot.x = L; dot.y = wy + 7; dot.fills = [solid(p.red)]; dot.name = "rec"; comp.appendChild(dot);
  txt(comp, params.memo.name, M, 28, p.ink, L + 32, wy, { ls: 2 });
  txt(comp, params.memo.when, M, 22, p.ink, L + 32, wy + 40, { ls: 8 });
  txt(comp, params.memo.length, M, 24, p.ink, 0, wy + 2, { ls: 8, right: R });
  // envelope of a crowd coming in: murmur, then everyone at once at the playhead, holding, easing off
  const bars = 96, bw = 5.6, span = R - L, step = span / bars, mid = wy + 170, hit = 60, play = hit / bars;
  const barNodes = [];
  for (let i = 0; i < bars; i++) {
    let e;
    if (i < hit) e = 0.08 + 0.1 * Math.sin(i * 0.21 + r() * 2.5) ** 2 + (r() < 0.12 ? 0.12 + r() * 0.22 : r() * 0.07) + (i > hit - 6 ? (i - (hit - 6)) * 0.06 : 0);
    else if (i < 86) e = 0.78 + r() * 0.22 - (i - hit) * 0.004;
    else e = 0.75 - (i - 86) * 0.05 + r() * 0.15;
    const h = Math.max(12, Math.min(1, e) * 150);
    const b = figma.createRectangle();
    b.resize(bw, h); b.x = L + i * step; b.y = mid - h / 2;
    b.fills = [solid(i < hit ? p.ink : p.dim)];
    comp.appendChild(b); barNodes.push(b);
  }
  figma.group(barNodes, comp).name = "waveform";
  const phx = L + hit * step - 3;
  const ph = figma.createRectangle(); ph.resize(5, 176); ph.x = phx; ph.y = mid - 88; ph.fills = [solid(p.red)]; ph.name = "playhead"; comp.appendChild(ph);
  const phd = figma.createEllipse(); phd.resize(18, 18); phd.x = phx - 6.5; phd.y = ph.y - 14; phd.fills = [solid(p.red)]; comp.appendChild(phd);
  txt(comp, params.memo.elapsed, M, 22, p.ink, L, mid + 98, { ls: 8 });
  txt(comp, params.memo.remaining, M, 22, p.ink, 0, mid + 98, { ls: 8, right: R });

  txt(comp, "FOR EVERYONE WHO SANG IT BACK", M, 24, p.ink, L, Hh - 66, { ls: 14 });
  txt(comp, "FAN MADE", M, 24, p.ink, 0, Hh - 66, { ls: 14, right: R });
  return comp;
}

// ---------- front chest: 400 x 400 units = 10 x 10 cm ----------
function buildFront(p) {
  const W = 400, Hh = 400, r = rng(26);
  const comp = figma.createComponent();
  comp.name = `PRINT / front / ${p.label}`; comp.resize(W, Hh); comp.fills = []; comp.clipsContent = false;
  const wm = wordmark(comp, 330, 34, 128, p, -1, "wordmark");
  handText(comp, "india '26", 60, p.red, 136, wm.y + wm.height + 4, -3, r, "india '26 (hand)");
  return comp;
}

// ---------- tee mockup (placement preview only) ----------
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
  // 1 tee unit ≈ 0.93 mm at this mockup scale (tee chest ≈ 55 cm across 592 units)
  if (back) { inst.rescale(323 / 1200); inst.x = 50 + 500 - 161; inst.y = 50 + 62 + 86 - 17; }
  else { inst.rescale(108 / 400); inst.x = 50 + 556; inst.y = 50 + 190; }
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
  const b = buildBack(p); page.appendChild(b); b.x = cx; b.y = 0;
  const fr = buildFront(p); page.appendChild(fr); fr.x = cx; fr.y = 1700;
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
return { built: page.children.length };
