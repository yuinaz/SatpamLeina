from importlib import import_module

_REDIRECT_CODES = {301, 302, 303, 307, 308}

class HttpSmokeClient:
    def __init__(self, app_or_module = "satpambot.dashboard.webui", app_attr: str = "app"):
        if hasattr(app_or_module, "test_client"):
            self.app = app_or_module
        else:
            mod = import_module(app_or_module)
            self.app = getattr(mod, app_attr)
        self.client = self.app.test_client()

    # HTTP verbs
    def get(self, path: str, **kwargs): return self.client.get(path, **kwargs)
    def post(self, path: str, data=None, json=None, **kwargs): return self.client.post(path, data=data, json=json, **kwargs)
    def head(self, path: str, **kwargs): return self.client.head(path, **kwargs)

    @staticmethod
    def text(resp) -> str:
        return resp.get_data(as_text=True)

    def assert_status(self, resp, expected=200, allow_redirect=False, **kwargs):
        code = getattr(resp, "status_code", None)
        if allow_redirect and code in _REDIRECT_CODES:
            return True, code
        if isinstance(expected, (list, tuple, set)):
            ok = code in expected
        else:
            ok = (code == expected)
        return ok, code

    def assert_layout(self, resp, **kwargs):
        try:
            ctype = resp.headers.get("Content-Type", "")
        except Exception:
            ctype = ""
        body = self.text(resp)
        ok = isinstance(body, str) and len(body) > 0
        return ok, ctype
