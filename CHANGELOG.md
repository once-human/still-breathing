# Changelog

Versions follow [SemVer](https://semver.org), counted by what a buyer would notice. Changes go live with every push and are noted under Unreleased; a release is cut when a set of them is finished (`npm run release`), and the bump follows from the sections:
- **Lineup** → MAJOR: a new drop or lineup, or the shop working differently (checkout, prices, a redesign).
- **New / Changed** → MINOR: a new shirt, colour or feature; new art or lettering on a shirt; a rename.
- **Fixed** → PATCH: fixes and polish: copy, a render refresh, a layout bug.

The shop stays 0.x until launch, which is 1.0.0. Every release is a git tag `vX.Y.Z` and a GitHub release with the studio renders that changed attached.

## Unreleased
### New
- On the table: the tee laid flat on a worn wooden table, lit by a window on the right whose frame throws a soft shadow across the boards. Air comes in through it, never quite straight: it dies away, breezes, builds slowly or bursts. Now and then a dry leaf (rarely a thread or a hair) drifts down or skates in; it has weight, holding until a puff beats its grip, then breaking loose, skidding and stopping again. Leaves glow a little with the light behind them. The cotton breathes with the air.

### Changed
- Up close is now on the table: it zooms in closer than before, zooms out only a little, and pans only a little past the tee.
- The print stays at full quality at every zoom, and renders sharper whenever the machine has room for it.
- Every load says something different: a word in hand picked at random from twenty or more for that kind of load (dressing it.., lights down.., closer.., swapping shirts.., in the darkroom.., tape out.. and the rest), never the same twice in a row. No more breathing in..
- The actual size button is called artwork.

## 0.18.0 — 2026-11-25
### New
- the tee view zooms in and out like the others (− zoom +, a pinch, a double-click) and slides along the print when close.

### Fixed
- The arrows and the little pictures over the 3D view click again (a press on them was taken as the start of a drag).
- Zooming in is sharp straight away: the back print at full resolution loads in the background once the 3D is up.
- The air never stops dead: a lull drops to a soft draught, so the cloth keeps moving.
- While the 3D loads, the tee view shows the tee on its own (the studio render), not someone wearing it; it opens on the back.

## 0.17.0 — 2026-11-25
### Studio
- up close has an actual size button: the print opens as big as it is on the shirt, on the shirt's own colour, to drag around. A dashed bank card outline checks the screen's scale; − and + set it right, and it's kept for next time.
- Keys 1, 2 and 3 turn the view to the front, ¾ and the back (up close: the front and back prints) while the viewer is on screen.
- New studio stills and turntable for 02 i am a party (no mirror ball) and 03 Mumbai.

## 0.16.4 — 2026-11-25
### Shirts
- 03 Mumbai map has its new lettering: the note reads we were somewhere in here, i swear, and every arrow has its dark line back.
- New try-on textures and prints to match.

## 0.16.3 — 2026-11-25
### Shirts
- 02 i am a party has no mirror ball after all; the title sits centred again.

## 0.16.2 — 2026-11-25
### Shirts
- The mirror ball on 02 i am a party is smaller and sits right after the date, no string: bigger tiles, lit from one side, every tile its own flat tone.

## 0.16.1 — 2026-11-25
02 is i am a party now, after the Fred again.. song.

### Shirts
- The title reads i am a party, with a small mirror ball hanging beside it: a real ball of mirror tiles, rendered and cut into flat tones, a blue light glancing off one side.
- the warmest place in the city sits lower now, over the crowd, out of the sky. The nose line is can't feel my nose. don't care. Both notes have small arrows.
- New try-on textures and prints to match.

## 0.16.0 — 2026-11-25
02 is called envelops me now, after a Fred again.. song, the way Still Breathing is.

### Shirts
- Its back is lettered again over the same heat picture: envelops me / india . 12 . 2026 in the crowd's hand, the title's dark edge between the two earlier tries, the date's thinner.
- The notes: bengaluru, 16° at night and mumbai, 20° at night where they were; the warmest place in the city over the crowd; the nose stays cold with a small arrow; hands up for the drop; his first fred show.
- New try-on textures and prints to match.

## 0.15.0 — 2026-11-25
Breath belongs to the whole tour now.

### Shirts
- 02 breath (black) is drawn again for both nights: a real crowd seen from the stage through a heat camera, the heat in flat bands of colour with clean edges, the far crowd melting into a purple haze, every breath rising. No grain.
- Its back reads breath.. / india . 12 . 2026, lettered in the crowd's hand, with notes: bengaluru, 16° at night; mumbai, 20° at night; hands up since the first song; the nose stays cold.
- The tour has two shirts, the crowd and breath; Mumbai and Bengaluru each have their map.
- New try-on textures and turntable frames for breath.

## 0.14.2 — 2026-11-25
The tee hangs even on you.

### Try-on
- Stand easy and the tee sits square and level, the same on both sides: the small tilts and turns the camera can't tell from noise no longer lean it, lift one shoulder or push one side of the hem forward.
- A real lean, turn or shrug still comes through whole, with no lag.

## 0.14.1 — 2026-11-25
The tee fills out on a bigger body, the way cotton does.

### Try-on
- The tee keeps its size and its loose fit. Where your body is wider than the tee at some height, the cloth is pushed out to lie on you, only there and only as far as heavy jersey gives; on most bodies it hangs free and nothing changes.
- Past what the cloth can give it stays tight, the way a size too small would look on you.

## 0.14.0 — 2026-11-25
Record yourself in the tee.

### Try-on
- A record button next to take a photo: up to 30 seconds of you in the tee, exactly as you see it, mirror, tee and hands.
- Clips save as MP4 where the phone or browser can write it (iPhone, Android, recent Chrome), WebM otherwise.
- Photos and clips can go straight to any app through your phone's share sheet, or save to the device. Nothing leaves it until you do.

## 0.13.2 — 2026-11-25
### Studio
- The shades near the edges come and go slowly and evenly now. The bottom one only rises at the very bottom, wider and softer.

## 0.13.1 — 2026-11-25
### Studio
- Down by the bottom of the view a softer shade comes up too, so the strip of views and the counter read clearly over any light.

## 0.13.0 — 2026-11-25
### Studio
- Nothing half-ready is ever shown. Switching views, shirts or the light fades the view out, a slow breath (and after a beat, "breathing in..") holds the stage while the new one gets ready, the person, the room and all, and only then it fades back in whole. On opening, the 3D takes over from the photos only once its room is in too.
- The strip of little pictures sits in the middle at the bottom on wider screens, each one the view as it really looks: the tee on its own, the person in it, the print. Hover for its name, click to go. The counter is back in its corner.

## 0.12.3 — 2026-11-25
### Site
- From abroad, the tour shirts follow Mumbai or Bengaluru, the two gateways, by real flight time from where you are: Mumbai from the Gulf, Europe, Africa and the Americas (the most direct routes), Bengaluru from Sri Lanka, Southeast Asia and Australia.

## 0.12.2 — 2026-11-25
### Site
- The countdown and the rest of the page really do follow your show now. The first shirt on the page never asked where you are, so everyone saw the next date, Delhi NCR.

## 0.12.1 — 2026-11-25
### Site
- For the tour shirts, the page now talks about the show that's quickest for you to reach, not the one nearest on a map: by road when it's close, by air when it's far, with a little grace for the cities with two nights. From Pune that's Mumbai.

## 0.12.0 — 2026-11-25
### Studio
- The view counter is a strip of three little pictures in the corner of the stage, one per view, like a photo app's: see what each shows, tap to go.
- Up close picks between the back and the front.
- The shade near an edge is deeper and comes up more slowly, so the arrow on it reads clearly.

## 0.11.0 — 2026-11-25
### Studio
- The carousel is three views now. **The tee** opens first: the shirt alone on paper, turning slowly; drag to turn it, or pick front or back. **Worn**: someone in it at the place you pick, with front, ¾, side and back, zoom, the light and the photo. **Up close**: framed on the whole back print, or the chest print, with the cloth still moving; zoom right in and slide along it. ¾ back, flat and the art are gone.
- The arrows on the picture are drawn like the notes on the shirts: a marker arrow, small and quiet until you come near that side, then the room dims softly there and a word in hand says where it goes.
- The mouse wheel only zooms once you've put your hand on the tee, so scrolling the page never gets caught in the viewer.

## 0.10.2 — 2026-11-25
### Studio
- Turning the tee never mixes in an old design's frames again. Every file the viewer loads now has its own fingerprint in its address, so a frame or texture that changed is always fetched fresh, and the ones that didn't stay cached.

## 0.10.1 — 2026-11-25
### Studio
- No more flicker while turning the tee. The twelve rendered frames load together and swap in place, so a drag never shows an empty stage. The path-traced still no longer comes and goes over the live cloth; it only develops the photos you ask for. The last view stays up while the next one loads.
- Each device gets what runs well on it: WebGPU desktops get everything plus photos; WebGL2, phones and machines with 4 GB or less get the same live view at up to 1.5x sharpness; with no real graphics, the rendered frames.

## 0.10.0 — 2026-11-25
### Studio
- The 3D view is a carousel of six views, each locked to what it shows: worn (someone in it at the place you pick, turn and zoom), alone (the tee by itself on paper, turn it), ¾ back (the hero angle, leaning toward the pointer), flat (the back straight on), close (right in on the print, slide along it) and the art (the artwork flat, pan and zoom). The cloth keeps moving in the air in every 3D view. Arrows on the picture, or the arrow keys.

## 0.9.3 — 2026-11-25
### Shirts
- Breath is a tour shirt now, next to the crowd: 01 crowd, 02 breath, 03 the Mumbai map, 04 the Bengaluru map.

## 0.9.2 — 2026-11-25
### Shirts
- End of the line is gone from the lineup, with its prints and frames.

## 0.9.1 — 2026-11-25
### Shirts
- 01 crowd: four more notes in the same hand: a december moon / mallige in her hair / best friends since 7th std / filter coffee, still hot.

## 0.9.0 — 2026-11-25
Bengaluru's map, drawn again as a picture to wear.

### Shirts
- 03 map (off white): closer in, so the grounds are the picture. Everyone in the crowd is a small drawn person seen from above, arms up; friends hold hands in pairs and dance in rings. The halls stand up off the ground, the Green Line is a solid line with the last train in at Madavara, buses, autos and cars are jammed on Tumakuru Road outside the gate, and the village streets run down to the lake, where bengaluru and the dates sit on the water.
- Four handwritten notes: madavara. the green line ends here / everyone's on tumakuru road / we'll be somewhere in here / strangers, holding hands.
- Bigger, bolder marks everywhere: no fine dots or speckle.

## 0.8.1 — 2026-11-25
### Shirts
- 01 crowd: the two friends on the right are drawn again, both from behind, his arm round her shoulders.

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
- Size chart XS-2XL, tech flat drawn from the real pattern, fit facts on the simulated body, print and cloth facts.

### Pipeline
- M pattern from the maker's published chest, length and shoulder; unpublished values are marked as estimates.
- Cloth simulation in Blender 5.3 on a 170 cm, 94 cm chest Indian male body (MakeHuman via MPFB).
- 240 GSM jersey settings, two-layer hems and rib collar, stitch and rib relief map, real single-jersey knit map.
- Print halos knocked out of the print files; ink without the cotton sheen; Khronos PBR Neutral view transform.
