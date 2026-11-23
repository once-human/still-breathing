const r = figma.createRectangle(); r.resize(20,20);
const b = await r.exportAsync({format:"PNG"}); r.remove();
return {bytes:b.length, page: figma.currentPage.name};
