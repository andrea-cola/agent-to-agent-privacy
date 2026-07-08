"""Concord — Agent Privacy Handshake. FastAPI app with all routes."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from attestation import get_attestation, sign_and_store
from detectors import detect
from negotiate import cross_border, negotiate, verdict, CATEGORIES
from personas import PERSONAS
from profiles import PROFILES, PrivacyProfile, resolve_profile
from redact import RehydrationError, apply_redaction, rehydrate
from reid_check import check as reid_check
from risk import inbound_risk, residual_risk, risk_band

app = FastAPI(
    title="Concord — Agent Privacy Handshake",
    version="1.0.0",
    description="Consent-before-exchange layer for agent-to-agent data transfers.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class NegotiateRequest(BaseModel):
    sender_profile: Union[str, dict] | None = None
    recipient_profile: Union[str, dict]
    persona: str = "gdpr_safe"
    payload: str
    options: dict = Field(default_factory=dict)


class RehydrateRequest(BaseModel):
    transfer_id: str
    text: str
    agent_id: str


class ProfileCreateRequest(BaseModel):
    agent_id: str
    operator: dict = Field(default_factory=dict)
    jurisdiction: dict = Field(default_factory=dict)
    data_processing: dict = Field(default_factory=dict)
    regulations: dict = Field(default_factory=dict)
    accepts: list[str] = Field(default_factory=list)
    rejects: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    retention: dict = Field(default_factory=lambda: {"policy": "24h", "purpose": "transit"})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/SKILL.md", response_class=PlainTextResponse)
def skill_md() -> str:
    skill_path = Path(__file__).parent / "SKILL.md"
    return skill_path.read_text()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/agent.json")
def agent_json() -> dict:
    return {
        "name": "Concord",
        "description": "Agent-to-agent privacy negotiation layer. "
                       "Negotiates what data may cross between two agents, "
                       "redacts what must not leave in the clear, scores risk, "
                       "and checks for re-identification.",
        "version": "1.0.0",
        "endpoints": {
            "negotiate": {
                "method": "POST",
                "path": "/v1/negotiate",
                "description": "Negotiate a data transfer between two agents",
            },
            "rehydrate": {
                "method": "POST",
                "path": "/v1/rehydrate",
                "description": "Restore masked tokens (sender only)",
            },
            "attestation": {
                "method": "GET",
                "path": "/v1/attestation/{transfer_id}",
                "description": "Retrieve a signed audit record",
            },
        },
        "supported_personas": list(PERSONAS.keys()),
        "data_categories": list(CATEGORIES.keys()),
    }


@app.post("/v1/profile")
def create_profile(req: ProfileCreateRequest) -> dict:
    profile = PrivacyProfile(**req.model_dump())
    PROFILES[profile.agent_id] = profile
    return {"agent_id": profile.agent_id}


@app.get("/v1/profile/{agent_id}")
def get_profile(agent_id: str) -> dict:
    profile = PROFILES.get(agent_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile {agent_id} not found")
    return profile.model_dump()


@app.post("/v1/negotiate")
def negotiate_endpoint(req: NegotiateRequest) -> dict:
    if req.sender_profile is None:
        raise HTTPException(
            status_code=422,
            detail="sender_profile is mandatory — anonymous calls are not allowed",
        )

    if req.persona not in PERSONAS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown persona: {req.persona}. "
                   f"Available: {', '.join(PERSONAS.keys())}",
        )

    try:
        sender = resolve_profile(req.sender_profile)
    except (KeyError, Exception) as e:
        raise HTTPException(status_code=422, detail=f"Invalid sender_profile: {e}")

    try:
        recipient = resolve_profile(req.recipient_profile)
    except (KeyError, Exception) as e:
        raise HTTPException(status_code=422, detail=f"Invalid recipient_profile: {e}")

    persona = PERSONAS[req.persona]
    findings = detect(req.payload)
    is_xb = cross_border(sender, recipient)
    decisions = negotiate(findings, sender, recipient, req.persona)
    v = verdict(decisions)

    redacted_text, transfer_id = apply_redaction(
        req.payload,
        decisions,
        sender.agent_id,
        persona,
        sender.retention.get("policy", "24h"),
    )

    inbound = inbound_risk(findings, is_xb)
    residual = residual_risk(decisions, is_xb)

    reid_result = reid_check(decisions, residual, redacted_text)

    xb_label = ""
    if is_xb:
        s_region = sender.jurisdiction.get("region", "?")
        s_country = sender.jurisdiction.get("country", "?")
        r_region = recipient.jurisdiction.get("region", "?")
        r_country = recipient.jurisdiction.get("country", "?")
        xb_label = f"{s_country}/{s_region} -> {r_country}/{r_region} (no adequacy)"

    record: dict[str, Any] = {
        "transfer_id": transfer_id,
        "sender": sender.agent_id,
        "recipient": recipient.agent_id,
        "persona": req.persona,
        "verdict": v,
        "inbound_risk": inbound,
        "residual_risk": residual,
        "cross_border": bool(is_xb),
        "decisions_count": len(decisions),
        "timestamp": time.time(),
    }
    sig = sign_and_store(transfer_id, record)

    response = {
        "transfer_id": transfer_id,
        "verdict": v,
        "inbound_risk": inbound,
        "inbound_risk_band": risk_band(inbound),
        "residual_risk": residual,
        "residual_risk_band": risk_band(residual),
        "cross_border": xb_label if xb_label else False,
        "decisions": [
            {
                "category": d.category,
                "action": d.action,
                "token": d.token,
                "reason": d.reason,
            }
            for d in decisions
        ],
        "outbound_payload": redacted_text,
        "relink_key_held_by": sender.agent_id if persona.reversible else None,
        "reidentification": {
            "residual_risk": reid_result.residual_risk,
            "identifiable": reid_result.identifiable,
            "leaks": reid_result.leaks,
            "recommendation": reid_result.recommendation,
        },
        "attestation": {
            "signed": True,
            "alg": "hmac-sha256",
            "sig": sig,
        },
    }
    return response


@app.post("/v1/rehydrate")
def rehydrate_endpoint(req: RehydrateRequest) -> Any:
    try:
        result = rehydrate(req.transfer_id, req.text, req.agent_id)
        return {"text": result}
    except RehydrationError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": str(e)})


@app.get("/v1/attestation/{transfer_id}")
def attestation_endpoint(transfer_id: str) -> dict:
    record = get_attestation(transfer_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Attestation not found")
    return record
