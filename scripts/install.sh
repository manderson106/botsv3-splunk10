#!/usr/bin/env bash
# BOTS v3 on Splunk 10: install Splunk Enterprise, the official BOTS v3 dataset, the compatibility-patched
# CTF scoreboard, the Splunk MCP Server and (optionally) an HTTPS reverse proxy.
# Run as root on a fresh Ubuntu 22.04/24.04 server:   sudo -E ./scripts/install.sh
#
# Required environment:
#   SPLUNK_ADMIN_PASSWORD   password for the Splunk 'admin' account (min 8 chars)
#   SPLUNKBASE_USER / SPLUNKBASE_PASSWORD   free splunk.com login, used to download the add-ons
# Optional:
#   DOMAIN              public hostname; installs Caddy for HTTPS and opens ports 80/443
#   BOTS_CONTENT_DIR    directory with the official ctf_questions.csv / ctf_answers.csv / ctf_hints.csv
#   SPLUNK_VERSION / SPLUNK_BUILD   defaults below
#   I_ACCEPT_SPLUNK_LICENSE=yes     required: you accept Splunk's software licence (splunk.com/en_us/legal)
set -euo pipefail

SPLUNK_VERSION=${SPLUNK_VERSION:-10.4.4}
SPLUNK_BUILD=${SPLUNK_BUILD:-f0f12fcdcaa1}
SPLUNK_HOME=/opt/splunk
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DL=${DL:-/opt/botsv3-install}
BOTS_URL=https://botsdataset.s3.amazonaws.com/botsv3/botsv3_data_set.tgz
BOTS_MD5=d7ccca99a01cff070dff3c139cdc10eb

say() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root"
[[ ${I_ACCEPT_SPLUNK_LICENSE:-} == yes ]] || die "set I_ACCEPT_SPLUNK_LICENSE=yes to accept Splunk's licence terms"
: "${SPLUNK_ADMIN_PASSWORD:?set SPLUNK_ADMIN_PASSWORD}"
: "${SPLUNKBASE_USER:?set SPLUNKBASE_USER}"
: "${SPLUNKBASE_PASSWORD:?set SPLUNKBASE_PASSWORD}"
[[ ${#SPLUNK_ADMIN_PASSWORD} -ge 8 ]] || die "SPLUNK_ADMIN_PASSWORD must be at least 8 characters"
[[ -z ${BOTS_CONTENT_DIR:-} || -d $BOTS_CONTENT_DIR ]] || die "BOTS_CONTENT_DIR '$BOTS_CONTENT_DIR' not found"
export SPLUNK_ADMIN_PASSWORD SPLUNKBASE_USER SPLUNKBASE_PASSWORD

say "Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates python3 ufw >/dev/null
mkdir -p "$DL/apps"

say "Splunk Enterprise $SPLUNK_VERSION"
if [[ ! -x $SPLUNK_HOME/bin/splunk ]]; then
  id splunk >/dev/null 2>&1 || useradd -r -m -d "$SPLUNK_HOME" -s /bin/bash splunk
  tgz="splunk-$SPLUNK_VERSION-$SPLUNK_BUILD-linux-amd64.tgz"
  url="https://download.splunk.com/products/splunk/releases/$SPLUNK_VERSION/linux/$tgz"
  [[ -f $DL/$tgz ]] || curl -fL --retry 3 -o "$DL/$tgz" "$url"
  curl -fsSL -o "$DL/$tgz.sha512" "$url.sha512"
  expected=$(grep -oE '[0-9a-f]{128}' "$DL/$tgz.sha512" | head -1)
  [[ "$(sha512sum "$DL/$tgz" | cut -d' ' -f1)" == "$expected" ]] || die "Splunk download checksum mismatch"
  tar -xzf "$DL/$tgz" -C /opt
  chown -R splunk:splunk "$SPLUNK_HOME"
  # Seed the admin account so first start needs no prompt.
  umask 077
  printf '[user_info]\nUSERNAME = admin\nPASSWORD = %s\n' "$SPLUNK_ADMIN_PASSWORD" > "$SPLUNK_HOME/etc/system/local/user-seed.conf"
  chown splunk:splunk "$SPLUNK_HOME/etc/system/local/user-seed.conf"
  umask 022
else
  echo "Splunk already installed at $SPLUNK_HOME; skipping download"
fi

say "BOTS v3 dataset (official pre-indexed package)"
if [[ ! -d $SPLUNK_HOME/etc/apps/botsv3_data_set ]]; then
  [[ -f $DL/botsv3_data_set.tgz ]] || curl -fL --retry 3 -o "$DL/botsv3_data_set.tgz" "$BOTS_URL"
  [[ "$(md5sum "$DL/botsv3_data_set.tgz" | cut -d' ' -f1)" == "$BOTS_MD5" ]] || die "dataset checksum mismatch"
  tar -xzf "$DL/botsv3_data_set.tgz" -C "$SPLUNK_HOME/etc/apps"
fi

say "Splunkbase add-ons (including the Splunk MCP Server)"
python3 "$REPO/scripts/fetch_apps.py" "$DL/apps"
for pkg in "$DL"/apps/*.tgz; do tar -xzf "$pkg" -C "$SPLUNK_HOME/etc/apps"; done

say "Splunk 10 compatibility layer"
python3 "$REPO/scripts/patch_mcp_safe_spl.py" "$SPLUNK_HOME/etc/apps/Splunk_MCP_Server/default/safe_spl.json"
mkdir -p "$SPLUNK_HOME/etc/apps/Splunk_MCP_Server/local"
cp "$REPO/overlay/Splunk_MCP_Server/mcp.conf" "$SPLUNK_HOME/etc/apps/Splunk_MCP_Server/local/mcp.conf"
for app in SA-ctf_scoreboard SA-ctf_scoreboard_admin; do
  rm -rf "${SPLUNK_HOME:?}/etc/apps/$app"
  cp -a "$REPO/apps/$app" "$SPLUNK_HOME/etc/apps/$app"
done
# system-level settings: only create if absent, so a re-run never clobbers local edits
for f in web.conf authorize.conf; do
  dest="$SPLUNK_HOME/etc/system/local/$f"
  [[ -e $dest ]] && cp -n "$dest" "$dest.pre-botsv3" || true
  cat "$REPO/templates/$f" >> "$dest"
done
chown -R splunk:splunk "$SPLUNK_HOME"

say "Start Splunk (boot-start enabled)"
sudo -u splunk "$SPLUNK_HOME/bin/splunk" start --accept-license --answer-yes --no-prompt
"$SPLUNK_HOME/bin/splunk" enable boot-start -systemd-managed 1 -user splunk --accept-license --answer-yes --no-prompt >/dev/null 2>&1 || true
for i in $(seq 1 60); do
  curl -sk -o /dev/null -u "admin:$SPLUNK_ADMIN_PASSWORD" "https://127.0.0.1:8089/services/server/info" && break
  sleep 5
done

if [[ -n ${BOTS_CONTENT_DIR:-} ]]; then
  say "Import official questions, answers and hints"
  python3 "$REPO/scripts/import_content.py" --content-dir "$BOTS_CONTENT_DIR" --splunk-home "$SPLUNK_HOME"
  systemctl restart Splunkd 2>/dev/null || sudo -u splunk "$SPLUNK_HOME/bin/splunk" restart
else
  echo "BOTS_CONTENT_DIR not set: skipping question import. See content/README.md for how to get the official files."
fi

say "Firewall"
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw limit 22/tcp >/dev/null
if [[ -n ${DOMAIN:-} ]]; then
  apt-get install -y -qq caddy >/dev/null
  sed "s/__DOMAIN__/$DOMAIN/" "$REPO/templates/Caddyfile.template" > /etc/caddy/Caddyfile
  systemctl reload caddy || systemctl restart caddy
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
  echo "HTTPS: https://$DOMAIN (DNS for $DOMAIN must point at this server)"
else
  echo "No DOMAIN set: Splunk Web is bound to 127.0.0.1:8000 only. Use an SSH tunnel: ssh -L 8000:127.0.0.1:8000 root@<server>"
fi
ufw --force enable >/dev/null

say "Done"
echo "Next: scripts/provision_users.py roster.csv --out credentials.csv   (see README.md)"
