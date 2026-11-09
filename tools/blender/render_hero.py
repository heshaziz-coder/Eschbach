"""
ESCHBACH scroll-hero: camera move through a dark showroom, light comes up on an XXL vessel.

Run (headless):
  blender -b --factory-startup -P tools/blender/render_hero.py -- [options]

Options:
  --out DIR          output folder for PNG frames (default .tmp/hero_png)
  --frames N         number of frames (default 150)
  --only i,j,k       render only these frame numbers (1-based) - for tests
  --samples N        Cycles samples (default 96)
  --pct P            resolution percentage (default 100 of 1920x1080)
  --save-blend PATH  also save the .blend
  --no-render        build scene only
"""
import sys, os, math, argparse
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)
import vessel_lib as vl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", ".tmp", "hero_png"))
ap.add_argument("--frames", type=int, default=150)
ap.add_argument("--only", default="")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--pct", type=int, default=100)
ap.add_argument("--save-blend", default="")
ap.add_argument("--no-render", action="store_true")
A = ap.parse_args(argv)

vl.clear_scene()
sc = vl.setup_cycles(samples=A.samples, pct=A.pct)
sc.frame_start, sc.frame_end = 1, A.frames


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def smooth(x): x = clamp(x); return x * x * (3 - 2 * x)
def ease_io(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def seg(t, a, b): return clamp((t - a) / (b - a))
def lerp(a, b, t): return a + (b - a) * t


# ---------------------------------------------------------------- world
world = bpy.data.worlds.new("World"); sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.0035, 0.0032, 0.0029, 1)
bg.inputs["Strength"].default_value = 1.0


