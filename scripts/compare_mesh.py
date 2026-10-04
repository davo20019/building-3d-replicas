"""Compare a built model with a reference mesh (a museum scan, a maker's CAD) by surface distance, in mm.
  python scripts/compare_mesh.py <job.json>

job.json (paths relative to it):
  model      list of STL files or globs (the CAD's parts, in mm, model frame), or a GLB
  reference  STL or GLB (glTF, y-up)
  referenceScale  multiplies the reference's units into mm (a GLB in metres: 1000; default 1)
  referenceOffsetMm  [x, y, z] added after scaling, into the model frame
  modelScale, modelOffsetMm  the same for the model (a GLB in metres: 1000)
  icp        true: also report the distances after a rigid alignment (rotation and translation, no scale),
             which separates a misplaced object from a misshapen one
  samples    points sampled on each surface (default 200000)
  expect     optional {"meanMm": max, "p95Mm": max}: exit 1 if the result is worse (a regression test)
Prints and writes <job>.result.json: mean, 95th percentile and max distance each way (model -> reference:
"extra" material; reference -> model: "missing" material), and both bounding boxes.

Distances are point-to-nearest-sample on densely sampled surfaces: accurate to about the sample spacing.
"""
import json, struct, sys
from glob import glob
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

def read_stl(path):
    b = Path(path).read_bytes()
    if b[:5] == b'solid' and b'facet' in b[:300]:
        v = [list(map(float, l.split()[1:4])) for l in b.decode().splitlines() if l.strip().startswith('vertex')]
        return np.array(v).reshape(-1, 3, 3)
    n = struct.unpack('<I', b[80:84])[0]
    a = np.frombuffer(b, dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]), count=n, offset=84)
    return a['v'].reshape(-1, 3, 3).astype(float)

def read_glb(path):
    """Triangles of every mesh in a GLB, with node transforms (no Draco or meshopt compression)."""
    b = Path(path).read_bytes()
    n = struct.unpack('<I', b[12:16])[0]
    g = json.loads(b[20:20 + n])
    bin_ = b[20 + n + 8:]
    def acc(i):
        a = g['accessors'][i]
        v = g['bufferViews'][a['bufferView']]
        dt = {5126: '<f4', 5125: '<u4', 5123: '<u2', 5121: 'u1'}[a['componentType']]
        k = {'SCALAR': 1, 'VEC3': 3, 'VEC2': 2, 'VEC4': 4}[a['type']]
        off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = v.get('byteStride', 0)
        if stride and stride != np.dtype(dt).itemsize * k:
            raw = np.frombuffer(bin_, 'u1', count=stride * a['count'], offset=off).reshape(-1, stride)
            return raw[:, :np.dtype(dt).itemsize * k].copy().view(dt).reshape(-1, k).astype(float)
        return np.frombuffer(bin_, dt, count=a['count'] * k, offset=off).reshape(-1, k).astype(float)
    def local(nd):
        if 'matrix' in nd:
            return np.array(nd['matrix']).reshape(4, 4).T
        x, y, z, w = nd.get('rotation', [0, 0, 0, 1])
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M = np.eye(4)
        M[:3, :3] = R * nd.get('scale', [1, 1, 1])
        M[:3, 3] = nd.get('translation', [0, 0, 0])
        return M
    tris = []
    def walk(i, parent):
        nd = g['nodes'][i]
        M = parent @ local(nd)
        if 'mesh' in nd:
            for pr in g['meshes'][nd['mesh']]['primitives']:
                if 'extensions' in pr and 'KHR_draco_mesh_compression' in pr['extensions']:
                    sys.exit(f'{path}: Draco-compressed; use an uncompressed GLB or the OBJ')
                P = acc(pr['attributes']['POSITION'])
                P = P @ M[:3, :3].T + M[:3, 3]
                I = acc(pr['indices']).astype(int).ravel() if 'indices' in pr else np.arange(len(P))
                tris.append(P[I].reshape(-1, 3, 3))
        for c in nd.get('children', []):
            walk(c, M)
    for r in g['scenes'][g.get('scene', 0)]['nodes']:
        walk(r, np.eye(4))
    return np.vstack(tris)

