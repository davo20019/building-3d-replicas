# building-3d-replicas

An [Agent Skill](https://agentskills.io) (works in Claude Code, Codex and other agents that read
`SKILL.md`), and the scripts behind it, for building **exact 3D
replicas of real objects from photos**: parametric code-CAD (build123d), silhouette fitting through each
photo's solved camera, measurement from known reference points, and headless Blender for assembly,
materials and review renders.

It is for the case where you need a model of a specific real object, no model exists under a licence you
can use, and "looks about right" isn't good enough. Every uncertain dimension is a named parameter; the
photos decide its value, and the review shows the model through each photo's own camera so differences
are real, not perspective.

## What's in it

Everything the agent uses is in `skills/building-3d-replicas/` (`<skill>` below):

| | |
|---|---|
| `SKILL.md` | The workflow and the rules that always apply; loaded when the skill is used. |
| `references/` | Lessons per stage (evidence, structure and building, fitting, measuring, review), frames, WebXR notes; read when a step needs them. |
| `scripts/fit_silhouette.py` | Fits shape parameters and every photo's camera together, by silhouette overlap, outline distance, measured landmarks and dark-part placement. |
| `scripts/measure.py` | Measures points in mm in one photo from 6+ points of known position (interiors, details the outline can't see). |
| `scripts/review.py`, `render_views.py` | A review round: the model rendered through each solved photo camera, beside the photo, with sizes and budget checks. |
| `scripts/render_cams.py` | Renders the model through any solved or eye/look camera, beside its photo. |
| `scripts/compare_mesh.py` | Grades a model against a reference mesh (a museum scan, a maker's CAD) in mm. |
| `examples/cowbell/` | A complete worked example on public-domain material, graded against the museum's scan. |
| `assets/model-template/` | An empty model folder to copy. |
| `agents/openai.yaml` | Display metadata for Codex and ChatGPT. |

At the repo root: `.claude-plugin/` and `.codex-plugin/` (plugin manifests; the marketplace that lists them
is [davo20019/plugins](https://github.com/davo20019/plugins)), `evals/` (scenarios for checking an agent's use of the skill) and `tests/`.

## Install

The skill is `skills/building-3d-replicas/`. Pick the way your agent installs things:

| Agent | Install |
|---|---|
| Claude Code (plugin) | `/plugin marketplace add davo20019/plugins`, then `/plugin install building-3d-replicas@davo20019` |
| Codex (plugin) | `codex plugin marketplace add davo20019/plugins`, then `codex plugin add building-3d-replicas@davo20019` |
| Codex (skill only) | ask Codex: `$skill-installer install skills/building-3d-replicas from davo20019/building-3d-replicas` |
| Any agent that reads Agent Skills (Claude Code, Codex, Cursor, Gemini CLI and others) | `npx skills add davo20019/building-3d-replicas` |
| By hand | copy `skills/building-3d-replicas/` into `~/.claude/skills/` (Claude Code) or `~/.agents/skills/` (Codex) |

Then ask for a model of a real object; the agent loads the skill when the request matches its description.

Requirements on the machine that runs it: [uv](https://docs.astral.sh/uv/) (it creates the pinned Python
environment on first use), [Blender](https://www.blender.org/) 4.2+ on PATH as `blender` (tested with 5.2),
Node 18+ for `npx @gltf-transform/cli`, and ffmpeg if you work from video. Not for claude.ai or the Claude API's
code sandbox: they have no Blender.

## Walkthrough: the cowbell

The example rebuilds a cowbell in the National Museum of American History (object 2018.0174.01) from one
CC0 museum photo, its published size, and four renders of the museum's CC0 scan through known cameras. The
scan's mesh is never used to build: it is the answer key.

```sh
cd skills/building-3d-replicas/examples/cowbell
./fetch_refs.sh                                   # the photo and scan (CC0), and the four scan renders
S=../..                                           # the skill's folder
uv run --project $S python $S/scripts/fit_silhouette.py .   # cameras for all five pictures, then the shape (~15 min)
./build.sh                                        # CAD parts -> Blender -> out/cowbell.glb
uv run --project $S python $S/scripts/review.py .         # review/round-N/sheet.png
uv run --project $S python $S/scripts/compare_mesh.py check/scan.json   # the grade, in mm
```

[REPORT.md](skills/building-3d-replicas/examples/cowbell/REPORT.md) has the numbers from each step: the cut-outs, the
solved cameras against the true ones, and the replica against the scan.

## Your own object

```sh
cp -r <skill>/assets/model-template path/to/your/project/models/<name>   # then set SKILL= in its build.sh
```

Then follow `SKILL.md`: evidence from every side, the structure decided by looking at all views, the
uncertain sizes as parameters in `cad.py`, a fit with `params: {}` first to check the cut-outs and
cameras, then the shape, then review rounds until the remaining differences are deliberate or unknowable.

## Status: early (0.2)

Proven so far on three objects: a museum cowbell graded against its scan (1.4 mm mean, 4.4 mm at the 95th
percentile on 266 mm), a wrist altimeter and a full-size pickup truck with its interior. Known limits:

- Camera angles solved from real photos can be 10 to 15 degrees off when the model is simpler than the
  object (distances stay within a few percent); fixing published sizes keeps the shape right.
- A full fit takes about 15 minutes; most of it is the CAD rebuild per step.
- Tested on macOS with Blender 5.2. Linux should work but is untested; Windows isn't supported (shell scripts).
- The evaluations in `evals/` are written but have not yet been run across models.

## Reference material and licences

The code is MIT. Reference photos are not: keep shop photos, video frames and anything else you may not
redistribute out of any repository you publish (the template's `.gitignore` keeps `refs/` local). Prefer
evidence you may share: your own photos, museum open-access collections, Wikimedia Commons (record each
file's licence in `refs/SOURCES.md`). Leave out logos and wordmarks, and check before publishing a replica
of a product whose shape is itself a protected design.

## Releasing

Claude Code and Codex keep users on the version in the plugin manifests, so every release needs a new
version. Commit your changes, then:

```sh
python3 tools/release.py patch "What changed, in one line"    # or minor, major, or an exact X.Y.Z
```

It writes the version into both plugin manifests, SKILL.md and pyproject.toml, adds the line to
CHANGELOG.md, runs the checks, commits, tags `vX.Y.Z` and pushes. `tests/test_versions.py` and the GitHub
Actions check fail if the versions ever disagree.

## Tests

```sh
uv run --project skills/building-3d-replicas pytest tests -m "not slow"   # compare_mesh and measure, exact answers
uv run --project skills/building-3d-replicas pytest tests                 # also the cowbell end to end: needs Blender and fetch_refs.sh (minutes)
```
