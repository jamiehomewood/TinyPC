"""
Room Builder tour-player patch for TinyPC (4 Nov 2026): two optional item fields for holding a part up to look at it.

  "upright": true     hold it as it is: don't stand it on end even though it's wide and low (the player treats anything
                      less than 0.35 x as tall as it is wide as flat paper and turns its top to face you). A RAM stick is
                      134 x 44 mm, so it was held long side vertical and spun round its own length.
  "holdTurn": 90      turn it this many degrees about the vertical first (so its long side runs across and its label
                      faces you).

Items without them behave exactly as before (the Glenda tours don't use them).

    python engine_patch_2026-11-04.py <RoomBuilder folder> [--check]

Backs up builder/tour3d.js and builder/tour.html to _backup_2026-11-04_tinypc/ first; refuses unless each old piece occurs
exactly once.
"""
import os, shutil, sys

RB = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"D:\Projects\01_Active\RoomBuilder"
EDITS = {
    "tour3d.js": [
        ("""        const inst = skClone(m.proto); inst.position.y = -m.size.y / 2; mine.size = m.size.clone();""",
         """        const inst = skClone(m.proto); inst.position.y = -m.size.y / 2; mine.size = m.size.clone();
        let held = inst, hs = m.size.clone();                             // o.holdTurn: turned about the vertical first
        if (+o.holdTurn) {
          held = new THREE.Group(); held.rotation.y = +o.holdTurn * D2R; held.add(inst);
          if (Math.abs(Math.sin(+o.holdTurn * D2R)) > 0.7) hs = new THREE.Vector3(m.size.z, m.size.y, m.size.x);
          mine.size = hs.clone();
        }"""),
        ("""        if (m.size.y < 0.35 * Math.max(m.size.x, m.size.z)) {
          const up = new THREE.Group(); up.rotation.x = Math.PI / 2; up.add(inst); mine.spin.add(up);
          mine.size = new THREE.Vector3(m.size.x, m.size.z, m.size.y);  // its size as held""",
         """        if (!o.upright && hs.y < 0.35 * Math.max(hs.x, hs.z)) {          // o.upright: held as it is, never stood on end
          const up = new THREE.Group(); up.rotation.x = Math.PI / 2; up.add(held); mine.spin.add(up);
          mine.size = new THREE.Vector3(hs.x, hs.z, hs.y);  // its size as held"""),
        ("""        } else mine.spin.add(inst);
        mine.raw = m.size.clone();""",
         """        } else mine.spin.add(held);
        mine.raw = m.size.clone();"""),
    ],
    "tour.html": [
        ("""      t3.setInspect({ model: mid, yaw, dist: wallDist(r, yaw) - 0.35, y: -0.3, fit: 0.7, rx: S.rot.rx, ry: S.rot.ry, zoom: S.rot.zoom, from });""",
         """      const hi = itemOf(S.insp) || {};
      t3.setInspect({ model: mid, yaw, dist: wallDist(r, yaw) - 0.35, y: -0.3, fit: 0.7, rx: S.rot.rx, ry: S.rot.ry, zoom: S.rot.zoom, from,
                      upright: !!hi.upright, holdTurn: +hi.holdTurn || 0 });"""),
    ],
}
out = {}
for f, edits in EDITS.items():
    p = os.path.join(RB, "builder", f); src = open(p, encoding="utf-8").read()
    for old, new in edits:
        n = src.count(old)
        if n != 1: raise SystemExit(f"{f}: expected 1 match, found {n}: {old[:100]}")
        src = src.replace(old, new)
    out[f] = src
if "--check" in sys.argv: print("all edits match once"); raise SystemExit(0)
back = os.path.join(RB, "_backup_2026-11-04_tinypc"); os.makedirs(back, exist_ok=True)
for f, src in out.items():
    p = os.path.join(RB, "builder", f)
    if not os.path.exists(os.path.join(back, f)): shutil.copy2(p, os.path.join(back, f))
    open(p, "w", encoding="utf-8", newline="").write(src)
print("patched", ", ".join(out), "; originals in", back)
