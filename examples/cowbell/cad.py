"""Rigid parts of the cowbell (NMAH 2018.0174.01), in millimetres, exported as STL to parts/.

Frame: up +y (mouth at y = 0, handle on top), front +z (a broad face), origin at the mouth's centre.
First guesses come from the museum's photo and published size (spec.md); fit_silhouette.py fits the
uncertain ones and writes params.json. The museum's 3D scan is the answer key, never an input.
"""
import json, math
from pathlib import Path
from build123d import *

OUT = Path(__file__).parent / 'parts'

P = dict(
    mouth_w=88.9,      # mouth, across the broad faces: the published overall width (sourced, not fitted)
    mouth_d=60.0,      # mouth, front to back (published depth 63.5 includes the loops' wire)
    crown_w=73.0,      # top of the body, across
    crown_d=36.0,      # top of the body, front to back (no side photo: a guess the scan views fit)
    body_h=112.0,      # mouth to crown
    corner_r=6.0,      # rounding of the four vertical corners
    shoulder_r=5.0,    # rounding where the crown meets the sides
    handle_d=18.0,     # handle tube
    top=263.7,         # handle's top above the rim: published overall 266.7, less the clapper's ~3 mm below the
                       # rim (museum photo); sourced, not fitted
    paint_y=152.0,     # where the red stops and the black handle grip starts
    loop_out=25.0,     # outer edge of the side loops, from the centre line
    loop_top=135.0,    # top of the side loops' outer corners
    loop_rise=5.0,     # how much higher the straps meet the handle than their outer corners
    loop_w=10.0,       # the straps' width, front to back (a side view shows it)
)
PARAMS = Path(__file__).parent / 'params.json'
if PARAMS.exists():
    P.update(json.loads(PARAMS.read_text()))

WALL = 1.5            # sheet steel
WIRE = 3.0            # the loops' strap thickness
CLAPPER_R, CLAPPER_Y, CLAPPER_Z = 7.0, 4.0, 10.0     # ball radius, centre height (3 mm below the rim, museum photo), how far forward
UP = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))     # a sketch plane facing +y

def at(y):
    return UP.offset(y)

def body_solid(p):
    """A tapered box, lofted from the mouth to the crown, hollowed by a smaller loft open at the mouth
    (subtracting is robust; the kernel's shell fails on the filleted crown)."""
    r0 = min(p['corner_r'], p['mouth_d'] / 2 - 1)
    r1 = min(p['corner_r'], p['crown_d'] / 2 - 1)
    mouth = at(0) * RectangleRounded(p['mouth_w'], p['mouth_d'], r0)
    crown = at(p['body_h']) * RectangleRounded(p['crown_w'], p['crown_d'], r1)
    b = loft([mouth, crown])
    try:
        b = fillet(b.faces().sort_by(Axis.Y)[-1].edges(), radius=p['shoulder_r'])
    except Exception:
        pass                                                   # the kernel refused this radius: leave it square
    t = WALL
    inner = loft([at(-1) * RectangleRounded(p['mouth_w'] - 2 * t, p['mouth_d'] - 2 * t, max(r0 - t, 0.5)),
                  at(p['body_h'] - t) * RectangleRounded(p['crown_w'] - 2 * t, p['crown_d'] - 2 * t, max(r1 - t, 0.5))])
    return b - inner

def tube(p, y0, y1):
    return at(y0) * Cylinder(p['handle_d'] / 2, y1 - y0, align=(Align.CENTER, Align.CENTER, Align.MIN))

def loops_solid(p):
    """Two flat straps, one each side of the handle: up from the crown, then sloping up and in to the handle.
    Seen from the side a strap is as wide as loop_w; seen from the front, a WIRE-thick frame."""
    parts = []
    x0, x1 = p['handle_d'] / 2 - 1, p['loop_out']
    y0, y1 = p['body_h'] - 4, p['loop_top']
    yi = y1 + p['loop_rise']                                   # where the strap meets the handle
    w = p['loop_w']
    for s in (1, -1):
        parts.append(Box(WIRE, y1 - y0, w).moved(Location((s * (x1 - WIRE / 2), (y0 + y1) / 2, 0))))
        dx, dy = x1 - x0, y1 - WIRE / 2 - yi
        bar = Box(math.hypot(dx, dy) + WIRE / 2, WIRE, w).rotate(Axis.Z, math.degrees(math.atan2(dy, dx)))
        if s < 0:
            bar = bar.mirror(Plane.YZ)
        parts.append(bar.moved(Location((s * (x0 + x1) / 2, (yi + y1 - WIRE / 2) / 2, 0))))
    return Part() + parts

def clapper_parts():
    """Rod and ball. The ball hangs out of the mouth, resting against the front wall (the museum photo
    shows it below the rim's middle); fixed sizes, not fitted."""
    rod = at(CLAPPER_Y) * Cylinder(1.5, P['body_h'] - CLAPPER_Y, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return rod, Sphere(CLAPPER_R).moved(Location((0, CLAPPER_Y, CLAPPER_Z)))

def parts_solid(p=P):
    """{part: shape}, for the fit and the build. The black grip is its own part: the fit's dark channel
    places the paint line from where the photos turn black. Names starting with _ are for the fit only."""
    return {
        'body': body_solid(p),
        'neck': tube(p, p['body_h'] - 4, p['paint_y']),
        'grip': tube(p, p['paint_y'], p['top']),
        'loops': loops_solid(p),
        'clapper': clapper_parts()[1],
        # The mouth's opening as a plate: dark from below (you see inside), so a photo from below tells
        # the fit it is below. From above it would darken the rim, which the photo doesn't show.
        '_mouth': extrude(at(0.1) * RectangleRounded(p['mouth_w'] - 2 * WALL, p['mouth_d'] - 2 * WALL,
                                                     max(min(p['corner_r'], p['mouth_d'] / 2 - 1) - WALL, 0.5)), amount=0.2),
    }

def landmarks(p=P):
    """Named points (mm) that a photo can mark by hand."""
    return {
        'handle_top': [0, p['top'], 0],
        'paint_line': [0, p['paint_y'], p['handle_d'] / 2],
        'loop_l_top': [-p['loop_out'], p['loop_top'], 0],
        'loop_r_top': [p['loop_out'], p['loop_top'], 0],
    }

VIEW_DARK = {'all': ['grip', 'clapper'], 'below': ['grip', 'clapper', '_mouth']}

def save(part, name, tolerance=0.05, angular=0.2):
    export_stl(part, str(OUT / f'{name}.stl'), tolerance=tolerance, angular_tolerance=angular)

if __name__ == '__main__':
    import shutil
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    for name, shape in parts_solid().items():
        if name.startswith('_'):
            continue
        save(shape, name, *((0.1, 0.4) if name == 'clapper' else ()))
    save(clapper_parts()[0], 'clapper_rod', 0.1, 0.4)
    print('cad: parts ->', OUT)
