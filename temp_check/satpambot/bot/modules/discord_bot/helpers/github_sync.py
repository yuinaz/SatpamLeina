# -*- coding: utf-8 -*-
"""helpers.github_sync
Drop-in GitHub client with safe fallback.
- Provides GitHubClient so imports like `from ...helpers.github_sync import GitHubClient` work.
- Reads token/repo from env if not passed explicitly.
- If token/repo not present or HTTP lib missing, methods become no-op but won't crash.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from typing import Any, Dict, Optional

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # will use urllib

try:
    # py3 stdlib fallback
    import urllib.request as _urlreq
    import urllib.error as _urlerr
except Exception:  # pragma: no cover
    _urlreq = None
    _urlerr = None

__all__ = ["GitHubClient", "get_client"]

class GitHubClient:
    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None, base_url: str = "https://api.github.com", user_agent: str = "SatpamBot/ghsync"):
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        self.repo = repo or os.environ.get("GITHUB_REPO") or ""
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self._enabled = bool(self.token and self.repo)
        self._session = requests.Session() if requests else None

    # ---------- internal HTTP ----------
    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json", "User-Agent": self.user_agent}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _http(self, method: str, path: str, data: Optional[bytes] = None, json_body: Optional[Dict[str, Any]] = None, etag: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if etag:
            headers["If-None-Match"] = etag

        if self._session:
            resp = self._session.request(method.upper(), url, headers=headers, json=json_body, data=data, timeout=20)
            status = resp.status_code
            text = resp.text or ""
        elif _urlreq:
            req = _urlreq.Request(url, method=method.upper(), headers=headers)
            if json_body is not None:
                body = json.dumps(json_body).encode("utf-8")
                req.add_header("Content-Type", "application/json")
                resp = _urlreq.urlopen(req, data=body, timeout=20)  # noqa: S310
            elif data is not None:
                resp = _urlreq.urlopen(req, data=data, timeout=20)  # noqa: S310
            else:
                resp = _urlreq.urlopen(req, timeout=20)  # noqa: S310
            status = getattr(resp, "status", 200)
            text = resp.read().decode("utf-8")
        else:  # pragma: no cover
            return {"status": 0, "text": "", "json": None}

        try:
            js = json.loads(text) if text else None
        except Exception:
            js = None
        return {"status": status, "text": text, "json": js}

    # ---------- content (files) ----------
    def _contents_path(self, path: str) -> str:
        return f"/repos/{self.repo}/contents/{path.lstrip('/')}"

    def get_text(self, path: str, ref: str = "main") -> Optional[str]:
        if not self._enabled:
            return None
        r = self._http("GET", self._contents_path(path) + f"?ref={ref}")
        if r["status"] == 200 and isinstance(r["json"], dict):
            content = r["json"].get("content")
            if content:
                return base64.b64decode(content.encode("utf-8")).decode("utf-8", "replace")
        return None

    def get_json(self, path: str, ref: str = "main") -> Optional[Any]:
        txt = self.get_text(path, ref=ref)
        if txt is None:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None

    def upsert_text(self, path: str, text: str, message: str, branch: str = "main", committer: Optional[Dict[str, str]] = None) -> bool:
        """Create or update a text file at path."""
        if not self._enabled:
            return False
        sha = None
        # lookup existing sha
        r0 = self._http("GET", self._contents_path(path) + f"?ref={branch}")
        if r0["status"] == 200 and isinstance(r0["json"], dict):
            sha = r0["json"].get("sha")

        body = {
            "message": message or f"update {path}",
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        if committer:
            body["committer"] = committer

        r = self._http("PUT", self._contents_path(path), json_body=body)
        return r["status"] in (200, 201)

    def upsert_json(self, path: str, obj: Any, message: str, branch: str = "main", committer: Optional[Dict[str, str]] = None, pretty: bool = True) -> bool:
        text = json.dumps(obj, ensure_ascii=False, indent=2 if pretty else None)
        return self.upsert_text(path, text, message=message, branch=branch, committer=committer)

    # ---------- issues ----------
    def _issues_path(self) -> str:
        return f"/repos/{self.repo}/issues"

    def create_issue(self, title: str, body: str = "", labels: Optional[list[str]] = None) -> Optional[int]:
        if not self._enabled:
            return None
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        r = self._http("POST", self._issues_path(), json_body=payload)
        if r["status"] in (200, 201) and isinstance(r["json"], dict):
            return r["json"].get("number")
        return None

    def comment_issue(self, number: int, body: str) -> bool:
        if not self._enabled:
            return False
        r = self._http("POST", f"{self._issues_path()}/{int(number)}/comments", json_body={"body": body})
        return r["status"] in (200, 201)

    def close_issue(self, number: int) -> bool:
        if not self._enabled:
            return False
        r = self._http("PATCH", f"{self._issues_path()}/{int(number)}", json_body={"state": "closed"})
        return r["status"] in (200, 201)

def get_client(token: Optional[str] = None, repo: Optional[str] = None) -> GitHubClient:
    return GitHubClient(token=token, repo=repo)
