"""
Draws the top of the projected walls (red) on Room Builder panoramas, so you can see what will be lost on the
unprojected ceiling, and the floor line (the base of the walls, orange). Everything above the red line is not shown in
the room.

    python tools/check_render.py <view.jpg> [more.jpg ...] [--room W D H] [--eye E] [--out folder]

Defaults: the Peterborough room (6.40 x 5.71 x 2.244 m), eye 1.12 m, output next to each image as <name>_check.jpg.
Assumes the panorama's centre is the middle of the Front wall (Room Builder's convention) and the camera is at the
room centre. Needs Pillow.
"""
import math, os, sys
from PIL import Image, ImageDraw

def wall_lines(w, h, W, D, H, eye):
    top, base = [], []
    for i in range(w + 1):
        yaw = (i / w - 0.5) * 2 * math.pi
        dx, dy = abs(math.sin(yaw)), abs(math.cos(yaw))
        dist = min(W / 2 / dx if dx > 1e-9 else 1e9, D / 2 / dy if dy > 1e-9 else 1e9)
        top.append((i, h / 2 - math.atan((H - eye) / dist) / math.pi * h))
        base.append((i, h / 2 + math.atan(eye / dist) / math.pi * h))
    return top, base

def main(argv):
    W, D, H, eye, out, files = 6.40, 5.71, 2.244, 1.12, None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--room": W, D, H = map(float, argv[i + 1:i + 4]); i += 4; continue
        if a == "--eye": eye = float(argv[i + 1]); i += 2; continue
        if a == "--out": out = argv[i + 1]; i += 2; continue
        files.append(a); i += 1
    for f in files:
        im = Image.open(f).convert("RGB")
        if im.width > 3072: im = im.resize((3072, 1536), Image.LANCZOS)
        top, base = wall_lines(im.width, im.height, W, D, H, eye)
        d = ImageDraw.Draw(im); lw = max(2, im.width // 900)
        d.line(top, fill=(255, 50, 50), width=lw); d.line(base, fill=(255, 150, 0), width=max(1, lw - 1))
        name = os.path.splitext(os.path.basename(f))[0] + "_check.jpg"
        if out: name = os.path.basename(os.path.dirname(os.path.abspath(f))) + "_" + name     # keep names apart
        dst = os.path.join(out or os.path.dirname(os.path.abspath(f)), name)
        im.save(dst, quality=88); print("wrote", dst)

if __name__ == "__main__":
    main(sys.argv[1:])
