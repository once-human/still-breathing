# Still Breathing

The Still Breathing site and the pipeline that makes its garments: every tee is simulated from the blank's real measurements, sewn in Blender's cloth solver, and shown exactly as it comes off the press.

Live: https://www.sahn.in (Vercel behind Cloudflare; sahn.in redirects there, deploys on every push to `main` that touches `public/`).

## Layout
- `src/` the Next.js site (`npm run dev`); `src/lib/viewer/` has the WebGPU real-time renderer, the BVH builder and the WGSL path tracer
- `public/tee/` meshes, maps and offline frames the viewer loads
- `pipeline/` pattern, body, cloth sim, textures and renders
  - `pattern.py` flat pattern of the blank (sizes in `sizes.py`)
  - `body.py` builds a body from height and chest (MakeHuman via the MPFB Blender extension); `bodies.sh` makes the five in `bodies/`
  - `build.py` sews a size onto a body and poses it (standing, hands up, sitting); `FORM=1` drapes the shop tee on a ghost form
  - `texture.py`, `knit.py` colour atlas, ink mask, stitch relief, knit map
  - `render.py` Cycles stills and turntable frames; `export.py` web meshes + fit numbers per pose; `webtex.py` web textures
- `render.ipynb` one-click GPU rendering on Google Colab
- `.github/workflows/fit.yml` every body x size simulation, published to `public/tee/fit/`
- `.github/workflows/render.yml` fallback turntable frames from the ghost-form tee, published to `public/tee/still/`

## Rendering
- Laptop: `cd pipeline && blender -b tee-drape.blend -P render.py -- B black front out.png 96`
- GitHub: Actions → *fit* → Run workflow first (sims), then *render* → Run workflow. Both split the work across runners and commit to `public/tee/`.
- Colab: open `render.ipynb` in Colab, Runtime → Change runtime type → T4 GPU, Run all.

## Versions
See `CHANGELOG.md`. Tags are `vX.Y.Z`; the site footer shows the version from `public/version.json`.
