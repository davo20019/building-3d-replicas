"""Assemble the cowbell from parts/ (cad.py) into out/cowbell.glb and out/cowbell.json.
  blender -b --factory-startup --python assemble.py

The CAD is in millimetres, up +y, front +z. Blender is z-up, so each part's mesh is turned into Blender's
frame on import ((x, y, z) -> (x, -z, y)); the glTF exporter turns it back, so the GLB is y-up with the
front on +z. The root is never rotated: every node keeps identity rotation and turns about its own axes.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
PARTS, OUT = HERE / 'parts', HERE / 'out'
OUT.mkdir(exist_ok=True)
P = json.loads((HERE / 'params.json').read_text()) if (HERE / 'params.json').exists() else {}
BODY_H = P.get('body_h', 112.0)
TO_BLENDER = Matrix.Rotation(math.pi / 2, 4, 'X')

bpy.ops.wm.read_factory_settings(use_empty=True)

def material(name, color, rough, coat=0.0, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = rough
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Coat Roughness'].default_value = 0.1
    return m

def srgb(r, g, b):
    f = lambda c: (c / 255) ** 2.2
    return f(r), f(g), f(b)

# Colours sampled from the museum photo's lit faces. Gloss enamel over steel: dielectric with a coat,
# so it reads right without environment lighting.
RED = material('red_enamel', srgb(150, 18, 22), 0.35, coat=0.5)
BLACK = material('black_grip', srgb(28, 28, 30), 0.7)
STEEL = material('dark_steel', srgb(60, 60, 62), 0.45, metallic=1.0)

def stl(name, mat, smooth_angle=35):
    bpy.ops.wm.stl_import(filepath=str(PARTS / f'{name}.stl'))
    o = bpy.context.selected_objects[0]
    o.name = o.data.name = name
    o.data.transform(TO_BLENDER)
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth_angle))
    return o

body = stl('body', RED)
neck = stl('neck', RED, 60)
grip = stl('grip', BLACK, 60)
loops = stl('loops', RED)
rod = stl('clapper_rod', STEEL, 60)
ball = stl('clapper', STEEL, 80)

# The clapper swings from the crown: one node, its pivot at the rod's top.
swing = bpy.data.objects.new('clapper_swing', None)
bpy.context.scene.collection.objects.link(swing)
swing.location = (0, 0, BODY_H)                              # mm under the root; Blender z = model y
for o in (rod, ball):
    o.data.transform(Matrix.Translation((0, 0, -BODY_H)))
    o.parent = swing

root = bpy.data.objects.new('cowbell', None)
bpy.context.scene.collection.objects.link(root)
for o in bpy.context.scene.objects:
    if o is not root and o.parent is None:
        o.parent = root
root.scale = (0.001,) * 3

bpy.ops.export_scene.gltf(filepath=str(OUT / 'cowbell.glb'), export_format='GLB',
                          export_cameras=False, export_lights=False, export_apply=True)
info = {
    'units': 'metres; glTF frame: up +y (handle), front +z (a broad face), origin at the mouth centre',
    'clapper': {'node': 'clapper_swing', 'pivotM': [0, BODY_H / 1000, 0], 'axes': 'x and z',
                'note': 'swing by rotating the node about x and z, a few degrees each way'},
}
(OUT / 'cowbell.json').write_text(json.dumps(info, indent=2))
print('assemble: wrote', OUT / 'cowbell.glb')
