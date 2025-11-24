import asyncio, discord

async def _presence_loop(bot):
    while True:
        try:
            await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Menjaga Server Dari Scam"))
        except Exception:
            pass
        await asyncio.sleep(60)

def run_background_tasks(bot):
    bot.loop.create_task(_presence_loop(bot))
