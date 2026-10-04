"""measure.py against a synthetic camera: references and queries projected exactly, so the answer is known."""
import json
import cv2
import numpy as np
from conftest import run

W, H = 1200, 1600

def rotation(pyr):
    rx, ry, rz = np.radians(pyr)
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
    return Rz @ Rx @ Ry

def project(X, pyr=(20, -40, 0), centre=(0, 130, 0), dist=600.0, s=4.4):
    P = (np.atleast_2d(X) - centre) @ rotation(pyr).T
    z = dist - P[:, 2]
    f = s * dist
    return np.c_[W / 2 + f * P[:, 0] / z, H / 2 - f * P[:, 1] / z]

def job(tmp_path, noise=0.0, expect_tol=1.0):
    cv2.imwrite(str(tmp_path / 'photo.png'), np.full((H, W, 3), 255, np.uint8))
    # A cowbell-sized frame of known points: the mouth's corners, the crown's, the handle's top.
    refs = {'mouth_fl': [-45, 0, 29], 'mouth_fr': [45, 0, 29], 'mouth_br': [45, 0, -29], 'mouth_bl': [-45, 0, -29],
            'crown_fl': [-35, 112, 17], 'crown_fr': [35, 112, 17], 'crown_br': [35, 112, -17], 'top': [0, 265, 0]}
    rng = np.random.default_rng(1)
    px = {n: (project(np.array(p, float))[0] + rng.normal(0, noise, 2)).tolist() for n, p in refs.items()}
    target = np.array([12.0, 60.0, 23.0])                     # a point on the front face's plane z = 23
    j = {'photo': 'photo.png', 'refs': {n: {'px': px[n], 'mm': refs[n]} for n in refs},
         'queries': {'dent': {'px': project(target)[0].tolist(), 'plane': {'z': 23.0}}},
         'expect': {'dent': {'x': 12.0, 'y': 60.0, 'tol': expect_tol}}}
    (tmp_path / 'job.json').write_text(json.dumps(j))
    return tmp_path / 'job.json'

def test_exact_points_measure_exactly(tmp_path):
    r = run('measure.py', job(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'PASS' in r.stdout and 'FAIL' not in r.stdout

def test_one_px_noise_stays_within_a_millimetre(tmp_path):
    r = run('measure.py', job(tmp_path, noise=1.0, expect_tol=1.5))
    assert r.returncode == 0, r.stdout + r.stderr

def test_expect_reports_a_miss(tmp_path):
    p = job(tmp_path)
    j = json.loads(p.read_text())
    j['expect']['dent']['x'] = 20.0                            # wrong on purpose
    p.write_text(json.dumps(j))
    r = run('measure.py', p)
    assert r.returncode == 1 and 'FAIL' in r.stdout
