#!/usr/bin/env bash
# EXPERIMENTAL / UNTESTED: stage everything the Splunk container needs into docker/staging/.
# Needs: bash, curl, python3, tar, md5sum. Env: SPLUNKBASE_USER, SPLUNKBASE_PASSWORD.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
REPO=$(cd .. && pwd)
S=$PWD/staging
BOTS_URL=https://botsdataset.s3.amazonaws.com/botsv3/botsv3_data_set.tgz
BOTS_MD5=d7ccca99a01cff070dff3c139cdc10eb
: "${SPLUNKBASE_USER:?}"; : "${SPLUNKBASE_PASSWORD:?}"
mkdir -p "$S/apps" "$S/work"

[[ -f $S/apps/botsv3_data_set.tgz ]] || curl -fL --retry 3 -o "$S/apps/botsv3_data_set.tgz" "$BOTS_URL"
[[ "$(md5sum "$S/apps/botsv3_data_set.tgz" | cut -d' ' -f1)" == "$BOTS_MD5" ]] || { echo "dataset checksum mismatch" >&2; exit 1; }

python3 "$REPO/scripts/fetch_apps.py" "$S/apps"

# Patch the MCP Server package (7931-*) and re-pack it.
mcp=$(ls "$S"/apps/7931-*.tgz | head -1)
rm -rf "$S/work/mcp" && mkdir -p "$S/work/mcp" && tar -xzf "$mcp" -C "$S/work/mcp"
python3 "$REPO/scripts/patch_mcp_safe_spl.py" "$S/work/mcp/Splunk_MCP_Server/default/safe_spl.json"
mkdir -p "$S/work/mcp/Splunk_MCP_Server/local" && cp "$REPO/overlay/Splunk_MCP_Server/mcp.conf" "$S/work/mcp/Splunk_MCP_Server/local/"
tar -czf "$mcp" -C "$S/work/mcp" Splunk_MCP_Server

# Package the patched scoreboard apps.
for a in SA-ctf_scoreboard SA-ctf_scoreboard_admin; do tar -czf "$S/apps/$a.tgz" -C "$REPO/apps" "$a"; done
cp "$REPO/templates/authorize.conf" "$S/authorize.conf"
echo "staged in $S. Next: cp .env.example .env (edit), then docker compose up -d, then see README (Docker)."
