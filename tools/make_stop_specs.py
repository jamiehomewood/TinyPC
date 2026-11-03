"""
Writes a Room Builder spec for each TinyPC stop (specs/<stop id>.json) from board_layout.py and the models' bounds
(models/<id>/model.json "bbox_mm"), and runs the clear-zone check.

    python tools/make_stop_specs.py [quality] [set]    (quality: draft | standard | high; set: v1 | v2, default v1)

Set 1 writes specs/<stop>.json, set 2 specs/v2/<stop>.json; the sets use different case models, so neither changes the other.

Each stop is an "outdoor" scene (no room box, no lights of its own): the case shell, the board and the parts are models
at the stop's scale k (1 mm real = k mm in the room), moved so the stop point is at the room centre. The world is left
almost black (no HDRI): the light comes from the case's daylight panel, the RGB on the RAM and fans, and board LEDs.

Heights: the case tray's underside sits just above z = 0 (Room Builder's outdoor ground is a shadow catcher at z = 0,
so nothing may go below it). The camera stands 1.12 m above what you stand on (the board, or the CPU lid at stop 2).
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import board_layout as L

QUALITY = sys.argv[1] if len(sys.argv) > 1 else "standard"
SET = sys.argv[2] if len(sys.argv) > 2 else "v1"                 # which set of stops (board_layout.SETS): v1 | v2
MODELS = os.path.join(ROOT, "models")
EYE = 1.12
TRAY_BELOW_BOARD = 7.0                       # mm from the board's underside down to the tray's underside (6 mm standoffs + 1 mm steel)
# how far above the board's top surface each part's own z = 0 sits (mm): sticks sit down in their slots, the GPU's
# fingers in its slot, the cooler on the CPU lid
SEAT = {"tpc_dimm": 1.2, "tpc_gpu": 2.0, "tpc_tower_cooler": 5.3}
def seat_of(model):
    """Seat height for a model or its switched-on / switched-off variant (tpc_dimm_off sits like tpc_dimm)."""
    for suf in ("_off", "_on"):
        if model.endswith(suf): model = model[: -len(suf)]
    return SEAT.get(model, 0.0)

def bbox(model):
    with open(os.path.join(MODELS, model, "model.json"), encoding="utf-8") as fh:
        return json.load(fh)["bbox_mm"]

def place(model, ax, ay, rot, base_mm, stop):
    """Room position for a model whose anchor is at board (ax, ay) mm, with its z = 0 at base_mm above the board's underside."""
    k = stop["k"] / 1000.0
    x0, x1, y0, y1, z0, z1 = bbox(model)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = math.radians(rot)
    rx, ry = cx * math.cos(r) - cy * math.sin(r), cx * math.sin(r) + cy * math.cos(r)
    X = (ax - stop["x"]) * k + rx * k
    Y = -(ay - stop["y"]) * k + ry * k
    Z = 0.002 + (TRAY_BELOW_BOARD + base_mm + z0) * k
    return round(X, 4), round(Y, 4), round(Z, 4)

def spec_for(stop):
    k = stop["k"]
    items = []
    def add(iid, model, ax, ay, rot, base):
        x, y, z = place(model, ax, ay, rot, base, stop)
        items.append({"id": iid, "model": model, "x": x, "y": y, "z": z, "rot": rot, "scale": k})
    add("case", L.SETS[SET].get("case_model") or L.CASES[L.SETS[SET]["case"]]["model"], 0, 0, 0, 0.0)
    add("board", L.SETS[SET]["models"].get("board", "tpc_board"), 0, 0, 0, 0.0)
    for pid, model, x, y, rot, w, d, h in L.all_parts():
        if pid in stop["omit"]: continue
        model = L.SETS[SET]["models"].get(pid, model)
        add(pid, model, x, y, rot, L.BOARD_T + seat_of(model))
    eye_z = 0.002 + (TRAY_BELOW_BOARD + L.BOARD_T + stop["floor_z"]) * k / 1000.0 + EYE
    return {
        "version": 1,
        "name": f"{L.SETS[SET]['label']} - {stop['title']}",
        "room": {"preset": "igloo-main", "width": 6.4, "depth": 5.71, "height": 2.244, "eye": EYE,
                 "projected": {"walls": True, "floor": True, "ceiling": False}, "type": "outdoor"},
        "style": "outdoor",
        "lighting": "night",
        "outside": {"view": "custom", "hdri": None},
        "features": [],
        "items": items,
        "views": [{"name": "centre", "x": 0, "y": 0, "z": round(eye_z, 4), "yaw": stop.get("yaw", 0)}],
        "render": {"quality": QUALITY, "exposure": stop.get("exposure", 0.0)},
        "tinypc": {"set": SET, "stop": stop["id"], "scale": k, "stand_mm": [stop["x"], stop["y"]], "floor_mm": stop["floor_z"],
                   "note": "Made by tools/make_stop_specs.py from tools/board_layout.py: edit those, not this file."},
    }

