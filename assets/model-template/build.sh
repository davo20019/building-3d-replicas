#!/bin/sh
# Build the model end to end: CAD parts, Blender assembly, then compression (keeping the node tree).
#   <model>/build.sh   (SKILL=<where the skill is> if not in ~/.claude/skills)
set -e
cd "$(dirname "$0")"
SKILL="${SKILL:-$HOME/.claude/skills/build-3d-model}"     # where this skill is installed
"${PY:-$SKILL/.venv/bin/python}" cad.py
blender -b --factory-startup --python assemble.py 2>&1 | grep -E 'Error|assemble:'
npx -y @gltf-transform/cli@4.5.1 optimize out/model.glb out/model.glb \
  --compress meshopt --texture-compress webp --texture-size 1024 --simplify false \
  --flatten false --join false --instance false --palette false   # keep moving nodes (optimize flattens and joins by default)
ls -l out/model.glb
