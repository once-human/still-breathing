const page = figma.root.children.find((p) => p.name === params.page);
await page.loadAsync();
const comp = page.children.find((n) => n.type === "COMPONENT" && n.name.includes("front") && n.name.includes("black"));
const t0 = Date.now ? 0 : 0;
const times = {};
let s = Date.now(); const a = await comp.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: 1 } }); times.front1x = Math.round(Date.now() - s);
const back = page.children.find((n) => n.type === "COMPONENT" && n.name.includes("back") && n.name.includes("black"));
const kids = back.children.map((c) => [c.name, c.type, c.children ? c.children.length : 0]);
return { times, kids, bytes: a.length };
