import logging
import signal
import sys
import inspect
import asyncio

log = logging.getLogger("minipc_app")

def _resolve_runner():
    """
    Try several entry points so the app is robust across repo layouts:
      1) entry.main()
      2) run_local_minipc.run()
      3) main.main()   (fallback if you use main.py)
    """
    # 1) entry.main
    try:
        import entry  # type: ignore
        if hasattr(entry, "main") and callable(entry.main):
            log.info("Delegating run to entry.main()")
            return entry.main
    except Exception as e:
        log.debug("entry not available: %r", e)

    # 2) run_local_minipc.run
    try:
        import run_local_minipc as rlm  # type: ignore
        if hasattr(rlm, "run") and callable(rlm.run):
            log.info("Delegating run to run_local_minipc.run()")
            return rlm.run
    except Exception as e:
        log.debug("run_local_minipc not available: %r", e)

    # 3) main.main
    try:
        import main  # type: ignore
        if hasattr(main, "main") and callable(main.main):
            log.info("Delegating run to main.main()")
            return main.main
    except Exception as e:
        log.debug("main not available: %r", e)

    raise RuntimeError("No runnable entry found: expected entry.main / run_local_minipc.run / main.main")

def _install_signal_handlers():
    # Graceful Ctrl+C on Windows & Unix
    def _graceful_exit(signum, frame):
        try:
            loop = asyncio.get_running_loop()
            for task in asyncio.all_tasks(loop):
                task.cancel()
        except RuntimeError:
            pass  # no running loop; just fall through
        log.warning("🔻 Received signal %s — shutting down gracefully...", signum)
        sys.exit(0)

    for sig in (getattr(signal, "SIGINT", None),
                getattr(signal, "SIGTERM", None),
                getattr(signal, "SIGBREAK", None)):  # Windows console Ctrl+Break
        if sig is not None:
            try:
                signal.signal(sig, _graceful_exit)
            except Exception:
                pass

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s"
    )

    try:
        _install_signal_handlers()
        runner = _resolve_runner()

        if inspect.iscoroutinefunction(runner):
            # Runner is an async function
            asyncio.run(runner())
            return

        result = runner()
        if inspect.isawaitable(result):
            asyncio.run(result)
    except KeyboardInterrupt:
        log.warning("🔻 KeyboardInterrupt — exit.")
    except Exception as e:
        log.exception("💥 Unhandled error bubbled up from main(): %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
