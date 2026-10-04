"""Render the museum's CC0 scan through known cameras, as extra "photos" with a known answer.
  blender -b --factory-startup --python refs/scan_views.py -- refs/scan/<scan>.glb refs/scan/views.json refs/scan

views.json: {"centreMm": [x, y, z], "offsetMm": [x, y, z], "size": [W, H],
             "cameras": {name: {"pitchYawRollDeg": [...], "distanceMm": d, "pxPerMm": s}}}
offsetMm moves the scan into the model frame (mm, front +z, up +y, the mouth's centre at the origin).
The cameras use fit_silhouette.py's own model: a pinhole at distanceMm from centreMm, turned by
pitch/yaw/roll, with pxPerMm at the centre and the centre at the image's middle. So the fit's solved
cameras can be checked against these numbers directly (tests/test_cowbell.py).
Writes <outdir>/<name>.png on a white backdrop.
"""
import bpy, sys, json, math, os
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
glb, views_path, outdir = args[:3]
cfg = json.load(open(views_path))
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
# glTF is y-up and Blender z-up: turn the import back, so Blender's world is the model frame (in metres).
fix = Matrix.Translation(Vector(cfg['offsetMm']) / 1000) @ Matrix.Rotation(-math.pi / 2, 4, 'X')
for o in bpy.context.scene.objects:
    if o.parent is None:
        o.matrix_world = fix @ o.matrix_world

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new('w')
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (1, 1, 1, 1)
bg.inputs['Strength'].default_value = 1.0
key = bpy.data.objects.new('key', bpy.data.lights.new('key', 'AREA'))
key.data.energy = 60
key.data.size = 0.6
key.location = (0.5, 0.9, 0.8)
key.rotation_euler = (Vector((0, 0.13, 0)) - key.location).to_track_quat('-Z', 'Y').to_euler()
sc.collection.objects.link(key)

def rotation(pyr):
    """fit_silhouette.rotation: yaw about up, then pitch, then roll."""
    rx, ry, rz = np.radians(pyr)
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
    return Rz @ Rx @ Ry

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
W, H = cfg['size']
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
C = np.array(cfg['centreMm'], float)
for name, c in cfg['cameras'].items():
    R = rotation(c['pitchYawRollDeg'])
    d = c['distanceMm']
    eye = C + R.T @ [0, 0, d]
    m = Matrix(np.c_[R.T, eye / 1000].tolist() + [[0, 0, 0, 1]])   # columns: right, up, back, eye
    cam.matrix_world = m
    f = c['pxPerMm'] * d                                       # px
    cam.data.sensor_fit = 'HORIZONTAL' if W >= H else 'VERTICAL'
    cam.data.sensor_width = cam.data.sensor_height = 36
    cam.data.lens = f / max(W, H) * 36
    cam.data.clip_start = 0.01
    sc.render.filepath = os.path.join(outdir, f'{name}.png')
    bpy.ops.render.render(write_still=True)
    print('scan_views:', sc.render.filepath)
