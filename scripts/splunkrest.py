"""Tiny Splunk REST client (stdlib only) shared by the provisioning scripts.

The admin password is read from $SPLUNK_ADMIN_PASSWORD, or from the file named by
$SPLUNK_ADMIN_PASSWORD_FILE, or prompted for. It is never accepted on the command line.
"""
import base64
import getpass
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request


def admin_password():
    if os.environ.get("SPLUNK_ADMIN_PASSWORD"):
        return os.environ["SPLUNK_ADMIN_PASSWORD"]
    path = os.environ.get("SPLUNK_ADMIN_PASSWORD_FILE")
    if path:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return getpass.getpass("Splunk admin password: ")


class Splunk:
    def __init__(self, base="https://127.0.0.1:8089", user="admin", password=None):
        self.base = base.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.auth = f"Basic {token}"
        # Splunk's management port uses a self-signed certificate by default.
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def call(self, path, form=None, body=None, method=None, ok=(200, 201)):
        """Return (status, parsed_json_or_text). `form` is urlencoded, `body` is sent as JSON."""
        sep = "&" if "?" in path else "?"
        url = f"{self.base}{path}{sep}output_mode=json"
        data, headers = None, {"Authorization": self.auth}
        if body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form, doseq=True).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=120) as r:
                status, raw = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read().decode()
        try:
            parsed = json.loads(raw) if raw else {}
        except ValueError:
            parsed = raw
        if ok and status not in ok:
            raise RuntimeError(f"{method or 'POST' if data else 'GET'} {path} -> HTTP {status}: {str(parsed)[:300]}")
        return status, parsed

    def kv_save(self, app, collection, records, chunk=500):
        for i in range(0, len(records), chunk):
            self.call(f"/servicesNS/nobody/{app}/storage/collections/data/{collection}/batch_save",
                      body=records[i:i + chunk])
