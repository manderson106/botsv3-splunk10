# Third-party material

| Component | Source | Licence | In this repo? |
|---|---|---|---|
| `apps/SA-ctf_scoreboard`, `apps/SA-ctf_scoreboard_admin` | github.com/splunk/SA-ctf_scoreboard(_admin) at commits `bef2d5c` / `7a694a5` | CC0 1.0 (see each app's `LICENSE`) | Yes, with Splunk 10 patches (`patches/`) |
| BOTS v3 dataset (`botsv3_data_set`) | github.com/splunk/botsv3 | CC0 1.0 | **No**: downloaded from Splunk's official bucket and checksum-verified |
| BOTS v3 questions / answers / hints | Splunk, on request (bots@splunk.com) | Splunk's terms | **No**: supplied by the user |
| Splunk Enterprise | splunk.com | Splunk General Terms | **No**: downloaded at install time; you accept the licence |
| Splunkbase add-ons (Cisco ASA, AWS, Windows, CIM, Security Essentials, MCP Server, etc.) | splunkbase.splunk.com | Per app | **No**: downloaded with your Splunkbase login |
| `six.py` 1.17.0 (inside the scoreboard apps) | github.com/benjaminp/six | MIT | Yes (replaces the older bundled copies) |

Scripts, templates and docs written for this repo are MIT-licensed (see `LICENSE`).
This project is not affiliated with or endorsed by Splunk.
