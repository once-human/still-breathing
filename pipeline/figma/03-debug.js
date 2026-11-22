const page = figma.currentPage;
const back = page.children.find(n => n.name === "PRINT / back / light ink · black tee");
const g = back.children[0];
const mask = g.children[0], art = g.children[1];
const img = figma.getImageByHash(mask.fills[0].imageHash);
const size = img ? await img.getSizeAsync() : null;
mask.isMask = false; mask.visible = false;
const noMask = figma.base64Encode(await back.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: 0.4 } }));
mask.visible = true; mask.isMask = true;
return { groupKids: g.children.map(c => [c.name, c.type, c.isMask, c.visible, Math.round(c.width), Math.round(c.height)]),
  artKids: art.children.length, artBox: [art.x, art.y, art.width, art.height], maskBox: [mask.x, mask.y, mask.width, mask.height], imgSize: size,
  png64: { "back-nomask": noMask } };
