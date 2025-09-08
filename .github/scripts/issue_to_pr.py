#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import textwrap
import subprocess
from pathlib import Path
import urllib.request
import urllib.error

# ---------- Paths & Env ----------
REPO_ROOT = Path(__file__).resolve().parents[2]

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
ISSUE_BODY = os.environ.get("ISSUE_BODY", "").strip()
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "").strip()

assert OPENAI_API_KEY, "Missing OPENAI_API_KEY"
assert ISSUE_BODY, "Missing ISSUE_BODY"
assert ISSUE_NUMBER, "Missing ISSUE_NUMBER"

# ---------- Prompts ----------
SYSTEM_PROMPT = (
    "You are a senior iOS engineer. Produce a minimal, testable Xcode project "
    "with a shared scheme and XCTest unit tests. Return ONLY JSON."
)

USER_PROMPT = textwrap.dedent(f"""
需求（來自 Issue #{ISSUE_NUMBER}）：
{ISSUE_BODY}

目標（請嚴格遵守）：
- 產出 iOS App 專案，專案/方案名稱固定為 **AutoDevApp**
- 一定要有 **Shared Scheme** 檔案：AutoDevApp.xcodeproj/xcshareddata/xcschemes/AutoDevApp.xcscheme
- 使用 SwiftUI + MVVM（最小可行）
- 提供 **XCTest 單元測試**（針對 ViewModel 純邏輯）
- 在 iPhone 15 模擬器以 `xcodebuild -scheme AutoDevApp test` 可通過
- JSON 以 UTF-8 傳回，**不得使用省略號或佔位符**（例如 "..."、"YOUR_BLUEPRINT_ID"）。
- 回傳 JSON（只回 JSON），格式如下：
{{
  "branch": "簡短分支名（小寫連字號）",
  "commit_message": "第一次提交訊息",
  "pr_title": "PR 標題",
  "pr_body": "PR 說明",
  "files": [
    {{"path":"AutoDevApp.xcodeproj/project.pbxproj","content":"完整內容"}},
    {{"path":"AutoDevApp/App/AutoDevAppApp.swift","content":"..."}},
    {{"path":"AutoDevApp/App/ContentView.swift","content":"..."}},
    {{"path":"AutoDevAppTests/AutoDevAppTests.swift","content":"..."}},
    {{"path":"AutoDevApp.xcodeproj/xcshareddata/xcschemes/AutoDevApp.xcscheme","content":"完整內容"}}
  ]
}}
""").strip()

# ---------- OpenAI Call ----------
def call_openai(messages):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        data=json.dumps({
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.2
        }).encode("utf-8")
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"OpenAI HTTPError {e.code}: {body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"OpenAI URLError: {e}")

# ---------- Helpers ----------
def extract_json(text: str) -> str:
    """
    Remove markdown code fences like ```json ... ``` and return the inner JSON.
    Fallback: take substring from first '{' to last '}'.
    """
    # 專抓 ```json ... ```
    m = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    # 任何 ``` 語法
    m = re.search(r"```(?:\w+)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    # 退而求其次：第一個 { 到最後一個 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text.strip()

def run(cmd, cwd=None, check=True):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or REPO_ROOT, check=check)

def ensure_git_identity():
    # 在 runner 內可能無 git identity；設定一個 bot 身份
    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])

def create_or_checkout_branch(branch: str):
    # 試創建；若已存在則 checkout
    try:
        run(["git", "checkout", "-b", branch])
    except subprocess.CalledProcessError:
        run(["git", "checkout", branch])

# ---------- Main ----------
print("🔵 Sending request to OpenAI API…")
resp = call_openai([
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": USER_PROMPT}
])
reply = resp["choices"][0]["message"]["content"]

clean = extract_json(reply)
print("🟢 OpenAI reply (prefix):", clean[:200].replace("\n", " "), "…")

try:
    plan = json.loads(clean)
except Exception as e:
    raise SystemExit("LLM did not return valid JSON after cleanup. See prefix above.") from e

branch = plan.get("branch", "auto-commit").strip()
branch = re.sub(r"[^a-z0-9\-]", "-", branch.lower()) or "auto-commit"
commit_message = plan.get("commit_message", "feat: initial app")
pr_title = plan.get("pr_title", commit_message)
pr_body = plan.get("pr_body", "")
files = plan.get("files", [])

if not files:
    raise SystemExit("LLM JSON has no 'files' array.")

# 寫檔前切分支
ensure_git_identity()
create_or_checkout_branch(branch)

# 寫入檔案
for f in files:
    path = REPO_ROOT / f["path"]
    content = f.get("content", "")
    path.parent.mkdir(parents=True, exist_ok=True)
    # 確保以 UTF-8 落檔，並保留換行
    path.write_text(content, encoding="utf-8")

# Commit + Push
run(["git", "add", "-A"])
run(["git", "commit", "-m", commit_message])
run(["git", "push", "-u", "origin", branch])

# 建 PR（用 GITHUB_TOKEN）
env = os.environ.copy()
if GH_TOKEN:
    env["GH_TOKEN"] = GH_TOKEN

print("🔵 Creating pull request…")
subprocess.run(
    ["gh", "pr", "create", "--title", pr_title, "--body", pr_body, "--base", "main", "--head", branch],
    cwd=REPO_ROOT,
    check=True,
    env=env
)

print("✅ PR created from issue.")
