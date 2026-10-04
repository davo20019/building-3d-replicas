"""Blender side of scripts/review.py: import a GLB, measure its nodes, render review views.
  blender -b --factory-startup --python scripts/render_views.py -- <glb> <outdir> <review.json> [camera.json ...]

Writes <outdir>/front.png (orthographic, straight on, frontFrameMm wide), three_quarter.png, side.png and
measure.json (each object's world size in mm and the scene's triangle count). For each camera.json from
fit_silhouette.py, also photo_<name>.png: the model seen through that photo's solved camera.

The model frame is millimetres with the front on +z and up on +y. review.json's "glbFrame" says how the
GLB stores it: "y-up" (default; glTF +y up, front +z, for anything standing on the ground) or "front+y"
(up is glTF -z, for hand-held objects with a face you look down at). See docs/frames.md. Either way the
import is turned into the model frame. Camera distances scale with frontFrameMm, so a 6 m truck and a
6 cm altimeter get the same framing.
"""
import bpy, sys, json, math
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index('--') + 1:]
glb, outdir, review_json = args[:3]
cams = args[3:]
cfg = json.load(open(review_json))
frame = cfg['frontFrameMm'] / 1000
k = cfg['frontFrameMm'] / 75                                    # the views were tuned on a 75 mm frame

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
if cfg.get('glbFrame', 'y-up') == 'y-up':                    # Blender imports glTF y-up as z-up: turn it back
    fix = Matrix.Rotation(-math.pi / 2, 4, 'X')
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.matrix_world = fix @ o.matrix_world
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

sizes, bounds, tris = {}, {}, 0
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    sizes[o.name] = [round((max(p[i] for p in pts) - min(p[i] for p in pts)) * 1000, 2) for i in range(3)]
    bounds[o.name] = [[round(min(p[i] for p in pts) * 1000, 1) for i in range(3)], [round(max(p[i] for p in pts) * 1000, 1) for i in range(3)]]
    for p in pts:
        lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    me = o.evaluated_get(dg).to_mesh()
    tris += sum(len(p.vertices) - 2 for p in me.polygons)
sizes['_all'] = [round((hi[i] - lo[i]) * 1000, 2) for i in range(3)]
json.dump({'sizesMm': sizes, 'boundsMm': bounds, 'triangles': tris}, open(f'{outdir}/measure.json', 'w'), indent=2)
centre = (lo + hi) / 2

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 800
sc.view_settings.view_transform = 'Khronos PBR Neutral'
sc.view_settings.exposure = float(cfg.get('exposure', 0))
world = bpy.data.worlds.new('studio'); sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
if cfg.get('environment') == 'sky':
    # Metal mirrors its surroundings: a plain white world turns steel flat grey. A sky with a ground gives
    # it the light-above, dark-below gradient the outdoor photos show.
    sky = world.node_tree.nodes.new('ShaderNodeTexSky')
    sky.sun_elevation = math.radians(35); sky.sun_rotation = math.radians(40)
    world.node_tree.links.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.25
else:
    bg.inputs['Color'].default_value = (1, 1, 1, 1)
    bg.inputs['Strength'].default_value = 0.6

def look_at(o, target, up=Vector((0, 1, 0))):
    """Aim an object's -z at target with its +y towards the model's up (+y). Blender's to_track_quat keeps
    world +z up instead, which turns side views of a y-up model on end."""
    z = (o.location - target).normalized()
    u = up if abs(z.dot(up)) < 0.99 else Vector((0, 0, -1))
    x = u.cross(z).normalized()
    o.matrix_world = Matrix((x, z.cross(x), z)).transposed().to_4x4()

def light(loc, energy, size):
    d = bpy.data.lights.new('key', 'AREA'); d.energy = energy * k * k; d.size = size * k
    o = bpy.data.objects.new('key', d); sc.collection.objects.link(o)
    o.location = centre + Vector(loc) * k
    loc_w = o.location.copy(); look_at(o, centre); o.matrix_world.translation = loc_w
light((0.2, 0.35, 0.3), 5, 0.4)      # off-axis, so glass does not mirror it into the front camera
light((-0.3, -0.1, 0.2), 2, 0.5)

def shot(name, loc, ortho=None, lens=85):
    cd = bpy.data.cameras.new(name)
    cd.clip_end = 1000
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cam = bpy.data.objects.new(name, cd); sc.collection.objects.link(cam)
    cam.location = centre + Vector(loc) * k
    loc_w = cam.location.copy(); look_at(cam, centre); cam.matrix_world.translation = loc_w
    sc.camera = cam
    sc.render.filepath = f'{outdir}/{name}.png'
    bpy.ops.render.render(write_still=True)

shot('front', (0, 0, 0.5), ortho=frame)
shot('three_quarter', tuple(cfg.get('threeQuarter', (0.16, -0.12, 0.2))), lens=70)
shot('side', (0.5, 0, 0), ortho=frame * 1.6)

for cj in cams:
    c = json.load(open(cj))
    s = min(1.0, 1000 / max(c['width'], c['height']))           # render at most 1000 px wide
    W, Hh = round(c['width'] * s), round(c['height'] * s)
    sc.render.resolution_x, sc.render.resolution_y = W, Hh
    R = Matrix(c['rotation'])                                     # photo camera frame from model frame (mm)
    cd = bpy.data.cameras.new('photo'); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36; cd.clip_end = 1000
    cd.lens = c['focalPx'] * s * 36 / W
    cx, cy = c['principalPx']
    cd.shift_x = (W / 2 - cx * s) / max(W, Hh)                    # a shift moves the view, so the content moves the other way
    cd.shift_y = (cy * s - Hh / 2) / max(W, Hh)
    cam = bpy.data.objects.new('photo', cd); sc.collection.objects.link(cam)
    Rt = R.transposed()
    cam.matrix_world = Matrix.Translation((Vector(c['centreMm']) + Rt @ Vector((0, 0, c['distanceMm']))) * 0.001) @ Rt.to_4x4()
    sc.camera = cam
    sc.render.filepath = f'{outdir}/photo_{c.get("name", "main")}.png'
    bpy.ops.render.render(write_still=True)
