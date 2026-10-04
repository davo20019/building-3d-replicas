"""Fit a model's uncertain shape parameters to reference photos by silhouette, solving each photo's camera too.
  .venv/bin/python scripts/fit_silhouette.py <model>

Reads the "fit" block of <model>/review.json. Two forms:

Single photo (a small object seen from the front):
  photo      reference photo, relative to the model folder
  solid      name of the function in <model>/cad.py that builds the part to fit from a params dict
  hsv        [[h, s, v], [h, s, v]] OpenCV HSV range that cuts the part out of the photo
  params     {name: [min, max]}: only parameters this photo can see; the rest stay as they are
  landmark   optional {"point": [x, y, z] mm, "hsv": [...]}: an inner feature cut out by colour; its position
             inside the outline tells a symmetric part's tilt (outlines look the same tilted up or down)

Several photos fitted together (shared shape parameters, one camera per photo):
  solid, params as above; landmarks: name of a function in cad.py returning {name: [x, y, z] mm} for a
  params dict; iouWeightMm: how many mm of outline error a whole IoU point is worth (default 10);
  landmarkWeight: multiplies the landmark error (default 1; raise it when the first cut-out is rough, so
  measured points hold the camera while the outline is still wrong);
  rideOffset: {"fixed": [name prefixes], "range": [lo, hi]}: a per-photo vertical offset (mm) of every part
  and landmark not named in fixed, solved with that photo's camera (air suspension: a parked truck sits
  lower than its spec height); cameraHeightMm: [lo, hi] above y = 0, a penalty keeps each camera there
  (silhouettes alone trade tilt for distance and can put the camera under the ground);
  tessellation: [tolerance, angular] for the fit's meshes; centreMm: fixed point the cameras look at;
  photos: list of
    name, photo
    view       [pitch, yaw, roll] degrees to start from: yaw -90 shows the model's +x side, 90 its -x side
    search     {"pitch": [lo, hi, step], "yaw": [lo, hi, step]} grid tried before refining (default: around view)
    mask       {"method": "hsv", "hsv": ...}
               {"method": "grabcut", "rect": [x0, y0, x1, y1], "ground": [[x, y], [x, y]], "refine": true}
               {"method": "file", "path": ...}
               grabcut cuts the part out by colour statistics and edges, seeded by the rectangle; everything
               below the ground line (through the tyres' contact points) is background. With "refine", it is
               run again seeded by the model's own silhouette through the solved camera, inside a band of
               bandFrac x the part's size: for parts that don't separate by colour (bare steel, silver, black).
               "exclude": [[[x, y], ...], ...] polygons that are sure background for grabcut: a drop shadow, a
               car parked beside it, a sign in front. A few marked pixels also teach grabcut their colour.
    landmarks  {landmark name: [x, y] px in the photo}: measured inner points (wheel centres, light bar)
    focalPx    optional focal length in px, when known: from EXIF, focal_mm / sensor_width_mm x image width px.
               Silhouettes alone trade tilt for perspective (a steep view from far looks like a shallow one
               from near); a known focal length removes most of that
    parts      (with a parts solid) which entry of cad.<viewDark> lists the dark parts this photo sees
    dark       {"valueMax": v} or {"method": "otsu"}: the dark parts (cladding, tyres, glass) cut out inside
               the part by brightness; compared with the model's dark parts, weighted by darkWeightMm.
               {"satMax": s, "valueMax": v}: by saturation instead, for a coloured object's neutral parts
               (a black grip on red paint, where the paint's shade is as dark as the grip)

Parts solid: `solid` may return a dict {name: shape} instead of one shape. The outline is then all parts
together, and with viewDark (name of a dict in cad.py, {view: [part names]}) the fit also matches where the
dark parts sit inside the outline: steel is painted first, then that view's dark parts on top. That is how
it sees features the outline can't, such as wheel arches, windows and bumper heights.

Writes <model>/params.json (merged) and, per photo, camera.json, target.png (the cut-out), overlay.png
(magenta: model only, cyan: photo only) and report.md: in fit/ for the single form, fit/<name>/ for the list.

Frame: the CAD is in mm with its front facing +z and up +y. Each camera is a pinhole looking at the centre.
"""
import importlib, json, sys
from pathlib import Path
import cv2, numpy as np
from scipy.optimize import minimize

