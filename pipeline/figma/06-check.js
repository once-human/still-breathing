const back = figma.currentPage.children.find(n => n.name === "PRINT / back / light ink · black tee");
const front = figma.currentPage.children.find(n => n.name === "PRINT / front / light ink · black tee");
return { back: back.children.map(c => [c.name, c.type, c.children ? c.children.length : 0]), front: front.children.map(c => [c.name, c.children ? c.children.length : 0]),
  proofs: figma.currentPage.children.filter(n => n.name.startsWith("PROOF")).map(n => [n.name, n.children[0].type, n.children[0].mainComponent && n.children[0].mainComponent.id]),
  comps: figma.currentPage.children.filter(n => n.type === "COMPONENT").map(n => [n.name, n.id]), total: figma.currentPage.children.length };
