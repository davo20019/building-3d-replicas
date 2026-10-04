# Measuring what the outline can't see

Interiors, handles, a light's height, a seam: measured in one photo from known reference points with
`scripts/measure.py` (its docstring documents the job format). Read for workflow step 5.

## How to measure

- Look in the manual first: its illustrations are rendered from the maker's CAD, so they have true proportions. Scale each from a published size inside it, and render the model from a similar camera to compare.
- Otherwise pick the photo or frame that shows the feature best, from a long lens if there is one.
- Mark at least 6 reference points whose positions are known in mm, spread over the photo: published sizes, parts already fitted, a part of known size (a screen's corners, with a fixed focal length: then 4 do).
- Mark each point to measure on a plane you know it lies on (the door's plane, the floor, the dash top).
- Trust the result when the references reproject within a few px. References near one plane leave focal length and distance loose, but points on planes near them still measure well.
- A fitted camera measures points near the outline's plane well, but its height and distance are barely constrained by an outline: points a metre or more behind that plane can be off by hundreds of mm. Measure deep features from a photo taken near them, with references near them.
- Check that you have marked what you think: measure one feature whose position is already known in the same view first, and stop if it misses.
- Put each measurement in `spec.md` with the job that made it, and give the job an `expect` block when the answer is known: it is then a test.

## Lessons

- **Perspective shortens what is further away**, even in a "straight" side view: a nose on the centreline a metre behind the wheels' plane looked 150 mm short. Measure through the solved camera, never by scaling pixels.
- **Check a photo's scale against a second known size before measuring with it.** One reference makes a scale; two make a check. A seat drawing scaled from the head room put the dummy's head 40 mm through the roof; a second span gave the right scale.
- **Solve a camera for every perspective photo you compare against, then render the model through it** (`measure.py` writes `<job>.camera.json`; `render_cams.py` renders through it, beside the photo, optionally only some parts). Side-by-side pairs find errors that renders alone miss.
- **A rectangle seen nearly face-on can't fix the focal length.** Add references at a different depth.
- **Published room dimensions place surfaces, not just people.** Hip room sets the armrests' faces, shoulder room the trim above them, head room the seating point's height (SAE J1100: along a line 8 degrees back from vertical, plus 102 mm). Calibrate such a rule on the row you measured and apply the same correction to the others.
- **Audit the built model against published figures by their definitions, with a script, after every change.** Measuring the built parts by SAE J1100 found front head room 43 mm too large: the line ran past a thin beam to the glass. Every figure then came within 2 mm.
