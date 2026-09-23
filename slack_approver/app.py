"""Slack diff review + Approve for SDD low-risk PRs.

"View diff & approve" opens a modal showing the PR diff. Approve exists only
inside that modal, so the approver has the diff in front of them. Approving
records a GitHub review *as the clicking human* (GitHub App user token via
device flow), after enforcing:
  - repo is ALLOWED_REPO
  - approver is not the PR author, a commit author, or the person who ran the
    agent (Requested-by trailer); agent PRs without that record are refused
  - PR head has not changed since the card was posted
  - risk class is low (medium/high must be reviewed in GitHub)
  - the whole diff fit in the modal (otherwise review in GitHub)
Every attempt, allowed or refused, is appended to audit.jsonl.
"""
import datetime
import json
import os
import pathlib
import re
import threading
import time

import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

HERE = pathlib.Path(__file__).parent
load_dotenv(HERE / ".env")

ALLOWED_REPO = os.environ["ALLOWED_REPO"]
CLIENT_ID = os.environ["GITHUB_APP_CLIENT_ID"]
# Runtime state lives outside the repo so it can never be committed.
STATE_DIR = pathlib.Path(os.path.expanduser(os.environ.get("SDD_STATE_DIR", "~/.config/sdd-agent")))
STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
TOKENS_FILE = STATE_DIR / "tokens.json"
AUDIT_FILE = STATE_DIR / "audit.jsonl"
GH = "https://api.github.com"
RISK = re.compile(r"^Risk class:\s*(low|medium|high)\s*$", re.I | re.M)
REQUESTED_BY = re.compile(r"^Requested-by:\s*@?([A-Za-z0-9-]+)\s*$", re.M)

app = App(token=os.environ["SLACK_BOT_TOKEN"])


def audit(**event):
    event["at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with AUDIT_FILE.open("a") as f:
        f.write(json.dumps(event) + "\n")
    AUDIT_FILE.chmod(0o600)


def load_tokens():
    return json.loads(TOKENS_FILE.read_text()) if TOKENS_FILE.exists() else {}


def save_token(slack_user, token):
    tokens = load_tokens()
    tokens[slack_user] = token
    TOKENS_FILE.write_text(json.dumps(tokens))
    TOKENS_FILE.chmod(0o600)


def gh(token, method, path, **kwargs):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    return requests.request(method, f"{GH}{path}", headers=headers, timeout=20, **kwargs)


def start_device_flow(slack_user, respond):
    """Link a Slack user to their own GitHub identity; token stays on this machine."""
    r = requests.post("https://github.com/login/device/code",
                      data={"client_id": CLIENT_ID}, headers={"Accept": "application/json"}, timeout=20)
    r.raise_for_status()
    d = r.json()
    respond(response_type="ephemeral", replace_original=False,
            text=(f"First, link your GitHub account: open {d['verification_uri']} and enter "
                  f"*{d['user_code']}*. Then click Approve again."))

    def poll():
        interval = d.get("interval", 5)
        deadline = time.time() + d.get("expires_in", 900)
        while time.time() < deadline:
            time.sleep(interval)
            t = requests.post("https://github.com/login/oauth/access_token", timeout=20,
                              headers={"Accept": "application/json"},
                              data={"client_id": CLIENT_ID, "device_code": d["device_code"],
                                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}).json()
            if "access_token" in t:
                save_token(slack_user, t["access_token"])
                audit(action="link", slack_user=slack_user, result="linked")
                return
            if t.get("error") == "slow_down":
                interval += 5
            elif t.get("error") != "authorization_pending":
                audit(action="link", slack_user=slack_user, result=t.get("error"))
                return

    threading.Thread(target=poll, daemon=True).start()


MAX_FILES = 20
MAX_PATCH_CHARS = 2800  # Slack section text limit is 3000


def linked_token(slack_user, respond):
    token = load_tokens().get(slack_user)
    if token and gh(token, "GET", "/user").status_code != 401:
        return token
    start_device_flow(slack_user, respond)
    return None


def people_involved(token, repo, number, pr):
    """Everyone who wrote or asked for this change: PR author, commit authors, agent requesters."""
    commits = gh(token, "GET", f"/repos/{repo}/pulls/{number}/commits", params={"per_page": 100}).json()
    writers = {pr["user"]["login"].lower()}
    requesters = set()
    for c in commits:
        if (c.get("author") or {}).get("login"):
            writers.add(c["author"]["login"].lower())
        requesters.update(m.group(1).lower() for m in REQUESTED_BY.finditer(c["commit"]["message"]))
    return writers, requesters


def diff_blocks(files):
    """Render PR files as modal blocks. Returns (blocks, complete)."""
    blocks, complete = [], len(files) <= MAX_FILES
    for f in files[:MAX_FILES]:
        patch = f.get("patch") or "(binary or too large to display)"
        if len(patch) > MAX_PATCH_CHARS or "patch" not in f:
            patch, complete = patch[:MAX_PATCH_CHARS] + "\n... truncated", False
        blocks += [
            {"type": "section", "text": {"type": "mrkdwn",
                                         "text": f"*{f['filename']}*  (+{f['additions']} / -{f['deletions']})"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"```{patch}```"}},
        ]
    return blocks, complete


@app.action("view_diff")
def view_diff(ack, body, action, respond, client):
    ack()
    card = json.loads(action["value"])
    slack_user = body["user"]["id"]
    # trigger_id expires in 3s: open a loading view first, fill it in after the GitHub calls.
    view_id = client.views_open(trigger_id=body["trigger_id"], view={
        "type": "modal", "title": {"type": "plain_text", "text": "Loading diff"},
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Fetching the diff from GitHub..."}}],
    })["view"]["id"]

    def show(title, blocks, submit=False, metadata=""):
        view = {"type": "modal", "title": {"type": "plain_text", "text": title[:24]},
                "close": {"type": "plain_text", "text": "Close"}, "blocks": blocks[:100],
                "callback_id": "approve_modal", "private_metadata": metadata}
        if submit:
            view["submit"] = {"type": "plain_text", "text": "Approve"}
        client.views_update(view_id=view_id, view=view)

    def note(text):
        return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]

    if card["repo"] != ALLOWED_REPO:
        return show("Not allowed", note(f"{card['repo']} is not an allowed repository."))
    token = linked_token(slack_user, respond)
    if not token:
        return show("Link GitHub first", note("Check the message I just sent you, link GitHub, then reopen."))

    repo, number = card["repo"], int(card["pr"])
    pr = gh(token, "GET", f"/repos/{repo}/pulls/{number}").json()
    files = gh(token, "GET", f"/repos/{repo}/pulls/{number}/files", params={"per_page": 100}).json()
    blocks, complete = diff_blocks(files)
    _, requesters = people_involved(token, repo, number, pr)
    audit(action="view_diff", slack_user=slack_user, repo=repo, pr=number, sha=card["sha"],
          files=len(files), complete=complete)

    header = note(f"*<{pr['html_url']}|#{number} {pr['title']}>*\nAuthor: {pr['user']['login']} | "
                  f"Commit `{card['sha'][:7]}` | {len(files)} file(s)"
                  + (f"\nAgent run requested by: {', '.join(sorted(requesters))}" if requesters else ""))
    if not complete:
        return show("Review in GitHub", header + blocks + note(
            ":warning: This diff is too large to show in full here, so it can't be approved from Slack. "
            f"<{pr['html_url']}/files|Review it in GitHub.>"))
    footer = note("_Approving records a GitHub review under your own account for this exact commit._")
    show(f"PR #{number} diff", header + [{"type": "divider"}] + blocks + footer,
         submit=True, metadata=json.dumps({**card, "channel": body["channel"]["id"]}))


