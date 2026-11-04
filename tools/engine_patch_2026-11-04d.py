"""
Fourth Room Builder tour-player patch for TinyPC (4 Nov 2026), after engine_patch_2026-11-04c.py: a step-through
diagram drawn live in a room, for TinyPC's "Inside a core" fetch-decode-execute room. Opt-in: rooms without "sim" are
unchanged.

  room.sim = {
    boxes: [ { id, label, yaw, h, dist, w, hh, color, kind } ]      kind "panel" = the caption panel (title + text)
        each box is a flat panel facing the centre: yaw (degrees), h = height of its middle (m), dist (m), w x hh (m)
    buses: [ [boxId, boxId], ... ]                                  faint lines between boxes
    init:  { boxId: "text", ... }                                   starting values (\n = new line; a line starting
                                                                     with ">" is highlighted)
    states: [ { title, text, hi: [boxId...], moves: [ { from, to, text, set: { boxId: "text" } } ], set: { ... } } ]
        entering a state: its moves fly one after another (a value in a pill travels from box to box, about 1.1 s each,
        and its "set" lands on arrival), then the state's own "set"; "hi" boxes get a gold border; title/text go on the panel
  }
  marker.sim = "next" | "back" | "reset" | "auto" on any hotspot: tapping it steps the diagram (no card opens).
  "auto" plays the remaining steps one after another (about 4 s apart); tap again to stop.

    python engine_patch_2026-11-04d.py <RoomBuilder folder> [--check]

Backs up builder/tour3d.js and builder/tour.html to _backup_2026-11-04d_tinypc/ first; refuses unless each old piece
occurs exactly once.
"""
import os, shutil, sys