def rotors(stop, eye_z):
    """Where the tour should stand a spinning fan rotor over each fan in an "_on" render: room.props entries
    (yaw/dist/h/turn in the tour player's terms: yaw 0 = the middle of the panorama)."""
    k = stop["k"] / 1000.0; view = math.radians(stop.get("yaw", 0)); out = []
    fans = [(f"case{i}", sz, c, ax) for i, (sz, c, ax) in enumerate(L.FANS_V2)]
    for pid, model, x, y, rot, w, d, h in L.all_parts():
        if pid in stop["omit"] or pid not in L.PART_FANS: continue
        base = L.BOARD_T + seat_of(L.SETS[SET]["models"].get(pid, model))
        for j, (sz, (lx, ly, lz), ax) in enumerate(L.PART_FANS[pid]): fans.append((f"{pid}{j}", sz, (x + lx, -y + ly, base + lz), ax))
    for fid, sz, (mx, my, mz), ax in fans:
        X, Y = (mx - stop["x"]) * k, (my + stop["y"]) * k                       # room east / north of the eye
        Z = 0.002 + (TRAY_BELOW_BOARD + mz) * k                                  # centre height in the room
        b = math.atan2(X, Y) - view; r = math.hypot(X, Y)                        # bearing from the middle of the picture
        ab = (math.atan2(1, 0) if ax == "x" else 0.0) - view                     # the fan's axis (x = east, y = north)
        x3, z3 = r * math.sin(b), -r * math.cos(b)
        ax3, az3 = math.sin(ab), -math.cos(ab)
        out.append({"id": fid, "model": f"tpc_fan_rotor_{sz}", "yaw": round(math.degrees(math.atan2(x3, -z3)), 2),
                    "dist": round(r, 3), "h": round(Z - (0.47 * sz - 1.5) * k - eye_z + EYE, 3), "turn": round(-math.degrees(math.atan2(ax3, az3)), 2),
                    "size": stop["k"], "spin": 70 if sz != 88 else 90, "axis": "z",
                    "_room": [round(X, 4), round(Y, 4), round(Z, 4), round((0.47 * sz - 1.5) * k, 4), ax]})   # for check_rotors.py (the player ignores it)
    return out

if __name__ == "__main__":
    out_dir = os.path.join(ROOT, "specs", L.SETS[SET]["folder"]); os.makedirs(out_dir, exist_ok=True)
    problems = 0
    for st in L.SETS[SET]["stops"]:
        problems += len(L.check(st, L.SETS[SET]["case"], verbose=False))
        sp = spec_for(st)
        p = os.path.join(out_dir, st["id"] + ".json")
        with open(p, "w", encoding="utf-8") as fh: json.dump(sp, fh, indent=1)
        print("wrote", p, len(sp["items"]), "items, eye z", sp["views"][0]["z"])
        if L.SETS[SET].get("rotors"):
            # every candidate rotor -> .props.all.json; tools/check_rotors.py (run on a first render's room.blend) keeps the ones
            # you can see -> .props.json. Once that exists, the case and part models are picked so blades are left out
            # only where a rotor will spin (re-run this, then render again).
            pr = rotors(st, sp["views"][0]["z"])
            with open(p.replace(".json", ".props.all.json"), "w", encoding="utf-8") as fh: json.dump(pr, fh, indent=1)
            kp = p.replace(".json", ".props.json")
            if os.path.exists(kp):
                kept = {r["id"] for r in json.load(open(kp, encoding="utf-8"))}
                mask = "".join("1" if f"case{i}" in kept else "0" for i in range(len(L.FANS_V2)))
                for it in sp["items"]:
                    if it["id"] == "case": it["model"] = "tpc_case_shell_v2_on_" + mask
                    if it["id"] == "cooler": it["model"] = "tpc_tower_cooler_on" if "cooler0" in kept else "tpc_tower_cooler"
                    if it["id"] == "gpu": it["model"] = "tpc_gpu_on" if {"gpu0", "gpu1"} <= kept else "tpc_gpu"
                with open(p, "w", encoding="utf-8") as fh: json.dump(sp, fh, indent=1)
                print("    rotors kept:", sorted(kept), "-> case", mask)
            else:
                print("   ", len(pr), "candidate rotors; run check_rotors.py on a render of this spec next")
    print("clear-zone problems:", problems)
