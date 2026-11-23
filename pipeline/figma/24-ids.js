const out = {};
for (const name of ["mumbai · A · the ground", "mumbai · B · lines"]) {
  const pg = figma.root.children.find((p) => p.name === name); await pg.loadAsync();
  out[name] = pg.children.filter((n) => /^(PROOF|MOCKUP)/.test(n.name)).map((n) => [n.name, n.id]);
}
return out;