RB = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"D:\Projects\01_Active\RoomBuilder"
SIM_JS = r"""  // ---------------------------------------------------------------- a step-through diagram (registers, buses, values)
  //   setSim({ eye, boxes, buses, init, states }, key) or null; simStep('next' | 'back' | 'reset' | 'auto')
  let sim = null;
  const PXM = 600;                                                     // canvas pixels per metre of panel
  function boxPos(b, eye, inset = 0) {
    const y = (+b.yaw || 0) * D2R, d = (+b.dist || 2.5) - inset;
    return new THREE.Vector3(d * Math.sin(y), (+b.h || 1.2) - eye, -d * Math.cos(y));
  }
  function wrapLines(x, text, maxW) {
    const out = [];
    for (const para of String(text || '').split('\n')) {
      let line = '';
      for (const w of para.split(/\s+/).filter(Boolean)) { const t = line ? line + ' ' + w : w; if (x.measureText(t).width > maxW && line) { out.push(line); line = w; } else line = t; }
      out.push(line);
    }
    return out;
  }
  function drawBox(s, b) {
    const cv = s.cvs[b.id], x = cv.getContext('2d'), W = cv.width, H = cv.height, hi = s.hi.has(b.id);
    const col = hi ? '#ffd36b' : (b.color || '#6fd3e6');
    x.clearRect(0, 0, W, H);
    x.beginPath(); x.roundRect(6, 6, W - 12, H - 12, 22); x.fillStyle = hi ? 'rgba(40,32,10,0.92)' : 'rgba(10,16,24,0.88)'; x.fill();
    x.lineWidth = hi ? 14 : 6; x.strokeStyle = col; x.stroke();
    if (b.kind === 'panel') {
      let fp = 80; x.textBaseline = 'top'; x.textAlign = 'left';
      let tp = 96; do { x.font = `700 ${tp}px "Segoe UI", system-ui, sans-serif`; tp -= 4; } while (x.measureText(s.title || '').width > W - 80 && tp > 30);
      x.fillStyle = '#ffd36b'; x.fillText(s.title || '', 40, 34);
      for (;;) {                                                       // shrink the text until it fits
        x.font = `500 ${fp}px "Segoe UI", system-ui, sans-serif`;
        const ls = wrapLines(x, s.text || '', W - 80);
        if (ls.length * fp * 1.25 < H - 160 || fp < 30) { x.fillStyle = '#fff'; ls.forEach((l, i) => x.fillText(l, 40, 140 + i * fp * 1.25)); break; }
        fp -= 4;
      }
      s.tex[b.id].needsUpdate = true; return;
    }
    x.textAlign = 'left'; x.textBaseline = 'top'; x.fillStyle = col;
    let lp = 60; do { x.font = `600 ${lp}px "Segoe UI", system-ui, sans-serif`; lp -= 2; } while (x.measureText(b.label || b.id).width > W - 56 && lp > 18);
    x.fillText(b.label || b.id, 30, 24);
    const lines = String(s.vals[b.id] ?? '').split('\n');
    let fp = Math.min(170, (H - 110) / Math.max(1, lines.length) / 1.15);
    x.font = `700 ${fp}px Consolas, "Courier New", monospace`;
    const mw = Math.max(1, ...lines.map((l) => x.measureText(l.replace(/^>/, '')).width));
    if (mw > W - 70) { fp *= (W - 70) / mw; x.font = `700 ${fp}px Consolas, "Courier New", monospace`; }
    const top = 96 + Math.max(0, (H - 110 - lines.length * fp * 1.15) / 2);
    lines.forEach((l, i) => {
      const on = l.startsWith('>'), t = on ? l.slice(1) : l, yy = top + i * fp * 1.15;
      if (on) { x.fillStyle = 'rgba(255,211,107,0.25)'; x.fillRect(16, yy - fp * 0.05, W - 32, fp * 1.12); }
      x.fillStyle = on ? '#ffd36b' : '#fff'; x.textAlign = lines.length > 1 ? 'left' : 'center';
      x.fillText(t, lines.length > 1 ? 36 : W / 2, yy);
    });
    s.tex[b.id].needsUpdate = true;
  }
  function pill(text) {
    const cv = document.createElement('canvas'), x = cv.getContext('2d'), fp = 90;
    x.font = `700 ${fp}px Consolas, "Courier New", monospace`;
    cv.width = Math.ceil(x.measureText(text).width + fp * 1.2); cv.height = Math.round(fp * 1.5);
    x.font = `700 ${fp}px Consolas, "Courier New", monospace`;
    x.beginPath(); x.roundRect(4, 4, cv.width - 8, cv.height - 8, cv.height / 2 - 4); x.fillStyle = '#ffd36b'; x.fill();
    x.fillStyle = '#1a1406'; x.textBaseline = 'middle'; x.textAlign = 'center'; x.fillText(text, cv.width / 2, cv.height / 2 + 4);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(cv.width / 600, cv.height / 600), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false, toneMapped: false }));
    m.renderOrder = 10; return m;
  }
  function setSim(o, key = '') {
    const k = o ? key + '|' + JSON.stringify(o) : '';
    if (sim && sim.key === k) return;
    if (sim) { scene.remove(sim.group); sim.group.traverse((c) => { if (c.geometry) c.geometry.dispose(); if (c.material) { if (c.material.map) c.material.map.dispose(); c.material.dispose(); } }); sim = null; dirty = true; }
    if (!o || !o.boxes) return;
    const eye = +o.eye || 1.12, group = new THREE.Group(), s = { key: k, o, eye, group, cvs: {}, tex: {}, mesh: {}, byId: {}, vals: {}, hi: new Set(), i: 0, q: [], fly: null, auto: false, autoT: 0, title: '', text: '' };
    for (const b of o.boxes) {
      s.byId[b.id] = b;
      const w = +b.w || 0.9, hh = +b.hh || 0.42, cv = document.createElement('canvas');
      cv.width = Math.round(w * PXM); cv.height = Math.round(hh * PXM); s.cvs[b.id] = cv;
      const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8; s.tex[b.id] = tex;
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, hh), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, toneMapped: false }));
      m.position.copy(boxPos(b, eye)); m.rotation.y = -(+b.yaw || 0) * D2R; m.renderOrder = 5; group.add(m); s.mesh[b.id] = m;
    }
    for (const [a, c] of o.buses || []) {                              // faint bus lines, from edge to edge
      const A = s.byId[a], C = s.byId[c]; if (!A || !C) continue;
      const pa = boxPos(A, eye, 0.02), pc = boxPos(C, eye, 0.02);
      const tube = new THREE.Mesh(new THREE.TubeGeometry(new THREE.LineCurve3(pa, pc), 1, 0.012, 6, false),
        new THREE.MeshBasicMaterial({ color: 0x3f8fa0, transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false }));
      tube.renderOrder = 4; group.add(tube);
    }
    scene.add(group); sim = s; goState(0, true); dirty = true;
  }
  function valsUpTo(n) {                                               // the values after states 0..n have finished
    const v = { ...(sim.o.init || {}) };
    for (let i = 0; i <= n; i++) { const st = sim.o.states[i] || {}; for (const mv of st.moves || []) Object.assign(v, mv.set || {}); Object.assign(v, st.set || {}); }
    return v;
  }
  function goState(n, instant) {
    const s = sim, st = s.o.states[n] || {};
    if (s.fly) { s.group.remove(s.fly.m); s.fly.m.geometry.dispose(); s.fly.m.material.map.dispose(); s.fly.m.material.dispose(); s.fly = null; }
    s.i = n; s.q = instant ? [] : (st.moves || []).slice();
    s.vals = instant ? valsUpTo(n) : valsUpTo(n - 1);
    s.hi = new Set(st.hi || []); s.title = st.title || ''; s.text = st.text || '';
    if (!instant && !s.q.length) Object.assign(s.vals, st.set || {});
    for (const b of s.o.boxes) drawBox(s, b);
    dirty = true;
  }
  function simStep(cmd) {
    if (!sim) return;
    const n = sim.o.states.length;
    if (cmd === 'auto') { sim.auto = !sim.auto; sim.autoT = 0; if (sim.auto && sim.i >= n - 1) goState(0, true); return; }
    if (cmd === 'reset') { sim.auto = false; goState(0, true); return; }
    if (cmd === 'back') { sim.auto = false; goState(Math.max(0, sim.i - 1), true); return; }
    if (sim.q.length || sim.fly) { goState(sim.i, true); }             // tapped mid-move: finish this step at once
    goState(sim.i >= n - 1 ? 0 : sim.i + 1, sim.i >= n - 1);
  }
  function stepSim(dt) {
    const s = sim; if (!s) return false;
    let moved = false;
    if (!s.fly && s.q.length) {
      const mv = s.q.shift(), A = s.byId[mv.from], C = s.byId[mv.to];
      if (A && C) { const m = pill(String(mv.text ?? '')); s.group.add(m); s.fly = { m, a: boxPos(A, s.eye, 0.12), c: boxPos(C, s.eye, 0.12), t: 0, mv }; }
      else Object.assign(s.vals, mv.set || {});
    }
    if (s.fly) {
      const f = s.fly; f.t += dt / 1.1; const u = smooth(Math.min(1, f.t));
      const p = new THREE.Vector3().lerpVectors(f.a, f.c, u); p.multiplyScalar(1 - 0.18 * Math.sin(Math.PI * u));   // bows in towards you
      f.m.position.copy(p); f.m.lookAt(0, p.y, 0);
      if (f.t >= 1) {
        Object.assign(s.vals, f.mv.set || {}); s.group.remove(f.m); f.m.geometry.dispose(); f.m.material.map.dispose(); f.m.material.dispose(); s.fly = null;
        if (!s.q.length) Object.assign(s.vals, (s.o.states[s.i] || {}).set || {});
        for (const b of s.o.boxes) drawBox(s, b);
      }
      moved = true;
    }
    if (s.auto && !s.fly && !s.q.length) {
      s.autoT += dt;
      if (s.autoT > 4.0) { s.autoT = 0; if (s.i >= s.o.states.length - 1) s.auto = false; else goState(s.i + 1, false); moved = true; }
    }
    return moved;
  }
"""
EDITS = {
    "tour3d.js": [
        ("""  function setSize(w, h) { renderer.setSize(""", SIM_JS + """  function setSize(w, h) { renderer.setSize("""),
        ("""    if (stepAnim(dt)) dirty = true;
""", """    if (stepAnim(dt)) dirty = true;
    if (stepSim(dt)) dirty = true;
"""),
        ("""setAnim, playAnim, frame,""", """setAnim, playAnim, setSim, simStep, frame,"""),
    ],
    "tour.html": [
        ("""    if (t3.setAnim) t3.setAnim(r && r.anim ? { ...r.anim, eye: eyeOf(r) } : null, r ? r.id : '');""",
         """    if (t3.setAnim) t3.setAnim(r && r.anim ? { ...r.anim, eye: eyeOf(r) } : null, r ? r.id : '');
    if (t3.setSim) t3.setSim(r && r.sim ? { ...r.sim, eye: eyeOf(r) } : null, r ? r.id : '');      // a step-through diagram"""),
        ("""    S.typed = '';
    if (m.type === 'set')""", """    S.typed = '';
    if (m.sim && t3 && t3.simStep) { sound('tick'); t3.simStep(m.sim); return; }   // steps the room's diagram: no card
    if (m.type === 'set')"""),
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
back = os.path.join(RB, "_backup_2026-11-04d_tinypc"); os.makedirs(back, exist_ok=True)
for f, src in out.items():
    p = os.path.join(RB, "builder", f)
    if not os.path.exists(os.path.join(back, f)): shutil.copy2(p, os.path.join(back, f))
    open(p, "w", encoding="utf-8", newline="").write(src)
print("patched", ", ".join(out), "; originals in", back)
