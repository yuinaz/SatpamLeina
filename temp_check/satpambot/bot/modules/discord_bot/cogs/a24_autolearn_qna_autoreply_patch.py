import logging, asyncio
async def setup(bot):
    log = logging.getLogger(__name__)

    async def _apply():
        await asyncio.sleep(1)  # tunggu cog lain init
        target = None
        for name, cog in bot.cogs.items():
            # cari yang mendekati nama a24_autolearn_qna_autoreply
            if 'autolearn' in name.lower() and 'qna' in name.lower():
                target = cog
                break
        if not target:
            log.debug('[autolearn-patch] target cog not found')
            return

        orig_ask = getattr(target, '_ask_llm', None)
        if not orig_ask:
            log.debug('[autolearn-patch] _ask_llm not found; skip')
            return

        async def wrapped(question, prefer=None):
            # 1st try (original)
            try:
                if prefer is None:
                    ans = await orig_ask(question)
                else:
                    ans = await orig_ask(question, prefer=prefer)
            except TypeError:
                ans = await orig_ask(question)
            except Exception as e:
                ans = None
                log.debug('[autolearn-patch] primary _ask_llm err: %r', e)

            if ans:
                setattr(target, '_last_provider', prefer or getattr(target, '_last_provider', 'LLM'))
                return ans

            # Fallback ke kedua provider secara eksplisit
            for pref in ('gemini', 'groq'):
                try:
                    ans2 = await orig_ask(question, prefer=pref)
                    if ans2:
                        setattr(target, '_last_provider', pref)
                        return ans2
                except Exception as e:
                    log.debug('[autolearn-patch] fallback %s err: %r', pref, e)
            return None

        setattr(target, '_ask_llm', wrapped)
        log.info('[autolearn-patch] _ask_llm wrapped with dual-provider fallback')

    asyncio.create_task(_apply())
