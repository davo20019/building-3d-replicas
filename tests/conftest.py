import os, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
COWBELL = ROOT / 'examples' / 'cowbell'

def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True, cwd=cwd)

def pytest_configure(config):
    config.addinivalue_line('markers', 'slow: runs Blender and the fit (minutes); needs examples/cowbell/fetch_refs.sh first')

@pytest.fixture
def needs_cowbell_refs():
    if not shutil.which('blender'):
        pytest.skip('Blender is not on PATH')
    if not (COWBELL / 'refs' / 'scan' / 'scan_low.png').exists():
        pytest.skip('run examples/cowbell/fetch_refs.sh first')
