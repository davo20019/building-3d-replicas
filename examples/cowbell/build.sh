#!/bin/sh
# Build the cowbell end to end: CAD parts, Blender assembly, then compression (keeping the node tree).
#   examples/cowbell/build.sh        (first time: see the README's setup)
set -e
cd "$(dirname "$0")"
"${PY:-../../.venv/bin/python}" cad.py
blender -b --factory-startup --python assemble.py 2>&1 | grep -E 'Error|assemble:'
npx -y @gltf-transform/cli@4.5.1 optimize out/cowbell.glb out/cowbell.glb \
  --compress meshopt --texture-compress webp --texture-size 1024 --simplify false \
  --flatten false --join false --instance false   # keep the clapper's node (optimize flattens and joins by default)
ls -l out/cowbell.glb
