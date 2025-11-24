import asyncio
import logging
from typing import Optional
try:
    import discord
except Exception:
    discord = None  # type: ignore

log = logging.getLogger(__name__)

class SendQueue:
    """Durable-ish send queue (in-memory stub)."""
    def __init__(self, bot, rate_interval: float = 0.9):
        self.bot = bot
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker: Optional[asyncio.Task] = None
        self.rate_interval = rate_interval

    async def start(self):
        if self._worker is None:
            self._worker = asyncio.create_task(self._run(), name="send-queue-worker")

    async def stop(self):
        if self._worker:
            self._worker.cancel()
            self._worker = None

    async def enqueue(self, channel_id: int, **send_kwargs):
        await self.queue.put((channel_id, send_kwargs))

    async def _run(self):
        while True:
            channel_id, send_kwargs = await self.queue.get()
            try:
                ch = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
                if hasattr(ch, 'send'):
                    await asyncio.sleep(self.rate_interval)
                    await ch.send(**send_kwargs)
            except Exception as e:
                log.warning("send-queue: send failed: %r", e)
            finally:
                self.queue.task_done()
