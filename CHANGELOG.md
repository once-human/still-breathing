# Changelog

Versions follow [SemVer](https://semver.org): MAJOR for a new site or pipeline structure, MINOR for a new garment, colourway, size or studio feature, PATCH for fixes to renders, numbers or copy. Every release is a git tag `vX.Y.Z` with its renders attached to the GitHub release.

## 0.8.0 — 2026-11-25
Breath and end of the line are back.

### Shirts
- 04 breath (black): the crowd through a heat camera on a cold December night, hands up, every breath rising.
- 05 end of the line (off white): the Green Line out to Madavara, its last station, where the show is.
- Both sit in the Bengaluru row next to its map, and you can turn them in the viewer and try them on.

## 0.7.1 — 2026-11-25
### Viewer
- The tee turns half as fast on its own: one slow turn in about 51 seconds.

### Fixes
- The "now" strip no longer breaks the home page when the forecast service turns the request away; it just leaves the weather out.

## 0.7.0 — 2026-11-25
Your hands and hair in front of the tee, to the pixel.

### Try-on
- Your hands, forearms, hair and face show in front of the tee with their real edges. A trained model on your device reads every pixel of the camera as hair, skin, face, clothes or background; nothing leaves the browser.
- Your own clothes never show through, and bare skin counts only along your forearms and hands.

## 0.6.0 — 2026-11-25
The studio and the living room are real places now.

### Viewer
- The studio is a real daylight photo studio, photographed all the way round: paper rolls on the wall, a tall window, an octabox and a strip softbox on their stands, folding screens.
- The window light is a real sunny flat: a curtained corner window, the sun across the floorboards, a sofa against a plaster wall, plants and a small kitchen.
- The floor stays under the person's feet as you walk round, and the windows and softboxes you see are the lights on the tee, from where they stand and as bright as they are.

## 0.5.0 — 2026-11-25
A try-on that moves like a shirt on you, and three real places to see it in.

### Try-on
- Reacts sooner: where you stand, your turn, your hips and your arms follow quick movement almost at once, and holding still stays as steady as before.
- The tee stays on your shoulders when you move fast.
- Shrug one shoulder and only that side of the tee rises; the hem stays level.
- Raise your arms and the tee rides up on that side, as on a person, and settles back as you lower them.
- Sit down and the hips stay upright.
- No gaps at the shoulders, and no shadows across your face.

### Viewer
- Three places, each its own: a white studio, a sunny living room and the show's hall. Each wraps all the way round you and lights the tee and the person from every side.
- The show is lit the way a crowd is: a warm and a cool light over the stage, a follow spot from the side, the front-of-house spots behind.
- The body is solid: a gust no longer pushes the tee through the chest.
- The person looks like one: denim jeans, eyes with a shine, relaxed hands and an easy stance.

### Shirts
- 01 crowd: the voice-note line under again.. is gone.

### Fixes
- The version at the foot of the page was stuck at 0.3.1. It now matches the release.

## 0.4.0 — 2026-11-24
Three shirts: the crowd for the whole tour, a map for each city. And a viewer you can get close to.

### Shirts
- 01 crowd (black) is now one drawing for the tour, built on the Bengaluru crowd. Bengaluru is on the left: the Green Line stopping at Madavara, rain trees, a train pulling in. Mumbai is on the right: the skyline behind the race course, the twin crowns, a crane, kites, a plane lining up. In front are people from both nights. The back reads again.. / india . 12 . 2026.
- 02 map (off white): Mumbai's race course, unchanged.
- 03 map (off white): Bengaluru's NICE Grounds from above, drawn in the Mumbai map's hand: the halls, the crowd and the stage, sound rings, the Green Line ending at Madavara beside the grounds, the NICE Road interchange, the lake. It replaces end of the line and breath.
- The picker gets a "the tour" row for the shirt that belongs to no one city.
- Flat inks everywhere: no grain in any art.

### Viewer
- Zoom up to 5x with the wheel, a pinch, a double-click or the +/− buttons, and keep turning the shirt while zoomed. Zoomed in, the print swaps to a full-resolution copy, fetched only then.
- Livelier, lighter cloth: a quicker sway, a little more breeze, and the hem keeps its carry when you let go. Edges stay smooth when you drag hard.
- The chest no longer shows through the shirt. The display form is a hull, and the meshes are lighter.
- The small notches at the hem and the sleeve ends are closed.
- Scrolling no longer stutters: the 3D pauses while the page scrolls and is capped at 60 fps at rest.
- Smaller print files with sharper lines (area-averaged downsizing).

## 0.3.1 — 2026-11-24
Runs on any laptop. The viewer decides per device how much to do, and the shirt is on screen at once.

- Photo first: the path-traced frame shows the moment the page opens and can be turned; the 3D takes over when it is ready, at the same angle, and only loads once the viewer is near the screen.
- Three levels, picked per device before any 3D code downloads: path tracing on a real GPU, the live view alone on a modest one (resting on the traced frames at each 30°), and the traced frames only where there is no real GPU, 2 GB of memory or Data Saver is on.
- The tracer times itself: too slow, and it first traces fewer pixels, then hands over to the frames.
- Dragging drops resolution when frames run slow and goes back to full sharpness at rest. Nothing runs while the viewer is off screen.
- Turntable frames are WebP: 29 MB down to 1.5 MB for all four shirts (about 20 KB a frame). render.yml now writes WebP.
- Mahalakshmi's two dots get room on 04.

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
