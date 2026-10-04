"""Measure points in a photo in millimetres, from reference points whose positions are known.
  .venv/bin/python scripts/measure.py <job.json>

For what a silhouette can't constrain (an interior, a handle, a seam, a light's height): pick a photo that
shows the feature, mark at least six points whose 3D positions are known (published sizes, parts already
fitted, a part of known size such as a screen), and mark the points to measure, each on a known plane.

job.json:
  photo       path, relative to the job file
  refs        {name: {"px": [x, y], "mm": [x, y, z]}}, at least 6, not all on one line; spread them out
  camera      instead of refs: a camera.json from fit_silhouette.py (relative to the job file). Its ride
              offset is undone, so heights come out at the model's spec height, not the photo's
  ride        optional: the body's offset in this photo (mm), when measured better than the fit's: query the
              roof peak with "body": false and subtract the spec height
  queries     {name: {"px": [x, y], "plane": {"x"|"y"|"z": value} or {"point": [..], "normal": [..]}}}
              with a fitted camera, add "body": false for points that don't ride on the body (wheels, ground)
  distances   optional [[query a, query b], ...]
  focal       optional fixed focal length in px; otherwise solved with the camera (then 4 references do,
              e.g. the corners of a screen of known size)
  expect      optional {query: {"x"|"y"|"z": value, "tol": mm}}: prints PASS or FAIL and exits 1 on a FAIL,
              so a job with known answers is a regression test for this script

Writes <job>.md (camera, every reference's reprojection error in px and mm, the measured points) and
<job>.png (green: where you marked each reference, red: where the solved camera puts it, blue: queries).
Trust a measurement only when the references reproject within a few px: a large error means a misread
pixel, a wrong 3D position, or a lens with strong distortion (use frames from a long lens).
"""
import json, sys
from pathlib import Path
import cv2, numpy as np
from scipy.optimize import minimize_scalar

job_path = Path(sys.argv[1]).resolve()
job = json.loads(job_path.read_text())
img = cv2.imread(str(job_path.parent / job['photo']))
H, W = img.shape[:2]
fitcam = json.loads((job_path.parent / job['camera']).read_text()) if 'camera' in job else None
names = list(job.get('refs', {}))
obj = np.array([job['refs'][n]['mm'] for n in names], float).reshape(-1, 3)
pix = np.array([job['refs'][n]['px'] for n in names], float).reshape(-1, 2)
if not fitcam and len(names) < (4 if 'focal' in job else 6):
    sys.exit('measure: need at least 6 reference points (4 with a fixed focal length), or a camera')

def solve(f):
    K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
    ok, rvec, tvec = cv2.solvePnP(obj, pix, K, None, flags=cv2.SOLVEPNP_SQPNP)
    if not ok:
        return 1e9, None
    ok, rvec, tvec = cv2.solvePnP(obj, pix, K, None, rvec, tvec, useExtrinsicGuess=True, flags=cv2.SOLVEPNP_ITERATIVE)
    proj = cv2.projectPoints(obj, rvec, tvec, K, None)[0].reshape(-1, 2)
    return float(np.sqrt(np.mean(np.sum((proj - pix) ** 2, axis=1)))), (K, rvec, tvec, proj)

ride = 0.0
if fitcam:
    # fit_silhouette.py's pinhole: camera on its +z at distanceMm from centreMm, image y down, principal point given.
    f = fitcam['focalPx']
    Rf = np.array(fitcam['rotation'])
    cx, cy = fitcam['principalPx']
    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]])
    flip = np.diag([1.0, -1.0, -1.0])           # its camera looks down its -z with y up; OpenCV's down +z with y down
    R = flip @ Rf
    cam = np.array(fitcam['centreMm']) + Rf.T @ np.array([0, 0, fitcam['distanceMm']])
    ride = job.get('ride', fitcam.get('rideOffsetMm', 0.0))   # override with one measured in this photo (the roof peak)
    rms, proj = 0.0, np.zeros((0, 2))
else:
    if 'focal' in job:
        f = float(job['focal'])
    else:                                    # coarse scan, then refine: the focal length is part of the camera
        scan = [(solve(f)[0], f) for f in np.geomspace(0.3 * max(W, H), 6 * max(W, H), 60)]
        f0 = min(scan)[1]
        f = minimize_scalar(lambda f: solve(f)[0], bounds=(f0 / 1.15, f0 * 1.15), method='bounded').x
    rms, (K, rvec, tvec, proj) = solve(f)
    R = cv2.Rodrigues(rvec)[0]
    cam = (-R.T @ tvec).ravel()              # camera position, model frame (mm)

