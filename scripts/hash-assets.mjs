// Every file under public/tee gets a short hash of its bytes, written to src/lib/asset-hashes.json. The site asks
// for /tee/... ?v=<hash>: a file that changes gets a new address, so no browser can ever mix a cached old frame
// or texture with new ones, while files that didn't change stay cached. Runs before dev, build and typecheck.
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = "public", out = {};
const walk = (d) => {
  for (const f of readdirSync(d).sort()) {
    const p = join(d, f);
    if (statSync(p).isDirectory()) walk(p);
    else out["/" + relative(root, p).split("\\").join("/")] = createHash("sha1").update(readFileSync(p)).digest("base64url").slice(0, 8);
  }
};
walk(join(root, "tee"));
writeFileSync("src/lib/asset-hashes.json", JSON.stringify(out) + "\n");
console.log(`hashed ${Object.keys(out).length} files`);
