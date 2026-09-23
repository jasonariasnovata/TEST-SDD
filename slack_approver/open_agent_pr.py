"""Open a low-risk implementation PR as the GitHub App (the 'coding agent').

Usage: python slack_approver/open_agent_pr.py <gate_pr_number>

Commits carry a "Requested-by:" trailer naming who ran the agent, so the
approver can refuse that person. In the sandbox it is the local gh login;
in production it should come from the platform that starts the agent.
"""
import base64
import subprocess
import os
import pathlib
import sys
import time

import jwt
import requests
from dotenv import load_dotenv

HERE = pathlib.Path(__file__).parent
load_dotenv(HERE / ".env")
REPO = os.environ["ALLOWED_REPO"]
GH = "https://api.github.com"


def installation_token():
    key = pathlib.Path(os.path.expanduser(os.environ["GITHUB_APP_PRIVATE_KEY_PATH"])).read_text()
    now = int(time.time())
    app_jwt = jwt.encode({"iat": now - 60, "exp": now + 540, "iss": os.environ["GITHUB_APP_ID"]},
                         key, algorithm="RS256")
    h = {"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json"}
    inst = requests.get(f"{GH}/repos/{REPO}/installation", headers=h, timeout=20)
    inst.raise_for_status()
    tok = requests.post(f"{GH}/app/installations/{inst.json()['id']}/access_tokens", headers=h, timeout=20)
    tok.raise_for_status()
    return tok.json()["token"]


def requester():
    login = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True).stdout.strip()
    if not login:
        sys.exit("Cannot tell who is running the agent (gh not logged in); refusing to open a PR.")
    return login


def main(gate_pr):
    requested_by = requester()
    h = {"Authorization": f"Bearer {installation_token()}", "Accept": "application/vnd.github+json"}
    branch = f"agent/greet-extra-test-{int(time.time())}"
    main_sha = requests.get(f"{GH}/repos/{REPO}/git/ref/heads/main", headers=h, timeout=20).json()["object"]["sha"]
    requests.post(f"{GH}/repos/{REPO}/git/refs", headers=h, timeout=20,
                  json={"ref": f"refs/heads/{branch}", "sha": main_sha}).raise_for_status()
    test = ('from src.app.greeting import greet\n\n\n'
            'def test_title_case_single_word():\n'
            '    assert greet("grace") == "Hello, Grace!"\n')
    requests.put(f"{GH}/repos/{REPO}/contents/tests/test_greeting_agent.py", headers=h, timeout=20,
                 json={"message": f"Add single-word title-case test (SDD-1)\n\nRequested-by: {requested_by}",
                       "branch": branch,
                       "content": base64.b64encode(test.encode()).decode()}).raise_for_status()
    body = (f"Jira: SDD-1\nApproved artifact PR: #{gate_pr}\nRisk class: low\n\n"
            f"## Summary\nAgent-authored, run by @{requested_by}: adds a single-word test for R1.\n\n"
            "## Deviations from plan\nNone\n\n## Verification\n```bash\npython -m pytest -q\n```\n")
    pr = requests.post(f"{GH}/repos/{REPO}/pulls", headers=h, timeout=20,
                       json={"title": "Agent: add single-word title-case test", "head": branch,
                             "base": "main", "body": body})
    pr.raise_for_status()
    print(pr.json()["html_url"])


if __name__ == "__main__":
    main(int(sys.argv[1]))
