"""
ESCHBACH Farb-Atelier: render every form into every kie.ai scenery as compositing layers.

Per scene x form it writes (PNG, transparent, same framing as the scene photo):
  env.png            shadow on the floor (shadow catcher) + soil + grass; vessel body is a holdout
  body_<key>.png     vessel body only (grass/soil are holdouts so they stay in front/inside)
                     key = concrete|sand|lava  -> rendered WHITE, tinted per colour in the browser
                     key = <colour-slug>       -> rendered in its real colour (patina, granite, ribs, pure)

Browser composite:  scene.jpg  ->  env  ->  body (tinted with 'multiply' + alpha mask)

Run:
  blender -b --factory-startup -P tools/blender/render_atelier.py -- --scenes tools/atelier_scenes.json
          [--only-scene zen] [--only-form egg] [--pct 100] [--samples 96]
"""
import sys, os, math, json, argparse
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.append(HERE)
import vessel_lib as vl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--scenes", default=os.path.join(ROOT, "tools", "atelier_scenes.json"))
ap.add_argument("--out", default=os.path.join(ROOT, ".tmp", "atelier_png"))
ap.add_argument("--only-scene", default="")
ap.add_argument("--only-form", default="")
ap.add_argument("--only-key", default="")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--pct", type=int, default=100)
A = ap.parse_args(argv)
A.out = os.path.abspath(A.out)   # Blender resolves relative render paths unpredictably
A.scenes = os.path.abspath(A.scenes)

CFG = json.load(open(A.scenes, encoding="utf-8"))
RES = tuple(CFG.get("resolution", [1600, 900]))
FORM_H = CFG.get("form_heights", {"balloon": .55, "highballoon": .7, "egg": .6, "talleg": .95, "bowl": .42, "box": .5})

# body variants: (key, finish, colour, alt)
TINT = [("concrete", "concrete", "#FFFFFF", None), ("sand", "sand", "#FFFFFF", None), ("lava", "lava", "#FFFFFF", None)]
DIRECT = []
for cid, c in vl.COLLECTIONS.items():
    if c["finish"] in ("patina", "granite", "ribs", "smooth"):
        for name, val in c["colors"].items():
            col, alt = (val if isinstance(val, tuple) else (val, None))
            DIRECT.append((f"{cid}-{name.lower().replace(' ', '-')}", c["finish"], col, alt))
VARIANTS = TINT + DIRECT


def avg_image_color(path):
    try:
        img = bpy.data.images.load(path, check_existing=True)
        px = img.pixels[:]  # linear float RGBA
        n = len(px) // 4; step = max(1, n // 4000)
        r = g = b = 0.0; k = 0
        for i in range(0, n, step):
            r += px[4 * i]; g += px[4 * i + 1]; b += px[4 * i + 2]; k += 1
        return (r / k, g / k, b / k), img
    except Exception as e:
        print("WARN bg image", path, e)
        return (.18, .17, .16), None


