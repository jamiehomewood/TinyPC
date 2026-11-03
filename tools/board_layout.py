"""
TinyPC board layout: where every part sits on the motherboard, in real millimetres, and where each stop stands.

Shared by make_board_texture.py (draws traces, pads and silkscreen under the parts), make_stop_specs.py (writes a
Room Builder spec per stop) and the clear-zone check (python tools/board_layout.py).

Board coordinates (mm): origin at the board's top-rear corner (the rear I/O end of the top edge), x towards the front
edge (0..BOARD_W), y down towards the bottom edge (0..BOARD_H), z up out of the board. The board is our own generic
design, a little bigger than ATX (330 x 325 mm) so each stop has an open patch of flat board round it.

In a stop's render, the stop point sits at the room centre: room east = +x, room north = -y (the top edge of the board),
1 mm real = k/1000 m in the room, where k is the stop's scale.
"""
import math

BOARD_W, BOARD_H, BOARD_T = 330.0, 325.0, 1.6
Y_SHIFT = 20.0                                  # everything sits 20 mm down from the top edge (a wider top margin)

# id, catalogue model, centre x, centre y, rot (deg, about z, + = anticlockwise seen from above), footprint w (x), d (y), height h
# Footprints/heights are the real part's size (after rotation, w is along board x and d along board y).
PARTS = [
    # ---- top-rear: I/O, CPU power, VRM
    ("rear_io",      "tpc_rear_io",        11.0,  88.0,   0,  22, 150, 42),
    ("eps8",         "tpc_eps8",           40.0,   9.0,   0,  19,  10, 16),
    ("vrm_top",      "tpc_vrm_heatsink_l", 92.0,  16.0,   0,  86,  17, 34),
    ("vrm_left",     "tpc_vrm_heatsink_s", 32.0,  78.0,  90,  17,  70, 34),
    ("socket",       "tpc_cpu_socket",     92.0,  80.0,   0,  56,  64,  6.5),
    ("cooler",       "tpc_tower_cooler",   92.0,  80.0,   0,  75, 126, 158),
    # ---- memory: four DIMM slots (A1 A2 B1 B2), sticks in A2 and B2
    ("dimm_slot_a1", "tpc_dimm_slot",     156.0,  80.0,  90,   7, 146,  7),
    ("dimm_slot_a2", "tpc_dimm_slot",     165.0,  80.0,  90,   7, 146,  7),
    ("dimm_slot_b1", "tpc_dimm_slot",     180.0,  80.0,  90,   7, 146,  7),
    ("dimm_slot_b2", "tpc_dimm_slot",     189.0,  80.0,  90,   7, 146,  7),
    ("dimm_a2",      "tpc_dimm",          165.0,  80.0,  90,   7, 134, 44),
    ("dimm_b2",      "tpc_dimm",          189.0,  80.0,  90,   7, 134, 44),
    # ---- front edge: 24-pin power, front-edge capacitors, SATA
    ("atx24",        "tpc_atx24",         323.0, 112.0,  90,  10,  52, 20),
    ("sata",         "tpc_sata_ports",    320.0, 286.0,   0,  14,  30, 15),
    # ---- lower half: storage, chipset, expansion, battery
    ("m2_ssd",       "tpc_m2_ssd",         88.0, 168.0,   0,  86,  22,  2.4),
    ("pcie1",        "tpc_pcie_x16",       64.0, 198.0,   0,  89,   8, 11),
    ("pcie2",        "tpc_pcie_x1",        30.0, 235.0,   0,  25,   8, 11),
    ("pcie3",        "tpc_pcie_x16",       64.0, 274.0,   0,  89,   8, 11),
    ("gpu",          "tpc_gpu",           106.0, 222.0,   0, 200,  48, 112),
    ("chipset",      "tpc_chipset_heatsink", 228.0, 266.0, 0,  44,  44,  9),
    ("cmos",         "tpc_cmos_battery",  290.0, 236.0,   0,  23,  23,  5.5),
]

# Capacitor and choke groups (solid polymer caps 8 x 10 mm or 6 x 8 mm). Each: model, list of (x, y).
# Debug LEDs by the 24-pin (board mm, Y_SHIFT included): the board lights the one for the stage that fails at switch-on.
DEBUG_LEDS = [("CPU", 297.0, 160.0), ("DRAM", 297.0, 166.0), ("VGA", 297.0, 172.0), ("BOOT", 297.0, 178.0)]