def ray(px):
    d = R.T @ np.linalg.solve(K, [px[0], px[1], 1.0])
    return d / np.linalg.norm(d)

def on_plane(px, plane, body=True):
    """The point where the pixel's ray meets the plane (given at the model's spec height), at spec height."""
    lift = np.array([0, ride if body else 0.0, 0])   # the photo's body sits `ride` lower (or higher) on its wheels
    if 'normal' in plane:
        p0, n = np.array(plane['point'], float), np.array(plane['normal'], float)
    else:
        axis = next(k for k in 'xyz' if k in plane)
        n = np.eye(3)['xyz'.index(axis)]
        p0 = n * plane[axis]
    d = ray(px)
    t = np.dot(p0 + lift - cam, n) / np.dot(d, n)
    return cam + t * d - lift

def mm_per_px(p):
    return np.linalg.norm(p - cam) / f

lines = [f'# Measured in {job["photo"]}', '',
         f'Camera at {np.round(cam).tolist()} mm, focal {f:.0f} px ({f / max(W, H):.2f} x the long side). '
         + (f'From {job["camera"]} (ride offset {ride:.0f} mm undone).' if fitcam else f'Reprojection error {rms:.2f} px RMS over {len(names)} references.'), '',
         '| Reference | Marked px | Reprojected px | Error px | Error mm |', '|---|---|---|---|---|']
for n, p, q, o in zip(names, pix, proj, obj):
    e = np.linalg.norm(p - q)
    lines.append(f'| {n} | {np.round(p).astype(int).tolist()} | {np.round(q).astype(int).tolist()} | {e:.1f} | {e * mm_per_px(o):.0f} |')
results = {}
if job.get('queries'):
    lines += ['', '| Query | px | Point (mm) | mm per px there |', '|---|---|---|---|']
    for n, qd in job['queries'].items():
        pt = on_plane(qd['px'], qd['plane'], qd.get('body', True))
        results[n] = pt
        lines.append(f'| {n} | {qd["px"]} | {np.round(pt, 1).tolist()} | {mm_per_px(pt):.2f} |')
for a, b in job.get('distances', []):
    lines.append(f'\nDistance {a} to {b}: {np.linalg.norm(results[a] - results[b]):.1f} mm')
failed = False
for n, e in job.get('expect', {}).items():
    for axis in 'xyz':
        if axis in e:
            got = results[n]['xyz'.index(axis)]
            ok = abs(got - e[axis]) <= e['tol']
            failed |= not ok
            lines.append(f'\nExpect {n} {axis} = {e[axis]} ± {e["tol"]}: got {got:.1f}, {"PASS" if ok else "FAIL"}')
out = job_path.with_suffix('')
out.with_suffix('.md').write_text('\n'.join(lines) + '\n')
# The solved camera, for rendering the model through it (scripts/render_cams.py): OpenCV convention,
# x_cam = R (X - centre), image x right, y down; principal point at the image centre unless from a fit.
(out.parent / (out.name + '.camera.json')).write_text(json.dumps({
    'size': [W, H], 'focalPx': float(f), 'principalPx': [float(K[0, 2]), float(K[1, 2])],
    'R': np.asarray(R).tolist(), 'centreMm': np.asarray(cam).ravel().tolist(), 'rmsPx': float(rms)}, indent=1))
over = img.copy()
r = max(4, max(W, H) // 300)
for p, q in zip(pix, proj):
    cv2.circle(over, tuple(np.round(p).astype(int)), r * 2, (0, 255, 0), max(1, r // 2))
    cv2.circle(over, tuple(np.round(q).astype(int)), r, (0, 0, 255), -1)
for n, qd in (job.get('queries') or {}).items():
    cv2.circle(over, tuple(np.round(qd['px']).astype(int)), r, (255, 80, 0), -1)
    cv2.putText(over, n, (int(qd['px'][0]) + 2 * r, int(qd['px'][1])), cv2.FONT_HERSHEY_SIMPLEX, r / 5, (255, 80, 0), max(1, r // 3))
cv2.imwrite(str(out.with_suffix('.png')), over)
print('\n'.join(lines))
sys.exit(1 if failed else 0)