model = Path(sys.argv[1]).resolve()
CFG = json.loads((model / 'review.json').read_text())['fit']
sys.path.insert(0, str(model))
cad = importlib.import_module('cad')
build = getattr(cad, CFG['solid'])
KEYS, BOUNDS = list(CFG['params']), CFG['params']
LEGACY = 'photos' not in CFG
TESS = CFG.get('tessellation', [0.3, 0.5])
IOU_W = CFG.get('iouWeightMm', 10.0)
lm_fn = getattr(cad, CFG['landmarks']) if 'landmarks' in CFG else None
VIEW_DARK = getattr(cad, CFG['viewDark']) if 'viewDark' in CFG else {}
DARK_W = CFG.get('darkWeightMm', 0.0)
LM_W = CFG.get('landmarkWeight', 1.0)
# Per-photo ride height: a vertical offset of everything but the named fixed parts (the wheels), solved with
# each photo's camera. Vehicles on air suspension sit at different heights in different photos.
RIDE = CFG.get('rideOffset')
CAM_H = CFG.get('cameraHeightMm')                                  # [lo, hi]: where a photographer can stand

def moves(name):
    return RIDE is not None and not any(name.startswith(f) for f in RIDE['fixed'])

def rotation(cam):
    """Camera rotation from [pitch, yaw, roll] degrees: yaw turns the model about its up, then pitch tilts it."""
    rx, ry, rz = np.radians(cam[:3])
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
    return Rz @ Rx @ Ry

