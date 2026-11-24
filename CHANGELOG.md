# Changelog

Versions follow [SemVer](https://semver.org): MAJOR for a new site or pipeline structure, MINOR for a new garment, colourway, size or studio feature, PATCH for fixes to renders, numbers or copy. Every release is a git tag `vX.Y.Z` with its renders attached to the GitHub release.

## 0.2.0 — 2026-11-24
Lineup 01 is now two shirts, and the viewer path-traces in the browser.

### Site
- Rebuilt on Next.js. Its own look: after-dark palette, the print's blue as the only colour, Bricolage Grotesque, ruled labels and one giant word.
- Two designs: 01 crowd (lines) and 02 map (race course), each in black and off white.
- Real-time view on three.js WebGPURenderer (WebGL2 fallback built in).
- WebGPU path tracer: when you let go, the exact view is traced with the same cotton, ink, sweep and softboxes as the Cycles renders. Any angle, not just the 12 pre-rendered ones. Calibrated against the Cycles frames: chest patches match within 1-2 sRGB levels on black and off white.
- Fixed product camera (85 mm, f/5.6). The lens control is gone, so the collar never changes shape; the loupe crops and re-renders up to 12x instead.
- Removed supplier, print method, print-area and render-engine details from the page. Kept what a buyer needs: cloth, fit, sizes in cm, care, the fan-made note.
- Live countdown to the next show.

### Pipeline
- webtex.py writes maps per design: color-<design>-<tee>.jpg, orm-<design>-<tee>.png.

## 0.1.2 — 2026-11-24
- Site hosted on Vercel; every push that touches `public/` redeploys, render-farm commits included. Pipeline-only commits skip the deploy.

## 0.1.1 — 2026-11-24
- Turntable frames for both colourways rendered on the GitHub Actions render farm (24 frames, 64 spp).
- Real-time light rig calibrated against the Cycles frames, so the switch between them is close to invisible.

## 0.1.0 — 2026-11-24
First cut of the Still Breathing site and the garment pipeline.

### Site
- Product page for lineup 01 (fred again.., Mumbai tee), black and Off White.
- Real-time three.js studio: drag to turn, lens 24-200 mm with dolly, exposure, key light colour temperature and angle, fill ratio, rim light, knit detail, four backdrop papers.
- Path-traced Cycles frames take over whenever the view lands on a rendered angle at the reference light; falls back to the frames alone when WebGL is missing.
- Qikink UC22 size chart XS-2XL, tech flat drawn from the real pattern, fit facts on the simulated body, print and cloth facts.

### Pipeline
- UC22 M pattern from Qikink's published chest, length and shoulder; unpublished values are marked as estimates.
- Cloth simulation in Blender 5.3 on a 170 cm, 94 cm chest Indian male body (MakeHuman via MPFB).
- 240 GSM jersey settings, two-layer hems and rib collar, stitch and rib relief map, real single-jersey knit map.
- Print halos knocked out of the print files; DTG ink without the cotton sheen; Khronos PBR Neutral view transform.
