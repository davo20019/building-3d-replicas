#!/bin/sh
# Download the cowbell's references from the Smithsonian's Open Access (CC0, see refs/SOURCES.md),
# then render the scan through the truth cameras in refs/scan/views.json.
set -e
cd "$(dirname "$0")"
mkdir -p refs/scan
[ -s refs/nmah-2018_0174_01.jpg ] || curl -fsSL -o refs/nmah-2018_0174_01.jpg \
  "https://ids.si.edu/ids/deliveryService?id=NMAH-JN2020-00328&max=4000"
[ -s refs/scan/nmah-2018_0174_01-cowbell-150k.glb ] || curl -fsSL -o refs/scan/nmah-2018_0174_01-cowbell-150k.glb \
  "https://3d-api.si.edu/content/document/3d_package:80c485f9-c7db-4d46-aa1c-a57565cd7baf/resources/nmah-2018_0174_01-cowbell-150k-4096_std.glb"
[ -s refs/scan/scan_low.png ] || blender -b --factory-startup --python refs/scan_views.py -- \
  refs/scan/nmah-2018_0174_01-cowbell-150k.glb refs/scan/views.json refs/scan 2>&1 | grep -E 'Error|scan_views:'
