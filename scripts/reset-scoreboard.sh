#!/usr/bin/env bash
# Clear all scoreboard activity (answers, scores, hint purchases). Keeps questions, users and the BOTS data.
# Run as root on the Splunk server. Splunk is stopped for a couple of minutes. IRREVERSIBLE.
set -euo pipefail
SPLUNK_HOME=${SPLUNK_HOME:-/opt/splunk}
read -rp "This permanently deletes all scoreboard events. Type 'reset' to continue: " ans
[[ $ans == reset ]] || { echo "aborted"; exit 1; }
systemctl stop Splunkd
for idx in scoreboard scoreboard_admin; do
  sudo -u splunk "$SPLUNK_HOME/bin/splunk" clean eventdata -index "$idx" -f
done
rm -f "$SPLUNK_HOME"/var/log/scoreboard/scoreboard.log "$SPLUNK_HOME"/var/log/scoreboard/scoreboard_admin.log
# The score tables are only rewritten when new answers arrive, so blank them too.
for app in SA-ctf_scoreboard SA-ctf_scoreboard_admin; do
  f="$SPLUNK_HOME/etc/apps/$app/lookups/currentscore.csv"
  [[ -e $f ]] && echo 'Team,BasePoints,BonusPoints,Penalty,Score,Rank,currentcount,totalcount' > "$f"
done
systemctl start Splunkd
echo "Scoreboard reset. Splunk is starting."
