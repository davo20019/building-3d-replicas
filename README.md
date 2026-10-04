# build-3d-model

A [Claude Code](https://code.claude.com) skill, and the scripts behind it, for building **exact 3D
replicas of real objects from photos**: parametric code-CAD (build123d), silhouette fitting through each
photo's solved camera, measurement from known reference points, and headless Blender for assembly,
materials and review renders.

It is for the case where you need a model of a specific real object, no model exists under a licence you
can use, and "looks about right" isn't good enough. Every uncertain dimension is a named parameter; the
photos decide its value, and the review shows the model through each photo's own camera so differences
are real, not perspective.

## What's in it

| | |
|---|---|
| `SKILL.md` | The process and the rules learned building real objects. Claude Code loads it as a skill. |
| `scripts/fit_silhouette.py` | Fits shape parameters and every photo's camera together, by silhouette overlap, outline distance, measured landmarks and dark-part placement. |
| `scripts/measure.py` | Measures points in mm in one photo from 6+ points of known position (interiors, details the outline can't see). |
| `scripts/review.py`, `render_views.py` | A review round: the model rendered through each solved photo camera, beside the photo, with sizes and budget checks. |
| `scripts/render_cams.py` | Renders the model through any solved or eye/look camera, beside its picture. |
| `scripts/compare_mesh.py` | Grades a model against a reference mesh (a museum scan, a maker's CAD) in mm. |
| `examples/cowbell/` | A complete worked example on public-domain material, graded against the museum's scan. |
| `templates/model/` | An empty model folder to copy. |
| `docs/` | Frames and GLB conventions; notes for WebXR and real-time engines. |

## Install

Requirements: macOS or Linux, [uv](https://docs.astral.sh/uv/), [Blender](https://www.blender.org/) 4.2+
(tested with 5.2) on PATH as `blender`, Node 18+ (for `npx @gltf-transform/cli`), and ffmpeg if you work
from video.

```sh
git clone https://github.com/<owner>/build-3d-model ~/.claude/skills/build-3d-model
cd ~/.claude/skills/build-3d-model
uv sync                      # Python 3.12 and pinned build123d, OpenCV, SciPy, Pillow in .venv
uv run pytest -m "not slow"  # quick self-check, a few seconds
```

Claude Code finds the skill in `~/.claude/skills/` (or put it in a project's `.claude/skills/` to share it
with that project). Ask for a model of a real object and it follows `SKILL.md`. You can also run every
script by hand; each one's docstring documents its inputs.

## Walkthrough: the cowbell

The example rebuilds a cowbell in the National Museum of American History (object 2018.0174.01) from one
CC0 museum photo, its published size, and four renders of the museum's CC0 scan through known cameras. The
scan's mesh is never used to build: it is the answer key.

```sh
cd examples/cowbell
./fetch_refs.sh                                   # the photo and scan (CC0), and the four scan renders
S=../..                                           # the skill's folder
$S/.venv/bin/python $S/scripts/fit_silhouette.py .   # cameras for all five pictures, then the shape (~15 min)
./build.sh                                        # CAD parts -> Blender -> out/cowbell.glb
$S/.venv/bin/python $S/scripts/review.py .           # review/round-N/sheet.png
$S/.venv/bin/python $S/scripts/compare_mesh.py check/scan.json   # the grade, in mm
```

[examples/cowbell/REPORT.md](examples/cowbell/REPORT.md) has the numbers from each step: the cut-outs, the
solved cameras against the true ones, and the replica against the scan.

## Your own object

```sh
cp -r ~/.claude/skills/build-3d-model/templates/model path/to/your/project/models/<name>
```

Then follow `SKILL.md`: evidence from every side, the structure decided by looking at all views, the
uncertain sizes as parameters in `cad.py`, a fit with `params: {}` first to check the cut-outs and
cameras, then the shape, then review rounds until the remaining differences are deliberate or unknowable.

## Reference material and licences

The code is MIT. Reference photos are not: keep shop photos, video frames and anything else you may not
redistribute out of any repository you publish (the template's `.gitignore` keeps `refs/` local). Prefer
evidence you may share: your own photos, museum open-access collections, Wikimedia Commons (record each
file's licence in `refs/SOURCES.md`). Leave out logos and wordmarks, and check before publishing a replica
of a product whose shape is itself a protected design.

## Tests

```sh
uv run pytest -m "not slow"   # compare_mesh and measure against exact synthetic answers
uv run pytest                 # also the cowbell end to end: needs Blender and fetch_refs.sh (minutes)
```
