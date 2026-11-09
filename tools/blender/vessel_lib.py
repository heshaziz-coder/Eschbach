"""
ESCHBACH vessel library for Blender (5.x, headless-safe).

Builds the planter forms from the same normalized profiles the website uses
(FORMS in the prototype), as real lathed meshes with wall thickness, rounded
rim, soil and optional ornamental grass. Materials are procedural per
collection finish (Loft, Terra, Antique, Lava, Pure, Granite, Vertical Lines).

Import from a Blender script:
    import sys; sys.path.append(<tools/blender>)
    import vessel_lib as vl
    pot = vl.build_vessel("talleg", height=1.1, finish="concrete", color="#7B4B31")
"""
import math
import random
import bpy

# ---------------------------------------------------------------- data
# Same profiles as the website (v = 0 bottom .. 1 rim, r normalized to max).
FORMS = {
    "balloon":     {"aspect": .86, "pts": [[0, .7], [.1, .85], [.32, .98], [.52, 1], [.75, .9], [.92, .72], [1, .6]]},
    "highballoon": {"aspect": 1.18, "pts": [[0, .72], [.12, .87], [.38, 1], [.62, .97], [.84, .8], [1, .6]]},
    "egg":         {"aspect": 1.0, "pts": [[0, .74], [.12, .9], [.35, 1], [.6, .96], [.82, .78], [1, .5]]},
    "talleg":      {"aspect": 1.62, "pts": [[0, .8], [.18, .96], [.4, 1], [.66, .88], [.88, .64], [1, .48]]},
    "bowl":        {"aspect": .46, "pts": [[0, 1], [.18, .99], [.45, .92], [.75, .74], [1, .52]]},
    "box":         {"aspect": 1.0, "pts": [[0, 1], [1, 1]], "box": True},
}

COLLECTIONS = {
    "loft":     {"finish": "concrete", "colors": {"Off White": "#E4DFD4", "Light Grey": "#B8B5AE", "Concrete Grey": "#8D8A84",
                                                  "Rust Brown": "#7B4B31", "Lead Grey": "#5A5C5D", "Espresso Black": "#2C2825"}},
    "terra":    {"finish": "sand", "colors": {"Champagne White": "#E2D8C4", "Desert Beige": "#C2AC89", "Macchiato Grey": "#9B8F82",
                                              "Lead Grey": "#5E5F5E", "Black Sand": "#35322E", "Siena Red": "#8F402C"}},
    "antique":  {"finish": "patina", "colors": {"Antique Brown": ("#5E4532", "#2C2018"), "Copper Green": ("#587C6E", "#6A4D31"),
                                                "Bronze": ("#7D5D38", "#382817")}},
    "lava":     {"finish": "lava", "colors": {"Volcanic Black": "#2B2927", "Antique White": "#DBD4C5"}},
    "pure":     {"finish": "smooth", "colors": {"Santorin White": "#EFEEEA", "Onyx Black": "#1A1A1A"}},
    "granite":  {"finish": "granite", "colors": {"Granite Grey": "#6E6E6B"}},
    "vertical": {"finish": "ribs", "colors": {"Vertical White": "#EBE9E3"}},
    "empire":   {"finish": "concrete", "colors": {"Lead Grey": "#585A5A"}},
}


# ---------------------------------------------------------------- helpers
def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h, a=1.0):
    h = h.lstrip("#")
    return (srgb_to_lin(int(h[0:2], 16) / 255), srgb_to_lin(int(h[2:4], 16) / 255),
            srgb_to_lin(int(h[4:6], 16) / 255), a)


def sample_profile(pts, n):
    """Catmull-Rom sampling identical to the website's sampleProfile()."""
    out = []
    for i in range(n):
        v = i / (n - 1)
        s = 0
        while s < len(pts) - 2 and v > pts[s + 1][0]:
            s += 1
        p0 = pts[max(0, s - 1)]; p1 = pts[s]; p2 = pts[s + 1]; p3 = pts[min(len(pts) - 1, s + 2)]
        t = (v - p1[0]) / ((p2[0] - p1[0]) or 1); t2 = t * t; t3 = t2 * t
        out.append(.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                         + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3))
    return out


