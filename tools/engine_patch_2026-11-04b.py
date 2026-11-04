"""
Second Room Builder tour-player patch for TinyPC (4 Nov 2026), after engine_patch_2026-11-04.py:
- a room can hide the backpack strip on the floor ("hideBag": true), for rooms where the floor itself is the content
  (TinyPC's X-ray chip). Rooms without it are unchanged.

    python engine_patch_2026-11-04b.py <RoomBuilder folder> [--check]

Backs up builder/tour.html to _backup_2026-11-04b_tinypc/ first; refuses unless the old piece occurs exactly once.
"""
import os, shutil, sys

RB = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"D:\Projects\01_Active\RoomBuilder"
P = os.path.join(RB, "builder", "tour.html")
EDITS = [
    ("""    if (r && S.items.size && t3.setFloorText) {
      const home = WALLS[r.cardWall] ?? 0, half = wallDist(r, home);""",
     """    if (r && S.items.size && !r.hideBag && t3.setFloorText) {          // hideBag: a room whose floor is the content
      const home = WALLS[r.cardWall] ?? 0, half = wallDist(r, home);"""),
]
src = open(P, encoding="utf-8").read()
for old, new in EDITS:
    n = src.count(old)
    if n != 1: raise SystemExit(f"expected 1 match, found {n}: {old[:100]}")
    src = src.replace(old, new)
if "--check" in sys.argv: print("all edits match once"); raise SystemExit(0)
back = os.path.join(RB, "_backup_2026-11-04b_tinypc"); os.makedirs(back, exist_ok=True)
if not os.path.exists(os.path.join(back, "tour.html")): shutil.copy2(P, os.path.join(back, "tour.html"))
open(P, "w", encoding="utf-8", newline="").write(src)
print("patched tour.html; original in", back)
