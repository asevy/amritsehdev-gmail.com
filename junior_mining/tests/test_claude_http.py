"""Claude settings, connector tokens and Claude actions over real HTTP."""

from jmi import claude, policy


def test_only_admin_changes_claude_settings(http):
    an, adm = http.client("analyst.a"), http.client("admin.a")
    s, _ = an.post("claude.settings", {"enabled": "1"})
    assert s == 403
    s, _, _ = an.get("/admin/claude")
    assert s == 403
    s, body = adm.post("claude.settings", {"enabled": "1", "api_key_env": "JMI_KEY_FIRM_A", "model": "claude-opus-5-5"})
    assert s == 200 and body["result"]["enabled"] is True
    s, page, _ = adm.get("/admin/claude")
    assert s == 200 and b"JMI_KEY_FIRM_A" in page and b"NOT SET" in page
    assert policy.scan_html(page.decode()) == []
    s, body = adm.post("claude.settings", {"enabled": "1", "api_key_env": "sk-ant-not-a-name"})
    assert s == 400


def test_claude_actions_refused_when_disabled(http):
    an = http.client("analyst.a")
    v = http.store.find(http.A, "document_versions")[0]
    s, body = an.post("claude.propose", {"version_id": v["id"]})
    assert s == 400 and "not enabled" in body["message"]


def test_claude_action_on_other_firms_document_is_404(http):
    claude.set_config(http.store, http.ADM, enabled=True)
    b = http.client("analyst.b")
    v = http.store.find(http.A, "document_versions")[0]
    s, _ = b.post("claude.propose", {"version_id": v["id"]})
    assert s == 404


def test_connector_token_shown_once_and_revocable(http):
    an = http.client("analyst.a")
    s, page, _ = an.get("/account")
    assert s == 200 and b"read-only" in page and b"claude mcp add" in page
    assert policy.scan_html(page.decode()) == []
    s, created = an.post("token.create", {"label": "Desktop"})
    assert s == 200
    tokens = http.auth.list_api_tokens(http.A)
    assert len(tokens) == 1 and tokens[0]["label"] == "Desktop"
    s, page, _ = an.get("/account")
    assert b"jmit_" not in page                         # never displayed again
    s, _ = an.post("token.revoke", {"token_id": tokens[0]["id"]})
    assert s == 200 and http.auth.list_api_tokens(http.A)[0]["revoked_at"]
    b = http.client("analyst.b")
    s, _ = b.post("token.revoke", {"token_id": tokens[0]["id"]})
    assert s == 404
