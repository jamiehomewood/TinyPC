"""
Writes the open-day tour (tours/tpc-open-day.json) and copies it into Room Builder's tours folder.

    python3 tools/make_tour.py [RoomBuilder folder]

Rooms come from the Room Builder library by name ("TinyPC tour - <room> - ..."; the newest wins), so render them first
(tools/build_tour_renders.py library). Hotspot positions inside the PC are worked out from board_layout.py, so they
follow the parts if the layout changes.

The story (20-30 minutes, groups of 5-10, one tablet passed round):
  Bench B0      look at and collect the seven parts
  B0..B6        fit them in order (wrong order: "not yet" with a reason); shrink in after the CPU, the RAM
                (which two slots?) and the power cables; pressing power before the cables are in does nothing
  B6 power      three long beeps: F_dram (DRAM debug light) -> F_ram (one stick not clicked in) -> switch off ->
                R_fixed -> back to B6 -> power again -> S_on (one short beep, fans) -> B_on (setup screen, summing up)
"""
import glob, json, math, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import board_layout as L

RB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), "RoomBuilder")
TOUR_ID = "tpc-open-day"
SPECS = os.path.join(ROOT, "specs", "tour")
DIMS = {"w": 6.4, "d": 5.71, "h": 2.244, "eye": 1.12, "preset": "igloo-main"}

def lib(room):
    """Newest library entry made from specs/tour/<room>.json (matched on the spec's name)."""
    want = json.load(open(os.path.join(SPECS, room + ".json"), encoding="utf-8"))["name"]
    hits = []
    for mp in glob.glob(os.path.join(RB, "library", "*", "meta.json")):
        try: meta = json.load(open(mp, encoding="utf-8"))
        except Exception: continue
        if meta.get("name") == want: hits.append(os.path.basename(os.path.dirname(mp)))
    if not hits: raise SystemExit(f"No library entry called '{want}' yet: render the tour rooms first.")
    return sorted(hits)[-1]

def stop_of(room):
    return json.load(open(os.path.join(SPECS, room + ".json"), encoding="utf-8"))

def board_point(room, bx, by, bz_mm):
    """(yaw, pitch) of a point on the board (board mm, bz_mm above the board's top) seen from a tiny room's stop."""
    sp = stop_of(room); t = sp["tinypc"]
    st = next(s for s in L.STOPS_V2 if s["id"] == t["stop"]); k = st["k"] / 1000.0
    X, Y = (bx - st["x"]) * k, -(by - st["y"]) * k
    Z = 0.002 + (7.0 + L.BOARD_T + bz_mm) * k
    eye = sp["views"][0]["z"]
    yaw = math.degrees(math.atan2(X, Y)) - st.get("yaw", 0)
    yaw = (yaw + 180) % 360 - 180
    return round(yaw, 1), round(math.degrees(math.atan2(Z - eye, math.hypot(X, Y))), 1)

def part_point(room, pid, up_mm=0.0):
    p = next(p for p in L.all_parts() if p[0] == pid)
    return board_point(room, p[2], p[3], up_mm)

def room_point(x, y, z, eye=1.12):
    """(yaw, pitch, dist) of a point in a normal-size room (the workbench), x east, y north, z up."""
    return round(math.degrees(math.atan2(x, y)), 1), round(math.degrees(math.atan2(z - eye, math.hypot(x, y))), 1), round(math.hypot(x, y), 3)

def props(room):
    p = os.path.join(SPECS, room + ".props.json")
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in json.load(open(p, encoding="utf-8"))] if os.path.exists(p) else []

