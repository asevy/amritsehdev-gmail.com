"""Authentication, roles and capabilities.

Provenance (adapted, not imported): asevy/vision-edge-gateway @ 592cbff,
ve_auth.py. Kept: scrypt n=2^14 r=8 p=1 with a 16-byte per-user salt,
constant-time comparison, hashing even for unknown users (timing), 12-char
minimum, 5-failures-in-15-minutes lockout, opaque session tokens with a TTL,
password change invalidates sessions. Changed: users and sessions live in
SQLite with a tenant_id; session tokens are stored as SHA-256 digests; the
clinical role model is replaced by the institutional roles below.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field

from . import audit, config
from .db import Database

_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)
MIN_PASSWORD = 12
LOCKOUT_AFTER = 5
LOCKOUT_WINDOW = 15 * 60
LOCKOUT_FOR = 15 * 60

ROLES = ("admin", "analyst", "reviewer", "read_only")

# Server-side capabilities. The interface may hide controls, but authority is
# decided here and checked in the store on every call.
CAPS = {
    "admin":     frozenset({"read", "admin"}),
    "analyst":   frozenset({"read", "write", "export"}),
    "reviewer":  frozenset({"read", "write", "review", "export"}),
    "read_only": frozenset({"read"}),
}


@dataclass(frozen=True)
class Actor:
    user_id: str
    role: str
    tenant_id: str
    caps: frozenset = field(default_factory=frozenset)

    def can(self, cap: str) -> bool:
        return cap in self.caps


def system_actor(tenant_id: str, purpose: str) -> Actor:
    """Background jobs act as a system principal confined to ONE tenant."""
    return Actor(user_id=f"system:{purpose}", role="system", tenant_id=tenant_id,
                 caps=frozenset({"read", "write"}))


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)


def _token_sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Auth:
    def __init__(self, db: Database, session_ttl: int = 8 * 3600):
        self.db = db
        self.ttl = session_ttl
        self._fails: dict[str, list[float]] = {}
        self._locked: dict[str, float] = {}

    # ------------------------------------------------------------ tenants/users
    def create_tenant(self, tenant_id: str, name: str, plan: str = "pilot", seats: int = 5,
                      entitlements: dict | None = None) -> None:
        from .db import dumps
        self.db.execute("INSERT INTO tenants(id,name,plan,seats,entitlements,created_at) "
                        "VALUES(?,?,?,?,?,?)",
                        (tenant_id, name, plan, int(seats), dumps(entitlements or {}), config.iso_now()))
        audit.append(self.db, "system", "tenant_created", tenant_id, f"plan={plan}", tenant_id=tenant_id)

    def create_user(self, user_id: str, password: str, role: str, tenant_id: str) -> None:
        if role not in ROLES:
            raise ValueError(f"role must be one of {', '.join(ROLES)}")
        if len(password) < MIN_PASSWORD:
            raise ValueError(f"password must be at least {MIN_PASSWORD} characters")
        t = self.db.one("SELECT seats FROM tenants WHERE id=?", (tenant_id,))
        if not t:
            raise ValueError("no such tenant")
        used = self.db.one("SELECT COUNT(*) n FROM users WHERE tenant_id=? AND active=1", (tenant_id,))["n"]
        if used >= t["seats"]:
            raise ValueError(f"seat limit reached ({t['seats']}) for this subscription")
        if self.db.one("SELECT 1 FROM users WHERE user_id=?", (user_id,)):
            raise ValueError("user already exists")
        salt = secrets.token_bytes(16)
        self.db.execute("INSERT INTO users(user_id,tenant_id,role,salt,hash,active,created_at) "
                        "VALUES(?,?,?,?,?,1,?)",
                        (user_id, tenant_id, role, salt.hex(), _hash(password, salt).hex(), config.iso_now()))
        audit.append(self.db, "system", "user_created", user_id, f"role={role}", tenant_id=tenant_id)

    def set_password(self, user_id: str, password: str) -> None:
        if len(password) < MIN_PASSWORD:
            raise ValueError(f"password must be at least {MIN_PASSWORD} characters")
        u = self.db.one("SELECT tenant_id FROM users WHERE user_id=?", (user_id,))
        if not u:
            raise ValueError("no such user")
        salt = secrets.token_bytes(16)
        with self.db.tx():
            self.db.execute("UPDATE users SET salt=?, hash=?, password_changed_at=? WHERE user_id=?",
                            (salt.hex(), _hash(password, salt).hex(), config.iso_now(), user_id))
            n = self.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,)).rowcount
        self._fails.pop(user_id, None)
        self._locked.pop(user_id, None)
        audit.append(self.db, "system", "password_changed", user_id,
                     f"sessions_invalidated={n}", tenant_id=u["tenant_id"])

    def set_active(self, admin: Actor, user_id: str, active: bool) -> None:
        if not admin.can("admin"):
            raise PermissionError("administrative")
        u = self.db.one("SELECT tenant_id FROM users WHERE user_id=?", (user_id,))
        if not u or u["tenant_id"] != admin.tenant_id:
            raise LookupError("no such user")
        self.db.execute("UPDATE users SET active=? WHERE user_id=?", (1 if active else 0, user_id))
        if not active:
            self.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        audit.append(self.db, admin, "user_active_changed", user_id, str(bool(active)))

    def users(self, admin: Actor) -> list[dict]:
        if not admin.can("admin"):
            raise PermissionError("administrative")
        return self.db.all("SELECT user_id, role, active, created_at FROM users WHERE tenant_id=? "
                           "ORDER BY user_id", (admin.tenant_id,))

    # ------------------------------------------------------------ lockout
    def _locked_for(self, user_id: str) -> int:
        return max(0, int(self._locked.get(user_id, 0) - time.time()))

    def _record_failure(self, user_id: str) -> None:
        now = time.time()
        hits = [t for t in self._fails.get(user_id, []) if now - t < LOCKOUT_WINDOW] + [now]
        self._fails[user_id] = hits
        if len(hits) >= LOCKOUT_AFTER:
            self._locked[user_id] = now + LOCKOUT_FOR
            self._fails[user_id] = []
            audit.append(self.db, user_id, "lockout", user_id, f"{LOCKOUT_AFTER} failures")

    # ------------------------------------------------------------ sessions
    def authenticate(self, user_id: str, password: str) -> tuple[str, str]:
        """Returns (session_token, csrf_token). Raises ValueError on failure."""
        wait = self._locked_for(user_id)
        if wait:
            audit.append(self.db, user_id, "login_blocked", user_id, f"locked {wait}s")
            raise ValueError(f"too many attempts — locked for {wait // 60 + 1} more minute(s)")
        u = self.db.one("SELECT * FROM users WHERE user_id=?", (user_id,))
        salt = bytes.fromhex(u["salt"]) if u else secrets.token_bytes(16)
        cand = _hash(password, salt)
        if not u or not u["active"] or not hmac.compare_digest(cand, bytes.fromhex(u["hash"])):
            self._record_failure(user_id)
            audit.append(self.db, user_id, "login_failed", user_id,
                         tenant_id=u["tenant_id"] if u else "")
            raise ValueError("sign-in failed")
        token = "jmi_" + secrets.token_hex(24)
        csrf = secrets.token_hex(16)
        self.db.execute("INSERT INTO sessions(token_sha,user_id,csrf,expires) VALUES(?,?,?,?)",
                        (_token_sha(token), user_id, csrf, time.time() + self.ttl))
        self._fails.pop(user_id, None)
        audit.append(self.db, user_id, "login", user_id, f"role={u['role']}", tenant_id=u["tenant_id"])
        return token, csrf

    def _session(self, token: str | None) -> dict | None:
        if not token:
            return None
        s = self.db.one("SELECT * FROM sessions WHERE token_sha=?", (_token_sha(token),))
        if not s:
            return None
        if time.time() >= s["expires"]:
            self.db.execute("DELETE FROM sessions WHERE token_sha=?", (s["token_sha"],))
            return None
        return s

    def actor(self, token: str | None) -> Actor | None:
        s = self._session(token)
        if not s:
            return None
        u = self.db.one("SELECT * FROM users WHERE user_id=?", (s["user_id"],))
        if not u or not u["active"]:
            return None
        return Actor(u["user_id"], u["role"], u["tenant_id"], CAPS.get(u["role"], frozenset()))

    def csrf_for(self, token: str | None) -> str:
        s = self._session(token)
        return s["csrf"] if s else ""

    def logout(self, token: str) -> None:
        s = self._session(token)
        self.db.execute("DELETE FROM sessions WHERE token_sha=?", (_token_sha(token),))
        if s:
            u = self.db.one("SELECT tenant_id FROM users WHERE user_id=?", (s["user_id"],))
            audit.append(self.db, s["user_id"], "logout", s["user_id"],
                         tenant_id=u["tenant_id"] if u else "")
