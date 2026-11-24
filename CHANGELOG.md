# Changelog

Versions follow [SemVer](https://semver.org): MAJOR for a new site or pipeline structure, MINOR for a new garment, colourway, size or studio feature, PATCH for fixes to renders, numbers or copy. Every release is a git tag `vX.Y.Z` with its renders attached to the GitHub release.

## 0.3.0 — 2026-11-24
Bengaluru gets its two shirts. Everything is for sale, one colour per shirt, a cleaner print, and the tee on bodies like the people buying it.

### Shirts
- Bengaluru, drawn from scratch:
  - 03 breath (black): the crowd as a heat camera on the stage sees it on a December night, hands up, breath rising into the cold. Rendered from our own five Indian bodies (460 people), with a thermal readout, ಉಸಿರು / breath.
  - 04 end of the line (off white): the Green Line northbound from Majestic to Madavara, its last station and the show's, set in Kannada and English. Bengaluru is the last city of the tour. Mahalakshmi carries two blue dots for Mumbai's ground.
- The picker groups the shirts by city; the heading follows the shirt (again.. mumbai / again.. bengaluru).
- One colour each: 01 crowd is black, 02 map is off white. No colour picker.
- Front: "again.." in four scripts (again.. / फिर से.. / पुन्हा.. / ಮತ್ತೆ..) on the left chest at chest height. No name, no date.
- Back: the art fills the largest print the blank allows (15 x 20 in at 3:4).
- Copy says what it is: made to order, for sale, sent anywhere in India.

### Viewer
- No grain, ever: the path tracer works out of sight and the denoised frame fades in over the real-time view. No sample counters.
- Edge-avoiding à-trous denoiser (normal, depth and luminance guided, albedo demodulated), so folds and print edges stay sharp at 40 samples.
- Photo mode: story (1080 x 1920) or post (1080 x 1350), clean or film, with a caption. 64 samples + denoise, seconds instead of minutes. Save or share.
- Lights cut to three that look real: studio, window, the show (dark room, cool stage wash, one warm spot, a dim front-of-house fill). Overcast, tube light and phone flash are gone.
- The shop tee hangs on a smooth ghost form, so the empty tee shows no chest shape.
- Fit mode: say man or woman, height and weight, pick a skin tone; the tee is shown in your size on the nearest of five simulated Indian bodies, standing, hands up or sitting, with plain words for how it fits (room round the chest, where the hem falls, how far it rides up).
- Fallback frames are re-rendered from the ghost-form tee. With no 3D at all, the page shows them instead of an error, drag to turn.
- Bigger tap targets for the small text buttons on phones.
- The shop camera steps back a little so the collar has room.

### Page
- A live "now" strip that writes itself: days to the next show, the sky over it right now, the sunset, the show-night forecast once it's in range. Public forecast for three fixed places; nothing about the visitor leaves the browser.

### Pipeline
- `body.py` builds five Indian bodies from height and chest (m163, m170, m177, f155, f162); chest is measured on the connected torso loop.
- `pattern.py` grades every size from the chart; the atlas is neck-anchored so the print sits at the same place on every size.
- `build.py` sews any size onto any body and moves it through standing, hands up and sitting (stool collider); `FORM=1` swaps the torso for the ghost form.
- `export.py` bakes cloth AO into the vertices, exports tee + body per pose, `fit.json` measures and `proxy.glb`.
- `.github/workflows/fit.yml` runs all 15 body-size sims plus the ghost form in parallel and publishes them to `public/tee/fit/`.
- `render.yml` renders fallback frames from the published ghost-form tee (`GLB=` mode in `render.py`).
- `export.py` uses plain Catmull-Clark (the limit-surface evaluator needed ~3 GB and killed CI runners) and measures the body on frame 1 (it was measured on the saved sitting frame, which shifted every waistband reading by the sit drop; published numbers corrected).
- `art/make_line.py`, `art/make_breath.py` + `art/breath_post.py` generate the Bengaluru backs; `fonts/` holds Bricolage Grotesque and Noto Sans Kannada for them.

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
