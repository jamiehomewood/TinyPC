"""
Textures for the CPU with its lid peeled back (own work, generic, no brands):

  tex/die_map.png        the top of the chip as an "X-ray" map: 8 cores, shared L3 cache, memory controller, PCIe/I/O,
                         with big labels (5120 x 3072 = the 20 x 12 mm die; image right = +x = towards the RAM,
                         image top = +y = the board's top edge, which is the Front wall at the die stop)
  tex/cpu_substrate.png  the CPU's own small circuit board (green, fine traces and vias), 48 x 54 mm
  tex/lid_underside.png  the inside of the lid: nickel, with the solder imprint where it sat on the chip (37.5 mm square)

Real chips are flip-chip: the circuits are on the silicon's underside, facing the pads. The die map is labelled as an
X-ray view, and the tour says so.

    python tools/make_die_textures.py        (normal Python with Pillow)
"""
import os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex"); os.makedirs(OUT, exist_ok=True)

def F(px, bold=True):
    for d in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts"):
        p = os.path.join(d, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        if os.path.exists(p): return ImageFont.truetype(p, px)
    return ImageFont.load_default()

def jitter(c, n, rng): return tuple(max(0, min(255, v + rng.randint(-n, n))) for v in c)

# ------------------------------------------------------------------ the die map
W, H = 5120, 3072
PX = W / 20.0                                   # px per mm
rng = random.Random(7)
im = Image.new("RGB", (W, H), (34, 36, 52))
d = ImageDraw.Draw(im)
# fine metal-layer grid over everything
for x in range(0, W, 16): d.line([(x, 0), (x, H)], fill=(40, 42, 60))
for y in range(0, H, 16): d.line([(0, y), (W, y)], fill=(40, 42, 60))

def sram(box, base, cell=10):
    """A cache block: a very regular grid of cells (memory) with a darker spine (its address logic)."""
    x0, y0, x1, y1 = map(int, box)
    d.rectangle(box, fill=base)
    hi = tuple(min(255, v + 22) for v in base)
    for x in range(x0 + 4, x1 - 4, cell):
        d.line([(x, y0 + 4), (x, y1 - 4)], fill=hi, width=2)
    for y in range(y0 + 4, y1 - 4, cell):
        d.line([(x0 + 4, y), (x1 - 4, y)], fill=hi, width=1)
    mid = (x0 + x1) // 2
    d.rectangle((mid - 14, y0, mid + 14, y1), fill=tuple(max(0, v - 30) for v in base))
    d.rectangle(box, outline=tuple(max(0, v - 40) for v in base), width=6)

def logic(box, palette, n=900):
    """Random logic: lots of small irregular blocks (the ALUs, schedulers, decoders...)."""
    x0, y0, x1, y1 = map(int, box)
    d.rectangle(box, fill=palette[0])
    for _ in range(n):
        w, h = rng.randint(10, 70), rng.randint(10, 70)
        x, y = rng.randint(x0, max(x0, x1 - w)), rng.randint(y0, max(y0, y1 - h))
        d.rectangle((x, y, x + w, y + h), fill=jitter(rng.choice(palette[1:]), 10, rng))
    for _ in range(n // 6):                      # wiring channels
        if rng.random() < 0.5:
            y = rng.randint(y0, y1); d.line([(x0, y), (x1, y)], fill=palette[0], width=3)
        else:
            x = rng.randint(x0, x1); d.line([(x, y0), (x, y1)], fill=palette[0], width=3)

def label(xy, text, px, anchor="mm"):
    f = F(px)
    for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)):
        d.text((xy[0] + dx, xy[1] + dy), text, fill=(12, 12, 20), font=f, anchor=anchor)
    d.text(xy, text, fill=(245, 245, 240), font=f, anchor=anchor)

M = 40                                          # margin (px)
MC_X = int(W * 0.855)                           # memory controller strip, right (towards the RAM)
IO_Y = int(H * 0.86)                            # PCIe / I/O strip, bottom (towards the graphics card slot)
CORE_W = (MC_X - 2 * M - 3 * 30) / 4
ROW_H = (IO_Y - M) * 0.40
CACHE_Y0, CACHE_Y1 = M + ROW_H + 30, IO_Y - ROW_H - 30
warm = [(70, 52, 48), (130, 84, 60), (156, 112, 66), (104, 70, 96), (90, 96, 120), (170, 140, 90)]
cores = []
for row in range(2):
    y0 = M if row == 0 else IO_Y - ROW_H
    for i in range(4):
        x0 = M + i * (CORE_W + 30)
        box = (x0, y0, x0 + CORE_W, y0 + ROW_H)
        # inside a core: logic, an L2 cache block next to the shared cache, and two thin L1 strips
        l2h = ROW_H * 0.30
        l2 = (x0 + 20, y0 + ROW_H - l2h - 20, x0 + CORE_W - 20, y0 + ROW_H - 20) if row == 0 else (x0 + 20, y0 + 20, x0 + CORE_W - 20, y0 + 20 + l2h)
        lg = (x0, y0, x0 + CORE_W, l2[1] - 10) if row == 0 else (x0, l2[3] + 10, x0 + CORE_W, y0 + ROW_H)
        logic(lg, warm, n=700)
        sram(l2, (58, 92, 112), cell=9)
        for k in (0.30, 0.62):
            lx = lg[0] + (lg[2] - lg[0]) * k
            sram((lx, lg[1] + 40, lx + 70, lg[3] - 40), (66, 104, 120), cell=7)
        d.rectangle(box, outline=(200, 170, 90), width=10)
        cores.append(box)
