"""
ESCHBACH product shots + surface macros (replace the prototype's code-drawn canvases).

  blender -b --factory-startup -P tools/blender/render_products.py -- [--only products|textures] [--pct 100] [--samples 128]

Writes (PNG, into .tmp/products_png):
  products/<id>.png   square 1200x1200, transparent background with soft contact shadow (studio light)
  textures/<coll>.png 1920x1080 orthographic macro of the surface in raking light (for the material loupe)
Convert/publish with tools/products_publish.py.
"""
import sys, os, math, argparse
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.append(HERE)
import vessel_lib as vl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(ROOT, ".tmp", "products_png"))
ap.add_argument("--only", default="")
ap.add_argument("--ids", default="")
ap.add_argument("--pct", type=int, default=100)
ap.add_argument("--samples", type=int, default=128)
A = ap.parse_args(argv)
A.out = os.path.abspath(A.out)

# id, form, collection, colour name  (matches the website's featured cards + minis)
PRODUCTS = [
    ("loft", "egg", "loft", "Rust Brown"),
    ("terra", "talleg", "terra", "Champagne White"),
    ("antique", "balloon", "antique", "Copper Green"),
    ("lava", "bowl", "lava", "Volcanic Black"),
    ("pure", "highballoon", "pure", "Santorin White"),
    ("granite", "egg", "granite", "Granite Grey"),
    ("vertical", "talleg", "vertical", "Vertical White"),
    ("empire", "balloon", "empire", "Lead Grey"),
]
TEXTURES = [("loft", "Concrete Grey"), ("terra", "Desert Beige"), ("antique", "Copper Green"),
            ("lava", "Volcanic Black"), ("granite", "Granite Grey"), ("vertical", "Vertical White")]
HEIGHT = {"balloon": .55, "highballoon": .7, "egg": .6, "talleg": .95, "bowl": .42, "box": .5}


def color_of(cid, name):
    c = vl.COLLECTIONS[cid]; v = c["colors"][name]
    col, alt = (v if isinstance(v, tuple) else (v, None))
    return c["finish"], col, alt


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA"); ld.shape = "DISK"; ld.size = size; ld.energy = energy; ld.color = color
    ob = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def render(sc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); print("RENDERED", path, flush=True)


def product(pid, form, cid, cname):
    vl.clear_scene()
    sc = vl.setup_cycles(samples=A.samples, res=(1200, 1200), pct=A.pct, transparent=True)
    sc.view_settings.exposure = -0.45
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.32, .31, .3, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .35
    finish, col, alt = color_of(cid, cname)
    h = HEIGHT[form]
    vl.build_vessel(form, height=h, finish=finish, color=col, alt=alt, rotation_z=.5, plant="grass", name="P")
    me = bpy.data.meshes.new("F"); s = 20
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new("F", me); sc.collection.objects.link(fl); fl.is_shadow_catcher = True
    # studio: big soft key left-front, cool rim right-back, low fill
    tz = h * .62
    area("Key", (-1.6, -1.5, 1.9), (0, 0, tz * .7), 1.6, 150, (1, .95, .88))
    area("Rim", (1.5, 1.4, 1.5), (0, 0, tz), .9, 110, (.86, .9, 1))
    area("Fill", (1.8, -1.6, .8), (0, 0, tz * .6), 2.0, 25)
    cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    cam_d.lens = 70
    top = h + max(.42, h * .55) * .95                    # vessel + grass
    width = h / vl.FORMS[form]["aspect"] * 1.45
    extent = max(top, width) * 1.22
    dist = extent / (2 * math.tan(math.atan(18 / cam_d.lens)))
    target = Vector((0, 0, top * .5))
    el = math.radians(9)
    cam.location = target + Vector((0, -math.cos(el), math.sin(el))) * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    render(sc, os.path.join(A.out, "products", f"{pid}.png"))


def ribbed_plane(w, h, pitch, depth, res=1200):
    verts, faces = [], []
    for i in range(res + 1):
        x = -w / 2 + w * i / res
        z = depth * (abs(math.cos(math.pi * x / pitch)) ** .6 - .5)
        verts += [(x, -h / 2, z), (x, h / 2, z)]
    for i in range(res):
        a = 2 * i; faces.append((a, a + 2, a + 3, a + 1))
    me = bpy.data.meshes.new("Rib"); me.from_pydata(verts, [], faces); vl.set_smooth(me); return me


def texture(cid, cname):
    vl.clear_scene()
    sc = vl.setup_cycles(samples=A.samples, res=(1920, 1080), pct=A.pct)
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .08
    finish, col, alt = color_of(cid, cname)
    W, H = .32, .18
    if finish == "ribs":
        me = ribbed_plane(W * 1.2, H * 1.2, .022, .0035)
    else:
        me = bpy.data.meshes.new("Pl"); me.from_pydata([(-W * .6, -H * .6, 0), (W * .6, -H * .6, 0), (W * .6, H * .6, 0), (-W * .6, H * .6, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("Surf", me); sc.collection.objects.link(ob)
    ob.data.materials.append(vl.make_material(finish, col, alt))
    sun_d = bpy.data.lights.new("Sun", "SUN"); sun = bpy.data.objects.new("Sun", sun_d); sc.collection.objects.link(sun)
    d = Vector((-.9, .25, .42)).normalized()                  # raking light from the left
    sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); sun_d.energy = 4.5; sun_d.angle = math.radians(2)
    sun_d.color = (1, .95, .88)
    area("Soft", (.5, -.3, .6), (0, 0, 0), .6, 6)
    cam_d = bpy.data.cameras.new("C"); cam_d.type = "ORTHO"; cam_d.ortho_scale = W
    cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, 0, .5); cam.rotation_euler = (0, 0, 0)
    render(sc, os.path.join(A.out, "textures", f"{cid}.png"))


ids = set(x for x in A.ids.split(",") if x)
if A.only in ("", "products"):
    for p in PRODUCTS:
        if not ids or p[0] in ids:
            product(*p)
if A.only in ("", "textures"):
    for t in TEXTURES:
        if not ids or t[0] in ids:
            texture(*t)
print("DONE")
