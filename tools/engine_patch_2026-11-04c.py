"""
Third Room Builder tour-player patch for TinyPC (4 Nov 2026): a short animation on a room's floor, played when someone
taps a hotspot (TinyPC's fetch-decode-execute cycle on the chip). Opt-in: rooms without "anim" are unchanged.

  room.anim = { color, size, captionYaw, captionDist, steps: [ { caption, dur, path: [[x, y], ...], glow: [[x0, y0, x1, y1], ...],
                                                                color, flash } ] }
      x right, y forward, metres on the floor from the room centre. Each step: its caption on the floor, a glowing dot
      moving along its path over dur seconds, its glow rectangles pulsing. After the last step it fades out.
  marker.play = true on an info hotspot: tapping it plays the room's animation from the start (and shows its card).

    python engine_patch_2026-11-04c.py <RoomBuilder folder> [--check]

Backs up builder/tour3d.js and builder/tour.html to _backup_2026-11-04c_tinypc/ first; refuses unless each old piece
occurs exactly once.
"""
import os, shutil, sys

RB = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"D:\Projects\01_Active\RoomBuilder"
ANIM_JS = r"""  // ---------------------------------------------------------------- a short animation on the floor, played on demand
  //   setAnim({ eye, color, size, captionYaw, captionDist, steps: [{ caption, dur, path: [[x, y]...], glow: [[x0, y0, x1, y1]...],
  //   color, flash }] }, key) or null; x right, y forward (metres on the floor). playAnim() runs it once from the start.
  let anim = null;
  const glowMat = (c) => new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false });
  function setAnim(o, key = '') {
    const k = o ? key + '|' + JSON.stringify(o) : '';
    if (anim && anim.key === k) return;
    if (anim) {
      scene.remove(anim.group);
      anim.group.traverse((c) => { if (c.geometry) c.geometry.dispose(); if (c.material) c.material.dispose(); });
      setFloorText(null, 'anim'); anim = null; dirty = true;
    }
    if (!o || !o.steps || !o.steps.length) return;
    const group = new THREE.Group(), fy = 0.003 - (+o.eye || 1.12), col = new THREE.Color(o.color || '#7ff3ff'), sz = +o.size || 0.09;
    // each glow: a tinted fill and a bright outline (an outline still shows on a pale floor)
    const glows = o.steps.map((s) => (s.glow || []).map(([x0, y0, x1, y1]) => {
      const c = new THREE.Color(s.color || o.color || '#7ff3ff'), w = Math.abs(x1 - x0), h = Math.abs(y1 - y0), cx = (x0 + x1) / 2, cy = -(y0 + y1) / 2, e = 0.09;
      const fill = new THREE.Mesh(new THREE.PlaneGeometry(w, h), glowMat(c)), edge = glowMat(c), parts = [fill];
      for (const [px, pz, pw, ph] of [[cx, cy - h / 2, w + e, e], [cx, cy + h / 2, w + e, e], [cx - w / 2, cy, e, h], [cx + w / 2, cy, e, h]]) {
        const b = new THREE.Mesh(new THREE.PlaneGeometry(pw, ph), edge); b.rotation.x = -Math.PI / 2; b.position.set(px, fy + 0.001, pz); b.renderOrder = 1; group.add(b); parts.push(b);
      }
      fill.rotation.x = -Math.PI / 2; fill.position.set(cx, fy, cy); fill.renderOrder = 1; group.add(fill);
      return { fill, edge, get op() { return fill.material.opacity; }, set op(v) { fill.material.opacity = v; edge.opacity = Math.min(1, v * 3.5); } };
    }));
    const dotGeo = new THREE.SphereGeometry(sz, 20, 14);
    const dot = new THREE.Mesh(dotGeo, new THREE.MeshBasicMaterial({ color: col, toneMapped: false }));
    const halo = new THREE.Mesh(new THREE.SphereGeometry(sz * 2.2, 20, 14), glowMat(col)); halo.material.opacity = 0.3; dot.add(halo);
    dot.visible = false; dot.renderOrder = 3; group.add(dot);
    const trail = [];
    for (let i = 0; i < 8; i++) {
      const t = new THREE.Mesh(dotGeo.clone(), glowMat(col)); t.material.opacity = 0.45 * (1 - i / 8); t.scale.setScalar(0.85 - i * 0.08);
      t.visible = false; t.renderOrder = 2; group.add(t); trail.push(t);
    }
    scene.add(group);
    anim = { key: k, o, group, glows, dot, trail, fy, sz, t: -1, step: -1, hist: [] }; dirty = true;
  }
  function playAnim() { if (anim) { anim.t = 0; anim.step = -1; anim.hist = []; dirty = true; } }
  function pathAt(path, f) {
    if (path.length === 1) return path[0];
    const seg = []; let tot = 0;
    for (let i = 1; i < path.length; i++) { const l = Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]); seg.push(l); tot += l; }
    let d = Math.max(0, Math.min(1, f)) * tot;
    for (let i = 0; i < seg.length; i++) {
      if (d <= seg[i] || i === seg.length - 1) { const u = seg[i] ? Math.min(1, d / seg[i]) : 1, a = path[i], b = path[i + 1]; return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]; }
      d -= seg[i];
    }
    return path[path.length - 1];
  }
  function stepAnim(dt) {
    if (!anim || anim.t < 0) return false;
    const a = anim, steps = a.o.steps, HOLD = 2.5;
    a.t += dt;
    let t = a.t, i = 0;
    while (i < steps.length && t > (+steps[i].dur || 3)) { t -= (+steps[i].dur || 3); i++; }
    const all = a.glows.flat();
    if (i >= steps.length) {                                          // finished: everything fades away
      for (const g of all) g.op = Math.max(0, g.op - dt * 0.5);
      a.dot.material.transparent = true; a.dot.material.opacity = Math.max(0, 1 - t / HOLD);
      a.trail.forEach((m) => { m.visible = false; });
      if (t > HOLD) { a.t = -1; a.step = -1; a.dot.visible = false; a.dot.material.opacity = 1; for (const g of all) g.op = 0; setFloorText(null, 'anim'); }
      return true;
    }
    const s = steps[i], f = t / (+s.dur || 3);
    if (i !== a.step) {
      a.step = i;
      const dc = new THREE.Color(s.color || a.o.color || '#7ff3ff');            // the dot takes the step's colour
      a.dot.material.color.copy(dc); a.dot.children[0].material.color.copy(dc); a.trail.forEach((m) => m.material.color.copy(dc));
      setFloorText(s.caption ? { text: s.caption, yaw: +a.o.captionYaw || 0, dist: +a.o.captionDist || 1.2, eye: a.o.eye, maxW: 2.9, wrap: 24,
                                 color: s.color || a.o.color || '#7ff3ff' } : null, 'anim');
    }
    a.glows.forEach((gs, j) => gs.forEach((g) => {
      if (j !== i) { g.op = Math.max(0, g.op - dt * 0.8); return; }
      const pulse = 0.24 + 0.1 * Math.sin(a.t * 6);
      g.op = s.flash ? 0.3 + 0.5 * Math.abs(Math.sin(f * Math.PI * 3)) : Math.min(pulse, g.op + dt * 0.8);
    }));
    if (s.path && s.path.length) {
      const p = pathAt(s.path, smooth(Math.min(1, f * 1.2)));
      a.dot.visible = true; a.dot.material.transparent = false; a.dot.material.opacity = 1;
      a.dot.position.set(p[0], a.fy + a.sz, -p[1]);
    }
    a.hist.unshift(a.dot.position.clone()); if (a.hist.length > 40) a.hist.length = 40;
    a.trail.forEach((m, k) => { const h = a.hist[(k + 1) * 4]; m.visible = !!h && a.dot.visible; if (h) m.position.copy(h); });
    return true;
  }
"""
EDITS = {
    "tour3d.js": [
        ("""  function setSize(w, h) { renderer.setSize(""", ANIM_JS + """  function setSize(w, h) { renderer.setSize("""),
        ("""    if (stepInspect()) dirty = true;
    if (!dirty) return false;""",
         """    if (stepInspect()) dirty = true;
    if (stepAnim(dt)) dirty = true;
    if (!dirty) return false;"""),
        ("""  return { setSize, setRoom, sync, setInspect, setFloorText, frame,""",
         """  return { setSize, setRoom, sync, setInspect, setFloorText, setAnim, playAnim, frame,"""),
    ],
    "tour.html": [
        ("""  function sync3d() {
    if (!t3) return;
    const r = roomById(S.room);
""", """  function sync3d() {
    if (!t3) return;
    const r = roomById(S.room);
    if (t3.setAnim) t3.setAnim(r && r.anim ? { ...r.anim, eye: eyeOf(r) } : null, r ? r.id : '');   // a floor animation (played by a hotspot)
"""),
        ("""    } else if (m.type === 'info') {
""", """    } else if (m.type === 'info') {
      if (m.play && t3 && t3.playAnim) t3.playAnim();                   // play the room's floor animation
"""),
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
back = os.path.join(RB, "_backup_2026-11-04c_tinypc"); os.makedirs(back, exist_ok=True)
for f, src in out.items():
    p = os.path.join(RB, "builder", f)
    if not os.path.exists(os.path.join(back, f)): shutil.copy2(p, os.path.join(back, f))
    open(p, "w", encoding="utf-8", newline="").write(src)
print("patched", ", ".join(out), "; originals in", back)
