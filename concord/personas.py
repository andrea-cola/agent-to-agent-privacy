"""Persona definitions — each maps to mask/kill sets for the negotiation engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Persona:
    name: str
    mask: frozenset[str] = field(default_factory=frozenset)
    kill: frozenset[str] = field(default_factory=frozenset)
    reversible: bool = True


PERSONAS: dict[str, Persona] = {
    "ai_safe": Persona(
        name="ai_safe",
        mask=frozenset({"PERSON", "CONTACT", "LOCATION", "NATIONAL"}),
        kill=frozenset({"SECRET"}),
    ),
    "gdpr_safe": Persona(
        name="gdpr_safe",
        mask=frozenset({"PERSON", "CONTACT", "LOCATION", "FINANCIAL", "NATIONAL", "MEDICAL"}),
        kill=frozenset({"SECRET"}),
    ),
    "medical_safe": Persona(
        name="medical_safe",
        mask=frozenset({"PERSON", "CONTACT", "LOCATION", "FINANCIAL", "NATIONAL", "BIOMETRIC"}),
        kill=frozenset({"SECRET", "CHILDREN"}),
    ),
    "dataset_safe": Persona(
        name="dataset_safe",
        mask=frozenset(
            {"PERSON", "CONTACT", "LOCATION", "FINANCIAL", "NATIONAL", "MEDICAL", "BIOMETRIC"}
        ),
        kill=frozenset({"SECRET", "CHILDREN"}),
    ),
    "public": Persona(
        name="public",
        mask=frozenset(
            {
                "PERSON",
                "CONTACT",
                "LOCATION",
                "FINANCIAL",
                "NATIONAL",
                "MEDICAL",
                "BIOMETRIC",
                "CHILDREN",
            }
        ),
        kill=frozenset({"SECRET"}),
        reversible=False,
    ),
}