CAPS = [
    ("tpc_cap_8x10", [(52 + 9 * i, 33) for i in range(8)]),                 # under the top VRM heatsink edge
    ("tpc_cap_8x10", [(46, 42 + 9 * i) for i in range(6)]),                 # beside the left VRM heatsink
    ("tpc_cap_6x8",  [(310, 92 + 8 * i) for i in range(4)]),  # beside the 24-pin
    ("tpc_cap_6x8",  [(196, 250 + 8 * i) for i in range(3)]),               # by the chipset
]

def all_parts():
    """Every placed part as (id, model, x, y, rot, w, d, h), caps included, in board mm (Y_SHIFT applied)."""
    out = [(p[0], p[1], p[2], p[3] + Y_SHIFT) + tuple(p[4:]) for p in PARTS]
    sizes = {"tpc_cap_8x10": (8, 8, 10.5), "tpc_cap_6x8": (6, 6, 8.5), "tpc_choke": (10, 10, 7)}
    for model, pts in CAPS:
        w, d, h = sizes[model]
        for x, y in pts: out.append((f"{model[4:]}_{int(x)}_{int(y)}", model, x, y + Y_SHIFT, 0, w, d, h))
    return out

# Stops: id, title, stand point (x, y) on the board (board mm, Y_SHIFT already included), scale k, which parts are left out (e.g. the cooler lifted off),
# floor_z: height (mm) of what you stand on above the board surface (e.g. on top of the CPU).
# stand_on: the part you stand on (left out of the clear-zone check).
# yaw: which way the middle of the panorama (the Front wall) faces, compass degrees (0 = the board's top edge, 90 = front edge).
# Set 1 (v1, 3 Nov 2026 first pass): kept as it is so the two sets can be compared.
STOPS = [
    dict(id="tpc_s1_arrival", title="Arrival: by the 24-pin power", x=258.0, y=180.0, k=35, omit=[], floor_z=0.0, yaw=90, exposure=0.4),
    dict(id="tpc_s2_cpu",     title="On the CPU (cooler lifted off)", x=92.0, y=100.0, k=50, omit=["cooler"], floor_z=5.3, yaw=90, stand_on="socket"),
    dict(id="tpc_s3_ram",     title="Beside the RAM", x=268.0, y=48.0, k=35, omit=[], floor_z=0.0, yaw=270, exposure=0.4),
]
# Set 2 (v2): the case fans sit low so they land on the walls, the 24-pin cable drops through a tray grommet beside the
# board instead of arching overhead, and an overview stop on the case floor in front of the board at x22, looking back
# across the board: the cooler, GPU and RAM all fit below the top of the projected walls. (A first try stood on the PSU
# shroud: the board was hidden in a pit below its edge.) The v2 case is wider at the front to make room.
SHROUD_TOP = 90.4                                   # PSU shroud top, mm above the board's top surface
TRAY_DROP = 7.6                                     # case floor (tray top), mm below the board's top surface
STOPS_V2 = [
    dict(id="tpc2_s0_overview", title="Overview: by the front of the board", x=400.0, y=215.0, k=22, omit=[], floor_z=-TRAY_DROP, yaw=270, exposure=1.0),
    dict(id="tpc2_s1_arrival", title="By the 24-pin power", x=258.0, y=180.0, k=35, omit=[], floor_z=0.0, yaw=90, exposure=0.4),
    dict(id="tpc2_s2_cpu",     title="On the CPU (cooler lifted off)", x=92.0, y=100.0, k=50, omit=["cooler"], floor_z=5.3, yaw=90, stand_on="socket"),
    dict(id="tpc2_s3_ram",     title="Beside the RAM", x=268.0, y=48.0, k=35, omit=[], floor_z=0.0, yaw=270, exposure=0.4),
]

