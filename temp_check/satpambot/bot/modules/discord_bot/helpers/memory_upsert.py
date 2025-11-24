import json
import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


async def upsert_pinned_memory(bot, guild_id: int, channel_id: int, title: str, payload=None, max_keep: int = 1):
    """Singleton pin updater.

    - If a pinned message from this bot with the same *title* already exists in the
      target channel/thread, edit that message in place instead of sending a new one.
    - Otherwise, create a new message and pin it.
    - Keeps at most ``max_keep`` pins from this bot for this title (default 1).
    """
    import json
    import logging
    log = logging.getLogger(__name__)

    try:
        # Resolve channel
        ch = bot.get_channel(channel_id)
        if ch is None:
            ch = await bot.fetch_channel(channel_id)

        # Build content
        desc = ""
        embed = None
        try:
            from discord import Embed  # type: ignore
            embed = Embed(title=title)
            if payload is not None:
                txt = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
                if len(txt) > 3900:
                    txt = txt[:3900] + "\n... (truncated)"
                desc = f"""```json\n{txt}\n```"""
            embed.description = desc or "—"
        except Exception:
            # Fallback to plain text if embed not available
            embed = None
            if payload is not None:
                try:
                    desc = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                    if len(desc) > 1900:
                        desc = desc[:1900] + "\n... (truncated)"
                except Exception:
                    desc = str(payload)[:1900]

        # Find existing bot pin with same title
        existing = None
        try:
            pins = await ch.pins()
            def _match_title(m):
                try:
                    # prefer embed title match
                    if getattr(m, "embeds", None):
                        for e in m.embeds:
                            if getattr(e, "title", None) == title:
                                return True
                    # fallback to content startswith
                    mc = (m.content or "").strip()
                    if mc.startswith(title) or title in mc:
                        return True
                except Exception:
                    pass
                return False

            mine = [m for m in pins if getattr(m.author, "id", None) == getattr(bot.user, "id", None) and _match_title(m)]
            mine.sort(key=lambda m: getattr(m, "created_at", 0), reverse=True)
            if mine:
                existing = mine[0]
                # Unpin extras beyond max_keep; leave existing as first
                for m in mine[max_keep:]:
                    try:
                        await m.unpin()
                    except Exception:
                        pass
        except Exception:
            existing = None  # non-fatal

        # Edit-or-send
        if existing is not None:
            if embed:
                await existing.edit(embed=embed)
            else:
                await existing.edit(content=desc or title)
            # Make sure it stays pinned
            try:
                if not getattr(existing, "pinned", True):
                    await existing.pin()
            except Exception:
                pass
            msg = existing
        else:
            msg = await ch.send(embed=embed) if embed else await ch.send(content=desc or title)
            try:
                await msg.pin()
            except Exception:
                pass

        log.info("memory_upsert: pinned '%s' snapshot to channel %s", title, channel_id)
        return True
    except Exception as e:
        log.exception("memory_upsert failed: %s", e)
        return False

