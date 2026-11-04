"""
Writes the open-day tour (tours/tpc-open-day.json) and copies it into Room Builder's tours folder.

    python3 tools/make_tour.py [RoomBuilder folder]

Rooms come from the Room Builder library by name ("TinyPC tour - <room> - ..."; the newest wins), so render them first
(tools/build_tour_renders.py library). Hotspot positions inside the PC are worked out from board_layout.py, so they
follow the parts if the layout changes.

The story (20-30 minutes, groups of 5-10, one tablet passed round):
  Bench B0      look at and collect the seven parts
  B0..B6        fit them in order (wrong order: "not yet" with a reason); shrink in after the CPU, the RAM
                (which two slots?), the cooler, the graphics card and the power cables; questions on the bench after
                the paste and the SSD; pressing power before the cables are in does nothing
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

def lib_opt(room):
    """As lib(), or None when the room hasn't been rendered yet (or has no spec): the tour then does without it."""
    try: return lib(room)
    except (SystemExit, OSError): return None

def stop_of(room):
    """The spec the room's picture was actually rendered from (the copy in its library entry), so hotspots line up with
    the render in use even after specs/tour has moved on (e.g. a higher camera that hasn't been rendered yet)."""
    lid = lib_opt(room)
    if lid:
        p = os.path.join(RB, "library", lid, "spec.json")
        if os.path.exists(p):
            sp = json.load(open(p, encoding="utf-8"))
            if "tinypc" in sp: return sp
    return json.load(open(os.path.join(SPECS, room + ".json"), encoding="utf-8"))

def board_point(room, bx, by, bz_mm):
    """(yaw, pitch) of a point on the board (board mm, bz_mm above the board's top) seen from a tiny room's stop."""
    sp = stop_of(room); t = sp["tinypc"]
    st = next(s for s in L.STOPS_V2 + L.STOPS_TOUR if s["id"] == t["stop"]); k = st["k"] / 1000.0
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

def free_yaw(markers, cands, gap=25):
    """The first candidate yaw at least `gap` degrees from every marker already in the room."""
    d = lambda a, b: abs((a - b + 180) % 360 - 180)
    for c in cands:
        if all(d(c, mk["yaw"]) >= gap for mk in markers): return c
    return cands[0]

SLOT_ALONG = {"a1": 52, "a2": 18, "b1": -18, "b2": -52}     # mm along each slot from its middle: staggered, so the labels don't line up

def slot_labels(room, up_mm=7.0):
    """A1, A2, B1, B2 written on the four RAM slots (the board's own labels are too small to read from there). Seen from
    beside the RAM the slots line up one behind another, so each label sits at a different point along its slot."""
    out = []
    for sl in ("a1", "a2", "b1", "b2"):
        pt = next(q for q in L.all_parts() if q[0] == "dimm_slot_" + sl)
        y, p = board_point(room, pt[2], pt[3] + SLOT_ALONG[sl], up_mm)
        out.append({"id": f"lbl_{sl}_{room}", "type": "info", "yaw": y, "pitch": p, "label": sl.upper(), "title": f"Slot DIMM_{sl.upper()}",
                    "text": f"Memory channel {sl[0].upper()}, slot {sl[1]}. Two channels (A and B) with two slots each: one stick per channel lets the CPU use both at once."})
    return out

def monitor_marker(room_id, item, markers, cands=(-95, -120, -70, 150, -150)):
    """'The monitor' inside the PC (you can't see the real one from there): held up to show what's on the screen."""
    return {"id": f"m_mon_{room_id}", "type": "item", "item": item, "take": False, "yaw": free_yaw(markers, list(cands)), "pitch": 8,
            "label": "What's on the screen?"}

def props(room):
    p = os.path.join(SPECS, room + ".props.json")
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in json.load(open(p, encoding="utf-8"))] if os.path.exists(p) else []

