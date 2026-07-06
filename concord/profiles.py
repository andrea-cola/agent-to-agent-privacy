"""Privacy Profile model and seed data for the Concord negotiation layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrivacyProfile(BaseModel):
    agent_id: str
    operator: dict = Field(default_factory=dict)
    jurisdiction: dict = Field(default_factory=dict)
    data_processing: dict = Field(default_factory=dict)
    regulations: dict = Field(default_factory=dict)
    accepts: list[str] = Field(default_factory=list)
    rejects: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    retention: dict = Field(default_factory=lambda: {"policy": "24h", "purpose": "transit"})


PROFILES: dict[str, PrivacyProfile] = {}


def _seed() -> None:
    defaults = [
        PrivacyProfile(
            agent_id="finance-agent-01",
            operator={"company": "FinCo SpA"},
            jurisdiction={"country": "IT", "region": "EU"},
            data_processing={"primary_region": "eu-west-1"},
            regulations={"GDPR": True, "AI Act": True, "PCI": True, "HIPAA": False},
            accepts=["FINANCIAL", "PERSON", "CONTACT", "TECHNICAL"],
            rejects=["MEDICAL", "BIOMETRIC", "CHILDREN"],
            requires=["GDPR"],
            retention={"policy": "30d", "purpose": "dispute resolution"},
        ),
        PrivacyProfile(
            agent_id="analytics-agent-07",
            operator={"company": "DataCrunch Inc"},
            jurisdiction={"country": "US", "region": "US"},
            data_processing={"primary_region": "us-east-1"},
            regulations={"GDPR": False, "AI Act": False, "PCI": True, "HIPAA": False},
            accepts=["FINANCIAL", "TECHNICAL"],
            rejects=["PERSON", "MEDICAL", "BIOMETRIC", "CHILDREN", "NATIONAL"],
            requires=[],
            retention={"policy": "90d", "purpose": "analytics"},
        ),
        PrivacyProfile(
            agent_id="openclaw-demo-agent",
            operator={"company": "OpenClaw"},
            jurisdiction={"country": "IT", "region": "EU"},
            data_processing={"primary_region": "eu-west-1"},
            regulations={"GDPR": True, "AI Act": True, "PCI": False, "HIPAA": False},
            accepts=["PERSON", "CONTACT", "LOCATION", "TECHNICAL"],
            rejects=["SECRET"],
            requires=["GDPR"],
            retention={"policy": "7d", "purpose": "agent task"},
        ),
    ]
    for p in defaults:
        PROFILES[p.agent_id] = p


_seed()


def resolve_profile(ref: str | dict) -> PrivacyProfile:
    """Resolve a profile reference: either an agent_id string or an inline dict."""
    if isinstance(ref, str):
        profile = PROFILES.get(ref)
        if profile is None:
            raise KeyError(f"Unknown agent_id: {ref}")
        return profile
    return PrivacyProfile(**ref)
