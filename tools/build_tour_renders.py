"""
Builds everything the open-day tour's rooms need and renders them, in order. Run with Windows Python on the PC that has
Room Builder and Blender:

    py -3 tools\\build_tour_renders.py drafts      models -> catalogue -> specs -> draft renders (in _work\\tour\\) ->
                                                  rotor check for the switched-on rooms -> per-room cases -> drafts again
    py -3 tools\\build_tour_renders.py library     specs at standard quality, queued on Room Builder's server (it must be
                                                  running, port 8030): the renders land in its library as "TinyPC tour - ..."

    py -3 tools\\build_tour_renders.py update [rooms]
                                                  Re-renders just some rooms (default: the 4 Nov changes: the paste room and
                                                  the higher camera in the RAM, cooler and graphics-card stops). Applies the
                                                  click patch to Room Builder if it isn't there, builds the paste model, checks
                                                  the fan rotors of switched-on rooms on a draft, queues the rooms at standard
                                                  quality, waits for them, rewrites the tour and copies the new renders and the
                                                  tour into this repo. Room Builder's server must be running. About 30 minutes.

Copies models into Room Builder's catalogue (copy only, never deletes). Progress goes to _work\\tour\\build_log.txt.
"""
import glob, json, os, shutil, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RB = os.environ.get("ROOMBUILDER", r"D:\Projects\01_Active\RoomBuilder")
cfg = json.load(open(os.path.join(RB, "config.json"), encoding="utf-8"))
BLENDER = cfg.get("blender") or r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
WORK = os.path.join(ROOT, "_work", "tour"); os.makedirs(WORK, exist_ok=True)
SPECS = os.path.join(ROOT, "specs", "tour")
LOG = open(os.path.join(WORK, "build_log.txt"), "a", encoding="utf-8")
PY = sys.executable
ON_ROOMS = ["F_dram", "F_ram", "S_on"]
MODELS = (["tpc_board", "tpc_board_off", "tpc_board_dbg_dram", "tpc_board_dbg_cpu", "tpc_board_dbg_vga", "tpc_board_dbg_boot",
           "tpc_cpu_socket_clean", "tpc_cpu_socket_empty", "tpc_dimm_slot_open", "tpc_dimm", "tpc_dimm_off", "tpc_tower_cooler",
           "tpc_tower_cooler_on", "tpc_gpu", "tpc_gpu_on", "tpc_case_shell_v2_on", "tpc_case_shell_v2_off",
           "tpc_atx24_v2", "tpc_eps8_v2", "tpc_monitor", "tpc_monitor_on", "tpc_pc_tower_on", "tpc_pc_tower_fixed_on"]
          + [f"tpc_pc_tower_s{n}" for n in range(7)])

def log(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True); LOG.write(line + "\n"); LOG.flush()

def run(args, cwd=ROOT):
    log("run:", " ".join(os.path.basename(a) if i == 0 else a for i, a in enumerate(args))[:300])
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace")
    LOG.write(p.stdout[-6000:] + p.stderr[-3000:] + "\n"); LOG.flush()
    for ln in (p.stdout or "").splitlines():
        if ln.startswith(("TPC_", "ROTOR", "RB_DONE", "wrote")) or "rotors" in ln or "Traceback" in ln or "Error" in ln: log("  ", ln)
    return p

def build_models(ids):
    run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(ROOT, "tools", "make_pc_models.py"), "--"] + ids)
    for i in ids:
        src = os.path.join(ROOT, "models", i)
        if os.path.isdir(src): shutil.copytree(src, os.path.join(RB, "catalogue", "models", i), dirs_exist_ok=True)

def rooms():
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(SPECS, "*.json")) if not p.endswith("props.json") and ".props." not in p)

def render(room):
    out = os.path.join(WORK, room)
    run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(RB, "generator", "generate.py"), "--", os.path.join(SPECS, room + ".json"), out, "draft"], cwd=RB)

def drafts():
    build_models(MODELS)
    run([PY, os.path.join(ROOT, "tools", "make_tour_rooms.py"), "draft"])
    for r in rooms(): render(r)
    for r in ON_ROOMS:                                           # which fan rotors can be seen
        eye = json.load(open(os.path.join(SPECS, r + ".json"), encoding="utf-8"))["views"][0]["z"]
        run([BLENDER, "-b", os.path.join(WORK, r, "room.blend"), "-P", os.path.join(ROOT, "tools", "check_rotors.py"), "--",
             os.path.join(SPECS, r + ".props.all.json"), str(eye)])
    run([PY, os.path.join(ROOT, "tools", "make_tour_rooms.py"), "draft"])
    cases = sorted({it["model"] for r in ON_ROOMS for it in json.load(open(os.path.join(SPECS, r + ".json"), encoding="utf-8"))["items"]
                    if it["model"].startswith("tpc_case_shell_v2_on_")})
    if cases: build_models(cases)
    for r in ON_ROOMS: render(r)
    log("drafts done:", ", ".join(rooms()))

