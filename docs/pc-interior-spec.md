# Tiny Inside a PC – Igloo scenario (spec v0.4, 3 Nov 2026)

**Claude: read `igloo-room-playbook.md` first, then `errors-log.md`, then this.**

## What it is
Students are shrunk to a few millimetres tall and stand **on the motherboard inside a desktop PC**, in the Igloo room. The board is the floor; the parts tower round them as the walls. They move between several stops (each a Tour Builder room), find out what each part does, answer questions, and maybe trace a fault. An optional normal-size **workbench** room is where parts are picked up and turned.

Built with the same tools as the Glenda scenario: **Room Builder** (Cycles equirect renders) + **Tour Builder** (markers, cards, question stacks, pointer, tablets).

## Where things live
- **Engine (shared):** `D:\Projects\01_Active\RoomBuilder` – GitHub `jamiehomewood/SpoutyRoomBuilder`. Code only. Engine changes go there and must not break the Glenda tours.
- **This project's local folder (source of truth):** `D:\Projects\01_Active\TinyPC`. (There is also a git clone in `C:\Users\<you>\TinyPC`: not the source of truth.)
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

## Built so far (3 Nov 2026): pilot, stops 1–3, no engine changes
Each stop is an ordinary Room Builder **outdoor** spec (no room box, no lights of its own, a shadow-catcher ground at z = 0). Everything else is a model at the stop's scale:
- `tools/board_layout.py` – **the source of truth for the layout**: every part's position on the board (real mm), the stops (stand point, scale, facing, what's left out) and the clear-zone check (`python tools/board_layout.py`). The board is our own design, 330 × 325 mm (a bit bigger than ATX, so each stop has an open patch round it).
- `tools/make_board_texture.py` – draws the board surface at 8192 px (~25 px/mm): solder mask with glass weave, traces under the mask (memory/PCIe buses plus routed fill), copper pours, gold pads, vias, holes, silkscreen labels (DIMM_A1, CPU1, ATX_PWR1…; no brands), and picks ~1,200 surface-mount parts (`tools/smd_parts.json`). Run in normal Python (Pillow, numpy).
- `tools/make_label_textures.py` – capacitor tops, CR2032, SSD label, RAM sticker (generic wording).
- `tools/make_pc_models.py` – Blender, builds 21 own models into `models/tpc_*/` (glb, thumb, model.json with `bbox_mm`): board (with the SMD parts and LEDs, some lit), CPU in socket with paste, tower cooler, DDR5 stick with RGB bar, DIMM slot (shut/open clips), VRM heatsinks, polymer caps, 24-pin and 8-pin plugs with cables, rear I/O, PCIe x16/x1, compact GPU, chipset heatsink, CMOS battery, SATA, M.2 SSD, and the case interior (tray, panels, RGB fans, PSU shroud, a daylight panel high above the open side, out of the projected area).
- `tools/make_stop_specs.py` – writes `specs/<stop>.json` from the layout and the models' bounds. The case tray sits just above z = 0 (nothing may go below the shadow catcher); the camera is 1.12 m above what you stand on.
- `tools/sync-to-roombuilder.bat` / `collect-from-roombuilder.bat` – copy models/library/tours across (copy only; collect skips room.blend and the PNG views).
- World: `lighting: night` with no HDRI (near-black), so the light is the daylight panel, the RGB on the RAM and fans and the board LEDs.

| Stop | Stand point (board mm) | Scale | Facing (Front wall) | Nearest tall part |
|---|---|---|---|---|
| 1 Arrival | (258, 180), front half of the board | ×35 | 90 = towards the 24-pin / front edge | 24-pin, GPU end, DIMM ends at 2.2–2.35 m |
| 2 CPU (cooler off) | on the CPU lid (92, 100), lid 5.3 mm up | ×50 | 90 = towards the RAM | caps beside the VRM heatsinks at 2.1 m (0.26 m tall) |
| 3 RAM | (268, 48), front of the RAM bank | ×35 | 270 = the RAM bank | 24-pin caps 2.5 m, RAM 2.64 m |

Nothing taller than 5 cm inside 2 m at any stop. Close calls (2–2.5 m): stop 1's 24-pin (0.7 m tall), GPU end and DIMM ends; stop 2's low capacitors.

### What the room can show: the cut-off line
The walls are projected only up to 2.244 m, about **20° above eye level** (a bit more in the corners); everything above is on the black ceiling. A part at the wall (about 3 m) is shown whole only if its real height is under about 45 mm at ×50, 64 mm at ×35, 90 mm at ×25, 150 mm at ×15. So the cooler (158), GPU (112), 120 mm fans and the case (215) always run off the top at a "tiny" scale: build each close-up stop's walls from parts under ~60 mm (RAM, VRM heatsinks, connectors, caps, slots) and let tall parts run off on purpose. `python tools/board_layout.py` reports how much of each tall part shows; `python tools/check_render.py <view.jpg>` draws the line (red) and the floor line (orange) on a render. **Run both on every draft.**

