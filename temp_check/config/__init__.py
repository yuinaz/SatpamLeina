# satpambot/config/__init__.py
# Safe import layer: prefer runtime for cfg/set_cfg/get_secret;
# provide fallbacks for all_cfg/set_secret via runtime_ext when not defined in runtime.
from .runtime import cfg, set_cfg, get_secret  # type: ignore
try:
    from .runtime import all_cfg  # type: ignore
except Exception:  # pragma: no cover
    from .runtime_ext import all_cfg  # type: ignore
try:
    from .runtime import set_secret  # type: ignore
except Exception:  # pragma: no cover
    from .runtime_ext import set_secret  # type: ignore