# shared L3 cache: a long band between the two rows of cores, in slices
nsl = 8
for i in range(nsl):
    x0 = M + i * (MC_X - 2 * M) / nsl
    sram((x0 + 6, CACHE_Y0, x0 + (MC_X - 2 * M) / nsl - 6, CACHE_Y1), (52, 84, 118), cell=10)
d.rectangle((M, CACHE_Y0 - 8, MC_X - M, CACHE_Y1 + 8), outline=(110, 170, 230), width=10)
# memory controller (right): two channels of DDR interface stripes
mc = (MC_X + 10, M, W - M, IO_Y - 30)
d.rectangle(mc, fill=(38, 74, 58))
for ch in range(2):
    cy0 = mc[1] + ch * (mc[3] - mc[1]) / 2 + 30; cy1 = cy0 + (mc[3] - mc[1]) / 2 - 60
    logic((mc[0] + 30, cy0, mc[0] + (mc[2] - mc[0]) * 0.45, cy1), [(44, 80, 62), (70, 120, 84), (96, 140, 96), (60, 100, 110)], n=200)
    for y in range(int(cy0), int(cy1), 22):
        d.rectangle((mc[0] + (mc[2] - mc[0]) * 0.5, y, mc[2] - 30, y + 12), fill=(150, 170, 120))
d.rectangle(mc, outline=(120, 220, 140), width=10)
# PCIe / I/O (bottom): SerDes lanes along the edge plus some logic
io = (M, IO_Y + 10, W - M, H - M)
d.rectangle(io, fill=(72, 52, 36))
logic((io[0] + 20, io[1] + 20, io[2] * 0.55, io[3] - 20), [(72, 52, 36), (120, 84, 50), (150, 106, 64), (96, 80, 100)], n=260)
for x in range(int(io[2] * 0.58), int(io[2] - 30), 60):
    d.rectangle((x, io[1] + 30, x + 40, io[3] - 30), fill=(184, 136, 80))
d.rectangle(io, outline=(230, 160, 90), width=10)
# bond pads round the edge (bumps): tiny dots
for x in range(20, W, 64):
    for y in (12, H - 12): d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(170, 170, 160))
for y in range(20, H, 64):
    for x in (12, W - 12): d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(170, 170, 160))
im = im.filter(ImageFilter.GaussianBlur(0.8)); d = ImageDraw.Draw(im)
# labels (big enough to read on the room's floor: the die stop is at x500, so 1 mm = 0.5 m and 256 px = 1 m)
for n, (x0, y0, x1, y1) in enumerate(cores):
    label(((x0 + x1) / 2, (y0 + y1) / 2), f"CORE {n + 1}", 150)
label(((M + MC_X - M) / 2, (CACHE_Y0 + CACHE_Y1) / 2), "L3 CACHE (shared by all 8 cores)", 150)
mcl = Image.new("RGBA", (int(mc[3] - mc[1]), 360), (0, 0, 0, 0)); dm = ImageDraw.Draw(mcl)
for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4)):
    dm.text((mcl.width / 2 + dx, 180 + dy), "MEMORY CONTROLLER", fill=(12, 12, 20, 255), font=F(130), anchor="mm")
dm.text((mcl.width / 2, 180), "MEMORY CONTROLLER", fill=(245, 245, 240, 255), font=F(130), anchor="mm")
mcl = mcl.rotate(90, expand=True)
im.paste(mcl, (int((mc[0] + mc[2]) / 2 - mcl.width / 2), int(mc[1])), mcl); d = ImageDraw.Draw(im)
label(((io[0] + io[2]) / 2, (io[1] + io[3]) / 2), "PCIe + INPUT/OUTPUT", 130)
label((W - 60, 70), "X-RAY VIEW", 70, anchor="rm")
im.save(os.path.join(OUT, "die_map.png"), optimize=True)