# ---------------------------------------------------------------- room
def plane(name, size, loc, rot, mat):
    me = bpy.data.meshes.new(name)
    s = size
    me.from_pydata([(-s[0], -s[1], 0), (s[0], -s[1], 0), (s[0], s[1], 0), (-s[0], s[1], 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ob.location, ob.rotation_euler = loc, rot
    ob.data.materials.append(mat)
    return ob


def floor_mat():
    m = bpy.data.materials.new("Floor"); nt, bsdf, tc = vl._nodes(m)
    n = vl._noise(nt, tc, .9, 9, .62, (-900, 250))
    r = vl._ramp(nt, n.outputs["Fac"], [(.35, vl.hex_rgba("#1c1a17")), (.65, vl.hex_rgba("#2b2824"))], (-600, 250))
    nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
    rr = vl._ramp(nt, n.outputs["Fac"], [(.3, (.18, .18, .18, 1)), (.7, (.42, .42, .42, 1))], (-600, 0))
    nt.links.new(rr.outputs["Color"], bsdf.inputs["Roughness"])
    f = vl._noise(nt, tc, 220, 3, .6, (-900, -300))
    b = vl._bump(nt, f.outputs["Fac"], .06, .001); nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def wall_mat():
    """Dark lime-plaster wall with vertical fluting (reads as architectural, catches grazing light)."""
    m = bpy.data.materials.new("Wall"); nt, bsdf, tc = vl._nodes(m)
    n = vl._noise(nt, tc, 1.4, 10, .6, (-900, 250))
    r = vl._ramp(nt, n.outputs["Fac"], [(.3, vl.hex_rgba("#221f1b")), (.7, vl.hex_rgba("#34302a"))], (-600, 250))
    nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = .9
    wave = nt.nodes.new("ShaderNodeTexWave"); wave.location = (-900, -250)
    wave.wave_type = "BANDS"; wave.bands_direction = "X"; wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 3.2
    wave.inputs["Distortion"].default_value = 0
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    fine = vl._noise(nt, tc, 40, 6, .6, (-900, -550))
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"; mx.location = (-500, -400)
    mx.inputs[1].default_value = .15
    nt.links.new(fine.outputs["Fac"], mx.inputs[0]); nt.links.new(wave.outputs["Fac"], mx.inputs[2])
    b = vl._bump(nt, mx.outputs[0], .55, .012); nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


plane("Floor", (30, 30), (0, 0, 0), (0, 0, 0), floor_mat())
W = wall_mat()
# Back wall with a tall light slit: two wall panels with a gap at x in [-2.9, -2.3]
plane("WallL", (6, 4), (-8.9, 3.4, 4), (math.radians(90), 0, 0), W)
plane("WallR", (8.5, 4), (6.2, 3.4, 4), (math.radians(90), 0, 0), W)
plane("WallTop", (.5, 1.2), (-2.6, 3.4, 6.8), (math.radians(90), 0, 0), W)
# Side wall on the left (receives slit spill)
plane("WallSide", (12, 4), (-7.5, -3, 4), (math.radians(90), 0, math.radians(90)), W)

# ---------------------------------------------------------------- vessels
hero = vl.build_vessel("talleg", height=1.40, finish="concrete", color="#7B4B31",
                       location=(0, 0, 0), rotation_z=.3, plant="grass", name="Hero")
side1 = vl.build_vessel("balloon", height=.62, finish="concrete", color="#8D8A84",
                        location=(1.35, 1.05, 0), rotation_z=1.1, plant="grass", name="Balloon")
side2 = vl.build_vessel("bowl", height=.42, finish="lava", color="#2B2927",
                        location=(-1.2, 1.5, 0), rotation_z=2.0, name="Bowl")

# ---------------------------------------------------------------- lights
def area(name, loc, rot, size, color, energy, shape="RECTANGLE", size_y=None):
    ld = bpy.data.lights.new(name, "AREA"); ld.shape = shape
    ld.size = size; ld.size_y = size_y or size
    ld.color = color; ld.energy = energy
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot
    return ob


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# Key: warm daylight pouring through the wall slit (behind the wall, aimed at the vessel)
key = area("Key_Slit", (-4.6, 6.5, 5.6), (0, 0, 0), .5, (1.0, .78, .56), 0, "RECTANGLE", 5.5)
aim(key, (-.2, -.4, .7))
# Soft fill from the camera side, very low
fill = area("Fill", (2.5, -5.5, 2.8), (0, 0, 0), 4, (.85, .88, 1.0), 0)
aim(fill, (0, 0, .7))
# Cool rim from behind right: draws the silhouette in the dark opening
rim = area("Rim", (3.2, 3.0, 2.4), (0, 0, 0), 1.6, (.78, .86, 1.0), 0)
aim(rim, (0, 0, .9))
# Warm top spot (gallery downlight) for the final beat
spot_d = bpy.data.lights.new("Down", "SPOT"); spot_d.energy = 0; spot_d.spot_size = math.radians(38)
spot_d.spot_blend = .9; spot_d.shadow_soft_size = .25; spot_d.color = (1, .82, .62)
spot = bpy.data.objects.new("Down", spot_d); sc.collection.objects.link(spot)
spot.location = (1.6, -3.4, 4.4); aim(spot, (0, 0, .55))  # front-right, below the grass so no stripe shadows

# ---------------------------------------------------------------- camera
cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d)
sc.collection.objects.link(cam); sc.camera = cam
cam_d.sensor_width = 36
cam_d.dof.use_dof = True
cam_d.dof.aperture_fstop = 2.8

# Keyframe tracks:  t -> (azimuth deg, elevation deg, distance m, target z, lens mm, shift_x, fstop)
TRACK = [
    (0.00, (-14, 24, 8.0, .95, 40, .00, 5.6)),   # silhouette in the dark, centred
    (0.30, (-32, 15, 5.4, .95, 45, .00, 4.0)),   # light comes up, approach
    (0.56, (-74, 6, 2.6, 1.05, 70, .00, 2.2)),   # raking-light close-up: surface texture
    (0.70, (-62, 4, 2.0, 1.32, 85, .00, 1.8)),   # rim + grass
    (1.00, (30, 10, 6.2, 1.00, 50, -.21, 4.0)),  # pull back, vessel sits right for the headline
]
# Lights: t -> (key, fill, rim, down)
LIGHT = [
    (0.00, (0, 0, 120, 0)),
    (0.10, (0, 0, 160, 0)),
    (0.42, (5200, 20, 160, 0)),
    (0.74, (5200, 26, 120, 0)),
    (1.00, (4300, 110, 140, 1400)),
]


def sample_track(tr, t):
    for i in range(len(tr) - 1):
        a, b = tr[i], tr[i + 1]
        if a[0] <= t <= b[0]:
            u = ease_io((t - a[0]) / (b[0] - a[0]))
            return tuple(lerp(x, y, u) for x, y in zip(a[1], b[1]))
    return tr[-1][1]


def apply(t):
    az, el, dist, tz, lens, sx, fs = sample_track(TRACK, t)
    a, e = math.radians(az), math.radians(el)
    target = Vector((0, 0, tz))
    pos = target + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam_d.lens = lens; cam_d.shift_x = sx
    cam_d.dof.focus_distance = (pos - Vector((0, 0, tz))).length
    cam_d.dof.aperture_fstop = fs
    k, f, r, d = sample_track(LIGHT, t)
    key.data.energy, fill.data.energy, rim.data.energy, spot.data.energy = k, f, r, d
    # the hero vessel slowly turns (texture travels across the light)
    hero.rotation_euler[2] = .3 + 1.1 * ease_io(t)


for fr in range(1, A.frames + 1):
    t = (fr - 1) / max(1, A.frames - 1)
    apply(t)
    for ob, paths in ((cam, ("location", "rotation_euler")), (hero, ("rotation_euler",))):
        for p in paths:
            ob.keyframe_insert(p, frame=fr)
    for p in ("lens", "shift_x"):
        cam_d.keyframe_insert(p, frame=fr)
    cam_d.dof.keyframe_insert("focus_distance", frame=fr)
    cam_d.dof.keyframe_insert("aperture_fstop", frame=fr)
    for L in (key, fill, rim, spot):
        L.data.keyframe_insert("energy", frame=fr)

if A.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(A.save_blend))

if not A.no_render:
    out = os.path.abspath(A.out); os.makedirs(out, exist_ok=True)
    frames = [int(x) for x in A.only.split(",") if x.strip()] or list(range(1, A.frames + 1))
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    for fr in frames:
        path = os.path.join(out, f"hero_{fr:04d}.png")
        if os.path.exists(path) and not A.only:
            continue  # resumable
        sc.frame_set(fr)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED {fr}/{A.frames} -> {path}", flush=True)
