"""Redaction engine + in-memory vault for reversible masking."""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field

from negotiate import Decision
from personas import Persona


@dataclass
class VaultEntry:
    owner_agent_id: str
    mapping: dict[str, str]  # token -> original text
    created_at: float
    ttl_seconds: int


VAULT: dict[str, VaultEntry] = {}


def _parse_retention(policy: str) -> int:
    """Parse a retention policy string like '30d' or '24h' into seconds."""
    policy = policy.strip().lower()
    m = re.match(r"^(\d+)\s*(d|h|m)$", policy)
    if not m:
        return 86400  # default 24h
    value, unit = int(m.group(1)), m.group(2)
    multipliers = {"d": 86400, "h": 3600, "m": 60}
    return value * multipliers[unit]


def purge_expired() -> int:
    """Remove expired vault entries. Returns count of purged entries."""
    now = time.time()
    expired = [
        tid for tid, entry in VAULT.items()
        if now - entry.created_at > entry.ttl_seconds
    ]
    for tid in expired:
        del VAULT[tid]
    return len(expired)


def apply_redaction(
    payload: str,
    decisions: list[Decision],
    sender_agent_id: str,
    persona: Persona,
    retention_policy: str = "24h",
) -> tuple[str, str]:
    """Replace MASK spans with tokens, write vault if reversible.

    Returns (redacted_text, transfer_id).
    """
    purge_expired()

    transfer_id = f"trf_{uuid.uuid4().hex[:12]}"
    mapping: dict[str, str] = {}
    counters: dict[str, int] = {}

    # Assign tokens to MASK decisions in forward order so numbering is stable
    for d in decisions:
        if d.action == "MASK":
            cat = d.category
            counters[cat] = counters.get(cat, 0) + 1
            d.token = f"[{cat}_{counters[cat]:02d}]"

    # Apply all replacements in reverse order to preserve character offsets
    actionable = [d for d in decisions if d.action in ("MASK", "REJECT")]
    actionable.sort(key=lambda d: d.finding.start, reverse=True)

    redacted = payload
    for d in actionable:
        original = redacted[d.finding.start:d.finding.end]
        if d.action == "MASK":
            mapping[d.token] = original  # type: ignore[arg-type]
            redacted = redacted[:d.finding.start] + d.token + redacted[d.finding.end:]
        else:
            redacted = redacted[:d.finding.start] + "[REDACTED]" + redacted[d.finding.end:]

    if persona.reversible and mapping:
        ttl = _parse_retention(retention_policy)
        VAULT[transfer_id] = VaultEntry(
            owner_agent_id=sender_agent_id,
            mapping=mapping,
            created_at=time.time(),
            ttl_seconds=ttl,
        )

    return redacted, transfer_id


class RehydrationError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def rehydrate(transfer_id: str, text: str, requesting_agent_id: str) -> str:
    """Restore masked tokens to original values. Only the original sender may call this."""
    purge_expired()

    entry = VAULT.get(transfer_id)
    if entry is None:
        raise RehydrationError(
            f"Transfer {transfer_id} not found or expired", status_code=410
        )

    if entry.owner_agent_id != requesting_agent_id:
        raise RehydrationError(
            "Only the original sender may rehydrate", status_code=403
        )

    result = text
    for token, original in entry.mapping.items():
        result = result.replace(token, original)
    return result