# ------------------------------------------------------------------ the CPU's substrate (its own little circuit board)
SW, SH = 2048, 2304                              # 48 x 54 mm
rng = random.Random(9)
sub = Image.new("RGB", (SW, SH), (22, 70, 40)); d = ImageDraw.Draw(sub)
for _ in range(500):                              # traces (seen through the green solder mask)
    x, y = rng.randint(0, SW), rng.randint(0, SH); col = (34, 92, 52)
    pts = [(x, y)]
    for _ in range(rng.randint(2, 5)):
        if rng.random() < 0.5: x += rng.randint(-300, 300)
        else: y += rng.randint(-300, 300)
        pts.append((x, y))
    d.line(pts, fill=col, width=rng.choice((3, 4, 6)))
for _ in range(1600):                             # vias
    x, y = rng.randint(0, SW), rng.randint(0, SH)
    d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(150, 130, 70))
sub = sub.filter(ImageFilter.GaussianBlur(1.2)); d = ImageDraw.Draw(sub)
d.text((SW * 0.5, SH * 0.93), "TPC-9   8C/16T   3.6 GHz", fill=(210, 220, 200), font=F(70), anchor="mm")
d.text((SW * 0.08, SH * 0.07), "\u25B2", fill=(220, 190, 80), font=F(110), anchor="mm")    # the gold triangle (pin 1)
sub.save(os.path.join(OUT, "cpu_substrate.png"), optimize=True)

# ------------------------------------------------------------------ the inside of the lid
LS = 1536                                         # 37.5 mm square: 40.96 px/mm
lid = Image.effect_noise((LS, LS), 10).convert("L").resize((LS // 6, LS), Image.BILINEAR).resize((LS, LS), Image.BILINEAR)
lid = Image.blend(Image.new("RGB", (LS, LS), (176, 172, 166)), Image.merge("RGB", (lid, lid, lid)), 0.15)
d = ImageDraw.Draw(lid); p = LS / 37.5
cx, cy = LS / 2, LS / 2                           # the solder imprint where the 20 x 12 mm chip sat
d.rectangle((cx - 10 * p, cy - 6 * p, cx + 10 * p, cy + 6 * p), fill=(196, 198, 204))
for _ in range(240):
    x, y = rng.uniform(cx - 10 * p, cx + 10 * p), rng.uniform(cy - 6 * p, cy + 6 * p); r = rng.uniform(4, 18)
    d.ellipse((x - r, y - r, x + r, y + r), fill=jitter((214, 216, 222), 8, rng))
m = 1.6 * p                                       # black sealant line round the edge (where it was glued down)
d.rectangle((m * 0.3, m * 0.3, LS - m * 0.3, LS - m * 0.3), outline=(18, 18, 18), width=int(m))
lid.filter(ImageFilter.GaussianBlur(0.6)).save(os.path.join(OUT, "lid_underside.png"), optimize=True)
print("wrote die_map.png, cpu_substrate.png, lid_underside.png in", OUT)

# ------------------------------------------------------------------ inside a core: the floor of the "Inside a core" room
# Rows of standard cells (the tiny logic gates) between power rails, with copper wiring running across them. 14 m square
# in the room (the floor of tpc_core_hall); kept dark so the live register diagram reads on top.
CS = 4096
rng = random.Random(21)
core = Image.new("RGB", (CS, CS), (16, 18, 28)); d = ImageDraw.Draw(core)
ROW = 64
for y in range(0, CS, ROW):
    d.rectangle((0, y, CS, y + 5), fill=(60, 64, 80))                  # power rail
    x = 0
    while x < CS:                                                     # cells along the row
        w = rng.choice((18, 24, 30, 36, 48, 60))
        col = rng.choice(((34, 40, 62), (40, 36, 58), (30, 46, 56), (44, 40, 50)))
        d.rectangle((x + 2, y + 8, x + w - 2, y + ROW - 4), fill=col)
        for k in range(rng.randint(1, 3)):                            # contacts
            cx = x + rng.randint(4, max(5, w - 6)); d.rectangle((cx, y + 20, cx + 3, y + 23), fill=(120, 110, 90))
        x += w
for _ in range(260):                                                  # copper wiring on the layers above
    if rng.random() < 0.5:
        y = rng.randrange(0, CS, 16); x0 = rng.randint(0, CS); d.line([(x0, y), (x0 + rng.randint(200, 1400), y)], fill=(150, 96, 52), width=4)
    else:
        x = rng.randrange(0, CS, 16); y0 = rng.randint(0, CS); d.line([(x, y0), (x, y0 + rng.randint(200, 1400))], fill=(170, 120, 66), width=4)
core.filter(ImageFilter.GaussianBlur(0.6)).save(os.path.join(OUT, "core_floor.png"), optimize=True)
print("wrote core_floor.png")
