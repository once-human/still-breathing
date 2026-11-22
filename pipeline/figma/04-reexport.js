const pb = figma.currentPage.children.find(n => n.name === "PROOF / back / light ink · black tee");
return { png64: { "proof-back-light": figma.base64Encode(await pb.exportAsync({ format: "PNG", constraint: { type: "SCALE", value: 0.4 } })) } };