def library():
    run([PY, os.path.join(ROOT, "tools", "make_tour_rooms.py"), "standard"])
    for r in rooms():
        spec = json.load(open(os.path.join(SPECS, r + ".json"), encoding="utf-8"))
        req = urllib.request.Request(f"http://localhost:{cfg.get('port', 8030)}/api/render", method="POST", headers={"Content-Type": "application/json"},
                                     data=json.dumps({"spec": spec, "quality": "standard", "name": spec["name"]}).encode())
        log("queued", r, json.load(urllib.request.urlopen(req, timeout=20)).get("id"))

UPDATE_ROOMS = ["T_paste", "T_ramq", "T_ram", "F_ram", "R_fixed", "T_cooler", "T_gpu"]
NEW_MODELS = ["tpc_cpu_socket_paste"]

def update(rooms_):
    start = time.strftime("%Y%m%d-%H%M%S")
    run([PY, os.path.join(ROOT, "tools", "engine_patch_2026-11-04.py"), RB])              # the RAM click (skips if done)
    build_models(NEW_MODELS)
    run([PY, os.path.join(ROOT, "tools", "make_tour_rooms.py"), "draft"])
    on = [r for r in rooms_ if r in ON_ROOMS]
    for r in on:                                              # camera moved: which fan rotors can be seen now
        render(r)
        eye = json.load(open(os.path.join(SPECS, r + ".json"), encoding="utf-8"))["views"][0]["z"]
        run([BLENDER, "-b", os.path.join(WORK, r, "room.blend"), "-P", os.path.join(ROOT, "tools", "check_rotors.py"), "--",
             os.path.join(SPECS, r + ".props.all.json"), str(eye)])
    run([PY, os.path.join(ROOT, "tools", "make_tour_rooms.py"), "standard"])
    cases = sorted({it["model"] for r in on for it in json.load(open(os.path.join(SPECS, r + ".json"), encoding="utf-8"))["items"]
                    if it["model"].startswith("tpc_case_shell_v2_on_") and not os.path.isdir(os.path.join(RB, "catalogue", "models", it["model"]))})
    if cases: build_models(cases)
    names = {}
    for r in list(rooms_):
        sp = os.path.join(SPECS, r + ".json")
        if not os.path.exists(sp):
            log("SKIPPED", r, "- no spec (its model didn't build? see the log above)"); rooms_.remove(r); continue
        spec = json.load(open(sp, encoding="utf-8")); names[spec["name"]] = r
        req = urllib.request.Request(f"http://localhost:{cfg.get('port', 8030)}/api/render", method="POST", headers={"Content-Type": "application/json"},
                                     data=json.dumps({"spec": spec, "quality": "standard", "name": spec["name"]}).encode())
        log("queued", r, json.load(urllib.request.urlopen(req, timeout=20)).get("id"))
    done, t0 = {}, time.time()
    while len(done) < len(names) and time.time() - t0 < 3 * 3600:            # wait for each one to land in the library
        time.sleep(20)
        for mp in glob.glob(os.path.join(RB, "library", "*", "meta.json")):
            d = os.path.dirname(mp); lid = os.path.basename(d)
            if lid < start or lid in done.values(): continue
            try: nm = json.load(open(mp, encoding="utf-8")).get("name")
            except Exception: continue
            if nm in names and names[nm] not in done and glob.glob(os.path.join(d, "view_*.jpg")):
                done[names[nm]] = lid; log("rendered", names[nm], lid, f"({len(done)} of {len(names)})")
    if len(done) < len(names): log("still waiting for:", ", ".join(r for r in rooms_ if r not in done), "- run make_tour.py once they're in")
    run([PY, os.path.join(ROOT, "tools", "make_tour.py"), RB])
    for lid in done.values():                                 # keep the repo's copy of the library up to date
        shutil.copytree(os.path.join(RB, "library", lid), os.path.join(ROOT, "renders", "library", lid), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("*.blend", "*.blend1", "*.exr", "view_*.png"))
    for m in NEW_MODELS:
        if os.path.isdir(os.path.join(ROOT, "models", m)): log("model ready:", m)
    log("update done:", ", ".join(f"{r} {l}" for r, l in done.items()))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "drafts"
    if mode == "update": update(sys.argv[2:] or UPDATE_ROOMS)
    else: {"drafts": drafts, "library": library}[mode]()