### Two sets, kept side by side (3 Nov 2026)
- **Set 1 (`specs/*.json`, library "TinyPC - …")**: the first pass. 120 mm case fans at real height (mostly above the line), 24-pin cable rising out of view.
- **Set 2 (`specs/v2/*.json`, library "TinyPC v2 - …")**: case `tpc_case_shell_v2` (92 mm fans mounted low so their rings land on the walls; case wider at the front; a dimmer second daylight panel on the front side as fill), 24-pin `tpc_atx24_v2` (cable arches over and drops through a grommet in the case floor beside the board, so it stays below the line). Stops 1–3 at the same points as set 1. `python tools/make_stop_specs.py <quality> v2`.
- **Overview stop (tried, not working yet)**: on top of the PSU shroud the board is hidden in a pit below the shroud's edge; on the case floor in front of the board (×22) the cooler, RAM and GPU all fit below the line, but the board itself shrinks to a thin strip near the horizon (a flat surface 17 cm above your feet at that scale), and the dropped 24-pin cable stands 1.6 m away. Probably better: give the big picture in the normal-size **workbench** room instead, or a "hovering" view.

## Who it's for (Jamie, 3 Nov 2026)
**Applicants at an open day**: an introduction to computer architecture. They work out and build a PC, then start it: fans come on, the board lights up; an alarm (beep code, debug LED) if something is wrong.

## Workbench room (built 3 Nov 2026, `specs/workbench/tpc_workbench.json`, library "TinyPC - Workbench")
A normal-size college IT workshop at the Peterborough size (Room Builder "hospital" style for the panel lights and corridor; pale grey walls, blue-grey vinyl, window with the Cambridge college view, door to a corridor).
- **Front:** `tpc_workbench` (2 m bench, anti-static mat with earth lead, pegboard, shelf, tools, wrist strap, LED bar) in a full-width 0.8 m alcove; on it the PC waiting for its parts (`tpc_pc_tower_empty`: empty socket, empty RAM slots, no cooler/SSD/graphics card/cables), a monitor (off), keyboard and mouse.
- **Right wall:** a second bench with a finished PC switched on (`tpc_pc_tower_on`) and the setup screen on the monitor (`tpc_monitor_on`): "this is what you're building".
- Shelving and boxes either side. Nothing on the projected floor; everything below the cut-off line.
- **Parts to pick up are not in the render**: the tour adds them live (`show3d`) on the bench and students turn them with the tablet touchpad (inspect). Catalogue models ready: `tpc_cpu` (loose, generic etched lid, gold pads under), `tpc_tower_cooler`, `tpc_paste_syringe`, `tpc_dimm`, `tpc_m2_ssd`, `tpc_gpu`, `tpc_atx24_v2`, `tpc_eps8_v2`; also `tpc_cpu_socket_empty` (pins showing, plate and lever up) and `tpc_cpu_socket_clean` (CPU in, clean lid with markings, for the tiny CPU stop if the paste goes).
- The PC on the bench is built from the same board, parts and case as the tiny stops (side panel off, open side to the room), so what students see inside matches.

## Open day, from Jamie (3 Nov 2026)
Groups of 5–10, 20–30 minutes, one student tablet passed round; the facilitator also has a remote. Beeps and fan noise: yes. Spinning fans: yes.

## Switched off / switched on (3 Nov 2026)
- `specs/v2off/` and `specs/v2on/`: set 2's stops 1–3 switched off (RAM RGB, fan rings and board LEDs dark: `tpc_board_off`, `tpc_dimm_off`, `tpc_case_shell_v2_off`) and switched on (lit). Both use the clean CPU lid (`tpc_cpu_socket_clean`): no paste; the lid's generic markings ("TPC-9 PROCESSOR 8 CORES") are big on the floor at the CPU stop.
- **Spinning fans:** the tour spins live rotors (`tpc_fan_rotor_120/92/88`) over the fans in an "on" render. `make_stop_specs.py <q> v2on` writes every candidate to `<stop>.props.all.json`; `check_rotors.py` (Blender, on that render's room.blend) ray-tests each one and keeps the ones you can see in `<stop>.props.json` (the room's `props` in the tour); re-running `make_stop_specs.py` then picks a per-stop case `tpc_case_shell_v2_on_<mask>` with blades left out only where a rotor spins (other fans keep their blades), and the bladeless cooler/GPU only if theirs spin. Kept: arrival 4 (two front, one top, cooler), CPU 1 (rear exhaust), RAM 4.
- Library: "TinyPC v2 off 1–3", "TinyPC v2 on 1–3". Test tour `tpc-test-engine` (also in `tours/`): take RAM → slot refuses until the clips are opened → power without RAM = "No memory!" room with three long beeps → with RAM = "It's alive": one beep, fan hum, spinning fans.