# The case's walls and PSU shroud as boxes for the checks (board mm; h = height above the board's top surface).
def _case(bottom_y, front_x):
    mid, span, w = (bottom_y - 60) / 2, bottom_y + 60, front_x + 20
    return [("case_rear", "", -21, mid, 0, 2, span, 213), ("case_top", "", w / 2 - 20, -61, 0, w, 2, 213),
            ("case_front", "", front_x + 1, mid, 0, 2, span, 213), ("case_bottom", "", w / 2 - 20, bottom_y + 1, 0, w, 2, 213),
            ("shroud", "", w / 2 - 20, (360 + bottom_y) / 2, 0, w, bottom_y - 360, SHROUD_TOP)]
CASES = {"v1": {"model": "tpc_case_shell", "parts": _case(470, 405)},
         "v2": {"model": "tpc_case_shell_v2", "parts": _case(470, 520)}}
def _variant(stops, prefix, drop=()):
    return [dict(st, id=prefix + st["id"].split("_", 1)[1]) for st in stops if st["id"] not in drop]
# Switched off / switched on versions of set 2's stops 1-3, for the build-and-boot tour: off = RGB and LEDs dark,
# on = lit with the fan blades left out (the tour spins live rotors over them: make_stop_specs.py writes where, in
# specs/<folder>/<stop>.props.json). Both use the clean CPU lid (no paste).
STOPS_V2OFF = _variant(STOPS_V2, "tpc2off_", drop=("tpc2_s0_overview",))
STOPS_V2ON = _variant(STOPS_V2, "tpc2on_", drop=("tpc2_s0_overview",))
for _st in STOPS_V2OFF + STOPS_V2ON: _st["title"] = _st["title"] + (" (off)" if _st["id"].startswith("tpc2off") else " (on)")
# Case fans for the live rotors (case/board model coordinates, mm: x, y = -board y, z above the board's underside),
# and part fans relative to the part's anchor: (size, centre, axis)
FANS_V2 = [(92, (507, -60 - k * 105, 43), "x") for k in range(3)] + [(92, (90 + k * 130, 47, 43), "y") for k in range(2)] + [(120, (-7, -100, 110), "x")]
PART_FANS = {"cooler": [(120, (37.5, 0, 98), "x")], "gpu": [(88, (-48, -24.2, 58), "y"), (88, (48, -24.2, 58), "y")]}

# "models": parts drawn with a different model in that set
SETS = {"v1": {"case": "v1", "stops": STOPS, "folder": "", "label": "TinyPC", "models": {}},
        "v2": {"case": "v2", "stops": STOPS_V2, "folder": "v2", "label": "TinyPC v2", "models": {"atx24": "tpc_atx24_v2"},
               # the v2 24-pin cable arches over and drops through the case floor 34 mm in front of the connector
               "extra": [("atx24_cable", "", 357.0, 132.0, 0, 30, 30, 83)]},
        "v2off": {"case": "v2", "case_model": "tpc_case_shell_v2_off", "stops": STOPS_V2OFF, "folder": "v2off", "label": "TinyPC v2 (off)",
                  "models": {"atx24": "tpc_atx24_v2", "board": "tpc_board_off", "dimm_a2": "tpc_dimm_off", "dimm_b2": "tpc_dimm_off", "socket": "tpc_cpu_socket_clean"},
                  "extra": [("atx24_cable", "", 357.0, 132.0, 0, 30, 30, 83)]},
        "v2on": {"case": "v2", "case_model": "tpc_case_shell_v2_on", "stops": STOPS_V2ON, "folder": "v2on", "label": "TinyPC v2 (on)",
                 "models": {"atx24": "tpc_atx24_v2", "socket": "tpc_cpu_socket_clean", "cooler": "tpc_tower_cooler_on", "gpu": "tpc_gpu_on"},
                 "extra": [("atx24_cable", "", 357.0, 132.0, 0, 30, 30, 83)], "rotors": True}}

# ------------------------------------------------------------------ the open-day build, step by step
# Step 0: empty (socket open, pins showing, all slot clips open). 1: CPU in. 2: RAM in A2 + B2, but the B2 stick is not
# clicked home (raised, its clip open): the planted fault. 3: cooler. 4: SSD. 5: graphics card. 6: power cables.
# fixed=True: the B2 stick pushed home, clip shut.
BUILD = [("dimm_a2", 2), ("dimm_b2", 2), ("cooler", 3), ("m2_ssd", 4), ("gpu", 5), ("atx24", 6), ("eps8", 6)]
LOOSE_SEAT = 4.7                    # mm: the loose stick sits 3.5 mm higher than a seated one (1.2)

