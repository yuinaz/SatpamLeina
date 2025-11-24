"""
run_minipc.py — Single-file runner untuk lokal/MiniPC
- Auto-load SatpamBot.env (kalau ada)
- Tidak mengubah main.py lama
- Graceful shutdown saat Ctrl+C / SIGTERM
- Aman dipakai di Windows & Linux
Usage: python run_minipc.py
"""
from __future__ import annotations

import os
import sys
import signal
import asyncio
import logging
from pathlib import Path

log = logging.getLogger("runner.minipc")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(levelname)s:%(name)s:%(message)s",
)

def load_env_file():
    # Cari SatpamBot.env di cwd, parent, atau lewat arg --env
    env_name = "SatpamBot.env"
    cli_env = None
    for i, a in enumerate(sys.argv):
        if a == "--env" and i+1 < len(sys.argv):
            cli_env = sys.argv[i+1]
            break

    candidates = [
        Path(cli_env) if cli_env else None,
        Path.cwd() / env_name,
        Path.cwd().parent / env_name,
    ]
    for p in candidates:
        if p and p.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(p, override=False)
                print(f"✅ Loaded env file: {p.name}")
                return True
            except Exception:
                # Fallback kecil bila python-dotenv tak terpasang
                try:
                    for line in p.read_text(encoding="utf-8").splitlines():
                        if not line or line.strip().startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
                    print(f"✅ Loaded env file (fallback): {p.name}")
                    return True
                except Exception as e:
                    print(f"⚠️  Gagal load {p}: {e}")
    print("ℹ️  Tidak menemukan SatpamBot.env — lanjut dengan env proses saat ini.")
    return False


# Graceful shutdown helper
_shutdown_event: asyncio.Event | None = None

def _kickoff_shutdown(signame: str):
    print(f"INFO:graceful_shutdown:[shutdown] starting graceful shutdown ({signame}) ...")
    if _shutdown_event is not None:
        _shutdown_event.set()

async def main_async():
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # (Opsional) beri penanda runtime utk modul2 yg butuh
    os.environ.setdefault("SATPAMBOT_RUNTIME", "local")
    os.environ.setdefault("GRACEFUL_SHUTDOWN", "1")

    # Pasang signal handler (Linux/macOS). Di Windows, SIGINT cukup.
    loop = asyncio.get_running_loop()
    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is None: 
            continue
        try:
            loop.add_signal_handler(sig, _kickoff_shutdown, sig.name)
        except NotImplementedError:
            # Windows sebelum Python 3.8: fallback
            pass

    import main as _entry  # tidak mengubah main.py

    # Jalankan _entry.main() non-blocking di task, supaya kita bisa tunggu shutdown
    async def _entry_wrapper():
        try:
            _entry.main()
        except KeyboardInterrupt:
            # sudah ditangani ke _shutdown_event
            pass
        except SystemExit:
            pass
        except Exception:
            log.exception("entry.main crash")

    task = asyncio.create_task(asyncio.to_thread(_entry_wrapper))

    # Tunggu sinyal shutdown
    try:
        await _shutdown_event.wait()
    finally:
        # Coba hentikan discord bot dengan rapi bila tersedia
        # Banyak project punya hook sendiri; kita coba yang umum.
        # Jika tidak ada, biarkan proses selesai alami.
        try:
            from satpambot.bot.modules.discord_bot import shim_runner  # type: ignore
            bot = getattr(shim_runner, "BOT_INSTANCE", None)
            if bot and hasattr(bot, "close"):
                await bot.close()
        except Exception:
            pass

        # Beri waktu sedikit utk tugas latar belakang
        await asyncio.sleep(0.2)
        for t in asyncio.all_tasks():
            if t is not asyncio.current_task():
                t.cancel()
        try:
            await asyncio.gather(*[t for t in asyncio.all_tasks() if t is not asyncio.current_task()], return_exceptions=True)
        except Exception:
            pass

def main():
    load_env_file()
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        # double Ctrl+C
        print("INFO:graceful_shutdown:[shutdown] forced exit (KeyboardInterrupt)")
    finally:
        # Exit code 0 agar dianggap clean oleh supervisor/service
        os._exit(0)

if __name__ == "__main__":
    main()