# ------------------------------------------------------------------ the parts (items)
ITEMS = [
    ("i_cpu", "CPU (processor)", "tpc_cpu",
     ["The CPU (central processing unit) runs the program: it fetches each instruction from memory, decodes it, and carries it out. Billions of times a second.",
      "This one has 8 cores (8 processors in one chip) running at 3.6 GHz: 3.6 billion clock ticks a second.",
      "Underneath: over a thousand gold pads. Each one touches a spring pin in the socket on the motherboard."]),
    ("i_ram", "RAM (2 sticks)", "tpc_dimm",
     ["RAM is the computer's working memory: the programs and data the CPU is using right now.",
      "It is fast, but it forgets everything when the power goes off (volatile).",
      "Two 16 GB sticks = 32 GB. Fitted in the right pair of slots, the CPU can use both at once (dual channel)."]),
    ("i_paste", "Thermal paste", "tpc_paste_syringe",
     ["Thermal paste fills the tiny gaps between the CPU and its cooler, so heat can flow out of the chip.",
      "A pea-sized dot in the middle is enough: the cooler squashes it flat."]),
    ("i_cooler", "CPU cooler", "tpc_tower_cooler",
     ["A busy CPU can make over 100 watts of heat. The copper base soaks it up, heat pipes carry it into the fins, and the fan blows it away.",
      "Without a cooler the CPU would overheat within seconds and switch itself off."]),
    ("i_ssd", "SSD (storage)", "tpc_m2_ssd",
     ["The SSD (solid-state drive) keeps your files, programs and the operating system when the power is off (non-volatile).",
      "It is slower than RAM but holds far more: this one is 1 TB. It plugs straight into the motherboard (M.2) and talks to the CPU over PCIe lanes."]),
    ("i_gpu", "Graphics card (GPU)", "tpc_gpu",
     ["The GPU (graphics processing unit) draws the picture on the screen.",
      "It has thousands of small cores that work in parallel: great for graphics, video and AI. It plugs into the long PCIe x16 slot."]),
    ("i_cables", "Power cables", "tpc_atx24",
     ["From the power supply (PSU): the 24-pin cable powers the motherboard, and the 8-pin cable feeds the CPU's power circuits.",
      "The PSU turns mains electricity into the low voltages the parts need (12 V, 5 V, 3.3 V)."]),
]
ORDER = ["i_cpu", "i_ram", "i_paste", "i_cooler", "i_ssd", "i_gpu", "i_cables"]

def pc_marker(mid, yaw, pitch):
    """'The PC' on the bench: takes the parts, but only in a buildable order."""
    acc = [
        dict(item="i_cpu", correct=True, consume=True, flag="f_cpu", requires=[], go="T_cpu",
             feedback="Line up the little gold triangle with the socket's corner, drop the CPU in (no pushing!), lower the plate and latch the lever. Let's shrink down and look."),
        dict(item="i_ram", correct=True, consume=True, flag="f_ram", requires=["f_cpu"], go="T_ramq",
             notYet="Not yet: the CPU goes in first.", feedback="Before the RAM goes in, shrink down and pick the slots."),
        dict(item="i_paste", correct=True, consume=True, flag="f_paste", requires=["f_ram"], go=None,
             notYet="Not yet: CPU and RAM first. (Paste goes on just before the cooler.)", feedback="A pea-sized dot of paste on the middle of the CPU. Now the cooler can go on."),
        dict(item="i_cooler", correct=True, consume=True, flag="f_cooler", requires=["f_paste"], go="B3",
             notYet="Not yet: the cooler needs thermal paste on the CPU first, or the heat can't get across the gap.",
             feedback="Cooler on, screwed down evenly, fan cable plugged into CPU_FAN."),
        dict(item="i_ssd", correct=True, consume=True, flag="f_ssd", requires=["f_cooler"], go="B4",
             notYet="Not yet: CPU, RAM, paste and cooler first.", feedback="The SSD slots into M.2_1 at an angle, then one small screw holds it down."),
        dict(item="i_gpu", correct=True, consume=True, flag="f_gpu", requires=["f_ssd"], go="B5",
             notYet="Not yet: fit the SSD first. The graphics card covers its slot.", feedback="Graphics card into the top PCIe x16 slot until the latch clicks, and screwed to the case."),
        dict(item="i_cables", correct=True, consume=True, flag="f_power", requires=["f_gpu"], go="T_power",
             notYet="Not yet: power goes in last, once everything else is fitted.", feedback="24-pin and 8-pin plugged in until the latches click. Let's shrink down and look."),
    ]
    return {"id": mid, "type": "use", "yaw": yaw, "pitch": pitch, "label": "The PC", "text": "Fit the next part: pick it from your bag.",
            "accepts": acc, "wrongText": "That doesn't go in a PC."}

