"""Rigid parts of <object>, in millimetres, exported as STL to parts/.

Frame: up +y, front +z, origin at <where> (docs/frames.md). Sizes come from spec.md; uncertain ones are in P,
fitted by fit_silhouette.py into params.json.
"""
import json
from pathlib import Path
from build123d import *

OUT = Path(__file__).parent / 'parts'

P = dict(
    width=100.0,      # first guesses; each one fitted or measured, never left as a guess without saying so
    height=50.0,
    depth=30.0,
)
PARAMS = Path(__file__).parent / 'params.json'
if PARAMS.exists():
    P.update(json.loads(PARAMS.read_text()))

def parts_solid(p=P):
    """{part: shape} for the fit and the build. Separately coloured parts are separate entries."""
    body = Box(p['width'], p['height'], p['depth']).moved(Location((0, p['height'] / 2, 0)))
    return {'body': body}

def landmarks(p=P):
    """Named model points (mm) that photos can mark by hand: corners, centres, the ends of a feature."""
    return {'top_front_left': [-p['width'] / 2, p['height'], p['depth'] / 2]}

VIEW_DARK = {'all': []}       # per view: the parts the fit should find by darkness or lack of colour

def save(part, name, tolerance=0.05, angular=0.2):
    export_stl(part, str(OUT / f'{name}.stl'), tolerance=tolerance, angular_tolerance=angular)

if __name__ == '__main__':
    import shutil
    shutil.rmtree(OUT, ignore_errors=True)     # stale parts would come back otherwise
    OUT.mkdir()
    for name, shape in parts_solid().items():
        save(shape, name)
    print('cad: parts ->', OUT)
