"""Negotiation engine — decides SHARE / MASK / REJECT per finding."""

from __future__ import annotations

from dataclasses import dataclass

from detectors import Finding
from personas import Persona, PERSONAS
from profiles import PrivacyProfile

CATEGORIES: dict[str, dict] = {
    "PERSON":    {"weight": 8},
    "CONTACT":   {"weight": 5},
    "LOCATION":  {"weight": 4},
    "FINANCIAL": {"weight": 12},
    "NATIONAL":  {"weight": 15},
    "MEDICAL":   {"weight": 18},
    "BIOMETRIC": {"weight": 20},
    "CHILDREN":  {"weight": 25},
    "SECRET":    {"weight": 25},
    "TECHNICAL": {"weight": 3},
}

PERSONAL_CATEGORIES = {"PERSON", "CONTACT", "LOCATION", "MEDICAL", "BIOMETRIC", "CHILDREN"}


@dataclass
class Decision:
    category: str
    action: str  # SHARE | MASK | REJECT
    token: str | None  # filled during redaction
    reason: str
    finding: Finding


def cross_border(sender: PrivacyProfile, recipient: PrivacyProfile) -> bool:
    """True when the sender requires GDPR but the recipient is not GDPR-compliant
    and they are in different regions."""
    sender_requires_gdpr = "GDPR" in sender.requires
    recipient_gdpr = recipient.regulations.get("GDPR", False)
    different_region = sender.jurisdiction.get("region") != recipient.jurisdiction.get("region")
    return sender_requires_gdpr and not recipient_gdpr and different_region


def _regs_ok(sender: PrivacyProfile, recipient: PrivacyProfile) -> bool:
    """Check that the recipient satisfies all regulations the sender requires."""
    for reg in sender.requires:
        if not recipient.regulations.get(reg, False):
            return False
    return True


def negotiate(
    findings: list[Finding],
    sender: PrivacyProfile,
    recipient: PrivacyProfile,
    persona_name: str,
) -> list[Decision]:
    persona = PERSONAS[persona_name]
    xb = cross_border(sender, recipient)
    decisions: list[Decision] = []

    for f in findings:
        cat = f.category

        if cat in persona.kill:
            decisions.append(Decision(
                category=cat, action="REJECT", token=None,
                reason=f"{cat} is in the kill set — never forwarded",
                finding=f,
            ))
        elif cat in recipient.rejects:
            decisions.append(Decision(
                category=cat, action="REJECT", token=None,
                reason=f"recipient rejects {cat}",
                finding=f,
            ))
        elif cat in persona.mask:
            reason = f"persona '{persona.name}' masks {cat}"
            if xb and cat in PERSONAL_CATEGORIES:
                reason += " (cross-border transfer without GDPR adequacy)"
            decisions.append(Decision(
                category=cat, action="MASK", token=None, reason=reason, finding=f,
            ))
        elif cat in recipient.accepts and _regs_ok(sender, recipient):
            if xb and cat in PERSONAL_CATEGORIES:
                decisions.append(Decision(
                    category=cat, action="MASK", token=None,
                    reason=f"cross-border downgrade: {cat} would be SHARE but "
                           f"recipient lacks GDPR adequacy",
                    finding=f,
                ))
            else:
                decisions.append(Decision(
                    category=cat, action="SHARE", token=None,
                    reason=f"{cat} accepted by recipient and regulations satisfied",
                    finding=f,
                ))
        else:
            decisions.append(Decision(
                category=cat, action="MASK", token=None,
                reason=f"{cat} not in accepted set — masked by default",
                finding=f,
            ))

    return decisions


def verdict(decisions: list[Decision]) -> str:
    actions = {d.action for d in decisions}
    if "REJECT" in actions:
        return "CLEARED WITH HOLDS"
    if "MASK" in actions:
        return "CLEARED WITH REDACTION"
    return "CLEARED"
