#!/usr/bin/env python3
"""一条命令做完：建仓库 → 推代码 → 触发 iOS 构建 → 等完成 → 下载 ipa。

只用标准库（urllib），不需要 requests / gh CLI。

用法:
  # 1) 去 https://github.com/settings/tokens 建一个 classic token，勾 repo + workflow
  # 2) 设环境变量后运行
  set GITHUB_TOKEN=ghp_xxxxxxxx
  python scripts/gh_build_ios.py --repo gulu-ios

  # 或者把 token 写进同目录的 .gh_token 文件（已被 .gitignore 忽略）
  python scripts/gh_build_ios.py --repo gulu-ios --token-file .gh_token

参数:
  --repo      仓库名（默认 gulu-ios）
  --owner     用户名，省略则用 token 对应账号
  --private   建成私有仓库
  --branch    分支（默认 main）
  --timeout   等待构建的分钟数（默认 40）
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

API = "https://api.github.com"
ROOT = Path(__file__).resolve().parent.parent


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class GH:
    def __init__(self, token: str) -> None:
        self.token = token

    def req(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        accept: str = "application/vnd.github+json",
        raw: bool = False,
    ):
        url = path if path.startswith("http") else API + path
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", f"Bearer {self.token}")
        r.add_header("Accept", accept)
        r.add_header("X-GitHub-Api-Version", "2022-11-28")
        r.add_header("User-Agent", "gulu-ios-builder")
        if data:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                payload = resp.read()
                return payload if raw else (json.loads(payload) if payload else {})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from None

    def get(self, path: str, **kw):
        return self.req("GET", path, **kw)

    def post(self, path: str, body: dict | None = None):
        return self.req("POST", path, body or {})


def read_token(args) -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok and args.token_file:
        p = Path(args.token_file)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            tok = p.read_text(encoding="utf-8").strip()
    if not tok:
        log("缺少 token。设 GITHUB_TOKEN 环境变量，或用 --token-file 指向一个只含 token 的文件")
        sys.exit(2)
    return tok


def ensure_repo(gh: GH, owner: str, repo: str, private: bool) -> str:
    """仓库存在就直接用，不存在就建。返回 clone_url。"""
    try:
        info = gh.get(f"/repos/{owner}/{repo}")
        log(f"仓库已存在: {info['full_name']}")
        return info["clone_url"]
    except RuntimeError as e:
        if "HTTP 404" not in str(e):
            raise
    log(f"创建仓库 {owner}/{repo} (private={private})")
    body = {
        "name": repo,
        "private": private,
        "auto_init": False,
        "description": "咕噜咕噜 iOS 客户端重建工程",
    }
    info = gh.post("/user/repos", body)
    return info["clone_url"]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )


def push_code(gh: GH, clone_url: str, owner: str, branch: str) -> None:
    # 用 token 走 https，不能在日志里泄露 token
    auth_url = clone_url.replace("https://", f"https://x-access-token:{gh.token}@")

    has_git = (ROOT / ".git").exists()
    if not has_git:
        log("初始化本地 git 仓库")
        git("init", "-q", "-b", branch)
        git("add", "-A")
        git("commit", "-q", "-m", "咕噜咕噜 iOS 客户端重建工程")

    remotes = git("remote").stdout.split()
    if "origin" in remotes:
        git("remote", "set-url", "origin", auth_url)
    else:
        git("remote", "add", "origin", auth_url)

    log(f"推送到 {owner} 的 {branch} 分支")
    r = git("push", "-u", "origin", f"HEAD:{branch}", "--force")
    if r.returncode != 0:
        # 把 token 从错误输出里抹掉再抛
        err = (r.stderr or "").replace(gh.token, "<TOKEN>")
        raise RuntimeError(f"git push 失败:\n{err}")
    log("推送完成")


def trigger_workflow(gh: GH, owner: str, repo: str, branch: str, api_base: str) -> int:
    wf_file = "ios-unsigned.yml"
    wf_path = f"/repos/{owner}/{repo}/actions/workflows/{wf_file}"

    try:
        gh.get(wf_path)
    except RuntimeError as e:
        if "HTTP 404" not in str(e):
            raise
        raise RuntimeError(
            f"GitHub 看不到 {wf_file}。确认 .github/workflows/{wf_file} 已推送，"
            f"且 token 勾了 workflow 权限"
        ) from None

    log("触发 workflow_dispatch")
    gh.post(
        f"{wf_path}/dispatches",
        {"ref": branch, "inputs": {"api_base": api_base}},
    )

    # dispatch 后要等一会儿才会出现新 run
    log("等待 run 出现…")
    for _ in range(30):
        time.sleep(4)
        runs = gh.get(
            f"/repos/{owner}/{repo}/actions/workflows/{wf_file}/runs"
            f"?event=workflow_dispatch&branch={branch}&per_page=5"
        )
        items = runs.get("workflow_runs") or []
        if items:
            run = items[0]
            if run["status"] in ("queued", "in_progress", "waiting", "requested"):
                log(f"run #{run['run_number']} id={run['id']} 已启动")
                return int(run["id"])
            log(f"run #{run['run_number']} id={run['id']} 状态={run['status']}")
            return int(run["id"])
    raise RuntimeError("等了 2 分钟没等到 run，去 Actions 页面看看")


def wait_run(gh: GH, owner: str, repo: str, run_id: int, timeout_min: int) -> dict:
    deadline = time.time() + timeout_min * 60
    last = ""
    while time.time() < deadline:
        run = gh.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}")
        status, concl = run["status"], run.get("conclusion")
        line = f"{status}/{concl or '-'}"
        if line != last:
            log(f"构建状态: {line}")
            last = line
        if status == "completed":
            return run
        time.sleep(15)
    raise RuntimeError(f"超过 {timeout_min} 分钟还没结束，去 Actions 页面看")


def fetch_artifact(gh: GH, owner: str, repo: str, run_id: int, out_dir: Path) -> list[Path]:
    arts = gh.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts")
    items = arts.get("artifacts") or []
    if not items:
        raise RuntimeError("这次 run 没有产出 artifact")

    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for a in items:
        log(f"下载 artifact: {a['name']} ({a['size_in_bytes']} B)")
        blob = gh.get(a["archive_download_url"], raw=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for name in z.namelist():
                if name.endswith(".ipa"):
                    target = out_dir / Path(name).name
                    target.write_bytes(z.read(name))
                    log(f"  -> {target} ({target.stat().st_size} B)")
                    saved.append(target)
    if not saved:
        raise RuntimeError("artifact 里没有 .ipa")
    return saved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="gulu-ios")
    ap.add_argument("--owner", default="")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--timeout", type=int, default=40)
    ap.add_argument("--token-file", default="")
    ap.add_argument("--api-base", default="https://glgl.tv")
    ap.add_argument("--out", default="build/ios/ipa")
    ap.add_argument("--skip-build", action="store_true", help="只推代码不触发构建")
    args = ap.parse_args()

    tok = read_token(args)
    gh = GH(tok)

    if not args.owner:
        me = gh.get("/user")
        args.owner = me["login"]
        log(f"token 账号: {args.owner}")

    clone_url = ensure_repo(gh, args.owner, args.repo, args.private)
    push_code(gh, clone_url, args.owner, args.branch)

    if args.skip_build:
        log("已跳过构建（--skip-build）")
        return 0

    run_id = trigger_workflow(gh, args.owner, args.repo, args.branch, args.api_base)
    run = wait_run(gh, args.owner, args.repo, run_id, args.timeout)

    if run.get("conclusion") != "success":
        raise RuntimeError(
            f"构建失败: {run.get('conclusion')}\n查看日志: {run['html_url']}"
        )

    out_dir = ROOT / args.out
    ipas = fetch_artifact(gh, args.owner, args.repo, run_id, out_dir)
    log("完成：")
    for p in ipas:
        log(f"  {p}")
    log("")
    log("下一步安装：Sideloadly 拖入 ipa → 填 Apple ID → Start → 手机上信任证书")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        log(f"失败: {e}")
        raise SystemExit(1)
