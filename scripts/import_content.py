#!/usr/bin/env python3
"""Import the official BOTS v3 questions, answers and hints, and set up the scoreboard service account.

Splunk provides the content CSVs on request (email bots@splunk.com); they are not in this repository.
Usage: import_content.py --content-dir /path/with/csvs [--splunk-home /opt/splunk]
Expects ctf_questions.csv, ctf_answers.csv, ctf_hints.csv in the directory. Safe to re-run.
"""
import argparse
import configparser
import csv
import os
import pwd
import secrets
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunkrest import Splunk, admin_password  # noqa: E402

ALNUM = string.ascii_letters + string.digits
SVC_USER = "svcaccount"


def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def clean(row, drop=("_key", "_user")):
    return {k: v for k, v in row.items() if k and k not in drop}


def write_conf(path, section, values, owner):
    cp = configparser.ConfigParser()
    cp.optionxform = str
    cp[section] = values
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        cp.write(f)
    os.chmod(path, 0o600)
    try:
        info = pwd.getpwnam(owner)
        os.chown(path, info.pw_uid, info.pw_gid)
    except KeyError:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content-dir", required=True)
    ap.add_argument("--splunk-home", default="/opt/splunk")
    ap.add_argument("--splunk-user", default="splunk", help="OS user that owns the Splunk install")
    args = ap.parse_args()

    files = {n: os.path.join(args.content_dir, f"ctf_{n}.csv") for n in ("questions", "answers", "hints")}
    missing = [p for p in files.values() if not os.path.isfile(p)]
    if missing:
        sys.exit("missing content file(s): " + ", ".join(missing))

    s = Splunk(password=admin_password())
    apps = os.path.join(args.splunk_home, "etc", "apps")
    ctl_conf = os.path.join(apps, "SA-ctf_scoreboard", "appserver", "controllers", "scoreboard_controller.config")

    # Service account (role ctf_answers_service). Keep the existing VKEY on re-runs.
    password = "".join(secrets.choice(ALNUM) for _ in range(32))
    vkey = "".join(secrets.choice(ALNUM) for _ in range(32))
    if os.path.exists(ctl_conf):
        old = configparser.ConfigParser()
        old.read(ctl_conf)
        vkey = old.get("ScoreboardController", "VKEY", fallback=vkey)
    status, _ = s.call(f"/services/authentication/users/{SVC_USER}", ok=None)
    if status == 200:
        s.call(f"/services/authentication/users/{SVC_USER}", form={"password": password, "roles": "ctf_answers_service"})
    else:
        s.call("/services/authentication/users", form={"name": SVC_USER, "password": password,
                                                        "roles": "ctf_answers_service"})
    write_conf(ctl_conf, "ScoreboardController", {"USER": SVC_USER, "PASS": password, "VKEY": vkey}, args.splunk_user)
    write_conf(os.path.join(apps, "SA-ctf_scoreboard_admin", "bin", "backuprestore.config"), "BackupRestore",
               {"SCHEME": "https", "HOST": "127.0.0.1", "PORT": "8089", "USER": SVC_USER, "PASS": password,
                "VERIFYCERT": "False", "BACKUPDIR": "/tmp"}, args.splunk_user)
    print(f"service account '{SVC_USER}' ready; config files written (mode 600)")

    questions = [dict(clean(r), _key=f"botsv3:q:{r['Number']}") for r in rows(files["questions"])]
    answers = [dict(clean(r), _key=f"botsv3:a:{r['Number']}") for r in rows(files["answers"])]
    hints = [dict(clean(r), _key=f"botsv3:h:{r['Number']}:{r['HintNumber']}") for r in rows(files["hints"])]
    s.kv_save("SA-ctf_scoreboard", "ctf_questions", questions)
    s.kv_save("SA-ctf_scoreboard_admin", "ctf_answers", answers)
    s.kv_save("SA-ctf_scoreboard_admin", "ctf_hints", hints)
    print(f"imported {len(questions)} questions, {len(answers)} answers, {len(hints)} hints")
    print("Restart Splunk once so the scoreboard controller reads its new config: systemctl restart Splunkd")


if __name__ == "__main__":
    main()
