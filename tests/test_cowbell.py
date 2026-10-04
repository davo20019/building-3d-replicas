"""The cowbell end to end, against answers the method never sees: the true cameras of the scan renders,
and the museum's scan itself. Slow (Blender and the fit); run examples/cowbell/fetch_refs.sh first.

The limits are the example's reported results (REPORT.md) with a margin; a change that makes the method
worse fails here.
"""
import json, shutil, subprocess, sys
import pytest
from conftest import COWBELL, run

pytestmark = pytest.mark.slow

# On the real bell the cameras are the method's weak point: distances come out within ~3%, but pitch and
# yaw only within ~15 degrees, because the model is simpler than the bell (REPORT.md). On the model's own
# renders the same fit is within 2 degrees (test_fit_self.py). The limits guard against getting worse.
ANGLE_DEG = 20.0         # pitch, yaw (mod 180: the bell looks the same turned half round), roll
DIST = 0.08              # distance (mm), relative; the focal length is given, as EXIF would
SCAN_MEAN_MM = 1.6       # replica vs scan, after rigid alignment, worse direction (reported 1.38)
SCAN_P95_MM = 5.0        # (reported 4.40)

def copy_example(tmp_path):
    d = tmp_path / 'cowbell'
    shutil.copytree(COWBELL, d, ignore=shutil.ignore_patterns('.venv', 'fit', 'review', 'parts', 'out', '*.result.json'))
    return d

def test_cameras_match_truth(tmp_path, needs_cowbell_refs):
    """With the fitted shape held, the cameras solved from the scan renders' cut-outs are the true ones."""
    d = copy_example(tmp_path)
    cfg = json.loads((d / 'review.json').read_text())
    cfg['fit']['params'] = {}
    cfg['fit']['photos'] = [p for p in cfg['fit']['photos'] if p['name'].startswith('scan_')]
    (d / 'review.json').write_text(json.dumps(cfg))
    r = run('fit_silhouette.py', d)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    truth = json.loads((d / 'refs' / 'scan' / 'views.json').read_text())['cameras']
    for name, t in truth.items():
        c = json.loads((d / 'fit' / name / 'camera.json').read_text())
        p, y, ro = c['pitchYawRollDeg']
        tp, ty, tr = t['pitchYawRollDeg']
        dyaw = (y - ty + 90) % 180 - 90
        print(f"{name}: pitch {p - tp:+.1f}, yaw {dyaw:+.1f}, roll {ro - tr:+.1f} deg, distance {c['distanceMm'] / t['distanceMm'] - 1:+.1%}")
        assert abs(p - tp) < ANGLE_DEG and abs(dyaw) < ANGLE_DEG and abs(ro - tr) < ANGLE_DEG, (name, c['pitchYawRollDeg'], t)
        assert abs(c['distanceMm'] / t['distanceMm'] - 1) < DIST, (name, c['distanceMm'], t['distanceMm'])

def test_replica_matches_scan(tmp_path, needs_cowbell_refs):
    """The fitted parameters (params.json) build a cowbell within a couple of mm of the museum's scan."""
    d = copy_example(tmp_path)
    r = subprocess.run([sys.executable, 'cad.py'], cwd=d, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    job = json.loads((d / 'check' / 'scan.json').read_text())
    job['expect'] = {'meanMm': SCAN_MEAN_MM, 'p95Mm': SCAN_P95_MM}
    (d / 'check' / 'scan.json').write_text(json.dumps(job))
    r = run('compare_mesh.py', d / 'check' / 'scan.json')
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
