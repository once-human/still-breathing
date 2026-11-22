// Set text in a font, export its outlines as SVG (params: text, family, style, size, ls)
await figma.loadFontAsync({ family: params.family, style: params.style });
const t = figma.createText();
t.fontName = { family: params.family, style: params.style }; t.fontSize = params.size; t.characters = params.text;
if (params.ls != null) t.letterSpacing = { unit: "PERCENT", value: params.ls };
figma.currentPage.appendChild(t);
const svg = await t.exportAsync({ format: "SVG_STRING", svgOutlineText: true });
const box = [t.width, t.height];
t.remove();
return { svg, box };
