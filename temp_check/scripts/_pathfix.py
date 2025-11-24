# Auto-inject repo root into sys.path so 'satpambot' can be imported when running from scripts/
import sys
from pathlib import Path
HERE = Path(__file__).resolve()
CANDIDATES = [HERE] + list(HERE.parents)[:6]
added = None
for p in CANDIDATES:
    if (p / "satpambot").is_dir():
        sys.path.insert(0, str(p))
        added = p
        break
    if (p / "src" / "satpambot").is_dir():
        sys.path.insert(0, str(p / "src"))
        added = p / "src"
        break
if not added:
    # As a last resort, add repo two levels up (typical when scripts/ is under repo root)
    sys.path.insert(0, str(HERE.parent.parent))
