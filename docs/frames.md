# Frames and GLB conventions

## The model frame

Every script works in the **model frame**: millimetres, **up +y**, **front +z**, right-handed (so +x is the
object's left as you face its front). `cad.py` builds in it, `fit_silhouette.py` and `measure.py` report in
it, and landmark functions return points in it.

Cameras in `fit_silhouette.py` are given as `[pitch, yaw, roll]` degrees: yaw turns the model about its up
axis, then pitch tilts it, then roll. Yaw 0 looks at the front; yaw -90 shows the model's +x side, 90 its
-x side. Each camera is a pinhole at `distanceMm` from a centre point (`centreMm`, or the model's bounding
box centre), with a scale in px per mm at that centre.

## Two GLB conventions (`glbFrame` in review.json)

| `glbFrame` | GLB axes | Use for | How assemble.py gets there |
|---|---|---|---|
| `"y-up"` (default) | up +y, front +z (glTF's own convention) | vehicles, scenes, anything that stands on the ground | Turn each part's mesh data into Blender's frame on import, `(x, y, z) -> (x, -z, y)`; the glTF exporter turns it back. |
| `"front+y"` | front +y, up -z | hand-held objects whose "front" is a face you look down at (a dial, a screen) | Build in Blender with the face toward +z; the exporter maps Blender +z to glTF +y. |

In both cases **never rotate the root**: convert the mesh data and node positions instead, so every moving
node keeps identity rotation and turns about its own axes. Scale the root by 0.001 (mm to metres) at export,
and write the frame in the model's `.json` (`"units"`), so whoever loads it knows which way is up.

`review.py`, `render_views.py` and `render_cams.py` read `glbFrame` and turn the import back into the model
frame, so their renders and the fit's cameras agree.
