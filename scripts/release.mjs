// npm run release [-- patch|minor|major|X.Y.Z] [--dry] [--no-push]
//
// Cuts a release from the "## Unreleased" block of CHANGELOG.md. Work goes live with every push; a release is cut
// once a set of changes is finished (a session, a finished shirt), not per push.
//
// The bump is read off the block's sections, by what a buyer would notice:
//   ### Lineup                        -> major   a new drop or lineup, or the shop working differently (checkout,
//                                                prices, a redesign)
//   ### New  /  ### Changed           -> minor   a new shirt, colour or feature; new art, lettering or a rename
//   ### Fixed                         -> patch   fixes and polish: copy, a render refresh, a layout bug
// Before 1.0.0 (launch) a major is held back to a minor; 1.0.0 itself is cut by name: npm run release -- 1.0.0
//
// It dates the block, writes VERSION and package.json, commits, tags vX.Y.Z, pushes, and makes the GitHub release
// with the block as its notes and the studio renders changed since the last release attached.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = process.argv.slice(2);
const dry = args.includes("--dry"), push = !args.includes("--no-push");
const pick = args.find((a) => !a.startsWith("--"));
const sh = (cmd, ...a) => execFileSync(cmd, a, { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] }).trim();

const log = readFileSync("CHANGELOG.md", "utf8");
const m = log.match(/^## Unreleased[^\n]*\n([\s\S]*?)(?=^## |(?![\s\S]))/m);
if (!m || !m[1].trim()) { console.error("Nothing under ## Unreleased in CHANGELOG.md: nothing to release."); process.exit(1); }
const body = m[1].trim();
const sections = [...body.matchAll(/^### (.+)$/gm)].map((x) => x[1].trim().toLowerCase());
const known = ["lineup", "new", "changed", "fixed"];
const odd = sections.filter((s) => !known.includes(s));
if (odd.length) { console.error(`Unknown sections: ${odd.join(", ")} (use ${known.map((k) => "### " + k[0].toUpperCase() + k.slice(1)).join(", ")})`); process.exit(1); }

const pkg = JSON.parse(readFileSync("package.json", "utf8"));
const [MA, MI, PA] = pkg.version.split(".").map(Number);
let next, kind;
if (pick && /^\d+\.\d+\.\d+$/.test(pick)) { next = pick; kind = "named"; }
else {
  kind = pick ?? (sections.includes("lineup") ? "major" : sections.some((s) => s === "new" || s === "changed") ? "minor" : "patch");
  if (!["major", "minor", "patch"].includes(kind)) { console.error(`Unknown bump "${pick}"`); process.exit(1); }
  if (kind === "major" && MA === 0) kind = "minor";      // before launch the first number stays 0
  next = kind === "major" ? `${MA + 1}.0.0` : kind === "minor" ? `${MA}.${MI + 1}.0` : `${MA}.${MI}.${PA + 1}`;
}
const date = new Date().toISOString().slice(0, 10);
console.log(`${pkg.version} -> ${next} (${kind}), sections: ${sections.join(", ") || "none"}`);
if (dry) { console.log("\n" + body); process.exit(0); }

const prev = (() => { try { return sh("git", "describe", "--tags", "--abbrev=0", "--match", "v*"); } catch { return ""; } })();
writeFileSync("CHANGELOG.md", log.replace(/^## Unreleased[^\n]*$/m, `## ${next} — ${date}`));
writeFileSync("VERSION", next + "\n");
sh("npm", "version", next, "--no-git-tag-version", "--allow-same-version");
const title = (body.match(/^- (.+)$/m)?.[1] ?? "release").replace(/\.$/, "");
sh("git", "add", "CHANGELOG.md", "VERSION", "package.json", "package-lock.json");
sh("git", "-c", "user.name=once-human", "-c", "user.email=121476278+once-human@users.noreply.github.com", "commit", "-qm", `${next}: ${title.length > 70 ? title.slice(0, 67) + "…" : title}`);
sh("git", "tag", `v${next}`);
if (!push) { console.log(`tagged v${next}, not pushed`); process.exit(0); }
sh("git", "pull", "-q", "--rebase", "--autostash", "origin", "main");
sh("git", "push", "-q", "origin", "main", `v${next}`);

// the studio renders that changed since the last release go with it
const renders = prev ? sh("git", "diff", "--name-only", `${prev}..HEAD`, "--", "previews").split("\n").filter((f) => f && existsSync(f)) : [];
const notesFile = join(tmpdir(), `release-${next}.md`);
writeFileSync(notesFile, body + "\n");
try {
  sh("gh", "release", "create", `v${next}`, "--title", next, "--notes-file", notesFile, ...renders);
  console.log(`released ${next}${renders.length ? ` with ${renders.length} renders` : ""}`);
} catch { console.error(`v${next} is tagged and pushed; the GitHub release failed (run gh release create v${next} by hand)`); }