def bench_rooms():
    B = 2.855 + 0.8 - 0.375 - 0.02                      # bench centre (see specs/workbench)
    TOP = 0.9025
    pc_y, pc_p, _ = room_point(-0.62, B + 0.05, TOP + 0.48)                  # upper left of the PC
    pw_y, pw_p, _ = room_point(-0.3, B - 0.02, TOP + 0.48)                   # its top front corner (the power button)
    ex_y, ex_p, _ = room_point(3.4, -0.6, TOP + 0.95)
    E = 3.2 + 0.8 - 0.375 - 0.02                                             # right-hand bench centre (x); it runs along y
    # where the parts lie: four on the front bench's front strip, three on the right-hand bench (room x, y)
    SPOTS = {"i_cooler": (-0.95, 2.97), "i_cpu": (-0.62, 2.97), "i_paste": (-0.32, 2.97), "i_ram": (-0.02, 2.97),
             "i_ssd": (E - 0.28, 0.35), "i_gpu": (E - 0.28, -0.42), "i_cables": (E - 0.28, -1.55)}
    rooms = []
    for n in range(7):
        r = {"id": f"B{n}", "name": "The workbench" if n == 0 else f"The workbench ({n} of 6 fitted)" if n < 6 else "The workbench: all fitted",
             "lib": lib(f"B{n}"), "view": "centre", "dims": DIMS, "cardWall": "left", "end": False, "endText": "", "markers": []}
        m = r["markers"]
        if n == 0:
            r["intro"] = ("Your team's job: build this PC and get it to start.\nThe parts are on the two benches. Pick each one up to find out "
                          "what it does (it goes in your bag), then fit them into the PC, one at a time.")
            for iid, name, model, pages in ITEMS:
                yaw, pitch, dist = room_point(*SPOTS[iid], TOP)
                m.append({"id": f"m_{iid}", "type": "item", "item": iid, "take": True, "yaw": yaw, "pitch": pitch, "label": name,
                          "dist": dist, "h": TOP, "turn": round(yaw, 1), "size": 1, "show3d": True})
            m.append({"id": "m_example", "type": "info", "yaw": ex_y, "pitch": ex_p + 4, "label": "A finished PC",
                      "title": "What you're building", "text": "This one is finished and switched on. Yours has the same parts: a motherboard, CPU, RAM, cooler, SSD, graphics card and power."})
        if n < 7:
            if n < 6: m.append(pc_marker(f"m_pc_B{n}", pc_y, pc_p))
            if n < 6:
                m.append({"id": f"m_power_B{n}", "type": "go", "yaw": pw_y, "pitch": pw_p + 6, "label": "Power button", "target": "B6",
                          "requires": ["f_power"], "lockedText": "Nothing happens at all: no fans, no lights. Nothing can work until the power cables are in.", "code": ""})
            else:
                m.append({"id": "m_power_B6", "type": "go", "yaw": pw_y, "pitch": pw_p + 6, "label": "Power button", "target": "S_on",
                          "requires": ["f_ramclick"], "lockedGo": {"f_ramclick": "F_dram"}, "code": ""})
                r["intro"] = "Everything is in. Press the power button."
        rooms.append(r)
    rooms.append({"id": "B_on", "name": "It works!", "lib": lib("B_on"), "view": "centre", "dims": DIMS, "cardWall": "left", "end": True,
                  "ambient": "fan",
                  "endText": "You built a working PC.\nCPU: runs the program. RAM: working memory. SSD: storage. GPU: the picture. Cooler: takes the heat away. Power supply: power for everything.",
                  "intro": "", "markers": [
                      {"id": "q_sum1", "type": "question", "set": "Summing up", "yaw": -90, "pitch": 5, "label": "Summing up", "retry": True,
                       "text": "Which part forgets everything when the power goes off?",
                       "options": [{"text": "The SSD", "correct": False, "feedback": "No: the SSD keeps your files with the power off."},
                                   {"text": "The RAM", "correct": True, "feedback": "Yes: RAM is fast working memory, but volatile."},
                                   {"text": "The CPU", "correct": False, "feedback": "The CPU has a little memory (cache) that forgets too, but the big one is RAM."}]},
                      {"id": "q_sum2", "type": "question", "set": "Summing up", "yaw": -90, "pitch": 5, "label": "Summing up", "retry": True,
                       "text": "Three long beeps at switch-on usually mean...",
                       "options": [{"text": "a memory (RAM) problem", "correct": True, "feedback": "Yes. Like the stick that wasn't clicked in."},
                                   {"text": "everything's fine", "correct": False, "feedback": "No: one short beep means all the checks passed."},
                                   {"text": "the screen is unplugged", "correct": False, "feedback": "Not usually: that's normally a graphics code."}]},
                      {"id": "q_sum3", "type": "question", "set": "Summing up", "yaw": -90, "pitch": 5, "label": "Summing up", "retry": True,
                       "text": "Why does the cooler need thermal paste?",
                       "options": [{"text": "To glue it on", "correct": False, "feedback": "No: screws hold it on."},
                                   {"text": "To fill the tiny air gaps so heat flows into the cooler", "correct": True, "feedback": "Yes. Air is a poor conductor of heat."},
                                   {"text": "To stop electricity leaking", "correct": False, "feedback": "No: it's about heat."}]},
                  ]})
    return rooms

