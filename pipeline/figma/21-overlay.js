// Export the vector layer (everything but the art) of PRINT components at full print scale.
// params: page, which: ["back","front"], scale
const page = figma.root.children.find((p) => p.name === params.page);
await page.loadAsync();
const out = {};
for (const comp of page.children.filter((n) => n.type === "COMPONENT")) {
  const side = comp.name.includes("/ back /") ? "back" : "front";
  if (params.which && !params.which.includes(side)) continue;
  const art = comp.children.find((c) => c.name === "art");
  if (art) art.visible = false;
  try {
    const bytes = await comp.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: params.scale || 3 } });
    out[`ov-${side}-${comp.name.includes("black") ? "black" : "cream"}`] = figma.base64Encode(bytes);
  } finally { if (art) art.visible = true; }
}
return { png64: out };
