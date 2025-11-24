import logging, random
import discord
from .sticker_learner import StickerLearner
try:
    from ...config import envcfg
except Exception:
    envcfg = None

log = logging.getLogger("satpambot.sticker_helper")

async def _resolve_sticker(bot, sticker_id: int):
    for g in bot.guilds:
        try:
            try:
                stickers = await g.fetch_stickers()
            except Exception:
                stickers = getattr(g, "stickers", []) or []
            for s in stickers:
                if int(getattr(s, "id", 0)) == int(sticker_id):
                    return s
        except Exception:
            continue
    try:
        return await bot.fetch_sticker(int(sticker_id))
    except Exception:
        return None

async def send_sticker_smart(message: discord.Message, bot, emotion: str, style_summary):
    if not envcfg or not getattr(envcfg, "stickers_enabled", None) or not envcfg.stickers_enabled():
        return False
    ch = message.channel
    guild_id = getattr(message.guild, "id", None)
    has_user_sticker = bool(getattr(message, "stickers", None))

    base_rate = getattr(envcfg, "sticker_base_rate", lambda: 0.25)()
    min_rate  = getattr(envcfg, "sticker_min_rate", lambda: 0.05)()
    max_rate  = getattr(envcfg, "sticker_max_rate", lambda: 0.90)()

    learner = StickerLearner()
    rate = learner.recommend_rate(base_rate, style_summary, has_user_sticker, emotion, min_rate, max_rate)
    if random.random() > rate:
        learner.log_event(message.author.id, emotion, used=False, success=False,
                          guild_id=guild_id, dm=isinstance(ch, discord.DMChannel),
                          has_user_sticker=has_user_sticker, style_summary=style_summary)
        return False

    chosen = None
    try:
        env_ids = [int(x) for x in envcfg.stickers_for(emotion)]
        if env_ids:
            chosen = int(random.choice(env_ids))
    except Exception:
        chosen = None
    if chosen is None:
        try: learner.update_catalog_from_bot(bot)
        except Exception: pass
        chosen = learner.pick_sticker(bot, guild_id, emotion)

    if not chosen:
        learner.log_event(message.author.id, emotion, used=False, success=False,
                          guild_id=guild_id, dm=isinstance(ch, discord.DMChannel),
                          has_user_sticker=has_user_sticker, style_summary=style_summary)
        return False

    try:
        s = await _resolve_sticker(bot, int(chosen))
        if s:
            m = await ch.send(stickers=[s])
            learner.log_event(message.author.id, emotion, used=True, success=True,
                              guild_id=guild_id, dm=isinstance(ch, discord.DMChannel),
                              has_user_sticker=has_user_sticker, style_summary=style_summary)
            learner.record_sent_message(m.id, int(chosen), guild_id, getattr(ch, "id", 0), emotion)
            return True
        else:
            learner.log_event(message.author.id, emotion, used=True, success=False,
                              guild_id=guild_id, dm=isinstance(ch, discord.DMChannel),
                              has_user_sticker=has_user_sticker, style_summary=style_summary)
            return False
    except Exception as e:
        log.debug("send sticker failed: %s", e)
        learner.log_event(message.author.id, emotion, used=True, success=False,
                          guild_id=guild_id, dm=isinstance(ch, discord.DMChannel),
                          has_user_sticker=has_user_sticker, style_summary=style_summary)
        return False
