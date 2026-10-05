# What was changed to run BOTS v3 on Splunk 10

Splunk's own BOTS v3 tooling was last updated for Splunk 8.2 / Python 3. The exact changes to the
upstream scoreboard apps are in `patches/*.patch` (unified diffs against the pinned upstream commits).

## Scoreboard apps (`apps/`)
| Change | Why |
|---|---|
| `scoreboard_controller.py`: `bin_dir` uses the literal app name `SA-ctf_scoreboard` instead of `__file__.split('.')[-2]` | The old expression derived the app name from the module path; the hard-coded name is robust to how Splunk 10 loads the controller (reason inferred from the diff, not separately verified) |
| `welcome.js`: removed the `bootstrap.popover` / `bootstrap.tooltip` modules and their calls | Those Bootstrap modules are presumably not available in Splunk 10's web stack, so the page script failed to load (reason inferred from the diff, not separately verified) |
| `six.py` (3 copies) updated from 1.10 / 1.14 to 1.17.0 | Older `six` fails on newer Python |
| Dashboards (`local/data/ui/views/*.xml`): added `version="1.1"` to every dashboard that loads custom JS/CSS | Splunk 9/10 refuses to run a dashboard's `script=` / `stylesheet=` unless the root declares version 1.1 |
| `score_timeline` and `user_investigator`: the `simpletimeseries` visualization replaced with built-in line chart / tables | That Splunkbase visualization isn't available for Splunk 10 |
| `lookups/currentscore.csv` blanked | Upstream ships sample rows |

## Splunk MCP Server (applied by `scripts/patch_mcp_safe_spl.py`)
Removes `inputlookup`, `inputcsv`, `from`, `history`, `savedsearch`, `rest`, `loadjob` from the safe-SPL command
list and adds `decrypt`, `multikv`, `kv`, `eventtypes`. The intent (to confirm with the maintainer): stop an
MCP-connected agent from reading scoreboard answers out of lookups/saved searches while keeping the commands
BOTS v3 questions need. `overlay/Splunk_MCP_Server/mcp.conf` sets the MCP rate limits.

## System configuration (`templates/`)
* `web.conf`: HTTPS, bound to 127.0.0.1 (Caddy fronts it).
* `authorize.conf`: the `bots_player` role (limited to the `botsv3` and `scoreboard` indexes, 6 concurrent
  searches, 5 min max runtime, MCP tool execution) and token authentication (needed for MCP).
* `Caddyfile.template`: HTTPS reverse proxy with automatic Let's Encrypt certificates.
