---
name: build-3d-model
description: Use when a project needs a 3D model of a real object that doesn't exist under an acceptable license, and it should be an exact replica. Gathers evidence from every available view, builds the object with parametric code-CAD (build123d) and headless Blender, fits uncertain dimensions to the photos by numbers, and reviews it through each photo's solved camera.
---

# Build an exact replica of a real object

The goal is a model indistinguishable from the real object. Judge by numbers first, eyes second.

`<skill>` below is this skill's folder; run its Python as `<skill>/.venv/bin/python` (set up once with
`uv sync` in `<skill>`, see README.md). Blender, ffmpeg and Node (for `npx @gltf-transform/cli`) must be on PATH.

Worked example: `<skill>/examples/cowbell/` (a museum's cowbell, CC0 photo and scan). Copy it as the
starting point; its REPORT.md walks through every step with the numbers, and its scan grades the result.

## Layout

One folder per model, anywhere in your project (`<model>` below):

```
<model>/
  spec.md        real dimensions, each with a source; guesses listed under "Unknowns"; the structure and parameter list
  refs/          photos and video frames, comparison only, never shipped, with SOURCES.md (each file's source and licence)
  cad.py         parametric rigid parts in mm (build123d) -> parts/*.stl; uncertain sizes live in P
  params.json    fitted values of P (written by fit_silhouette.py)
  textures.py    drawn textures (dials, labels, decals, normal maps) -> parts/*.png
  assemble.py    headless Blender: import, materials, UVs, pivots, soft parts -> out/<name>.glb + .json
  build.sh       runs all of the above, then gltf-transform (meshopt + webp), keeping the node tree and materials
  review.json    expected sizes, budget, exposure, frame, and the "fit" block
  fit/           per photo: camera.json, target.png, overlay.png, report.md
  review/round-N/  sheet.png + report.md per round
  check/         compare_mesh.py jobs, when a reference mesh exists

<skill>/scripts/fit_silhouette.py  fit shape parameters and each photo's camera by silhouette (one photo or several)
<skill>/scripts/measure.py         measure points in mm in one photo from 6+ known reference points (interiors, details)
<skill>/scripts/review.py          review round: renders through every solved photo camera (render_views.py)
<skill>/scripts/render_cams.py     render the model through any solved or eye/look camera, beside its picture
<skill>/scripts/compare_mesh.py    surface distance in mm against a reference mesh (scan, maker's CAD)
```

Each script's docstring documents its inputs. Frames and GLB conventions: `docs/frames.md`.

## Process

1. **Evidence, from every side.** One front photo hides most of the shape (side scoops and corner facets often only show in an angled shot). Prefer evidence you may publish if the model will be shared.
   - Manufacturer pages and manuals for dimensions; write each in `spec.md` with its source. Manuals carry the best numbers (overhangs, clearances, offsets). Some makers' sites refuse scripted requests; their regional mirrors often don't.
   - Museums with open-access collections (Smithsonian Open Access, many others under CC0) publish photos, sizes and sometimes scans.
   - Wikimedia Commons, for anything photographed in public: list a category with the API (`action=query&list=categorymembers&cmtitle=Category:<X>&cmtype=file`), fetch licence and author with `prop=imageinfo&iiprop=url|size|extmetadata`, and download at a standard thumbnail width (3840; other widths get HTTP 400). Record each file's licence in `refs/SOURCES.md`.
   - Shops that sell it: each shoots different angles (Shopify stores list all images at `<product-url>.json`). These photos are for comparison only; don't publish them.
   - Video: your own footage is best. Downloading from YouTube is against its terms of service unless the video's licence or its owner allows it; check before you do. Make contact sheets (`ffmpeg -vf "fps=48/<duration>,scale=320:-1,tile=8x6"`), then pull full-resolution frames at the useful timestamps. Check it is the same product: lookalikes, prototypes and modified ones are common.
   - Label views by geometry, not by impression: a side view with the front pointing to the left of the frame shows the object's left side.
   - Write down which surfaces no photo shows. They stay marked guesses.
2. **Decide the structure by looking at all views.** The fit only tunes the shape you give it; it cannot invent a scoop or a facet. Describe every feature (facets, scoops, windows, lips, bevels) and give each uncertain size a parameter in `cad.py`'s `P`.
   - An object of flat faces (a vehicle body, a building, a machined block) is best built as the intersection of half-spaces, one plane per face, each through named corner points. Every face stays flat whatever the parameters, and convex creases come out by construction. Two neighbouring faces that must both survive have to share their crease line.
   - Keep what changes between photos out of the shape: suspension height, steering, open doors, a lowered antenna. These are per-photo pose values in the fit (`rideOffset`), not parameters.
   - If people will look inside (a vehicle, a cockpit, a room), plan the interior and see-through glass from the start: the shell has to be hollow, and the inside of a solid is invisible in real-time engines (back faces are culled).
   - Decide which parts move (doors, lids, wheels, needles, a clapper) now, not after the build: each becomes its own node, cut out of the shell along its seams with a hinge or pivot, and everything mounted on it goes with it. The manual says where the controls are; leave a fixed strip where a control sits on the body.
   - Make a separately coloured part its own part (a black grip on a red handle): the fit's dark channel then places its boundary.
3. **Pick a method per part:**
   - rigid, precise, mechanical: **code-CAD** (`cad.py`)
   - flat printed graphics: **drawn texture** (`textures.py`, PIL, 4x supersampled; ship a font you may redistribute)
   - simple soft parts (webbing, cables): **swept mesh in Blender** (`assemble.py`)
   - generic and available under CC0/CC-BY: **library**
4. **Fit by numbers.** `<skill>/.venv/bin/python <skill>/scripts/fit_silhouette.py <model>`, configured by `review.json`'s `fit` block. It solves each photo's camera, fits the parameters and reports overlap (IoU), mean outline error in mm and landmark error.
   - One photo: the photo, the HSV range that cuts the part out, the parameters it can see, and a landmark inside the part.
   - Several photos (`photos: [...]`): each with a starting `view` (pitch, yaw, roll), a cut-out `mask`, measured pixel `landmarks` for named model points, and the `parts` it sees. The shape parameters are shared, so each photo constrains what it can see and nothing else.
   - **Run it with `params: {}` first**: cut-outs and cameras only. Check every `target.png` (and `target_dark.png`, `overlay.png`) before fitting any shape: a bad cut-out makes every number wrong. A drop shadow or a neighbouring object in the cut-out: mark it with `exclude` polygons.
   - Landmarks: crisp points only (see the rules, Fitting).
   - Large objects: give landmarks that span the height (a wheel centre and the tyre's contact point under it) and `cameraHeightMm`, or the fit trades camera tilt for distance and puts the camera under the ground.
5. **Measure what the outline can't see**: an interior, a handle, a light's height, a seam. Never place these by eye. Use `<skill>/scripts/measure.py <job.json>`:
   - Look in the manual first: its illustrations are rendered from the maker's CAD, so they have true proportions. Scale each from a published size inside it, and render the model from a similar camera to compare.
   - Otherwise pick the photo or frame that shows the feature best, from a long lens if there is one.
   - Mark at least 6 reference points whose positions are known in mm, spread over the photo: published sizes, parts already fitted, a part of known size (a screen's corners, with a fixed focal length: then 4 do).
   - Mark each point to measure on a plane you know it lies on (the door's plane, the floor, the dash top).
   - Trust the result when the references reproject within a few px. References near one plane leave focal length and distance loose, but points on planes near them still measure well.
   - A fitted camera measures points near the outline's plane well, but its height and distance are barely constrained by an outline: points a metre or more behind that plane can be off by hundreds of mm. Measure deep features from a photo taken near them, with references near them.
   - Check that you have marked what you think: measure one feature whose position is already known in the same view first, and stop if it misses.
   - Put each measurement in `spec.md` with the job that made it, and give the job an `expect` block when the answer is known: it is then a test.
6. **Build** with `./build.sh`.
7. **Review** with `<skill>/.venv/bin/python <skill>/scripts/review.py <model>`. The sheet puts each photo next to the model rendered through that photo's solved camera, so differences are real, not perspective. List every difference in `report.md`, fix, run again. Stop and ask after 5 rounds without progress.
8. **Grade against a reference mesh when one exists** (a museum scan, the maker's CAD): `<skill>/scripts/compare_mesh.py check/<job>.json` gives mean and 95th-percentile surface distance each way, before and after a rigid alignment. Never build from the reference; it is the answer key.
9. **Test where it will be used** (a headset, a game engine, a browser), with a person looking at it. See `docs/webxr.md` for WebXR.
10. **Done** when the automatic checks pass, the remaining differences are deliberate or unknowable (and written down), and a person has approved it where it will be used.

## Rules learned the hard way

Grouped by stage. Each came from a model that went wrong.

### Evidence

- **Trust the numbers over your eye.** A front photo read as shot from above was shot from below: the dial's position inside the outline proved it.
- **A photo of the real object from where the viewer will be beats renders read for ratios.** The maker's renders showed a console in a white trim and a lid at its open thickness; one photo from the driver's seat of a real truck showed a satin top and a lid a quarter as tall.
- **Each photo shows a state.** Mirrors folded or not, suspension kneeling, a lid open, a door ajar: model the state the object is used in, and write down which state each photo shows. What changes between photos is a per-photo pose value in the fit, not a shape parameter.
- **Service and body repair manuals have orthographic, dimensioned drawings.** Check their scale with several labelled dimensions before using them (four labelled diagonals agreeing to 2 mm); a figure from a reader's protractor is not a source.
- **When published numbers disagree with each other** (track plus tyre width came out wider than the published width), write the conflict down and leave it; don't force one to fit.
- **Vet a third-party model's provenance before using it as a library part.** Free "CC-BY" uploads are often re-uploads or game rips (identical triangle counts across uploaders, game tags), and paid stock licences usually forbid shipping an extractable GLB.
- **Museum open-access sites often block scripted page requests**; their APIs, bulk metadata and image delivery services usually don't.
- **Tools that did not help:** monocular depth (Depth Anything V2 gave a smooth blob, relative only); image-to-3D (TRELLIS returned a flat disc after its background removal deleted a silver part). Don't use them for exact replicas.
- **Trademarks:** leave out logos and wordmarks. A distinctive product shape can itself be protected: don't publish replicas of trademarked designs without checking.

### Cut-outs

- **Colour can't cut out bare metal, silver or chrome.** It takes the colour of whatever it reflects. Use the `grabcut` mask: a rectangle and a ground line first, then `refine`, which runs GrabCut again seeded by the model's own outline through the solved camera. Inside the outline, cut dark parts with a fixed brightness limit (`dark: {"valueMax": 60}`): Otsu splits the steel itself where it reflects shade.
- **On a coloured object, cut its neutral parts by saturation** (`dark: {"satMax": 90, "valueMax": 140}`): red enamel in shade is as dark as a black grip, but far more saturated.
- **`refine` only when colour can't separate the object.** A poor first camera pulls the cut-out toward the wrong model and locks the error in. A coloured object on a plain backdrop needs a rectangle and `exclude` polygons, nothing more.
- **Shadows and neighbours read as part of the object.** A ground line removes what is below the contact points; `exclude` polygons remove a drop shadow, a car parked alongside, a sign post touching the roof.

### Fitting

- **Check that a photo can measure a parameter before trusting its value.** Score the outline over a range of the parameter, re-solving the camera each time: if the score is flat, the photo can't tell and the fitted value is arbitrary. A straight-on photo's outline is only the widest section; it couldn't tell a 1.5 mm corner rounding from 14 mm, the fit kept 1.5, and the case came out chamfered where the real one is one soft curve. Angled photos, and the person who has held the object, decide those.
- **Fix what is published; fit only what isn't.** Left free, published sizes absorb camera errors (a bell grew 12 mm taller while its cameras looked down 14 degrees too steeply).
- **A value at its bound, or a camera at its prior's limit, is a warning.** The structure or the range is wrong, or the photo can't constrain it. A front photo whose camera solved 3 m up (at the height prior's limit) left every width only it constrained unreliable; a windshield base stuck at its bound was still unsettled after two drawings.
- **Symmetric outlines can't tell up from down.** Always give the fit a cue inside the part: a landmark, or a dark part (from below, the inside of an open mouth shows dark; a fit-only plate there, listed as dark for that view, tells the fit which side it is on).
- **Landmarks must be points you can mark to a pixel or two** in every photo: the end of a handle, a strap's sharp corner, a bolt, a wheel centre. Not rounded corners: marked by eye they were 4 to 6 mm off and bent every camera. Large objects need landmarks that span the height (a wheel centre and the tyre's contact point under it).
- **When cues disagree, the structure is wrong.** If the outline wants one camera and the landmark another, a feature is missing or misplaced (a depth, a taper). Find it; don't average. A vehicle whose outline wanted a camera below the ground sat 55 mm lower on its wheels than its spec height (a parked truck on air suspension kneels); a per-photo ride offset fixed it. Thin 3 mm loops where the real ones were 19 mm straps left a gap in the side outline that the body grew into.
- **Give the focal length when you know it** (`focalPx`, from EXIF: focal mm / sensor width mm x image width px). Outlines alone trade tilt for perspective.
- **Measured values override fitted ones.** Apply them after params.json so a refit can't move them; a fit's dark cut-out had merged bumper, flare and tyre and never constrained them.
- **Measure a pose value directly when you can.** The fit's per-photo ride offset was 26 mm off; the roof peak measured through the same camera, minus the spec height, gave it.
- **Check the answer key's frame too.** A scan's lowest point was the clapper ball hanging below the rim, not the rim.

### Measuring

- **Perspective shortens what is further away**, even in a "straight" side view: a nose on the centreline a metre behind the wheels' plane looked 150 mm short. Measure through the solved camera, never by scaling pixels.
- **Check a picture's scale against a second known size before measuring with it.** One reference makes a scale; two make a check. A seat drawing scaled from the head room put the dummy's head 40 mm through the roof; a second span gave the right scale.
- **Solve a camera for every perspective picture you compare against, then render the model through it** (`measure.py` writes `<job>.camera.json`; `render_cams.py` renders through it, beside the picture, optionally only some parts). Side-by-side pairs find errors that renders alone miss.
- **A rectangle seen nearly face-on can't fix the focal length.** Add references at a different depth.
- **Published room dimensions place surfaces, not just people.** Hip room sets the armrests' faces, shoulder room the trim above them, head room the seating point's height (SAE J1100: along a line 8 degrees back from vertical, plus 102 mm). Calibrate such a rule on the row you measured and apply the same correction to the others.
- **Audit the built model against published figures by their definitions, with a script, after every change.** Measuring the built parts by SAE J1100 found front head room 43 mm too large: the line ran past a thin beam to the glass. Every figure then came within 2 mm.

### Building

- **Rounded, organic shapes: loft through sections, don't fillet a box.** Sections with the same edges at several depths, inset along a quarter ellipse toward the front, give a roll-off that meets the faces tangentially; a box with chamfers and small fillets reads as machined and angular.
- **Faceted parts from two silhouettes.** Intersect a side outline extruded across the part with a front outline extruded along it: both views' outlines come out exactly, every face is flat, and it costs a few hundred triangles. Recesses are boxes subtracted 20 to 45 mm deep.
- **Attach features to the geometry they belong to.** A light bar placed by its own coordinates sat 95 mm below the crease it runs along; built along the crease line, it stays there whatever the parameters. A part built through a point 22 mm inside its housing vanished; place parts on the face they mount to.
- **Build from positive parts, not by cutting windows.** A rim cut from a disc came out as shards; hub, spokes and ring unioned came out clean. Likewise hollow a filleted solid by subtracting a smaller loft: the kernel's shell operation fails on fillets.
- **No coplanar faces.** Parts that touch must be offset by at least 0.05 to 0.1 mm, or they z-fight. Inset panels (glass, lights) go in a pocket 1 mm under the surface, 0.5 mm smaller all round. A hole behind a pane has to start above the pocket floor, or a thin sheet closes it.
- **Glass edges need their black frit band**, or the trim behind tinted glass shows through at its corners.
- **Cut moving parts with regions, not by hand.** A door is the shell intersected with a region (between its seams, below the roof, outboard of the window plane), so the roof never comes away with it. Split every part that crosses the region the same way, skip empty results, and clear `parts/` at the start of each run, or stale STLs come back.
- **Check moving parts in every state.** With frameless windows down and a door open, a sliver of steel floated over the opening; render every door open and closed, every lid, every wheel turned.
- **Moving parts get their own node** with the pivot at the origin, and the `.json` says how to drive it. Parts that turn but don't spin (brakes) go in the steer node.
- **Interaction lives in the app, the model just names it.** Give each pressable part its own named mesh and each moving part its node, and write in the `.json` how to drive them.
- **Check every face that should look at the viewer.** Screens and dials built facing +z faced away; render from the seat or the hand before calling it done, and map a screen's texture so its right is the viewer's right.
- **Give every extrusion an explicit direction.** `extrude(face, amount)` follows the face's normal, which depends on the polygon's winding: mirrored outlines go the other way.
- **Profiles drawn in a reversed axis hide mistakes.** With s measured backward (z = front - s), "behind the face" is smaller s; keep profiles in the model's own axes.
- **Build scripts: module-level names shadow helpers.** A loop variable `belt` in `__main__` replaced the function `belt()`; name helpers distinctly.

### Triangles, materials and export

- **Tessellation per part.** Round parts at fine tolerance explode the triangle count (an O-ring was 14k triangles): pass coarser `tolerance`/`angular` to `save()` for small or round parts. But where a curve must read (a padded seat crown), tessellate finely enough that it survives (about 5 degrees a facet). Identical parts share one mesh in Blender (`object.copy()`), stored once in the GLB.
- **Rounded edges cost triangles.** Filleted interior blocks took a vehicle from 23k to 59k triangles; flat facets with bevels in Blender gave a better look at 33k.
- **Bevel padded and moulded edges in Blender** (Bevel modifier, 3 segments, 25 degree limit, hardened normals; remove smooth-by-angle first or it marks the bevels sharp again). Sharp-edged flat-coloured blocks read as silhouettes.
- **Enclosed spaces need baked light.** A real-time sky light and reflection probe don't know a cabin is enclosed, so everything inside is lit evenly and reads flat. Bake Cycles diffuse (direct and indirect) into a light map on its own UV set, smooth it within each island, and export it as the glTF occlusion map.
- **Metal only where the scene has environment lighting.** Metallic surfaces render black without it, and still go black in a dark footwell: use metallic 0 with a clear coat there (painted metal is a dielectric anyway).
- **`gltf-transform optimize` breaks things by default.** It flattens the scene and joins meshes, deleting every moving node; its palette step merges textured materials and renames ones the app looks up by name; and it prunes UVs no texture uses, such as those of a mirror the app draws a live view onto. Pass `--flatten false --join false --instance false --palette false`, and `--prune-attributes false` when the app textures a part at run time.

### Review

- **Review renders lie unless calibrated.** Khronos PBR Neutral tone mapping (AgX desaturates, Standard clips). Set `exposure` in `review.json` so a neutral in the photo matches the render; compare colours by sampling pixels. Keep the key light off-axis so glass doesn't mirror it into the camera. Metal needs `"environment": "sky"`, and still won't match each photo's surroundings.
- **Blender lens shift moves the view**, so the content moves the other way: shift_x = (W/2 - cx) / max(W, H), shift_y = (cy - H/2) / max(W, H).
