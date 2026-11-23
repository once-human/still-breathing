// Export review PNGs of every PROOF / MOCKUP frame (params.only: optional name filter, params.scale)
const out = {};
const page = figma.root.children.find((p) => p.name === (params.page || "tee"));
await page.loadAsync();
for (const n of page.children) {
  if (!/^(PROOF|MOCKUP)/.test(n.name)) continue;
  if (params.only && !n.name.includes(params.only)) continue;
  const key = n.name.replace(/ · .*$/, "").replace(/[^a-z]+/gi, "-").toLowerCase() + (n.name.includes("light ink") ? "light" : "dark");
  const scale = n.name.startsWith("PROOF / front") ? 1 : (params.scale || 0.5);
  out[key] = figma.base64Encode(await n.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: scale } }));
}
return { png64: out };
