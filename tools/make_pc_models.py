"""
Builds TinyPC's own PC part models in Blender, at real size, and writes them to models/<id>/ (glb, thumb.png, model.json)
in the same shape as Room Builder's catalogue entries, so sync-to-roombuilder can copy them into RoomBuilder/catalogue/models.

    blender -b --factory-startup -P tools/make_pc_models.py -- [ids...]

Run tools/make_board_texture.py and tools/make_label_textures.py first (they make tools/tex/* and tools/smd_parts.json).

Conventions
- Built in millimetres and exported in metres (real size). z = 0 is the surface the part stands on.
- Parts are built round their ANCHOR (the footprint centre in board_layout.py) at rot 0: the layout's w along x, d along
  y, with y pointing to the board's TOP edge (board y runs the other way). model.json "bbox_mm" records the bounds round
  the anchor, so make_stop_specs.py can place a part whose bounds aren't centred (a cable going one way, say).
- The board (tpc_board) and the case (tpc_case_shell) are built in board coordinates instead: anchor = the board's
  top-rear corner, x = board x, y = -board y, z = 0 at the underside of the board.
- No real logos or brand names anywhere: generic labels only.
"""
import bpy, json, math, os, random, sys
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools"); TEX = os.path.join(TOOLS, "tex")
OUT = os.path.join(ROOT, "models")
sys.path.insert(0, TOOLS)
import board_layout as LAY
ONLY = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MM = 0.001

# per-model switches, set from the model id in the main loop: "_off" = the PC switched off (RGB and LEDs dark);
# "_on" = switched on with the fan blades left out, because the tour spins live blade models (tpc_fan_rotor_*) over them
OFF, BLADES = [False], [True]
DBG = [None]          # which debug LED is lit ("_dbg_dram" in the model id -> "DRAM"), or None

# ------------------------------------------------------------------ materials (all glTF-exportable)
def principled(name):
    m = bpy.data.materials.get(name)
    if m: return m, None
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")

def mat(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, coat=0.0):
    m, b = principled(name)
    if b is None: return m
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        for k in ("Coat Weight", "Clearcoat"):
            if k in b.inputs: b.inputs[k].default_value = coat; break
    if emit:
        for k in ("Emission Color", "Emission"):
            if k in b.inputs: b.inputs[k].default_value = (*emit, 1); break
        b.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = (*color, 1)
    return m

def img_node(nt, path, non_color=False):
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True)
    if non_color: t.image.colorspace_settings.name = "Non-Color"
    return t

