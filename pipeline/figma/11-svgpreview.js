// Place an SVG on the scratch page over a background colour and export a PNG (params: svg, bg, fill, name)
const page = figma.root.children.find((p) => p.name === "scratch");
await page.loadAsync();
const old = page.children.find((n) => n.name === params.name); if (old) old.remove();
const n = figma.createNodeFromSvg(params.svg.replaceAll('fill="#000"', `fill="${params.fill}"`));
n.name = params.name; page.appendChild(n); n.x = 0; n.y = 3000;
const hex = (h) => { const v = parseInt(h.slice(1), 16); return { r: ((v >> 16) & 255) / 255, g: ((v >> 8) & 255) / 255, b: (v & 255) / 255 }; };
n.fills = [{ type: "SOLID", color: hex(params.bg) }];
return { png64: { [params.name]: figma.base64Encode(await n.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: 0.5 } })) } };
