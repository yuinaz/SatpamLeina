from __future__ import annotations

import logging
log = logging.getLogger(__name__)

def _apply():
    try:
        mod = __import__("satpambot.bot.modules.discord_bot.helpers.memory_upsert", fromlist=["*"])
    except Exception as e:
        log.debug("[upsert_callsites_overlay] import helper failed: %s", e)
        return
    target = getattr(mod, "memory_upsert", None)
    if not callable(target) or getattr(target, "__patched__", False):
        return

    def wrapper(*args, **kwargs):
        channel_id = kwargs.pop("channel_id", kwargs.pop("channel", None))
        title = kwargs.pop("title", None)
        body = kwargs.pop("body", None)

        # If positional variant (title, body, channel_id=...)
        if channel_id is None and args and hasattr(args[0], "id"):
            try:
                channel_id = int(getattr(args[0], "id", None))
                args = args[1:]
            except Exception:
                pass

        # If first arg is int -> channel id
        if channel_id is None and args and isinstance(args[0], int):
            channel_id = int(args[0]); args = args[1:]

        # Next two positional strings as title/body
        if title is None and args and isinstance(args[0], str):
            title = args[0]; args = args[1:]
        if body is None and args and isinstance(args[0], str):
            body = args[0]; args = args[1:]

        n_args = []
        if channel_id is not None: n_args.append(channel_id)
        if title is not None: n_args.append(title)
        if body is not None: n_args.append(body)

        try:
            return target(*n_args, **kwargs)
        except TypeError:
            return target(*args, **kwargs)

    setattr(wrapper, "__patched__", True)
    setattr(mod, "memory_upsert", wrapper)
    log.info("[upsert_callsites_overlay] installed")

_apply()