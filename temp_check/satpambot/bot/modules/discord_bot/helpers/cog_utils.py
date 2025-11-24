import inspect

async def safe_add_cog(bot, cog):
    """Await add_cog if the discord.py version makes it a coroutine.
    Idempotent: if add_cog returns a coroutine, await it; otherwise do nothing.
    """
    ret = bot.add_cog(cog)
    if inspect.iscoroutine(ret):
        return await ret
    return ret



from discord.ext import commands
async def setup(bot: commands.Bot):
    # auto-register Cog classes defined in this module
    for _name, _obj in globals().items():
        try:
            if isinstance(_obj, type) and issubclass(_obj, commands.Cog):
                await bot.add_cog(_obj(bot))
        except Exception:
            continue
