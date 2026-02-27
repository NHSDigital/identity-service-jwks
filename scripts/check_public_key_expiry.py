"""
Scan JWKS JSON files to detect expiring public keys and create Jira story.

The script searches configured directories (e.g. jwks/paas/prod, jwks/paas/ptl)
for JWKS JSON files and extracts expiry dates from the `kid` field. If a key is
expiring within the configured threshold, a Jira issue is created unless an
existing open issue with the same labelhash already exists.

The environment (PROD or PTL) is inferred from the file path and included in the
execution summary.

For DRYRUN - Set the env DRY_RUN to false
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import date, datetime
from typing import Optional, List

from jira import JIRA
from jira.exceptions import JIRAError

TARGET_DIRS = os.environ.get("TARGET_DIRS")
TARGET_DIRS_LIST = [path.strip() for path in TARGET_DIRS.split(",") if path.strip()]
DAYS_THRESHOLD = 60
JIRA_URL = os.environ.get("JIRA_URL", "").strip()
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "").strip()
JIRA_PROJECT_ID = os.environ.get("JIRA_PROJECT_ID", "").strip()
JIRA_EPIC_KEY = os.environ.get("JIRA_EPIC_KEY", "").strip()
JIRA_BOARD_ID = os.environ.get("JIRA_BOARD_ID", "").strip()

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
GITHUB_STEP_SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def scan_json_files():
    files: List[Path] = []
    for folder in TARGET_DIRS_LIST:
        path = Path(folder)
        if path.exists() and path.is_dir():
            files.extend(path.rglob("*.json"))
    return files


def add_job_summary(lines):
    if not GITHUB_STEP_SUMMARY:
        return
    try:
        Path(GITHUB_STEP_SUMMARY).write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Could not write job summary: {e}")


def extract_expiry_date(kid):
    if not isinstance(kid, str):
        return None
    m = DATE_RE.search(kid)
    token = m.group(1) if m else kid[:10]
    try:
        return datetime.strptime(token, "%Y-%m-%d").date()
    except Exception:
        return None


def days_to_expiry(kid: str) -> Optional[int]:
    d = extract_expiry_date(kid)
    if d is None:
        return None
    return (d - date.today()).days


def sha1_label(text: str) -> str:
    label_hash = hashlib.sha512(text.encode("utf-8")).hexdigest()[:12]
    return f"expkey-{label_hash}"


def find_existing_issue(client, dedupe_label):
    project = JIRA_PROJECT_ID
    if not project:
        return None

    jql = (
        f'project = {project} AND labels = "{dedupe_label}" AND statusCategory != Done'
    )
    try:
        issues = client.search_issues(jql, maxResults=1)
        return True if issues else None
    except JIRAError as e:
        print(f"[WARN] JQL search failed: {jql}\n{e}")
        return None


def get_current_sprint_id(client):
    if not JIRA_BOARD_ID:
        return None

    try:
        active_sprints = client.sprints(board_id=JIRA_BOARD_ID, state="active")
        for sprint in active_sprints:
            if "- Defence" in getattr(sprint, "name", ""):
                return sprint.id
        return None
    except JIRAError as e:
        print(
            f"[ERROR] Unable to create Jira ticket: status: /{e.response.status_code}, data: {e.response.data}"
        )
        return None


def get_env(file_path):
    p = str(file_path).lower()
    if "/prod" in p:
        return "PROD"
    else:
        return "PTL"


def create_issue(client, api_name, file_path, kid, days_left):

    label_key = f"{file_path.as_posix()}::{kid}"
    label_hash = sha1_label(label_key)
    summary = f"Public Key Expiry - {api_name}({get_env(file_path)})"
    description = (
        f"Public key for {api_name} in `{file_path}` will expire in {days_left} day(s).\n\n"
        f"- File: `{file_path}`\n"
        f"- kid: `{kid}`\n"
        f"- label hash: `{label_hash}`\n"
    )

    if not find_existing_issue(client, label_hash):
        fields = {
            "project": {"id": JIRA_PROJECT_ID},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Story"},
            "labels": [label_hash],
            "customfield_10005": JIRA_EPIC_KEY,
            "customfield_10004": get_current_sprint_id(client),
            "priority": {"name": "Not Set"},
        }

        try:
            issue = client.create_issue(fields=fields)
            ticket_id = getattr(issue, "id", None)
            print(f"[INFO] Created JIRA: {ticket_id} ({summary})")
            return (True, ticket_id)
        except JIRAError as e:
            print(
                f"[ERROR] Unable to create Jira ticket: status: {e.response.status_code}, data: {e.response.data}"
            )
            return (False, "Errored")
    else:
        return (False, "Jira Stroy exists")


def main():
    summary = []
    summary.append("Public Key Expiry Check")
    summary.append(f"- Date : {date.today().isoformat()}")
    summary.append(f"- Folders: {TARGET_DIRS_LIST}")
    summary.append(f"- Threshold: {DAYS_THRESHOLD} days")

    files = scan_json_files()
    summary.append(f"- JSON files found: **{len(files)}**")
    client: Optional[JIRA] = None
    if not DRY_RUN:
        if not JIRA_URL or not JIRA_TOKEN or not JIRA_PROJECT_ID:
            print("[ERROR] Missing JIRA_URL, JIRA_TOKEN, or JIRA_PROJECT_ID")
            return 2
        try:
            client = JIRA(server=JIRA_URL, token_auth=JIRA_TOKEN)
        except Exception as e:
            print(f"[ERROR] Failed to initialize JIRA client: {e}")
            return 2

    summary.append("| File | kid | Days left | Action |")
    summary.append("|------|-----|-----------|--------|")

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[WARN] Invalid JSON: {file} ({e})")
            summary.append(f"| `{file}` | — | — | invalid-json |")
            continue

        keys_list = data.get("keys", [])
        if not isinstance(keys_list, list):
            summary.append(f"| `{file}` | — | — | no-keys |")
            continue

        for key in keys_list:
            if not isinstance(key, dict):
                continue
            kid = key.get("kid")
            if not kid:
                continue

            days_left = days_to_expiry(kid)
            if days_left is None:
                summary.append(f"| `{file}` | `{kid}` | — | unparsable-kid |")
                continue

            if days_left <= DAYS_THRESHOLD:
                api = file.stem
                if DRY_RUN:
                    print(
                        f"[DRY-RUN] Would create Jira for {api} ({days_left} days) — {file}"
                    )
                    summary.append(f"| `{file}` | `{kid}` | {days_left} |")
                    continue

                changed, issue_key = create_issue(client, api, file, kid, days_left)
                if changed and issue_key:
                    summary.append(
                        f"| `{file}` | `{kid}` | {days_left} | created `{issue_key}` |"
                    )
                else:
                    summary.append(
                        f"| `{file}` | `{kid}` | {days_left} | {issue_key} |"
                    )
            else:
                summary.append(f"| `{file}` | `{kid}` | {days_left} | ok |")

    add_job_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