def fill_holes(m):
    """Holes are background regions that touch no border. Flood from a 1 px frame round the image: a part
    that spans the photo's width would otherwise turn the ground below it into a "hole". The cut-outs and
    the model's renders are both filled, so a see-through gap (inside a loop, between spokes) counts the
    same on both sides: filling only the photo's made the fit raise cameras until the model's gaps closed."""
    m = (m > 0).astype(np.uint8)
    outside = np.pad(m, 1); h, w = outside.shape
    cv2.floodFill(outside, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
    return m | (1 - outside[1:-1, 1:-1])

class Photo:
    def __init__(self, c):
        self.c = c
        self.name = c.get('name', 'main')
        self.img = cv2.imread(str(model / c['photo']))
        H, W = self.img.shape[:2]
        self.S = min(1.0, CFG.get('workPx', 1200) / max(H, W)) if not LEGACY else 0.5
        self.small = cv2.resize(self.img, None, fx=self.S, fy=self.S, interpolation=cv2.INTER_AREA)
        self.out = model / 'fit' if LEGACY else model / 'fit' / self.name
        self.out.mkdir(parents=True, exist_ok=True)
        self.marks = {k: np.array(v, float) * self.S for k, v in c.get('landmarks', {}).items()}
        self.focal = c['focalPx'] * self.S if 'focalPx' in c else None
        self.mark = None                                   # legacy colour landmark (relative to the outlines)
        self.mask_cfg = c.get('mask', {'method': 'hsv', 'hsv': c.get('hsv')})
        self.dark_names = VIEW_DARK.get(c.get('parts'), [])
        self.ground = self.below_ground()
        self.set_target(self.cut_out())

    def set_target(self, m):
        """The part's cut-out, and inside it the dark parts by brightness (if the photo asks for them)."""
        self.target = m
        self.dark = None
        dc = self.c.get('dark')
        if dc and self.dark_names:
            g = cv2.cvtColor(self.small, cv2.COLOR_BGR2GRAY)
            inside = m.astype(bool)
            if 'satMax' in dc:                                     # neutral parts of a coloured object (black grip, red paint)
                sat = cv2.cvtColor(self.small, cv2.COLOR_BGR2HSV)[..., 1]
                d = (sat < dc['satMax']) & (g < dc.get('valueMax', 256)) & inside
            else:
                thr = dc['valueMax'] if 'valueMax' in dc else cv2.threshold(g[inside].reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0]
                d = (g < thr) & inside
            d = d.astype(np.uint8)
            d = cv2.morphologyEx(d, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            self.dark = cv2.morphologyEx(d, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    def largest_filled(self, m):
        _, lab, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
        m = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
        return fill_holes(m)

    def below_ground(self):
        g = self.mask_cfg.get('ground')
        h, w = self.small.shape[:2]
        if not g:
            return np.zeros((h, w), bool)
        (x0, y0), (x1, y1) = np.array(g, float) * self.S
        xs = np.arange(w)
        yline = y0 + (y1 - y0) * (xs - x0) / (x1 - x0)
        return np.arange(h)[:, None] > yline[None, :]

    def cut_out(self, prior=None):
        mc = self.mask_cfg
        if mc['method'] == 'file':
            m = cv2.imread(str(model / mc['path']), 0)
            return (cv2.resize(m, (self.small.shape[1], self.small.shape[0]), interpolation=cv2.INTER_NEAREST) > 127).astype(np.uint8)
        if mc['method'] == 'hsv':
            img = self.img
            lo, hi = mc['hsv']
            m = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), tuple(lo), tuple(hi))
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
            m = self.largest_filled(m > 0)
            if 'landmark' in self.c:                       # centre of the landmark's colour region, inside the part
                lo, hi = self.c['landmark']['hsv']
                lmk = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), tuple(lo), tuple(hi)) & (m * 255)
                _, lab, stats, cents = cv2.connectedComponentsWithStats(lmk)
                self.mark = cents[1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])] * self.S
            return cv2.resize(m, (self.small.shape[1], self.small.shape[0]), interpolation=cv2.INTER_NEAREST)
        # grabcut
        h, w = self.small.shape[:2]
        gc = np.full((h, w), cv2.GC_BGD, np.uint8)
        if prior is None:
            x0, y0, x1, y1 = (np.array(mc['rect'], float) * self.S).astype(int)
            gc[y0:y1, x0:x1] = cv2.GC_PR_FGD
        else:
            b = max(3, int(mc.get('bandFrac', 0.025) * max(np.ptp(np.nonzero(prior)[1]), np.ptp(np.nonzero(prior)[0]))))
            k = np.ones((2 * b + 1, 2 * b + 1), np.uint8)
            sure = cv2.erode(prior, k).astype(bool)
            near = cv2.dilate(prior, k).astype(bool)
            gc[near] = cv2.GC_PR_BGD
            gc[prior.astype(bool)] = cv2.GC_PR_FGD
            gc[sure] = cv2.GC_FGD
        gc[self.below_ground()] = cv2.GC_BGD
        for poly in mc.get('exclude', []):                        # sure background: shadows, neighbours, props
            cv2.fillPoly(gc, [np.round(np.array(poly, float) * self.S).astype(np.int32)], cv2.GC_BGD)
        bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(self.small, gc, None, bgd, fgd, mc.get('iterations', 6), cv2.GC_INIT_WITH_MASK)
        m = np.isin(gc, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        return self.largest_filled(m)

_TESS_CACHE = {}

def mesh(p):
    """{part name: (vertices, triangles)} and the point the cameras look at."""
    shapes = build(p)
    shapes = shapes if isinstance(shapes, dict) else {'all': shapes}
    parts = {}
    for name, s in shapes.items():
        key = (name, tuple(np.round([c for v in s.vertices() for c in (v.X, v.Y, v.Z)], 3)))
        if key not in _TESS_CACHE:                                # most parameters move only some parts
            v, t = s.tessellate(*TESS)
            _TESS_CACHE[key] = (np.array([(q.X, q.Y, q.Z) for q in v]), np.array(t))
        parts[name] = _TESS_CACHE[key]
    allV = np.vstack([v for v, _ in parts.values()])
    centre = np.array(CFG['centreMm'], float) if 'centreMm' in CFG else (allV.min(0) + allV.max(0)) / 2
    return parts, centre

def project(V, centre, cam):
    cx, cy, s, dist = cam[3:7]
    P = (V - centre) @ rotation(cam).T
    z = max(dist, 1.0) - P[:, 2]                                  # camera on +z, looking at the front
    f = s * dist                                                  # s = px per mm at the centre
    return np.c_[cx + f * P[:, 0] / z, cy - f * P[:, 1] / z]

def ride(cam):
    return cam[7] if len(cam) > 7 else 0.0

def render(geo, cam, shape, dark=()):
    """Label image: 1 where the model is, 2 where one of the `dark` parts is painted over it."""
    parts, centre = geo
    m = np.zeros(shape, np.uint8)
    for names, label in ((list(parts), 1), (dark, 2)):
        for n in names:
            V, T = parts[n]
            if moves(n):
                V = V + [0, ride(cam), 0]
            pts = np.round(project(V, centre, cam)).astype(np.int32)
            for tri in pts[T]:                                    # each triangle: a union, no even-odd holes
                cv2.fillConvexPoly(m, tri, label)
    return m

def score(a, b, mm_per_px):
    iou = (a & b).sum() / max((a | b).sum(), 1)
    ea, eb = cv2.Canny(a * 255, 50, 150) > 0, cv2.Canny(b * 255, 50, 150) > 0
    if not ea.any() or not eb.any():
        return iou, 1e4
    da = cv2.distanceTransform((~eb).astype(np.uint8), cv2.DIST_L2, 3)
    db = cv2.distanceTransform((~ea).astype(np.uint8), cv2.DIST_L2, 3)
    return iou, (da[ea].mean() + db[eb].mean()) / 2 * mm_per_px

def landmark_error(ph, geo, cam, lms, m=None):
    if ph.mark is not None:                                       # legacy: relative to the outlines' centres
        pt = project(np.array([ph.c['landmark']['point']]), geo[1], cam)[0]
        m = (render(geo, cam, ph.target.shape) if m is None else m) > 0
        ym, xm = np.nonzero(m); yt, xt = np.nonzero(ph.target)
        return float(np.hypot(*((pt - [xm.mean(), ym.mean()]) - (ph.mark - [xt.mean(), yt.mean()])))) / cam[5]
    if not ph.marks:
        return 0.0
    names = list(ph.marks)
    pts = project(np.array([np.add(lms[n], [0, ride(cam) if moves(n) else 0, 0]) for n in names]), geo[1], cam)
    return float(np.mean([np.hypot(*(pts[i] - ph.marks[n])) for i, n in enumerate(names)])) / cam[5]

def dark_iou(ph, lab):
    if ph.dark is None:
        return 1.0
    a, b = lab == 2, ph.dark.astype(bool)
    return (a & b).sum() / max((a | b).sum(), 1)

def render_photo(ph, geo, cam):
    """The model as this photo's cut-out sees it: below the ground line counts as ground, as in the photo
    (tyres flatten where they meet the ground, a round model tyre doesn't)."""
    lab = render(geo, cam, ph.target.shape, ph.dark_names if ph.dark is not None else ())
    lab[ph.ground] = 0
    if ph.mask_cfg['method'] != 'file':                           # the cut-out's holes are filled: fill the model's
        lab[(fill_holes(lab) == 1) & (lab == 0)] = 1
    return lab

def with_focal(ph, cam):
    """A known focal length (EXIF) fixes the distance for each scale: f = s * distance."""
    cam = np.array(cam, float)
    if ph.focal:
        cam[6] = ph.focal / cam[5]
    return cam

def loss_cam(ph, geo, cam, lms):
    cam = with_focal(ph, cam)
    lab = render_photo(ph, geo, cam)
    m = (lab > 0).astype(np.uint8)
    iou, edge = score(m, ph.target, 1 / cam[5])
    l = edge + IOU_W * (1 - iou) + DARK_W * (1 - dark_iou(ph, lab)) + LM_W * landmark_error(ph, geo, cam, lms, m)
    if CAM_H:
        h = camera_position(geo, cam)[1]
        l += CFG.get('cameraHeightWeight', 0.5) * (max(CAM_H[0] - h, 0) + max(h - CAM_H[1], 0))
    if RIDE:
        lo, hi = RIDE['range']
        l += 10 * (max(lo - ride(cam), 0) + max(ride(cam) - hi, 0))
    return l

def camera_position(geo, cam):
    """Where the camera stands, in the model frame (mm)."""
    return geo[1] + rotation(cam).T @ np.array([0, 0, cam[6]])

def refine(ph, geo, cam, lms, n=1500):
    """Powell over the camera in steps of comparable effect (a degree, a few pixels, a percent of scale and
    distance): its line searches start at unit steps, which unscaled would be a 5x zoom or nothing at all."""
    cam = np.asarray(cam, float)
    step = np.array([1, 1, 1, 2, 2, 0.01 * cam[5], 0.05 * cam[6], 5][:len(cam)])
    def f(u):
        c = cam + u * step
        if c[5] <= 0 or c[6] <= 0:
            return 1e9
        return loss_cam(ph, geo, c, lms)
    u = minimize(f, np.zeros(len(cam)), method='Powell', options={'xtol': 1e-2, 'ftol': 1e-4, 'maxfev': n}).x
    return with_focal(ph, cam + u * step)

def align_box(ph, geo, cam):
    """Scale and shift the camera so the model's outline has the cut-out's bounding box. A heavy end moves
    the cut-out's centroid away from the model's centre, and a tilt search from a shifted start picks the
    tilt that hides the shift."""
    cam = with_focal(ph, cam)
    ys, xs = np.nonzero(ph.target)
    for _ in range(2):
        m = render_photo(ph, geo, cam) > 0
        if not m.any():
            return cam
        my, mx = np.nonzero(m)
        k = np.ptp(ys) / max(np.ptp(my), 1) if np.ptp(ys) >= np.ptp(xs) else np.ptp(xs) / max(np.ptp(mx), 1)
        cam[5] *= k
        cam = with_focal(ph, cam)
        my, mx = np.nonzero(render_photo(ph, geo, cam) > 0)
        cam[3] += (xs.min() + xs.max() - mx.min() - mx.max()) / 2
        cam[4] += (ys.min() + ys.max() - my.min() - my.max()) / 2
    return cam

def search(ph, geo, cam, lms):
    view = ph.c.get('view', [0, 0, 0])
    if LEGACY:
        grid = [(rx, ry) for rx in range(-35, 36, 5) for ry in (-10, 0, 10)]
    else:
        sp = ph.c.get('search', {})
        pr = sp.get('pitch', [view[0] - 10, view[0] + 20, 5]); yr = sp.get('yaw', [view[1] - 15, view[1] + 15, 5])
        grid = [(a, b) for a in np.arange(pr[0], pr[1] + 1e-6, pr[2]) for b in np.arange(yr[0], yr[1] + 1e-6, yr[2])]
    starts = [align_box(ph, geo, np.r_[a, b, cam[2:]]) for a, b in grid]
    best = min(starts, key=lambda c: loss_cam(ph, geo, c, lms))
    return refine(ph, geo, best, lms)

def initial_cam(ph, geo):
    ys, xs = np.nonzero(ph.target)
    view = ph.c.get('view', [0, 0, 0])
    parts, centre = geo
    V = np.vstack([v for v, _ in parts.values()])
    span = np.ptp((V - centre) @ rotation(np.r_[view, 0, 0, 1, 1]).T, axis=0)
    dist = ph.c.get('distanceMm', 300.0 if LEGACY else 2.5 * np.ptp(V, axis=0).max())
    cam = [*view, xs.mean(), ys.mean(), (xs.max() - xs.min()) / span[0], dist]
    return with_focal(ph, cam + ([0.0] if RIDE else []))

photos = [Photo(CFG)] if LEGACY else [Photo(c) for c in CFG['photos']]
for ph in photos:
    cv2.imwrite(str(ph.out / 'target_initial.png'), ph.target * 255)
p = dict(cad.P)
geo = mesh(p)
lms = lm_fn(p) if lm_fn else {}
cams = {}
for ph in photos:
    cams[ph.name] = search(ph, geo, initial_cam(ph, geo), lms)
    if ph.mask_cfg.get('refine'):                                 # cut out again, seeded by the model's outline
        for _ in range(ph.mask_cfg.get('refineRounds', 2)):
            ph.set_target(ph.cut_out(prior=(render_photo(ph, geo, cams[ph.name]) > 0).astype(np.uint8)))
            cams[ph.name] = refine(ph, geo, cams[ph.name], lms)
    cv2.imwrite(str(ph.out / 'target.png'), ph.target * 255)
    if ph.dark is not None:
        cv2.imwrite(str(ph.out / 'target_dark.png'), ph.dark * 255)

def report_line(ph, cam):
    lab = render_photo(ph, geo, cam)
    iou, edge = score((lab > 0).astype(np.uint8), ph.target, 1 / cam[5])
    return iou, edge, landmark_error(ph, geo, cam, lms), dark_iou(ph, lab)

before = {ph.name: report_line(ph, cams[ph.name]) for ph in photos}
for ph in photos:
    b = before[ph.name]
    print(f'{ph.name} before: IoU {b[0]:.4f}, outline error {b[1]:.3f} mm, landmark error {b[2]:.3f} mm, dark IoU {b[3]:.4f}', flush=True)

def total(x, n_cam=80, fixed_cams=False):
    global geo, lms
    q = dict(p, **{k: float(np.clip(v, *BOUNDS[k])) for k, v in zip(KEYS, x)})
    try:
        geo = mesh(q)
    except Exception:
        return 1e6                                                # the CAD kernel refused these values
    lms = lm_fn(q) if lm_fn else {}
    l = 0.0
    for ph in photos:
        if not fixed_cams:
            cams[ph.name] = refine(ph, geo, cams[ph.name], lms, n_cam)
        l += loss_cam(ph, geo, cams[ph.name], lms)
    return l

x0 = [p[k] for k in KEYS]
if not KEYS:                                                      # cut-outs and cameras only
    res = type('R', (), {'x': []})()
elif LEGACY:
    res = minimize(total, x0, method='Nelder-Mead', options={'maxfev': 50, 'xatol': 0.1, 'fatol': 1e-3})
else:
    # Alternate: the shape with every camera held still (each step is one CAD build and a render per photo),
    # then every camera with the shape held still. Re-solving three cameras inside every shape step is ~10x
    # slower, since Powell finishes whole line searches past its evaluation limit.
    x = np.array(x0, float)
    for rnd in range(CFG.get('rounds', 3)):
        res = minimize(lambda v: total(v, fixed_cams=True), x, method='Powell', bounds=[BOUNDS[k] for k in KEYS],
                       options={'maxfev': CFG.get('maxShapeEvals', 300), 'xtol': 1.0, 'ftol': 1e-4})
        x = res.x
        total(x, fixed_cams=True)
        for ph in photos:
            cams[ph.name] = refine(ph, geo, cams[ph.name], lms)
        print(f'round {rnd + 1}: loss {total(x, fixed_cams=True):.2f}  {dict(zip(KEYS, np.round(x, 1).tolist()))}', flush=True)
    res.x = x
best = dict(p, **{k: round(float(np.clip(v, *BOUNDS[k])), 2) for k, v in zip(KEYS, res.x)})
geo = mesh(best)
lms = lm_fn(best) if lm_fn else {}
for ph in photos:
    cams[ph.name] = search(ph, geo, cams[ph.name], lms)

old = json.loads((model / 'params.json').read_text()) if (model / 'params.json').exists() else {}
(model / 'params.json').write_text(json.dumps(dict(old, **{k: best[k] for k in KEYS}), indent=2) + '\n')

rows = []
for ph in photos:
    cam = cams[ph.name]
    lab = render_photo(ph, geo, cam)
    fit = (lab > 0).astype(np.uint8)
    iou, edge, lme, diou = report_line(ph, cam)
    H, W = ph.img.shape[:2]
    (ph.out / 'camera.json').write_text(json.dumps({              # full-resolution pinhole, for review.py
        'name': ph.name, 'photo': ph.c['photo'], 'width': W, 'height': H, 'rotation': rotation(cam).tolist(),
        'centreMm': geo[1].tolist(), 'distanceMm': cam[6], 'focalPx': cam[5] * cam[6] / ph.S,
        'principalPx': [cam[3] / ph.S, cam[4] / ph.S], 'iou': round(iou, 4), 'outlineErrorMm': round(edge, 3),
        'landmarkErrorMm': round(lme, 3), 'darkIou': round(diou, 4), 'pitchYawRollDeg': np.round(cam[:3], 2).tolist(),
        'rideOffsetMm': round(float(ride(cam)), 1), 'cameraPositionMm': np.round(camera_position(geo, cam)).tolist()}, indent=2))
    over = ph.small.copy()
    over[(fit == 1) & (ph.target == 0)] = (255, 0, 255)
    over[(fit == 0) & (ph.target == 1)] = (255, 255, 0)
    for n, xy in ph.marks.items():                                # measured landmark (green) and the model's (red)
        cv2.circle(over, tuple(np.round(xy).astype(int)), 6, (0, 255, 0), -1)
        cv2.circle(over, tuple(np.round(project(np.array([lms[n]]), geo[1], cam)[0]).astype(int)), 4, (0, 0, 255), -1)
    cv2.imwrite(str(ph.out / 'overlay.png'), over)
    if ph.dark is not None:                                       # dark parts: magenta model only, cyan photo only, white both
        dv = cv2.cvtColor(ph.small, cv2.COLOR_BGR2GRAY) // 3
        dv = cv2.cvtColor(dv, cv2.COLOR_GRAY2BGR)
        a, d = lab == 2, ph.dark.astype(bool)
        dv[a & ~d] = (255, 0, 255); dv[~a & d] = (255, 255, 0); dv[a & d] = (255, 255, 255)
        cv2.imwrite(str(ph.out / 'overlay_dark.png'), dv)
    b = before[ph.name]
    rows.append((ph, b, (iou, edge, lme, diou), cam))
    (ph.out / 'report.md').write_text(f"""# Silhouette fit, {ph.c['photo']}

| | IoU | Outline error (mm) | Landmark error (mm) |
|---|---|---|---|
| Before | {b[0]:.4f} | {b[1]:.3f} | {b[2]:.3f} |
| After | {iou:.4f} | {edge:.3f} | {lme:.3f} |

Dark parts IoU: before {b[3]:.4f}, after {diou:.4f}.

Camera (pitch, yaw, roll deg): {np.round(cam[:3], 2).tolist()}, distance {cam[6]:.0f} mm.
overlay.png: magenta = model only, cyan = photo only; green dot = measured landmark, red = the model's.
""")

table = '\n'.join(f'| {ph.name} | {b[0]:.4f} | {b[1]:.2f} | {a[0]:.4f} | {a[1]:.2f} | {a[2]:.2f} | {b[3]:.3f} -> {a[3]:.3f} | {np.round(cam[:3], 1).tolist()} | {cam[6]:.0f} | {camera_position(geo, cam)[1]:.0f} | {ride(cam):.0f} |'
                  for ph, b, a, cam in rows)
report = f"""# Silhouette fit

| Photo | IoU before | Outline before (mm) | IoU after | Outline after (mm) | Landmark (mm) | Dark IoU | Camera pitch/yaw/roll | Distance (mm) | Camera height (mm) | Ride offset (mm) |
|---|---|---|---|---|---|---|---|---|---|---|
{table}

Fitted: {json.dumps({k: best[k] for k in KEYS})}
"""
(model / 'fit' / 'report.md').write_text(report)
print(report)