def link_obj(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def lathe_mesh(name, prof, segments, rib=None, phase=0.0):
    """Revolve a list of (r, z, is_outer) around Z. Points with r == 0 collapse to one vertex (fans)."""
    verts, faces, rings = [], [], []
    for (r, z, outer) in prof:
        if r <= 1e-6:
            rings.append([len(verts)]); verts.append((0.0, 0.0, z)); continue
        ring = []
        for k in range(segments):
            a = phase + 2 * math.pi * k / segments
            rr = r * (rib(a, z) if (rib and outer) else 1.0)
            ring.append(len(verts)); verts.append((rr * math.cos(a), rr * math.sin(a), z))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        if len(A) == 1 and len(B) == 1:
            continue
        if len(A) == 1:
            for k in range(segments):
                faces.append((A[0], B[(k + 1) % segments], B[k]))
        elif len(B) == 1:
            for k in range(segments):
                faces.append((A[k], A[(k + 1) % segments], B[0]))
        else:
            for k in range(segments):
                k1 = (k + 1) % segments
                faces.append((A[k], A[k1], B[k1], B[k]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(); me.update()
    return me


def set_smooth(me, smooth=True):
    me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
    me.update()


# ---------------------------------------------------------------- materials
import os as _os
LAVA_INVERT = _os.environ.get('LAVA_INVERT', '1') == '1'
def _nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (600, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-1200, 0)
    return nt, bsdf, tc


def _noise(nt, tc, scale, detail=6.0, rough=.55, loc=(-900, 0), coord="Object"):
    n = nt.nodes.new("ShaderNodeTexNoise"); n.location = loc
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    nt.links.new(tc.outputs[coord], n.inputs["Vector"])
    return n


def _voronoi(nt, tc, scale, loc=(-900, -300), feature="F1"):
    v = nt.nodes.new("ShaderNodeTexVoronoi"); v.location = loc
    v.feature = feature
    v.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], v.inputs["Vector"])
    return v


def _ramp(nt, src, stops, loc=(-600, 0)):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc
    cr = r.color_ramp
    cr.elements[0].position, cr.elements[0].color = stops[0][0], stops[0][1]
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], stops[-1][1]
    for pos, col in stops[1:-1]:
        e = cr.elements.new(pos); e.color = col
    nt.links.new(src, r.inputs["Fac"])
    return r


def _mix_color(nt, a, b, fac, loc=(-300, 200), blend="MIX"):
    m = nt.nodes.new("ShaderNodeMix"); m.location = loc
    m.data_type = "RGBA"; m.blend_type = blend
    if isinstance(fac, float):
        m.inputs["Factor"].default_value = fac
    else:
        nt.links.new(fac, m.inputs["Factor"])
    for sock, val in ((m.inputs[6], a), (m.inputs[7], b)):
        if isinstance(val, tuple):
            sock.default_value = val
        else:
            nt.links.new(val, sock)
    return m


def _bump(nt, height_src, strength, distance=.002, loc=(300, -300), normal_in=None):
    b = nt.nodes.new("ShaderNodeBump"); b.location = loc
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(height_src, b.inputs["Height"])
    if normal_in is not None:
        nt.links.new(normal_in, b.inputs["Normal"])
    return b


def _shade(rgba, k):
    return (rgba[0] * k, rgba[1] * k, rgba[2] * k, 1.0)


