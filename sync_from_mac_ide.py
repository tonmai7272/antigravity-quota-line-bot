#!/usr/bin/env python3
"""
Local helper for macOS running Antigravity IDE:
Finds the running Antigravity language_server process, queries GetUserStatus
from its local port to read the exact quota shown in the Antigravity IDE status bar,
saves it to quota_state.json, and pushes to GitHub (or updates QUOTA_JSON_DATA secret).

Can also be invoked with manual values if needed:
  python3 sync_from_mac_ide.py --weekly-used 35 --weekly-reset "2026-11-21T14:00:00+07:00"
"""

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

BKK_TZ = timezone(timedelta(hours=7))


def find_antigravity_server():
    """Find running Antigravity language_server process and extract CSRF token & ports."""
    try:
        ps_out = subprocess.check_output(["ps", "-ax", "-o", "pid,command"], text=True)
    except Exception:
        return None

    for line in ps_out.splitlines():
        if "language_server" in line and ("antigravity" in line.lower() or "csrf_token" in line):
            pid_match = re.match(r"^\s*(\d+)", line)
            csrf_match = re.search(r"--csrf_token[=\s]+([^\s]+)", line)
            if not pid_match:
                continue
            pid = pid_match.group(1)
            csrf = csrf_match.group(1) if csrf_match else ""

            try:
                lsof_out = subprocess.check_output(
                    ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-a", "-p", pid],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                continue

            ports = re.findall(r":(\d+)\s+\(LISTEN\)", lsof_out)
            if ports:
                return {"pid": pid, "csrf": csrf, "ports": ports}
    return None


def query_local_user_status(server_info: dict):
    """Query GetUserStatus from the local Antigravity IDE language server."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    endpoints = [
        "/exa.language_server_pb.LanguageServerService/GetUserStatus",
        "/codeium.language_server_pb.LanguageServerService/GetUserStatus",
    ]

    for port in server_info["ports"]:
        for scheme in ("https", "http"):
            for ep in endpoints:
                url = f"{scheme}://127.0.0.1:{port}{ep}"
                headers = {
                    "Content-Type": "application/json",
                    "Connect-Protocol-Version": "1",
                }
                if server_info.get("csrf"):
                    headers["x-codeium-csrf-token"] = server_info["csrf"]

                req = urllib.request.Request(
                    url,
                    data=b'{"metadata":{"ideName":"antigravity"}}',
                    headers=headers,
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=3, context=ctx if scheme == "https" else None) as resp:
                        return json.loads(resp.read().decode("utf-8"))
                except Exception:
                    continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Sync Antigravity IDE quota to GitHub")
    parser.add_argument("--email", help="Account email")
    parser.add_argument("--five-hour-used", type=float, help="5-hour used percent")
    parser.add_argument("--five-hour-reset", help="5-hour reset ISO timestamp")
    parser.add_argument("--weekly-used", type=float, help="Weekly used percent")
    parser.add_argument("--weekly-reset", help="Weekly reset ISO timestamp")
    parser.add_argument("--push", action="store_true", help="Commit and push quota_state.json to GitHub")
    args = parser.parse_args()

    payload = None
    if args.weekly_used is not None and args.weekly_reset:
        payload = {
            "email": args.email or os.environ.get("ACCOUNT_EMAIL", "unknown"),
            "weekly": {
                "used_percent": args.weekly_used,
                "reset_at": args.weekly_reset,
            },
            "updated_at": datetime.now(BKK_TZ).isoformat(),
        }
        if args.five_hour_used is not None and args.five_hour_reset:
            payload["five_hour"] = {
                "used_percent": args.five_hour_used,
                "reset_at": args.five_hour_reset,
            }
    else:
        srv = find_antigravity_server()
        if srv:
            raw = query_local_user_status(srv)
            if raw:
                payload = raw

    if not payload:
        print("Could not auto-detect running Antigravity IDE language server or manual args.", file=sys.stderr)
        sys.exit(1)

    with open("quota_state.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("Saved quota_state.json")

    if args.push:
        subprocess.run(["git", "add", "quota_state.json"], check=True)
        subprocess.run(["git", "commit", "-m", "chore: sync quota_state.json"], check=False)
        subprocess.run(["git", "push"], check=True)


if __name__ == "__main__":
    main()
