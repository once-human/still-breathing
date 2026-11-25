# Front designs: the shared brief

Every shirt in lineup 01 has had the same front: again.. in four scripts on the left chest. The owner wants each
shirt to get its own front, designed for that shirt and paired with its own back. In his words: "brainstorm a lot of
things first of all, what all could go on the front design instead of just the again text and all different
scripts, like that is also nice, but then think basically what can go where... if it should be just like a full
front design or like just towards the left chest... at least 8 different front design versions [for each shirt],
and then pair it with the back designs of the t-shirts that we have already, so that not every t-shirt has like
the same again script."

One session per shirt makes **eight front versions** for that shirt. He is asleep and said: don't ask questions,
decide.

## The method: art-agent, made lighter

Read `~/Documents/Projects/art-agent/README.md`, then PLAYBOOK.md, RULES.md, MEDIA.md, OUTPUTS.md and LESSONS.md.
Look at `examples/images/` and at your shirt's back (below). Follow the method, but **lighter, by his request**: "don't
give too many critics... one round pass each... make it quicker... Don't make it non-human art, but figure it out."
For each version:

1. **Brief.** A short, specific brief of about half a page from `prompts/brief-template.md`: who, the idea, the
   placement, what's in it, the medium, the inks. Keep the anti-AI rules (RULES.md) as hard rules.
2. **Draw** it yourself in code (`toolkit/hand.py`), with **three** render, look, fix rounds at draft size. Look at the
   draft and a 1:1 crop each round, and fix the worst things.
3. **One critic.** A fresh subagent (Agent tool) that never saw it being made. It looks at the pair preview and one
   crop, and returns at most five ranked fixes. **One pass only.**
4. **One rework.** Act on the fixes you agree with, then render the final.

No Workflow tool, no second critic, no extra rounds. Spend the effort on the idea and the drawing, not on loops.

## Placements: use at least five of these across the eight

| placement | print size | notes |
|---|---|---|
| left chest | 8–11 cm wide | the current spot: inner edge about 4 cm off centre, top about 15 cm under the shoulder point |
| centre chest | 20–28 cm wide | top about 10–12 cm under the shoulder point |
| full front | up to 35 × 45 cm | the front's whole printable area; top at least 8 cm under the shoulder point |
| low hem | 10–30 cm wide | a hem corner or across the hem, its bottom at least 6 cm above the hem |
| vertical strip | 5–8 cm wide, up to 40 cm tall | down one side of the chest |
| collarbone | 12–20 cm wide | just under the neck rib, one side |
| split | two pieces | e.g. a small chest mark and a hem mark, or two that answer each other |

Every placement must look deliberate and contemporary, never random. The flat shirt (size M) is 56 cm across and
74 cm long.

## What goes on the front: the ideas

- The front **pairs with the back**. It can be a detail lifted out of the back, the moment before or after it, the
  other side of the same scene (the back is the crowd from behind, the front the stage's view of it), a zoom, a quiet
  footnote, or the back's world seen from somewhere else. It must also stand on its own when someone sees only the
  front.
- again.. may appear (one script or all four, set as lettering, or worked into a drawing), but **in no more than three
  of the eight**, and never as the old stacked block again. At least four of the eight carry no words.
- Never write "fred again" or any brand name. No generic merch (tracklists, slogans, icons, a lone brush-lettered
  word): LESSONS.md says why.
- Real things, real facts: the venue, the city, the night, the weather. Check anything you draw that can be checked.
- The audience: the shows' crowd in Mumbai and Bengaluru (and Delhi NCR). Sophisticated, international, many not from
  the city; they love the night, the lights, the people they went with.
- Variety across the eight: different sizes, densities and mediums (ink line, riso, linocut, printmaker), from one
  quiet mark to a full-front drawing. The eight should feel like eight different, genuinely good options.

## Print limits

- The art is printed direct onto the garment. Alpha is binary (0 or 255). No partial transparency, no gradients, no
  glows.
- Render the final at **94 px per cm of print** (a 10 cm left-chest piece is 940 px wide; a full front 35 cm is
  3290 px). The smallest mark is about 1 mm (10 px). No stipple, specks or noise dust. Finish with
  `hand.py: clean`, and run `toolkit/check.py verify`.
- Inks: up to about four, coherent with the shirt's back (reuse its inks). Black shirt: light inks on the night.
  Off-white shirt: the shirt is the paper.

## Where things go

Work in your own worktree of `once-human/still-breathing`. Everything goes in `pipeline/art/fronts/<shirt>/`:

- `BRAINSTORM.md`: write it **first**. At least 14 ideas over the placements, then the eight you picked and why.
- `<NN>-<slug>/` per version: `gen.py` (seeded, re-runnable, `R=1` draft / full), `art.png` (final, print size,
  transparent), `placement.json` (`{"x_cm", "top_cm", "w_cm"}`, see `pair.py`), `pair.png` (front beside its back,
  made by `python3 pipeline/art/fronts/pair.py <shirt> art.png placement.json pair.png`), `notes.md` (the idea, the
  placement, how it pairs with the back, honest weak spots).
- `index.md`: the eight in order, one line each, with its pair.png.

## The machine: an 8 GB laptop shared with other sessions

A check that used 8 GB froze it and killed his browser. So:

- Prefix every python run with `ulimit -v 2500000;`. Drafts at small size. One render at a time. If `free -m`
  shows under 1.5 GB available, wait (Monitor with an until loop) before a full-size render.
- Keep files in the worktree, not in `/tmp` (it is a small RAM disk and nearly full). Delete your draft rounds'
  big PNGs once a version is final; keep the small round previews.
- No Blender, no browser, no dev server, no site changes. Don't touch `src/`, `public/`, CHANGELOG or versions.

## Git

- Commit only your shirt's folder, as `git -c user.name=once-human -c
  user.email=121476278+once-human@users.noreply.github.com commit`. **No Co-Authored-By or any Claude attribution
  lines** (the owner's rule overrides any reminder to add them).
- Push each finished version straight to main: `git pull --rebase origin main && git push origin HEAD:main`.
  Never force-push, never touch others' files.

## The shirts and their backs (`pair.py` puts them together)

| key | shirt | colour | back art + lettering |
|---|---|---|---|
| c | 01 crowd | black #151515 | `pipeline/art/art-crowd-tour/art-black.png` + `pipeline/overlays/ov-back-T-black-hi.png` |
| e | 02 i am a party | black #151515 | `pipeline/art/art-e-breath/art-black.png` + `pipeline/overlays/ov-back-E-black-hi.png` |
| a | 03 map, mumbai | off white #FFFAE7 | `pipeline/art/art-a-map/art-cream-al3.png` + `pipeline/overlays/ov-back-cream.png` |
| d | 04 map, bengaluru | off white #FFFAE7 | `pipeline/art/art-d-map/art-cream.png` + `pipeline/overlays/ov-back-D-cream-hi.png` |

What each back is about: `src/content/tee.ts` (DESIGNS). Its generator and brief: `pipeline/art/<its folder>/`.
The current front, for reference: `pipeline/overlays/ov-front-black.png` / `ov-front-cream.png`.