def load(spec, base, scale, offset):
    files = spec if isinstance(spec, list) else [spec]
    paths = [p for f in files for p in sorted(glob(str(base / f)))]
    if not paths:
        sys.exit(f'nothing matches {spec}')
    T = np.vstack([read_glb(p) if p.endswith('.glb') else read_stl(p) for p in paths])
    return T * scale + np.array(offset, float)

def sample(T, n, rng):
    a = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    i = rng.choice(len(T), n, p=a / a.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    t = T[i]
    return t[:, 0] + u[:, None] * (t[:, 1] - t[:, 0]) + v[:, None] * (t[:, 2] - t[:, 0])

def stats(d):
    return {'meanMm': round(float(d.mean()), 2), 'p95Mm': round(float(np.percentile(d, 95)), 2), 'maxMm': round(float(d.max()), 2)}

def distances(A, B):
    return cKDTree(B).query(A)[0], cKDTree(A).query(B)[0]

def icp(A, B, iters=40):
    """Rigid transform moving A onto B (point-to-point ICP, Kabsch)."""
    tree = cKDTree(B)
    R, t = np.eye(3), np.zeros(3)
    for _ in range(iters):
        X = A @ R.T + t
        Y = B[tree.query(X)[1]]
        mx, my = X.mean(0), Y.mean(0)
        U, _, Vt = np.linalg.svd((X - mx).T @ (Y - my))
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
        dR = Vt.T @ D @ U.T
        R, t = dR @ R, dR @ (t - mx) + my
    return R, t

if len(sys.argv) != 2:
    sys.exit('usage: compare_mesh.py <job.json>')
job_path = Path(sys.argv[1]).resolve()
job = json.loads(job_path.read_text())
for k in ('model', 'reference'):
    if k not in job:
        sys.exit(f'compare_mesh.py: {job_path.name} needs "{k}" (see the docstring)')
base = job_path.parent
rng = np.random.default_rng(0)
n = job.get('samples', 200000)
M = load(job['model'], base, job.get('modelScale', 1), job.get('modelOffsetMm', [0, 0, 0]))
R_ = load(job['reference'], base, job.get('referenceScale', 1), job.get('referenceOffsetMm', [0, 0, 0]))
A, B = sample(M, n, rng), sample(R_, n, rng)
extra, missing = distances(A, B)
res = {
    'as placed': {'extra (model -> reference)': stats(extra), 'missing (reference -> model)': stats(missing)},
    'bbox model': [np.round(M.reshape(-1, 3).min(0), 1).tolist(), np.round(M.reshape(-1, 3).max(0), 1).tolist()],
    'bbox reference': [np.round(R_.reshape(-1, 3).min(0), 1).tolist(), np.round(R_.reshape(-1, 3).max(0), 1).tolist()],
}
if job.get('icp'):
    R, t = icp(A[::10], B[::10])
    e2, m2 = distances(A @ R.T + t, B)
    ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
    res['after rigid alignment'] = {'extra (model -> reference)': stats(e2), 'missing (reference -> model)': stats(m2),
                                    'rotationDeg': round(float(ang), 2), 'translationMm': np.round(t, 1).tolist()}
out = job_path.with_suffix('.result.json')
out.write_text(json.dumps(res, indent=2) + '\n')
print(json.dumps(res, indent=2))
exp = job.get('expect')
if exp:
    key = 'after rigid alignment' if job.get('icp') else 'as placed'
    worst = {k: max(res[key]['extra (model -> reference)'][k], res[key]['missing (reference -> model)'][k]) for k in exp}
    bad = {k: v for k, v in worst.items() if v > exp[k]}
    if bad:
        sys.exit(f'compare_mesh: worse than expected: {bad} (limits {exp})')
    print('compare_mesh: within', exp)
