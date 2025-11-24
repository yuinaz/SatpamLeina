from __future__ import annotations
from typing import Any
from .module_options import opt, opt_int, opt_bool, opt_list
def cfg(key: str, default: Any=None) -> Any: return opt(key, default)
def cfg_int(key: str, default: int=0) -> int: return opt_int(key, default)
def cfg_bool(key: str, default: bool=False) -> bool: return opt_bool(key, default)
def cfg_list(key: str) -> list[str]: return opt_list(key)