@app.view("approve_modal")
def approve_modal(ack, body, view, client):
    card = json.loads(view["private_metadata"])
    slack_user = body["user"]["id"]
    repo, number, card_sha = card["repo"], int(card["pr"]), card["sha"]

    def refuse(reason, **extra):
        audit(action="approve", slack_user=slack_user, repo=repo, pr=number, result="refused",
              reason=reason, **extra)
        ack(response_action="update", view={
            "type": "modal", "title": {"type": "plain_text", "text": "Not approved"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": f":no_entry: {reason}"}}]})

    token = load_tokens().get(slack_user)
    if not token:
        return refuse("your GitHub account is not linked.")
    login = gh(token, "GET", "/user").json()["login"]
    pr = gh(token, "GET", f"/repos/{repo}/pulls/{number}").json()
    author = pr["user"]["login"]
    risk = (RISK.search(pr.get("body") or "") or [None, None])[1]

    if repo != ALLOWED_REPO:
        return refuse(f"{repo} is not an allowed repository.", approver=login)
    if pr["state"] != "open":
        return refuse(f"PR #{number} is {pr['state']}.", approver=login)
    writers, requesters = people_involved(token, repo, number, pr)
    if pr["user"]["type"] == "Bot" and not requesters:
        return refuse("this agent PR has no Requested-by record, so who ran the agent is unknown.",
                      approver=login)
    if login.lower() in writers:
        return refuse("you authored this PR or one of its commits. Approver must differ from author.",
                      approver=login)
    if login.lower() in requesters:
        return refuse("you ran the agent that wrote this PR. The person who prompts the AI cannot approve it.",
                      approver=login)
    if pr["head"]["sha"] != card_sha:
        return refuse("the PR changed after this card was posted. Re-review the new diff.", approver=login)
    if (risk or "").lower() != "low":
        return refuse(f"risk class is {risk or 'unknown'}. Medium/high risk must be reviewed in GitHub.",
                      approver=login)

    r = gh(token, "POST", f"/repos/{repo}/pulls/{number}/reviews",
           json={"event": "APPROVE", "commit_id": card_sha,
                 "body": f"Approved via Slack (SDD Review Bot) for commit {card_sha[:7]} "
                         f"after viewing the diff in Slack. Low-risk route."})
    if r.status_code >= 300:
        return refuse(f"GitHub rejected the review ({r.status_code}): {r.json().get('message')}",
                      approver=login)

    ack()
    audit(action="approve", slack_user=slack_user, approver=login, author=author,
          requested_by=sorted(requesters), repo=repo, pr=number, sha=card_sha, risk=risk,
          result="approved", review_id=r.json()["id"])
    client.chat_postMessage(channel=card["channel"],
                            text=f":white_check_mark: PR #{number} approved in GitHub by *{login}* "
                                 f"(commit `{card_sha[:7]}`, diff viewed in Slack). "
                                 f"Merge still requires all checks to pass.")


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
