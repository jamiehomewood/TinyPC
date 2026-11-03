"""
Room Builder tour player additions for TinyPC (3 Nov 2026). Run once against a RoomBuilder folder:

    python engine_patch_2026-11-03.py <RoomBuilder folder>

Backs up builder/tour.html and builder/tour3d.js to _backup_2026-11-03_tinypc/ first, and refuses to patch unless every
piece of old code it replaces occurs exactly once. Everything added is opt-in: tours that don't use the new fields
behave exactly as before.

New tour fields
- Flags (hidden progress, never shown in the bag): use-marker accepts[].flag and question options[].flag set a flag;
  go-marker "requires" and accepts[].requires accept item ids or flags.
- accepts[].requires + accepts[].notYet: an item is only taken once those items/flags are in place ("paste before the cooler").
- accepts[].sound / room.enterSound: a sound to play ("yes", "no", "tick", "door", or a beep code "post:<pattern>",
  S = short beep, L = long beep, space = pause: "post:S" all fine, "post:LSS", "post:SSS SSS").
- go-marker lockedGo: { "<item or flag>": "<room id>", "*": "<room id>" }: when something it requires is missing, go
  to the room for the first missing one (in "requires" order) instead of showing the locked message (fault rooms).
- room.ambient: "fan" = a looping fan hum that spins up on arrival (stops in a room without it).
- room.props: [{ id, model, yaw, dist, h, turn, size, spin, axis }]: catalogue models standing in the room all the time
  (not markers). spin = turns per minute about the model's own axis through its middle (axis "z" = the model's front-back
  axis, i.e. a fan rotor built facing the front), no contact shadow.
"""
import os, shutil, sys

RB = sys.argv[1] if len(sys.argv) > 1 else r"D:\Projects\01_Active\RoomBuilder"
B = os.path.join(RB, "builder")
BACK = os.path.join(RB, "_backup_2026-11-03_tinypc")

def patch(path, edits):
    src = open(path, encoding="utf-8").read()
    for old, new in edits:
        n = src.count(old)
        if n != 1: raise SystemExit(f"{os.path.basename(path)}: expected 1 match, found {n}:\n{old[:200]}")
        src = src.replace(old, new)
    return src

