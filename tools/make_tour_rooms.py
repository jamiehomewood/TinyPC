"""
Writes a Room Builder spec for every room of the open-day tour (specs/tour/<room>.json):

  Workbench at each build step   B0 .. B6 (the PC on the bench gains parts), B_on (built, switched on, setup screen)
  Inside the PC                   T_cpu    on the CPU, just fitted (step 1, switched off)
                                  T_ramq   beside the RAM slots, empty (step 1, off)
                                  T_ram    beside the RAM, sticks in, B2 not clicked home (step 2, off)
                                  T_delid  on the CPU with its lid peeled back (step 1, off)
                                  T_die    standing on the chip, drawn as an X-ray map (step 1, off)
                                  T_run    the finished PC running, the chip as an X-ray (no lid, no cooler)
                                  T_cooler behind the RAM, facing the cooler (step 3, off)
                                  T_gpu    beside the graphics card (step 5, off)
                                  T_power  by the 24-pin, cables plugged in (step 6, off)
                                  F_dram   by the 24-pin, switched on, DRAM debug light lit (step 6, the fault)
                                  F_ram    beside the RAM, switched on, the loose stick (step 6, the fault)
                                  R_fixed  beside the RAM, switched off, stick pushed home (fixed)
                                  S_on     by the 24-pin, switched on, all well (fixed)

    python tools/make_tour_rooms.py [quality]           (draft | standard; default standard)

The build steps come from board_layout.BUILD / build_state. Switched-on rooms also get every candidate fan rotor in
<room>.props.all.json; run tools/check_rotors.py on a first render of that room to keep the visible ones
(<room>.props.json), then run this again: the case is then the per-room tpc_case_shell_v2_on_<mask> (blades left out
only where a rotor spins) and the cooler / graphics card lose their blades only if theirs spin.
"""
import copy, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import board_layout as L
import make_stop_specs as MS

QUALITY = sys.argv[1] if len(sys.argv) > 1 else "standard"
MS.SET = "v2on"                                     # (rotor seats: same parts as set 2)
OUT = os.path.join(ROOT, "specs", "tour"); os.makedirs(OUT, exist_ok=True)
STOP = {s["id"].split("_", 1)[1]: s for s in L.STOPS_V2 + L.STOPS_TOUR}   # s1_arrival, s2_cpu, s3_ram, s4_cooler, s5_gpu

TINY = {
    "T_cpu":   ("s2_cpu", 1, False, "off", None, "On the CPU (just fitted)"),
    "T_ramq":  ("s3_ram", 1, False, "off", None, "The empty RAM slots"),
    "T_ram":   ("s3_ram", 2, False, "off", None, "RAM fitted"),
    "T_delid":  ("s6_delid", 1, False, "off", None, "Under the CPU's lid", {"socket": "tpc_cpu_socket_open"}),
    "T_die":    ("s7_die", 1, False, "off", None, "On the chip (X-ray)", {"socket": "tpc_cpu_socket_xray"}),
    # the finished PC running, seen as an X-ray (no lid, no cooler): the fetch-decode-execute animation plays here.
    # Case fans keep their blades (mask 000000: no live rotors at this scale), graphics card with its blades.
    "T_run":    ("s8_run", 6, True, "on", None, "The chip at work (X-ray)",
                 {"socket": "tpc_cpu_socket_xray_nolid", "gpu": "tpc_gpu", "case": "tpc_case_shell_v2_on_000000"}),
    "T_cooler": ("s4_cooler", 3, False, "off", None, "The cooler fitted"),
    "T_gpu":   ("s5_gpu", 5, False, "off", None, "The graphics card fitted"),
    "T_power": ("s1_arrival", 6, False, "off", None, "Power plugged in"),
    "F_dram":  ("s1_arrival", 6, False, "on", "dram", "Switched on: DRAM light"),
    "F_ram":   ("s3_ram", 6, False, "on", "dram", "Switched on: the RAM"),
    "R_fixed": ("s3_ram", 6, True, "off", None, "RAM pushed home"),
    "S_on":    ("s1_arrival", 6, True, "on", None, "Switched on: all well"),
}

