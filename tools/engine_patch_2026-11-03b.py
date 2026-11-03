"""
Second small Room Builder tour-player patch for TinyPC (3 Nov 2026), after engine_patch_2026-11-03.py:
- the padlock on a go marker counts flags as well as items (the power button stops looking locked once the cables are in)
- question conditions ("after") understand "flag:<id>"

    python engine_patch_2026-11-03b.py <RoomBuilder folder> [--check]

Backs up builder/tour.html to _backup_2026-11-03b_tinypc/ first; refuses unless each old piece occurs exactly once.
"""
import os, shutil, sys

RB = sys.argv[1] if len(sys.argv) > 1 else r"D:\Projects\01_Active\RoomBuilder"
P = os.path.join(RB, "builder", "tour.html")
EDITS = [
    ("""  const locked = (m) => m.type === 'go' && (((m.requires || []).some((i) => !S.items.has(i))) || (m.code && !S.unlocked.has(m.id)));""",
     """  const locked = (m) => m.type === 'go' && (((m.requires || []).some((i) => !S.items.has(i) && !(S.flags && S.flags.has(i)))) || (m.code && !S.unlocked.has(m.id)));"""),
    ("""    if (k === 'have') return S.got.has(v);""",
     """    if (k === 'have') return S.got.has(v);
    if (k === 'flag') return S.flags.has(v);"""),
]
src = open(P, encoding="utf-8").read()
for old, new in EDITS:
    n = src.count(old)
    if n != 1: raise SystemExit(f"expected 1 match, found {n}: {old[:120]}")
    src = src.replace(old, new)
if "--check" in sys.argv: print("all edits match once"); raise SystemExit(0)
back = os.path.join(RB, "_backup_2026-11-03b_tinypc"); os.makedirs(back, exist_ok=True)
if not os.path.exists(os.path.join(back, "tour.html")): shutil.copy2(P, os.path.join(back, "tour.html"))
open(P, "w", encoding="utf-8", newline="").write(src)
print("patched; original in", back)
