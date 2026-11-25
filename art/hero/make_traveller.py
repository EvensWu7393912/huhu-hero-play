"""Run with Blender 3.6+ in background mode. Outputs an editable figure and two studio views."""

import math
import os
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

OUT = Path(bpy.path.abspath("//")) if "__file__" not in globals() else Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
figure = bpy.data.collections.new("TRAVELLER | poseable maquette")
studio = bpy.data.collections.new("STUDIO | presentation only")
scene.collection.children.link(figure)
scene.collection.children.link(studio)
parts = []


def srgb(hex_code):
    sr = [int(hex_code[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in sr) + (1,)


def mat(label, hex_code, texture=0.10, metal=0):
    m = bpy.data.materials.new(label)
    m.diffuse_color = srgb(hex_code)
    m.use_nodes = True
    n = m.node_tree.nodes
    bs = n.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = m.diffuse_color
    bs.inputs["Roughness"].default_value = 0.76
    bs.inputs["Metallic"].default_value = metal
    if texture:
        noise = n.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 145
        noise.inputs["Detail"].default_value = 2
        bump = n.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = texture
        bump.inputs["Distance"].default_value = 0.006
        m.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        m.node_tree.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    return m


skin = mat("Face | maple", "f1c599")
blush = mat("Cheeks | terracotta wash", "e9a28c")
hair = mat("Hair | warm charcoal", "282323")
hair2 = mat("Hair | umber planes", "302a29")
hair3 = mat("Hair | soft grain", "3a3230")
ink = mat("Eyes | espresso", "231c1b")
ivory = mat("Ivory | warm paper", "fff1d4")
fox = mat("Fox | burnt orange", "cf7234")
foxlit = mat("Fox | copper", "e58743")
earpink = mat("Ear lining | rose", "a75c4f")
coat = mat("Coat | chestnut", "805039")
edge = mat("Coat piping | dark leather", "573e31")
lapel = mat("Coat seams | nutmeg", "996547")
gold = mat("Scarf | golden ochre", "eeb44e")
gold2 = mat("Scarf folds | amber", "cc8a33")
goldhi = mat("Scarf weave | sun", "ffd079")
brass = mat("Buttons | old brass", "d5aa5b", 0.04, 0.23)
trouser = mat("Trousers | charcoal linen", "4a4540")
boot = mat("Boots | umber", "634632")
sole = mat("Soles | dark hide", "45362a")
welt = mat("Boot welt | oiled edge", "937251")


def put(obj, parent=None, collection=figure):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    if collection == figure:
        parts.append(obj)
    return obj


def joint(label, where, parent=None):
    ob = bpy.data.objects.new(label, None)
    ob.location = where
    put(ob, parent)
    ob.empty_display_type = "PLAIN_AXES"
    ob.empty_display_size = 0.095
    bpy.context.view_layer.update()
    return ob


def mesh(label, verts, faces, material, parent, smooth=False, secondary=None):
    center = sum((Vector(v) for v in verts), Vector((0, 0, 0))) / len(verts)
    data = bpy.data.meshes.new(label)
    data.from_pydata([Vector(v) - center for v in verts], [], faces)
    data.update()
    if len(faces) > 2:
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(data)
        bm.free()
    ob = bpy.data.objects.new(label, data)
    ob.location = center
    put(ob, parent)
    ob.data.materials.append(material)
    if secondary:
        ob.data.materials.append(secondary)
    for poly in data.polygons:
        poly.use_smooth = smooth
    return ob


round_forms = {}


def ell(label, center, scale, material, parent, rot=(0, 0, 0), sm=True):
    # Repeated small fittings can share their unit mesh; each has its own transform.
    key = (material.name, sm)
    if key in round_forms:
        ob = bpy.data.objects.new(label, round_forms[key])
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=16)
        ob = bpy.context.object
        ob.name = label
        ob.data.materials.append(material)
        for face in ob.data.polygons:
            face.use_smooth = sm
        round_forms[key] = ob.data
    ob.location = center
    ob.scale = scale
    ob.rotation_euler = rot
    put(ob, parent)
    return ob


def closed_loft(label, rings, material, parent, sides=32, exponent=1.0):
    verts = []
    faces = []
    for z, cx, cy, rx, ry in rings:
        for i in range(sides):
            a = 2 * math.pi * i / sides
            c, s = math.cos(a), math.sin(a)
            verts.append(
                (
                    cx + rx * math.copysign(abs(c) ** exponent, c),
                    cy + ry * math.copysign(abs(s) ** exponent, s),
                    z,
                )
            )
    for j in range(len(rings) - 1):
        for i in range(sides):
            k = j * sides + i
            nexti = j * sides + (i + 1) % sides
            faces.append((k, nexti, nexti + sides, k + sides))
    faces.extend(
        [tuple(range(sides - 1, -1, -1)), tuple(range((len(rings) - 1) * sides, len(rings) * sides))]
    )
    return mesh(label, verts, faces, material, parent, True)


def filament(label, coords, radius, material, parent):
    # Bevel around a three-dimensional Bezier spine; keep the curve editable.
    curve = bpy.data.curves.new(label, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 6
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(coords) - 1)
    for pt, co in zip(spline.bezier_points, coords):
        pt.co = co[:3]
        pt.handle_left_type = "AUTO"
        pt.handle_right_type = "AUTO"
        if len(co) > 3:
            pt.radius = co[3]
    obj = bpy.data.objects.new(label, curve)
    put(obj, parent)
    curve.materials.append(material)
    return obj


def blade(label, spine, widthdir, normal, material, parent, second=None):
    # Model folded locks, coat panels and cloth as tapered, double-sided ribbons.
    v = []
    f = []
    vec = Vector(widthdir).normalized()
    n = Vector(normal).normalized()
    for x, y, z, half, thick in spine:
        c = Vector((x, y, z))
        v.extend([c - vec * half, c + n * thick, c + vec * half, c - n * max(0.008, thick * 0.45)])
    for j in range(len(spine) - 1):
        for i in range(4):
            f.append((4 * j + i, 4 * j + (i + 1) % 4, 4 * j + (i + 1) % 4 + 4, 4 * j + i + 4))
    f.extend([(3, 2, 1, 0), tuple(range(len(v) - 4, len(v)))])
    ob = mesh(label, v, f, material, parent, True, second)
    if second:
        for p in ob.data.polygons:
            if p.index % 4 == 1:
                p.material_index = 1
    return ob


def tube(label, spine, material, parent, cream=None, split=99, sides=14):
    v = []
    faces = []
    coords = [Vector(p[:3]) for p in spine]
    for j, (center, p) in enumerate(zip(coords, spine)):
        direction = (coords[min(j + 1, len(coords) - 1)] - coords[max(j - 1, 0)]).normalized()
        axis = direction.cross(Vector((0, 0, 1)))
        if axis.length < 0.01:
            axis = Vector((1, 0, 0))
        axis.normalize()
        up = direction.cross(axis).normalized()
        for i in range(sides):
            a = 2 * math.pi * i / sides
            v.append(center + p[3] * math.cos(a) * axis + p[4] * math.sin(a) * up)
    for j in range(len(coords) - 1):
        for i in range(sides):
            faces.append(
                (
                    j * sides + i,
                    j * sides + (i + 1) % sides,
                    (j + 1) * sides + (i + 1) % sides,
                    (j + 1) * sides + i,
                )
            )
    faces.extend([tuple(reversed(range(sides))), tuple(range(len(v) - sides, len(v)))])
    ob = mesh(label, v, faces, material, parent, True, cream)
    if cream:
        for poly in ob.data.polygons:
            if split * sides <= poly.index < (len(coords) - 1) * sides or poly.index == len(faces) - 1:
                poly.material_index = 1
    return ob


root = joint("00 · Traveller", (0, 0, 0))
hips = joint("01 · Hips", (0, 0.02, 0.84), root)
chest = joint("02 · Chest", (0, 0.02, 1.15), hips)
head = joint("03 · Head", (0, 0, 1.79), chest)
foxroot = joint("04 · Sleeping fox", (0, 0.04, 2.87), head)
scarf = joint("05 · Scarf", (0, 0.14, 1.76), chest)
for sign, suffix in [(-1, "L"), (1, "R")]:
    x = sign * 0.196
    leg = joint("Leg." + suffix, (x, 0.02, 0.86), hips)
    foot = joint("Boot." + suffix, (x, 0.02, 0.36), leg)
    closed_loft(
        "Trouser leg." + suffix,
        [
            (0.39, x, 0.018, 0.098, 0.091),
            (0.46, x, 0.020, 0.109, 0.105),
            (0.495, x, 0.020, 0.144, 0.139),
            (0.67, x, 0.02, 0.144, 0.159),
            (0.90, x, 0.02, 0.157, 0.152),
        ],
        trouser,
        leg,
    )
    closed_loft(
        "Leather upper." + suffix,
        [
            (0.07, x, -0.05, 0.148, 0.203),
            (0.115, x, -0.07, 0.157, 0.225),
            (0.175, x, -0.047, 0.15, 0.202),
            (0.235, x, -0.005, 0.121, 0.14),
            (0.375, x, 0.023, 0.122, 0.129),
            (0.444, x, 0.026, 0.139, 0.141),
            (0.459, x, 0.025, 0.135, 0.14),
        ],
        boot,
        foot,
        32,
        0.79,
    )
    closed_loft(
        "Stacked sole." + suffix,
        [
            (0.025, x, -0.07, 0.149, 0.216),
            (0.04, x, -0.07, 0.16, 0.226),
            (0.079, x, -0.07, 0.16, 0.225),
            (0.09, x, -0.07, 0.154, 0.218),
        ],
        sole,
        foot,
        32,
        0.77,
    )
    closed_loft(
        "Boot welt." + suffix,
        [(0.077, x, -0.07, 0.158, 0.223), (0.092, x, -0.07, 0.158, 0.223)],
        welt,
        foot,
        32,
        0.77,
    )
    closed_loft(
        "Rolled boot cuff." + suffix,
        [(0.406, x, 0.023, 0.14, 0.14), (0.424, x, 0.025, 0.147, 0.148), (0.465, x, 0.025, 0.144, 0.145)],
        boot,
        foot,
        32,
        0.81,
    )
    for j in range(2):
        z = 0.205 + j * 0.061
        filament(
            "Boot tie." + suffix + str(j),
            [(x - 0.08, -0.123, z + 0.009), (x, -0.153, z), (x + 0.08, -0.123, z + 0.011)],
            0.009,
            welt,
            foot,
        )

closed_loft(
    "A-line travelling coat",
    [
        (0.70, 0, 0.025, 0.39, 0.25),
        (0.73, 0, 0.025, 0.406, 0.258),
        (0.83, 0, 0.024, 0.405, 0.248),
        (1.16, 0, 0.035, 0.332, 0.242),
        (1.42, 0, 0.036, 0.327, 0.235),
        (1.59, 0, 0.032, 0.385, 0.208),
        (1.68, 0, 0.017, 0.312, 0.175),
        (1.72, 0, 0.01, 0.222, 0.145),
    ],
    coat,
    chest,
    40,
    0.90,
)
filament(
    "Coat hem",
    [
        (0.385 * math.cos(t * math.pi / 12), 0.023 + 0.252 * math.sin(t * math.pi / 12), 0.737)
        for t in range(25)
    ],
    0.012,
    edge,
    chest,
)
filament(
    "Front placket",
    [
        (0.03, -0.225, 0.735),
        (0.023, -0.223, 0.89),
        (0.012, -0.209, 1.15),
        (0.003, -0.200, 1.42),
        (0, -0.178, 1.6),
    ],
    0.015,
    edge,
    chest,
)
for z, y in [(0.87, -0.23), (1.10, -0.217), (1.34, -0.205), (1.51, -0.194)]:
    ell("Hammered brass button", (0.055, y - 0.018, z), (0.039, 0.019, 0.039), brass, chest)
    for dx in [-0.009, 0.009]:
        ell("Button recess", (0.055 + dx, y - 0.035, z), (0.0035, 0.0025, 0.005), edge, chest)
for sign, suffix in [(-1, "L"), (1, "R")]:
    x = sign * 0.245
    filament(
        "Pocket welt." + suffix,
        [(x - sign * 0.05, -0.193, 0.971), (x, -0.177, 1.006), (x + sign * 0.05, -0.141, 1.042)],
        0.016,
        lapel,
        chest,
    )
    shoulder = joint("Arm." + suffix, (sign * 0.31, 0.02, 1.54), chest)
    hand = joint("Hand." + suffix, (sign * 0.446, -0.071, 0.935), shoulder)
    closed_loft(
        "Coat sleeve." + suffix,
        [
            (0.932, sign * 0.448, -0.065, 0.108, 0.118),
            (0.966, sign * 0.446, -0.060, 0.128, 0.132),
            (1.13, sign * 0.431, -0.033, 0.124, 0.134),
            (1.36, sign * 0.399, 0.0, 0.125, 0.144),
            (1.50, sign * 0.361, 0.014, 0.137, 0.147),
            (1.585, sign * 0.327, 0.023, 0.138, 0.13),
            (1.617, sign * 0.309, 0.019, 0.080, 0.081),
        ],
        coat,
        shoulder,
    )
    closed_loft(
        "Cuff seam." + suffix,
        [
            (0.944, sign * 0.448, -0.063, 0.122, 0.126),
            (0.962, sign * 0.447, -0.062, 0.129, 0.132),
            (0.977, sign * 0.446, -0.060, 0.129, 0.13),
        ],
        edge,
        shoulder,
    )
    closed_loft(
        "Mitten fingers." + suffix,
        [
            (0.805, sign * 0.448, -0.078, 0.045, 0.058),
            (0.83, sign * 0.449, -0.082, 0.082, 0.082),
            (0.89, sign * 0.45, -0.079, 0.094, 0.092),
            (0.954, sign * 0.448, -0.069, 0.087, 0.087),
        ],
        skin,
        hand,
        28,
    )
    ell(
        "Thumb." + suffix,
        (sign * 0.399, -0.127, 0.893),
        (0.049, 0.055, 0.068),
        skin,
        hand,
        rot=(0.14, sign * 0.23, 0),
    )
# Scarf wraps and wind-lifted tail. The central fold and woven edge are modeled.
closed_loft(
    "Scarf | neck wrap",
    [
        (1.625, 0, 0.012, 0.282, 0.198),
        (1.66, 0, -0.004, 0.34, 0.212),
        (1.72, 0, -0.002, 0.344, 0.22),
        (1.789, 0, 0.006, 0.307, 0.207),
        (1.827, 0, 0.009, 0.269, 0.172),
    ],
    gold,
    scarf,
    44,
)
filament(
    "Scarf | rolled front fold",
    [
        (-0.316, -0.065, 1.73),
        (-0.18, -0.194, 1.695),
        (0.029, -0.219, 1.705),
        (0.20, -0.179, 1.75),
        (0.305, -0.092, 1.78),
    ],
    0.019,
    goldhi,
    scarf,
)
ell("Scarf | knot", (-0.223, 0.132, 1.748), (0.158, 0.144, 0.13), gold2, scarf, rot=(0.3, -0.1, -0.12))
# Cloth crosses a gently twisting midline; unequal final points form a forked hem.
stops = [
    (-0.21, 0.18, 1.76, 0.03),
    (-0.35, 0.285, 1.70, 0.098),
    (-0.59, 0.346, 1.52, 0.143),
    (-0.80, 0.388, 1.43, 0.151),
    (-0.99, 0.456, 1.40, 0.146),
    (-1.15, 0.522, 1.29, 0.135),
]
v = []
faces = []
for i, (x, y, z, w) in enumerate(stops):
    v.extend([(x + 0.12 * w, y - 0.20 * w, z + w), (x, y + 0.039, z), (x - 0.12 * w, y + 0.22 * w, z - w)])
for i in range(len(stops) - 1):
    k = 3 * i
    faces.extend([(k, k + 3, k + 4, k + 1), (k + 1, k + 4, k + 5, k + 2)])
v.extend([(-1.255, 0.552, 1.39), (-1.195, 0.562, 1.275), (-1.26, 0.57, 1.173)])
a = len(v) - 3
b = a - 3
faces.extend([(b, a, a + 1, b + 1), (b + 1, a + 1, a + 2, b + 2)])
cloth = mesh("Scarf | folded broad streamer", v, faces, gold, scarf, True, gold2)
for polygon in cloth.data.polygons:
    if polygon.index % 2:
        polygon.material_index = 1
sol = cloth.modifiers.new("Woven cloth thickness", "SOLIDIFY")
sol.thickness = 0.019
for off in [0.72, -0.78]:
    coords = [(x, y + (0.012 if off > 0 else 0.026), z + off * w) for x, y, z, w in stops[1:]]
    filament("Scarf | woven selvedge", coords, 0.008, goldhi, scarf)
blade(
    "Scarf | shorter trailing end",
    [
        (-0.20, 0.18, 1.76, 0.035, 0.008),
        (-0.41, 0.30, 1.61, 0.082, 0.018),
        (-0.62, 0.39, 1.43, 0.092, 0.015),
        (-0.78, 0.47, 1.24, 0.067, 0.013),
        (-0.84, 0.51, 1.15, 0.014, 0.004),
    ],
    (0.25, 0.03, 1),
    (0, 1, -0.1),
    gold2,
    scarf,
    gold,
)
face_mesh = closed_loft(
    "Head | carved face",
    [
        (1.794, 0, -0.03, 0.18, 0.17),
        (1.84, 0, -0.053, 0.268, 0.240),
        (1.93, 0, -0.047, 0.383, 0.322),
        (2.065, 0, -0.033, 0.478, 0.381),
        (2.25, 0, -0.010, 0.531, 0.416),
        (2.42, 0, 0.014, 0.536, 0.433),
        (2.59, 0, 0.031, 0.487, 0.409),
        (2.735, 0, 0.045, 0.381, 0.347),
        (2.833, 0, 0.06, 0.246, 0.238),
        (2.873, 0, 0.065, 0.116, 0.132),
    ],
    skin,
    head,
    48,
)
for sign, suffix in [(-1, "L"), (1, "R")]:
    ell(
        "Ear." + suffix,
        (sign * 0.513, -0.014, 2.177),
        (0.108, 0.102, 0.144),
        skin,
        head,
        rot=(0.20, sign * 0.17, 0),
    )
    ell(
        "Inner ear." + suffix,
        (sign * 0.563, -0.084, 2.18),
        (0.045, 0.039, 0.078),
        blush,
        head,
        rot=(0.20, sign * 0.17, 0),
    )
    yy = -0.403
    xx = sign * 0.204
    ell(
        "Ink eye." + suffix,
        (xx, yy, 2.284),
        (0.068, 0.027, 0.112),
        ink,
        head,
        rot=(0, sign * 0.03, sign * 0.29),
    )
    ell("Catchlight." + suffix, (xx - 0.013, yy - 0.025, 2.325), (0.015, 0.008, 0.019), ivory, head)
    # A conforming paint patch keeps the colour on the face in both profiles.
    cheek_points = []
    cheek_faces = []
    segments = 26
    for ring in range(3):
        count = 1 if ring == 0 else segments
        radius = ring / 2
        for k in range(count):
            angle = k * 2 * math.pi / count
            x = sign * 0.339 + radius * 0.075 * math.cos(angle)
            z = 2.119 + radius * 0.055 * math.sin(angle)
            origin = Vector((x, -2, z)) - face_mesh.location
            hit, point, normal, _ = face_mesh.ray_cast(origin, Vector((0, 1, 0)))
            if not hit:
                raise RuntimeError("Cheek lies outside face")
            cheek_points.append(point + face_mesh.location + normal * 0.003)
    for k in range(segments):
        a, b = k + 1, 1 + (k + 1) % segments
        cheek_faces.extend([(0, a, b), (a, a + segments, b + segments, b)])
    mesh("Painted cheek." + suffix, cheek_points, cheek_faces, blush, head, True)
    filament(
        "Eyebrow." + suffix,
        [
            (sign * 0.137, -0.399, 2.427, 0.45),
            (sign * 0.202, -0.39, 2.447, 1),
            (sign * 0.256, -0.36, 2.436, 0.34),
        ],
        0.015,
        hair2,
        head,
    )
ell("Nose | carved notch", (0, -0.414, 2.166), (0.044, 0.045, 0.044), skin, head)
filament(
    "Quiet smile",
    [
        (-0.048, -0.416, 2.059, 0.2),
        (-0.021, -0.417, 2.052, 0.8),
        (0.009, -0.417, 2.052, 0.8),
        (0.042, -0.416, 2.060, 0.25),
    ],
    0.0075,
    edge,
    head,
)
# Sculpted cap whose hairline rises over the face and drops around the nape.
verts = []
faces = []
sides = 64
levels = 16
for j in range(levels + 1):
    for i in range(sides):
        a = 2 * math.pi * i / sides
        front = (1 - math.sin(a)) / 2
        limit = 2.28 - 0.88 * (front**2.15) + 0.040 * math.sin(5 * a)
        t = 0.027 + (limit - 0.027) * j / levels
        verts.append(
            (
                0.555 * math.sin(t) * math.cos(a),
                0.051 + 0.464 * math.sin(t) * math.sin(a),
                2.396 + 0.536 * math.cos(t),
            )
        )
for j in range(levels):
    for i in range(sides):
        k = j * sides + i
        n = j * sides + (i + 1) % sides
        faces.append((k, k + sides, n + sides, n))
faces.extend([tuple(range(sides)), tuple(reversed(range(levels * sides, (levels + 1) * sides)))])
mesh("Hair | cut cap", verts, faces, hair, head, True)
# Asymmetric fringe with shallow central ridges; the locks follow the forehead to the temples.
for name, points, widths, tone in [
    (
        "Outer left",
        [(-0.14, -0.15, 2.867), (-0.32, -0.28, 2.745), (-0.445, -0.27, 2.54), (-0.495, -0.225, 2.285)],
        [0.065, 0.124, 0.097, 0.008],
        hair2,
    ),
    (
        "Temple left",
        [(-0.24, -0.14, 2.80), (-0.427, -0.207, 2.62), (-0.50, -0.17, 2.39), (-0.475, -0.17, 2.18)],
        [0.08, 0.105, 0.083, 0.008],
        hair,
    ),
    (
        "Sweep left",
        [(0.072, -0.17, 2.889), (-0.067, -0.362, 2.735), (-0.194, -0.416, 2.591), (-0.334, -0.373, 2.42)],
        [0.04, 0.153, 0.126, 0.005],
        hair2,
    ),
    (
        "Sweep centre",
        [(0.240, -0.166, 2.858), (0.124, -0.355, 2.695), (0.028, -0.435, 2.565), (-0.112, -0.412, 2.392)],
        [0.042, 0.118, 0.094, 0.005],
        hair,
    ),
    (
        "Part right",
        [(0.226, -0.162, 2.86), (0.315, -0.31, 2.696), (0.334, -0.365, 2.566), (0.283, -0.379, 2.447)],
        [0.052, 0.094, 0.072, 0.005],
        hair2,
    ),
    (
        "Right temple",
        [(0.278, -0.124, 2.84), (0.434, -0.218, 2.63), (0.502, -0.161, 2.435), (0.478, -0.205, 2.304)],
        [0.034, 0.10, 0.080, 0.004],
        hair,
    ),
]:
    blade(
        "Hair | " + name,
        [(*pt, w, 0.012 + w * 0.24) for pt, w in zip(points, widths)],
        (0.99, 0.02, 0.13),
        (0, -1, 0.10),
        tone,
        head,
        hair if tone == hair2 else hair2,
    )
# Layered pointed locks around the back and sides. Tapered silhouettes read in profile.
for j in range(10):
    a = -0.12 + j * (math.pi + 0.24) / 9
    cs = math.cos(a)
    sn = math.sin(a)
    h = 0.04 * math.cos(j * 2.6)
    points = [
        (0.44 * cs, 0.06 + 0.36 * sn, 2.66, 0.088, 0.025),
        (0.541 * cs, 0.07 + 0.433 * sn, 2.45, 0.13, 0.032),
        (0.552 * cs, 0.11 + 0.435 * sn, 2.26 + h, 0.111, 0.032),
        (0.515 * cs, 0.17 + 0.426 * sn, 2.076 + h, 0.064, 0.022),
        (0.478 * cs - 0.055, 0.227 + 0.42 * sn, 1.998 + h, 0.004, 0.004),
    ]
    blade("Hair | nape lock %02d" % j, points, (-sn, cs, 0), (cs, sn, 0), hair2 if j % 3 == 0 else hair, head)
# Resting fox: lofted body, compact tapered muzzle, folded feet and a wrapped two-colour brush.
ell(
    "Fox | curled back", (-0.115, 0.072, 2.979), (0.385, 0.260, 0.22), fox, foxroot, rot=(0.09, -0.065, -0.14)
)
ell("Fox | shoulder", (0.149, -0.008, 2.982), (0.246, 0.213, 0.182), foxlit, foxroot)
for x, y in [(0.106, -0.235), (0.304, -0.15)]:
    ell("Fox | tucked paw", (x, y, 2.845), (0.109, 0.095, 0.054), foxlit, foxroot, rot=(0, -0.08, -0.34))
    ell("Fox | pale toes", (x + 0.024, y - 0.049, 2.839), (0.065, 0.058, 0.032), ivory, foxroot)
closed_loft(
    "Fox | sculpted mask",
    [
        (2.863, 0.27, -0.130, 0.095, 0.110),
        (2.895, 0.27, -0.14, 0.18, 0.15),
        (2.976, 0.268, -0.133, 0.232, 0.176),
        (3.069, 0.254, -0.100, 0.237, 0.18),
        (3.144, 0.248, -0.076, 0.199, 0.157),
        (3.185, 0.241, -0.064, 0.103, 0.103),
    ],
    foxlit,
    foxroot,
    36,
    0.93,
)
for sign in [-1, 1]:
    ell(
        "Fox | ivory cheek",
        (0.275 + sign * 0.088, -0.244, 2.955),
        (0.108, 0.109, 0.059),
        ivory,
        foxroot,
        rot=(0, sign * 0.18, sign * -0.10),
    )
ell("Fox | muzzle", (0.275, -0.307, 2.962), (0.079, 0.094, 0.056), ivory, foxroot, rot=(-0.10, 0, 0))
ell("Fox | nose", (0.275, -0.379, 2.983), (0.042, 0.030, 0.027), ink, foxroot)
for sign in [-1, 1]:
    x = 0.26 + sign * 0.103
    filament(
        "Fox | closed eye",
        [
            (x - sign * 0.035, -0.305, 3.027, 0.28),
            (x, -0.313, 3.013, 1),
            (x + sign * 0.036, -0.291, 3.02, 0.34),
        ],
        0.011,
        ink,
        foxroot,
    )
    bx = 0.244 + sign * 0.133
    outer = [
        (bx - sign * 0.091, -0.125, 3.102),
        (bx + sign * 0.098, -0.090, 3.101),
        (bx + sign * 0.073, -0.038, 3.347),
        (bx - sign * 0.052, 0.034, 3.099),
        (bx + sign * 0.09, 0.047, 3.108),
    ]
    mesh(
        "Fox | pointed ear",
        outer,
        [(0, 1, 2), (1, 4, 2), (4, 3, 2), (3, 0, 2), (0, 3, 4, 1)],
        foxlit,
        foxroot,
    )
    mesh(
        "Fox | ear lining",
        [
            (bx - sign * 0.047, -0.128, 3.12),
            (bx + sign * 0.067, -0.102, 3.123),
            (bx + sign * 0.060, -0.067, 3.285),
        ],
        [(0, 1, 2)],
        earpink,
        foxroot,
    )
tube(
    "Fox | curled brush",
    [
        (0.076, 0.183, 3.0, 0.043, 0.059),
        (-0.10, 0.254, 3.012, 0.085, 0.125),
        (-0.29, 0.23, 2.996, 0.122, 0.148),
        (-0.437, 0.113, 2.952, 0.134, 0.141),
        (-0.461, -0.033, 2.914, 0.124, 0.12),
        (-0.404, -0.159, 2.893, 0.111, 0.103),
        (-0.321, -0.221, 2.885, 0.086, 0.085),
        (-0.233, -0.233, 2.906, 0.050, 0.055),
        (-0.173, -0.223, 2.929, 0.007, 0.012),
    ],
    fox,
    foxroot,
    ivory,
    5,
    20,
)
for j in range(3):
    filament(
        "Fox | shoulder carving",
        [
            (-0.24 + j * 0.08, -0.14, 3.135, 0.15),
            (-0.19 + j * 0.08, -0.151, 3.105, 0.68),
            (-0.145 + j * 0.08, -0.163, 3.107, 0.15),
        ],
        0.007,
        foxlit,
        foxroot,
    )


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(label, position, target, scale):
    data = bpy.data.cameras.new(label)
    obj = bpy.data.objects.new(label, data)
    put(obj, collection=studio)
    obj.location = position
    aim(obj, target)
    data.type = "ORTHO"
    data.ortho_scale = scale
    return obj


def lamp(label, xyz, color, energy, size, target):
    data = bpy.data.lights.new(label, "AREA")
    obj = bpy.data.objects.new(label, data)
    put(obj, collection=studio)
    obj.location = xyz
    aim(obj, target)
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size


lamp("Softbox | warm key", (-3.7, -5.2, 6.4), (1, 0.90, 0.78), 395, 4.4, (0, 0, 1.6))
lamp("Softbox | frontal fill", (3, -3.2, 4.6), (0.83, 0.91, 1), 270, 3.6, (0, 0, 1.85))
lamp("Softbox | back rim", (2.8, 3.3, 5.2), (1, 0.87, 0.62), 440, 3.7, (0, 0, 2.12))
world = bpy.data.worlds.new("Studio | ambient")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.68, 0.71, 0.72, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.31
scene.world = world
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0.018))
floor = bpy.context.object
floor.name = "Studio | matte sweep"
put(floor, collection=studio)
floor.data.materials.append(mat("Sweep | sage grey", "b4bcb0", 0))
front = camera("Camera | traveller and fox", (-2.46, -8.4, 3.76), (-0.16, -0.02, 1.69), 3.91)
side = camera("Camera | profile", (-7.4, -1.88, 3.47), (-0.16, 0.03, 1.68), 3.91)
scene.camera = front
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.render.threads_mode = "FIXED"
scene.render.threads = 5
scene.render.resolution_x = 740
scene.render.resolution_y = 840
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = False
scene.render.image_settings.compression = 20
# Save a camera-framed material-color solid view for opening the .blend without rendered mode.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_rotation = front.rotation_euler.to_quaternion()
            space.region_3d.view_location = (-0.16, 0, 1.67)
            space.region_3d.view_distance = 5.35
            space.region_3d.view_perspective = "ORTHO"
            space.shading.color_type = "MATERIAL"
            space.shading.light = "STUDIO"
            space.shading.show_shadows = True
            space.shading.show_cavity = True
            space.overlay.show_overlays = False
draft = os.getenv("HUHU_VIEW_DRAFT") == "1"
scene.cycles.samples = 10 if draft else 32
scene.render.resolution_percentage = 55 if draft else 100
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = root
bpy.context.preferences.filepaths.save_version = 0
if not draft:
    for obj in parts:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUT / "traveller.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
    )
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    scene.render.filepath = "//traveller-front.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "traveller.blend"), compress=True)
for cam, tag in [(front, "front"), (side, "profile")]:
    scene.camera = cam
    scene.render.filepath = str(
        Path("/tmp") / ("huhu-draft-" + tag + ".png") if draft else OUT / ("traveller-" + tag + ".png")
    )
    bpy.ops.render.render(write_still=True)
