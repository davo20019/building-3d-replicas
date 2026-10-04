# Review and grading

Read for workflow steps 7 and 8.

- `scripts/review.py <model>` renders the model through every solved photo camera beside the photo, checks
  sizes and budget, and writes `review/round-N/sheet.png` and `report.md`. List every difference under
  "Differences", fix, run again.
- `scripts/render_cams.py` renders the model through any camera (one solved by `measure.py`, or eye/look)
  beside its photo, optionally only some parts: use it for manual photos and interiors.
- `scripts/compare_mesh.py check/<job>.json` grades the model against a reference mesh (a museum scan, the
  maker's CAD): mean, 95th percentile and max distance each way, before and after a rigid alignment. Give the
  job an `expect` block and it becomes a regression test.

## Lessons

- **Review renders lie unless calibrated.** Khronos PBR Neutral tone mapping (AgX desaturates, Standard clips). Set `exposure` in `review.json` so a neutral in the photo matches the render; compare colours by sampling pixels. Keep the key light off-axis so glass doesn't mirror it into the camera. Metal needs `"environment": "sky"`, and still won't match each photo's surroundings.
- **Blender lens shift moves the view**, so the content moves the other way: shift_x = (W/2 - cx) / max(W, H), shift_y = (cy - H/2) / max(W, H).
