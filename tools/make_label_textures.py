"""
Small label textures for TinyPC parts (own work, generic wording, no brands):
capacitor tops, the CMOS battery, the M.2 SSD label and the RAM sticker.

    python tools/make_label_textures.py        -> tools/tex/*.png

Run in a normal Python with Pillow (not Blender's).
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex"); os.makedirs(OUT, exist_ok=True)

def F(px, bold=True):
    for d in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts"):
        p = os.path.join(d, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        if os.path.exists(p): return ImageFont.truetype(p, px)
    return ImageFont.load_default()

def brushed(size, base, streak=14, radial=False):
    im = Image.effect_noise(size, streak).convert("L")
    im = im.resize((size[0] // 8, size[1]), Image.BILINEAR).resize(size, Image.BILINEAR) if not radial else im.filter(ImageFilter.GaussianBlur(1))
    col = Image.new("RGB", size, base)
    return Image.blend(col, Image.merge("RGB", (im, im, im)), 0.12)

# ---- polymer capacitor top: aluminium with a coloured polarity band, value and voltage
for name, band, val, volt in (("cap_top_a", (92, 40, 120), "560", "6.3V"), ("cap_top_b", (30, 30, 34), "270", "16V")):
    s = 512
    im = brushed((s, s), (176, 178, 182), radial=True); d = ImageDraw.Draw(im)
    d.pieslice((0, 0, s, s), 120, 240, fill=band)                     # band over the negative side
    d.text((s * 0.6, s * 0.36), val, fill=(30, 30, 30), font=F(110), anchor="mm")
    d.text((s * 0.6, s * 0.62), volt, fill=(30, 30, 30), font=F(80), anchor="mm")
    d.text((s * 0.6, s * 0.83), "+", fill=(30, 30, 30), font=F(70), anchor="mm")
    mask = Image.new("L", (s, s), 0); ImageDraw.Draw(mask).ellipse((0, 0, s - 1, s - 1), fill=255)
    bg = Image.new("RGB", (s, s), (150, 152, 156)); bg.paste(im, (0, 0), mask)
    bg.save(os.path.join(OUT, name + ".png"))

# ---- CMOS battery (a standard CR2032 cell: the size code is a standard, not a brand)
s = 1024
im = brushed((s, s), (196, 198, 202), radial=True); d = ImageDraw.Draw(im)
d.text((s / 2, s * 0.30), "+", fill=(40, 40, 44), font=F(200), anchor="mm")
d.text((s / 2, s * 0.52), "CR2032", fill=(40, 40, 44), font=F(150), anchor="mm")
d.text((s / 2, s * 0.68), "3V  LITHIUM CELL", fill=(40, 40, 44), font=F(70), anchor="mm")
d.ellipse((24, 24, s - 24, s - 24), outline=(150, 152, 156), width=18)
im.save(os.path.join(OUT, "battery_top.png"))

# ---- M.2 SSD label (black with white type)
w, h = 2048, 560
im = Image.new("RGB", (w, h), (18, 18, 20)); d = ImageDraw.Draw(im)
d.text((80, 90), "NVMe SSD", fill=(235, 235, 235), font=F(150))
d.text((80, 290), "1 TB   M.2 2280   PCIe 4.0 x4", fill=(200, 200, 200), font=F(78, False))
d.text((80, 410), "TINY PC STORAGE  -  NOT A REAL PRODUCT", fill=(150, 150, 150), font=F(52, False))
for i in range(36):                                                 # a generic barcode
    x = 1500 + i * 12 + (i * 7) % 5; d.rectangle((x, 120, x + 4 + (i * 5) % 6, 330), fill=(230, 230, 230))
im.save(os.path.join(OUT, "ssd_label.jpg"), quality=92)

# ---- RAM heat-spreader sticker
w, h = 1600, 360
im = Image.new("RGB", (w, h), (226, 226, 222)); d = ImageDraw.Draw(im)
d.text((50, 50), "DDR5  16 GB", fill=(20, 20, 22), font=F(110))
d.text((50, 205), "5600 MT/s   1.25 V   CL36", fill=(40, 40, 44), font=F(64, False))
for i in range(30):
    x = 1150 + i * 13 + (i * 7) % 5; d.rectangle((x, 60, x + 4 + (i * 3) % 5, 300), fill=(20, 20, 22))
im.save(os.path.join(OUT, "dimm_label.jpg"), quality=92)
print("labels written to", OUT)

# ---- CPU lid (generic laser-etched markings on nickel) and the pads under the CPU
s = 1024
im = brushed((s, s), (176, 178, 181)); d = ImageDraw.Draw(im)
ink = (92, 94, 98)
d.text((s * 0.5, s * 0.30), "TPC-9", fill=ink, font=F(130), anchor="mm")
d.text((s * 0.5, s * 0.44), "PROCESSOR  8 CORES", fill=ink, font=F(56), anchor="mm")
d.text((s * 0.5, s * 0.53), "3.6 GHz", fill=ink, font=F(56, False), anchor="mm")
d.text((s * 0.5, s * 0.66), "SN  TPC7-0042-1103", fill=ink, font=F(40, False), anchor="mm")
import random as _r; rr = _r.Random(5)
x0, y0, c = int(s * 0.40), int(s * 0.72), 12                        # a generic data-matrix square
for i in range(16):
    for j in range(16):
        if i == 15 or j == 0 or (i + j) % 2 == 0 and (i == 0 or j == 15) or (0 < i < 15 and 0 < j < 15 and rr.random() < 0.5):
            d.rectangle((x0 + j * c, y0 + i * c, x0 + j * c + c - 1, y0 + i * c + c - 1), fill=ink)
d.polygon([(40, s - 40), (40, s - 130), (130, s - 40)], fill=ink)  # pin-1 triangle
im.save(os.path.join(OUT, "cpu_lid.png"))

s = 1024                                                            # underside: a field of gold pads on green
im = Image.new("RGB", (s, s), (26, 70, 44)); d = ImageDraw.Draw(im)
n = 40
for i in range(n):
    for j in range(n):
        if 14 < i < 26 and 14 < j < 26: continue
        x, y = 30 + j * (s - 60) / (n - 1), 30 + i * (s - 60) / (n - 1)
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(214, 172, 86))
im.save(os.path.join(OUT, "cpu_pads.png"))

# ---- empty socket: the field of spring pins (gold dots on dark grey)
s = 1024
im = Image.new("RGB", (s, s), (40, 40, 42)); d = ImageDraw.Draw(im)
n = 44
for i in range(n):
    for j in range(n):
        if 15 < i < 28 and 15 < j < 28: continue
        x, y = 24 + j * (s - 48) / (n - 1) + (6 if i % 2 else 0), 24 + i * (s - 48) / (n - 1)
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(222, 182, 92)); d.point((x - 2, y - 2), fill=(255, 236, 170))
im.save(os.path.join(OUT, "socket_pins.png"))

# ---- pegboard (perforated hardboard)
s = 1024
im = Image.new("RGB", (s, s), (168, 132, 92)); d = ImageDraw.Draw(im)
step = s / 16
for i in range(16):
    for j in range(16):
        x, y = (j + 0.5) * step, (i + 0.5) * step
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(40, 30, 22))
im.save(os.path.join(OUT, "pegboard.png"))

# ---- monitor screen: a generic firmware setup page (shown when the PC is switched on)
w, h = 1920, 1080
im = Image.new("RGB", (w, h), (8, 22, 52)); d = ImageDraw.Draw(im)
d.rectangle((0, 0, w, 110), fill=(16, 60, 130))
d.text((60, 30), "TINY PC  SETUP UTILITY", fill=(235, 240, 255), font=F(56))
rows = [("Processor", "TPC-9  8 cores  3.6 GHz"), ("CPU temperature", "38 °C"), ("Memory", "32 GB  (2 x 16 GB)  dual channel"),
        ("Storage", "NVMe SSD  1 TB  (M.2_1)"), ("Graphics", "PCIe x16 card  (PCIE_1)"), ("CPU fan", "1150 RPM"), ("System fans", "5 detected"),
        ("Boot device", "NVMe SSD")]
for k, (a, b) in enumerate(rows):
    d.text((90, 190 + k * 92), a, fill=(150, 175, 220), font=F(46, False)); d.text((760, 190 + k * 92), b, fill=(240, 244, 255), font=F(46))
d.text((90, h - 110), "All checks passed.  Press F10 to start.", fill=(120, 230, 150), font=F(48))
im.save(os.path.join(OUT, "screen_setup.jpg"), quality=92)
print("workbench textures written")