def tex_mat(name, base, mr=None, normal=None, rough=0.5, metal=0.0, normal_strength=1.0):
    m, b = principled(name)
    if b is None: return m
    nt = m.node_tree
    t = img_node(nt, base); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if mr:
        t2 = img_node(nt, mr, True); sp = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t2.outputs["Color"], sp.inputs[0])
        nt.links.new(sp.outputs[1], b.inputs["Roughness"]); nt.links.new(sp.outputs[2], b.inputs["Metallic"])
    if normal:
        t3 = img_node(nt, normal, True); nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(t3.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m

def M():
    return {
        "black_plastic": mat("Black_plastic", (0.018, 0.018, 0.02), 0.45),
        "black_matte": mat("Black_matte", (0.012, 0.012, 0.013), 0.75),
        "grey_plastic": mat("Grey_plastic", (0.28, 0.29, 0.3), 0.45),
        "white_plastic": mat("White_nylon", (0.78, 0.77, 0.72), 0.5),
        "nickel": mat("Nickel_IHS", (0.55, 0.55, 0.56), 0.48, 1.0),
        "steel": mat("Steel", (0.62, 0.63, 0.65), 0.32, 1.0),
        "steel_dark": mat("Steel_dark", (0.12, 0.12, 0.13), 0.4, 1.0),
        "alu": mat("Aluminium", (0.8, 0.8, 0.81), 0.3, 1.0),
        "alu_brushed": mat("Aluminium_brushed", (0.75, 0.75, 0.77), 0.38, 1.0),
        "gunmetal": mat("Anodised_gunmetal", (0.06, 0.065, 0.07), 0.38, 0.9),
        "copper": mat("Copper", (0.85, 0.42, 0.25), 0.28, 1.0),
        "gold": mat("Gold_contacts", (0.95, 0.72, 0.32), 0.22, 1.0),
        "solder": mat("Solder", (0.72, 0.72, 0.7), 0.25, 1.0),
        "chip": mat("Chip_epoxy", (0.025, 0.025, 0.027), 0.55),
        "ceramic_cap": mat("Ceramic_cap_tan", (0.36, 0.25, 0.14), 0.5),
        "resistor": mat("Resistor_black", (0.02, 0.02, 0.022), 0.6),
        "paste": mat("Thermal_paste", (0.36, 0.37, 0.38), 0.42, 0.1),
        "ferrite": mat("Ferrite_grey", (0.16, 0.16, 0.17), 0.7),
        "pcb_black": mat("PCB_black", (0.02, 0.022, 0.024), 0.45),
        "fr4_edge": mat("FR4_edge", (0.36, 0.33, 0.2), 0.7),
        "sleeve": mat("Cable_sleeve_black", (0.02, 0.02, 0.022), 0.8),
        "rubber": mat("Rubber_black", (0.015, 0.015, 0.015), 0.9),
        "fan_blade": mat("Fan_blade_smoke", (0.05, 0.05, 0.055), 0.35, coat=0.3),
        "case_steel": mat("Case_steel_black", (0.03, 0.03, 0.032), 0.55, 0.6),
        "led_green": mat("LED_green_lit", (0.1, 1.0, 0.25), 0.3, emit=(0.15, 1.0, 0.3), strength=40.0),
        "led_blue": mat("LED_blue_lit", (0.1, 0.35, 1.0), 0.3, emit=(0.15, 0.4, 1.0), strength=40.0),
        "led_off": mat("LED_white_body", (0.85, 0.85, 0.8), 0.3),
        "rgb_cyan": mat("RGB_diffuser_cyan", (0.6, 0.95, 1.0), 0.4, emit=(0.1, 0.75, 1.0), strength=8.0) if not OFF[0] else mat("RGB_diffuser_unlit", (0.55, 0.56, 0.58), 0.45),
        "rgb_magenta": mat("RGB_diffuser_magenta", (1.0, 0.6, 0.95), 0.4, emit=(0.9, 0.12, 0.85), strength=8.0) if not OFF[0] else mat("RGB_diffuser_unlit", (0.55, 0.56, 0.58), 0.45),
        "rgb_violet": mat("RGB_diffuser_violet", (0.8, 0.7, 1.0), 0.4, emit=(0.45, 0.2, 1.0), strength=8.0) if not OFF[0] else mat("RGB_diffuser_unlit", (0.55, 0.56, 0.58), 0.45),
        "screen": mat("Screen_off", (0.01, 0.012, 0.015), 0.12, coat=0.6),
        "daylight": mat("Daylight_panel", (1, 1, 1), 1.0, emit=(0.95, 0.97, 1.0), strength=9.0),
    }

# ------------------------------------------------------------------ mesh builder (all sizes in mm)
class MB:
    """Collects faces per material and builds one object. Each face has its own vertices, so flat faces stay flat."""
    def __init__(self):
        self.verts, self.faces, self.fmat, self.fsmooth, self.fuv, self.mats = [], [], [], [], [], []

    def mi(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)

    def face(self, pts, m, smooth=False, uv=None):
        i0 = len(self.verts); self.verts += [tuple(p) for p in pts]
        self.faces.append(tuple(range(i0, i0 + len(pts)))); self.fmat.append(self.mi(m)); self.fsmooth.append(smooth)
        self.fuv.append(uv or [(0, 0)] * len(pts))

    def box(self, x0, y0, z0, x1, y1, z1, m, T=None, top_uv=None, skip_bottom=True, mtop=None):
        c = [Vector(v) for v in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        if T: c = [T @ v for v in c]
        quads = [((4, 5, 6, 7), "top"), ((0, 1, 5, 4), "s"), ((1, 2, 6, 5), "s"), ((2, 3, 7, 6), "s"), ((3, 0, 4, 7), "s")]
        if not skip_bottom: quads.append(((3, 2, 1, 0), "b"))
        for q, k in quads:
            uv = top_uv if (k == "top" and top_uv) else None
            self.face([c[i] for i in q], (mtop or m) if k == "top" else m, uv=uv)

    def cyl(self, r, z0, z1, m, T=None, seg=24, r_top=None, cap=True, mcap=None, cap_uv=False, open_bottom=True):
        """A cylinder along z from z0 to z1 round (0, 0), then moved by T."""
        rt = r if r_top is None else r_top
        ring0 = [Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z0)) for i in range(seg)]
        ring1 = [Vector((rt * math.cos(2 * math.pi * i / seg), rt * math.sin(2 * math.pi * i / seg), z1)) for i in range(seg)]
        if T: ring0 = [T @ v for v in ring0]; ring1 = [T @ v for v in ring1]
        for i in range(seg):
            j = (i + 1) % seg
            self.face([ring0[i], ring0[j], ring1[j], ring1[i]], m, smooth=True)
        if cap:
            uv = [(0.5 + 0.5 * math.cos(2 * math.pi * i / seg), 0.5 + 0.5 * math.sin(2 * math.pi * i / seg)) for i in range(seg)] if cap_uv else None
            self.face(ring1, mcap or m, uv=uv)
            if not open_bottom: self.face(list(reversed(ring0)), m)

    def tube(self, pts, r, m, seg=10):
        """A round tube through points (a wire, a heat pipe)."""
        pts = [Vector(p) for p in pts]
        prev = None
        for k in range(len(pts)):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            a = t.cross(up).normalized(); b = t.cross(a).normalized()
            ring = [pts[k] + (a * math.cos(2 * math.pi * i / seg) + b * math.sin(2 * math.pi * i / seg)) * r for i in range(seg)]
            if prev:
                for i in range(seg):
                    j = (i + 1) % seg
                    self.face([prev[i], prev[j], ring[j], ring[i]], m, smooth=True)
            prev = ring

    def build(self, name, bevel=0.0, coll=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata([(v[0] * MM, v[1] * MM, v[2] * MM) for v in self.verts], [], self.faces)
        for mm_ in self.mats: me.materials.append(mm_)
        uvl = me.uv_layers.new()
        for p, mi, sm, uv in zip(me.polygons, self.fmat, self.fsmooth, self.fuv):
            p.material_index = mi; p.use_smooth = sm
            for li, (u, v) in zip(p.loop_indices, uv): uvl.data[li].uv = (u, v)
        me.validate(); me.update()
        o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
        if bevel:
            # merge the shared corners first so the bevel rounds edges, then bevel by angle
            import bmesh
            bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bm.to_mesh(me); bm.free()
            md = o.modifiers.new("bevel", "BEVEL"); md.width = bevel * MM; md.segments = 2; md.limit_method = "ANGLE"
            md.harden_normals = False
        return o

def R(deg, axis="Z"): return Matrix.Rotation(math.radians(deg), 4, axis)
def Tr(x, y, z): return Matrix.Translation((x, y, z))

# ------------------------------------------------------------------ the board
def board(m):
    W, H, T = LAY.BOARD_W, LAY.BOARD_H, LAY.BOARD_T
    top = tex_mat("Board_top", os.path.join(TEX, "board_basecolor.jpg"), os.path.join(TEX, "board_mr.jpg"), os.path.join(TEX, "board_normal.jpg"))
    b = MB()
    b.face([(0, -H, T), (W, -H, T), (W, 0, T), (0, 0, T)], top, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for q in (((0, 0, 0), (W, 0, 0), (W, 0, T), (0, 0, T)), ((W, 0, 0), (W, -H, 0), (W, -H, T), (W, 0, T)),
              ((W, -H, 0), (0, -H, 0), (0, -H, T), (W, -H, T)), ((0, -H, 0), (0, 0, 0), (0, 0, T), (0, -H, T))):
        b.face(q, m["fr4_edge"])
    b.face([(0, 0, 0), (W, 0, 0), (W, -H, 0), (0, -H, 0)], m["pcb_black"])
    b.build("board")
    # surface-mount parts (positions from make_board_texture.py)
    smd = json.load(open(os.path.join(TOOLS, "smd_parts.json"), encoding="utf-8"))["parts"]
    s = MB(); rng = random.Random(3)
    for p in smd:
        x, y, rot, t = p["x"], -p["y"], p["rot"], p["type"]
        Tm = Tr(x, y, T) @ R(rot)
        if t in ("r0402", "c0402", "r0603", "c0603", "c0805", "led0603"):
            l, w, h = {"r0402": (1.0, 0.5, 0.35), "c0402": (1.0, 0.5, 0.5), "r0603": (1.6, 0.8, 0.45), "c0603": (1.6, 0.8, 0.8),
                       "c0805": (2.0, 1.25, 1.0), "led0603": (1.6, 0.8, 0.6)}[t]
            body = {"r": m["resistor"], "c": m["ceramic_cap"], "l": m["led_off"]}[t[0]]
            e = l * 0.2
            s.box(-l / 2 + e, -w / 2, 0, l / 2 - e, w / 2, h, body, Tm)
            for sx_ in (-1, 1):
                s.box(sx_ * l / 2 - (e if sx_ > 0 else 0), -w / 2, 0, sx_ * l / 2 + (0 if sx_ > 0 else e), w / 2, h, m["solder"], Tm)
            if t == "led0603":
                lit = rng.random() < 0.45 and not OFF[0]
                s.box(-l * 0.25, -w * 0.4, h, l * 0.25, w * 0.4, h + 0.15, (m["led_green"] if rng.random() < 0.6 else m["led_blue"]) if lit else m["led_off"], Tm)
        elif t == "qfn32":
            s.box(-2.5, -2.5, 0, 2.5, 2.5, 0.9, m["chip"], Tm)
            s.cyl(0.35, 0.9, 0.92, m["grey_plastic"], Tm @ Tr(-1.8, 1.8, 0), seg=10)             # pin-1 dot
        else:
            bw, bd, bh, n, pitch = {"tssop16": (5.0, 4.4, 1.1, 8, 0.65), "soic8": (4.9, 3.9, 1.5, 4, 1.27), "sot23": (2.9, 1.3, 1.0, 2, 1.9)}[t]
            s.box(-bw / 2, -bd / 2, 0.1, bw / 2, bd / 2, bh, m["chip"], Tm)
            for i in range(n):
                o = (i - (n - 1) / 2) * pitch
                for sy_ in (-1, 1):
                    if t == "sot23" and sy_ > 0 and i > 0: continue
                    xx = 0 if (t == "sot23" and sy_ > 0) else o
                    s.box(xx - 0.15, sy_ * bd / 2, 0, xx + 0.15, sy_ * (bd / 2 + 0.7), 0.45, m["solder"], Tm)
    # debug LEDs by the 24-pin: dark, or the failing stage's lit red
    for name, lx, ly in LAY.DEBUG_LEDS:
        Tm_ = Tr(lx, -ly, T)
        s.box(-0.8, -0.4, 0, -0.5, 0.4, 0.6, m["solder"], Tm_); s.box(0.5, -0.4, 0, 0.8, 0.4, 0.6, m["solder"], Tm_)
        lit = DBG[0] == name and not OFF[0]
        s.box(-0.5, -0.4, 0, 0.5, 0.4, 0.6, mat("Debug_LED_red_lit", (1.0, 0.15, 0.1), 0.3, emit=(1.0, 0.12, 0.05), strength=80.0) if lit
              else mat("Debug_LED_red_dark", (0.45, 0.08, 0.06), 0.3), Tm_)
    s.build("smd_parts")

# ------------------------------------------------------------------ parts
def cpu_socket(m, clean=False):
    """LGA socket, load plate closed, lever latched, a CPU in it with thermal paste on the lid. Top of the lid: 5.3 mm."""
    b = MB()
    b.box(-28, -32, 0, 28, 32, 2.6, m["black_plastic"])                      # socket body / frame on the board
    b.box(-24, -27, 2.6, 24, 27, 4.0, m["grey_plastic"])                     # CPU substrate edge (green-grey)
    lid = tex_mat("CPU_lid", os.path.join(TEX, "cpu_lid.png"), rough=0.42, metal=0.9) if clean else None
    b.box(-18.75, -18.75, 4.0, 18.75, 18.75, 5.3, m["nickel"], mtop=lid, top_uv=[(0, 0), (1, 0), (1, 1), (0, 1)] if clean else None)   # lid (IHS)
    # load plate: a stainless frame round the lid
    for x0, y0, x1, y1 in ((-27, -31, 27, -20.5), (-27, 20.5, 27, 31), (-27, -20.5, -20.5, 20.5), (20.5, -20.5, 27, 20.5)):
        b.box(x0, y0, 3.2, x1, y1, 4.6, m["steel"])
    for x in (-25, 25):                                                      # hinge / screw lugs
        b.cyl(1.8, 0, 5.0, m["steel"], Tr(x, -31.5, 0), seg=16)
    # lever: latched flat along the +x side, with its hook
    b.tube([(30.5, -33, 2.2), (30.5, 30, 2.2), (35, 33, 2.2)], 0.9, m["steel"])
    b.box(29, 26, 0, 33, 33, 2.0, m["steel"])
    b.build("socket", bevel=0.25)
    if clean: return
    # thermal paste: a thin smear left on the lid after the cooler came off, thicker towards the middle
    pm = MB(); rng = random.Random(11)
    for i in range(46):
        a = rng.random() * 2 * math.pi; r = 11 * math.sqrt(rng.random())
        x, y = r * math.cos(a), r * math.sin(a); rr = rng.uniform(3.0, 6.0)
        th = 0.03 + 0.09 * max(0.0, 1 - r / 12)
        pm.cyl(rr, 5.3, 5.3 + th, m["paste"], Tr(x, y, 0), seg=28, r_top=rr * 0.92)
    pm.build("paste")

def tower_cooler(m):
    """Single tower cooler: copper base on the CPU, four heat pipes, 56 aluminium fins, 120 mm fan on the +x side."""
    b = MB()
    b.box(-20, -20, 0, 20, 20, 4, m["copper"])                                # contact base
    b.box(-24, -22, 4, 24, 22, 10, m["nickel"])                               # base block
    b.box(-36, -5, 7, 36, 5, 10, m["steel_dark"])                             # mounting bar
    for x in (-36, 36): b.cyl(2.6, 0, 10, m["steel_dark"], Tr(x, 0, 0), seg=12)
    fx0, fx1, fy = -25, 25, 62.5
    for i in range(56):                                                       # fins
        z = 40 + i * 2.05
        b.box(fx0, -fy, z, fx1, fy, z + 0.4, m["alu"], skip_bottom=False)
    b.box(fx0, -fy, 155, fx1, fy, 158, m["black_matte"], skip_bottom=False)  # top cover
    for k, (yy, xo) in enumerate(((-24, -6), (-8, 6), (8, -6), (24, 6))):  # heat pipes (U through the fins)
        b.tube([(xo, yy, 5), (xo, yy, 20), (xo, yy * 2.3, 40), (xo, yy * 2.3, 157)], 3.0, m["copper"], seg=12)
        b.tube([(xo, yy, 5), (xo, -yy * 0.2, 6)], 3.0, m["copper"], seg=12)
    # fan on the +x face
    fan(b, m, Tr(fx1 + 12.5, 0, 98) @ R(90, "Y"), size=120, depth=25)
    b.build("cooler", bevel=0.0)

def fan(b, m, T, size=120, depth=25, rgb=None, blades=9, spun=None):
    """spun: True = blades left out (a live rotor turns here), False = blades drawn; None = follow BLADES (model-wide)."""
    """A case fan centred on T's origin, axis along T's z."""
    h = size / 2; d2 = depth / 2; r_in = size * 0.47
    for x0, y0, x1, y1 in ((-h, -h, h, -r_in * 0.9), (-h, r_in * 0.9, h, h), (-h, -r_in * 0.9, -r_in * 0.9, r_in * 0.9), (r_in * 0.9, -r_in * 0.9, h, r_in * 0.9)):
        b.box(x0, y0, -d2, x1, y1, d2, m["black_plastic"], T, skip_bottom=False)
    b.cyl(r_in, -d2, d2, m["black_plastic"], T, seg=48, cap=False)
    b.cyl(size * 0.17, -d2 + 2, d2 - 2, m["black_matte"], T, seg=32, open_bottom=False)
    show = BLADES[0] if spun is None else not spun
    for i in range(blades if show else 0):                                   # blades: twisted quads (left out for the live spinners)
        a0 = 2 * math.pi * i / blades
        pts = []
        for (rr, aa, zz) in ((size * 0.17, a0, -6), (r_in - 1.5, a0 + 0.35, -3), (r_in - 1.5, a0 + 0.95, 3), (size * 0.17, a0 + 0.75, 6)):
            pts.append(T @ Vector((rr * math.cos(aa), rr * math.sin(aa), zz)))
        b.face(pts, m["fan_blade"]); b.face(list(reversed(pts)), m["fan_blade"])
    for k in range(4):                                                      # struts at the back
        a = math.pi / 4 + k * math.pi / 2
        b.box(size * 0.16, -1.2, -d2, r_in, 1.2, -d2 + 2, m["black_plastic"], T @ R(math.degrees(a)))
    if rgb:
        b.cyl(r_in + 1.2, d2, d2 + 0.6, rgb, T, seg=48, r_top=r_in + 1.2, cap=False)
        b.cyl(r_in + 1.4, d2 - 0.2, d2 + 0.6, rgb, T, seg=48, cap=False)

def fan_rotor(m, size=120, blades=9):
    """Just the turning part of a fan (hub and blades), axis front-back (y), for the tour to spin over an "_on" render."""
    b = MB(); T = R(-90, "X"); r_in = size * 0.47
    b.cyl(size * 0.17, -10, 10, m["black_matte"], T, seg=32, open_bottom=False)
    for i in range(blades):
        a0 = 2 * math.pi * i / blades
        pts = [T @ Vector((rr * math.cos(aa), rr * math.sin(aa), zz)) for (rr, aa, zz) in
               ((size * 0.17, a0, -6), (r_in - 1.5, a0 + 0.35, -3), (r_in - 1.5, a0 + 0.95, 3), (size * 0.17, a0 + 0.75, 6))]
        b.face(pts, m["fan_blade"]); b.face(list(reversed(pts)), m["fan_blade"])
    rt = r_in - 1.5                                                          # four specks at the tip radius: the model's bounds are then
    for a in (0, 90, 180, 270):                                              # centred on the hub, so it spins true and sits where it should
        c = T @ Vector((rt * math.cos(math.radians(a)), rt * math.sin(math.radians(a)), 0))
        b.face([c, c + Vector((0.02, 0, 0)), c + Vector((0, 0.02, 0.02))], m["fan_blade"])
    b.build("fan_rotor")

def dimm(m):
    """DDR5 stick with heat spreader and an RGB light bar on top. 133.35 long, 7 thick, 44 tall (from the slot floor)."""
    b = MB()
    b.box(-66.7, -0.65, 0, 66.7, 0.65, 31.25, m["pcb_black"])                   # module PCB
    for i in range(80):                                                     # gold fingers (just above the slot)
        x = -64 + i * 1.62
        if abs(x + 3) < 1.5: continue                                       # the key notch
        for s_ in (-1, 1): b.box(x, s_ * 0.65, 0.3, x + 0.9, s_ * 0.7, 4.0, m["gold"])
    label = tex_mat("DIMM_label", os.path.join(TEX, "dimm_label.jpg"), rough=0.5)
    for s_ in (-1, 1):                                                     # spreader plates
        y0, y1 = (0.65, 3.3) if s_ > 0 else (-3.3, -0.65)
        b.box(-67.5, y0, 5.5, 67.5, y1, 38.5, m["gunmetal"])
        for k in range(5):                                                   # sculpted ridges
            b.box(-60 + k * 26, (y1 if s_ > 0 else y0) - 0.01 * s_, 26, -42 + k * 26, (y1 + 0.5) if s_ > 0 else (y0 - 0.5), 36, m["alu_brushed"])
        yy = y1 + 0.02 if s_ > 0 else y0 - 0.02                              # sticker
        pts = [(-30, yy, 8), (30, yy, 8), (30, yy, 21.5), (-30, yy, 21.5)] if s_ > 0 else [(30, yy, 8), (-30, yy, 8), (-30, yy, 21.5), (30, yy, 21.5)]
        # seen from outside, +x is on the viewer's right on the -y side and on the left on the +y side
        b.face(pts, label, uv=[(1, 0), (0, 0), (0, 1), (1, 1)])
    b.box(-67.5, -3.3, 38.5, 67.5, 3.3, 39.5, m["gunmetal"])
    segs = (m["rgb_cyan"], m["rgb_violet"], m["rgb_magenta"], m["rgb_violet"], m["rgb_cyan"])
    for i, sm in enumerate(segs):                                          # light bar
        x0 = -66 + i * 26.4
        b.box(x0, -2.6, 39.5, x0 + 26.4, 2.6, 44, sm)
    b.build("dimm", bevel=0.3)

def dimm_slot(m, open_clips=False):
    """Black DIMM slot, 146 long, with latching clips at both ends (closed) and gold contacts in the groove."""
    b = MB(); L2 = 73
    b.box(-63, -3.15, 0, 63, -1.0, 7.0, m["black_plastic"]); b.box(-63, 1.0, 0, 63, 3.15, 7.0, m["black_plastic"])
    b.box(-63, -1.0, 0, 63, 1.0, 1.2, m["black_plastic"])                      # groove floor
    b.box(-4, -1.0, 0, -2, 1.0, 5.0, m["black_plastic"])                       # key
    for i in range(70):
        x = -61 + i * 1.75
        for s_ in (-1, 1): b.box(x, s_ * 1.0 - 0.15 * s_, 1.2, x + 0.5, s_ * 1.0, 4.5, m["gold"])
    # clips (latches), light grey so they show against the black stick. In each end's frame +x points away from the slot's
    # middle. Shut: the lever stands upright and its hook reaches in over the end of the stick. Open: the lever swings
    # outwards (away from the stick) about its foot, hook clear.
    clip = mat("Clip_light_grey", (0.62, 0.63, 0.65), 0.45)
    for s_ in (-1, 1):
        T = Tr(s_ * 68, 0, 0) @ R(0 if s_ > 0 else 180)
        b.box(-5, -3.15, 0, 3, 3.15, 6.0, m["black_plastic"], T)
        ang = 40 if open_clips else 0
        Tc = T @ Tr(2.5, 0, 3.0) @ R(ang, "Y") @ Tr(-2.5, 0, -3.0)          # pivot at the lever's outer foot
        b.box(1.0, -2.6, 3.0, 4.0, 2.6, 17.0, clip, Tc)                         # the lever
        b.box(-1.8, -2.6, 13.5, 1.0, 2.6, 17.0, clip, Tc)                       # its hook, over the stick's end when shut
        b.box(4.0, -2.0, 12.0, 6.5, 2.0, 17.0, clip, Tc)                        # the thumb tab on the outside
    b.build("dimm_slot", bevel=0.25)

def vrm_heatsink(m, length):
    """Finned heatsink over the VRM, sitting on a row of chokes. length along x, 17 deep, 34 tall."""
    b = MB(); h = length / 2
    n = int(length / 11.5)
    for i in range(n):                                                         # chokes underneath
        x = -h + 5 + i * (length - 10) / max(1, n - 1)
        b.box(x - 5, -8, 0, x + 5, 2, 7, m["ferrite"])
    b.box(-h, -8.5, 7, h, 8.5, 14, m["gunmetal"])                              # base
    fins = int(length / 2.6)
    for i in range(fins):
        x = -h + 0.6 + i * (length - 1.2) / max(1, fins - 1)
        b.box(x - 0.6, -8.5, 14, x + 0.6, 8.5, 31, m["gunmetal"])
    b.box(-h, -8.5, 31, h, 8.5, 34, m["alu_brushed"], mtop=m["gunmetal"])      # top cap
    b.build("vrm_heatsink", bevel=0.3)

def cap(m, d, hgt, top):
    b = MB()
    b.box(-d / 2 - 0.3, -d / 2 - 0.3, 0, d / 2 + 0.3, d / 2 + 0.3, 0.9, m["black_plastic"])   # seat plate
    b.cyl(d / 2, 0.9, hgt - 0.6, m["alu"], seg=32, cap=False)
    b.cyl(d / 2 - 0.25, hgt - 0.6, hgt - 0.35, m["alu"], seg=32, cap=False)                 # rolled top edge
    b.cyl(d / 2 - 0.35, hgt - 0.35, hgt, m["alu"], seg=32, mcap=tex_mat("Cap_" + top, os.path.join(TEX, top + ".png"), rough=0.35, metal=0.8), cap_uv=True)
    b.build("cap", bevel=0.0)

def power_plug(m, pins, rows=2, height_up=150, bend_to=(0, -1), colours=None, drop_at=None):
    """A PSU plug in its header with wires rising out of it and bending away as a sleeved bundle.
    drop_at: instead of rising out of view, the bundle arches over and drops through the case floor that far
    (mm) away in the bend_to direction, ending 7.6 mm below the board's surface (the tray), with a grommet."""
    b = MB(); n = pins // rows; pitch = 4.2
    L2 = n * pitch / 2 + 1
    b.box(-L2, -5, 0, L2, 5, 6.5, m["white_plastic"] if pins == 24 else m["black_plastic"])   # header on the board
    b.box(-L2 + 0.3, -4.7, 6.5, L2 - 0.3, 4.7, 20, m["black_plastic"])                          # plug
    b.box(-3, 4.7, 9, 3, 6.6, 17, m["black_plastic"])                                          # latch
    wires = colours or ["yellow", "black", "red", "orange", "black", "red", "black", "green"]
    cols = {"yellow": (0.8, 0.65, 0.05), "black": (0.02, 0.02, 0.02), "red": (0.6, 0.03, 0.02), "orange": (0.8, 0.3, 0.02),
            "green": (0.05, 0.4, 0.08), "grey": (0.3, 0.3, 0.3), "purple": (0.3, 0.05, 0.4), "blue": (0.03, 0.1, 0.5), "white": (0.8, 0.8, 0.78)}
    bx, by = bend_to
    for i in range(n):
        for r in range(rows):
            x = -n * pitch / 2 + pitch / 2 + i * pitch; y = -2.1 + r * 4.2
            c = wires[(i * rows + r) % len(wires)]
            wm = mat("Wire_" + c, cols[c], 0.45)
            bundle_x, bundle_y = x * 0.35, y * 0.35
            pts = [(x, y, 20), (x, y, 30), (bundle_x, bundle_y, 45), (bundle_x, bundle_y, 60)]
            b.tube(pts, 0.85, wm, seg=8)
    # sleeved bundle: up, then bending away (bend_to), out of view
    rb = max(4.0, n * pitch * 0.22)
    if drop_at:
        top = 72.0; r = drop_at / 2
        path = [(0, 0, 55), (0, 0, top - r * 0.6)]
        for k in range(1, 13):                                              # half-round arch over to the grommet
            a = k / 12 * math.pi
            d = r * (1 - math.cos(a)); z = top - r * 0.6 + r * 0.6 * math.sin(a) * 1.0 + (0 if a < math.pi / 2 else 0)
            path.append((bx * d, by * d, z))
        path += [(bx * drop_at, by * drop_at, 20), (bx * drop_at, by * drop_at, -7.6)]
        b.cyl(rb + 4, -7.6, -6.9, m["rubber"], Tr(bx * drop_at, by * drop_at, 0), seg=24)
    else:
        z0, rad = 55 + height_up * 0.35, 40
        path = [(0, 0, 55), (0, 0, z0)]
        for k in range(1, 13):
            a = k / 12 * math.pi / 2
            path.append((bx * rad * (1 - math.cos(a)), by * rad * (1 - math.cos(a)), z0 + rad * math.sin(a)))
        path.append((bx * (rad + height_up), by * (rad + height_up), z0 + rad))
    b.tube(path, rb, m["sleeve"], seg=16)
    b.build("power_plug", bevel=0.2)

def rear_io(m):
    """The rear I/O stack under a sculpted shroud: 22 deep (x), 150 long (y), 42 tall."""
    b = MB()
    b.box(-11, -75, 0, 11, 75, 38, m["steel_dark"])                             # port stack
    b.box(-9, -76, 0, 12, 76, 42, m["gunmetal"])                                # shroud
    for k in range(6):
        b.box(12, -70 + k * 24, 6, 12.6, -54 + k * 24, 36, m["alu_brushed"])    # sculpted vents
    for k in range(8):                                                          # ports showing at the back (USB, LAN, audio)
        y = -66 + k * 17
        b.box(-11.6, y - 6, 6, -11, y + 6, 18, m["black_plastic"]); b.box(-11.6, y - 6, 22, -11, y + 6, 34, m["black_plastic"])
    b.build("rear_io", bevel=0.4)

def pcie_slot(m, length, x16=True):
    b = MB(); h = length / 2
    b.box(-h, -4, 0, h, -1, 11, m["black_plastic"]); b.box(-h, 1, 0, h, 4, 11, m["black_plastic"])
    b.box(-h, -1, 0, h, 1, 2, m["black_plastic"])
    if x16:                                                                     # steel armour
        b.box(-h + 1, -4.4, 3, h - 6, -4.0, 11.4, m["steel"]); b.box(-h + 1, 4.0, 3, h - 6, 4.4, 11.4, m["steel"])
        b.box(-h + 1, -4.4, 11, h - 6, 4.4, 11.4, m["steel"])
        b.box(h - 6, -4.5, 0, h + 4, 4.5, 12, m["grey_plastic"])                 # latch
    for i in range(int(length / 1.0) - 6):
        x = -h + 2 + i * 1.0
        for s_ in (-1, 1): b.box(x, s_ * 1.0 - 0.15 * s_, 2, x + 0.4, s_ * 1.0, 8, m["gold"])
    b.build("pcie_slot", bevel=0.2)

def gpu(m):
    """A compact two-fan graphics card standing in a PCIe x16 slot: 200 long, 112 tall, 48 thick.
    The card's circuit board is at y = +22 (on the slot); the fans face -y (towards the board's bottom edge)."""
    b = MB()
    b.box(-100, 20.5, 0, 98, 22.1, 108, m["pcb_black"])                          # card PCB
    for i in range(60): b.box(-80 + i * 1.2, 20.3, 0, -79.5 + i * 1.2, 22.3, 7, m["gold"])  # fingers
    b.box(-100, 22.1, 3, 98, 24.5, 110, m["gunmetal"])                           # backplate (seen from above the card)
    for k in range(7): b.box(-90 + k * 26, 24.5, 30, -74 + k * 26, 25.0, 90, m["alu_brushed"])
    b.box(-100, -24, 3, 100, 20.5, 112, m["black_matte"])                        # shroud and cooler
    for x in (-48, 48):
        fan(b, m, Tr(x, -24.2, 58) @ R(90, "X"), size=88, depth=8, blades=11)
    b.box(60, 0, 112, 84, 14, 118, m["black_plastic"])                           # 8-pin power on top
    b.box(-118, 18, -15, -100, 22, 120, m["steel"])                              # bracket (into the case's slot)
    b.build("gpu", bevel=0.4)

def chipset_heatsink(m):
    b = MB()
    b.box(-22, -22, 0, 22, 22, 4, m["gunmetal"])
    for i in range(9): b.box(-22, -20 + i * 5, 4, 22, -17.6 + i * 5, 9, m["gunmetal"])
    b.box(-14, -14, 9, 14, 14, 9.4, m["alu_brushed"])
    b.build("chipset_heatsink", bevel=0.3)

def cmos_battery(m):
    b = MB()
    b.box(-11.5, -11.5, 0, 11.5, 11.5, 1.2, m["black_plastic"])
    b.cyl(10, 1.2, 4.4, m["steel"], seg=48, mcap=tex_mat("Battery_top", os.path.join(TEX, "battery_top.png"), rough=0.3, metal=0.9), cap_uv=True)
    b.box(-2.5, -12.5, 1.2, 2.5, -8, 5.5, m["steel"])                            # retaining spring clip
    b.build("cmos_battery", bevel=0.15)

def sata_ports(m):
    b = MB()
    for k in range(2):
        for j in range(2):
            y = -8 + k * 16; z = j * 7.2
            b.box(-7, y - 7, z, 7, y + 7, z + 6.6, m["black_plastic"])
            b.box(6.9, y - 4.5, z + 1.8, 7.1, y + 4.5, z + 4.8, m["black_matte"])
    b.build("sata", bevel=0.2)

def m2_ssd(m):
    b = MB()
    b.box(-43, -11, 0, -37, 11, 4.2, m["black_plastic"])                          # slot connector
    b.box(-41, -11, 1.8, 40, 11, 2.6, m["pcb_black"])                             # SSD board
    b.box(36, -3, 0, 42, 3, 1.8, m["steel"]); b.cyl(2.7, 2.6, 3.4, m["steel"], Tr(40, 0, 0), seg=16)   # standoff + screw
    lab = tex_mat("SSD_label", os.path.join(TEX, "ssd_label.jpg"), rough=0.45)
    b.box(-32, -10, 2.6, 33, 10, 2.75, m["black_matte"], top_uv=[(0, 0), (1, 0), (1, 1), (0, 1)], mtop=lab)
    b.build("m2_ssd", bevel=0.1)

def case_shell(m, v2=False, light=True, spun=None):
    """The case round the board, in board coordinates (z = 0 under the board). The board sits on 6 mm standoffs over
    the tray. Rear panel (x < 0) with the I/O cutout and an exhaust fan, top panel (y > 0) with two fans, front panel
    (x > 330) with three RGB fans, PSU shroud along the bottom. The side (z = 210) is left open, with a daylight panel
    outside it off to one side (the window of the room the PC is in).
    spun: for v2, a string of 0/1 per fan in board_layout.FANS_V2 order (front 0-2, top 0-1, rear): 1 = blades left out
    because the tour spins a live rotor there (model id tpc_case_shell_v2_on_<mask>, made per stop by check_rotors.py).
    v2: 92 mm fans mounted low on the front and top panels (so they land on the projected walls, which stop about
    20 degrees above eye level), and a wider case (front panel at x = 520) so the overview stop can stand on the case
    floor in front of the board."""
    b = MB(); W, H = LAY.BOARD_W, LAY.BOARD_H
    x0, x1, y0, y1, zt, zz = -20, (520 if v2 else 405), -470, 60, -7, 215          # inner walls; tray top at z = -6
    b.box(x0 - 2, y0 - 2, zt, x1 + 2, y1 + 2, -6, m["case_steel"])                 # tray
    Y = LAY.Y_SHIFT                                                               # brass standoffs under the mounting holes
    for sx, sy in ((8, 8 + Y), (160, 8 + Y), (322, 8 + Y), (8, 175 + Y), (140, 140 + Y), (322, 175 + Y), (8, H - 8), (160, H - 8), (322, H - 8)):
        b.cyl(3.0, -6, 0, m["solder"], Tr(sx, -sy, 0), seg=6)
    b.box(x0 - 2, y0, zt, x0, y1, zz, m["case_steel"])                             # rear panel
    b.box(x0, y1, zt, x1, y1 + 2, zz, m["case_steel"])                             # top panel
    b.box(x1, y0, zt, x1 + 2, y1, zz, m["case_steel"])                             # front panel
    b.box(x0, y0 - 2, zt, x1, y0, zz, m["case_steel"])                             # bottom panel
    b.box(x0, y0, -6, x1, -360, 92, m["case_steel"])                               # PSU shroud
    b.box(x0, -362, 92, x1, -360, 94, m["black_matte"])
    for k in range(7):                                                            # PCIe slot covers in the rear panel
        b.box(x0 - 0.5, -(225 + k * 20.3) - 7, 15, x0 + 0.4, -(225 + k * 20.3) + 7, 120, m["steel"])
    sp = (lambda i: None) if spun is None else (lambda i: spun[i] == "1")
    fan(b, m, Tr(x0 + 13, -100, 110) @ R(90, "Y"), size=120, depth=25, spun=sp(5))   # rear exhaust
    if v2:
        for k in range(2): fan(b, m, Tr(90 + k * 130, y1 - 13, 43) @ R(90, "X"), size=92, depth=25, rgb=m["rgb_violet"], spun=sp(3 + k))   # top, low
        for k in range(3): fan(b, m, Tr(x1 - 13, -60 - k * 105, 43) @ R(-90, "Y"), size=92, depth=25, rgb=m["rgb_cyan"], spun=sp(k))      # front, low
        for i in range(14):                                                       # vent slots and a cable cut-out in the shroud top
            for j in range(3):
                b.box(40 + i * 22, -395 - j * 9, 92, 56 + i * 22, -391 - j * 9, 92.3, m["black_matte"])
        b.box(300, -372, 92, 380, -362, 92.3, m["rubber"])
        for i in range(10):                                                       # tray details in front of the board
            b.box(372, -40 - i * 40, -6, 378, -24 - i * 40, -5.7, m["black_matte"])  # cable-tie slots
        b.box(430, -330, -6, 500, -250, -5.8, m["steel_dark"])                    # drive-cage foot plate
        # a second, dimmer daylight panel on the front side (high up, out of the projected area): fill light so
        # faces turned to the front aren't silhouettes
        if light: b.face([(1150, 250, 1500), (1150, -750, 1500), (1000, -750, 1000), (1000, 250, 1000)], mat("Daylight_fill", (1, 1, 1), 1.0, emit=(1.0, 0.96, 0.9), strength=4.0))
    else:
        for k in range(2): fan(b, m, Tr(90 + k * 130, y1 - 13, 110) @ R(90, "X"), size=120, depth=25, rgb=m["rgb_violet"])   # top
        for k in range(3): fan(b, m, Tr(x1 - 13, -60 - k * 125, 110) @ R(-90, "Y"), size=120, depth=25, rgb=m["rgb_cyan"])  # front
    for k in range(3):                                                            # rubber cable grommets in the tray, front side
        b.box(345, -(70 + k * 90) - 18, -6, 360, -(70 + k * 90) + 18, -5.4, m["rubber"])
    # daylight from the room, through the open side, off the zenith
    if light: b.face([(-450, -750, 1500), (-450, 250, 1500), (-300, 250, 1000), (-300, -750, 1000)], m["daylight"])   # high up: out of the projected area
    b.build("case_shell")


# ------------------------------------------------------------------ workbench room: loose parts and the PC on the bench
def Tm(x, y, z): return Matrix.Translation((x * MM, y * MM, z * MM))

def transformed(build, M):
    """Run a model function and move everything it made by M (metres)."""
    before = set(bpy.data.objects)
    build()
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o not in before]:
        o.matrix_world = M @ o.matrix_world

def cpu_socket_empty(m):
    """The socket with no CPU: the field of spring pins showing, load plate and lever up."""
    b = MB()
    b.box(-28, -32, 0, 28, 32, 2.6, m["black_plastic"])
    pins = tex_mat("Socket_pins", os.path.join(TEX, "socket_pins.png"), rough=0.35, metal=0.6)
    b.face([(-21, -21, 2.61), (21, -21, 2.61), (21, 21, 2.61), (-21, 21, 2.61)], pins, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for x0, y0, x1, y1 in ((-24, -26, 24, -21), (-24, 21, 24, 26), (-24, -21, -21, 21), (21, -21, 24, 21)):
        b.box(x0, y0, 2.6, x1, y1, 4.2, m["black_plastic"])                 # the walls the CPU drops between
    b.box(-24, 11, 2.6, -21, 14, 4.6, m["grey_plastic"])                     # key notches
    b.box(21, 11, 2.6, 24, 14, 4.6, m["grey_plastic"])
    T = Tr(0, -31, 4.0) @ R(112, "X") @ Tr(0, 31, -4.0)                      # load plate swung open on its hinge
    for x0, y0, x1, y1 in ((-27, -31, 27, -20.5), (-27, 20.5, 27, 31), (-27, -20.5, -20.5, 20.5), (20.5, -20.5, 27, 20.5)):
        b.box(x0, y0, 3.2, x1, y1, 4.6, m["steel"], T, skip_bottom=False)
    for x in (-25, 25): b.cyl(1.8, 0, 5.0, m["steel"], Tr(x, -31.5, 0), seg=16)
    b.tube([(30.5, -33, 2.2), (30.5, -33 + 60 * math.cos(math.radians(80)), 2.2 + 60 * math.sin(math.radians(80)))], 0.9, m["steel"])  # lever up
    b.box(29, 26, 0, 33, 33, 2.0, m["steel"])
    b.build("socket_empty", bevel=0.25)

def cpu(m):
    """A loose CPU: green substrate with gold pads underneath, etched lid on top (generic markings). 45 x 37.5 mm."""
    b = MB()
    pads = tex_mat("CPU_pads", os.path.join(TEX, "cpu_pads.png"), rough=0.4)
    lid = tex_mat("CPU_lid", os.path.join(TEX, "cpu_lid.png"), rough=0.42, metal=0.9)
    b.box(-22.5, -18.75, 0, 22.5, 18.75, 1.1, mat("CPU_substrate", (0.06, 0.2, 0.1), 0.45), skip_bottom=True)
    b.face([(-22.5, 18.75, 0), (22.5, 18.75, 0), (22.5, -18.75, 0), (-22.5, -18.75, 0)], pads, uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
    b.box(-17, -16, 1.1, 17, 16, 2.6, m["nickel"])                            # lid skirt
    b.box(-16, -15.5, 2.6, 16, 15.5, 4.2, m["nickel"], mtop=lid, top_uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for i in range(14):                                                    # small capacitors on the substrate
        x = -20.5 + (i % 7) * 6.8
        b.box(x, 17.2 if i < 7 else -17.8, 1.1, x + 1.0, 17.7 if i < 7 else -17.3, 1.6, m["ceramic_cap"])
    b.build("cpu", bevel=0.2)

def glow_tex_mat(name, path, strength, rough=0.35):
    """An image texture that also glows a little (the X-ray die map has to read in the dark case)."""
    m = tex_mat(name, path, rough=rough)
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    t = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    k = "Emission Color" if "Emission Color" in b.inputs else "Emission"
    nt.links.new(t.outputs["Color"], b.inputs[k]); b.inputs["Emission Strength"].default_value = strength
    return m

LID_ANGLE = -145.0                       # degrees the peeled lid is turned back about its hinge (the +y edge)
def cpu_socket_open(m, xray=False, lid=True):
    """The CPU in its socket with the lid (heat spreader) peeled back over the +y edge, as if it could be: the green
    substrate, the 20 x 12 mm silicon chip with its solder (xray=False), or the chip's circuits drawn on its top as an
    X-ray map (xray=True). No load plate or lever, so nothing stands up round the edge. Substrate top 4.0 mm, chip top
    4.8 mm (solder 4.9)."""
    b = MB()
    b.box(-28, -32, 0, 28, 32, 2.6, m["black_plastic"])                      # socket body
    sub = tex_mat("CPU_substrate_tex", os.path.join(TEX, "cpu_substrate.png"), rough=0.5)
    b.box(-24, -27, 2.6, 24, 27, 4.0, mat("CPU_substrate", (0.06, 0.2, 0.1), 0.45), mtop=sub, top_uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    glue = mat("Lid_sealant", (0.02, 0.02, 0.02), 0.7)
    for x0, y0, x1, y1 in ((-18.75, -18.75, 18.75, -17.6), (-18.75, 17.6, 18.75, 18.75), (-18.75, -17.6, -17.6, 17.6), (17.6, -17.6, 18.75, 17.6)):
        b.box(x0, y0, 4.0, x1, y1, 4.1, glue)                                # where the lid was glued down
    for i in range(6):                                                       # small capacitors either side of the chip
        for sx in (-1, 1):
            y = -5 + i * 2.0
            b.box(sx * 14.5 - 0.5, y - 0.25, 4.0, sx * 14.5 + 0.5, y + 0.25, 4.5, m["ceramic_cap"])
            b.box(sx * 14.5 - 0.7, y - 0.25, 4.0, sx * 14.5 - 0.5, y + 0.25, 4.5, m["solder"])
            b.box(sx * 14.5 + 0.5, y - 0.25, 4.0, sx * 14.5 + 0.7, y + 0.25, 4.5, m["solder"])
    b.box(-10.4, -6.4, 4.0, 10.4, 6.4, 4.15, mat("Underfill", (0.12, 0.08, 0.05), 0.6))      # underfill round the chip's base
    sil = mat("Silicon_back", (0.09, 0.09, 0.11), 0.18, 0.6)
    if xray:
        top = glow_tex_mat("Die_map_xray", os.path.join(TEX, "die_map.png"), 0.9)
        b.box(-10, -6, 4.0, 10, 6, 4.8, sil, mtop=top, top_uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    else:
        b.box(-10, -6, 4.0, 10, 6, 4.8, sil)
        b.box(-9.7, -5.7, 4.8, 9.7, 5.7, 4.88, mat("Solder_TIM", (0.86, 0.87, 0.88), 0.55, 0.3))   # solder that joined it to the lid
        rng = random.Random(5)
        for _ in range(40):
            x, y = rng.uniform(-9, 9), rng.uniform(-5, 5); r = rng.uniform(0.3, 1.1)
            b.cyl(r, 4.88, 4.88 + rng.uniform(0.02, 0.06), mat("Solder_TIM", (0.86, 0.87, 0.88), 0.55, 0.3), Tr(x, y, 0), seg=14, r_top=r * 0.8)
    b.build("cpu_open", bevel=0.05)
    if not lid: return                                                       # the running PC's X-ray: no lid at all
    # the lid, built closed (underside at 4.9, top 5.3, rim down to 4.0) then turned back about its +y edge
    L = MB()
    under = tex_mat("Lid_underside", os.path.join(TEX, "lid_underside.png"), rough=0.4, metal=0.9)
    outer = tex_mat("CPU_lid", os.path.join(TEX, "cpu_lid.png"), rough=0.42, metal=0.9)
    h = 18.75
    L.face([(-h, -h, 5.3), (h, -h, 5.3), (h, h, 5.3), (-h, h, 5.3)], outer, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    L.face([(-h, h, 4.9), (h, h, 4.9), (h, -h, 4.9), (-h, -h, 4.9)], under, uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
    for x0, y0, x1, y1 in ((-h, -h, h, -h + 1.4), (-h, h - 1.4, h, h), (-h, -h + 1.4, -h + 1.4, h - 1.4), (h - 1.4, -h + 1.4, h, h - 1.4)):
        L.box(x0, y0, 4.0, x1, y1, 4.9, m["nickel"], skip_bottom=False)                  # the rim that sat on the substrate
    for q in (((-h, -h, 4.9), (h, -h, 4.9), (h, -h, 5.3), (-h, -h, 5.3)), ((h, -h, 4.9), (h, h, 4.9), (h, h, 5.3), (h, -h, 5.3)),
              ((h, h, 4.9), (-h, h, 4.9), (-h, h, 5.3), (h, h, 5.3)), ((-h, h, 4.9), (-h, -h, 4.9), (-h, -h, 5.3), (-h, h, 5.3))):
        L.face(q, m["nickel"])
    lid = L.build("lid_peeled")
    hinge = Vector((0, h * MM, 5.3 * MM))
    lid.matrix_world = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(LID_ANGLE), 4, "X") @ Matrix.Translation(-hinge)

def core_hall(m):
    """Backdrop for "Inside a core": a 14 m floor of standard-cell rows and copper wiring (tex/core_floor.png, glowing a
    little); nothing standing, so the live register diagram has the walls to itself. Built at real room size (scale 1); the register diagram is drawn
    live over it by the tour player."""
    b = MB(); H = 7000.0
    fl = glow_tex_mat("Core_floor", os.path.join(TEX, "core_floor.png"), 0.35, rough=0.6)
    b.face([(-H, -H, 0), (H, -H, 0), (H, H, 0), (-H, H, 0)], fl, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    b.build("core_hall")

def paste_syringe(m):
    b = MB()
    b.cyl(5, 0, 70, mat("Syringe_clear", (0.85, 0.87, 0.9), 0.15), Tr(0, 0, 5) @ R(90, "Y"), seg=24)
    b.cyl(4.2, 2, 68, m["paste"], Tr(0, 0, 5) @ R(90, "Y"), seg=24)
    b.cyl(1.5, 70, 80, m["grey_plastic"], Tr(0, 0, 5) @ R(90, "Y"), seg=12, r_top=0.8)
    b.box(-14, -9, 0, -10, 9, 10, m["grey_plastic"])                          # finger grip
    b.cyl(3, -40, 0, m["white_plastic"], Tr(0, 0, 5) @ R(90, "Y"), seg=16)   # plunger
    b.build("paste_syringe", bevel=0.2)

def pc_tower(m, built=True, power=False, step=None, fixed=False):
    """The PC on the bench: the same case, board and parts as inside, standing up with the side panel off.
    Open side towards -y (into the room), front of the case towards +x, standing on z = 0 on four feet.
    built=False: an empty case waiting for its CPU, cooler, RAM, SSD, graphics card and power cables."""
    FEET = 18
    Mb = Tm(0, 0, 472 + FEET) @ R(90, "X")                                  # board coordinates -> tower
    transformed(lambda: case_shell(m, False, light=False), Mb)
    transformed(lambda: board(m), Mb)
    seat = {}
    if step is not None:                                                     # a step of the open-day build (board_layout.BUILD)
        skip, swap, seat = LAY.build_state(step, fixed)
    else:
        skip = set() if built else {"cooler", "dimm_a2", "dimm_b2", "gpu", "m2_ssd", "atx24", "eps8"}
        swap = {"atx24": "tpc_atx24_v2", "eps8": "tpc_eps8_v2"}              # cables routed through the tray
        if not built: swap["socket"] = "tpc_cpu_socket_empty"
    for pid, model, x, y, rot, w, d, h in LAY.all_parts():
        if pid in skip: continue
        model = swap.get(pid, model)
        fn = MODELS[model][1]
        z0 = seat.get(pid, {"tpc_dimm": 1.2, "tpc_gpu": 2.0, "tpc_tower_cooler": 5.3}.get(model, 0.0))
        transformed(lambda fn=fn: fn(m), Mb @ Tm(x, -y, LAY.BOARD_T + z0) @ R(rot))
    b = MB()
    for x in (10, 380):
        for y in (-200, -10): b.box(x - 15, y - 12, 0, x + 15, y + 12, FEET, m["rubber"])
    b.box(407, -217, FEET, 428, 9, 552, m["black_matte"])                    # front panel
    for k in range(18): b.box(428, -205, 60 + k * 22, 428.6, -185 + 0 * k, 72 + k * 22, m["case_steel"])
    b.box(407, -217, 552, 428, 9, 556, m["case_steel"])
    b.cyl(8, 0, 4, m["steel"], Tr(428, -170, 520) @ R(90, "Y"), seg=24)       # power button
    led = mat("Power_LED_on", (0.2, 0.5, 1.0), 0.3, emit=(0.2, 0.55, 1.0), strength=30.0) if power else m["black_plastic"]
    b.cyl(10, 0, 3.5, led, Tr(428, -170, 520) @ R(90, "Y"), seg=24, cap=False)
    b.box(428, -120, 500, 430, -60, 508, m["black_plastic"])                  # USB ports
    b.build("tower_outer", bevel=0.8)

def monitor(m, on=False):
    b = MB()
    b.box(-110, -80, 0, 110, 100, 8, m["black_matte"])                         # foot
    b.box(-20, 40, 8, 20, 60, 300, m["black_matte"])                           # neck
    b.box(-272, -9, 140, 272, 9, 465, m["black_plastic"])                      # panel
    b.box(-60, 9, 200, 60, 40, 330, m["black_matte"])                          # back hump
    scr = tex_mat("Screen_setup", os.path.join(TEX, "screen_setup.jpg"), rough=0.2) if on else m["screen"]
    if on:
        sm = mat("Screen_glow", (0.05, 0.1, 0.25), 0.2)
        nt = scr.node_tree; bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tex_node = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
        for k in ("Emission Color", "Emission"):
            if k in bsdf.inputs: nt.links.new(tex_node.outputs["Color"], bsdf.inputs[k]); break
        bsdf.inputs["Emission Strength"].default_value = 1.5
    b.face([(-264, -9.1, 150), (264, -9.1, 150), (264, -9.1, 455), (-264, -9.1, 455)], scr, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    b.build("monitor", bevel=1.0)

def keyboard(m):
    b = MB()
    b.box(-220, -68, 0, 220, 68, 14, m["black_matte"])
    key = mat("Keycap_dark", (0.03, 0.03, 0.035), 0.55)
    p = 19.05
    rows = [(-50, 15, 1.0), (-31, 14, 1.0), (-12, 14, 1.0), (7, 13, 1.0), (26, 12, 1.0)]
    for ry, n, _ in rows:
        for i in range(n):
            x = -210 + i * p + (ry + 50) * 0.12
            b.box(x, -ry - 8, 14, x + 16, -ry + 8, 22, key)
    b.box(-130, -61, 14, -10, -45, 22, key)                                    # space bar
    b.box(-210, 52, 14, 75, 64, 20, key)                                      # function row (strip of keys)
    for i in range(15): b.box(-210 + i * 19, 52, 20, -210 + i * 19 + 15, 64, 22, key)
    for i in range(4):
        for j in range(5): b.box(105 + i * p, -55 + j * p, 14, 121 + i * p, -39 + j * p, 22, key)   # number pad
    b.build("keyboard", bevel=0.6)

def mouse(m):
    b = MB()
    b.box(-32, -60, 0, 32, 60, 34, m["black_matte"])
    b.box(-1, 5, 34, 1, 50, 35, m["grey_plastic"])
    b.cyl(4, 34, 38, m["rubber"], Tr(0, 30, 0), seg=16)
    b.build("mouse", bevel=14.0)

def workbench(m):
    """A 2 m electronics workbench: beech top on a steel frame, grey anti-static mat with its earth lead, pegboard back
    with a shelf, hand tools and an anti-static wrist strap, and an LED light bar under the shelf. Front faces -y."""
    b = MB(); W, D, H = 2000, 750, 900
    beech = mat("Beech_top", (0.62, 0.45, 0.28), 0.5)
    frame = mat("Bench_frame_grey", (0.35, 0.37, 0.4), 0.45, 0.6)
    b.box(-W / 2, -D / 2, H - 30, W / 2, D / 2, H, beech, skip_bottom=False)
    for x in (-W / 2 + 30, W / 2 - 80):
        for y in (-D / 2 + 30, D / 2 - 80): b.box(x, y, 0, x + 50, y + 50, H - 30, frame)
    b.box(-W / 2 + 30, -D / 2 + 30, 180, W / 2 - 30, D / 2 - 30, 200, frame)   # lower shelf
    for y in (-D / 2 + 30, D / 2 - 80): b.box(-W / 2 + 80, y, 700, W / 2 - 80, y + 50, 740, frame)
    esd = mat("ESD_mat_grey", (0.2, 0.26, 0.3), 0.85)
    b.box(-850, -330, H, 850, 290, H + 2.5, esd)
    b.cyl(6, H + 2.5, H + 9, mat("Earth_stud_yellow", (0.8, 0.65, 0.05), 0.4, 0.6), Tr(800, 250, 0), seg=16)
    b.tube([(800, 250, H + 9)] + [(800 + 18 * math.cos(t), 280 + t * 6, H + 9 + 18 * math.sin(t)) for t in [k * 0.5 for k in range(1, 30)]] + [(800, 380, H - 80)],
           2.5, mat("Earth_lead_green", (0.05, 0.4, 0.1), 0.5))
    # pegboard back with posts and a shelf
    peg = tex_mat("Pegboard", os.path.join(TEX, "pegboard.png"), rough=0.7)
    b.box(-W / 2, D / 2 - 30, H, -W / 2 + 40, D / 2, H + 820, frame); b.box(W / 2 - 40, D / 2 - 30, H, W / 2, D / 2, H + 820, frame)
    b.face([(-W / 2 + 40, D / 2 - 15, H), (W / 2 - 40, D / 2 - 15, H), (W / 2 - 40, D / 2 - 15, H + 800), (-W / 2 + 40, D / 2 - 15, H + 800)], peg,
           uv=[(0, 0), (8, 0), (8, 3.3), (0, 3.3)])
    b.box(-W / 2 + 40, D / 2 - 260, H + 560, W / 2 - 40, D / 2 - 15, H + 580, beech, skip_bottom=False)
    b.box(-W / 2 + 60, D / 2 - 240, H + 540, W / 2 - 60, D / 2 - 200, H + 556, mat("LED_bar_on", (1, 1, 1), 0.3, emit=(1.0, 0.97, 0.9), strength=12.0), skip_bottom=False)
    # parts boxes on the shelf
    for i, c in enumerate(((0.6, 0.15, 0.1), (0.1, 0.3, 0.6), (0.85, 0.65, 0.1), (0.15, 0.45, 0.2))):
        x = -700 + i * 160
        b.box(x, D / 2 - 220, H + 580, x + 130, D / 2 - 40, H + 680, mat(f"Parts_bin_{i}", c, 0.5))
    # hand tools on the pegboard: screwdrivers, pliers, the wrist strap
    for i, (hc, ln) in enumerate((((0.85, 0.65, 0.05), 180), ((0.7, 0.1, 0.08), 160), ((0.1, 0.25, 0.7), 140))):
        x = 300 + i * 70
        b.cyl(14, H + 420, H + 520, mat(f"Driver_handle_{i}", hc, 0.4), Tr(x, D / 2 - 40, 0), seg=16)
        b.cyl(3, H + 520 - ln + 100, H + 420, m["steel"], Tr(x, D / 2 - 40, 0), seg=10)
    for s_ in (-1, 1): b.tube([(560, D / 2 - 40, H + 520), (560 + s_ * 8, D / 2 - 40, H + 430), (560 + s_ * 4, D / 2 - 40, H + 330)], 5, mat("Plier_grip_red", (0.6, 0.05, 0.04), 0.5))
    b.tube([(720 + 30 * math.cos(t), D / 2 - 40, H + 450 + 30 * math.sin(t)) for t in [k * 0.4 for k in range(17)]], 6, mat("Wrist_strap_black", (0.02, 0.02, 0.02), 0.7))
    b.tube([(720, D / 2 - 40, H + 420), (740, D / 2 - 60, H + 300), (780, D / 2 - 100, H + 50)], 1.8, mat("Strap_lead_coil", (0.05, 0.15, 0.5), 0.5))
    b.build("workbench", bevel=1.5)

MODELS = {
    "tpc_board": ("Motherboard (TinyPC)", board, "Generic own-design motherboard, 330 x 325 mm, traces, pads, silkscreen and surface-mount parts. Board coordinates: anchor = top-rear corner."),
    "tpc_cpu_socket": ("CPU in socket, paste on", cpu_socket, "LGA socket, load plate shut, lever latched, CPU lid with thermal paste. Lid top 5.3 mm."),
    "tpc_tower_cooler": ("Tower CPU cooler", tower_cooler, "Copper base, four heat pipes, 56 fins, 120 mm fan on +x. 158 mm tall."),
    "tpc_dimm": ("RAM stick (DDR5, RGB)", dimm, "133 mm stick with heat spreader, sticker and RGB bar (lit)."),
    "tpc_dimm_slot": ("DIMM slot (clips shut)", lambda m: dimm_slot(m, False), "146 mm slot, clips shut."),
    "tpc_dimm_slot_open": ("DIMM slot (clips open)", lambda m: dimm_slot(m, True), "146 mm slot, clips open."),
    "tpc_vrm_heatsink_l": ("VRM heatsink (long)", lambda m: vrm_heatsink(m, 86), "86 x 17 x 34 mm finned heatsink on chokes."),
    "tpc_vrm_heatsink_s": ("VRM heatsink (short)", lambda m: vrm_heatsink(m, 70), "70 x 17 x 34 mm finned heatsink on chokes."),
    "tpc_cap_8x10": ("Polymer capacitor 8 x 10", lambda m: cap(m, 8, 10.5, "cap_top_a"), "Solid polymer capacitor, 8 mm, 10.5 tall."),
    "tpc_cap_6x8": ("Polymer capacitor 6 x 8", lambda m: cap(m, 6, 8.5, "cap_top_b"), "Solid polymer capacitor, 6 mm, 8.5 tall."),
    "tpc_atx24": ("24-pin power, plugged in", lambda m: power_plug(m, 24, 2, 150, (0, -1), ["yellow", "black", "red", "orange", "black", "red", "black", "grey", "purple", "green", "black", "blue"]),
                  "24-pin header with plug; wires rise into a sleeved bundle bending towards -y (the board's front edge at rot 90)."),
    "tpc_atx24_v2": ("24-pin power, cable through the tray", lambda m: power_plug(m, 24, 2, 150, (0, -1), ["yellow", "black", "red", "orange", "black", "red", "black", "grey", "purple", "green", "black", "blue"], drop_at=34),
                  "24-pin header with plug; the sleeved bundle arches over and drops through a grommet 34 mm away (-y, the board's front edge at rot 90), into the case floor."),
    "tpc_eps8": ("8-pin CPU power, plugged in", lambda m: power_plug(m, 8, 2, 120, (0, 1), ["yellow", "black"]), "8-pin header with plug; bundle bends towards +y (the top edge)."),
    "tpc_rear_io": ("Rear I/O with shroud", rear_io, "Port stack under a sculpted shroud, 150 mm long."),
    "tpc_pcie_x16": ("PCIe x16 slot", lambda m: pcie_slot(m, 89, True), "Armoured x16 slot with latch."),
    "tpc_pcie_x1": ("PCIe x1 slot", lambda m: pcie_slot(m, 25, False), "x1 slot."),
    "tpc_gpu": ("Graphics card (compact)", gpu, "200 mm two-fan card, fans towards -y, backplate +y."),
    "tpc_chipset_heatsink": ("Chipset heatsink", chipset_heatsink, "44 mm low heatsink."),
    "tpc_cmos_battery": ("CMOS battery in holder", cmos_battery, "CR2032 cell in its holder."),
    "tpc_sata_ports": ("SATA ports (4)", sata_ports, "Four right-angle SATA ports, facing +x."),
    "tpc_m2_ssd": ("M.2 SSD", m2_ssd, "M.2 2280 SSD in its slot with a generic label."),
    "tpc_case_shell": ("PC case interior", case_shell, "Case round the board (board coordinates): tray, panels, fans, PSU shroud, daylight panel."),
    "tpc_eps8_v2": ("8-pin CPU power, cable through the tray", lambda m: power_plug(m, 8, 2, 120, (0, 1), ["yellow", "black"], drop_at=30), "8-pin header with plug; bundle arches over and drops through the tray towards +y."),
    "tpc_cpu_socket_clean": ("CPU in socket, clean lid", lambda m: cpu_socket(m, clean=True), "LGA socket with the CPU in, lid clean with generic etched markings (no paste)."),
    "tpc_cpu_socket_empty": ("CPU socket, empty, open", cpu_socket_empty, "Socket with no CPU: spring-pin field showing, load plate and lever up."),
    "tpc_cpu_socket_open": ("CPU with its lid peeled back", cpu_socket_open, "CPU in the socket, lid turned back over the +y edge: substrate, chip with its solder. Substrate top 4.0 mm, chip top 4.8 mm."),
    "tpc_cpu_socket_xray": ("CPU lid peeled back, chip X-ray", lambda m: cpu_socket_open(m, xray=True), "As tpc_cpu_socket_open, the chip's top drawn as an X-ray map of its circuits (cores, cache, memory controller, I/O)."),
    "tpc_cpu_socket_xray_nolid": ("CPU chip X-ray, no lid", lambda m: cpu_socket_open(m, xray=True, lid=False), "The chip's X-ray map with the lid left out altogether (the running PC, seen as an X-ray)."),
    "tpc_core_hall": ("Inside a core (backdrop)", core_hall, "14 m floor of standard cells and copper wiring. Room size: scale 1."),
    "tpc_cpu": ("CPU (loose)", cpu, "Loose CPU, 45 x 37.5 mm: gold pads underneath, generic etched lid."),
    "tpc_paste_syringe": ("Thermal paste syringe", paste_syringe, "Small syringe of grey thermal paste, lying flat."),
    "tpc_pc_tower": ("PC tower, built, side off", lambda m: pc_tower(m, True, False), "The TinyPC built, side panel off, open side facing -y, front +x. 430 x 225 x 556 mm."),
    "tpc_pc_tower_on": ("PC tower, built, switched on", lambda m: pc_tower(m, True, True), "As tpc_pc_tower, power LED lit."),
    "tpc_pc_tower_empty": ("PC tower, waiting for parts", lambda m: pc_tower(m, False, False), "Case and board only: empty CPU socket, no cooler, RAM, SSD, graphics card or power cables."),
    **{f"tpc_pc_tower_s{n}": (f"PC tower, build step {n}", (lambda m, n=n: pc_tower(m, step=n)),
                             f"The open-day PC at build step {n} (board_layout.BUILD); switched off.") for n in range(7)},
    "tpc_pc_tower_fixed_on": ("PC tower, built and running", lambda m: pc_tower(m, power=True, step=6, fixed=True), "Finished open-day PC, RAM clicked home, power LED lit."),
    "tpc_monitor": ("Monitor (off)", lambda m: monitor(m, False), "24-inch monitor, screen off, faces -y."),
    "tpc_monitor_on": ("Monitor (setup screen)", lambda m: monitor(m, True), "24-inch monitor showing a generic firmware setup page."),
    "tpc_keyboard": ("Keyboard", keyboard, "Full-size keyboard, front -y."),
    "tpc_mouse": ("Mouse", mouse, "Mouse, front -y."),
    "tpc_workbench": ("Electronics workbench", workbench, "2 m bench, top 0.9 m, anti-static mat with earth lead, pegboard back with shelf, tools, wrist strap and LED light bar. Front faces -y; back against the wall."),
    "tpc_board_dbg_cpu": ("Motherboard, CPU debug light on", board, "As tpc_board with the CPU debug LED lit red."),
    "tpc_board_dbg_dram": ("Motherboard, DRAM debug light on", board, "As tpc_board with the DRAM debug LED lit red."),
    "tpc_board_dbg_vga": ("Motherboard, VGA debug light on", board, "As tpc_board with the VGA debug LED lit red."),
    "tpc_board_dbg_boot": ("Motherboard, BOOT debug light on", board, "As tpc_board with the BOOT debug LED lit red."),
    "tpc_board_off": ("Motherboard (switched off)", board, "As tpc_board with every LED dark."),
    "tpc_dimm_off": ("RAM stick (switched off)", dimm, "As tpc_dimm with the RGB bar dark."),
    "tpc_case_shell_v2_off": ("PC case interior, switched off", lambda m: case_shell(m, True), "Set 2 case, fans still, RGB dark."),
    "tpc_case_shell_v2_on": ("PC case interior, on (no blades)", lambda m: case_shell(m, True), "Set 2 case lit, fan blades left out: the tour spins tpc_fan_rotor_92/120 over them."),
    "tpc_tower_cooler_on": ("Tower cooler, on (no blades)", tower_cooler, "Cooler with its fan blades left out (spun live by the tour)."),
    "tpc_gpu_on": ("Graphics card, on (no blades)", gpu, "Graphics card with its fan blades left out (spun live by the tour)."),
    "tpc_fan_rotor_120": ("Fan rotor 120 mm", lambda m: fan_rotor(m, 120, 9), "Hub and 9 blades of a 120 mm fan, axis front-back; spun live by the tour."),
    "tpc_fan_rotor_92": ("Fan rotor 92 mm", lambda m: fan_rotor(m, 92, 9), "Hub and 9 blades of a 92 mm fan, axis front-back; spun live by the tour."),
    "tpc_fan_rotor_88": ("Fan rotor 88 mm (graphics card)", lambda m: fan_rotor(m, 88, 11), "Hub and 11 blades of a graphics card fan; spun live by the tour."),
    "tpc_case_shell_v2": ("PC case interior (low fans)", lambda m: case_shell(m, True), "Set 2 case: 92 mm fans mounted low so they land on the walls; deeper PSU shroud to stand on."),
}

def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for d in list(c):
            if d.users == 0: c.remove(d)

def bounds():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH": continue
        oe = o.evaluated_get(dg); pts += [oe.matrix_world @ Vector(c) for c in oe.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

def thumbnail(path, mn, mx):
    sc = bpy.context.scene
    ctr = (mn + mx) / 2; rad = (mx - mn).length / 2
    cam_d = bpy.data.cameras.new("thumbcam"); cam_d.lens = 50; cam_d.clip_start = rad * 0.01; cam_d.clip_end = rad * 20
    cam = bpy.data.objects.new("thumbcam", cam_d); sc.collection.objects.link(cam)
    d = Vector((0.75, -1.0, 0.65)).normalized()
    cam.location = ctr + d * rad * 2.1
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler(); sc.camera = cam
    ld = bpy.data.lights.new("key", "AREA"); ld.energy = 600 * rad * rad; ld.size = rad * 2
    key = bpy.data.objects.new("key", ld); sc.collection.objects.link(key)
    key.location = ctr + Vector((-1.5, -2, 3)) * rad * 1.5
    key.rotation_euler = (ctr - key.location).to_track_quat("-Z", "Y").to_euler()
    w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.32, 0.34, 0.36, 1); bg.inputs[1].default_value = 1.0
    sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dt in ("OPTIX", "CUDA"):
            prefs.compute_device_type = dt; prefs.get_devices()
            if any(dv.type == dt for dv in prefs.devices):
                for dv in prefs.devices: dv.use = dv.type == dt
                sc.cycles.device = "GPU"; break
    except Exception: pass
    sc.render.resolution_x = sc.render.resolution_y = 512; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.filepath = path
    sc.view_settings.view_transform = "AgX"
    bpy.ops.render.render(write_still=True)
    for o in (cam, key): bpy.data.objects.remove(o, do_unlink=True)

for mid in ONLY:                                                         # per-stop "on" cases: tpc_case_shell_v2_on_<mask>
    if mid.startswith("tpc_case_shell_v2_on_") and mid not in MODELS:
        mask = mid.rsplit("_", 1)[1]
        MODELS[mid] = ("PC case interior, on (" + mask + ")", lambda m, mask=mask: case_shell(m, True, spun=mask),
                       "Set 2 case lit; blades left out only where the tour spins a rotor (mask: front 0-2, top 0-1, rear).")
for mid, (name, fn, notes) in MODELS.items():
    if ONLY and mid not in ONLY: continue
    try:
        OFF[0] = mid.endswith("_off") or mid in ("tpc_pc_tower", "tpc_pc_tower_empty") or mid.startswith("tpc_pc_tower_s")   # PCs not switched on
        BLADES[0] = not mid.endswith("_on") or mid in ("tpc_pc_tower_on", "tpc_pc_tower_fixed_on", "tpc_monitor_on")
        DBG[0] = mid.split("_dbg_")[1].upper() if "_dbg_" in mid else None
        clear(); m = M(); fn(m)
        d = os.path.join(OUT, mid); os.makedirs(d, exist_ok=True)
        mn, mx = bounds()
        bpy.ops.object.select_all(action="DESELECT")
        for o in bpy.context.scene.objects:
            if o.type == "MESH": o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(d, mid + ".glb"), export_format="GLB", use_selection=True, export_apply=True)
        thumbnail(os.path.join(d, "thumb.png"), mn, mx)
        tris = sum(len(p.vertices) - 2 for o in bpy.context.scene.objects if o.type == "MESH" for p in o.data.polygons)
        meta = {"id": mid, "name": name, "file": mid + ".glb", "thumb": "thumb.png", "category": "pc",
                "styles": ["outdoor"], "tags": ["pc", "tinypc", "computer"], "status": "untested", "notes": notes,
                "scale": 1.0, "polycount": tris,
                "bbox_mm": [round(v / MM, 2) for v in (mn.x, mx.x, mn.y, mx.y, mn.z, mx.z)],
                "licence": {"source": "TinyPC", "author": "Own model (made for TinyPC)", "licence": "Own work",
                            "licence_url": "", "url": "", "credit_required": False}}
        json.dump(meta, open(os.path.join(d, "model.json"), "w", encoding="utf-8"), indent=2)
        print("TPC_MODEL", mid, tris, meta["bbox_mm"], flush=True)
    except Exception as e:
        import traceback; traceback.print_exc(); print("TPC_FAILED", mid, e, flush=True)
print("TPC_DONE", flush=True)
