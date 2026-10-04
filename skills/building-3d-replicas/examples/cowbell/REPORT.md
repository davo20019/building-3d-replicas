# Cowbell: what happened, step by step

The point of this example is that the answer is known. The museum's CC0 scan is never an input; it grades
the replica (`check/scan.json`), and its four renders come with the true cameras (`refs/scan/views.json`).
Every number below can be reproduced with the commands in the README.

## 1. Evidence

- One museum photo (CC0), front, shot from above on white with a drop shadow to the right.
- The published size: 266.7 x 88.9 x 63.5 mm.
- Four renders of the scan, standing in for the photos a person would take from other sides: front, side,
  three-quarter from above, and from below. Their focal lengths are given to the fit as a camera's EXIF
  would give them; their angles and distances are not.

What no picture shows: the wall thickness, the inside, the clapper's exact size. They stay guesses.

## 2. Structure

A tapered box lofted from the mouth to the crown, open at the mouth; a tube handle, red up to the paint
line and black above it (two parts, so the dark channel can place the line); two loops; a clapper on its
own swinging node. First guesses from the photo, scaled by the published height (spec.md).

## 3. Fitting, and what went wrong

Each row is one full run of `fit_silhouette.py`; the grade is `compare_mesh.py` against the scan after a
rigid alignment (mean / 95th percentile in mm, the worse of the two directions).

| Run | Change | Grade (mean / p95) | What it showed |
|---|---|---|---|
| first guess | photo and published size only | 1.92 / 5.33 | the baseline to beat |
| 1 | 12 parameters, outlines only | 1.64 / 5.67 | mean better, worst areas worse: the body grew to 130 mm (real ~113) to fill something at the crown |
| 2 | loops as flat straps 19 mm wide (the side view shows them face-on), not 3 mm wire | 1.44 / 5.53 | better, but the bottom-up camera flipped to above the bell |
| 3 | hand-marked landmarks in every view, mouth corners included | worse | the cameras bent to meet the marks: two errors at once, below |
| 4 | the scan's y = 0 is the clapper ball, the rim is 5 mm up; frame fixed; mouth corners dropped (rounded, can't be marked to a pixel) | - | cut-outs collapsed: see run 6 |
| 5 | crisp landmarks only; a fit-only "mouth" plate, dark from below, so the low view knows it is below | 1.33 / 4.99 | good shape, cameras still 10-15 degrees off |
| 6, 7 | focal lengths given; `refine` turned off | 1.45 / 5.33 | `refine` had been locking in a bad first camera's outline |
| 8 | the handle-top landmarks removed (they duplicate the outline's top and held a museum camera in a local minimum) | 1.51 / 5.80 | outlines all fit (IoU 0.92 to 0.96), but front and side cameras at 22 degrees (truth 8): the shape absorbed it, 12 mm too tall |
| 9 | published height and width fixed, not fitted | 1.33 / 4.60 | the shape settles; front and quarter cameras still 10-15 degrees off |
| self-test | the fit on renders of its own model, where the shape is exact | - | front camera 34 degrees off: two bugs in fit_silhouette.py, below |
| 10 | both bugs fixed | **1.37 / 4.37** | final |

The self-test (`tests/test_fit_self.py`) renders the model through the same four true cameras and solves
them again. With the shape exact, any error is the fit's own, and there were two:

- The photo's cut-out filled every enclosed hole, the model's render didn't. The gap between each loop,
  the handle and the crown is enclosed, so it was solid in the photo and open in the model, and the
  cheapest way to close it was to raise the camera until the crown's top showed through. Both are filled
  now. Every object with a handle, a loop or spokes was affected.
- The tilt search started from the cut-out's centroid. A bottom-heavy object's centroid is far from the
  model's centre, and the search picked the tilt that hid the offset. Each start is now scaled and moved
  so the model's bounding box matches the cut-out's first.

After the fixes the fit recovers its own model's cameras within 2 degrees and 0.3 % in distance.

Lessons, all now in SKILL.md:

- **Outlines trade tilt for height.** A tapered box seen more steeply from above looks shorter; the fit
  made it taller instead of moving the camera. Fix what is published (height, width) and give the focal
  length when it is known.
- **A side view shows what the front can't.** The loops are 19 mm wide straps; as 3 mm wire they left a
  gap in the side outline that the body grew into.
- **Landmarks must be crisp.** Rounded corners marked by eye were 4 to 6 mm off and pulled every camera.
- **Check the frame of the answer key too.** The scan's lowest point was the clapper ball, not the rim.
- **`refine` only for metal or clutter.** On a clean backdrop it can only make a bad first camera worse.
- **Up from down, again.** From below, the open mouth shows dark inside; a fit-only plate in the mouth,
  listed as dark for that view, tells the fit which side it is on.

## 4. Result

Replica against the scan (`check/scan.json`), mm:

| | mean | 95th percentile | max |
|---|---|---|---|
| extra material (replica to scan), as placed | 1.55 | 5.06 | 18.3 |
| missing material (scan to replica), as placed | 1.21 | 3.81 | 10.7 |
| extra material, after rigid alignment | 1.37 | 4.37 | 17.6 |
| missing material, after rigid alignment | 1.12 | 3.57 | 10.7 |

The alignment moves the replica 3.4 mm down and turns it 0.5 degrees: the frames agree to a few mm.

Fitted against the scan (sections through the scan, for comparison only):

| | fitted | scan |
|---|---|---|
| mouth depth | 56.7 | 58.4 |
| body height, mouth to crown | 107.0 | ~113 |
| crown | 69.3 x 33.9 | ~65 x 30 (at 110 above the rim) |
| handle diameter | 18.3 | 18.0 to 18.7 |
| loops' outer edge | 24.9 | ~24.7 |

Cameras solved from the scan renders, against the truth (pitch / yaw / distance):

| View | Error |
|---|---|
| front | +16 / -7 degrees, +2 % |
| side | -3 / -1 degrees, +2 % |
| three-quarter | -8 / -15 degrees, +4 % |
| from below | 0 / -12 degrees, +2 % |

Distances are good; angles are not. On the model's own renders the same fit is within 2 degrees, so this
is the model being simpler than the bell (next section), not the fit. Outlines can't see the difference
between a camera 15 degrees higher and a bell whose crown is a little narrower: here the published sizes
kept the shape right while the cameras took up the slack.

Budget: 1,772 triangles, an 18 KB GLB. The clapper swings on its own node (`out/cowbell.json`).

## 5. Differences that remain

- The real crown's shoulder curves into a weld blob around the handle; the model's crown is a flat top
  with a fillet. Most of the worst 5 % is here and at the handle's dented top.
- The narrow sides have a folded seam with a slit; not modelled.
- The mouth flares slightly over its last 15 mm; the model's sides are straight.
- The real loops are bent by hand and not quite symmetric (the right one sits ~2.5 mm lower).
- The enamel's colour is matched by eye, not sampled and calibrated.

Each of these is a parameter or a part that could be added; the scan says how much each is worth.
