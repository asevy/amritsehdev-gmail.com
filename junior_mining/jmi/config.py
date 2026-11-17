"""Runtime settings and the clock.

Every timestamp the application writes goes through `now()` so that tests and
demonstrations can pin the analysis time. Analysis time is always shown next
to evidence cutoff — an output must never look more current than its inputs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent


@dataclass
class Settings:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8780
    # A company's coverage is "stale" when its newest reviewed document is older
    # than this many days. Configurable per deployment; not a judgement of quality.
    freshness_days: int = 120
    # A market-data upload older than this is shown as stale market data.
    market_data_stale_days: int = 7
    session_ttl_seconds: int = 8 * 60 * 60
    max_upload_bytes: int = 50_000_000
    # "none" = deterministic extraction only. No provider is configured in the
    # development environment; see docs/DATA_SOURCES.md.
    model_provider: str = "none"
    plans_file: Path | None = None


def load_settings(env: dict | None = None) -> Settings:
    env = dict(os.environ if env is None else env)
    data_dir = Path(env.get("JMI_DATA_DIR") or (PROJECT_DIR / "data"))
    plans = env.get("JMI_PLANS_FILE")
    return Settings(
        data_dir=data_dir,
        host=env.get("JMI_HOST", "127.0.0.1"),
        port=int(env.get("JMI_PORT", "8780")),
        freshness_days=int(env.get("JMI_FRESHNESS_DAYS", "120")),
        market_data_stale_days=int(env.get("JMI_MARKET_DATA_STALE_DAYS", "7")),
        session_ttl_seconds=int(env.get("JMI_SESSION_TTL_SECONDS", str(8 * 3600))),
        max_upload_bytes=int(env.get("JMI_MAX_UPLOAD_BYTES", "50000000")),
        model_provider=env.get("JMI_MODEL_PROVIDER", "none"),
        plans_file=Path(plans) if plans else None,
    )


# ---------------------------------------------------------------- the clock
_CLOCK: datetime | None = None


def set_clock(dt: datetime | None) -> None:
    """Pin the clock (tests and scripted demonstrations). None releases it."""
    global _CLOCK
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    _CLOCK = dt


def now() -> datetime:
    return _CLOCK or datetime.now(timezone.utc)


def today() -> date:
    return now().date()


def iso_now() -> str:
    return now().strftime("%Y-%m-%dT%H:%M:%SZ")
