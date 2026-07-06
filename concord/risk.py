"""Risk scoring — inbound and residual, pure arithmetic."""

from __future__ import annotations

from detectors import Finding
from negotiate import CATEGORIES, Decision


def inbound_risk(findings: list[Finding], is_cross_border: bool) -> int:
    """Raw risk score before any negotiation decisions."""
    base = sum(CATEGORIES.get(f.category, {}).get("weight", 0) for f in findings)
    penalty = 15 if is_cross_border else 0
    return min(100, base + penalty)


def residual_risk(decisions: list[Decision], is_cross_border: bool) -> int:
    """Risk score after negotiation — only SHARE decisions contribute."""
    shared = [d for d in decisions if d.action == "SHARE"]
    base = sum(CATEGORIES.get(d.category, {}).get("weight", 0) for d in shared)
    penalty = 6 if shared and is_cross_border else 0
    return min(100, base + penalty)


def risk_band(score: int) -> str:
    if score <= 32:
        return "low"
    if score <= 65:
        return "elevated"
    return "high"
