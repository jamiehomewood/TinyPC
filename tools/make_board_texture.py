"""
Draws the TinyPC motherboard's surface: solder mask, copper traces and pours under the mask, gold pads, vias, drill
holes and white silkscreen, plus the glass-weave of the board. Also picks where the small surface-mount parts go.

    python tools/make_board_texture.py [px_per_mm]      (default 24.8: an 8192 px wide texture)

Writes (all own work):
    tools/tex/board_basecolor.jpg   sRGB colour
    tools/tex/board_mr.jpg          glTF metallic-roughness (G = roughness, B = metallic)
    tools/tex/board_normal.jpg      OpenGL-style normal map
    tools/smd_parts.json            surface-mount parts for make_pc_models.py: [{type, x, y, rot}] in board mm

Run it in a normal Python with Pillow and numpy (not Blender's Python, which has no Pillow).
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board_layout as L

S = float(sys.argv[1]) if len(sys.argv) > 1 else 8192 / L.BOARD_W        # pixels per mm
WPX, HPX = int(round(L.BOARD_W * S)), int(round(L.BOARD_H * S))
OUT = os.path.join(HERE, "tex"); os.makedirs(OUT, exist_ok=True)
rng = random.Random(7)

def P(x, y): return (x * S, y * S)

# ------------------------------------------------------------------ masks (L images, 0..255)
def layer(): return Image.new("L", (WPX, HPX), 0)
trace, pour, pad, silk, hole, via, mask_open = layer(), layer(), layer(), layer(), layer(), layer(), layer()
dT, dP, dPad, dS, dH, dV = (ImageDraw.Draw(i) for i in (trace, pour, pad, silk, hole, via))

# occupancy grid for routing (0.25 mm cells): parts' footprints and everything already drawn
G = 0.25
GW, GH = int(L.BOARD_W / G) + 1, int(L.BOARD_H / G) + 1
occ = np.zeros((GH, GW), bool)

def block(x0, y0, x1, y1, m=0.0):
    a, b = int(max(0, (min(x0, x1) - m) / G)), int(min(GW - 1, (max(x0, x1) + m) / G))
    c, d = int(max(0, (min(y0, y1) - m) / G)), int(min(GH - 1, (max(y0, y1) + m) / G))
    occ[c:d + 1, a:b + 1] = True

def free_line(pts, half, m=0.25):
    """True if a polyline (mm) with half-width 'half' and clearance m misses everything already used."""
    r = half + m
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / (G * 0.8)))
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n; y = y0 + (y1 - y0) * i / n
            if x - r < 1.5 or y - r < 1.5 or x + r > L.BOARD_W - 1.5 or y + r > L.BOARD_H - 1.5: return False
            a, b = int((x - r) / G), int((x + r) / G); c, d = int((y - r) / G), int((y + r) / G)
            if occ[c:d + 1, a:b + 1].any(): return False
    return True

def mark_line(pts, half):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / (G * 0.8)))
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n; y = y0 + (y1 - y0) * i / n
            block(x - half, y - half, x + half, y + half)

def draw_line(d, pts, w):
    d.line([P(*p) for p in pts], fill=255, width=max(1, int(round(w * S))), joint="curve")
    r = w * S / 2
    for p in (pts[0], pts[-1]):
        x, y = P(*p); d.ellipse((x - r, y - r, x + r, y + r), fill=255)

def draw_via(x, y, tented=True, r_out=0.3, r_in=0.13):
    X, Y = P(x, y)
    dV.ellipse((X - r_out * S, Y - r_out * S, X + r_out * S, Y + r_out * S), fill=255)
    dT.ellipse((X - r_out * S, Y - r_out * S, X + r_out * S, Y + r_out * S), fill=255)
    if not tented: dPad.ellipse((X - r_out * S, Y - r_out * S, X + r_out * S, Y + r_out * S), fill=255)
    dH.ellipse((X - r_in * S, Y - r_in * S, X + r_in * S, Y + r_in * S), fill=255 if not tented else 120)
    block(x - r_out, y - r_out, x + r_out, y + r_out, 0.15)

def rect_px(x, y, w, d):
    return (P(x - w / 2, y - d / 2), P(x + w / 2, y + d / 2))

# ------------------------------------------------------------------ fonts
def font(mm, bold=True):
    for f in ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "DejaVuSansCondensed-Bold.ttf"):
        for d in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts"):
            p = os.path.join(d, f)
            if os.path.exists(p): return ImageFont.truetype(p, max(6, int(mm * S)))
    return ImageFont.load_default()

def text(x, y, s, mm=1.2, rot=0, anchor="mm"):
    """Silkscreen text centred at (x, y) mm, cap height ~ mm."""
    f = font(mm * 1.35)
    bb = dS.textbbox((0, 0), s, font=f, anchor="lt")
    w, h = bb[2] - bb[0] + 8, bb[3] - bb[1] + 8 + int(f.size * 0.35)
    im = Image.new("L", (w, h), 0); ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), s, fill=255, font=f)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    X, Y = P(x, y)
    silk.paste(255, (int(X - im.width / 2), int(Y - im.height / 2)), im)

def outline(x, y, w, d, lw=0.15, notch=None):
    (a, b), (c, e) = rect_px(x, y, w, d)
    dS.rectangle((a, b, c, e), outline=255, width=max(1, int(lw * S)))

# ------------------------------------------------------------------ board furniture: edges, mounting holes
EDGE = 3.0
for hx, hy in ((8, 8 + L.Y_SHIFT), (160, 8 + L.Y_SHIFT), (322, 8 + L.Y_SHIFT), (8, 175 + L.Y_SHIFT), (140, 140 + L.Y_SHIFT),
               (322, 175 + L.Y_SHIFT), (8, L.BOARD_H - 8), (160, L.BOARD_H - 8), (322, L.BOARD_H - 8)):
    X, Y = P(hx, hy)
    dPad.ellipse((X - 3.2 * S, Y - 3.2 * S, X + 3.2 * S, Y + 3.2 * S), fill=255)           # plated ring
    dH.ellipse((X - 1.75 * S, Y - 1.75 * S, X + 1.75 * S, Y + 1.75 * S), fill=255)         # the hole (the screw goes here)
    for i in range(8):                                                                      # stitching vias round it
        a = i * math.pi / 4; draw_via(hx + 4.2 * math.cos(a), hy + 4.2 * math.sin(a))
    block(hx - 5, hy - 5, hx + 5, hy + 5)

# ------------------------------------------------------------------ parts: keep-outs, silkscreen outlines and labels
parts = L.all_parts()
LABELS = {"socket": "CPU1", "dimm_slot_a1": "DIMM_A1", "dimm_slot_a2": "DIMM_A2", "dimm_slot_b1": "DIMM_B1", "dimm_slot_b2": "DIMM_B2",
          "atx24": "ATX_PWR1", "eps8": "CPU_PWR1", "m2_ssd": "M2_1", "pcie1": "PCIE_1", "pcie2": "PCIE_2", "pcie3": "PCIE_3",
          "sata": "SATA1-4", "cmos": "BAT1", "chipset": "U40"}
for pid, model, x, y, rot, w, d, h in parts:
    if pid in ("cooler", "gpu", "dimm_a2", "dimm_b2"): continue                 # these stand on other parts
    if model.startswith("tpc_cap"):
        r = w / 2
        X, Y = P(x, y)
        dS.ellipse((X - (r + 0.35) * S, Y - (r + 0.35) * S, X + (r + 0.35) * S, Y + (r + 0.35) * S), outline=255, width=int(0.15 * S))
        # half-moon fill marks the negative side; "+" on the other
        dS.chord((X - (r + 0.35) * S, Y - (r + 0.35) * S, X + (r + 0.35) * S, Y + (r + 0.35) * S), 90, 270, fill=255)
        text(x + r + 1.0, y - r, "+", 1.1)
        text(x, y + r + 1.4, f"C{rng.randint(100, 899)}", 0.9)
        for sx in (-1, 1):
            a, b = P(x + sx * r * 0.55 - 0.6, y - 0.9); c, e = P(x + sx * r * 0.55 + 0.6, y + 0.9)
            dPad.rectangle((a, b, c, e), fill=255)
        block(x - r, y - r, x + r, y + r, 0.8)
        continue
    m = 1.0
    outline(x, y, w + 0.8, d + 0.8)
    block(x - w / 2, y - d / 2, x + w / 2, y + d / 2, m)
    if pid in LABELS:
        big = pid in ("socket", "atx24", "eps8") or pid.startswith("dimm") or pid.startswith("pcie") or pid == "m2_ssd"
        sz = 3.2 if big else 2.0
        if pid.startswith("dimm_slot"):
            text(x, y + d / 2 + 4.0, LABELS[pid], 2.0, rot=90)
        elif pid == "atx24":
            text(x - w / 2 - 4.0, y, LABELS[pid], 3.0, rot=90)
        elif pid == "socket":
            text(x, y + d / 2 + 4.5, LABELS[pid], 3.2)
        else:
            text(x, y + d / 2 + 3.2, LABELS[pid], sz)

# keep the cooler's mounting holes (Intel-style, 75 mm square) and the M.2 standoff clear
sx, sy = next(p[2:4] for p in parts if p[0] == "socket")
for dx in (-37.5, 37.5):
    for dy in (-37.5, 37.5):
        X, Y = P(sx + dx, sy + dy)
        dPad.ellipse((X - 2.4 * S, Y - 2.4 * S, X + 2.4 * S, Y + 2.4 * S), fill=255)
        dH.ellipse((X - 1.6 * S, Y - 1.6 * S, X + 1.6 * S, Y + 1.6 * S), fill=255)
        block(sx + dx - 3, sy + dy - 3, sx + dx + 3, sy + dy + 3)

# debug LEDs by the 24-pin: pads, a box round them, and big labels so they read from the arrival stop
for name, lx, ly in L.DEBUG_LEDS:
    for sx_ in (-1, 1):
        (a, b), (c, e) = rect_px(lx + sx_ * 0.6, ly, 0.6, 0.8); dPad.rectangle((a, b, c, e), fill=255)
    text(lx - 7.5, ly, name, 2.4)
    block(lx - 13, ly - 2.5, lx + 2, ly + 2.5, 0.3)
outline(L.DEBUG_LEDS[0][1] - 5.5, (L.DEBUG_LEDS[0][2] + L.DEBUG_LEDS[-1][2]) / 2, 18, 26, lw=0.25)
text(L.DEBUG_LEDS[0][1] - 5.5, L.DEBUG_LEDS[0][2] - 5.5, "DEBUG", 2.0)

# section silkscreen (big, generic, no brand)
text(300, 20 + L.Y_SHIFT - 8, "TPC-B1  REV 1.0", 3.0)
text(250, L.BOARD_H - 6, "MADE FOR TINY PC  -  NOT A REAL PRODUCT", 1.6)
text(sx, sy - 40, "CPU_FAN", 1.8)
text(212, 6 + L.Y_SHIFT, "SYS_FAN1", 1.8)

# ------------------------------------------------------------------ SMD parts (geometry comes from make_pc_models.py)
SMD = []
SMD_SIZE = {"r0402": (1.0, 0.5), "c0402": (1.0, 0.5), "r0603": (1.6, 0.8), "c0603": (1.6, 0.8), "c0805": (2.0, 1.25),
            "sot23": (2.9, 2.4), "qfn32": (5.0, 5.0), "tssop16": (5.0, 6.4), "soic8": (4.9, 6.0), "led0603": (1.6, 0.8)}

def place_smd(t, x, y, rot=0, label=True):
    w, d = SMD_SIZE[t]
    if rot in (90, 270): w, d = d, w
    if occ[int((y - d / 2 - 0.3) / G):int((y + d / 2 + 0.3) / G) + 1, int((x - w / 2 - 0.3) / G):int((x + w / 2 + 0.3) / G) + 1].any():
        return False
    if x - w < 3 or y - d < 3 or x + w > L.BOARD_W - 3 or y + d > L.BOARD_H - 3: return False
    SMD.append({"type": t, "x": round(x, 3), "y": round(y, 3), "rot": rot})
    # pads
    if t in ("r0402", "c0402", "r0603", "c0603", "c0805", "led0603"):
        pw = min(w, d) * 0.9; L2 = max(w, d)
        for s_ in (-1, 1):
            if w >= d: a, b = P(x + s_ * (L2 / 2 - pw * 0.35) - pw * 0.35, y - pw / 2); c, e = P(x + s_ * (L2 / 2 - pw * 0.35) + pw * 0.35, y + pw / 2)
            else: a, b = P(x - pw / 2, y + s_ * (L2 / 2 - pw * 0.35) - pw * 0.35); c, e = P(x + pw / 2, y + s_ * (L2 / 2 - pw * 0.35) + pw * 0.35)
            dPad.rectangle((a, b, c, e), fill=255)
    elif t == "qfn32":
        for i in range(8):
            o = -1.75 + i * 0.5
            for (px, py, pw, pd) in ((x + o, y - 2.7, 0.25, 0.6), (x + o, y + 2.7, 0.25, 0.6), (x - 2.7, y + o, 0.6, 0.25), (x + 2.7, y + o, 0.6, 0.25)):
                (a, b), (c, e) = rect_px(px, py, pw, pd); dPad.rectangle((a, b, c, e), fill=255)
    else:
        n = {"tssop16": 8, "soic8": 4, "sot23": 2}[t]; pitch = {"tssop16": 0.65, "soic8": 1.27, "sot23": 1.9}[t]
        span = {"tssop16": 3.6, "soic8": 3.0, "sot23": 1.2}[t]
        for i in range(n):
            o = (i - (n - 1) / 2) * pitch
            for s_ in (-1, 1):
                if rot in (0, 180): (a, b), (c, e) = rect_px(x + o, y + s_ * span, pitch * 0.5, 1.2)
                else: (a, b), (c, e) = rect_px(x + s_ * span, y + o, 1.2, pitch * 0.5)
                dPad.rectangle((a, b, c, e), fill=255)
        if t == "sot23":
            (a, b), (c, e) = rect_px(x, y - (span if rot in (0, 180) else 0), 0.6, 1.0); dPad.rectangle((a, b, c, e), fill=255)
    block(x - w / 2, y - d / 2, x + w / 2, y + d / 2, 0.35)
    if label and t not in ("r0402", "c0402") and rng.random() < 0.6:
        pre = {"r": "R", "c": "C", "s": "Q", "q": "U", "t": "U", "l": "D"}[t[0]]
        text(x + (max(w, d) / 2 + 1.6 if rot in (90, 270) else 0), y + (0 if rot in (90, 270) else d / 2 + 1.0),
             f"{pre}{rng.randint(1, 499)}", 0.75)
    return True

# ------------------------------------------------------------------ copper pours (power planes seen through the mask)
def poly(d, pts): d.polygon([P(*p) for p in pts], fill=255)
vx, vy = next(p[2:4] for p in parts if p[0] == "vrm_top")
poly(dP, [(40, 20 + L.Y_SHIFT - 12), (140, 20 + L.Y_SHIFT - 12), (140, 34 + L.Y_SHIFT), (60, 34 + L.Y_SHIFT), (52, 42 + L.Y_SHIFT), (52, 125 + L.Y_SHIFT), (28, 125 + L.Y_SHIFT), (28, 20 + L.Y_SHIFT)])
ax, ay = next(p[2:4] for p in parts if p[0] == "atx24")
poly(dP, [(ax - 12, ay - 34), (ax + 4, ay - 34), (ax + 4, ay + 34), (ax - 12, ay + 34)])
poly(dP, [(200, 255 + L.Y_SHIFT - 30), (260, 255 + L.Y_SHIFT - 30), (260, 300), (200, 300)])
# wide power traces from the 24-pin across to the VRM and the slots
for i, (yy, w) in enumerate(((ay - 18, 2.4), (ay - 10, 1.8), (ay + 6, 1.8))):
    pts = [(ax - 8, yy), (ax - 40, yy), (ax - 52, yy - 12 - 4 * i), (ax - 52, 14 + L.Y_SHIFT - 8 + 3 * i)]
    draw_line(dT, pts, w); mark_line(pts, w / 2 + 0.3)

# ------------------------------------------------------------------ buses
def bus(start, dirs, n, pitch, w, lens, pair=False, via_end=True, m=0.08):
    """n parallel traces from 'start' (mm), each segment heading one of 8 directions (deg, 0 = +x, 90 = +y)."""
    drawn = 0
    for i in range(n):
        off = i * pitch + (0.25 * (i // 2) if pair else 0)
        x, y = start
        a0 = math.radians(dirs[0] + 90)
        x += math.cos(a0) * off; y += math.sin(a0) * off
        pts = [(x, y)]
        for k, (dg, ln) in enumerate(zip(dirs, lens)):
            a = math.radians(dg)
            ln2 = ln
            if k + 1 < len(dirs):                                  # keep the bundle parallel through 45 deg turns
                turn = (dirs[k + 1] - dg) % 360
                if turn in (45, 315): ln2 = ln + (off if turn == 315 else -off) * math.tan(math.radians(22.5))
            x += math.cos(a) * ln2; y += math.sin(a) * ln2; pts.append((x, y))
        if free_line(pts, w / 2, m):
            draw_line(dT, pts, w); mark_line(pts, w / 2)
            if via_end: draw_via(*pts[-1])
            drawn += 1
    return drawn

sw, sd = 56, 64                                   # socket footprint
# memory buses: socket right edge -> DIMM slots
# (the traces end at the slot's edge: under the slot they go down to the inner layers)
for ch, y0 in enumerate((sy - 26, sy + 4)):
    bus((sx + sw / 2 + 7, y0 + ch * 2), (0, 315 if ch == 0 else 45, 0), 26, 0.42, 0.13, (6, 9, 150.5 - (sx + sw / 2 + 7) - 6 - 9 * 0.707))
# PCIe x16: socket bottom -> slot 1 (pairs)
bus((sx - 22, sy + sd / 2 + 7), (90, 135, 90), 32, 0.38, 0.12, (6, 12, 40), pair=True)
# M.2 lanes
bus((sx + 6, sy + sd / 2 + 7), (90, 45, 90), 10, 0.4, 0.12, (6, 14, 18), pair=True)
# chipset links: chipset -> socket (DMI), -> SATA, -> PCIe x1
cx, cy = next(p[2:4] for p in parts if p[0] == "chipset")
bus((cx - 26, cy - 10), (180, 225, 180), 12, 0.4, 0.12, (10, 30, 40), pair=True)
bus((cx + 26, cy - 6), (0, 45, 0), 12, 0.4, 0.12, (12, 10, 40), pair=True)
bus((cx - 26, cy + 14), (180, 135, 180), 8, 0.4, 0.12, (14, 8, 60), pair=True)

# ------------------------------------------------------------------ small parts (after the buses, before the random routing)
# decoupling caps right round the CPU socket (seen from the CPU stop)
for side in range(4):
    for i in range(26):
        t = rng.choice(("c0402", "c0402", "c0603", "r0402"))
        o = -sw / 2 + 2 + i * (sw - 4) / 25 if side < 2 else -sd / 2 + 2 + i * (sd - 4) / 25
        for ring in (2.2, 4.4):
            if side == 0: place_smd(t, sx + o, sy - sd / 2 - ring, 0, label=False)
            if side == 1: place_smd(t, sx + o, sy + sd / 2 + ring, 0, label=False)
            if side == 2: place_smd(t, sx - sw / 2 - ring, sy + o * sd / sd, 90, label=False)
            if side == 3: place_smd(t, sx + sw / 2 + ring, sy + o, 90, label=False)

# small circuits (an IC with its resistors and caps round it) scattered over the open board, denser near the stops
def cluster(cx, cy):
    ic = rng.choice(("qfn32", "tssop16", "soic8", "sot23", "qfn32"))
    rot = rng.choice((0, 90))
    if not place_smd(ic, cx, cy, rot): return
    for _ in range(rng.randint(4, 12)):
        a = rng.random() * 2 * math.pi; r = rng.uniform(4.5, 9.0)
        place_smd(rng.choice(("r0402", "c0402", "r0603", "c0603", "c0805", "r0402")), cx + r * math.cos(a), cy + r * math.sin(a), rng.choice((0, 90)))

for st in L.STOPS:
    for _ in range(220):
        a = rng.random() * 2 * math.pi; r = rng.uniform(8, 75)
        if rng.random() < 0.18: cluster(st["x"] + r * math.cos(a), st["y"] + r * math.sin(a))
        else: place_smd(rng.choice(("r0402", "c0402", "r0603", "c0603", "c0805", "sot23", "led0603")), st["x"] + r * math.cos(a), st["y"] + r * math.sin(a), rng.choice((0, 90)))
for _ in range(500):
    x, y = rng.uniform(5, L.BOARD_W - 5), rng.uniform(5, L.BOARD_H - 5)
    if rng.random() < 0.12: cluster(x, y)
    else: place_smd(rng.choice(("r0402", "c0402", "r0603", "c0603")), x, y, rng.choice((0, 90)))
# keep the stand points themselves clear of parts (a clean patch to stand on)
SMD = [s for s in SMD if all(math.hypot(s["x"] - st["x"], s["y"] - st["y"]) > 6 for st in L.STOPS)]

# ------------------------------------------------------------------ random routing over the open board
DIRS = [0, 45, 90, 135, 180, 225, 270, 315]
def wander(x, y):
    n = rng.choice((1, 1, 2, 2, 3, 4, 6, 8)); w = rng.choice((0.12, 0.12, 0.15, 0.2, 0.25, 0.4)) if n < 3 else rng.choice((0.12, 0.15))
    pitch = w + rng.choice((0.2, 0.25, 0.3))
    d0 = rng.choice((0, 90, 180, 270, 0, 90, 180, 270, 45, 135))
    dirs = [d0]; lens = [rng.uniform(2, 14)]
    for _ in range(rng.randint(1, 4)):
        dirs.append((dirs[-1] + rng.choice((45, -45, 45, -45, 90, -90))) % 360); lens.append(rng.uniform(1.5, 12))
    # segments that turn 90 deg get a short 45 deg chamfer between them
    D2, L2 = [dirs[0]], [lens[0]]
    for dg, ln in zip(dirs[1:], lens[1:]):
        t = (dg - D2[-1]) % 360
        if t in (90, 270):
            D2.append((D2[-1] + (45 if t == 90 else -45)) % 360); L2.append(1.2)
        D2.append(dg); L2.append(ln)
    return bus((x, y), D2, n, pitch, w, L2, via_end=rng.random() < 0.8, m=0.12)

total = 0
for st in L.STOPS:                                              # dense round the stops: that's what students see
    for _ in range(9000):
        a = rng.random() * 2 * math.pi; r = rng.uniform(3, 85)
        total += wander(st["x"] + r * math.cos(a), st["y"] + r * math.sin(a))
for _ in range(30000):
    total += wander(rng.uniform(4, L.BOARD_W - 4), rng.uniform(4, L.BOARD_H - 4))
# loose vias (stitching to the ground plane)
for _ in range(5000):
    x, y = rng.uniform(4, L.BOARD_W - 4), rng.uniform(4, L.BOARD_H - 4)
    if not occ[int(y / G), int(x / G)]: draw_via(x, y)
print("traces drawn:", total, " smd parts:", len(SMD))

# ------------------------------------------------------------------ composite (in bands of rows, to keep memory down)
blurred = {k: im.filter(ImageFilter.GaussianBlur(r)) for k, (im, r) in
           dict(t=(trace, 0.6), p=(pour, 0.8), pd=(pad, 0.5), sk=(silk, 0.5), ho=(hole, 0.6), vi=(via, 0.6)).items()}
del trace, pour, pad, silk, hole, via
grain_im = Image.effect_noise((WPX, HPX), 40).filter(ImageFilter.GaussianBlur(2.5))
dust_im = Image.effect_noise((WPX // 6, HPX // 6), 70).filter(ImageFilter.GaussianBlur(1.2)).resize((WPX, HPX), Image.BICUBIC)

base = np.array([16, 52, 30], np.float32)          # solder mask over bare laminate (sRGB)
over_cu = np.array([36, 92, 48], np.float32)        # mask over copper
over_pour = np.array([26, 72, 40], np.float32)
gold = np.array([214, 172, 86], np.float32)
silkc = np.array([232, 232, 222], np.float32)
holec = np.array([12, 12, 10], np.float32)
dustc = np.array([118, 112, 100], np.float32)

out_col = Image.new("RGB", (WPX, HPX)); out_mr = Image.new("RGB", (WPX, HPX)); out_n = Image.new("RGB", (WPX, HPX))
BAND, PADR = 768, 6
for r0 in range(0, HPX, BAND):
    a0, a1 = max(0, r0 - PADR), min(HPX, r0 + BAND + PADR)
    def A(im): return np.asarray(im.crop((0, a0, WPX, a1)), dtype=np.float32) / 255.0
    t, p, pd, sk, ho, vi = (A(blurred[k]) for k in ("t", "p", "pd", "sk", "ho", "vi"))
    grain = A(grain_im) - 0.5
    dust = np.clip((A(dust_im) - 0.66) * 4.0, 0, 1) * 0.22
    yy, xx = np.mgrid[a0:a1, 0:WPX].astype(np.float32)
    weave = np.sin(xx / S * 2 * math.pi / 0.55) * np.sin(yy / S * 2 * math.pi / 0.55)     # glass-cloth weave
    del xx, yy
    E = lambda v: v[..., None]
    col = base * (1 + 0.05 * E(weave) + 0.08 * E(grain))
    col = col * (1 - E(p)) + over_pour * E(p)
    col = col * (1 - E(t)) + over_cu * E(t)
    col = col * (1 - E(sk)) + silkc * E(sk)
    col = col * (1 - E(pd)) + gold * (1 + 0.06 * E(grain)) * E(pd)
    col = col * (1 - E(ho)) + holec * E(ho)
    col = col * (1 - E(dust)) + dustc * E(dust)
    i0, i1 = r0 - a0, r0 - a0 + min(BAND, HPX - r0)
    out_col.paste(Image.fromarray(np.clip(col[i0:i1], 0, 255).astype(np.uint8)), (0, r0)); del col
    rough = np.clip(0.42 + 0.06 * grain + 0.25 * sk - 0.2 * pd + 0.35 * dust, 0, 1)
    metal = np.clip(pd * (1 - ho), 0, 1)
    mr = np.stack([np.zeros_like(rough), rough, metal], -1)
    out_mr.paste(Image.fromarray((mr[i0:i1] * 255).astype(np.uint8)), (0, r0)); del mr, rough, metal
    h = 0.04 * weave + 0.6 * t + 0.35 * p + 0.5 * sk + 0.9 * pd - 1.2 * ho + 0.08 * grain + 0.6 * vi
    h = np.asarray(Image.fromarray(np.clip((h + 1.5) * 60, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), np.float32) / 60.0
    gy, gx = np.gradient(h)
    k = 1.6
    nx, ny = -gx * k, gy * k
    ln = np.sqrt(nx * nx + ny * ny + 1)
    nm = np.stack([nx / ln, ny / ln, 1 / ln], -1) * 0.5 + 0.5
    out_n.paste(Image.fromarray((nm[i0:i1] * 255).astype(np.uint8)), (0, r0))
    del t, p, pd, sk, ho, vi, grain, dust, weave, h, gx, gy, nx, ny, ln, nm
out_col.save(os.path.join(OUT, "board_basecolor.jpg"), quality=92)
out_mr.save(os.path.join(OUT, "board_mr.jpg"), quality=92)
out_n.save(os.path.join(OUT, "board_normal.jpg"), quality=94)

json.dump({"units": "board mm (see board_layout.py)", "parts": SMD}, open(os.path.join(HERE, "smd_parts.json"), "w"), indent=0)
print("written", WPX, "x", HPX)
