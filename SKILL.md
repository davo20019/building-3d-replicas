---
name: building-3d-replicas
description: Builds exact 3D replicas of real objects from photos, to the millimetre. Parametric code-CAD (build123d), silhouette fitting of uncertain sizes and of each photo's camera, measurement from known points, headless Blender assembly to GLB, and review through each photo's solved camera. Use when a project needs a 3D model or GLB of a specific real object (a product, tool, instrument, vehicle, museum artifact) that must match the real one and no model exists under a licence it can use, or when checking or correcting an existing replica's details against the real object ("is this the same as the real one?", parts that look wrong or floating). Not for stylised or approximate models, cleaning up an existing scan, or generating 3D from a single image.
license: MIT
compatibility: Requires Python 3.12 with uv, Blender 4.2+ and Node 18+ on PATH (ffmpeg for video). Tested on macOS.
metadata:
  author: David Loor
  version: "0.2.0"
---

# Build an exact replica of a real object

The goal is a model indistinguishable from the real object. Numbers decide; eyes check.

Terms: a **photo** is any reference image (a photograph, video frame, manual drawing, render of a scan); a
**cut-out** is the object's silhouette in a photo; the **model** is what you build.

## Setup

Paths are relative to this skill's directory. Once: `uv sync` (makes `.venv` with pinned build123d, OpenCV,
SciPy and Pillow). Run every script as `.venv/bin/python scripts/<name>.py`; each one's docstring documents its
inputs. Blender, Node (for `npx @gltf-transform/cli`) and, for video, ffmpeg must be on PATH.

Start each model by copying `assets/model-template/` into the user's project (`<model>` below). For a worked
example with every number, see [examples/cowbell/REPORT.md](examples/cowbell/REPORT.md).

## Model folder

| File | What |
|---|---|
| `spec.md` | every size with its source; guesses under "Unknowns"; structure and parameters |
| `refs/` | photos, comparison only, never shipped; `SOURCES.md` records each file's source and licence |
| `cad.py` | parametric rigid parts in mm (build123d) to `parts/*.stl`; uncertain sizes in `P` |
| `params.json` | fitted values of `P`, written by the fit |
| `textures.py` | drawn textures (dials, labels, normal maps) to `parts/*.png` |
| `assemble.py` | headless Blender: materials, UVs, pivots, soft parts, to `out/<name>.glb` and `.json` |
| `build.sh` | all of the above, then gltf-transform keeping nodes and materials |
| `review.json` | expected sizes, budget, frame, and the `fit` block |

## Workflow

Copy this checklist into your reply and tick it off:

```
Replica progress:
- [ ] 1. Evidence from every side; each size in spec.md with its source
- [ ] 2. Structure decided from all views; uncertain sizes are parameters; moving parts planned
- [ ] 3. Method chosen per part
- [ ] 4. Fit: cut-outs and cameras checked first, then the shape; each fitted parameter shown measurable
- [ ] 5. Features the outline can't see measured, none placed by eye
- [ ] 6. Built with build.sh, within budget
- [ ] 7. Review rounds until every remaining difference is deliberate or unknowable, and written down
- [ ] 8. Graded against a reference mesh, if one exists
- [ ] 9. Approved by a person where it will be used
```

1. **Evidence.** Collect every view: manuals and makers' pages for sizes, museum open access, Wikimedia
   Commons, shops, video. Label views by geometry. Write down what no photo shows. See
   [references/evidence.md](references/evidence.md).
2. **Structure.** Look at all views and name every feature (facets, scoops, lips, bevels); the fit only tunes
   the shape you give it. Give each uncertain size a parameter in `P`; plan moving parts and interiors now. See
   [references/structure-and-building.md](references/structure-and-building.md).
3. **Method per part:** code-CAD for rigid parts, drawn textures for printed graphics, swept meshes in Blender
   for soft parts, a library part only if its licence and provenance check out. Same file as step 2.
4. **Fit.** Run `scripts/fit_silhouette.py <model>` with `params: {}` first and look at every `target.png` and
   `overlay.png`; then add the parameters. See [references/fitting.md](references/fitting.md).
5. **Measure** interiors and details from 6 or more known points with `scripts/measure.py <job.json>`. See
   [references/measuring.md](references/measuring.md).
6. **Build** with `<model>/build.sh`. Frames and GLB conventions: [references/frames.md](references/frames.md).
7. **Review** with `scripts/review.py <model>`: fix the differences on `review/round-N/sheet.png`, run again.
   See [references/review.md](references/review.md).
8. **Grade** with `scripts/compare_mesh.py <model>/check/<job>.json` when a scan or the maker's CAD exists.
9. **Test where it will be used**, with a person looking at it. For WebXR and real-time engines, see
   [references/webxr.md](references/webxr.md).

## Rules that always apply

- **Trust the numbers over your eye.** A photo read as shot from above was shot from below; the dial's
  position inside the outline proved it.
- **Check the cut-outs and cameras before fitting any shape.** A bad cut-out makes every number wrong.
- **Check that a photo can measure a parameter before trusting its value.** Score the outline over a range
  of it: if the score is flat, the value is arbitrary and other views (or a person who has seen the object)
  must decide.
- **Fix what is published; fit only what isn't.** Free published sizes absorb camera errors.
- **When cues disagree, the structure is wrong.** Find the missing feature; don't average.
- **Never place a feature by eye.** Measure it, or mark it as a guess in `spec.md`.
- **Never build from a reference mesh.** It is the answer key.
- **Leave out logos and wordmarks; publish only references whose licence allows it.**
- **Stop and ask after 5 review rounds without progress.**
