"""Render a GLB from named cameras, for comparing a model with photos or manual pictures side by side.
  blender -b --factory-startup --python scripts/render_cams.py -- <glb> <cams.json> <outdir>

cams.json: {"glbFrame": "y-up" | "front+y", "exposure": 0, "samples": 32, "lights": [{"at": [x, y, z], "watts": 100, "size": 500}],
            "cameras": {name: camera}}, where a camera is either
  {"eye": [x, y, z], "look": [x, y, z], "fovDeg": 80, "size": [W, H]}     model frame, mm, up +y
  {"measure": "path/to/<job>.camera.json"}                                 solved by scripts/measure.py
                                                                            (relative to cams.json)
  optional per camera: "exposure", "hide": [object or node name prefixes], "only": [mesh name prefixes to keep], "photo": path to place beside the render
Writes <outdir>/<name>.png, and <name>_pair.png (photo left, render right, same height) when "photo" is set.

The model frame is millimetres, front +z, up +y. Lighting: a bright sky (the cabin is lit through its glass,
as in a showroom) and an off-axis sun; Khronos PBR Neutral tone mapping, as in review.py.
"""
import bpy, sys, json, math, os
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index('--') + 1:]
glb, cams_path, outdir = args[:3]
cfg = json.load(open(cams_path))
base = os.path.dirname(os.path.abspath(cams_path))
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
if cfg.get('glbFrame', 'y-up') == 'y-up':                    # Blender imports glTF y-up as z-up: turn it back
    fix = Matrix.Rotation(-math.pi / 2, 4, 'X')
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.matrix_world = fix @ o.matrix_world
bpy.context.view_layer.update()

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = cfg.get('samples', 32)
sc.cycles.use_denoising = True
try:
    sc.cycles.device = 'GPU'
    bpy.context.preferences.addons['cycles'].preferences.compute_device_type = 'METAL'
    bpy.context.preferences.addons['cycles'].preferences.get_devices()
    for d in bpy.context.preferences.addons['cycles'].preferences.devices:
        d.use = True
except Exception:
    pass
sc.view_settings.view_transform = 'Khronos PBR Neutral'
sc.view_settings.exposure = cfg.get('exposure', 0)
world = bpy.data.worlds.new('w')
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.75, 0.8, 0.9, 1)
bg.inputs['Strength'].default_value = 1.2
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(-50), math.radians(25), 0)   # from above and to one side (model frame, y up)
sun.rotation_mode = 'XYZ'
sun.matrix_world = Matrix.Rotation(math.radians(-60), 4, 'X') @ Matrix.Rotation(math.radians(30), 4, 'Y')
sc.collection.objects.link(sun)
for i, l in enumerate(cfg.get('lights', [])):          # fill lights: {"at": [x, y, z] mm, "watts": 100, "size": 1000 mm}
    lo = bpy.data.objects.new(f'fill{i}', bpy.data.lights.new(f'fill{i}', 'POINT'))
    lo.data.energy = l.get('watts', 100)
    lo.data.shadow_soft_size = l.get('size', 500) / 1000
    lo.location = Vector(l['at']) / 1000
    sc.collection.objects.link(lo)

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam

def look_matrix(eye, look, up=(0, 1, 0)):
    eye, look, up = Vector(eye), Vector(look), Vector(up)
    back = (eye - look).normalized()
    right = up.cross(back).normalized()
    upv = back.cross(right)
    m = Matrix((right, upv, back)).transposed().to_4x4()
    m.translation = eye
    return m

if not cfg.get('cameras'):
    sys.exit('render_cams.py: cams.json needs a "cameras" block: {name: {"eye", "look"} or {"measure": "<job>.camera.json"}}')
for name, c in cfg['cameras'].items():
    if 'measure' not in c and not ('eye' in c and 'look' in c):
        sys.exit(f'render_cams.py: camera {name!r} needs "eye" and "look" (mm, model frame) or "measure"')
    hidden = []
    only = c.get('only')
    for o in sc.objects:
        if only and o.type == 'MESH' and not any(o.name.startswith(h) for h in only):
            if not o.hide_render:
                o.hide_render = True
                hidden.append(o)
            continue
        hide = any(o.name.startswith(h) or (o.parent and o.parent.name.startswith(h)) for h in c.get('hide', []))
        p = o.parent
        while p is not None and not hide:
            hide = any(p.name.startswith(h) for h in c.get('hide', []))
            p = p.parent
        if hide and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    if 'measure' in c:
        m = json.load(open(os.path.join(base, c['measure'])))
        W, H = m['size']
        R = Matrix(m['R'])
        ctr = Vector(m['centreMm']) / 1000
        # OpenCV camera axes (x right, y down, z forward) to Blender's (x right, y up, z back).
        right, down, fwd = R[0], R[1], R[2]
        mw = Matrix((right, -down, -fwd)).transposed().to_4x4()
        mw.translation = ctr
        cam.matrix_world = mw
        f = m['focalPx']
        cx, cy = m['principalPx']
        cam.data.sensor_fit = 'HORIZONTAL' if W >= H else 'VERTICAL'
        cam.data.sensor_width = 36
        cam.data.sensor_height = 36
        cam.data.lens = f / max(W, H) * 36
        cam.data.shift_x = (cx - W / 2) / max(W, H) * -1
        cam.data.shift_y = (cy - H / 2) / max(W, H)
    else:
        W, H = c.get('size', [1200, 800])
        cam.matrix_world = look_matrix([v / 1000 for v in c['eye']], [v / 1000 for v in c['look']])
        cam.data.sensor_fit = 'HORIZONTAL' if W >= H else 'VERTICAL'
        cam.data.angle = math.radians(c.get('fovDeg', 80))
        cam.data.shift_x = cam.data.shift_y = 0
    cam.data.clip_start = 0.01
    sc.view_settings.exposure = c.get('exposure', cfg.get('exposure', 0))
    sc.render.resolution_x, sc.render.resolution_y = int(W), int(H)
    sc.render.resolution_percentage = 100
    out = os.path.join(outdir, f'{name}.png')
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    if c.get('photo'):
        ph = bpy.data.images.load(os.path.join(base, c['photo']))
        rn = bpy.data.images.load(out)
        pw, phh = ph.size
        rw, rh = rn.size
        s = rh / phh
        nw = int(pw * s)
        ph.scale(nw, rh)
        pair = bpy.data.images.new('pair', nw + rw, rh, alpha=False)
        import numpy as np
        a = np.zeros((rh, nw + rw, 4), np.float32)
        a[:, :nw] = np.array(ph.pixels[:], np.float32).reshape(rh, nw, 4)
        a[:, nw:] = np.array(rn.pixels[:], np.float32).reshape(rh, rw, 4)
        a[..., 3] = 1
        pair.pixels[:] = a.ravel()
        pair.filepath_raw = os.path.join(outdir, f'{name}_pair.png')
        pair.file_format = 'PNG'
        pair.save()
    print('render_cams:', out)
