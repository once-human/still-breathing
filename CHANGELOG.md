# Changelog

Versions follow [SemVer](https://semver.org): MAJOR for a new site or pipeline structure, MINOR for a new garment, colourway, size or studio feature, PATCH for fixes to renders, numbers or copy. Every release is a git tag `vX.Y.Z` with its renders attached to the GitHub release.

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
