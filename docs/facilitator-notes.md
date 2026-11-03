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
| 14–15 | Bench | Paste (cooler before paste = refused). A question appears by the PC: **how much paste?** | A pea-sized dot. |
| 15–16 | **The cooler** (tiny) | Behind the RAM, looking at the cooler tower and its fan. Question: where does the heat end up? | In the air, blown out of the case. The loose B2 stick is in the foreground: a second chance to spot it. Still don't give it away. |
| 16–17 | Bench | SSD. A question appears by the PC: **why before the graphics card?** | The card covers the SSD's slot. (Trying the card first is refused for the same reason.) |
| 17–18 | **The graphics card** (tiny) | The card stands like a wall; the SSD is hidden under it. Question: why thousands of small cores? | Millions of pixels worked out at the same time (in parallel). |
| 18 | Bench | Power cables. Pressing power before the cables: nothing happens. | |
| 18–19 | **Power in** (tiny) | The 24-pin, and the four **debug lights** (CPU, DRAM, VGA, BOOT). | Point the lights out: they'll matter in a minute. |
| 19 | Bench → **Power button** | Fans spin… **three long beeps**. | |
| 20 | **Something's wrong** (tiny) | Fans spinning, the **DRAM** light on. | DRAM = the memory. |
| 21–23 | **The RAM** (tiny, running) | What's wrong? → Before pushing it in? | The B2 stick isn't home → **switch off and unplug first**. |
| | **Click!** → bench → power | | |
| 24 | **It's alive!** (tiny) | One short beep, fans spinning, no debug light. | POST = power-on self-test. |
| 25 | **It works!** (bench) | Setup screen on the monitor; "Summing up": 3 questions, then the score. | RAM forgets at power-off; three long beeps = memory; paste fills the air gaps. |

## If something goes wrong
- No sound: tap the screen or press a key once (browsers only start sound after a touch).
- A room is black or a card won't go: the facilitator remote's Restart starts the tour again (from the workbench).
- Parts on the bench are small: tap the ring hotspot; the part is then held up big in front of the left wall.
