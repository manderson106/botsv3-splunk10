#!/usr/bin/env python3
"""Create or update competitor accounts and scoreboard teams from a roster CSV.

Roster CSV: header row `Username,Team` (extra columns are ignored); the Team text is used verbatim.
Usage: provision_users.py roster.csv --out credentials.csv [--role bots_player] [--mcp-token-expiry +30d]
                          [--reset-passwords] [--dry-run]
New users get a random password. Existing users keep theirs unless --reset-passwords is given.
The credentials file is written with mode 600; hand each person only their own row.
"""
import argparse
import csv
import os
import secrets
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunkrest import Splunk, admin_password  # noqa: E402

ALNUM = string.ascii_letters + string.digits


def find_token(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if "token" in k.lower() and isinstance(v, str) and len(v) > 100:
                return v
        for v in node.values():
            found = find_token(v)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = find_token(v)
            if found:
                return found
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roster")
    ap.add_argument("--out", required=True)
    ap.add_argument("--role", default="bots_player")
    ap.add_argument("--mcp-token-expiry", help="also mint an MCP token per user, e.g. +30d (max +180d)")
    ap.add_argument("--reset-passwords", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.roster, newline="", encoding="utf-8-sig") as f:
        roster = [(r["Username"].strip().lower(), r["Team"].strip()) for r in csv.DictReader(f)
                  if r.get("Username", "").strip()]
    if args.dry_run:
        for user, team in roster:
            print(f"would provision {user} -> {team}")
        return

    s = Splunk(password=admin_password())
    if args.mcp_token_expiry:
        s.call("/services/admin/token-auth/tokens_auth", form={"disabled": "false"})

    fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["Username", "Team", "Password", "Token"])
        for user, team in roster:
            password = "".join(secrets.choice(ALNUM) for _ in range(14))
            exists, _ = s.call(f"/services/authentication/users/{user}", ok=None)
            if exists == 200:
                shown = "(unchanged)"
                form = {"roles": args.role}
                if args.reset_passwords:
                    form["password"], shown = password, password
                s.call(f"/services/authentication/users/{user}", form=form)
                action = "updated"
            else:
                s.call("/services/authentication/users", form={"name": user, "password": password,
                                                                 "roles": args.role,
                                                                 "defaultApp": "SA-ctf_scoreboard"})
                shown, action = password, "created"
            s.kv_save("SA-ctf_scoreboard", "ctf_users", [{
                "_key": user, "Username": user, "FirstName": user, "LastName": "", "DisplayUsername": user,
                "Team": team, "Email": f"{user}@localhost", "SearchUrl": "search",
                "SearchUrlDesc": "Default Search App", "SearchUrl2": "search", "SearchUrl2Desc": "",
                "ScoringUrl": "AllScores", "Event": "BOTS v3"}])
            token = ""
            if args.mcp_token_expiry:
                _, resp = s.call(f"/services/mcp_token?username={user}&expires_on={args.mcp_token_expiry}",
                                 ok=None)
                token = find_token(resp)
            writer.writerow([user, team, shown, token])
            print(f"{user}: {action}, team={team}" + (", token ok" if token else ""))
    print(f"credentials written to {args.out} (mode 600)")


if __name__ == "__main__":
    main()
