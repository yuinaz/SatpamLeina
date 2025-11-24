import os, json, re

SENIOR_PHASES = ["SMP","SMA","KULIAH"]

def _to_windows_drive_if_gitbash_style(path: str) -> str:
    if not path: return path
    m = re.match(r"^/([a-zA-Z])/(.*)$", path.replace('\\','/'))
    if m:
        drive = m.group(1).upper()
        rest = m.group(2).replace('/', os.sep)
        return f"{drive}:{os.sep}{rest}"
    return path

def _repo_root_candidates(start_dir: str):
    cur = os.path.abspath(start_dir)
    for _ in range(12):
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur: break
        cur = parent
    cur = os.path.abspath(os.getcwd())
    for _ in range(10):
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur: break

def resolve_ladder_path(script_dir: str):
    envp = os.getenv("LADDER_FILE")
    if envp:
        envp2 = _to_windows_drive_if_gitbash_style(envp)
        if os.path.exists(envp2):
            return os.path.abspath(envp2)
    # canonical
    for root in _repo_root_candidates(script_dir):
        cand = os.path.join(root, "data", "neuro-lite", "ladder.json")
        if os.path.exists(cand):
            return os.path.abspath(cand)
    # fallback root
    for root in _repo_root_candidates(script_dir):
        cand = os.path.join(root, "ladder.json")
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return None

def load_ladders(script_file: str):
    path = resolve_ladder_path(os.path.dirname(script_file))
    if not path:
        raise FileNotFoundError("ladder.json not found (tried LADDER_FILE and data/neuro-lite/ladder.json).")
    with open(path, "r", encoding="utf-8") as f:
        j = json.load(f)
    ladders = {}
    for domain in ("junior","senior"):
        d = j.get(domain) or {}
        for phase, stages in d.items():
            ladders[phase] = {str(k): int(v) for k,v in stages.items()}
    return ladders

def parse_stage_idx(k: str) -> int:
    ks = str(k).strip().upper()
    for p in ("L","S"):
        if ks.startswith(p):
            try: return int(ks[len(p):])
            except Exception: pass
    try: return int(ks)
    except Exception: return 999999

def order_stages(d):
    return sorted(d.items(), key=lambda kv: parse_stage_idx(kv[0]))

def compute_senior_label(total: int, ladders: dict):
    spent = 0
    for phase in SENIOR_PHASES:
        chunks = ladders.get(phase, {})
        for (stage, need) in order_stages(chunks):
            need = max(1, int(need))
            have = max(0, total - spent)
            if have < need:
                pct = 100.0 * (have / float(need))
                rem = max(0, need - have)
                return (f"{phase}-S{parse_stage_idx(stage)}", round(pct,1), rem)
            spent += need
    last = SENIOR_PHASES[-1]
    last_idx = len(order_stages(ladders.get(last, {"S1":1})))
    return (f"{last}-S{last_idx}", 100.0, 0)

def senior_boundaries(ladders: dict):
    # Return cumulative thresholds for each stage
    bounds = []
    total = 0
    for phase in SENIOR_PHASES:
        for (stage, need) in order_stages(ladders.get(phase, {})):
            need = max(1, int(need))
            bounds.append((phase, parse_stage_idx(stage), total, total+need))
            total += need
    return bounds
