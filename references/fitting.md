# Fitting shape and cameras to the photos

How to configure and run `scripts/fit_silhouette.py`, and what went wrong with cut-outs and fits before.
Read for workflow step 4. Every config key is documented in the script's docstring.

## Contents
- Running the fit
- Cut-outs
- Fitting lessons

## Running the fit

- One photo: the photo, the HSV range that cuts the part out, the parameters it can see, and a landmark inside the part.
- Several photos (`photos: [...]`): each with a starting `view` (pitch, yaw, roll), a cut-out `mask`, measured pixel `landmarks` for named model points, and the `parts` it sees. The shape parameters are shared, so each photo constrains what it can see and nothing else.
- **Run it with `params: {}` first**: cut-outs and cameras only. Check every `target.png` (and `target_dark.png`, `overlay.png`) before fitting any shape: a bad cut-out makes every number wrong. A drop shadow or a neighbouring object in the cut-out: mark it with `exclude` polygons.
- Large objects: give landmarks that span the height (a wheel centre and the tyre's contact point under it) and `cameraHeightMm`, or the fit trades camera tilt for distance and puts the camera under the ground.

## Cut-outs

- **Colour can't cut out bare metal, silver or chrome.** It takes the colour of whatever it reflects. Use the `grabcut` mask: a rectangle and a ground line first, then `refine`, which runs GrabCut again seeded by the model's own outline through the solved camera. Inside the outline, cut dark parts with a fixed brightness limit (`dark: {"valueMax": 60}`): Otsu splits the steel itself where it reflects shade.
- **On a coloured object, cut its neutral parts by saturation** (`dark: {"satMax": 90, "valueMax": 140}`): red enamel in shade is as dark as a black grip, but far more saturated.
- **`refine` only when colour can't separate the object.** A poor first camera pulls the cut-out toward the wrong model and locks the error in. A coloured object on a plain backdrop needs a rectangle and `exclude` polygons, nothing more.
- **Shadows and neighbours read as part of the object.** A ground line removes what is below the contact points; `exclude` polygons remove a drop shadow, a car parked alongside, a sign post touching the roof.

## Fitting lessons

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
