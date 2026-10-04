"""compare_mesh.py on boxes whose answer is known exactly."""
import json
import numpy as np
from conftest import run

def box(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    c = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float) * (hi - lo) + lo
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return np.array([[c[a], c[b], c[d]] for a, b, cc, d in quads for a, b, d in ((a, b, cc), (a, cc, d))])

def write_stl(path, T):
    with open(path, 'w') as f:
        f.write('solid t\n')
        for t in T:
            f.write(' facet normal 0 0 0\n  outer loop\n' + ''.join(f'   vertex {x} {y} {z}\n' for x, y, z in t) + '  endloop\n endfacet\n')
        f.write('endsolid t\n')

def test_same_box_is_zero(tmp_path):
    write_stl(tmp_path / 'a.stl', box([0, 0, 0], [100, 50, 20]))
    write_stl(tmp_path / 'b.stl', box([0, 0, 0], [100, 50, 20]))
    (tmp_path / 'job.json').write_text(json.dumps({'model': ['a.stl'], 'reference': 'b.stl', 'samples': 50000}))
    r = run('compare_mesh.py', tmp_path / 'job.json')
    assert r.returncode == 0, r.stderr
    res = json.loads((tmp_path / 'job.result.json').read_text())
    assert res['as placed']['extra (model -> reference)']['meanMm'] < 0.5

def test_offset_box_and_icp(tmp_path):
    """A box moved 3 mm along x: about 3 mm on the two end faces as placed, ~0 after alignment."""
    write_stl(tmp_path / 'a.stl', box([3, 0, 0], [103, 50, 20]))
    write_stl(tmp_path / 'b.stl', box([0, 0, 0], [100, 50, 20]))
    (tmp_path / 'job.json').write_text(json.dumps({'model': ['a.stl'], 'reference': 'b.stl', 'samples': 50000, 'icp': True,
                                                   'expect': {'meanMm': 0.5}}))
    r = run('compare_mesh.py', tmp_path / 'job.json')
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads((tmp_path / 'job.result.json').read_text())
    assert res['as placed']['extra (model -> reference)']['maxMm'] > 2.5
    assert abs(res['after rigid alignment']['translationMm'][0] + 3) < 0.3

def test_expect_fails_when_worse(tmp_path):
    write_stl(tmp_path / 'a.stl', box([0, 0, 0], [110, 50, 20]))
    write_stl(tmp_path / 'b.stl', box([0, 0, 0], [100, 50, 20]))
    (tmp_path / 'job.json').write_text(json.dumps({'model': ['a.stl'], 'reference': 'b.stl', 'samples': 50000,
                                                   'expect': {'p95Mm': 1.0}}))
    assert run('compare_mesh.py', tmp_path / 'job.json').returncode != 0