def make_material(finish, color, alt=None, name=None):
    """Procedural ESCHBACH surface. color/alt are hex strings (sRGB)."""
    mat = bpy.data.materials.new(name or f"ESB_{finish}_{color}")
    nt, bsdf, tc = _nodes(mat)
    base = hex_rgba(color)
    L = nt.links

    if finish == "concrete":          # Loft: cast-stone, soft mottling, tiny air pores
        mott = _noise(nt, tc, 3.5, 8, .6, (-900, 250))
        rmp = _ramp(nt, mott.outputs["Fac"], [(.3, _shade(base, .86)), (.7, _shade(base, 1.12))], (-600, 250))
        bsdf.inputs["Roughness"].default_value = .82
        L.new(rmp.outputs["Color"], bsdf.inputs["Base Color"])
        # sparse round air pores (cast stone); DISTANCE_TO_EDGE looked like crazing cracks in macro shots
        pores = _noise(nt, tc, 240, 2, .5, (-900, -300))
        prm = _ramp(nt, pores.outputs["Fac"], [(.64, (1, 1, 1, 1)), (.69, (0, 0, 0, 1))], (-600, -300))
        fine = _noise(nt, tc, 180, 4, .7, (-900, -650))
        add = nt.nodes.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"; add.location = (-300, -400)
        add.inputs[1].default_value = .35
        L.new(fine.outputs["Fac"], add.inputs[0]); L.new(prm.outputs["Color"], add.inputs[2])
        b = _bump(nt, add.outputs[0], .6, .0018)
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])

    elif finish == "sand":            # Terra: mineral sand grain
        mott = _noise(nt, tc, 6, 6, .55, (-900, 250))
        rmp = _ramp(nt, mott.outputs["Fac"], [(.35, _shade(base, .9)), (.65, _shade(base, 1.08))], (-600, 250))
        grain = _noise(nt, tc, 900, 2, .5, (-900, -250))
        gr = _ramp(nt, grain.outputs["Fac"], [(.4, (0, 0, 0, 1)), (.6, (1, 1, 1, 1))], (-600, -250))
        mix = _mix_color(nt, rmp.outputs["Color"], (base[0] * 1.25, base[1] * 1.25, base[2] * 1.25, 1), .0, (-300, 200))
        L.new(mix.outputs[2], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = .9
        b = _bump(nt, gr.outputs["Color"], .45, .0008)
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])

    elif finish == "patina":          # Antique: metallic-looking patina with darker oxide
        a2 = hex_rgba(alt or "#2C2018")
        big = _noise(nt, tc, 2.2, 10, .62, (-900, 250))
        rmp = _ramp(nt, big.outputs["Fac"], [(.38, a2), (.5, _shade(base, .9)), (.66, _shade(base, 1.18))], (-600, 250))
        L.new(rmp.outputs["Color"], bsdf.inputs["Base Color"])
        rr = _ramp(nt, big.outputs["Fac"], [(.38, (.75, .75, .75, 1)), (.66, (.38, .38, .38, 1))], (-600, 0))
        L.new(rr.outputs["Color"], bsdf.inputs["Roughness"])
        bsdf.inputs["Metallic"].default_value = .35
        fine = _noise(nt, tc, 60, 8, .6, (-900, -300))
        b = _bump(nt, fine.outputs["Fac"], .2, .001)
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])

    elif finish == "smooth":          # Pure: satin, clear-coated
        bsdf.inputs["Base Color"].default_value = base
        bsdf.inputs["Roughness"].default_value = .32
        bsdf.inputs["Coat Weight"].default_value = .35
        bsdf.inputs["Coat Roughness"].default_value = .12
        fine = _noise(nt, tc, 40, 3, .5, (-900, -300))
        b = _bump(nt, fine.outputs["Fac"], .03, .001)
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])

    elif finish == "lava":            # Lava: porous volcanic
        mott = _noise(nt, tc, 5, 6, .6, (-900, 250))
        rmp = _ramp(nt, mott.outputs["Fac"], [(.35, _shade(base, .85)), (.65, _shade(base, 1.1))], (-600, 250))
        L.new(rmp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = .88
        # dense volcanic pores; ramp inverted (white at the cell centre) - the first version read as raised beads
        pores = _voronoi(nt, tc, 115, (-900, -300), "F1")
        pores.inputs["Randomness"].default_value = 1.0
        prm = _ramp(nt, pores.outputs["Distance"], [(0., (1, 1, 1, 1)), (.3, (0, 0, 0, 1))], (-600, -300))
        b = _bump(nt, prm.outputs["Color"], .7, .003)
        b.invert = LAVA_INVERT
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])
        # pore floors darker (soot-dark cavities), keeps them reading as holes
        dk = _mix_color(nt, rmp.outputs["Color"], _shade(base, .35), prm.outputs["Color"], (-300, 250))
        L.new(dk.outputs[2], bsdf.inputs["Base Color"])

    elif finish == "granite":         # Granite: speckled stone
        sp1 = _noise(nt, tc, 420, 1, .5, (-900, 250))
        rmp = _ramp(nt, sp1.outputs["Fac"], [(.33, (0.012, 0.012, 0.012, 1)), (.36, _shade(base, .95)),
                                              (.64, _shade(base, 1.05)), (.67, (.75, .74, .72, 1))], (-600, 250))
        L.new(rmp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = .42
        b = _bump(nt, sp1.outputs["Fac"], .12, .0006)
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])

    elif finish == "ribs":            # Vertical Lines: ribs are geometry; surface like Pure-matte
        bsdf.inputs["Base Color"].default_value = base
        bsdf.inputs["Roughness"].default_value = .55
        fine = _noise(nt, tc, 140, 4, .6, (-900, -300))
        b = _bump(nt, fine.outputs["Fac"], .12, .0008)
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        raise ValueError(finish)
    return mat


