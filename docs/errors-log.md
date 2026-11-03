# Errors log – PC Interior scenario

**Read this (after `igloo-room-playbook.md`) before doing anything in this project. When a new mistake happens, add it here straight away.** Generic Igloo/tool mistakes go in the playbook's own log instead.

## Before starting – quick checklist
- [ ] Is the PC folder reachable in this session? If not, say so in the first reply.
- [ ] List the project folder and `RoomBuilder` newest first: build on what's there.
- [ ] Engine changes go in the RoomBuilder repo and must not break the Glenda tours.
- [ ] Change only what Jamie named; ask if a request could mean two things.
- [ ] Nothing on the projected floor; ceiling not projected; build at 6.40 × 5.71 × 2.244 m.
- [ ] No real logos or brand names on parts.
- [ ] No commits or pushes unless Jamie asks.

## Errors
| Date | What went wrong | Rule from now on |
|---|---|---|
| 3 Nov 2026 | The RAM sticker printed mirrored on the first model build (UVs ran the wrong way on the side seen) | Check text on every label in the thumbnails; text faces map u along the viewer's right |
| 3 Nov 2026 | First CPU-stop draft: the shiny CPU lid mirrored the daylight panel and turned the whole floor white; the paste looked like cobbles at ×50; the daylight panel showed at the top of the projected walls | Floors you stand on must be fairly rough; check the floor and the top band of every draft; keep emissive "window" panels above ~30° elevation |
| 3 Nov 2026 | Set 1: two-thirds of each case fan, and most of the cooler at the RAM stop, were above the top of the projected walls (~20° above eye level); I'd only checked the clear zone round the centre, not what lands above the walls | Check every draft with `tools/check_render.py` and the "shows %" column of `board_layout.py`; a stop's main wall content must sit below the line |
| 3 Nov 2026 | Overview stop on the PSU shroud: the board was hidden below the shroud's edge, 1.8 m down; then on the case floor the board shrank to a thin strip, and the clear-zone check missed the 24-pin cable dropping 1.6 m away (the layout's box only covered the connector) | Draft a new viewpoint before building on it; give cables and overhangs their own boxes in the check (`extra` in SETS) |
| 3 Nov 2026 | The spec writer looked up seat heights by exact model name, so the "_on"/"_off" variants sat at 0: the cooler 5.3 mm low, RAM 1.2 mm, graphics card 2 mm, in the set-2 on/off renders | Variants share the base model's placement (`make_stop_specs.seat_of`); check part heights in a close-up when adding variants |
| | | |
