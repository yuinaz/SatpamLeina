SENIOR_PHASES = ["SMP","SMA","KULIAH"]

def rank_tuple(label: str):
    try: p, s = label.split("-",1)
    except ValueError: p, s = label, "S0"
    try: pi = SENIOR_PHASES.index(p)
    except ValueError: pi = -1
    try: si = int(s.upper().replace("S",""))
    except Exception: si = 0
    return (pi, si)

def is_lower(new_label: str, base_label: str) -> bool:
    return rank_tuple(new_label) < rank_tuple(base_label)
