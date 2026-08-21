"""
ntfy_publish.py -- one wrapper around the ntfy topic that every analyst
uses to push. Centralizing here means the topic name, priorities, and
action-button syntax all live in one file. When the topic ever changes,
one edit.

USAGE
-----
    from ntfy_publish import push, DIGEST, ZONE, CLUSTER, GATE_BREAK

    push(ZONE, title="GOOGL entered zone",
         body="GOOGL 340.67 (<= 355) — half now; half post-print ~Jul 23",
         tags=["dollar"])

    # with action button that writes user reply into the journal
    push(GATE_BREAK, title="NVDA failed gate 4 on 2027-Q1 10-Q",
         body="Dilution 6.2% (threshold: 5%). Held: 240 sh.",
         actions=[action_button("Acknowledge", "acted"),
                  action_button("Ignore",       "ignored"),
                  action_button("Not applicable", "na")])

DESIGN NOTES
------------
- Topic name is imported from an env var so it's not hardcoded in git.
- Every push includes a click URL back to the digest for context.
- Priorities:
    DIGEST      = 2  (low  — silent, tag "notebook")
    SILENCE     = 2  (low  — "nothing fired today" reports)
    ZONE        = 4  (high — banner + sound)
    CLUSTER     = 4  (high — congress cluster ≥3 members)
    GATE_BREAK  = 5  (max  — held name lost a gate on new filing)
- Action buttons post back to a webhook endpoint that the journal watcher
  consumes; the webhook URL is also env-configured.
- If NTFY_TOPIC is unset OR NTFY_DISABLED=1, this module logs and no-ops.
  Local testing / paused mode / vacation mode all set NTFY_DISABLED=1.
"""
from __future__ import annotations
import os
import json
import time
import logging
import urllib.request
import urllib.error
from typing import Iterable, Optional

log = logging.getLogger(__name__)

# --- config (env-driven so nothing sensitive is in git) --------------------
NTFY_HOST = os.environ.get("NTFY_HOST", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")          # required for a real push
NTFY_DISABLED = os.environ.get("NTFY_DISABLED", "") == "1"
JOURNAL_WEBHOOK = os.environ.get("JOURNAL_WEBHOOK", "")  # optional callback for action buttons
DIGEST_BASE_URL = os.environ.get("DIGEST_BASE_URL", "")  # optional link back to digest

# --- priorities ------------------------------------------------------------
DIGEST     = 2  # silent daily summary
SILENCE    = 2  # "nothing fired today"
ZONE       = 4  # watchlist name entered buy zone
CLUSTER    = 4  # congress cluster detected
GATE_BREAK = 5  # held name failed a gate on new filing


def action_button(label: str, response: str) -> dict:
    """Build one action button that POSTs the response back to the journal webhook.
    The webhook writes the response into journal.jsonl tagged with the message id.
    """
    if not JOURNAL_WEBHOOK:
        # fall back to a view action if no webhook configured
        return {"action": "view", "label": label, "url": DIGEST_BASE_URL or NTFY_HOST}
    return {
        "action": "http",
        "label": label,
        "url": JOURNAL_WEBHOOK,
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"response": response, "ts": int(time.time())}),
        "clear": True,
    }


