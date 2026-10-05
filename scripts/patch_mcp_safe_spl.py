#!/usr/bin/env python3
"""Apply the BOTS v3 changes to the Splunk MCP Server's safe-SPL command list.

Usage: patch_mcp_safe_spl.py /opt/splunk/etc/apps/Splunk_MCP_Server/default/safe_spl.json

Removes commands that can read lookups, saved searches, job results or REST endpoints (so an MCP
client cannot pull scoreboard answers out of KV store lookups) and adds the commands the BOTS v3
questions need. Idempotent; the file itself is a Splunkbase asset, so we patch it instead of shipping it.
"""
import json
import sys

REMOVE = ["inputlookup", "inputcsv", "from", "history", "savedsearch", "rest", "loadjob"]
ADD = ["decrypt", "multikv", "kv", "eventtypes"]
ANCHOR = "cluster"  # the additions go in the list that contains this command

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    doc = json.load(f)

removed, added, anchor_lists = [], [], []


def walk(node):
    if isinstance(node, dict):
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        if ANCHOR in node:
            anchor_lists.append(node)
        for cmd in REMOVE:
            while cmd in node:
                node.remove(cmd)
                removed.append(cmd)
        for v in node:
            walk(v)


walk(doc)
if not anchor_lists:
    sys.exit(f"no list containing '{ANCHOR}' found in {path}: the app layout changed, review manually")
target = anchor_lists[0]
for cmd in ADD:
    if cmd not in target:
        target.append(cmd)
        added.append(cmd)

with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
print(f"removed {sorted(set(removed)) or 'nothing (already applied)'}; added {added or 'nothing (already applied)'}")
