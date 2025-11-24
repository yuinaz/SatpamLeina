from discord.ext import commands
import asyncio
import importlib
import pkgutil

async def load_all_cogs(bot: commands.Bot, base_package: str = "modules.discord_bot.cogs"):
    try:
        spec = importlib.util.find_spec(base_package)
        if spec is None or not spec.submodule_search_locations:
            return
        package_root = list(spec.submodule_search_locations)[0]
        for _, name, _ in pkgutil.iter_modules([package_root]):
            mod = f"{base_package}.{name}"
            try:
                m = importlib.import_module(mod)
                if hasattr(m, "setup"):
                    await bot.load_extension(mod)
            except Exception:
                pass
    except Exception:
        pass
