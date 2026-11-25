"""Bake the four Y-up Wavefront props into the game's transparent sprites.

Run with python3 art/weapons/render.py (Pillow and NumPy). Units are
illustrative: local origin is the hand; 1 model unit is 32 in-game pixels.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parents[1] / "assets"
# (canvas width, height, grip x, grip y) must match weapon-motion.js.
FRAMES = {
    "sword": (36, 96, 18, 21),
    "axe": (44, 104, 12, 81),
    "hammer": (50, 104, 23, 82),
    "spear": (35, 120, 6, 89),
}
SCALE = 6


def materials():
    colors = {}
    for line in (HERE / "forest.mtl").read_text().splitlines():
        if line.startswith("newmtl "):
            name = line.split()[1]
        elif line.startswith("Kd "):
            colors[name] = np.array(line.split()[1:], dtype=float) * 255
    return colors


def render(name, colors):
    width, height, gx, gy = FRAMES[name]
    w, h = width * SCALE, height * SCALE
    vertices = []
    depth = np.full((h, w), -np.inf)
    rgb = np.zeros((h, w, 3))
    yy, xx = np.mgrid[0:h, 0:w] + .5
    # One subdued, fixed paper grain. The face lighting remains readable
    # after resampling at the tiny in-game size.
    grain = np.random.default_rng(81).normal(0., 4., (h, w))
    fibers = 1.2 * np.sin((xx + yy * .27) * .45) + 1.4 * np.cos(yy * .37)
    light = np.array([-.52, .57, .64])

    for line in (HERE / (name + ".obj")).read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        kind, values = fields[0], fields[1:]
        if kind == "v":
            vertices.append([float(v) * 32 for v in values])
        elif kind == "usemtl":
            material = values[0]
        elif kind == "f":
            points = np.array([vertices[int(i) - 1] for i in values])
            x, y, z = points.T
            projected = np.stack(((gx + x + .12 * z) * SCALE,
                                  (gy - y - .09 * z) * SCALE, z), axis=1)
            normal = np.cross(projected[1] - projected[0], projected[2] - projected[0])
            if abs(normal[2]) < 1e-8:
                continue
            u, v, z0 = projected[0]
            face_depth = z0 - (normal[0] * (xx - u) + normal[1] * (yy - v)) / normal[2]
            mask = Image.new("1", (w, h))
            ImageDraw.Draw(mask).polygon([tuple(p[:2]) for p in projected], fill=1)
            visible = np.asarray(mask) & (face_depth >= depth)
            if not np.any(visible):
                continue
            depth[visible] = face_depth[visible]
            n = np.cross(points[1] - points[0], points[2] - points[0])
            n /= np.linalg.norm(n)
            tint = .78 + .28 * max(np.dot(n, light), 0)
            texture = grain + fibers
            if material in {"OchreWood", "Grain", "DeepWood"}:
                texture = texture + 9 * np.sin(xx * .28 + np.sin(yy * .018) * 2)
            rgb[visible] = colors[material] * tint + texture[visible, None]

    fill = Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).convert("RGBA")
    alpha = Image.fromarray(np.uint8(np.isfinite(depth)) * 255)
    fill.putalpha(alpha)
    # A dark sepia ink edge keeps each silhouette legible in the forest.
    ink = Image.new("RGBA", (w, h), "#413637")
    ink.putalpha(alpha.filter(ImageFilter.MaxFilter(11)))
    ink.alpha_composite(fill)
    sprite = ink.resize((width, height), Image.Resampling.LANCZOS)
    sprite.save(ASSETS / (name + ".webp"), lossless=True, method=6)


if __name__ == "__main__":
    palette = materials()
    for item in FRAMES:
        render(item, palette)
