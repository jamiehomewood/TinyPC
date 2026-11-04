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
| 3 Nov 2026 | Open-day tour: after the RAM, four build steps (paste, cooler, SSD, graphics card) only swapped one workbench render for the next, where the small PC gained one part. In the room it read as a flash with nothing to do (Jamie, first playthrough) | Every step a student takes needs a visible result or a task: a tiny stop, a held-up view or a question. Play the whole tour in the room order before calling it done |
| 3 Nov 2026 | Copying a changed file to the PC from the same staging path a second time silently wrote the first version again, so a re-render used the old stop | Give every copy to the PC a new staging file name, and check the file on the PC (md5 or a search for the change) before running anything from it |
| 3 Nov 2026 | A question's "after" condition was ignored on the switched-on RAM room's "Fix it" question: the player only checks "after" for questions in a set, so it could be answered before the fault was found | Any question with "after" goes in a set (a one-question set is fine) |
| 4 Nov 2026 | First run in the room: the "The PC" hotspot sat over the PC it named and hid the parts going in; the power button showed a padlock, so it looked broken rather than "nothing happens"; the RAM slot labels were never readable from any stop (Jamie) | Hotspots go beside what they name, not on it (check on the render); a control that's always there is never shown locked: give it an outcome for every state; anything a question asks about must be readable in the room |
| | | |