def push(priority: int, title: str, body: str,
         tags: Optional[Iterable[str]] = None,
         actions: Optional[list[dict]] = None,
         click_url: Optional[str] = None,
         topic_override: Optional[str] = None) -> bool:
    """Publish one notification. Returns True if sent, False if suppressed.
    Never raises on network error -- logs and returns False so cron doesn't
    crash the whole run over a transient push failure."""
    if NTFY_DISABLED:
        log.info("ntfy DISABLED: would have sent title=%r prio=%d", title, priority)
        return False
    topic = topic_override or NTFY_TOPIC
    if not topic:
        log.warning("ntfy: no topic configured, dropping title=%r", title)
        return False

    url = f"{NTFY_HOST}/{topic}"
    headers = {
        "Title": _ascii_header(title),
        "Priority": str(priority),
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    if click_url or DIGEST_BASE_URL:
        headers["Click"] = click_url or DIGEST_BASE_URL
    if actions:
        headers["Actions"] = _encode_actions(actions)

    req = urllib.request.Request(url, data=body.encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = 200 <= resp.status < 300
            log.info("ntfy push %s: title=%r prio=%d status=%d",
                     "OK" if ok else "FAIL", title, priority, resp.status)
            return ok
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log.warning("ntfy push failed: title=%r err=%s", title, exc)
        return False


def _ascii_header(s: str) -> str:
    """ntfy header values must be latin-1 safe. Drop non-ASCII."""
    return s.encode("ascii", "replace").decode("ascii")


def _encode_actions(actions: list[dict]) -> str:
    """Encode actions per ntfy Actions header spec.
    Format: `action=<a>, label=<l>, url=<u>[, method=<m>][, body=<b>][, clear=true]; ...`
    Multiple actions separated by `;`.
    """
    parts = []
    for a in actions[:3]:  # ntfy supports up to 3
        pieces = [f"{k}={_hdr_quote(str(v))}" for k, v in a.items()]
        parts.append(", ".join(pieces))
    return "; ".join(parts)


def _hdr_quote(v: str) -> str:
    """Values with commas or semicolons must be double-quoted per ntfy spec."""
    if any(c in v for c in ",;"):
        return '"' + v.replace('"', '\\"') + '"'
    return v


# ------------------------------------------------------------------
# Self-test with mock URL opener (offline, no network)
# ------------------------------------------------------------------
if __name__ == "__main__":
    import io
    import unittest.mock as mock

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # 1. topic missing -> False, no crash
    os.environ.pop("NTFY_TOPIC", None)
    NTFY_TOPIC = ""
    assert push(ZONE, "no topic", "should be dropped") is False
    print("  ok  push with no topic is dropped, no crash")

    # 2. disabled -> False, no crash
    os.environ["NTFY_TOPIC"] = "stock-alerts-f58fea644aedeff437"
    NTFY_TOPIC = os.environ["NTFY_TOPIC"]
    os.environ["NTFY_DISABLED"] = "1"
    NTFY_DISABLED = True
    assert push(ZONE, "disabled test", "should log only") is False
    print("  ok  push in disabled mode logs and returns False")

    # 3. enabled with mock urlopen -> True
    os.environ["NTFY_DISABLED"] = "0"
    NTFY_DISABLED = False

    class _MockResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with mock.patch("urllib.request.urlopen", return_value=_MockResp()) as m:
        ok = push(ZONE, "GOOGL entered zone",
                  "GOOGL 340.67 (<= 355)",
                  tags=["dollar"],
                  actions=[action_button("Acted", "acted"),
                           action_button("Ignored", "ignored"),
                           action_button("N/A", "na")])
        assert ok is True
        req = m.call_args[0][0]
        assert req.get_full_url() == "https://ntfy.sh/stock-alerts-f58fea644aedeff437"
        assert req.headers["Title"] == "GOOGL entered zone"
        assert req.headers["Priority"] == "4"
        assert req.headers["Tags"] == "dollar"
        assert "Actions" in req.headers
        print("  ok  push enabled sends correct request shape")

    # 4. non-ASCII title gets sanitized (ntfy header requires latin-1)
    with mock.patch("urllib.request.urlopen", return_value=_MockResp()) as m:
        push(DIGEST, "Digest — 20 Aug", "body with emoji 📊")
        req = m.call_args[0][0]
        # Title got sanitized
        assert "?" in req.headers["Title"] or "—" not in req.headers["Title"]
        print("  ok  non-ASCII title sanitized for header")

    # 5. network error returns False, no crash
    with mock.patch("urllib.request.urlopen",
                    side_effect=urllib.error.URLError("boom")):
        assert push(ZONE, "net down", "should return False") is False
        print("  ok  network error handled gracefully")

    print("\nAll ntfy_publish self-tests passed.")