TOUR = [
# flags live with the rest of the tour state
("gave: new Set() };", "gave: new Set(), flags: new Set() };"),
# beep codes + fan hum
("""      const notes = { yes: [[660, 0], [880, .12]], no: [[220, 0], [180, .16]], tick: [[740, 0]], door: [[180, 0], [140, .1]] }[kind] || [];""",
 """      if (String(kind).startsWith('post:')) { postBeeps(String(kind).slice(5)); return; }
      const notes = { yes: [[660, 0], [880, .12]], no: [[220, 0], [180, .16]], tick: [[740, 0]], door: [[180, 0], [140, .1]] }[kind] || [];"""),
("""  addEventListener('pointerdown', () => { if (actx && actx.state === 'suspended') actx.resume(); });""",
 """  // PC-speaker beep codes: S = short, L = long, space = pause ("S" = all fine, "LSS", "SSS SSS")
  function postBeeps(p) {
    try {
      let t = actx.currentTime + 0.05;
      for (const ch of String(p).toUpperCase()) {
        if (ch === ' ') { t += 0.6; continue; }
        if (ch !== 'S' && ch !== 'L') continue;
        const len = ch === 'L' ? 0.75 : 0.18, o = actx.createOscillator(), g = actx.createGain();
        o.type = 'square'; o.frequency.value = 1000;
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.05, t + 0.01);
        g.gain.setValueAtTime(0.05, t + len - 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + len);
        o.connect(g).connect(actx.destination); o.start(t); o.stop(t + len + 0.05);
        t += len + 0.22;
      }
    } catch (e) {}
  }
  // a looping room sound ("fan": filtered noise and a low hum that spin up over a couple of seconds); null = quiet
  let amb = null;
  function ambient(kind) {
    if (!SOUND) return;
    try {
      if (amb && amb.kind === kind) return;
      if (amb) { const a = amb; a.g.gain.setTargetAtTime(0.0001, actx.currentTime, 0.35); setTimeout(() => { try { a.src.forEach((s) => s.stop()); } catch (e) {} }, 2500); amb = null; }
      if (kind !== 'fan') return;
      actx = actx || new (window.AudioContext || window.webkitAudioContext)();
      if (actx.state === 'suspended') actx.resume();
      const n = actx.sampleRate * 4, buf = actx.createBuffer(1, n, actx.sampleRate), d = buf.getChannelData(0);
      let b = 0; for (let i = 0; i < n; i++) { b = 0.985 * b + 0.06 * (Math.random() * 2 - 1); d[i] = b; }
      for (let i = 0; i < 2000; i++) { const k = i / 2000; d[i] = d[i] * k + d[n - 2000 + i] * (1 - k); }   // soften the loop point
      const src = actx.createBufferSource(); src.buffer = buf; src.loop = true; src.loopEnd = (n - 2000) / actx.sampleRate;
      const lp = actx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 900;
      const pk = actx.createBiquadFilter(); pk.type = 'peaking'; pk.frequency.value = 180; pk.gain.value = 6;
      const hum = actx.createOscillator(); hum.type = 'sine'; hum.frequency.value = 95;
      const hg = actx.createGain(); hg.gain.value = 0.035;
      const g = actx.createGain(); g.gain.setValueAtTime(0.0001, actx.currentTime); g.gain.exponentialRampToValueAtTime(0.32, actx.currentTime + 2.5);
      src.connect(lp).connect(pk).connect(g); hum.connect(hg).connect(g); g.connect(actx.destination);
      src.start(); hum.start(); amb = { kind, g, src: [src, hum] };
    } catch (e) {}
  }
  addEventListener('pointerdown', () => { if (actx && actx.state === 'suspended') actx.resume(); });"""),
# arriving in a room: its ambient sound and arrival sound (e.g. the POST beep)
("""    await fadeTo(1, 550);
    busy = false;""",
 """    await fadeTo(1, 550);
    busy = false;
    ambient(r.ambient || null);
    if (r.enterSound) setTimeout(() => sound(r.enterSound), 300);"""),
("""  function restart() { hush(); fresh();""", """  function restart() { hush(); ambient(null); fresh();"""),
# go markers: flags count as having something; lockedGo sends you to a fault room
("""      const missing = (m.requires || []).filter((i) => !S.items.has(i));
      if (missing.length) { sound('no');""",
 """      const missing = (m.requires || []).filter((i) => !S.items.has(i) && !S.flags.has(i));
      const lg = missing.length && m.lockedGo ? (missing.map((i) => m.lockedGo[i]).find((g) => g && roomById(g)) || (roomById(m.lockedGo['*']) ? m.lockedGo['*'] : null)) : null;
      if (lg) { goTo(lg); return; }
      if (missing.length) { sound('no');"""),
# use markers: an item only goes in once what it needs is there; flags; own sound
("""    const acc = (m.accepts || []).find((a) => a.item === itemId), scoredUse = (m.accepts || []).some((a) => a.correct);""",
 """    const acc = (m.accepts || []).find((a) => a.item === itemId), scoredUse = (m.accepts || []).some((a) => a.correct);
    const need = acc ? (acc.requires || []).filter((i) => !S.items.has(i) && !S.flags.has(i)) : [];
    if (need.length) {                                                 // not yet: something else has to go in first
      S.card = { kind: 'useResult', mid, yaw: wallOf(m.yaw), title: `${m.label || 'Give or use'}: ${itemName(itemId)}`, good: false,
                 text: acc.notYet || 'Not yet: something else has to go in first.', go: null };
      sound('no'); changed(); return;
    }"""),
("""    if (acc && acc.give) { S.items.add(acc.give); S.got.add(acc.give); S.sel = acc.give; }""",
 """    if (acc && acc.give) { S.items.add(acc.give); S.got.add(acc.give); S.sel = acc.give; }
    if (acc && acc.flag && good) S.flags.add(acc.flag);"""),
("""    sound(good ? 'yes' : 'no');
    if (acc && acc.say) speak(acc.say);""",
 """    if (acc && acc.sound) sound(acc.sound); else sound(good ? 'yes' : 'no');
    if (acc && acc.say) speak(acc.say);"""),
("""    if (o.give) { S.items.add(o.give); S.got.add(o.give); }""",
 """    if (o.give) { S.items.add(o.give); S.got.add(o.give); }
    if (o.flag) S.flags.add(o.flag);"""),
# room props: models standing in the room all the time, some spinning (fans)
("""      dist: +m.dist || 1.5, h: baseH(r, m), eye: eyeOf(r), turn: +m.turn || 0, size: +m.size || 1 })) : []);""",
 """      dist: +m.dist || 1.5, h: baseH(r, m), eye: eyeOf(r), turn: +m.turn || 0, size: +m.size || 1 })).concat((r.props || []).filter((p) => p.model).map((p) => ({
      key: 'prop:' + p.id, model: p.model, yaw: +p.yaw || 0, dist: +p.dist || 1.5, h: +p.h || 0, eye: eyeOf(r), turn: +p.turn || 0, size: +p.size || 1,
      spin: +p.spin || 0, axis: p.axis || 'z', shadow: false }))) : []);"""),
]

