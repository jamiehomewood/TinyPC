"""
Keeps only the fan rotors a student can actually see from a stop: casts rays in the built scene (the room.blend Room
Builder saves next to each render) from the eye to points across each rotor's disc, and drops rotors that are hidden
behind something (another part, the far side of the graphics card...). Reads every candidate from <stop>.props.all.json
and writes the visible ones to <stop>.props.json (the room.props list for the tour).

    blender -b <render dir>/room.blend -P tools/check_rotors.py -- <stop>.props.all.json <eye z>      (writes <stop>.props.json)
"""
import bpy, json, math, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
props_path, eye_z = argv[0], float(argv[1])
props = json.load(open(props_path, encoding="utf-8"))
dg = bpy.context.evaluated_depsgraph_get(); sc = bpy.context.scene
eye = Vector((0, 0, eye_z))
keep = []
for p in props:
    X, Y, Z, R, ax = p["_room"]
    c = Vector((X, Y, Z)); n = Vector((1, 0, 0)) if ax == "x" else Vector((0, 1, 0))
    u = n.cross(Vector((0, 0, 1))).normalized(); v = Vector((0, 0, 1))
    pts = [c] + [c + (u * math.cos(a) + v * math.sin(a)) * R * 0.75 for a in [i * math.pi / 4 for i in range(8)]]
    seen = 0
    for q in pts:
        d = q - eye; dist = d.length
        hit, loc, *_ = sc.ray_cast(dg, eye, d.normalized(), distance=dist + 1.0)
        if not hit or (loc - eye).length >= dist - max(0.06, R * 0.45):     # nothing in front of the fan (its own hub is allowed)
            seen += 1
    frac = seen / len(pts)
    p["_seen"] = round(frac, 2)
    print("ROTOR", p["id"], p["model"], "seen", round(frac, 2), flush=True)
    if frac >= 0.7: keep.append(p)
json.dump(keep, open(props_path.replace(".props.all.json", ".props.json"), "w", encoding="utf-8"), indent=1)
print("ROTORS_KEPT", len(keep), "of", len(props), flush=True)
