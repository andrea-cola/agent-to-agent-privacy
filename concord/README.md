# Concord — Agent Privacy Handshake

Concord is a consent-before-exchange agent privacy layer, implemented as a single FastAPI service.

## Features

- **PII Detection**: Identifies various categories of Personally Identifiable Information (PII) using regex and heuristic detectors.
- **Privacy Negotiation**: Determines sharing decisions (SHARE, MASK, REJECT) based on sender and recipient profiles, personas, and cross-border data transfer rules.
- **Data Redaction**: Masks sensitive data with tokens or redacts it completely, with optional reversibility.
- **Risk Assessment**: Calculates inbound and residual risk scores for data transfers.
- **Re-identification Check**: Performs deterministic quasi-identifier checks to prevent re-identification.
- **Attestation**: Provides HMAC-SHA256 signed attestations for data transfer records.
- **FastAPI Service**: Exposes all functionalities via a RESTful API.

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### Running the service

```bash
uvicorn main:app --host 0.0.0.0 --port 8787
```

### API Endpoints

- `GET /health` — Health check.
- `GET /agent.json` — Agent descriptor (capabilities, personas, categories).
- `POST /v1/negotiate` — Main endpoint for privacy negotiation and data redaction.
- `POST /v1/rehydrate` — Restore masked tokens (sender only).
- `GET /v1/attestation/{transfer_id}` — Retrieve a signed audit record.
- `POST /v1/profile` / `GET /v1/profile/{id}` — Profile CRUD.

### Pre-loaded demo profiles

| Agent ID | Jurisdiction | Notable rules |
|---|---|---|
| `finance-agent-01` | IT / EU | GDPR required, accepts FINANCIAL/PERSON/CONTACT/TECHNICAL, rejects MEDICAL/BIOMETRIC/CHILDREN |
| `analytics-agent-07` | US / US | No GDPR, accepts FINANCIAL/TECHNICAL only, rejects most personal categories |
| `openclaw-demo-agent` | IT / EU | GDPR required, accepts PERSON/CONTACT/LOCATION/TECHNICAL, rejects SECRET |

### Known limitations

- PII detection uses regex and keyword heuristics, not NER. Recall is imperfect.
- All state is in-memory — restarts clear the vault and attestation store.
- Attestation is HMAC-SHA256 (symmetric key) rather than public-key signatures.
- This is a hackathon prototype, not a legal compliance guarantee.

## NandaHack Submission

This service addresses the need for a robust privacy layer in agent-to-agent communication for the NandaHack competition.
