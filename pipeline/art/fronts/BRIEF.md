# Front designs: the shared brief

Every shirt in lineup 01 has had the same front: again.. in four scripts on the left chest. The owner wants each
shirt to get its own front: **a design of its own for the front of the shirt that goes well with that shirt's
back.** One session per shirt makes **eight front versions**. Don't ask the owner questions: decide.

## What he said, after two wrong tries (read every line)

1. A first round made every front out of the back's picture: the back's crowd seen from the stage, a person lifted
   out of it, a hand from the heat picture, the train from the map. **Thrown out.** "You are just literally reverting
   that design that we have from the front side... have you seen any t-shirt that looks good like this?"
2. "The front design doesn't have to be anything like the back design." It should be **smaller and more
   restrained** ("it could be bigger as well, but I think the front design has to be smaller, and a little more
   restrained"): a different design that goes well with the back. The backs are already very illustrative, so a
   busy illustration on the front looks bad.
3. **A wordmark belongs in nearly every design**, and it is one of these:
   - again..
   - fred again..
   - actual life
   - again.. in its four scripts (again.. / फिर से.. / पुन्हा.. / ಮತ್ತೆ..)

   In his words: "I think that should be there in every design. Like you would skip it on some designs if it is not
   looking good... At least again should be there, or like actual life should be there, or like Fred again dot dot
   should be there, or like again in all different scripts should be there, along with like an illustration or
   something, or like we could skip the illustration completely and then just work on the word mark." Skip it only
   where the design is clearly better without, and say why in its notes. "Make it more Fred again."
4. **What he liked from the first round**, as the direction. They are in `liked/`; look at them first.
   - Mumbai, **the map key** (`liked/a-01-the-key`): "I actually do like the map one, the map index one... keep
     working on that."
   - Mumbai, **looking up** (`liked/a-04-looking-up`): the half circles over the skyline. "Just on the chest or
     something. That looks kind of nice."
   - Crowd, **filming** (`liked/c-03-filming`): "the photo icon was actually nice, the idea was nice behind it", but
     as drawn it is too illustrative for a front.

   "Something like this is what I want... very realistic and then very good on that particular t-shirt."
5. **Show the graphic itself, never a fake t-shirt.** "Just give me the graphics render itself." No shirt
   silhouettes or mockups: the art alone, on a plain patch of the shirt's colour.

## What a front can be

- A wordmark alone, drawn and composed with real care: one script, or the four together but never the old stacked
  block. Lettering made by hand, or set from the lineup's fonts and then worked by hand.
- A wordmark with a small, restrained mark: a map key, a few arcs of sound, a phone's frame, a moon, a seal.
- A small emblem or badge that holds the wordmark.
- A restrained chest piece (up to about 25 cm) where the wordmark and one idea work together.

Make the eight genuinely different from each other, all at the quality of a great tour or label shirt's front.
Never take the back's picture as the subject, and drop nothing from his list above. No slogans, tracklists or
clip-art icons.

## Placement and size

- Mostly the chest: left chest (8–11 cm wide, inner edge about 4 cm off centre, top about 15 cm under the high
  shoulder point) or centre chest (12–25 cm wide, top about 10–12 cm under it).
- One or two may be bigger or placed elsewhere (a hem corner, a collarbone line) if they stay restrained.
- Write the placement in `placement.json`: `{"where": "left chest" | "centre chest" | ..., "w_cm": ..., "top_cm": ...}`.

## The method: art-agent, the optional light loop (he asked for it this time)

Read `~/Documents/Projects/art-agent/README.md`, then PLAYBOOK.md (including "Optional: the light loop"),
RULES.md, MEDIA.md, OUTPUTS.md and LESSONS.md. For each version:

1. A short, specific brief (about half a page).
2. Draw it in code (`toolkit/hand.py`, the lineup's fonts in `pipeline/fonts/`), with three render, look, fix
   rounds. Look at the render and a 1:1 crop each round.
3. One fresh critic subagent (Agent tool) that never saw it being made. It looks at `preview.png` and one crop, and
   returns at most five ranked fixes. One pass only.
4. One rework, then the final.

No Workflow tool, no second critic.

## Print limits

- The art is printed direct onto the garment. Alpha is binary (0 or 255). No partial transparency, gradients or
  glows.
- The final is at **94 px per cm of print** (a 10 cm piece is 940 px wide). The smallest mark is about 1 mm (10 px),
  and that includes lettering strokes and counters. No stipple, specks or noise. Finish with `hand.py: clean` and
  run `toolkit/check.py verify`.
- Up to about three inks, from the shirt's palette (below). Black shirt: light inks. Off-white shirt: the shirt is
  the paper.

## Where things go

Work in your own worktree of `once-human/sahn`. Everything goes in `pipeline/art/fronts/<shirt>/`:

- `BRAINSTORM.md`: write it first. At least 14 ideas, then the eight you picked and why.
- `<NN>-<slug>/` per version:
  - `gen.py`: seeded and re-runnable
  - `art.png`: the final, print size, transparent
  - `preview.png`: the art alone on a plain rectangle of the shirt colour with a margin round it, about 1200 px
    on its long side. No shirt shape.
  - `placement.json`
  - `notes.md`: the idea, the placement, how it goes with the back, honest weak spots
- `index.md`: the eight in order, one line each.

## The machine: an 8 GB laptop shared with other sessions

A check that used 8 GB froze it and killed his browser. So:

- Prefix every python run with `ulimit -v 2500000;`. One render at a time. If `free -m` shows under 1.5 GB
  available, wait (Monitor with an until loop).
- Keep files in the worktree, not `/tmp` (a small RAM disk, nearly full).
- No Blender, no browser, no dev server, no site changes. Don't touch `src/`, `public/`, CHANGELOG or versions.

## Git

- Commit only your shirt's folder, as `git -c user.name=once-human -c
  user.email=121476278+once-human@users.noreply.github.com commit`. **No Co-Authored-By or any Claude attribution
  lines** (the owner's rule overrides any reminder to add them).
- Push each finished version straight to main: `git pull --rebase origin main && git push origin HEAD:main`.

## The shirts, their colours and their backs (what the front has to go with)

| key | shirt | colour | inks | back |
|---|---|---|---|---|
| c | 01 crowd | black #151515 | cream line, green, marigold, blue | `pipeline/art/art-crowd-tour/art-black.png` + `pipeline/overlays/ov-back-T-black-hi.png` |
| e | 02 i am a party | black #151515 | violet, orange, pale yellow, cream | `pipeline/art/art-e-breath/art-black.png` + `pipeline/overlays/ov-back-E-black-hi.png` |
| a | 03 map, mumbai | off white #FFFAE7 | black line, green, blue | `pipeline/art/art-a-map/art-cream-al3.png` + `pipeline/overlays/ov-back-cream.png` |
| d | 04 map, bengaluru | off white #FFFAE7 | black line, green, blue | `pipeline/art/art-d-map/art-cream.png` + `pipeline/overlays/ov-back-D-cream-hi.png` |

What each back is about: `src/content/tee.ts` (DESIGNS). Look at the back to match its hand and inks. Never take its
picture as the front's subject. The current front, for reference: `pipeline/overlays/ov-front-black.png`. The brand
blue is #4C66F5 on black and #2C46BE on off white.
