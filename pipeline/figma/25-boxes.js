const pg = figma.root.children.find((p) => p.name === "mumbai · B · lines"); await pg.loadAsync();
const c = pg.children.find((n) => n.type === "COMPONENT" && n.name.includes("back") && n.name.includes("black"));
const o = c.absoluteTransform; const bx = (n) => { const b = n.absoluteBoundingBox; return [Math.round(b.x - o[0][2]), Math.round(b.y - o[1][2]), Math.round(b.width), Math.round(b.height)]; };
return c.children.map((n) => [n.name, n.type, bx(n), n.children ? n.children.map((k) => [k.name, k.type, bx(k)]).slice(0, 4) : null]);
