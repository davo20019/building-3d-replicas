# Using the models in WebXR (and other real-time engines)

Notes from shipping these models in a WebXR site (Babylon.js, Meta Quest). None of this is needed to build
a model; it is what made them work once loaded.

## Budgets (Quest-class standalone headsets)

| Object | Triangles | Textures | GLB after build.sh |
|---|---|---|---|
| Hand-held | under 10k | up to 1024 px | under 500 KB |
| Vehicle | under 60k | up to 2048 px | under 3 MB |

## Lighting

- Metallic surfaces need environment lighting (image-based lighting). In Babylon.js, a `ReflectionProbe`
  that renders the sky (and the ground) once, set as `scene.environmentTexture`, is enough. Without one,
  metal renders black: use metallic 0 with a clear coat instead.
- A `ReflectionProbe` must be drawn before it becomes `scene.environmentTexture`: materials that sample it while it renders form a feedback loop. Set the environment in the probe's first `onAfterRenderObservable`. Create it with mipmaps (fourth argument) and trilinear sampling, or rough surfaces reflect it as blocks.
- Shadow lookups outside a spot light's cone return garbage in blocks: let only the surfaces inside its cone receive its shadows.
- Load the largest textures by distance: a 2k KTX2 at start, the 4k when the viewer comes within reach (references/flat.md).
- A cabin needs baked light (see SKILL.md). In Babylon.js the glTF occlusion map becomes `ambientTexture`;
  set `material.ambientTextureImpactOnAnalyticalLights = 1` so it dims the sun and sky light too, not only
  the environment.
- A showroom for bare metal should be evenly lit (a bright, plain hall): steel then shows its own tone
  instead of one hot reflection.

## Coplanar faces

Two faces in the same plane, overlapping and facing the same way, flicker in a headset (z-fighting): its depth
precision is lower and the head never stops moving, so it can look clean on a desktop. Room boxes whose floor
sits on the floor mesh, a wall opening cut to the inside of the case set into it, trim pieces that overlap at a
corner. Build assembled pieces to meet, not overlap, and check: for every pair of meshes, compare their faces'
planes (axis-aligned bounding boxes are enough for boxes and planes) and report the ones that share a plane,
overlap, and face the same way. Faces that touch while facing each other hide each other and are fine.

Sub-pixel bright detail flickers too: gilding's fine edges and punched marks, a 12 mm light strip seen from
3 m. Turn on specular anti-aliasing for shiny materials with fine normal detail (Babylon.js:
`material.enableSpecularAntiAliasing = true`), and make emissive strips and lamps a few pixels tall from where
people stand.

## Loading

- glTF is right-handed; Babylon.js is left-handed. Its loader adds a `__root__` node that mirrors z, so a
  node's own glTF rotation still turns it the right way. Parent the loaded root nodes under your own
  `TransformNode` and place that; don't touch `__root__`.
- Drive moving parts by setting the named node's rotation (the model's `.json` says the node, the axis and
  the rate). Keep the node's rest rotation and multiply onto it.
- A pressable part needs a pick target bigger than the real control (a 3 cm button wants a ~12 cm target
  for a controller ray) and a hover glow.

## Seating the viewer

Put the head at the seat's eye point (SAE J1100: the eye ellipse above the seating point), not at the eye
minus the room height the headset reports: before the headset has reported a height, that put people in the
floor. After someone sits down or stands up in the room, move the view back to the eye once it settles.

## Mounting on a controller

WebXR's grip space, as Babylon.js exposes it: fingers along +z, thumb along +y. So the back of the left
hand faces -x and the back of the right hand +x. A wrist instrument whose face is the GLB's +y goes on the
back of the left hand with the mount's rotation taking +y to -x.

## Build tooling

- `vite build --watch` ignores `public/`: after copying a new GLB into `public/models/`, touch a source file
  so the watcher rebuilds, and check the served file's size.
- Stream the page's log (fps, presses, errors) back to your machine while someone tests in the headset;
  start the logger before the XR session, or its own start-up wins and the page's state is never reported.