def build_state(n, fixed=False):
    """(parts left out, part -> model, part -> seat height mm) for build step n."""
    omit = {pid for pid, k in BUILD if n < k}
    models = {"socket": "tpc_cpu_socket_clean" if n >= 1 else "tpc_cpu_socket_empty", "atx24": "tpc_atx24_v2", "eps8": "tpc_eps8_v2"}
    seat = {}
    if n < 2:
        for sl in ("a1", "a2", "b1", "b2"): models["dimm_slot_" + sl] = "tpc_dimm_slot_open"
    elif not fixed:
        models["dimm_slot_b2"] = "tpc_dimm_slot_open"; seat["dimm_b2"] = LOOSE_SEAT
    return omit, models, seat

CLEAR_R, FLAT_H, WALL_MIN, WALL_IDEAL = 2.0, 0.05, 2.5, (2.8, 3.5)   # metres in the room
ROOM_W, ROOM_D, ROOM_H, EYE = 6.40, 5.71, 2.244, 1.12                # Peterborough

def rect_dist(px, py, x, y, w, d):
    dx = max(abs(px - x) - w / 2, 0.0); dy = max(abs(py - y) - d / 2, 0.0)
    return math.hypot(dx, dy)

def wall_top_elev(direction_deg):
    """Elevation (rad) of the top of the projected walls, seen from the room centre, for a direction relative to Front."""
    a = math.radians(direction_deg); dx, dy = abs(math.sin(a)), abs(math.cos(a))
    dist = min(ROOM_W / 2 / dx if dx > 1e-6 else 1e9, ROOM_D / 2 / dy if dy > 1e-6 else 1e9)
    return math.atan((ROOM_H - EYE) / dist)

def shown(stop, x, y, w, d, h_room, dist):
    """Fraction of a part's height (above what you stand on) that falls below the top of the projected walls."""
    cx, cy = min(max(stop["x"], x - w / 2), x + w / 2), min(max(stop["y"], y - d / 2), y + d / 2)   # nearest point
    bearing = math.degrees(math.atan2(cx - stop["x"], -(cy - stop["y"])))          # compass, 0 = board top edge
    lim = EYE + max(dist, 0.05) * math.tan(wall_top_elev(bearing - stop.get("yaw", 0)))
    return max(0.0, min(1.0, lim / h_room)) if h_room > 0 else 1.0

def check(stop, case="v1", verbose=True):
    """Distances (room metres) from a stop to every part that stands proud of the floor it stands on, and how much of
    each tall one shows below the top of the projected walls."""
    k = stop["k"] / 1000.0; bad = []; rows = []
    extra = next((v.get("extra", []) for v in SETS.values() if v["case"] == case), [])
    for pid, model, x, y, rot, w, d, h in all_parts() + CASES[case]["parts"] + extra:
        if pid in stop["omit"] or pid == stop.get("stand_on"): continue
        dist = rect_dist(stop["x"], stop["y"], x, y, w, d) * k
        hr = (h - stop["floor_z"]) * k
        if hr <= FLAT_H: continue
        level = "CLEAR-ZONE" if dist < CLEAR_R else ("near" if dist < WALL_MIN else "")
        rows.append((dist, pid, hr, level, shown(stop, x, y, w, d, hr, dist)))
        if level == "CLEAR-ZONE": bad.append(pid)
    rows.sort()
    if verbose:
        print(f"\n{stop['id']}  ({stop['title']})  at ({stop['x']}, {stop['y']}) mm, x{stop['k']}")
        for dist, pid, hr, level, sh in rows[:14]:
            print(f"   {dist:5.2f} m  {pid:18s} {hr:5.2f} m tall  shows {sh * 100:3.0f}%  {level}")
    return bad

if __name__ == "__main__":
    import sys
    for name in (sys.argv[1:] or SETS):
        n = 0
        for st in SETS[name]["stops"]: n += len(check(st, SETS[name]["case"]))
        print(f"\n[{name}] clear-zone problems:", n)