## The open-day tour (built 3 Nov 2026): `tours/tpc-open-day.json`
See `docs/facilitator-notes.md` for the flow, answers and timings.
- **Story:** collect and inspect the parts at the workbench → fit them in order (CPU, RAM, paste, cooler, SSD, graphics card, power cables; wrong order is refused with a reason) → shrink in after the CPU, the RAM (which two slots? A2 + B2) and the power cables → press power: three long beeps (planted fault: the RAM stick in B2 isn't clicked home, its clip open) → the DRAM **debug light** → the loose stick → switch off first → click → power again → one short beep, fans spinning → the setup screen and "Summing up".
- **Debug lights** (CPU / DRAM / VGA / BOOT) by the 24-pin: `board_layout.DEBUG_LEDS`, labels and pads in the board texture, `tpc_board_dbg_<led>` lights one red.
- **Build steps:** `board_layout.BUILD` / `build_state(step, fixed)` decide what's fitted at each step, for both the bench PC (`tpc_pc_tower_s0..s6`, `tpc_pc_tower_fixed_on`) and the rooms inside. The loose stick sits 3.5 mm high (`LOOSE_SEAT`) with its slot's clips open.
- **Rooms:** `tools/make_tour_rooms.py` writes `specs/tour/*.json` (B0–B6, B_on at the workbench; T_cpu, T_ramq, T_ram, T_power, F_dram, F_ram, R_fixed, S_on inside). `tools/build_tour_renders.py drafts` builds the models, renders drafts to `_work/tour/`, ray-tests the fan rotors and makes the per-room cases; `… library` queues the full renders ("TinyPC tour - …"). `tools/make_tour.py` writes the tour from them (hotspots placed from the layout) and copies it into RoomBuilder/tours.
- Player patch b (`tools/engine_patch_2026-11-03b.py`): the padlock counts flags; question `after` takes `flag:<id>`.
- Player patch 4 Nov (`tools/engine_patch_2026-11-04.py`): items can be held `upright` (the RAM stick) or turned (`holdTurn`); patch 4b: `room.hideBag` (no backpack strip on the chip's floor); patch 4c: `room.anim` + `play` hotspots (a floor animation; its first use, the fetch-decode-execute dot in T_run, was dropped on 4 Nov); patch 4d: `room.sim` step-through diagrams, used by T_core "Inside a core" (register-level fetch-decode-execute of LOAD/ADD/STORE, reached from T_run).

## What the Tour Builder can and can't do (checked 3 Nov 2026)
- Can: item take/inspect/show3d with the touchpad, use (right/wrong outcomes), questions, codes, go between rooms with a fade.
- Added 3 Nov (Jamie's go-ahead): flags, install order (`requires`/`notYet`), fault routing (`lockedGo`), beep codes, fan hum, spinning room props. See the playbook, section 3.

## Engine work (RoomBuilder repo) – not needed for the pilot; maybe later
1. **Scene mode "tiny"** – only if outdoor mode runs out (e.g. to drop the shadow catcher so things can sit below z = 0): the ground is the PCB texture instead of a shadow catcher, no room box, models placed by mm with a per-scene scale, and a backdrop scene instead of an HDRI. Check first what outdoor mode already does.
2. **Clear-zone check** in the builder (TinyPC has its own in `board_layout.py`).
3. Library entries for each stop so the Tour Builder can use them as rooms.

## Open decisions (ask Jamie)
*(3 Nov: Jamie said "gogogo" to the defaults: pilot = stops 1–3, explore only, Peterborough room size.)*
1. ~~Who it's for~~: open-day applicants, intro to computer architecture (build it, start it). Learning outcomes still to agree.
2. Which stops to build first (suggest 1, 2, 3 as a pilot).
3. Explore only, or the won't-boot fault thread?
4. Workbench room: yes/no.
5. Is the room at work the same size as Peterborough? If not, renders are rebuilt at that size.
6. ~~Repo~~ decided 3 Nov 2026: `TinyPC`, public. CC-BY credits must go with anything published; no BlenderKit or logos.

## Checks before delivering a render
Playbook list, plus: the clear patch round the centre is flat board only; tall parts land on the walls (check in spoutyPreview); parts sit on the board (no floating, no sinking); detail holds up in close-ups; no logos; labels readable from the centre.
