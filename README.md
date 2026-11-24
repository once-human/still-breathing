# Still Breathing

The Still Breathing site and the pipeline that makes its garments: every tee is simulated from the blank's real measurements, sewn in Blender's cloth solver, and shown exactly as it comes off the press.

Live: https://still-breathing-studio.vercel.app (Vercel, deploys on every push to `main` that touches `public/`).

## Layout
- `src/` the Next.js site (`npm run dev`); `src/lib/viewer/` has the WebGPU real-time renderer, the BVH builder and the WGSL path tracer
- `public/tee/` meshes, maps and offline frames the viewer loads
- `pipeline/` pattern, body, cloth sim, textures and renders
  - `pattern.py` flat pattern of the Qikink UC22 blank (sizes in `sizes.py`)
  - `body.py` the body the tee is draped on (MakeHuman via the MPFB Blender extension)
  - `build.py` sews and drapes the tee -> `tee-drape.blend`
  - `texture.py`, `knit.py` colour atlas, ink mask, stitch relief, knit map
  - `render.py` Cycles stills and turntable frames; `export.py`, `webtex.py` web model and textures
- `render.ipynb` one-click GPU rendering on Google Colab
- `.github/workflows/render.yml` turntable rendering on GitHub Actions

## Rendering
- Laptop: `cd pipeline && blender -b tee-drape.blend -P render.py -- B black front out.png 96`
- GitHub: Actions → *render* → Run workflow. Frames are split across runners and committed to `public/tee/`.
- Colab: open `render.ipynb` in Colab, Runtime → Change runtime type → T4 GPU, Run all.

## Versions
See `CHANGELOG.md`. Tags are `vX.Y.Z`; the site footer shows the version from `public/version.json`.
