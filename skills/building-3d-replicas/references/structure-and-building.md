# Structure and building

How to turn the views into a parametric model, which method to use per part, and the CAD, triangle,
material and export lessons. Read for workflow steps 2, 3 and 6.

## Contents
- Deciding the structure
- Method per part
- Building lessons
- Triangles, materials and export

## Deciding the structure

- An object of flat faces (a vehicle body, a building, a machined block) is best built as the intersection of half-spaces, one plane per face, each through named corner points. Every face stays flat whatever the parameters, and convex creases come out by construction. Two neighbouring faces that must both survive have to share their crease line.
- Keep what changes between photos out of the shape: suspension height, steering, open doors, a lowered antenna. These are per-photo pose values in the fit (`rideOffset`), not parameters.
- If people will look inside (a vehicle, a cockpit, a room), plan the interior and see-through glass from the start: the shell has to be hollow, and the inside of a solid is invisible in real-time engines (back faces are culled).
- Decide which parts move (doors, lids, wheels, needles, a clapper) now, not after the build: each becomes its own node, cut out of the shell along its seams with a hinge or pivot, and everything mounted on it goes with it. The manual says where the controls are; leave a fixed strip where a control sits on the body.
- Make a separately coloured part its own part (a black grip on a red handle): the fit's dark channel then places its boundary.

## Method per part

- rigid, precise, mechanical: **code-CAD** (`cad.py`)
- flat printed graphics: **drawn texture** (`textures.py`, PIL, 4x supersampled; ship a font you may redistribute)
- simple soft parts (webbing, cables): **swept mesh in Blender** (`assemble.py`)
- generic and available under CC0/CC-BY: **library**

## Building lessons

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

## Triangles, materials and export

- **Tessellation per part.** Round parts at fine tolerance explode the triangle count (an O-ring was 14k triangles): pass coarser `tolerance`/`angular` to `save()` for small or round parts. But where a curve must read (a padded seat crown), tessellate finely enough that it survives (about 5 degrees a facet). Identical parts share one mesh in Blender (`object.copy()`), stored once in the GLB.
- **Rounded edges cost triangles.** Filleted interior blocks took a vehicle from 23k to 59k triangles; flat facets with bevels in Blender gave a better look at 33k.
- **Bevel padded and moulded edges in Blender** (Bevel modifier, 3 segments, 25 degree limit, hardened normals; remove smooth-by-angle first or it marks the bevels sharp again). Sharp-edged flat-coloured blocks read as silhouettes.
- **Enclosed spaces need baked light.** A real-time sky light and reflection probe don't know a cabin is enclosed, so everything inside is lit evenly and reads flat. Bake Cycles diffuse (direct and indirect) into a light map on its own UV set, smooth it within each island, and export it as the glTF occlusion map.
- **Metal only where the scene has environment lighting.** Metallic surfaces render black without it, and still go black in a dark footwell: use metallic 0 with a clear coat there (painted metal is a dielectric anyway).
- **`gltf-transform optimize` breaks things by default.** It flattens the scene and joins meshes, deleting every moving node; its palette step merges textured materials and renames ones the app looks up by name; and it prunes UVs no texture uses, such as those of a mirror the app draws a live view onto. Pass `--flatten false --join false --instance false --palette false`, and `--prune-attributes false` when the app textures a part at run time.
