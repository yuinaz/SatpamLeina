# dev_server_guard: suppress Flask dev server in production



import logging
import os

try:



    from flask import Flask



except Exception:  # pragma: no cover



    Flask = None







RUN_LOCAL_DEV_ON = os.getenv("RUN_LOCAL_DEV", "0") == "1"







if Flask is not None and not RUN_LOCAL_DEV_ON:



    _orig_run = Flask.run







    def _noop_run(self, *a, **kw):



        logging.getLogger("dev_server_guard").info("[dev-server-guard] Flask.run() suppressed (RUN_LOCAL_DEV!=1)")



        return None







    Flask.run = _noop_run  # type: ignore[attr-defined]