def tiny_spec(room, stop_key, step, fixed, power, dbg, title, swap=None):
    st = copy.deepcopy(STOP[stop_key])
    omit, models, seat = L.build_state(step, fixed)
    models.update(swap or {})
    st["omit"] = sorted(set(st["omit"]) | omit)
    k = st["k"] / 1000.0
    kept = None
    kp = os.path.join(OUT, room + ".props.json")
    if power == "on" and os.path.exists(kp):
        kept = {r["id"] for r in json.load(open(kp, encoding="utf-8"))}
    items = []
    def add(iid, model, ax, ay, rot, base):
        x, y, z = MS.place(model, ax, ay, rot, base, st)
        items.append({"id": iid, "model": model, "x": x, "y": y, "z": z, "rot": rot, "scale": st["k"]})
    if power == "off": case = "tpc_case_shell_v2_off"
    elif kept is None: case = "tpc_case_shell_v2_on"
    else: case = "tpc_case_shell_v2_on_" + "".join("1" if f"case{i}" in kept else "0" for i in range(len(L.FANS_V2)))
    case = (swap or {}).get("case", case)
    add("case", case, 0, 0, 0, 0.0)
    add("board", "tpc_board_off" if power == "off" else ("tpc_board_dbg_" + dbg if dbg else "tpc_board"), 0, 0, 0, 0.0)
    for pid, model, x, y, rot, w, d, h in L.all_parts():
        if pid in st["omit"]: continue
        model = models.get(pid, model)
        if power == "off" and model == "tpc_dimm": model = "tpc_dimm_off"
        if power == "on" and pid == "cooler": model = "tpc_tower_cooler_on" if (kept is None or "cooler0" in kept) else "tpc_tower_cooler"
        if power == "on" and pid == "gpu": model = "tpc_gpu_on" if (kept is None or {"gpu0", "gpu1"} <= kept) else "tpc_gpu"
        model = (swap or {}).get(pid, model)
        base = seat.get(pid, MS.seat_of(model))
        add(pid, model, x, y, rot, L.BOARD_T + base)
    eye_z = 0.002 + (MS.TRAY_BELOW_BOARD + L.BOARD_T + st["floor_z"]) * k + MS.EYE
    spec = {"version": 1, "name": f"TinyPC tour - {room} - {title}",
            "room": {"preset": "igloo-main", "width": 6.4, "depth": 5.71, "height": 2.244, "eye": MS.EYE,
                     "projected": {"walls": True, "floor": True, "ceiling": False}, "type": "outdoor"},
            "style": "outdoor", "lighting": "night", "outside": {"view": "custom", "hdri": None}, "features": [], "items": items,
            "views": [{"name": "centre", "x": 0, "y": 0, "z": round(eye_z, 4), "yaw": st.get("yaw", 0)}],
            "render": {"quality": QUALITY, "exposure": st.get("exposure", 0.0)},
            "tinypc": {"tour_room": room, "stop": st["id"], "step": step, "fixed": fixed, "power": power, "debug_led": dbg,
                       "note": "Made by tools/make_tour_rooms.py: edit that (or board_layout.py), not this file."}}
    with open(os.path.join(OUT, room + ".json"), "w", encoding="utf-8") as fh: json.dump(spec, fh, indent=1)
    if power == "on":
        with open(os.path.join(OUT, room + ".props.all.json"), "w", encoding="utf-8") as fh: json.dump(MS.rotors(st, eye_z), fh, indent=1)
    return eye_z, kept

def core_spec(room, title):
    """Inside a core: the tpc_core_hall backdrop at room size; the register diagram is live (the tour player draws it)."""
    spec = {"version": 1, "name": f"TinyPC tour - {room} - {title}",
            "room": {"preset": "igloo-main", "width": 6.4, "depth": 5.71, "height": 2.244, "eye": MS.EYE,
                     "projected": {"walls": True, "floor": True, "ceiling": False}, "type": "outdoor"},
            "style": "outdoor", "lighting": "night", "outside": {"view": "custom", "hdri": None}, "features": [],
            "items": [{"id": "hall", "model": "tpc_core_hall", "x": 0, "y": 0, "z": 0.002, "rot": 0, "scale": 1}],
            "views": [{"name": "centre", "x": 0, "y": 0, "z": MS.EYE + 0.002, "yaw": 0}],
            "render": {"quality": QUALITY, "exposure": 0.0},
            "tinypc": {"tour_room": room, "note": "Made by tools/make_tour_rooms.py."}}
    with open(os.path.join(OUT, room + ".json"), "w", encoding="utf-8") as fh: json.dump(spec, fh, indent=1)

def bench_spec(room, pc, monitor, title):
    s = json.load(open(os.path.join(ROOT, "specs", "workbench", "tpc_workbench.json"), encoding="utf-8"))
    s["name"] = f"TinyPC tour - {room} - {title}"
    for it in s["items"]:
        if it["id"] == "pc": it["model"] = pc
        if it["id"] == "monitor": it["model"] = monitor
    s["render"]["quality"] = QUALITY
    s["tinypc"] = {"tour_room": room, "note": "Made by tools/make_tour_rooms.py from specs/workbench/tpc_workbench.json."}
    with open(os.path.join(OUT, room + ".json"), "w", encoding="utf-8") as fh: json.dump(s, fh, indent=1)

if __name__ == "__main__":
    titles = ["Empty case", "CPU fitted", "RAM fitted", "Cooler fitted", "SSD fitted", "Graphics card fitted", "Power cables in"]
    for n in range(7): bench_spec(f"B{n}", f"tpc_pc_tower_s{n}", "tpc_monitor", titles[n])
    bench_spec("B_on", "tpc_pc_tower_fixed_on", "tpc_monitor_on", "Running")
    core_spec("T_core", "Inside a core")
    for room, args in TINY.items():
        eye, kept = tiny_spec(room, *args)
        print(f"{room:8s} eye {eye:.3f}" + (f"  rotors kept {sorted(kept)}" if kept is not None else ("  (rotors: not checked yet)" if args[3] == "on" else "")))
    print("wrote", OUT)
