// Type sampler: which candidate fonts load in this Figma, and how they look.
const sets = {
  grotesk: [["Archivo", "Black"], ["Archivo", "ExtraBold"], ["Inter Tight", "Black"], ["Inter Tight", "Bold"], ["Space Grotesk", "Bold"],
            ["Familjen Grotesk", "Bold"], ["Bricolage Grotesque", "ExtraBold"], ["Schibsted Grotesk", "Black"], ["Hanken Grotesk", "Black"], ["Instrument Sans", "Bold"]],
  mono: [["IBM Plex Mono", "Medium"], ["JetBrains Mono", "Medium"], ["Space Mono", "Regular"], ["DM Mono", "Medium"], ["Martian Mono", "Medium"]],
  hand: [["Reenie Beanie", "Regular"], ["Nanum Pen Script", "Regular"], ["Covered By Your Grace", "Regular"], ["Caveat Brush", "Regular"],
         ["Gochi Hand", "Regular"], ["Rock Salt", "Regular"], ["Kalam", "Bold"], ["Shadows Into Light Two", "Regular"], ["Permanent Marker", "Regular"], ["Gaegu", "Bold"]],
};
const sample = { grotesk: "fred again..", mono: "08 DEC  MUMBAI  MAHALAXMI RACE COURSE", hand: "thank u, india  05 . 08 . 09 . 12 . 13" };
let page = figma.root.children.find((p) => p.name === "scratch");
if (!page) { page = figma.createPage(); page.name = "scratch"; }
await figma.setCurrentPageAsync(page);
for (const n of [...page.children]) n.remove();
const frame = figma.createFrame();
frame.name = "font sampler"; frame.fills = [{ type: "SOLID", color: { r: 0.08, g: 0.08, b: 0.08 } }];
frame.layoutMode = "VERTICAL"; frame.itemSpacing = 14; frame.paddingTop = frame.paddingBottom = frame.paddingLeft = frame.paddingRight = 40;
frame.primaryAxisSizingMode = "AUTO"; frame.counterAxisSizingMode = "AUTO";
await figma.loadFontAsync({ family: "Inter", style: "Regular" });
const ok = {}, missing = [];
for (const [kind, list] of Object.entries(sets)) {
  ok[kind] = [];
  for (const [family, style] of list) {
    try { await figma.loadFontAsync({ family, style }); } catch (e) { missing.push(family + " " + style); continue; }
    ok[kind].push(family + " " + style);
    const label = figma.createText(); label.fontName = { family: "Inter", style: "Regular" }; label.fontSize = 12;
    label.characters = `${kind} · ${family} ${style}`; label.fills = [{ type: "SOLID", color: { r: 0.55, g: 0.55, b: 0.55 } }];
    const t = figma.createText(); t.fontName = { family, style };
    t.fontSize = kind === "grotesk" ? 72 : kind === "mono" ? 26 : 44;
    t.characters = sample[kind]; t.fills = [{ type: "SOLID", color: { r: 0.94, g: 0.91, b: 0.85 } }];
    frame.appendChild(label); frame.appendChild(t);
  }
}
const bytes = await frame.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: 0.6 } });
return { ok, missing, png64: { fonts: figma.base64Encode(bytes) } };
