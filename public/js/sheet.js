// The garment sheet: colourway, UC22 sizes, a tech flat drawn from the real pattern, fit, print and cloth facts.
// the 3D studio is optional: the sheet works on its own and talks to it only if it loaded
let studio = { setTee() {} };
import("./studio.js").then((m) => { studio = m.studio; }).catch((e) => console.warn("studio failed", e));

const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const [S, FIT] = await Promise.all([fetch("tee/fred/sizes.json").then((r) => r.json()), fetch("tee/fred/fit.json").then((r) => r.json())]);
const ORDER = ["XS", "S", "M", "L", "XL", "2XL"];
const TEE = { black: { fill: "#151515", line: "#4a4844", ink: "#4C66F5", name: "Black" }, cream: { fill: "#FFFAE7", line: "#b9b2a2", ink: "#2C46BE", name: "Off White" } };
let size = "M", tee = "black";
const SLOPE = 3.2, ARMHOLE = 25;      // pattern.py

// ---------- colour ----------
document.querySelectorAll("#swatches button").forEach((b) => b.addEventListener("click", () => {
  tee = b.dataset.tee; document.querySelectorAll("#swatches button").forEach((x) => x.classList.toggle("on", x === b));
  studio.setTee(tee); drawFlat(); drawPrint();
}));

// ---------- sizes ----------
for (const s of ORDER) {
  const b = document.createElement("button"); b.textContent = s; b.classList.toggle("on", s === size);
  if (S.sizes[s].simulated) { b.classList.add("sim"); b.title = "Simulated in 3D"; }
  b.addEventListener("click", () => { size = s; document.querySelectorAll("#sizes button").forEach((x) => x.classList.toggle("on", x === b)); render(); });
  $("sizes").appendChild(b);
}

