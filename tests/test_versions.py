"""Every file that carries the version must agree: the plugin manifests decide what users install."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('release', Path(__file__).resolve().parents[1] / 'tools' / 'release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

def test_versions_agree():
    versions = release.current_versions()
    assert len(set(versions.values())) == 1, f'versions disagree: {versions} (run tools/release.py)'

def test_bump():
    assert release.bumped('0.2.0', 'patch') == '0.2.1'
    assert release.bumped('0.2.3', 'minor') == '0.3.0'
    assert release.bumped('0.2.3', 'major') == '1.0.0'
    assert release.bumped('0.2.3', '0.4.0') == '0.4.0'
