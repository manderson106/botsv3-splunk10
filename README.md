# BOTS v3 on Splunk 10, with an agentic (MCP) twist

Everything needed to run a **Boss of the SOC v3** event on **Splunk Enterprise 10.x**: the official pre-indexed
dataset, the Splunk CTF scoreboard patched to work on Splunk 10, the Splunk MCP Server so AI agents can take
part, bulk user/team provisioning, and an HTTPS front end.

> **Status.** This is the configuration of a live event server. `install.sh` was assembled from that server and
> has had syntax checks and unit-level tests of the helper scripts, but has **not yet been run end-to-end on a
> clean machine**. The Docker variant is experimental. Please open an issue with anything that breaks.

## What you need
* A fresh Ubuntu 22.04/24.04 server (16 GB RAM / 300 GB disk is comfortable; the dataset is ~600 MB installed, ~2 M events)
* A free [Splunkbase](https://splunkbase.splunk.com) account (to download the add-ons)
* The official questions/answers/hints from Splunk, see [`content/README.md`](content/README.md) (optional at install time)
* A DNS name pointing at the server if you want HTTPS (optional)

## Install (single server)
```bash
git clone <this repo> && cd <repo>
export I_ACCEPT_SPLUNK_LICENSE=yes        # accepts Splunk's licence terms; read them first
export SPLUNK_ADMIN_PASSWORD='choose-a-strong-one'
export SPLUNKBASE_USER=you@example.com SPLUNKBASE_PASSWORD='...'
export DOMAIN=bots.example.com            # optional: installs Caddy + Let's Encrypt, opens 80/443
export BOTS_CONTENT_DIR=$PWD/content      # optional: official ctf_*.csv files
sudo -E ./scripts/install.sh
```
The script installs Splunk (checksum-verified), the official dataset (MD5-verified), the add-ons, applies the
Splunk 10 compatibility layer, enables boot-start, imports the questions if provided, and configures ufw
(SSH rate-limited; 80/443 only when `DOMAIN` is set). Without `DOMAIN`, Splunk Web is bound to localhost:
`ssh -L 8000:127.0.0.1:8000 root@server`, then open https://localhost:8000.

## Add competitors and teams
```bash
cp roster.example.csv roster.csv           # Username,Team
export SPLUNK_ADMIN_PASSWORD=...           # or SPLUNK_ADMIN_PASSWORD_FILE=/path/to/file
sudo -E python3 scripts/provision_users.py roster.csv --out credentials.csv --mcp-token-expiry +30d
```
Creates each user (role `bots_player`), sets their scoreboard team, and writes random passwords (and optional
MCP tokens) to `credentials.csv` (mode 600; never commit it). Re-running updates teams without changing passwords
unless you pass `--reset-passwords`. Team text is used exactly as written; keep one consistent format.

## Run the event
* Competitors log in at the scoreboard (`SA-ctf_scoreboard`, "Capture the Flag"); search data lives in index `botsv3`.
* Agents connect to the Splunk MCP Server using the per-user token from `credentials.csv`.
* Between rehearsal and the real event run `sudo scripts/reset-scoreboard.sh` (wipes answers and scores).

## Repository layout
| Path | What |
|---|---|
| `apps/` | Scoreboard + admin apps with the Splunk 10 patches applied (CC0 upstream) |
| `patches/` | The same changes as unified diffs against the pinned upstream commits |
| `overlay/`, `templates/` | MCP settings, `web.conf`, `authorize.conf`, Caddyfile template |
| `scripts/` | `install.sh`, `fetch_apps.py`, `patch_mcp_safe_spl.py`, `import_content.py`, `provision_users.py`, `reset-scoreboard.sh` |
| `docker/` | Experimental container variant |
| `docs/CHANGES.md` | What was changed and why |
| `THIRD_PARTY.md` | Licences and what is *not* redistributed |

## Docker (experimental, untested)
```bash
export SPLUNKBASE_USER=... SPLUNKBASE_PASSWORD=...
./docker/prepare.sh && cd docker && cp .env.example .env   # set the password and APPS_URLS as described inside
docker compose up -d
```

## Security notes
* Change every default; use a long unique admin password. Never commit `credentials.csv`, tokens, or the official answer files (`.gitignore` blocks them).
* Management port 8089 is not opened by the firewall; keep it that way.
* Rotate the admin password and all MCP tokens after the event.

## Licence
Scripts, templates and docs: MIT. Third-party components keep their own licences, see [`THIRD_PARTY.md`](THIRD_PARTY.md).
Not affiliated with Splunk. "Boss of the SOC" and "BOTS" are Splunk trademarks.
