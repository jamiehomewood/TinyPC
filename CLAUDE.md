# TinyPC

Igloo-room scenario: students shrunk to a few mm tall, standing on a motherboard inside a desktop PC.

Before doing anything, read in this order:
1. `docs/igloo-room-playbook.md`
2. `docs/errors-log.md`
3. `docs/pc-interior-spec.md`

- The engine (Room Builder / Tour Builder) lives in `jamiehomewood/SpoutyRoomBuilder`, not here. This repo holds this scenario's output: specs, tours, models, renders.
- The local PC folder is the source of truth. No commits or pushes unless Jamie asks.
- Large binaries (renders, GLB, audio) use Git LFS (see `.gitattributes`).
- Log new mistakes in `docs/errors-log.md` (scenario) or the playbook's log (generic) straight away.
