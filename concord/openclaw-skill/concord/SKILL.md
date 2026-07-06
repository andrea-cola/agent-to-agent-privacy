---
name: concord
description: Privacy-check any text before sharing it with another agent. Detects PII, negotiates what to mask/reject/share, and returns a safe redacted version.
user-invocable: true
---

# Concord — Agent Privacy Handshake

Use this skill whenever you need to **check, redact, or negotiate** what data is safe to share with another agent or service.

## Base URL

`https://concord-xybl.onrender.com`

> First request may take ~60s (free-tier cold start).

## When to use

- Before sending a message containing names, emails, medical info, financial data, or secrets to another agent
- When a user asks you to "anonymize", "redact", or "privacy-check" a text
- When forwarding data cross-border (EU → US) and GDPR compliance matters

## Endpoints

### 1. Negotiate (main endpoint)

```bash
curl -s -X POST "{{BASE_URL}}/v1/negotiate" \
  -H "Content-Type: application/json" \
  -d '{
    "sender_profile": "SENDER_AGENT_ID",
    "recipient_profile": "RECIPIENT_AGENT_ID",
    "persona": "PERSONA",
    "payload": "THE TEXT TO CHECK"
  }'
```

**Profiles** (pre-loaded): `finance-agent-01`, `analytics-agent-07`, `openclaw-demo-agent`

**Personas**: `ai_safe`, `gdpr_safe`, `medical_safe`, `dataset_safe`, `public`

**Response** contains: `verdict`, `decisions` (per-category action + reason), `outbound_payload` (safe redacted text), `transfer_id`, risk scores, attestation.

### 2. Rehydrate (restore masked tokens)

Only the original sender can restore. Use the `transfer_id` and `outbound_payload` from step 1.

```bash
curl -s -X POST "{{BASE_URL}}/v1/rehydrate" \
  -H "Content-Type: application/json" \
  -d '{
    "transfer_id": "TRANSFER_ID",
    "text": "THE REDACTED TEXT",
    "agent_id": "SENDER_AGENT_ID"
  }'
```

### 3. Attestation (audit trail)

```bash
curl -s "{{BASE_URL}}/v1/attestation/TRANSFER_ID"
```

## Workflow

1. Call `/v1/negotiate` with the text you want to share and who you're sharing it with
2. Use the `outbound_payload` from the response — it has PII masked with tokens like `[PERSON_01]`, `[CONTACT_01]`
3. If you need the original values back later, call `/v1/rehydrate` with the `transfer_id`
4. For audit, call `/v1/attestation/{transfer_id}` to get the signed record

## Example

User says: "Send Mario Rossi's medical record to the analytics team"

1. Call negotiate with `sender_profile: "openclaw-demo-agent"`, `recipient_profile: "analytics-agent-07"`, `persona: "gdpr_safe"`, and the text
2. The response will mask the name, redact medical terms, and reject secrets
3. Forward only the `outbound_payload` to the analytics team
