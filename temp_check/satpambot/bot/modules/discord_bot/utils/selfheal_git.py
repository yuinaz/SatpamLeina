# -*- coding: utf-8 -*-
import os, subprocess, logging, json, base64
from typing import Optional, List, Dict
import httpx

LOG = logging.getLogger(__name__)

def run(cmd: list, cwd: Optional[str]=None, env: Optional[dict]=None, timeout: int=60) -> int:
    LOG.info("[selfheal.git] $ %s", " ".join(cmd))
    p = subprocess.Popen(cmd, cwd=cwd, env=env or os.environ.copy(),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        out = p.communicate(timeout=timeout)[0]
    except subprocess.TimeoutExpired:
        p.kill()
        out = "(timeout)"
    LOG.info("[selfheal.git] out: %s", out[:1000])
    return p.returncode

def ensure_user(repo_dir: str, name: str="selfheal-bot", email: str="selfheal@local"):
    run(["git", "config", "user.name", name], cwd=repo_dir)
    run(["git", "config", "user.email", email], cwd=repo_dir)

def current_branch(repo_dir: str) -> str:
    try:
        import subprocess
        out = subprocess.check_output(["git","rev-parse","--abbrev-ref","HEAD"], cwd=repo_dir, text=True).strip()
        return out
    except Exception:
        return "unknown"

def checkout_branch(repo_dir: str, branch: str):
    # create if not exists
    code = run(["git", "checkout", "-B", branch], cwd=repo_dir)
    if code != 0:
        raise RuntimeError("git checkout failed")

def add_commit_push(repo_dir: str, message: str, branch: Optional[str]=None, remote: str="origin"):
    run(["git","add","-A"], cwd=repo_dir)
    run(["git","commit","-m", message], cwd=repo_dir)
    if branch:
        run(["git","push", remote, branch], cwd=repo_dir)
    else:
        run(["git","push"], cwd=repo_dir)

def pull(repo_dir: str, remote: str="origin", branch: Optional[str]=None):
    if branch:
        run(["git","pull", remote, branch], cwd=repo_dir)
    else:
        run(["git","pull", remote], cwd=repo_dir)

# --- GitHub simple helpers (contents & PR) ---
def gh_update_file(owner_repo: str, path: str, content_bytes: bytes, message: str, branch: str, token: str):
    url = f"https://api.github.com/repos/{owner_repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    # read current sha if exists
    sha = None
    with httpx.Client(timeout=30) as cli:
        r = cli.get(url, params={"ref": branch}, headers=headers)
        if r.status_code == 200:
            sha = r.json().get("sha")
        payload = {
            "message": message,
            "content": base64.b64encode(content_bytes).decode("ascii"),
            "branch": branch,
        }
        if sha: payload["sha"] = sha
        r2 = cli.put(url, headers=headers, json=payload)
        r2.raise_for_status()
        return r2.json()

def gh_create_pr(owner_repo: str, head_branch: str, base_branch: str, title: str, body: str, token: str):
    url = f"https://api.github.com/repos/{owner_repo}/pulls"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    data = {"title": title, "head": head_branch, "base": base_branch, "body": body}
    with httpx.Client(timeout=30) as cli:
        r = cli.post(url, headers=headers, json=data)
        r.raise_for_status()
        return r.json()
