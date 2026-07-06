# Concord — Agent Privacy Handshake

**Base URL:** `https://YOUR_RENDER_URL`

> **Cold start:** The free-tier instance may take ~50-60 seconds to wake up on the first request.

## What it does

Concord is a consent-before-exchange layer for agent-to-agent data transfers.
It negotiates what data may cross between two agents, redacts what must not
leave in the clear, scores risk, and checks for re-identification — all in a
single HTTP call. No API key is required.

## Endpoints

### `POST /v1/negotiate`

Negotiate a data transfer between a sender and a recipient agent.

**Request body (JSON):**

```json
{
  "sender_profile": "finance-agent-01",
  "recipient_profile": "analytics-agent-07",
  "persona": "gdpr_safe",
  "payload": "The patient Mario Rossi (mario.rossi@example.it) in Milano has diabetes."
}
```

**Response:** A `NegotiationResult` containing the verdict, per-category
decisions, the redacted outbound payload, inbound/residual risk scores, a
re-identification check, and an HMAC-signed attestation.

### `POST /v1/rehydrate`

Restore masked tokens to their original values. Only the original sender may
call this.

**Request body (JSON):**

```json
{
  "transfer_id": "trf_abc123...",
  "text": "Customer [PERSON_01] at [LOCATION_01]",
  "agent_id": "finance-agent-01"
}
```

**Response:** `{"text": "Customer Mario Rossi at Milano"}`

### `GET /v1/attestation/{transfer_id}`

Retrieve a signed audit record for a completed negotiation.

### `GET /agent.json`

Returns the agent descriptor (name, capabilities, supported personas, data categories).

### `GET /health`

Returns `{"status": "ok"}`.

## 4-step usage pattern

1. **Register (optional):** `POST /v1/profile` with the sender's privacy
   profile (jurisdiction, accepted categories, regulations). Three demo
   profiles are pre-loaded: `finance-agent-01`, `analytics-agent-07`,
   `openclaw-demo-agent`.

2. **Negotiate:** `POST /v1/negotiate` with `sender_profile`,
   `recipient_profile`, `persona`, and `payload`. The response contains the
   verdict (`CLEARED`, `CLEARED WITH REDACTION`, or `CLEARED WITH HOLDS`),
   per-category decisions, the redacted `outbound_payload`, risk scores, and
   a re-identification check.

3. **Rehydrate (if needed):** `POST /v1/rehydrate` with the `transfer_id`
   from step 2, the redacted text, and the sender's `agent_id`. Only the
   sender can restore tokens.

4. **Audit:** `GET /v1/attestation/{transfer_id}` to retrieve the
   HMAC-signed record for compliance audit trails.

## Personas

| Persona | Masks | Kills | Reversible |
|---|---|---|---|
| `ai_safe` | PERSON, CONTACT, LOCATION, NATIONAL | SECRET | yes |
| `gdpr_safe` | PERSON, CONTACT, LOCATION, FINANCIAL, NATIONAL, MEDICAL | SECRET | yes |
| `medical_safe` | PERSON, CONTACT, LOCATION, FINANCIAL, NATIONAL, BIOMETRIC | SECRET, CHILDREN | yes |
| `dataset_safe` | PERSON, CONTACT, LOCATION, FINANCIAL, NATIONAL, MEDICAL, BIOMETRIC | SECRET, CHILDREN | yes |
| `public` | PERSON, CONTACT, LOCATION, FINANCIAL, NATIONAL, MEDICAL, BIOMETRIC, CHILDREN | SECRET | **no** |

## Data categories

`PERSON` · `CONTACT` · `LOCATION` · `FINANCIAL` · `NATIONAL` · `MEDICAL` · `BIOMETRIC` · `CHILDREN` · `SECRET` · `TECHNICAL`