def setup_scene(sc_cfg):
    vl.clear_scene()
    sc = vl.setup_cycles(samples=A.samples, res=RES, pct=A.pct, transparent=True)
    # Lessons (2026-11-07): "Standard" at exposure 0 clips a WHITE tint-body to flat 1.0 under sun;
    # AgX avoids clipping but squashes the light/shadow ratio so vessels look flat after tinting.
    # => Standard (linear ratios) with a negative exposure for headroom, plus a darker floor bounce.
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = sc_cfg.get("exposure", -0.5)
    img_path = os.path.join(ROOT, sc_cfg["image"])
    avg, img = avg_image_color(img_path)
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    nt = world.node_tree; bg = nt.nodes["Background"]
    if img is not None and sc_cfg.get("image_light", True):
        # Use the scenery photo itself as (blurred) environment light: gives matching colour bounce + reflections
        tex = nt.nodes.new("ShaderNodeTexEnvironment"); tex.image = img
        tex.projection = "MIRROR_BALL" if sc_cfg.get("mirror_ball") else "EQUIRECTANGULAR"
        nt.links.new(tex.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs["Color"].default_value = (*avg, 1)
    bg.inputs["Strength"].default_value = sc_cfg.get("world_strength", 1.0)

    # camera: height h, level-ish; tilt derived from the horizon position in the photo
    cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    cam_d.lens = sc_cfg.get("lens", 50); cam_d.sensor_fit = "HORIZONTAL"; cam_d.sensor_width = 36
    vfov_half = math.atan((36 * RES[1] / RES[0]) / 2 / cam_d.lens)
    horizon = sc_cfg.get("horizon", .40)          # fraction from top
    tilt = math.atan((.5 - horizon) * 2 * math.tan(vfov_half))   # >0 = camera looks down
    h = sc_cfg.get("camera_height", 1.1)
    cam.location = (0, 0, h)
    cam.rotation_euler = (math.radians(90) - tilt, 0, 0)       # looking along +Y
    # vessel stands where the ray through the floor spot hits the ground
    sx, sy = sc_cfg.get("spot", [.5, .82])                     # image fractions (x from left, y from top)
    ndc_y = (.5 - sy) * 2 * math.tan(vfov_half)                # tan of angle above optical axis
    ang = tilt - math.atan(ndc_y)                              # angle below horizontal
    dist = h / math.tan(max(ang, math.radians(2)))
    hfov_half = math.atan(18 / cam_d.lens)
    x = (sx - .5) * 2 * math.tan(hfov_half) * dist / math.cos(ang) * math.cos(tilt)
    bz = sc_cfg.get("base_z", 0.0)                             # raised plinth (e.g. slate slab)
    spot = Vector((x, dist, bz))
    # floor = shadow catcher
    me = bpy.data.meshes.new("Floor"); s = 30
    me.from_pydata([(-s, -s, bz), (s, -s, bz), (s, s, bz), (-s, s, bz)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("Floor", me); sc.collection.objects.link(floor)
    floor.is_shadow_catcher = True
    fm = bpy.data.materials.new("FloorMat"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*[c * sc_cfg.get("floor_albedo", 0.25) for c in avg], 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    floor.data.materials.append(fm)
    # key light: sun matching the photo's light direction
    sun_d = bpy.data.lights.new("Sun", "SUN"); sun = bpy.data.objects.new("Sun", sun_d); sc.collection.objects.link(sun)
    az, el = map(math.radians, sc_cfg.get("sun", [-60, 25]))  # azimuth: 0 = from camera, -90 = from left
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sun_d.energy = sc_cfg.get("sun_strength", 3.0)
    sun_d.color = sc_cfg.get("sun_color", [1, .9, .78])
    sun_d.angle = math.radians(sc_cfg.get("sun_softness", 4))
    # optional soft fill from the camera side (lifts a backlit vessel's front; casts no shadow, so the
    # floor shadow direction from the photo is unchanged)
    if sc_cfg.get("fill", 0) > 0:
        fd = bpy.data.lights.new("Fill", "SUN"); fo = bpy.data.objects.new("Fill", fd); sc.collection.objects.link(fo)
        fdir = Vector((0.25, -1.0, 0.45)).normalized()
        fo.rotation_euler = (-fdir).to_track_quat("-Z", "Y").to_euler()
        fd.energy = sc_cfg["fill"]; fd.angle = math.radians(60)
        fd.color = sc_cfg.get("fill_color", [1, .97, .93])
        fd.use_shadow = False
        fo.visible_shadow = False
    return sc, spot


def render(sc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path, flush=True)


def parts(root):
    kids = [o for o in bpy.data.objects if o.parent == root]
    body = next(o for o in kids if o.name.endswith("_body"))
    rest = [o for o in kids if o is not body]
    return body, rest


for scn in CFG["scenes"]:
    if A.only_scene and scn["id"] != A.only_scene:
        continue
    for form in vl.FORMS:
        if A.only_form and form != A.only_form:
            continue
        out_dir = os.path.join(A.out, scn["id"], form)
        for vi, (key, finish, col, alt) in enumerate([("env", "concrete", "#8D8A84", None)] + VARIANTS):
            if A.only_key and key not in (A.only_key, "env"):
                continue
            path = os.path.join(out_dir, f"{key if key == 'env' else 'body_' + key}.png")
            if os.path.exists(path):
                continue
            sc, spot = setup_scene(scn)
            root = vl.build_vessel(form, height=FORM_H[form] * scn.get("scale", 1.0), finish=finish, color=col, alt=alt,
                                   location=spot, rotation_z=scn.get("vessel_rot", .4), plant="grass", name="V")
            body, rest = parts(root)
            floor = bpy.data.objects["Floor"]
            if key in ("concrete", "sand", "lava"):   # white tint-bodies: keep headroom for the shading
                sc.view_settings.exposure = scn.get("exposure", -0.5) + scn.get("tint_exposure", -0.6)
            if key == "env":
                body.is_holdout = True               # body cuts a hole; still casts its shadow
            else:
                for o in rest:
                    o.is_holdout = True              # grass/soil stay in env layer
                floor.visible_camera = False         # no second shadow; floor still bounces light
            render(sc, path)
print("DONE")