T3D = [
("""//   t.sync([{ key, model, yaw, dist, h, eye, turn, size, visible }]);   models standing in the room (h = height of the surface)""",
 """//   t.sync([{ key, model, yaw, dist, h, eye, turn, size, visible, spin, axis, shadow }]);   models standing in the room (h = height of the surface)
//     spin: turns per minute about the model's own axis ("x" | "y" | "z", default z) through its middle; shadow: false = no contact shadow"""),
("""          mine.group.add(skClone(m.proto)); mine.group.add(blob(m.size)); mine.size = m.size.clone(); dirty = true; onLoad && onLoad(o.key);""",
 """          const c = skClone(m.proto);
          if (+o.spin) { const piv = new THREE.Group(); piv.position.y = m.size.y / 2; c.position.y = -m.size.y / 2; piv.add(c); mine.group.add(piv); mine.spinner = piv; }
          else mine.group.add(c);
          if (o.shadow !== false) mine.group.add(blob(m.size));
          mine.size = m.size.clone(); dirty = true; onLoad && onLoad(o.key);"""),
("""  function frame() {
    if (stepInspect()) dirty = true;""",
 """  let spinT = 0;
  function frame() {
    const tn = performance.now(), dt = spinT ? Math.min(0.1, (tn - spinT) / 1000) : 0; spinT = tn;
    for (const p of placed.values()) if (p.spinner && p.spec && +p.spec.spin && p.group.visible) {
      const ax = p.spec.axis === 'x' || p.spec.axis === 'y' ? p.spec.axis : 'z';
      p.spinner.rotation[ax] += dt * p.spec.spin / 60 * Math.PI * 2; dirty = true;
    }
    if (stepInspect()) dirty = true;"""),
]

if __name__ == "__main__":
    tour_p, t3_p = os.path.join(B, "tour.html"), os.path.join(B, "tour3d.js")
    a, b = patch(tour_p, TOUR), patch(t3_p, T3D)                  # check everything before touching anything
    if "--check" in sys.argv: print("all edits match once"); raise SystemExit(0)
    os.makedirs(BACK, exist_ok=True)
    for p in (tour_p, t3_p):
        dst = os.path.join(BACK, os.path.basename(p))
        if not os.path.exists(dst): shutil.copy2(p, dst)
    open(tour_p, "w", encoding="utf-8", newline="").write(a)
    open(t3_p, "w", encoding="utf-8", newline="").write(b)
    print("patched; originals in", BACK)
