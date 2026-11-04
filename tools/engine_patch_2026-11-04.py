"""
Third small Room Builder tour-player patch for TinyPC (4 Nov 2026), after engine_patch_2026-11-03.py and ...03b.py:
- a "click" sound (enterSound / accepts[].sound): the plastic snap of a RAM stick's two clips shutting. "click2" = two
  sticks, one after the other.

    python engine_patch_2026-11-04.py <RoomBuilder folder> [--check]

Backs up builder/tour.html to _backup_2026-11-04_tinypc/ first; refuses unless each old piece occurs exactly once.
Safe to run twice: if the click is already there it says so and changes nothing. Tours that don't use "click" behave
exactly as before (and an older player just stays quiet for "click").
"""
import os, shutil, sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
CHECK = "--check" in sys.argv
RB = args[0] if args else r"D:\Projects\01_Active\RoomBuilder"
P = os.path.join(RB, "builder", "tour.html")

CLICK_FN = """  // a RAM clip snapping shut: two short bursts of filtered noise 60 ms apart (n = how many sticks, half a second apart)
  function clickSnap(n) {
    try {
      const t0 = actx.currentTime + 0.05, sr = actx.sampleRate;
      for (let i = 0; i < n; i++) for (const dt of [0, 0.06]) {
        const buf = actx.createBuffer(1, Math.ceil(sr * 0.03), sr), d = buf.getChannelData(0);
        for (let j = 0; j < d.length; j++) d[j] = (Math.random() * 2 - 1) * Math.exp(-j / (sr * 0.004));
        const s = actx.createBufferSource(); s.buffer = buf;
        const bp = actx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2800; bp.Q.value = 1.2;
        const g = actx.createGain(); g.gain.value = 0.9;
        s.connect(bp).connect(g).connect(actx.destination); s.start(t0 + i * 0.5 + dt);
      }
    } catch (e) {}
  }
"""
EDITS = [
    ("""      if (String(kind).startsWith('post:')) { postBeeps(String(kind).slice(5)); return; }""",
     """      if (kind === 'click' || kind === 'click2') { clickSnap(kind === 'click2' ? 2 : 1); return; }
      if (String(kind).startsWith('post:')) { postBeeps(String(kind).slice(5)); return; }"""),
    ("""  // PC-speaker beep codes: S = short, L = long, space = pause ("S" = all fine, "LSS", "SSS SSS")""",
     CLICK_FN + """  // PC-speaker beep codes: S = short, L = long, space = pause ("S" = all fine, "LSS", "SSS SSS")"""),
]

if not os.path.exists(P): raise SystemExit(f"Not found: {P}")
src = open(P, encoding="utf-8").read()
if "function clickSnap(" in src:
    print("Already patched (the click is there): nothing to do."); sys.exit(0)
if "postBeeps(" not in src:
    raise SystemExit("This tour.html hasn't had engine_patch_2026-11-03.py yet: run that (and ...03b.py) first.")
for old, new in EDITS:
    n = src.count(old)
    if n != 1: raise SystemExit(f"expected 1 match, found {n}: {old[:120]}")
    src = src.replace(old, new)
if CHECK:
    print("Check only: the patch would apply cleanly. Nothing changed."); sys.exit(0)
back = os.path.join(RB, "_backup_2026-11-04_tinypc"); os.makedirs(back, exist_ok=True)
shutil.copy2(P, os.path.join(back, "tour.html"))
open(P, "w", encoding="utf-8").write(src)
print("Patched", P, "(backup in", back + ")")
