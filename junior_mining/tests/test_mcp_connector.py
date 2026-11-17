"""Claude connector (MCP): read-only, tenant-scoped, policy-scanned, audited —
tested through the real MCP 2.x server object and once over a real stdio
transport with the MCP client SDK."""

import json
import os
import sys
from pathlib import Path

import anyio
import pytest

from jmi import audit, mcp_server, policy

pytest.importorskip("mcp")


def _server(ws, user):
    token = ws.auth.create_api_token(user, "test")
    actor = ws.auth.actor_for_api_token(token)
    return mcp_server.build_server(ws.store, actor), token, actor


def _call(server, name, args=None):
    async def go():
        return await server.call_tool(name, args or {})
    r = anyio.run(go)
    return json.loads(r.content[0].text)


def test_token_is_hashed_read_only_and_revocable(ws):
    token = ws.auth.create_api_token("reviewer.a", "desktop")
    assert token.startswith("jmit_")
    assert token not in "\n".join(ws.db.conn.iterdump())
    actor = ws.auth.actor_for_api_token(token)
    assert actor.tenant_id == "alpha" and actor.caps == frozenset({"read"})     # even a reviewer's token is read-only
    tid = ws.auth.list_api_tokens(actor)[0]["id"]
    ws.auth.revoke_api_token(actor, tid)
    assert ws.auth.actor_for_api_token(token) is None
    assert ws.auth.actor_for_api_token("jmit_" + "0" * 48) is None


def test_tools_are_all_read_only(ws):
    server, _, _ = _server(ws, "analyst.a")

    async def go():
        return await server.list_tools()
    tools = anyio.run(go)
    names = {t.name for t in tools}
    assert names == {"list_companies", "get_facts", "ask", "get_coverage", "get_risks", "get_comparison",
                     "get_memo", "search_documents", "list_definitions"}
    assert all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in tools)


def test_facts_carry_sources_and_default_to_approved(approved):
    server, _, _ = _server(approved, "analyst.a")
    out = _call(server, "get_facts", {"company": "Halvard Peak Gold Corp.", "metric": "cash_unrestricted"})
    facts = out["data"]["facts"]
    assert facts and all(f["workflow_state"] == "reviewer_approved" for f in facts)
    assert facts[0]["source"]["quote"] and facts[0]["source"]["page"] and facts[0]["attribution"]
    assert "not established" in out["data"]["note"] and out["notice"].startswith("Evidence records")
    assert policy.scan(out) == []


def test_unapproved_only_when_asked(ws):
    server, _, _ = _server(ws, "analyst.a")
    assert _call(server, "get_facts", {"company": "Halvard Peak Gold Corp."})["data"]["facts"] == []
    some = _call(server, "get_facts", {"company": "Halvard Peak Gold Corp.", "include_unapproved": True})
    assert some["data"]["facts"] and all(f["workflow_state"] != "reviewer_approved" for f in some["data"]["facts"])


def test_ask_keeps_refusals_and_not_found(approved):
    server, _, _ = _server(approved, "analyst.a")
    assert _call(server, "ask", {"company": "Halvard Peak Gold Corp.", "question": "Should we buy it?"})["data"]["status"] == "declined"
    nf = _call(server, "ask", {"company": "Halvard Peak Gold Corp.", "question": "What is the 2027 production guidance?"})
    assert nf["data"]["status"] == "not_found"


def test_other_firm_sees_only_its_own_records(approved):
    server, _, _ = _server(approved, "analyst.b")
    listed = _call(server, "list_companies")["data"]
    assert [c["name"] for c in listed] == ["Halvard Peak Gold Corp."] and listed[0]["company_id"] == approved.HPG_B
    own = _call(server, "get_facts", {"company": "Halvard Peak Gold Corp."})["data"]["facts"]
    assert own == []                                        # beta's same-named company has no approved facts

    async def go():
        return await server.call_tool("get_facts", {"company": approved.HPG})
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError) as e:
        anyio.run(go)
    assert "no company named" in str(e.value) and "18.4" not in str(e.value)


def test_calls_are_audited_as_the_user(approved):
    server, _, _ = _server(approved, "analyst.a")
    _call(server, "get_risks", {"company": "Halvard Peak Gold Corp."})
    ev = [e for e in audit.tail(approved.db, "alpha", 10) if e["action"] == "mcp_get_risks"]
    assert ev and ev[0]["actor"] == "analyst.a"


def test_connector_refuses_a_non_read_only_actor(ws):
    with pytest.raises(mcp_server.ConnectorError):
        mcp_server.Connector(ws.store, ws.A)


def test_real_stdio_round_trip(approved):
    """Spawn `python -m jmi mcp` and talk to it with the MCP client SDK."""
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    approved.db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    token = approved.auth.create_api_token("analyst.a", "stdio test")
    root = Path(__file__).resolve().parent.parent
    params = StdioServerParameters(command=sys.executable, args=["-m", "jmi", "mcp"], cwd=str(root),
                                   env={**os.environ, "JMI_DATA_DIR": str(approved.path), "JMI_API_TOKEN": token})

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                r = await session.call_tool("get_facts", {"company": "Halvard Peak Gold Corp.", "metric": "npv"})
                return [t.name for t in tools.tools], json.loads(r.content[0].text)
    names, out = anyio.run(go)
    assert "ask" in names and out["data"]["facts"]
    assert {f["statement"].split(" reports ")[0] for f in out["data"]["facts"]} == {"Halvard Peak Gold Corp."}
