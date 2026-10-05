#!/usr/bin/env python3
"""Download the Splunkbase apps that BOTS v3 and the scoreboard need, into ./downloads/apps.

Splunkbase requires a free splunk.com login. Credentials come from the environment
(SPLUNKBASE_USER / SPLUNKBASE_PASSWORD) or, if unset, an interactive prompt. Nothing is stored.
Usage: fetch_apps.py [output_dir]
"""
import getpass
import json
import os
import re
import sys
import urllib.parse
import urllib.request

# Splunkbase app id -> label. Newest release compatible with Splunk 10 (else 9) is chosen.
APPS = {
    3790: "AWS GuardDuty", 2992: "CiscoNVM", 3736: "Code42 App", 3746: "Code42 TA",
    1620: "Add-on for Cisco ASA", 3110: "Add-on for MS Cloud Services", 4055: "Add-on for Office 365",
    742: "Add-on for Microsoft Windows", 2772: "Add-on for Symantec EP", 1710: "Add-on for Tenable",
    833: "Add-on for Unix and Linux", 1621: "Common Information Model", 3435: "Security Essentials",
    1809: "Stream Add-on", 3446: "TA-VirusTotalActions", 2734: "URL Toolbox", 2655: "DecryptCommands",
    3757: "Azure AD Reporting Add-on", 3786: "Microsoft Cloud App", 3720: "O365 Reporting Add-on",
    1914: "Sysmon Add-on", 3902: "OSquery App", 1876: "Add-on for AWS", 3449: "ES Content Updates",
    2968: "SA-cim_vladiator", 1724: "Lookup File Editor", 3137: "Parallel Coordinates viz",
    3120: "Timeline viz", 7931: "Splunk MCP Server",
}
# Not installed on purpose: 3436 (Simple Timeseries viz) is unavailable on Splunk 10; the scoreboard
# dashboards were converted to built-in charts instead (see patches/).

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "downloads", "apps")
os.makedirs(out, exist_ok=True)

user = os.environ.get("SPLUNKBASE_USER") or input("Splunkbase username: ")
password = os.environ.get("SPLUNKBASE_PASSWORD") or getpass.getpass("Splunkbase password: ")
data = urllib.parse.urlencode({"username": user, "password": password}).encode()
with urllib.request.urlopen("https://splunkbase.splunk.com/api/account:login/", data, timeout=30) as r:
    m = re.search(r"<id>(.*?)</id>", r.read().decode(), re.S | re.I)
password = None
if not m:
    sys.exit("Splunkbase login failed")
hdr = {"X-Auth-Token": m.group(1)}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=300)


failed = 0
for app_id, label in APPS.items():
    try:
        with get(f"https://splunkbase.splunk.com/api/v1/app/{app_id}/release/") as r:
            rels = json.load(r)
        rel = next((x for x in rels if any(str(c).startswith("10") for c in x.get("splunk_compatibility", []))),
                   next((x for x in rels if any(str(c).startswith("9") for c in x.get("splunk_compatibility", []))), rels[0]))
        ver = rel["name"]
        dest = os.path.join(out, f"{app_id}-{ver}.tgz")
        if not os.path.exists(dest):
            with get(f"https://splunkbase.splunk.com/app/{app_id}/release/{ver}/download/") as r, open(dest, "wb") as f:
                f.write(r.read())
        print(f"OK   {app_id:5} {label} {ver} ({os.path.getsize(dest) // 1024} KB)")
    except Exception as e:  # keep going; report at the end
        failed += 1
        print(f"FAIL {app_id:5} {label}: {e}")
sys.exit(1 if failed else 0)
