# TinyPC – build a PC (open day): facilitator notes

**Tour:** `tpc-open-day` (Tour Builder list: "TinyPC - build a PC (open day)"). **Who:** open-day applicants, groups of 5–10, 20–30 minutes, one student tablet passed round; you have the facilitator remote.
**What they learn:** the main parts of a computer and what each does (CPU, RAM, storage, GPU, cooling, power), why they go in in a certain order, and how a PC checks itself at switch-on (POST, beep codes, debug lights).

## Running it
- Room PC: Room Builder's library rooms ("TinyPC tour - …") and `tours/tpc-open-day.json` must be on the room PC (`tools/sync-to-roombuilder.bat`), with the 3 Nov tour-player update (`tools/engine_patch_2026-11-03.py` and `…03b.py`, run once against that RoomBuilder folder).
- In ICE: a web layer, 360 / equirectangular, **2:1** size (Dynamic Resolution off): the tour from the scene server (`/rbtour.html?tour=tpc-open-day`), or pick it on the tablet under "Tours".
- Sound (beeps, fan hum) comes from the web layer; it starts after the first tap or key press.
- Student tablet: `play.html` (tap hotspots, answer, turn held parts with the pad). Facilitator: `control.html` (Black screen, Point, Restart, Change, and every answer button).
- Room PC keys: 1–9 answer, Enter continue/close, Esc close, Backspace back.

## The flow (about 25 minutes)
| Time | Where | What happens | Answer / tip |
|---|---|---|---|
| 0–8 | **Workbench** | Pick up each part on the bench (it goes in the bag). Turn it with the pad; the card says what it does. "A finished PC" on the right-hand bench shows the goal. | Let each student take one part and explain it to the group. |
| 8–10 | Bench → **The PC** | Give the PC the CPU. Wrong part = "Not yet" with a reason. | Order: CPU, RAM, paste, cooler, SSD, graphics card, power cables. |
| 10–12 | **On the CPU** (tiny) | Standing on the CPU lid. Question: 3.6 GHz = ? | 3.6 billion ticks a second. |
| 12–14 | **RAM slots** (tiny) | Which two slots? | **A2 and B2** (one per channel = dual channel). |
| | **RAM fitted** (tiny) | "Have a good look at the clips…" | The planted fault: the stick in **B2 isn't fully in** (its clip is open; you can see its gold contacts). Don't give it away! |
| 14–15 | Bench → **Thermal paste** (tiny) | Paste (cooler before paste = refused). Once the paste room is rendered: tiny on the CPU lid beside the pea of paste, question **how much paste?** (Until then the question appears on the bench by the PC.) | A pea-sized dot. |
| 15–16 | **The cooler** (tiny) | Behind the RAM, looking at the cooler tower and its fan. Question: where does the heat end up? | In the air, blown out of the case. The loose B2 stick is in the foreground: a second chance to spot it. Still don't give it away. |
| 16–17 | Bench | SSD. A question appears by the PC: **why before the graphics card?** | The card covers the SSD's slot. (Trying the card first is refused for the same reason.) |
| 17–18 | **The graphics card** (tiny) | The card stands like a wall; the SSD is hidden under it. Question: why thousands of small cores? | Millions of pixels worked out at the same time (in parallel). |
| 18 | Bench | Power cables. The power button can be pressed at any time: before the cables are in, nothing happens. | |
| 18–19 | **Power in** (tiny) | The 24-pin, and the four **debug lights** (CPU, DRAM, VGA, BOOT). | Point the lights out: they'll matter in a minute. |
| 19 | Bench → **Power button** | Fans spin… **three long beeps**. | |
| 20 | **Something's wrong** (tiny) | Fans spinning, the **DRAM** light on. | DRAM = the memory. |
| 21–23 | **The RAM** (tiny, running) | What's wrong? → Before pushing it in? | The B2 stick isn't home → **switch off and unplug first**. |
| | **Click!** → bench → power | You hear the clips snap shut. | |
| 24 | **It's alive!** (tiny) | One short beep, fans spinning, no debug light. | POST = power-on self-test. |
| 25 | **It works!** (bench) | Setup screen on the monitor; "Summing up": 3 questions, then the score. | RAM forgets at power-off; three long beeps = memory; paste fills the air gaps. |

## Also in the tour (4 Nov)
- **The monitor**: tap it on the bench (or "What's on the screen?" when tiny and switched on) to hold it up: black while off, still black during the fault (the PC stops before the graphics), the setup screen once it starts.
- **Slot labels**: A1, A2, B1, B2 are written over the RAM slots in the RAM rooms.
- **The power button** never shows a padlock: nothing (no cables), three long beeps (loose RAM), or it starts (fixed).
- The RAM rooms, the cooler and the graphics card are seen from a little higher up (once re-rendered).
- Needs the 4 Nov click patch for the clip sound (`tools/engine_patch_2026-11-04.py`, after the two 3 Nov patches); without it the tour is just quiet there.

## If something goes wrong
- No sound: tap the screen or press a key once (browsers only start sound after a touch).
- A room is black or a card won't go: the facilitator remote's Restart starts the tour again (from the workbench).
- Parts on the bench are small: tap the ring hotspot; the part is then held up big in front of the left wall.