PASTE_ROOM = None            # set in __main__: the library id of the paste room, once it's rendered

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
# The monitor, held up to look at (look only, never goes in the bag): one item per thing the screen can show.
MONITOR = [
    ("i_mon_off", "The monitor (PC off)", "tpc_monitor",
     ["Black: the PC is switched off, so nothing is being sent to the screen yet."]),
    ("i_mon_fault", "The monitor: black screen", "tpc_monitor",
     ["Still black. The fans are spinning, but the PC stopped at the memory check, before it got as far as the graphics: it has nothing to show.",
      "A black screen plus beeps is a clue: count the beeps and look for a debug light."]),
    ("i_mon_on", "The monitor: setup screen", "tpc_monitor_on",
     ["The setup screen (BIOS / UEFI): the PC passed its checks and found its parts.",
      "It lists the CPU, the 32 GB of RAM and the 1 TB SSD. Next it would load the operating system from the SSD."]),
]
ORDER = ["i_cpu", "i_ram", "i_paste", "i_cooler", "i_ssd", "i_gpu", "i_cables"]

def pc_marker(mid, yaw, pitch):
    """'The PC' on the bench: takes the parts, but only in a buildable order."""
    acc = [
        dict(item="i_cpu", correct=True, consume=True, flag="f_cpu", requires=[], go="T_cpu",
             feedback="Line up the little gold triangle with the socket's corner, drop the CPU in (no pushing!), lower the plate and latch the lever. Let's shrink down and look."),
        dict(item="i_ram", correct=True, consume=True, flag="f_ram", requires=["f_cpu"], go="T_ramq",
             notYet="Not yet: the CPU goes in first.", feedback="Before the RAM goes in, shrink down and pick the slots."),
        dict(item="i_paste", correct=True, consume=True, flag="f_paste", requires=["f_ram"], go="T_paste" if PASTE_ROOM else None,
             notYet="Not yet: CPU and RAM first. (Paste goes on just before the cooler.)",
             feedback="A little paste goes on the middle of the CPU. Let's shrink down and look." if PASTE_ROOM else "Paste on. There's a question on the PC: how much paste is right?"),
        dict(item="i_cooler", correct=True, consume=True, flag="f_cooler", requires=["f_paste"], go="T_cooler",
             notYet="Not yet: the cooler needs thermal paste on the CPU first, or the heat can't get across the gap.",
             feedback="Cooler on, screwed down evenly, fan cable plugged into CPU_FAN. Let's shrink down and look."),
        dict(item="i_ssd", correct=True, consume=True, flag="f_ssd", requires=["f_cooler"], go="B4",
             notYet="Not yet: CPU, RAM, paste and cooler first.", feedback="The SSD slots into M.2_1 at an angle, then one small screw holds it down. There's a question on the PC."),
        dict(item="i_gpu", correct=True, consume=True, flag="f_gpu", requires=["f_ssd"], go="T_gpu",
             notYet="Not yet: fit the SSD first. The graphics card covers its slot.", feedback="Graphics card into the top PCIe x16 slot until the latch clicks, and screwed to the case. Let's shrink down and look."),
        dict(item="i_cables", correct=True, consume=True, flag="f_power", requires=["f_gpu"], go="T_power",
             notYet="Not yet: power goes in last, once everything else is fitted.", feedback="24-pin and 8-pin plugged in until the latches click. Let's shrink down and look."),
    ]
    return {"id": mid, "type": "use", "yaw": yaw, "pitch": pitch, "label": "The PC", "text": "Fit the next part: pick it from your bag.",
            "accepts": acc, "wrongText": "That doesn't go in a PC."}

# Questions that appear on the bench once a part is in (room number -> (flag that shows it, question)): the paste goes
# on in B2 (no new picture), the SSD takes you to B4. Each is a one-question set: the player only checks "after" for
# questions in a set (until then the hotspot is drawn faint).
BENCH_Q = {
    2: ("f_paste", {"id": "q_paste", "label": "How much paste?",
         "text": "How much thermal paste goes on the CPU?",
         "options": [{"text": "A pea-sized dot in the middle", "correct": True, "feedback": "Yes: the cooler squashes it into a thin, even layer."},
                     {"text": "As much as possible: more paste, more cooling", "correct": False, "feedback": "No: paste is much worse at carrying heat than metal. Only enough to fill the gaps."},
                     {"text": "None: the cooler is metal, so it touches the CPU anyway", "correct": False, "feedback": "Two flat metal surfaces still leave tiny air gaps, and air carries heat badly."}]}),
    4: ("f_ssd", {"id": "q_ssd", "label": "Why now?",
         "text": "Why does the SSD go in before the graphics card?",
         "options": [{"text": "The graphics card covers the SSD's slot", "correct": True, "feedback": "Yes: once the card is in, you can't reach the M.2 slot."},
                     {"text": "The SSD has to be powered on first", "correct": False, "feedback": "No: nothing is powered on yet. It's about space."},
                     {"text": "The CPU checks it first", "correct": False, "feedback": "Not this one: it's about getting your fingers to the slot."}]}),
}

