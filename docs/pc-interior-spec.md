# Tiny Inside a PC – Igloo scenario (spec v0.2, 3 Nov 2026)

**Claude: read `igloo-room-playbook.md` first, then `errors-log.md`, then this.**

## What it is
Students are shrunk to a few millimetres tall and stand **on the motherboard inside a desktop PC**, in the Igloo room. The board is the floor; the parts tower round them as the walls. They move between several stops (each a Tour Builder room), find out what each part does, answer questions, and maybe trace a fault. An optional normal-size **workbench** room is where parts are picked up and turned.

Built with the same tools as the Glenda scenario: **Room Builder** (Cycles equirect renders) + **Tour Builder** (markers, cards, question stacks, pointer, tablets).

## Where things live
- **Engine (shared):** `D:\Projects\01_Active\RoomBuilder` – GitHub `jamiehomewood/SpoutyRoomBuilder`. Code only. Engine changes go there and must not break the Glenda tours.
- **This project's local folder (source of truth):** `D:\Projects\01_Active\PC Interior 001` *(confirm the name)*.
- **This project's repo (new, for work):** `jamiehomewood/TinyPC` (created 3 Nov 2026). Unlike the engine repo, it **holds the output**:
  - `specs/` – scene specs (JSON)
  - `tours/` – tour JSON + `audio/`
  - `models/` – part models (GLB) + `credits.md`
  - `renders/library/<id>/` – finished library entries (panorama views, meta, spec.json, proxies.glb); Git LFS for `.jpg/.png/.exr/.glb`
  - `docs/` – this spec, facilitator notes
- **Work PC has Room Builder** (from the engine repo). `sync-to-roombuilder.bat` copies `renders/library` → `RoomBuilder/library`, `tours` → `RoomBuilder/tours`, `models` → the catalogue (check exact folders on the PC first); copy only, never delete. `collect-from-roombuilder.bat` does the reverse on the home PC. Check the work PC's Python/Blender versions before rendering there; viewing tours needs only the server.
- No commits or pushes unless Jamie asks.

## Why tiny works in the room
- The room projects on the **walls and floor**, not the ceiling, from a viewer at the centre (eye ~1.12 m).
- **Floor = the board**: flat (traces, solder pads, silkscreen, vias, flat chips, M.2 drive), so it projects correctly from anywhere. Low things are fine on it (a CMOS battery is a 70 cm disc, 11 cm high).
- **Walls = tall parts** standing roughly where the real walls are. Their tops running out of view above 2.244 m reads naturally: you're tiny.
- **Keep a clear patch round the centre**: about 2 m radius of flat board only (nothing taller than ~5 cm). Tall parts from about 2.5 m out, ideally 2.8–3.5 m, so they land on the real walls. Same idea as outdoor scenes (props 3.3 m+ out).
- Render size is still the physical room's (Peterborough 6.40 × 5.71 × 2.244 m), which sets the camera and floor/wall layout.

## Scale
- Base **×35** (1 mm real = 3.5 cm in the room). Each stop may use its own scale (×25–×50) so its nearest tall parts sit at wall distance; students won't notice small changes between stops.
- At ×35: DIMM stick 31 × 133 mm → **1.1 × 4.7 m slab**; tower cooler 155 mm → **5.4 m** (top out of view); 8 × 10 mm capacitor → **28 × 35 cm barrel**; CPU socket 40 mm → 1.4 m square; M.2 2280 → 0.8 × 2.8 m flat strip; CR2032 → 70 cm disc.

