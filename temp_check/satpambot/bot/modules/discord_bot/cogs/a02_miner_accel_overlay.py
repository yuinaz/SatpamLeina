from discord.ext import commands
import inspect, logging, asyncio

log = logging.getLogger(__name__)

async def _maybe_add_cog(bot, cog):
    add = getattr(bot, "add_cog", None)
    if not add:
        return
    try:
        res = add(cog)
        if inspect.isawaitable(res):
            await res
    except Exception as e:
        log.exception("failed to add cog %s: %s", type(cog).__name__, e)

import re, logging, os, json

log = logging.getLogger(__name__)

def _parse_floats(s):
    if s is None:
        return []
    if isinstance(s, (list, tuple)):
        try:
            return [float(x) for x in s]
        except Exception:
            pass
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(s))
    out = []
    for n in nums:
        try:
            out.append(float(n))
        except Exception:
            continue
    return out

def _load_local_json():
    for cand in ("local.json", "/opt/render/project/src/local.json"):
        try:
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

class MinerAccelOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cfg = _load_local_json().get("miner", {})
        raw = cfg.get("accel_factors") or os.getenv("MINER_ACCEL_FACTORS", "0.85,1.00,1.20")
        self.factors = _parse_floats(raw) or [1.0]
        log.info("[miner_accel_overlay] factors=%s (raw=%r)", self.factors, raw)
async def setup(bot):
    if bot.get_cog("MinerAccelOverlay"):
        return
    await _maybe_add_cog(bot, MinerAccelOverlay(bot))