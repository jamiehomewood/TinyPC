# TinyPC – build a PC (open day): facilitator notes

**Tour:** `tpc-open-day` (Tour Builder list: "TinyPC - build a PC (open day)"). **Who:** open-day applicants, groups of 5–10, 20–30 minutes (about 28 with everything; skip "Under the lid" to save 3), one student tablet passed round; you have the facilitator remote.
**What they learn:** the main parts of a computer and what each does (CPU, RAM, storage, GPU, cooling, power), why they go in in a certain order, and how a PC checks itself at switch-on (POST, beep codes, debug lights).

## Running it
- Room PC: Room Builder's library rooms ("TinyPC tour - …") and `tours/tpc-open-day.json` must be on the room PC (`tools/sync-to-roombuilder.bat`), with the tour-player updates (`tools/engine_patch_2026-11-03.py`, `…03b.py`, `…04.py`, `…04b.py`, `…04c.py` and `…04d.py`, each run once against that RoomBuilder folder).
- In ICE: a web layer, 360 / equirectangular, **2:1** size (Dynamic Resolution off): the tour from the scene server (`/rbtour.html?tour=tpc-open-day`), or pick it on the tablet under "Tours".
- Sound (beeps, fan hum) comes from the web layer; it starts after the first tap or key press.
- Student tablet: `play.html` (tap hotspots, answer, turn held parts with the pad). Facilitator: `control.html` (Black screen, Point, Restart, Change, and every answer button).
- Room PC keys: 1–9 answer, Enter continue/close, Esc close, Backspace back.

## The flow (about 25 minutes)
| Time | Where | What happens | Answer / tip |
|---|---|---|---|
| 0–8 | **Workbench** | Pick up each part on the bench (it goes in the bag). Turn it with the pad; the card says what it does. "A finished PC" on the right-hand bench shows the goal. | Let each student take one part and explain it to the group. |
| 8–10 | Bench → **The PC** | Give the PC the CPU. Wrong part = "Not yet" with a reason. | Order: CPU, RAM, paste, cooler, SSD, graphics card, power cables. |
| 10–11 | **On the CPU** (tiny) | Standing on the CPU lid. Question: 3.6 GHz = ? Then "Look under the lid". | 3.6 billion ticks a second. |
| 11–12 | **Under the lid** (tiny) | "Imagine you could peel the lid back" (in real life it usually breaks the CPU). The chip, its solder, the inside of the lid, the CPU's own little circuit board. | The chip is 20 × 12 mm with billions of transistors. |
| 12–14 | **On the chip** (X-ray) | Standing on the silicon: 8 cores ahead, the shared cache underfoot, the memory controller to the right (towards the RAM), PCIe behind. Two questions. Then back to full size. | Cache: the RAM is far slower to reach. 8 cores: 8 jobs at once (only faster if the work can be split). The circuits are really on the chip's underside: the floor is an X-ray view. |
| 14–15 | **RAM slots** (tiny) | The slots are labelled A1, A2, B1, B2 in the scene. Open **The manual** (two channels; one stick in each); then "Which slots?" unlocks. | **A2 and B2** (one per channel = dual channel). Get a student to read the manual card out. |
| | **RAM fitted** (tiny) | "Have a good look at the clips…" | The planted fault: the stick in **B2 isn't fully in** (its clip is open; you can see its gold contacts). Don't give it away! |
| 16–17 | Bench | Paste (cooler before paste = refused). A question appears by the PC: **how much paste?** | A pea-sized dot. |
| 17–18 | **The cooler** (tiny) | Behind the RAM, looking at the cooler tower and its fan. Question: where does the heat end up? | In the air, blown out of the case. The loose B2 stick is in the foreground: a second chance to spot it. Still don't give it away. |
| 18–19 | Bench | SSD. A question appears by the PC: **why before the graphics card?** | The card covers the SSD's slot. (Trying the card first is refused for the same reason.) |
| 19–20 | **The graphics card** (tiny) | The card stands like a wall; the SSD is hidden under it. Question: why thousands of small cores? | Millions of pixels worked out at the same time (in parallel). |
| 20 | Bench | Power cables. Pressing power before the cables: nothing happens. | |
| 20–21 | **Power in** (tiny) | The 24-pin, and the four **debug lights** (CPU, DRAM, VGA, BOOT). | Point the lights out: they'll matter in a minute. |
| 21 | Bench → **Power button** | Fans spin… **three long beeps**. | |
| 22 | **Something's wrong** (tiny) | Fans spinning, the **DRAM** light on. | DRAM = the memory. |
| 23–25 | **The RAM** (tiny, running) | What's wrong? → Before pushing it in? | The B2 stick isn't home → **switch off and unplug first**. |
| | **Click!** → bench → power | | |
| 26 | **It's alive!** (tiny) | One short beep, fans spinning, no debug light. | POST = power-on self-test. |
| 27 | **It works!** (bench) | Setup screen on the monitor; "Summing up": 3 questions, then the score. | RAM forgets at power-off; three long beeps = memory; paste fills the air gaps. |
| 28–29 | **The chip at work** (X-ray, running) | From "It works!": "Watch the CPU work". The finished PC as an X-ray, RAM glowing to the right. Tap **Go inside core 4**. | Optional: skip if time is short. |
| 29–33 | **Inside a core** | Registers in front (PC, MAR, MDR, CIR, control unit, ALU, ACC), the RAM on the right, the explanation panel on the left. **Next step** (under the panel) runs a 3-line program one move at a time: LOAD 200, ADD 201, STORE 202. Values fly between registers; 12 steps; ends with 3 + 4 = 7 stored at 202. **Play it all** runs it by itself (tap again to stop); **Start again**. Question behind you. | Let a student say what will move next before tapping. The first fetch is 3 taps (PC→MAR, RAM→MDR, MDR→CIR + PC goes up); later fetches are one tap. |

## If something goes wrong
- No sound: tap the screen or press a key once (browsers only start sound after a touch).
- A room is black or a card won't go: the facilitator remote's Restart starts the tour again (from the workbench).
- Parts on the bench are small: tap the ring hotspot; the part is then held up big in front of the left wall.