## Stops (one Tour Builder room each)
| # | Stop | Floor around you | Walls | Learning points |
|---|---|---|---|---|
| 1 | **Arrival: board edge by the 24-pin** | Traces, screw hole, silkscreen | 24-pin power connector + cables, rear I/O block, capacitor barrels | Welcome, scale, how to move, power in |
| 2 | **CPU** | Socket area (cooler lifted off in a "maintenance" version, or its base plate) | Cooler fin tower, VRM heatsinks, RAM slabs on one side | CPU, thermal paste, cooling, VRMs |
| 3 | **RAM** | Between DIMM slots (clear lane) | Row of RAM slabs, slot clips, cooler side | Memory, channels, seating |
| 4 | **Storage & chipset** | M.2 SSD flat on the floor (walk on it), chipset heatsink low | PCIe slot edges, SATA ports, GPU side | SSD vs HDD, SATA, chipset |
| 5 | **Beside the GPU** | Board by the PCIe slot | GPU card edge as a long wall, its power connector, fan visible | Graphics, PCIe, power draw |
| 6 | **CMOS battery** | Battery disc on the floor | Nearby headers, capacitors | BIOS/UEFI settings, CMOS reset |
| 7 | **Inside the PSU** *(optional)* | PSU PCB | Big capacitors, transformer, heatsinks, fan | What a PSU does; **never open one: stored charge** |
| W | **Workbench** *(optional, normal size)* | Floor clear | Bench on the Front wall, parts on shelves | Pick up and turn parts (`show3d`), build order |

Stops join with `go` markers ("walk to the RAM"). A simple map on the card wall or tablet shows where you are on the board.

## Interaction
- Parts can't be picked up at this size: **they light up, show cards, ask questions, react** (e.g. a fan spins up, the RAM slot clip snaps shut).
- Picking up / turning parts happens in the workbench room only.
- Question stacks per stop; a "Summing up" stack in an end room.
- Possible fault-finding thread: the PC won't boot; clues across stops (RAM not clicked in, 8-pin CPU power unplugged, flat CMOS battery), fixed with `use` markers, then the board "powers on" (lights, fans spin) in the final stop.
- Facilitator controls as built: Black screen, Point, Restart, Change.

## Look
- Realistic macro photography feel: PCB weave and solder mask, gold pads, solder fillets, printed component labels (generic), brushed aluminium fins, dust in places.
- Dim interior lit by board LEDs and RGB on RAM/fans, plus soft daylight from the side panel far away. Nothing bright straight overhead.
- Far background (beyond the nearest parts): the rest of the case at that scale (very distant) – a rendered case-interior backdrop, not a real photo HDRI.
- **No real logos or brand names** (no Intel/AMD/NVIDIA/Corsair etc.). Generic labels only.
- Close-up detail must hold up: textures and geometry at the real screen size from the centre, checked in close-up test views.

## Models
- Own work first: script the parts in Blender (`tools/make_pc_models.py`, like the `rb_*` ward models): PCB with traces, slots, sockets, capacitors, heatsink fins, RAM, M.2, fans, connectors, cables. Real size in mm; scaled per stop.
- Otherwise Sketchfab **CC0 / CC-BY only** (credits go with the renders), Poly Haven textures. No BlenderKit. Strip any logos.
- Workbench items need catalogue entries (`up_*` or `rb_pc_*`) for `show3d`.

## Engine work likely needed (RoomBuilder repo)
1. **Scene mode "tiny"** (or extend the outdoor mode, which is already HDRI + models on a shadow-catcher ground): the ground is the PCB texture instead of a shadow catcher, no room box, models placed by mm with a per-scene scale, and a backdrop scene instead of an HDRI. Check first what outdoor mode already does.
2. **Clear-zone check**: warn if anything taller than ~5 cm stands within ~2 m of the centre.
3. Library entries for each stop so the Tour Builder can use them as rooms.

## Open decisions (ask Jamie)
1. Who it's for (computing students, staff digital-skills, apprentices?) and the learning outcomes.
2. Which stops to build first (suggest 1, 2, 3 as a pilot).
3. Explore only, or the won't-boot fault thread?
4. Workbench room: yes/no.
5. Is the room at work the same size as Peterborough? If not, renders are rebuilt at that size.
6. ~~Repo~~ decided 3 Nov 2026: `TinyPC`, public. CC-BY credits must go with anything published; no BlenderKit or logos.

## Checks before delivering a render
Playbook list, plus: the clear patch round the centre is flat board only; tall parts land on the walls (check in spoutyPreview); parts sit on the board (no floating, no sinking); detail holds up in close-ups; no logos; labels readable from the centre.
