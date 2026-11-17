"""Minimal HTTP client for tests and the scripted demonstration (stdlib only)."""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
import uuid


class Client:
    def __init__(self, base: str):
        self.base = base
        self.cookie = None
        self.csrf = ""

    def _open(self, req):
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            r = opener.open(req, timeout=60)
            return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def login(self, user: str, password: str) -> bool:
        data = f"user_id={user}&password={password}".encode()
        req = urllib.request.Request(self.base + "/login", data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        s, body, h = self._open(req)
        sc = h.get("Set-Cookie", "")
        m = re.match(r"(jmisess=[^;]+)", sc)
        if s != 303 or not m:
            return False
        self.cookie = m.group(1)
        st, b = self.get_json("/api/whoami")
        self.csrf = b.get("csrf", "")
        return st == 200

    def get(self, path: str):
        s, body, h = self._open(urllib.request.Request(self.base + path))
        return s, body, h

    def get_json(self, path: str):
        s, body, _ = self.get(path)
        try:
            return s, json.loads(body or b"{}")
        except ValueError:
            return s, {"_raw": body[:200]}

    def post(self, action: str, payload: dict, csrf: str | None = None):
        req = urllib.request.Request(self.base + "/api/" + action, data=json.dumps(payload).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-JMI-CSRF", self.csrf if csrf is None else csrf)
        s, body, _ = self._open(req)
        try:
            return s, json.loads(body or b"{}")
        except ValueError:
            return s, {"_raw": body[:200]}

    def upload(self, fields: dict, filename: str, data: bytes):
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in {**fields, "csrf": self.csrf}.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
                     f"Content-Type: application/octet-stream\r\n\r\n".encode() + data + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(self.base + "/api/document.upload", data=b"".join(parts), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        s, body, _ = self._open(req)
        try:
            return s, json.loads(body or b"{}")
        except ValueError:
            return s, {"_raw": body[:300]}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def serve_in_thread(store, auth):
    from jmi.server import make_server
    httpd = make_server(store, auth, "127.0.0.1", 0, quiet=True)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"