def tiny_rooms():
    R = []
    back = lambda mid, target, yaw=180: {"id": mid, "type": "go", "yaw": yaw, "pitch": 0, "label": "Back to full size", "target": target, "requires": [], "code": ""}
    # ---- on the CPU, just fitted
    cy, cp = board_point("T_cpu", 92, 112, 5.3)
    R.append({"id": "T_cpu", "name": "Standing on the CPU", "lib": lib("T_cpu"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "You're a few millimetres tall, standing on the CPU's metal lid. The chip itself is underneath, smaller than a fingernail.",
              "markers": [
                  {"id": "i_lid", "type": "info", "yaw": 0, "pitch": -45, "label": "The lid", "title": "The lid (heat spreader)",
                   "text": "The metal lid spreads the chip's heat out so the cooler can take it away. The markings say what it is: TPC-9, 8 cores, 3.6 GHz."},
                  {"id": "q_cpu", "type": "question", "yaw": -60, "pitch": 3, "label": "Question", "retry": True,
                   "text": "3.6 GHz means the CPU's clock ticks...",
                   "options": [{"text": "3.6 million times a second", "correct": False, "feedback": "Bigger! Giga = billion."},
                               {"text": "3.6 billion times a second", "correct": True, "feedback": "Yes: 3,600,000,000 ticks every second."},
                               {"text": "3.6 times a second", "correct": False, "feedback": "Much, much faster than that."}]},
                  {"id": "i_ramside", "type": "info", "yaw": 0, "pitch": 4, "label": "The RAM slots", "title": "Next door: the memory slots",
                   "text": "Those four long slots are for the RAM. The CPU talks to the RAM through hundreds of copper traces in the board."},
                  back("g_cpu_back", "B1")]})
    # ---- the empty RAM slots: which two?
    sy, sp = part_point("T_ramq", "dimm_slot_b2", 7)
    R.append({"id": "T_ramq", "name": "The RAM slots", "lib": lib("T_ramq"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "Four empty slots, clips open. You have two sticks.",
              "markers": [
                  {"id": "q_slots", "type": "question", "yaw": sy, "pitch": sp + 6, "label": "Which slots?", "retry": True,
                   "text": "The labels on the board say DIMM_A1, A2, B1, B2 (A and B are two channels). Where do two sticks go?",
                   "options": [{"text": "A1 and A2", "correct": False, "feedback": "Both on channel A: the CPU could only use one channel. Try again."},
                               {"text": "A2 and B2", "correct": True, "go": "T_ram",
                                "feedback": "Yes: one on each channel (dual channel), in the slots the board's manual recommends. Pushing them in now..."},
                               {"text": "B1 and B2", "correct": False, "feedback": "Both on channel B. Try again."}]}]})
    # ---- RAM fitted (one stick not quite home: the planted fault)
    R.append({"id": "T_ram", "name": "RAM fitted", "lib": lib("T_ram"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "Both sticks are in slots A2 and B2. Each one should be pushed down until both of its clips snap shut.",
              "markers": [
                  {"id": "i_clips", "type": "info", "yaw": sy, "pitch": sp + 4, "label": "The clips", "title": "Clips",
                   "text": "The clips at each end of a slot snap shut when a stick is pushed fully home. Have a good look..."},
                  back("g_ram_back", "B2", 0 if abs(sy) > 90 else 180)]})
    # ---- power cables in
    ly, lp = board_point("T_power", 297, 169, 0.6)
    ay, ap = part_point("T_power", "atx24", 25)
    R.append({"id": "T_power", "name": "Power in", "lib": lib("T_power"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "The 24-pin cable is plugged in: power for the whole motherboard.",
              "markers": [
                  {"id": "i_24pin", "type": "info", "yaw": ay, "pitch": ap, "label": "24-pin power", "title": "24-pin power",
                   "text": "24 wires: yellow = 12 V, red = 5 V, orange = 3.3 V, black = 0 V (ground). The green wire tells the power supply to switch on."},
                  {"id": "i_debug", "type": "info", "yaw": ly, "pitch": lp + 6, "label": "Debug lights", "title": "Debug lights",
                   "text": "Four little lights: CPU, DRAM, VGA, BOOT. At switch-on the board checks each part in turn. If it gets stuck, that light stays on."},
                  back("g_power_back", "B6")]})
    # ---- switched on: the DRAM light
    R.append({"id": "F_dram", "name": "Something's wrong", "lib": lib("F_dram"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "ambient": "fan", "enterSound": "post:LLL", "props": props("F_dram"),
              "intro": "The fans spun up... then three long beeps, and nothing on the screen.\nFind the light that's on.",
              "markers": [
                  {"id": "i_dbg_on", "type": "info", "yaw": ly, "pitch": lp + 6, "label": "Debug lights", "title": "The DRAM light is on",
                   "text": "The board got stuck checking the memory (DRAM = the RAM). Three long beeps say the same thing."},
                  {"id": "g_to_ram", "type": "go", "yaw": ly - 35, "pitch": 0, "label": "Go and check the RAM", "target": "F_ram", "requires": [], "code": ""}]})
    # ---- switched on: the loose stick
    fy, fp = part_point("F_ram", "dimm_slot_b2", 7)
    R.append({"id": "F_ram", "name": "The RAM", "lib": lib("F_ram"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "ambient": "fan", "props": props("F_ram"), "intro": "Look closely at both sticks and their clips.",
              "markers": [
                  {"id": "q_whats_wrong", "type": "question", "yaw": fy, "pitch": fp + 6, "label": "What's wrong?", "retry": True,
                   "text": "What's wrong here?",
                   "options": [{"text": "The stick in B2 isn't pushed all the way in: its clip is still open", "correct": True, "flag": "f_found",
                                "feedback": "Well spotted. Its gold contacts aren't touching the slot's contacts properly."},
                               {"text": "The sticks are in the wrong slots", "correct": False, "feedback": "No: A2 and B2 is right. Look at the clips."},
                               {"text": "The RAM is too slow", "correct": False, "feedback": "No: it would still start. Look at the clips."}]},
                  {"id": "q_safe", "type": "question", "yaw": fy + 40, "pitch": 3, "label": "Fix it", "retry": True, "after": "flag:f_found",
                   "text": "Before you push the stick in, what do you do first?",
                   "options": [{"text": "Switch off and unplug at the wall", "correct": True, "flag": "f_ramclick", "go": "R_fixed",
                                "feedback": "Yes: never fit or move parts with the power on."},
                               {"text": "Nothing: push it in while it's running", "correct": False, "feedback": "No! That can damage the RAM or the board. Switch off first."}]}]})
    R.append({"id": "R_fixed", "name": "Click!", "lib": lib("R_fixed"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "Switched off, stick pushed down firmly: click, both clips shut.\nBack to full size and try the power again.",
              "markers": [back("g_fixed_back", "B6", 0 if abs(fy) > 90 else 180)]})
    R.append({"id": "S_on", "name": "It's alive!", "lib": lib("S_on"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "ambient": "fan", "enterSound": "post:S", "props": props("S_on"),
              "intro": "One short beep: the start-up checks (the POST: power-on self-test) all passed.\nFans spinning, lights on, no debug light.",
              "markers": [
                  {"id": "i_dbg_off", "type": "info", "yaw": ly, "pitch": lp + 6, "label": "Debug lights", "title": "All clear",
                   "text": "No light on: CPU, memory, graphics and boot device all passed."},
                  back("g_on_back", "B_on")]})
    return R

if __name__ == "__main__":
    items = [{"id": i, "name": n, "model": m, "description": "", "pages": p} for i, n, m, p in ITEMS]
    tour = {"version": 1, "id": TOUR_ID, "name": "TinyPC - build a PC (open day)", "start": "B0",
            "description": "Collect the parts, build the PC in order, shrink inside to see them fitted, then switch on, find the fault and fix it.",
            "items": items, "rooms": bench_rooms() + tiny_rooms()}
    os.makedirs(os.path.join(ROOT, "tours"), exist_ok=True)
    out = os.path.join(ROOT, "tours", TOUR_ID + ".json")
    with open(out, "w", encoding="utf-8") as fh: json.dump(tour, fh, indent=1)
    shutil.copy2(out, os.path.join(RB, "tours", TOUR_ID + ".json"))
    print("wrote", out, "and copied it to", os.path.join(RB, "tours"), "|", len(tour["rooms"]), "rooms")
