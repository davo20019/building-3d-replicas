# Living and soft objects: anatomy from scan data, and motion

For organs and other living tissue (a heart, a joint, a brain), and for any soft part that moves by deforming
rather than on a hinge. Read with structure-and-building.md, whose rules still apply: parts assembled as they
are made, each declaring what it is fixed to, motion checked every build. Worked from a beating heart: the
CT average of 19 adults, a second atlas carried onto it, valves, papillary muscles and chordae rebuilt to
published sizes, and a beat calibrated on chamber volumes.

## Contents
- Evidence: scan data and the literature
- Carrying a second atlas onto the scan
- Parts that must work are rebuilt
- Motion of soft tissue
- Checks

## Evidence: scan data and the literature

- **For anatomy the evidence is measured scan data, not photos.** Segmented CT or MRI meshes, statistical shape
  models and their population averages are published with open licences (Zenodo, journal supplements, CC BY);
  search for them before anything else. An average of many people is the best "normal" shape; one person's scan
  is one variant. A dataset you build on is evidence; a scan you only grade against is the answer key: don't
  build from that one (SKILL.md).
- **Check the import against the dataset's own published numbers first.** The heart's extracted LV muscle came
  to 135.3 cm³ against the dataset's 135.34 and its blood volumes to 126.6 and 149.8 mL against 126.5 and 149.7:
  that proved the labels, units and cavity extraction before anything was built on them.
- **Read every field the dataset ships.** Beyond the surfaces, the heart came with muscle-fibre directions and
  ventricular coordinates (apex to base, inside to outside of the wall, round the ventricle): those placed
  every later detail and drove the motion. Learn each field's convention by printing where its values lie
  (which coordinate value is the septum, which the front wall) before using it.
- **Know its axes.** Medical data is usually in patient coordinates (DICOM: x to the patient's left, y to the
  back, z up). Write the frame in spec.md and convert once, at export.
- **Collect the literature in one file before building**: each number with its paper, mean ± SD, and the
  population (sex, age, in vivo or cadaver, which phase of the cycle). Mark second-hand numbers "unverified"
  and gaps "not found"; never fill a gap from memory. A research subagent can do this while you build.
- **A number belongs to a state.** A distance published at end-systole doesn't fit a model at end-diastole;
  cadaver muscle is contracted and shorter than in life. Write each number's state next to it.

## Carrying a second atlas onto the scan