function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent?.appendChild(e); return e; }
function dim(svg, x1, y1, x2, y2, label, side = -1) {
  // engineering dimension: extension ticks, arrowheads, label in the gap
  const g = el("g", { class: "dim" }, svg), horiz = Math.abs(y2 - y1) < 0.01;
  el("line", { x1, y1, x2, y2, stroke: "currentColor", "stroke-width": 0.25, "marker-start": "url(#ar)", "marker-end": "url(#ar)" }, g);
  const t = el("text", { x: (x1 + x2) / 2 + (horiz ? 0 : side * 1.6), y: (y1 + y2) / 2 + (horiz ? -1.1 : 0.9), "font-size": 2.6, "text-anchor": horiz ? "middle" : side < 0 ? "end" : "start", fill: "currentColor", "font-family": "JetBrains Mono, monospace" }, g);
  t.textContent = label;
}
function drawFlat() {
  const svg = $("flat"), z = S.sizes[size], L = z.cm.length, HC = z.cm.chest_flat / 2, HS = z.cm.shoulder / 2, c = TEE[tee];
  svg.innerHTML = "";
  svg.style.color = "#5d5a54";
  const defs = el("defs", {}, svg);
  const m = el("marker", { id: "ar", viewBox: "0 0 6 6", refX: 3, refY: 3, markerWidth: 3.2, markerHeight: 3.2, orient: "auto-start-reverse" }, defs);
  el("path", { d: "M0 0 L6 3 L0 6 z", fill: "currentColor" }, m);
  const P = (pts) => pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)} ${(L - y).toFixed(2)}`).join(" ") + "Z";
  // back panel peeks out above the front neckline, like a real flat lay
  el("path", { d: P(z.back), fill: c.fill, stroke: c.line, "stroke-width": 0.3, "stroke-linejoin": "round" }, svg);
  el("path", { d: P(z.front), fill: c.fill, stroke: c.line, "stroke-width": 0.3, "stroke-linejoin": "round" }, svg);
  // construction lines: rib seam, hem and sleeve stitch rows (dashed like a tech pack)
  const nw = S.neck.width / 2, fd = S.neck.front_drop, rib = S.neck.rib;
  const ribPath = Array.from({ length: 33 }, (_, i) => { const t = (i / 32) * Math.PI; return [Math.cos(t) * (nw + 0), fd * Math.sin(t) + 0]; });
  el("path", { d: "M" + ribPath.map(([x, y]) => `${x.toFixed(2)} ${(y + rib * 0.95).toFixed(2)}`).join(" L"), fill: "none", stroke: c.line, "stroke-width": 0.22, "stroke-dasharray": "0.6 0.5" }, svg);
  el("line", { x1: -HC, x2: HC, y1: L - 2.5, y2: L - 2.5, stroke: c.line, "stroke-width": 0.22, "stroke-dasharray": "0.6 0.5" }, svg);
  // front print, drawn at its true size and place
  el("rect", { x: 9.46 - 3.33, y: 10.86, width: 6.65, height: 7.39, fill: "none", stroke: c.ink, "stroke-width": 0.3, "stroke-dasharray": "1 0.6" }, svg);
  // dimensions
  dim(svg, -HS, -4.5, HS, -4.5, `shoulder ${z.cm.shoulder} cm`);
  const yc = SLOPE + ARMHOLE + 2.5;
  dim(svg, -HC, yc, HC, yc, `chest ${z.cm.chest_flat} cm flat`);
  dim(svg, -HC - 5, 0, -HC - 5, L, `${z.cm.length} cm`, -1);
  el("line", { x1: -HC - 6.5, x2: -nw, y1: 0, y2: 0, stroke: "currentColor", "stroke-width": 0.15, "stroke-dasharray": "0.5 0.5" }, svg);
  el("line", { x1: -HC - 6.5, x2: -HC, y1: L, y2: L, stroke: "currentColor", "stroke-width": 0.15, "stroke-dasharray": "0.5 0.5" }, svg);
  $("flatCap").textContent = `UC22 ${size} · flat lay · front · dashed = stitch rows & print area · neck ${S.neck.width} cm wide (est.)`;
}

function drawChart() {
  const t = $("chart"); t.innerHTML = "";
  const head = t.createTHead().insertRow(); head.insertCell().outerHTML = "<th>cm</th>";
  for (const s of ORDER) { const th = document.createElement("th"); th.textContent = s; th.className = s === size ? "on" : ""; head.appendChild(th); }
  const body = t.createTBody();
  for (const [label, k] of [["Chest, round", "chest_round"], ["Chest, flat", "chest_flat"], ["Length (HPS)", "length"], ["Shoulder", "shoulder"]]) {
    const r = body.insertRow(); r.insertCell().textContent = label;
    for (const s of ORDER) { const c = r.insertCell(); c.textContent = S.sizes[s].cm[k]; c.className = s === size ? "on" : ""; }
  }
}

function drawFit() {
  const z = S.sizes[size], M = S.sizes.M, sim = z.simulated;
  const ease = z.cm.chest_round - FIT.body.chest_cm;
  const hem = FIT.hem_below_crotch_cm + (z.cm.length - M.cm.length);
  const shoulderDrop = (z.cm.shoulder / 2 - 19.3).toFixed(1);     // body.blend acromion sits 19.3 cm from centre
  $("fitBody").textContent = `${sim ? "Simulated" : "Estimated from the chart"} on a ${FIT.body.height_cm} cm, ${FIT.body.chest_cm} cm chest Indian male body.${sim ? "" : " The 3D view shows M."}`;
  const rows = [
    ["Room at the chest", `${ease > 0 ? "+" : ""}${ease.toFixed(0)} cm`],
    ["Hem", hem >= 0 ? `${hem.toFixed(0)} cm below the crotch` : `${(-hem).toFixed(0)} cm above the crotch`],
    ["Shoulder seam", `${shoulderDrop} cm down the arm`],
    ["Sleeve", sim ? `ends ${FIT.sleeve_above_elbow_cm} cm above the elbow` : "about the same as M (not graded by Qikink)"],
  ];
  $("fitFacts").innerHTML = rows.map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("");
  $("sizeNote").textContent = sim ? "● simulated" : "chart only";
}

function drawPrint() {
  // to scale, cm: DTG max box vs the A3 tier vs our back print, plus the 4 in pocket box for the front
  const svg = $("printbox"), c = TEE[tee]; svg.innerHTML = "";
  svg.setAttribute("viewBox", "-2 -6 104 58"); svg.style.color = "#5d5a54";
  const k = 1;
  const box = (x, y, w, h, stroke, dash, label, fill = "none") => {
    el("rect", { x, y, width: w * k, height: h * k, fill, stroke, "stroke-width": 0.35, "stroke-dasharray": dash || "" }, svg);
    if (label) { const t = el("text", { x: x + 0.8, y: y - 1, "font-size": 2.4, fill: "currentColor", "font-family": "JetBrains Mono, monospace" }, svg); t.textContent = label; }
  };
  box(0, 2, 35.6, 45.7, "currentColor", "1 0.7", "DTG max 35.6×45.7");
  box(2.95, 3.85, 29.7, 42, "currentColor", "0.4 0.6");
  box(3.45, 3.85, 28.7, 34.3, c.ink, "", "", tee === "black" ? "rgba(76,102,245,.12)" : "rgba(44,70,190,.10)");
  const t = el("text", { x: 17.8, y: 22, "font-size": 2.6, "text-anchor": "middle", fill: c.ink, "font-family": "JetBrains Mono, monospace" }, svg); t.textContent = "back ink 28.7×34.3";
  const a3 = el("text", { x: 17.8, y: 44.6, "font-size": 2.2, "text-anchor": "middle", fill: "currentColor", "font-family": "JetBrains Mono, monospace" }, svg); a3.textContent = "A3 tier 29.7×42";
  box(48, 2, 10.16, 10.16, "currentColor", "1 0.7", "pocket 4×4 in");
  box(49.75, 2.86, 6.65, 7.39, c.ink, "", "", tee === "black" ? "rgba(76,102,245,.12)" : "rgba(44,70,190,.10)");
  const f = el("text", { x: 53.1, y: 17, "font-size": 2.4, "text-anchor": "middle", fill: c.ink, "font-family": "JetBrains Mono, monospace" }, svg); f.textContent = "front ink 6.7×7.4";
  const n = el("text", { x: 48, y: 40, "font-size": 2.2, fill: "currentColor", "font-family": "JetBrains Mono, monospace" }, svg);
  n.textContent = "all boxes drawn to scale, cm";
  $("printFacts").innerHTML = [
    ["Method", "DTG, white underbase on dark"],
    ["Back ink", "28.7 × 34.3 cm · 3390 × 4051 px"],
    ["Back place", "ink starts 12.4 cm under the back neck"],
    ["Front ink", "6.7 × 7.4 cm · 785 × 873 px"],
    ["Front place", "wearer's left, 10.9 cm under the shoulder"],
    ["Resolution", "300 dpi PNG"],
    ["Ink blue", tee === "black" ? "#4C66F5" : "#2C46BE"],
    ["Halos", "knocked out, fabric shows through"],
  ].map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("");
}

$("fabric").innerHTML = [
  ["Blank", "Qikink UC22 Unisex Oversized"],
  ["Cloth", "100% super-combed cotton, single jersey"],
  ["Weight", "240 g/m²"],
  ["Knit", "≈14 wales · 18 courses per cm (est.)"],
  ["Neck", "Lycra rib, 2 cm (est.)"],
  ["Hems", "double-needle, two layers"],
  ["Shoulder", "dropped, sleeve set low on the arm"],
  ["Finish", "pre-shrunk, bio-washed"],
].map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("");

function render() { drawFlat(); drawChart(); drawFit(); }
render(); drawPrint();

fetch("version.json").then((r) => r.json()).then((v) => { $("version").textContent = `still breathing v${v.version}`; }).catch(() => {});