def bench_rooms():
    B = 2.855 + 0.8 - 0.375 - 0.02                      # bench centre (see specs/workbench)
    TOP = 0.9025
    # "The PC" stands just left of the case (the case spans x -0.57..-0.12 on the bench), not over it, so the parts
    # going in can be seen (4 Nov: it hid the PC)
    pc_y, pc_p, _ = room_point(-1.10, B - 0.05, TOP + 0.30)
    mo_y, mo_p, _ = room_point(0.30, 3.40, TOP + 0.30)                        # middle of the monitor's screen
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
        if n in BENCH_Q and not (n == 2 and PASTE_ROOM):       # the paste question moves into the paste room once it's rendered
            fl, q = BENCH_Q[n]
            m.append(dict(q, set=q["label"], yaw=round(pc_y - 16, 1), pitch=round(pc_p - 4, 1), after="flag:" + fl, retry=True, type="question"))
        # The power button can always be pressed (4 Nov): before the cables are in nothing happens; with the loose RAM
        # stick it beeps (F_dram); once the stick is home it starts (S_on, from B6f). Never shown locked.
        if n < 6:
            m.append(pc_marker(f"m_pc_B{n}", pc_y, pc_p))
            m.append({"id": f"m_power_B{n}", "type": "info", "yaw": pw_y, "pitch": pw_p + 6, "label": "Power button", "title": "Nothing happens",
                      "text": "No fans, no lights, no beeps: nothing at all. The PC can't get any power until the power cables are plugged in."})
        else:
            m.append({"id": "m_power_B6", "type": "go", "yaw": pw_y, "pitch": pw_p + 6, "label": "Power button", "target": "F_dram", "requires": [], "code": ""})
            r["intro"] = "Everything is in. Press the power button."
        m.append({"id": f"m_mon_B{n}", "type": "item", "item": "i_mon_off", "take": False, "yaw": mo_y, "pitch": mo_p, "label": "The monitor"})
        rooms.append(r)
    # B6 again, once the RAM stick is pushed home: same picture, and now the power button starts the PC
    f = json.loads(json.dumps(rooms[-1]))
    f.update(id="B6f", name="The workbench: RAM fixed", intro="Stick pushed home, power back on at the wall. Press the power button again.")
    for mk in f["markers"]:
        mk["id"] = mk["id"].replace("B6", "B6f")
        if mk["type"] == "go" and mk["label"] == "Power button": mk["target"] = "S_on"
    rooms.append(f)
    rooms.append({"id": "B_on", "name": "It works!", "lib": lib("B_on"), "view": "centre", "dims": DIMS, "cardWall": "left", "end": True,
                  "ambient": "fan",
                  "endText": "You built a working PC.\nCPU: runs the program. RAM: working memory. SSD: storage. GPU: the picture. Cooler: takes the heat away. Power supply: power for everything.",
                  "intro": "", "markers": [
                      {"id": "m_mon_B_on", "type": "item", "item": "i_mon_on", "take": False, "yaw": mo_y, "pitch": mo_p, "label": "The monitor"},
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
              "markers": slot_labels("T_ramq") + [
                  {"id": "q_slots", "type": "question", "yaw": sy, "pitch": sp + 6, "label": "Which slots?", "retry": True,
                   "text": "The labels on the board say DIMM_A1, A2, B1, B2 (A and B are two channels). Where do two sticks go?",
                   "options": [{"text": "A1 and A2", "correct": False, "feedback": "Both on channel A: the CPU could only use one channel. Try again."},
                               {"text": "A2 and B2", "correct": True, "go": "T_ram",
                                "feedback": "Yes: one on each channel (dual channel), in the slots the board's manual recommends. Pushing them in now..."},
                               {"text": "B1 and B2", "correct": False, "feedback": "Both on channel B. Try again."}]}]})
    # ---- RAM fitted (one stick not quite home: the planted fault)
    R.append({"id": "T_ram", "name": "RAM fitted", "lib": lib("T_ram"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "enterSound": "click",
              "intro": "Both sticks are in slots A2 and B2. Each one should be pushed down until both of its clips snap shut.",
              "markers": slot_labels("T_ram") + [
                  {"id": "i_clips", "type": "info", "yaw": sy, "pitch": sp + 4, "label": "The clips", "title": "Clips",
                   "text": "The clips at each end of a slot snap shut when a stick is pushed fully home. Have a good look..."},
                  back("g_ram_back", "B2", 0 if abs(sy) > 90 else 180)]})
    # ---- the cooler fitted (seen from behind the RAM; the loose B2 stick is in the foreground)
    fy_, fp_ = board_point("T_cooler", 130, 100, 98)
    R.append({"id": "T_cooler", "name": "The cooler", "lib": lib("T_cooler"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "Tiny again, behind the RAM. The tower in front of you is the CPU cooler, sitting on the CPU.",
              "markers": [
                  {"id": "i_fan", "type": "info", "yaw": fy_, "pitch": fp_, "label": "The fan", "title": "Fan and fins",
                   "text": "Copper heat pipes carry the heat from the CPU up into dozens of thin metal fins. The fan pushes air through the fins and the heat goes with it."},
                  {"id": "q_heat", "type": "question", "yaw": fy_ - 30, "pitch": 3, "label": "Question", "retry": True,
                   "text": "Where does the CPU's heat end up?",
                   "options": [{"text": "In the air, blown out of the case by the fans", "correct": True, "feedback": "Yes: CPU to paste to cooler to fins to air, then out of the case."},
                               {"text": "Stored in the cooler", "correct": False, "feedback": "The cooler only passes it on: it would get hotter and hotter otherwise."},
                               {"text": "Turned back into electricity", "correct": False, "feedback": "No: it just warms the air."}]},
                  back("g_cooler_back", "B3")]})
    # ---- the graphics card fitted
    gy, gp = part_point("T_gpu", "gpu", 60)
    R.append({"id": "T_gpu", "name": "The graphics card", "lib": lib("T_gpu"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "That wall in front of you is the graphics card. The SSD you fitted is hidden underneath it.",
              "markers": [
                  {"id": "i_gpu", "type": "info", "yaw": gy, "pitch": gp, "label": "Graphics card", "title": "A computer in a computer",
                   "text": "The card has its own processor (the GPU), its own fast memory and its own fans, which face the other way. It gets data from the CPU through the PCIe slot and sends the picture to the monitor."},
                  {"id": "q_gpu", "type": "question", "yaw": gy - 30, "pitch": 3, "label": "Question", "retry": True,
                   "text": "A CPU has a few big cores; a GPU has thousands of small ones. Why does that suit drawing pictures?",
                   "options": [{"text": "Millions of pixels can be worked out at the same time", "correct": True, "feedback": "Yes: lots of simple jobs done in parallel. That's also why GPUs are used for AI."},
                               {"text": "Small cores are faster than big ones", "correct": False, "feedback": "No: each GPU core is slower. There are just far more of them."},
                               {"text": "The screen only needs one colour at a time", "correct": False, "feedback": "No: every pixel needs its own colour, many times a second."}]},
                  back("g_gpu_back", "B5")]})
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
    R[-1]["markers"].append(monitor_marker("F_dram", "i_mon_fault", R[-1]["markers"]))
    # ---- switched on: the loose stick
    fy, fp = part_point("F_ram", "dimm_slot_b2", 7)
    R.append({"id": "F_ram", "name": "The RAM", "lib": lib("F_ram"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "ambient": "fan", "props": props("F_ram"), "intro": "Look closely at both sticks and their clips.",
              "markers": slot_labels("F_ram") + [
                  {"id": "q_whats_wrong", "type": "question", "set": "The RAM", "yaw": fy, "pitch": fp + 6, "label": "What's wrong?", "retry": True,
                   "text": "What's wrong here?",
                   "options": [{"text": "The stick in B2 isn't pushed all the way in: its clip is still open", "correct": True, "flag": "f_found",
                                "feedback": "Well spotted. Its gold contacts aren't touching the slot's contacts properly."},
                               {"text": "The sticks are in the wrong slots", "correct": False, "feedback": "No: A2 and B2 is right. Look at the clips."},
                               {"text": "The RAM is too slow", "correct": False, "feedback": "No: it would still start. Look at the clips."}]},
                  {"id": "q_safe", "type": "question", "set": "The RAM", "yaw": fy + 40, "pitch": 3, "label": "Fix it", "retry": True, "after": "flag:f_found",
                   "text": "Before you push the stick in, what do you do first?",
                   "options": [{"text": "Switch off and unplug at the wall", "correct": True, "flag": "f_ramclick", "go": "R_fixed",
                                "feedback": "Yes: never fit or move parts with the power on."},
                               {"text": "Nothing: push it in while it's running", "correct": False, "feedback": "No! That can damage the RAM or the board. Switch off first."}]}]})
    R[-1]["markers"].append(monitor_marker("F_ram", "i_mon_fault", R[-1]["markers"]))
    R.append({"id": "R_fixed", "name": "Click!", "lib": lib("R_fixed"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "enterSound": "click",
              "intro": "Switched off, stick pushed down firmly: click, both clips shut.\nBack to full size and try the power again.",
              "markers": [back("g_fixed_back", "B6f", 0 if abs(fy) > 90 else 180)]})
    R.append({"id": "S_on", "name": "It's alive!", "lib": lib("S_on"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "ambient": "fan", "enterSound": "post:S", "props": props("S_on"),
              "intro": "One short beep: the start-up checks (the POST: power-on self-test) all passed.\nFans spinning, lights on, no debug light.",
              "markers": [
                  {"id": "i_dbg_off", "type": "info", "yaw": ly, "pitch": lp + 6, "label": "Debug lights", "title": "All clear",
                   "text": "No light on: CPU, memory, graphics and boot device all passed."},
                  back("g_on_back", "B_on")]})
    R[-1]["markers"].append(monitor_marker("S_on", "i_mon_on", R[-1]["markers"]))
    # ---- the pea of paste on the CPU (only once it's rendered: until then the paste question stays on the bench)
    if PASTE_ROOM:
        py_, pp_ = board_point("T_paste", 92, 80, 2.0)
        q = dict(BENCH_Q[2][1]); q.update(type="question", yaw=round(py_ - 25, 1), pitch=3, retry=True)
        dot = {"id": "i_paste_dot", "type": "info", "yaw": py_, "pitch": pp_, "label": "The paste", "title": "A pea of paste",
               "text": "About 5 mm across, in the middle of the lid. The cooler's flat copper base presses it out into a layer thinner than a hair."}
        R.append({"id": "T_paste", "name": "Thermal paste", "lib": PASTE_ROOM, "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
                  "intro": "Tiny again, on the CPU lid. That grey dome is the paste, squeezed out of the syringe. The cooler goes on next and squashes it flat.",
                  "markers": [dot, q, back("g_paste_back", "B2", 180 if abs(py_) < 90 else 0)]})
    return R

if __name__ == "__main__":
    PASTE_ROOM = lib_opt("T_paste")
    print("paste room:", PASTE_ROOM or "not rendered yet (paste question stays on the bench)")
    items = [{"id": i, "name": n, "model": m, "description": "", "pages": p} for i, n, m, p in ITEMS + MONITOR]
    tour = {"version": 1, "id": TOUR_ID, "name": "TinyPC - build a PC (open day)", "start": "B0",
            "description": "Collect the parts, build the PC in order, shrink inside to see them fitted, then switch on, find the fault and fix it.",
            "items": items, "rooms": bench_rooms() + tiny_rooms()}
    os.makedirs(os.path.join(ROOT, "tours"), exist_ok=True)
    out = os.path.join(ROOT, "tours", TOUR_ID + ".json")
    with open(out, "w", encoding="utf-8") as fh: json.dump(tour, fh, indent=1)
    shutil.copy2(out, os.path.join(RB, "tours", TOUR_ID + ".json"))
    print("wrote", out, "and copied it to", os.path.join(RB, "tours"), "|", len(tour["rooms"]), "rooms")
