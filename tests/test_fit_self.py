"""The fit against itself: render the example's own model through known cameras, then solve those cameras
from the renders' cut-outs. The shape is exact here, so any error is the fit's: this caught the cut-outs'
holes being filled while the model's weren't, and a tilt search that started from the wrong place.
Slow (Blender); needs no downloads.
"""
import json, shutil, subprocess, sys
import pytest
from conftest import COWBELL, run

pytestmark = pytest.mark.slow

ANGLE_DEG = 3.0
DIST = 0.02

def test_fit_recovers_its_own_cameras(tmp_path):
    if not shutil.which('blender'):
        pytest.skip('Blender is not on PATH')
    d = tmp_path / 'cowbell'
    shutil.copytree(COWBELL, d, ignore=shutil.ignore_patterns('.venv', 'fit', 'review', 'parts', 'out', '*.result.json', '*.jpg', '*.glb', 'scan_*.png'))
    r = subprocess.run([sys.executable, 'cad.py'], cwd=d, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    r = subprocess.run(['blender', '-b', '--factory-startup', '--python', 'assemble.py'], cwd=d, capture_output=True, text=True)
    assert (d / 'out' / 'cowbell.glb').exists(), r.stdout[-2000:]

    views = json.loads((d / 'refs' / 'scan' / 'views.json').read_text())
    views['offsetMm'] = [0, 0, 0]                              # the model is already in the model frame
    (tmp_path / 'views.json').write_text(json.dumps(views))
    r = subprocess.run(['blender', '-b', '--factory-startup', '--python', 'refs/scan_views.py', '--',
                        'out/cowbell.glb', str(tmp_path / 'views.json'), 'self'], cwd=d, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]

    cfg = json.loads((d / 'review.json').read_text())
    cfg['fit']['params'] = {}
    cfg['fit']['photos'] = [dict(p, photo=f"self/{p['name']}.png", landmarks={})
                            for p in cfg['fit']['photos'] if p['name'] in views['cameras']]
    (d / 'review.json').write_text(json.dumps(cfg))
    r = run('fit_silhouette.py', d)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    for name, t in views['cameras'].items():
        c = json.loads((d / 'fit' / name / 'camera.json').read_text())
        p, y, ro = c['pitchYawRollDeg']
        tp, ty, tr = t['pitchYawRollDeg']
        dyaw = (y - ty + 90) % 180 - 90
        print(f"{name}: pitch {p - tp:+.1f}, yaw {dyaw:+.1f}, roll {ro - tr:+.1f} deg, distance {c['distanceMm'] / t['distanceMm'] - 1:+.1%}")
        assert abs(p - tp) < ANGLE_DEG and abs(dyaw) < ANGLE_DEG and abs(ro - tr) < ANGLE_DEG, (name, c['pitchYawRollDeg'], t)
        assert abs(c['distanceMm'] / t['distanceMm'] - 1) < DIST, (name, c['distanceMm'])