When the scan lacks parts another atlas has (the heart's CT had no coronary vessels), register the atlas
onto the scan and carry its parts across:

- Match each atlas structure only to the same structure on the scan (its ventricles to the ventricles, each
  atrium to its atrium), sampled by area. First a similarity (rotation, translation, one scale) by ICP with
  closest points both ways, then a smooth displacement field: Gaussian-weighted closest-point residuals, both
  ways, the kernel narrowing over a few stages (24 to 8 mm for a heart). Report the error per structure after
  each stage. Apply the same similarity and field to every carried part.
- **Then check where every carried part landed** (inside which tissue, how far from the surface): about 2 mm
  of residual sank two thirds of the coronary vessels' vertices into the muscle. Settle them: push each vessel
  out along the surface normal until its whole cross-section clears the surface, the push shared across the
  cross-section, and leave alone the ends that must enter something (a coronary ostium opens into the aorta).
- **Don't trust a carried part's geometry because its name is right.** One atlas's LV papillary muscles were
  twice the published length (chordae merged in) and one stood where neither belongs; its valves were in one
  state only and 5 to 11 mm off the scan's rings. Use such parts for positions they get right, cross-checked,
  and rebuild the rest.
- **When two sources disagree on a position, prefer the one that is consistent with itself.** The atlas's three
  tricuspid leaflets sat over its own three papillary muscles; a landmark rule ("the septal leaflet faces the
  basal septum") put them 50° off, because the basal septum's middle is pulled forward by the outflow tract.

## Parts that must work are rebuilt

Valves, cords, flaps: anything that moves by changing shape is built parametrically, on the scan's own
landmarks, in every state it takes, with the same vertices in each (so the states can morph):

- **Anchor on the scan, size from the literature.** Each valve's ring is the scan's (the outermost points of its
  valve plane, at mid-thickness, per angle bin, smoothed); leaflet sizes are published ones.
- **Solve shapes from the numbers, don't draw them.** The closed mitral valve was solved chord by chord: each
  leaflet's published length, less the coaptation zone, and the tenting depth split each chord. The closure
  line came out curved, close to the posterior ring, as in echo images. Two straight lines to a centre point
  gave a small anterior leaflet, the opposite of real anatomy.
- **Place from every published distance at once.** The LV papillary muscles' angles were only described in
  words; their tips' distances to the anterior ring (28 mm) and to each other (23 mm) were measured. Solving
  angle and level together against all three distances, with the description as a weak preference, put them
  within 0.5 mm. The guessed angles alone left them 6 to 9 mm off.
- **Assign by the anatomy's rule, not nearest.** Chordae fan from each papillary muscle to the leaflets it
  serves; "nearest head" left the deepest muscle with none. Assign by angle round the valve, among the muscles
  that serve that leaflet.
- **Build living parts as they grow.** A papillary muscle is a finger growing out of the wall (centreline from
  inside the wall, out along the wall's normal, curving towards its valve), not a cone standing on the wall.
- Cords: taut when the valve is shut; open, they keep their length and bow, capped (15% of their span) so they
  never loop.

## Motion of soft tissue

- **The rest pose is the scan's state**; each independent motion is one displacement field from it (for the
  heart: the ventricles at end-systole, the atria full, each valve open), exported as one morph target each.
  Weights over time come from measured timing (the cycle's phase durations), not from the eye.
- **Calibrate fields on measured quantities**: volumes, excursions, angles. Each chamber's inward motion was
  solved so it holds its published end-systolic volume, with the wall's outside moving so the muscle keeps its
  volume (it is nearly incompressible, so the wall thickens). Precompute the cavity's boundary triangles once:
  a volume is then a signed sum, 4 ms instead of 3 s, and calibration takes seconds.
- **Set motion on surfaces only, then fill the rest harmonically.** Rules evaluated everywhere tore the mesh
  (thousands of edges jumping over 2 mm). Applying them only on the surfaces that matter, smoothing along each
  surface (a wall's inside and outside are separate surfaces, so its thickening survives), then solving
  Laplace's equation for everything else (the wall's interior, attached tissue, vessels) with the far ends held
  where the body holds them, brought the tears to zero with every volume still on target.
- **Scale motion with distance; spread transitions over centimetres.** A thin wall moving towards the septum by a
  fixed amount drove points near the septum through it; a fraction of each point's distance is physical. A fade
  over 8 mm sheared muscle 100%; real tissue blends over 25 mm or more.
- **A vertex takes the motion of the surface it is mounted on**: sample only surface points of the mount, never
  an interior point (the inside and outside of a 4 mm wall move differently), and a shared boundary from all
  parts at once, so two touching parts can't separate. Muscles and cords take their motion from both ends:
  the base from the wall, the tip from the ring it keeps its distance to.
- **Solvers make no assumption of direction.** A bisection that assumed every function falls ran every
  parameter to its limit; check the sign at both ends and fail loudly when the target is outside the range.

## Checks

- A motion check every build: the volumes each field reaches against their targets, the muscle's volume kept,
  and tears counted as absolute jumps per edge (over 1 and 2 mm), not as a strain ratio, which sliver edges
  inflate.
- Render each state from inside, cut open along the part's own axis: a sign error on a normal had the papillary
  muscles pointing into the atrium, which no outside view showed.
- Draw the review from where the camera can see: a clip keeps one side; check which before blaming the model.
