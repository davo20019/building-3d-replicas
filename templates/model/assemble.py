"""Assemble the model from parts/ (cad.py) into out/model.glb and out/model.json.
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

# Colours: sample the photo's lit faces. Metallic only where the scene has environment lighting.
PAINT = material('paint', srgb(200, 200, 200), 0.4, coat=0.3)

def stl(name, mat, smooth_angle=35):
    bpy.ops.wm.stl_import(filepath=str(PARTS / f'{name}.stl'))
    o = bpy.context.selected_objects[0]
    o.name = o.data.name = name
    o.data.transform(TO_BLENDER)
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth_angle))
    return o

body = stl('body', PAINT)

# Moving parts: an empty at the pivot, the part's mesh moved so the pivot is its origin, parented to it.

root = bpy.data.objects.new('model', None)
bpy.context.scene.collection.objects.link(root)
for o in bpy.context.scene.objects:
    if o is not root and o.parent is None:
        o.parent = root
root.scale = (0.001,) * 3

bpy.ops.export_scene.gltf(filepath=str(OUT / 'model.glb'), export_format='GLB',
                          export_cameras=False, export_lights=False, export_apply=True)
info = {
    'units': 'metres; glTF frame: up +y, front +z, origin at <where>',
}
(OUT / 'model.json').write_text(json.dumps(info, indent=2))
print('assemble: wrote', OUT / 'model.glb')
