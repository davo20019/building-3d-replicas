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
- A cabin needs baked light (see SKILL.md). In Babylon.js the glTF occlusion map becomes `ambientTexture`;
  set `material.ambientTextureImpactOnAnalyticalLights = 1` so it dims the sun and sky light too, not only
  the environment.
- A showroom for bare metal should be evenly lit (a bright, plain hall): steel then shows its own tone
  instead of one hot reflection.

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
