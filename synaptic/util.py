from __future__ import annotations
import hashlib, json, re, time, math
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def parse_iso_utc(ts: str) -> Optional[float]:
    """Parse timestamps like '2026-01-11T04:10:00Z' into epoch seconds (UTC)."""
    if not ts:
        return None
    ts = ts.strip()
    try:
        # NOTE: mktime interprets struct_time as local time. We use timegm to force UTC.
        import calendar
        return float(calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")))
    except Exception:
        return None

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))

def stable_id(prefix: str, payload: Dict[str, Any]) -> str:
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"{prefix}_{sha256_text(canon)[:16]}"

def tokenize(text: str):
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]

def clamp01(x: float) -> float:
    if x < 0.0: return 0.0
    if x > 1.0: return 1.0
    return x

def to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return str(obj)

def safe_truncate(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1] + "…"

def exp_decay_factor(*, last_ts: str, now_ts: str, half_life_days: float) -> float:
    """Return multiplier in (0,1] for exponential decay based on time since last use."""
    if half_life_days <= 0:
        return 1.0
    t0 = parse_iso_utc(last_ts) if last_ts else None
    t1 = parse_iso_utc(now_ts) if now_ts else None
    if t0 is None or t1 is None:
        return 1.0
    dt_days = max(0.0, (t1 - t0) / 86400.0)
    if dt_days <= 0:
        return 1.0
    lam = math.log(2.0) / float(half_life_days)
    return float(math.exp(-lam * dt_days))