def soil_material():
    mat = bpy.data.materials.new("ESB_soil")
    nt, bsdf, tc = _nodes(mat)
    n = _noise(nt, tc, 60, 8, .7)
    r = _ramp(nt, n.outputs["Fac"], [(.3, hex_rgba("#1b140f")), (.7, hex_rgba("#3a2a1e"))])
    nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = .95
    b = _bump(nt, n.outputs["Fac"], .9, .01)
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def grass_material(tint="#6d7a4a"):
    mat = bpy.data.materials.new("ESB_grass")
    nt, bsdf, tc = _nodes(mat)
    attr = nt.nodes.new("ShaderNodeAttribute"); attr.attribute_name = "blade_t"; attr.location = (-900, 0)
    r = _ramp(nt, attr.outputs["Fac"], [(0, hex_rgba("#2a331b")), (.5, hex_rgba(tint)), (1, hex_rgba("#cdbf93"))])
    rnd = nt.nodes.new("ShaderNodeAttribute"); rnd.attribute_name = "blade_r"; rnd.location = (-900, -250)
    r2 = _ramp(nt, rnd.outputs["Fac"], [(0, hex_rgba("#8a8a62")), (.5, hex_rgba("#ffffff")), (1, hex_rgba("#c8a86a"))], (-600, -250))
    m = _mix_color(nt, r.outputs["Color"], r2.outputs["Color"], 1.0, (-300, 0), "MULTIPLY")
    nt.links.new(m.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = .5
    bsdf.inputs["Subsurface Weight"].default_value = .0
    try:
        bsdf.inputs["Transmission Weight"].default_value = .18
    except KeyError:
        pass
    return mat


# ---------------------------------------------------------------- geometry
def vessel_profile(form, height, max_r, wall=.022, soil_depth=.09, n=120):
    """Return list of (r, z, is_outer) going: bottom centre -> outer wall -> rim -> inner wall -> inner floor."""
    f = FORMS[form]
    # The website profiles run v=0 at the RIM -> v=1 at the FOOT. Flip so index 0 = foot.
    prof = sample_profile(f["pts"], n)[::-1]
    P = []
    r0 = prof[0] * max_r
    foot = min(.012, height * .03)
    P.append((0.0, 0.0, False))
    # rounded bottom edge (small inset foot)
    for k in range(5):
        a = (math.pi / 2) * k / 4
        P.append((r0 - foot + foot * math.sin(a), foot - foot * math.cos(a), True))
    for i in range(1, n):
        v = i / (n - 1)
        z = v * height
        if z <= foot:
            continue
        P.append((prof[i] * max_r, z, True))
    rt = prof[-1] * max_r
    # rounded rim (outer -> inner)
    h2 = wall / 2
    for k in range(1, 9):
        a = math.pi * k / 8
        P.append((rt - h2 + h2 * math.cos(a), height + h2 * math.sin(a) * .9, False))
    # inner wall down to below the soil
    zs = height - soil_depth
    for i in range(n - 1, -1, -1):
        z = i / (n - 1) * height
        if z < zs - .04:
            break
        P.append((max(.001, prof[i] * max_r - wall), z, False))
    P.append((0.0, zs - .04, False))
    return P, zs, max(.001, sample_at(prof, zs / height) * max_r - wall)


def sample_at(prof, v):
    v = min(1, max(0, v)) * (len(prof) - 1)
    i = int(v); t = v - i
    return prof[i] if i >= len(prof) - 1 else prof[i] * (1 - t) + prof[i + 1] * t


def make_soil(name, radius, z, coll=None):
    segs, rings = 96, 14
    verts, faces = [(0, 0, z + .006)], []
    rnd = random.Random(7)
    for j in range(1, rings + 1):
        rr = radius * 1.02 * j / rings
        for k in range(segs):
            a = 2 * math.pi * k / segs
            dz = (rnd.random() - .5) * .006 * (1 - j / rings * .5)
            verts.append((rr * math.cos(a), rr * math.sin(a), z + dz + .004 * (1 - (j / rings) ** 2)))
    for k in range(segs):
        faces.append((0, 1 + k, 1 + (k + 1) % segs))
    for j in range(rings - 1):
        a0, a1 = 1 + j * segs, 1 + (j + 1) * segs
        for k in range(segs):
            k1 = (k + 1) % segs
            faces.append((a0 + k, a1 + k, a1 + k1, a0 + k1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); set_smooth(me)
    ob = bpy.data.objects.new(name, me); link_obj(ob, coll)
    ob.data.materials.append(soil_material())
    return ob


def make_grass(name, radius, z, height=.75, blades=1400, seed=3, tint="#6d7a4a", coll=None):
    """Ornamental grass (Pennisetum/Carex-like): fine, arching, tapered blades as mesh strips.
    Attributes: 'blade_t' (0 base .. 1 tip) and 'blade_r' (per-blade random, for colour variation)."""
    rnd = random.Random(seed)
    verts, faces, tvals, rvals = [], [], [], []
    SEG = 12
    for b in range(blades):
        ang = rnd.random() * 2 * math.pi
        rr = radius * math.sqrt(rnd.random()) * .8
        x0, y0 = rr * math.cos(ang), rr * math.sin(ang)
        out = ang + (rnd.random() - .5) * 1.1                 # lean direction
        rel = rr / radius
        lean = .15 + 1.05 * rel ** 1.3 + rnd.random() * .35    # outer blades arch and droop more
        L = height * (.6 + .6 * rnd.random()) * (1.1 - .3 * rel)
        w = .0028 + .0032 * rnd.random()
        twist = (rnd.random() - .5) * 2.4
        br = rnd.random()
        base_idx = len(verts)
        for s in range(SEG + 1):
            t = s / SEG
            # arch: rises, bends outward, tip droops (quadratic + cubic terms)
            h = L * (t - .55 * lean * t * t + .12 * lean * t ** 3)
            d = L * (.08 * t + .62 * lean * t * t)
            cx, cy, cz = x0 + d * math.cos(out), y0 + d * math.sin(out), z + h
            ww = w * (1 - t) ** .55 + .0003
            a2 = out + twist * t
            px, py = -math.sin(a2), math.cos(a2)
            verts.append((cx - px * ww, cy - py * ww, cz)); tvals.append(t); rvals.append(br)
            verts.append((cx + px * ww, cy + py * ww, cz)); tvals.append(t); rvals.append(br)
        for s in range(SEG):
            i = base_idx + 2 * s
            faces.append((i, i + 1, i + 3, i + 2))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); set_smooth(me)
    at = me.attributes.new("blade_t", "FLOAT", "POINT")
    at.data.foreach_set("value", tvals)
    at = me.attributes.new("blade_r", "FLOAT", "POINT")
    at.data.foreach_set("value", rvals)
    ob = bpy.data.objects.new(name, me); link_obj(ob, coll)
    ob.data.materials.append(grass_material(tint))
    return ob


def build_vessel(form="egg", height=.6, finish="concrete", color="#7B4B31", alt=None,
                 location=(0, 0, 0), rotation_z=0.0, plant=None, name=None, coll=None, segments=None):
    """Create a vessel (+ soil, + optional plant) parented to an empty. Returns the empty."""
    f = FORMS[form]
    name = name or f"Vessel_{form}"
    width = height / f["aspect"]
    is_box = f.get("box", False)
    if is_box:
        max_r = (width / 2) * math.sqrt(2)
        segs, phase = 4, math.pi / 4
    else:
        max_r = width / 2
        segs = segments or (384 if finish == "ribs" else 160)
        phase = 0.0
    prof, zs, rs = vessel_profile(form, height, max_r, wall=.022 if not is_box else .03)
    rib = None
    if finish == "ribs" and not is_box:
        N = 56
        def rib(a, z, N=N, H=height):
            fade = min(1, z / (H * .06)) * min(1, (H - z) / (H * .05))
            return 1 + .011 * fade * (abs(math.cos(N * a / 2)) ** .6 - .5)
    me = lathe_mesh(name + "_mesh", prof, segs, rib, phase)
    set_smooth(me, not is_box)
    body = bpy.data.objects.new(name + "_body", me)
    link_obj(body, coll)
    if is_box:
        bev = body.modifiers.new("Bevel", "BEVEL")
        bev.width = .012; bev.segments = 4; bev.limit_method = "ANGLE"
        bev.angle_limit = math.radians(40)
        bev.harden_normals = False
        set_smooth(me, True)
        try:
            sm = body.modifiers.new("Smooth", "NODES")
            sm.node_group = bpy.data.node_groups.get("Smooth by Angle")
            if sm.node_group is None:
                body.modifiers.remove(sm)
        except Exception:
            pass
    body.data.materials.append(make_material(finish, color, alt))

    root = bpy.data.objects.new(name, None)
    link_obj(root, coll)
    body.parent = root
    soil_r = rs if not is_box else (width / 2 - .03)
    soil = make_soil(name + "_soil", soil_r, zs, coll)
    if is_box:  # square soil: scale disc into box by clipping radius to inner square
        soil.scale = (1.0, 1.0, 1.0)
    soil.parent = root
    if plant == "grass":
        g = make_grass(name + "_grass", soil_r, zs, height=max(.42, height * .55), tint="#77804f", coll=coll)
        g.parent = root
    root.location = location
    root.rotation_euler = (0, 0, rotation_z)
    root["height"] = height
    root["width"] = width
    return root


# ---------------------------------------------------------------- render setup
def setup_cycles(samples=128, res=(1920, 1080), pct=100, gpu=True, transparent=False):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = pct
    sc.render.film_transparent = transparent
    cy = sc.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = .02
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    cy.max_bounces = 8
    cy.caustics_reflective = cy.caustics_refractive = False
    if gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "HIP"
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = (d.type == "HIP")
        cy.device = "GPU"
    vs = sc.view_settings
    try:
        vs.view_transform = "AgX"
        for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
            try:
                vs.look = look; break
            except TypeError:
                continue
    except TypeError:
        pass
    return sc


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for b in list(coll):
            coll.remove(b)
