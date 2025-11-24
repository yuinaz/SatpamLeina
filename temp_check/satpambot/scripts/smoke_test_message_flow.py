# satpambot/scripts/smoke_test_message_flow.py
import os, sys, types, asyncio

# pastikan bisa jalan dari mana saja
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from satpambot.bot.modules.discord_bot.message_handlers import handle_on_message  # type: ignore
except Exception as e:
    print(f"❌ cannot import handle_on_message: {type(e).__name__}: {e}")
    raise

class DummyBot:
    def __init__(self):
        self._calls = 0
    async def process_commands(self, message):
        self._calls += 1

class DummyChannel:
    def __init__(self):
        self.sent = []
    async def send(self, *a, **kw):
        self.sent.append((a, kw))
        return types.SimpleNamespace(id=1)

class DummyAuthor:
    def __init__(self, is_bot=False):
        self.bot = is_bot
        self.id = 1234
        self.name = "tester"

class DummyMessage:
    def __init__(self, content, is_bot=False):
        self.content = content
        self.author = DummyAuthor(is_bot)
        self.channel = DummyChannel()
        self.guild = types.SimpleNamespace(id=1, name="TestGuild")
        self.attachments = []
        self.embeds = []
        self.id = 999

async def main():
    bot = DummyBot()

    # pesan biasa
    try:
        await handle_on_message(bot, DummyMessage("hello", is_bot=False))
        print("OK: handle_on_message(normal) no error")
    except Exception as e:
        print(f"FAIL: normal message -> {type(e).__name__}: {e}")
        raise

    # pesan dari bot (should be ignored)
    try:
        await handle_on_message(bot, DummyMessage("from bot", is_bot=True))
        print("OK: handle_on_message(bot message) no error")
    except Exception as e:
        print(f"FAIL: bot message -> {type(e).__name__}: {e}")
        raise

    print(f"process_commands calls (informational): {bot._calls}")

if __name__ == "__main__":
    asyncio.run(main())
