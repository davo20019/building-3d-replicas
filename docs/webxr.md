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
- Light a cabin from inside too; a sky light through glass leaves it flat and even.

## Loading

- glTF is right-handed; Babylon.js is left-handed. Its loader adds a `__root__` node that mirrors z, so a
  node's own glTF rotation still turns it the right way. Parent the loaded root nodes under your own
  `TransformNode` and place that; don't touch `__root__`.
- Drive moving parts by setting the named node's rotation (the model's `.json` says the node, the axis and
  the rate). Keep the node's rest rotation and multiply onto it.
- A pressable part needs a pick target bigger than the real control (a 3 cm button wants a ~12 cm target
  for a controller ray) and a hover glow.

## Mounting on a controller

WebXR's grip space, as Babylon.js exposes it: fingers along +z, thumb along +y. So the back of the left
hand faces -x and the back of the right hand +x. A wrist instrument whose face is the GLB's +y goes on the
back of the left hand with the mount's rotation taking +y to -x.

## Build tooling

- `vite build --watch` ignores `public/`: after copying a new GLB into `public/models/`, touch a source file
  so the watcher rebuilds, and check the served file's size.
- Stream the page's log (fps, presses, errors) back to your machine while someone tests in the headset;
  start the logger before the XR session, or its own start-up wins and the page's state is never reported.
