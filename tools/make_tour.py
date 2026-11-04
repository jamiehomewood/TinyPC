"""
Writes the open-day tour (tours/tpc-open-day.json) and copies it into Room Builder's tours folder.

    python3 tools/make_tour.py [RoomBuilder folder]

Rooms come from the Room Builder library by name ("TinyPC tour - <room> - ..."; the newest wins), so render them first
(tools/build_tour_renders.py library). Hotspot positions inside the PC are worked out from board_layout.py, so they
follow the parts if the layout changes.

The story (20-30 minutes, groups of 5-10, one tablet passed round):
  Bench B0      look at and collect the seven parts
  T_cpu         can also look under the lid (T_delid) and stand on the chip (T_die, an X-ray map), then back to B1
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

def stop_of(room):
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
             notYet="Not yet: CPU and RAM first. (Paste goes on just before the cooler.)", feedback="Paste on. There's a question on the PC: how much paste is right?"),
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
        if n in BENCH_Q:
            fl, q = BENCH_Q[n]
            m.append(dict(q, set=q["label"], yaw=round(pc_y - 16, 1), pitch=round(pc_p - 4, 1), after="flag:" + fl, retry=True, type="question"))
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
                      {"id": "g_run", "type": "go", "yaw": round(pc_y - 14, 1), "pitch": round(pc_p + 4, 1), "label": "Watch the CPU work",
                       "target": "T_run", "requires": [], "code": ""},
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

def core_sim():
    """Register-level fetch-decode-execute of a 3-line program (LOAD 200, ADD 201, STORE 202 with 3 and 4 as data), as
    the states of the player's step-through diagram (room.sim). Boxes face the centre at 2.5 m; the left wall has the
    explanation panel, the right the RAM."""
    D = 2.5
    boxes = [dict(id="CU", label="CONTROL UNIT (decodes)", yaw=-42, h=1.68, w=1.15, hh=0.5, color="#c69cff"),
             dict(id="PC", label="PC (program counter)", yaw=-12, h=1.72, w=0.95, hh=0.45),
             dict(id="MAR", label="MAR (memory address)", yaw=18, h=1.72, w=0.95, hh=0.45),
             dict(id="CIR", label="CIR (current instruction)", yaw=-12, h=1.12, w=0.95, hh=0.45),
             dict(id="MDR", label="MDR (memory data)", yaw=18, h=1.12, w=0.95, hh=0.45),
             dict(id="ALU", label="ALU (arithmetic logic unit)", yaw=-42, h=1.08, w=1.15, hh=0.5, color="#ff9f6b"),
             dict(id="ACC", label="ACC (accumulator)", yaw=-42, h=0.5, w=1.15, hh=0.42, color="#ff9f6b"),
             dict(id="RAM", label="RAM (main memory)", yaw=62, h=1.2, w=1.25, hh=1.55, color="#7fe39a"),
             dict(id="PANEL", kind="panel", yaw=-100, h=1.3, w=2.3, hh=1.1, dist=2.6)]
    for b in boxes: b.setdefault("dist", D)
    mem = {100: "LOAD 200", 101: "ADD 201", 102: "STORE 202", 200: "3", 201: "4", 202: "0"}
    def ram(hl=None):
        rows = []
        for a_ in (100, 101, 102, None, 200, 201, 202):
            rows.append("" if a_ is None else (">" if a_ == hl else "") + f"{a_}  {mem[a_]}")
        return "\n".join(rows)
    mv = lambda f, t, txt, **st: {"from": f, "to": t, "text": txt, "set": st}
    S = []
    def fetch(pc, instr, n):
        if n == 1:
            S.append(dict(title="FETCH (1 of 3)", hi=["PC", "MAR"], text=f"The address in the PC ({pc}) is copied into the MAR, the memory address register. It tells the RAM which address we want.",
                          moves=[mv("PC", "MAR", str(pc), MAR=str(pc), RAM=ram(pc))]))
            S.append(dict(title="FETCH (2 of 3)", hi=["RAM", "MDR"], text=f"The RAM sends back what's stored at {pc}, along the data bus, into the MDR (memory data register): the instruction {instr}.",
                          moves=[mv("RAM", "MDR", instr, MDR=instr)]))
            S.append(dict(title="FETCH (3 of 3)", hi=["CIR", "PC"], text=f"The instruction is copied into the CIR (current instruction register), and the PC goes up by 1 to {pc + 1}, ready for the next one.",
                          moves=[mv("MDR", "CIR", instr, CIR=instr)], set={"PC": str(pc + 1)}))
        else:
            S.append(dict(title="FETCH", hi=["PC", "MAR", "MDR", "CIR"], text=f"Next cycle. The same three fetch moves: PC → MAR ({pc}), RAM → MDR, MDR → CIR. The PC goes up to {pc + 1}.",
                          moves=[mv("PC", "MAR", str(pc), MAR=str(pc), RAM=ram(pc)), mv("RAM", "MDR", instr, MDR=instr), mv("MDR", "CIR", instr, CIR=instr)],
                          set={"PC": str(pc + 1)}))
    S.append(dict(title="A program in memory", hi=["RAM", "PC"], text="The RAM (right) holds a 3-line program at addresses 100 to 102, and its numbers at 200 to 202. The PC holds 100: the address of the first instruction. Tap Next step.", moves=[]))
    fetch(100, "LOAD 200", 1)
    S.append(dict(title="DECODE", hi=["CU", "CIR"], text="The control unit decodes the instruction. LOAD 200 means: copy the number stored at address 200 into the accumulator.",
                  moves=[mv("CIR", "CU", "LOAD 200", CU="LOAD\nfrom 200 → ACC")]))
    S.append(dict(title="EXECUTE", hi=["MAR", "MDR", "ACC"], text="Execute: address 200 goes into the MAR, the RAM sends back 3, and the 3 goes into the ACC (accumulator).",
                  moves=[mv("CIR", "MAR", "200", MAR="200", RAM=ram(200)), mv("RAM", "MDR", "3", MDR="3"), mv("MDR", "ACC", "3", ACC="3")]))
    fetch(101, "ADD 201", 2)
    S.append(dict(title="DECODE", hi=["CU", "CIR"], text="ADD 201 means: add the number stored at address 201 to whatever is in the accumulator.",
                  moves=[mv("CIR", "CU", "ADD 201", CU="ADD\nACC + 201")]))
    S.append(dict(title="EXECUTE", hi=["ALU", "ACC"], text="The 4 comes in from address 201. The ALU (arithmetic logic unit) adds it to the accumulator: 3 + 4 = 7.",
                  moves=[mv("CIR", "MAR", "201", MAR="201", RAM=ram(201)), mv("RAM", "MDR", "4", MDR="4"), mv("MDR", "ALU", "4", ALU="? + 4"),
                         mv("ACC", "ALU", "3", ALU="3 + 4"), mv("ALU", "ACC", "7", ALU="3 + 4 = 7", ACC="7")]))
    fetch(102, "STORE 202", 2)
    S.append(dict(title="DECODE", hi=["CU", "CIR"], text="STORE 202 means: copy the accumulator back into the RAM, at address 202.",
                  moves=[mv("CIR", "CU", "STORE 202", CU="STORE\nACC → 202")]))
    mem[202] = "7"
    S.append(dict(title="EXECUTE: done", hi=["RAM"], text="The answer goes back to the RAM: address 202 now holds 7. That's the whole program. A real core does billions of these cycles every second.",
                  moves=[mv("CIR", "MAR", "202", MAR="202", RAM=ram(202).replace("202  7", "202  0")), mv("ACC", "MDR", "7", MDR="7"), mv("MDR", "RAM", "7", RAM=ram(202))]))
    mem[202] = "0"
    init = {"PC": "100", "MAR": "–", "MDR": "–", "CIR": "–", "CU": "–", "ALU": "–", "ACC": "0", "RAM": ram()}
    buses = [["PC", "MAR"], ["MAR", "RAM"], ["RAM", "MDR"], ["MDR", "CIR"], ["CIR", "CU"], ["CU", "ALU"], ["ALU", "ACC"], ["MDR", "ALU"]]
    return {"boxes": boxes, "buses": buses, "init": init, "states": S}

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
                  {"id": "g_delid", "type": "go", "yaw": 35, "pitch": -25, "label": "Look under the lid", "target": "T_delid", "requires": [], "code": ""},
                  back("g_cpu_back", "B1")]})
    # ---- under the lid (imagined: in real life taking the lid off usually breaks the CPU)
    dy, dp = board_point("T_delid", 92, 100, 4.9)
    uy, up_ = board_point("T_delid", 92, 66.1, 16.4)           # the middle of the lid's underside (lid turned back 145 degrees)
    cy_, cp_ = board_point("T_delid", 106.5, 100, 4.5)
    R.append({"id": "T_delid", "name": "Under the lid", "lib": lib("T_delid"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "Imagine you could peel the metal lid back. (In real life this usually breaks the CPU.)\nThe flat slab in front of you is the actual chip.",
              "markers": [
                  {"id": "i_chip", "type": "info", "yaw": dy, "pitch": dp + 3, "label": "The chip", "title": "The chip (the die)",
                   "text": "A slab of silicon 20 by 12 mm and less than 1 mm thick. It holds billions of transistors: tiny switches, each far smaller than a bacterium. Everything the CPU does happens in here."},
                  {"id": "i_solder", "type": "info", "yaw": dy + 18, "pitch": dp - 2, "label": "Solder", "title": "Soldered to the lid",
                   "text": "The shiny layer is solder: it joined the chip to the lid, so heat flows straight out into the lid and then the cooler."},
                  {"id": "i_lidunder", "type": "info", "yaw": uy, "pitch": up_, "label": "Inside the lid", "title": "Inside the lid",
                   "text": "The bright patch is where the lid was soldered to the chip. The black line round the edge is the glue that held it down."},
                  {"id": "i_substrate", "type": "info", "yaw": cy_, "pitch": cp_ + 3, "label": "The green board", "title": "The CPU's own little circuit board",
                   "text": "The chip sits on its own small circuit board. Thousands of tiny connections under the chip spread out through it to the gold pads underneath, which touch the pins in the socket. The little capacitors smooth out the power."},
                  {"id": "g_onchip", "type": "go", "yaw": dy - 25, "pitch": dp, "label": "Shrink onto the chip", "target": "T_die", "requires": [], "code": ""},
                  {"id": "g_lidback", "type": "go", "yaw": 180, "pitch": 0, "label": "Put the lid back", "target": "T_cpu", "requires": [], "code": ""}]})
    # ---- on the chip: its circuits drawn as an X-ray map (the circuits are really on the underside, facing the pads)
    def die(u, v): return board_point("T_die", 92 - 10 + 20 * u, 100 - (-6 + 12 * v), 4.8)
    c2y, c2p = die(0.322, 0.818); l3y, l3p = die(0.62, 0.565); mcy, mcp = die(0.927, 0.57); ioy, iop = die(0.5, 0.075); c6y, c6p = die(0.322, 0.25)
    R.append({"id": "T_die", "name": "On the chip", "lib": lib("T_die"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "hideBag": True,                                          # the floor is the chip map (engine_patch_2026-11-04b.py)
              "intro": "Smaller still: you're standing on the chip.\nThe circuits are really on its underside, facing down into the pads, so this floor shows them as if the silicon were see-through.",
              "markers": [
                  {"id": "i_core", "type": "info", "yaw": c2y, "pitch": c2p, "label": "A core", "title": "8 cores",
                   "text": "Each core is a complete processor: it fetches an instruction, decodes it and carries it out. With 8 cores the CPU can run 8 jobs at the same time."},
                  {"id": "i_l3", "type": "info", "yaw": l3y, "pitch": l3p, "label": "Cache", "title": "Cache: memory on the chip",
                   "text": "The regular blue grids are cache: very fast memory right next to the cores. The big band in the middle (L3) is shared by all 8. Each core also has its own smaller, even faster caches (L1 and L2)."},
                  {"id": "i_mc", "type": "info", "yaw": mcy, "pitch": mcp, "label": "Memory controller", "title": "The memory controller",
                   "text": "This part talks to the RAM you fitted, on two channels (A and B). That's why one stick in each channel was faster."},
                  {"id": "i_io", "type": "info", "yaw": ioy, "pitch": iop, "label": "PCIe + I/O", "title": "PCIe and input/output",
                   "text": "The connections to the rest of the PC: the graphics card and the SSD talk to the CPU through PCIe lanes from here."},
                  {"id": "q_chip1", "type": "question", "set": "The chip", "yaw": c6y, "pitch": max(c6p, -20), "label": "The chip", "retry": True,
                   "text": "Why keep cache on the chip when the RAM is just next door?",
                   "options": [{"text": "Fetching from the RAM takes far longer than from the cache", "correct": True, "feedback": "Yes: getting data from the RAM can take a hundred times longer, so the CPU keeps what it's using right next to the cores."},
                               {"text": "The cache holds more than the RAM", "correct": False, "feedback": "No: the cache is tiny (tens of MB) next to the RAM (32 GB). It's about speed."},
                               {"text": "The RAM is only for the graphics card", "correct": False, "feedback": "No: the RAM is the CPU's working memory."}]},
                  {"id": "q_chip2", "type": "question", "set": "The chip", "yaw": c6y, "pitch": max(c6p, -20), "label": "The chip", "retry": True,
                   "text": "8 cores means the CPU...",
                   "options": [{"text": "can work on 8 jobs at the same time", "correct": True, "feedback": "Yes. A program only goes faster if its work can be split up between the cores."},
                               {"text": "is 8 times faster at everything", "correct": False, "feedback": "Only if the work can be split into 8. Many jobs can't."},
                               {"text": "has 8 times as much memory", "correct": False, "feedback": "No: cores do the work; memory is the cache and the RAM."}]},
                  back("g_die_back", "B1")]})
    # ---- the finished PC running, the chip as an X-ray: which core we're about to go into
    c4y, c4p = board_point("T_run", 92 - 10 + 20 * 0.74, 100 - (-6 + 12 * 0.82), 4.8)       # core 4 on the chip map
    R.append({"id": "T_run", "name": "The chip at work", "lib": lib("T_run"), "view": "centre", "dims": DIMS, "cardWall": "left", "end": False, "endText": "",
              "ambient": "fan", "hideBag": True,
              "intro": "The finished PC, switched on, seen as an X-ray: no lid, no cooler. The RAM you fitted is off to the right.\nEach of the 8 cores is running programs right now. Go inside core 4 to see how.",
              "markers": [
                  {"id": "g_core", "type": "go", "yaw": c4y, "pitch": c4p + 4, "label": "Go inside core 4", "target": "T_core", "requires": [], "code": ""},
                  back("g_run_back", "B_on")]})
    # ---- inside a core: the fetch-decode-execute cycle, one step per tap (engine_patch_2026-11-04d.py draws it live)
    R.append({"id": "T_core", "name": "Inside a core", "lib": lib("T_core"), "view": "centre", "dims": DIMS, "cardWall": "back", "end": False, "endText": "",
              "ambient": "fan", "hideBag": True, "sim": core_sim(),
              "intro": "You're inside core 4. In front of you: its registers (tiny, very fast stores), the control unit and the ALU. On the right: the RAM.\nTap \"Next step\" (on the left) to run a 3-line program.",
              "markers": [
                  {"id": "s_next", "type": "info", "sim": "next", "yaw": -100, "pitch": -15, "label": "Next step"},
                  {"id": "s_auto", "type": "info", "sim": "auto", "yaw": -124, "pitch": -15, "label": "Play it all"},
                  {"id": "s_reset", "type": "info", "sim": "reset", "yaw": -76, "pitch": -15, "label": "Start again"},
                  {"id": "q_cycle", "type": "question", "yaw": 150, "pitch": 3, "label": "Question", "retry": True,
                   "text": "This CPU runs at 3.6 GHz. Roughly how often does each core go round the fetch-decode-execute cycle?",
                   "options": [{"text": "Billions of times a second", "correct": True, "feedback": "Yes: roughly one instruction per clock tick (modern cores manage several), 3.6 billion ticks a second, on each of the 8 cores."},
                               {"text": "Thousands of times a second", "correct": False, "feedback": "Far more: giga = billion."},
                               {"text": "Once a second", "correct": False, "feedback": "Much, much faster than that."}]},
                  back("g_core_back", "B_on", 180)]})
    # ---- the empty RAM slots: which two? The slots are named in the scene (A1..B2, a diagonal from the nearest slot to the
    # furthest) and the board's manual gives the rule; the question opens once the manual has been read.
    sy, sp = part_point("T_ramq", "dimm_slot_b2", 7)
    SLOT_AT = {"a1": (156, 149), "a2": (165, 107), "b1": (180, 77), "b2": (189, 56)}     # board x, y along each slot
    slot_marks = []
    for sl_, (bx_, by_) in SLOT_AT.items():
        yy, pp = board_point("T_ramq", bx_, by_, 7)
        ch, n = sl_[0].upper(), sl_[1]
        slot_marks.append({"id": "i_slot_" + sl_, "type": "info", "yaw": yy, "pitch": pp + 3, "label": sl_.upper(), "title": f"Slot DIMM_{ch}{n}",
                           "text": f"Channel {ch}, slot {n}. (The label is printed on the board at the end of the slot.)"})
    R.append({"id": "T_ramq", "name": "The RAM slots", "lib": lib("T_ramq"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "Four empty slots, clips open. You have two sticks.\nCheck the board's manual before you choose.",
              "markers": slot_marks + [
                  {"id": "i_manual", "type": "info", "yaw": 45, "pitch": 2, "label": "The manual", "title": "From the motherboard's manual",
                   "text": "Four memory slots in two channels: A1 and A2 are channel A, B1 and B2 are channel B.\nThe CPU's memory controller uses both channels at the same time. So with two sticks, put one in each channel (dual channel): about twice as fast as both on one channel."},
                  {"id": "q_slots", "type": "question", "set": "Which slots?", "after": "opened:i_manual", "yaw": 20, "pitch": 2, "label": "Which slots?", "retry": True,
                   "text": "Where do your two sticks go?",
                   "options": [{"text": "A1 and A2", "correct": False, "feedback": "Both on channel A: the CPU could only use one channel. Try again."},
                               {"text": "A2 and B2", "correct": True, "go": "T_ram",
                                "feedback": "Yes: one in each channel (dual channel), and slot 2 of each is the pair the manual recommends. Pushing them in now..."},
                               {"text": "B1 and B2", "correct": False, "feedback": "Both on channel B. Try again."}]}]})
    # ---- RAM fitted (one stick not quite home: the planted fault)
    R.append({"id": "T_ram", "name": "RAM fitted", "lib": lib("T_ram"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "intro": "Both sticks are in slots A2 and B2. Each one should be pushed down until both of its clips snap shut.",
              "markers": [
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
    # ---- switched on: the loose stick
    fy, fp = part_point("F_ram", "dimm_slot_b2", 7)
    R.append({"id": "F_ram", "name": "The RAM", "lib": lib("F_ram"), "view": "centre", "dims": DIMS, "cardWall": "right", "end": False, "endText": "",
              "ambient": "fan", "props": props("F_ram"), "intro": "Look closely at both sticks and their clips.",
              "markers": [
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
    # held up to look at: the RAM stick lies long ways with its label to you (needs engine_patch_2026-11-04.py)
    HOLD = {"i_ram": {"upright": True}}
    items = [dict({"id": i, "name": n, "model": m, "description": "", "pages": p}, **HOLD.get(i, {})) for i, n, m, p in ITEMS]
    tour = {"version": 1, "id": TOUR_ID, "name": "TinyPC - build a PC (open day)", "start": "B0",
            "description": "Collect the parts, build the PC in order, shrink inside to see them fitted, then switch on, find the fault and fix it.",
            "items": items, "rooms": bench_rooms() + tiny_rooms()}
    os.makedirs(os.path.join(ROOT, "tours"), exist_ok=True)
    out = os.path.join(ROOT, "tours", TOUR_ID + ".json")
    with open(out, "w", encoding="utf-8") as fh: json.dump(tour, fh, indent=1)
    shutil.copy2(out, os.path.join(RB, "tours", TOUR_ID + ".json"))
    print("wrote", out, "and copied it to", os.path.join(RB, "tours"), "|", len(tour["rooms"]), "rooms")
