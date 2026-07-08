# Concord — Demo Story

## The Scene

Two AI agents need to collaborate.

**Agent A** — `finance-agent-01` — works for an Italian financial institution operating under GDPR.
It has just processed a customer case and wants to share context with an analytics partner.

**Agent B** — `analytics-agent-07` — is a US-based data analytics service.
It accepts financial and technical data only. No personal names, no medical data, no national IDs.

They have never spoken before. There is no shared trust agreement. One is in the EU, the other in the US.

**The question:** Can they share data at all — and if so, what exactly?

---

## Act 1 — The Handshake

Agent A wants to forward this case note to Agent B:

> *"Customer Mario Rossi, mario.rossi@example.it, located in Milano, IBAN IT60X0542811101000000123456, card 4539 1488 0343 6467. Medical diagnosis: type-2 diabetes, treatment: metformin. Secret key: sk-live-9fJ2kXyz. National ID: RSSMRA85M01F205Z."*

Before sending a single byte, Agent A calls Concord:

```bash
POST /v1/negotiate
{
  "sender_profile":    "finance-agent-01",
  "recipient_profile": "analytics-agent-07",
  "persona":           "gdpr_safe",
  "payload":           "Customer Mario Rossi, mario.rossi@example.it ..."
}
```

---

## Act 2 — The Verdict

Concord scans the payload, detects 10 PII findings across 6 categories, and negotiates each one:

| Category | Finding | Decision | Why |
|---|---|---|---|
| PERSON | Mario Rossi | **REJECT** | analytics-agent-07 rejects all personal names |
| CONTACT | mario.rossi@example.it | **MASK** → `[CONTACT_01]` | GDPR persona masks contact cross-border |
| LOCATION | Milano | **MASK** → `[LOCATION_01]` | GDPR persona masks location cross-border |
| FINANCIAL | IBAN IT60X… | **MASK** → `[FINANCIAL_01]` | GDPR persona masks financial data |
| FINANCIAL | card 4539… | **MASK** → `[FINANCIAL_02]` | GDPR persona masks financial data |
| NATIONAL | RSSMRA85… | **REJECT** | analytics-agent-07 rejects national IDs |
| MEDICAL | diagnosis, diabetes, metformin | **REJECT** | analytics-agent-07 rejects medical data |
| SECRET | sk-live-9fJ2kXyz | **REJECT** | Kill set — never forwarded under any persona |

**Verdict: `CLEARED WITH HOLDS`**
**Inbound risk: 100 (high) → Residual risk: 0 (low)**
**Cross-border flag: IT/EU → US/US (no GDPR adequacy)**

The safe payload Agent A can forward:

> *"Customer [REDACTED], [CONTACT_01], located in [LOCATION_01], IBAN [FINANCIAL_01], card [FINANCIAL_02]. Medical [REDACTED]: type-2 [REDACTED], [REDACTED]: metformin. Secret key: [REDACTED]. National ID: [REDACTED]."*

The API secret never left. The name never left. The medical record never left.

---

## Act 3 — The Recall

Two hours later, a compliance officer at Agent A's institution needs to reconstruct the original message for an audit trail.

They call:

```bash
POST /v1/rehydrate
{
  "transfer_id": "trf_8fe52f7555c0",
  "text":        "Customer [REDACTED], [CONTACT_01], ...",
  "agent_id":    "finance-agent-01"
}
```

Concord checks: same sender? Yes. TTL expired? No.

Response: the original text, fully restored.

Agent B tries the same call. Gets `403 Forbidden` — only the original sender holds the key.

---

## Act 4 — The Audit

The regulator asks for proof that the transfer was handled correctly.

```bash
GET /v1/attestation/trf_8fe52f7555c0
```

Response: a signed record — sender, recipient, persona, verdict, risk scores, timestamp — all HMAC-SHA256 signed at transfer time. Immutable. Tamper-evident.

```json
{
  "sender": "finance-agent-01",
  "recipient": "analytics-agent-07",
  "verdict": "CLEARED WITH HOLDS",
  "inbound_risk": 100,
  "residual_risk": 0,
  "cross_border": true,
  "signed": true,
  "alg": "hmac-sha256",
  "sig": "eeb38d0a..."
}
```

---

## The Point

No human reviewed this transfer. No policy document was consulted. No compliance team was cc'd.

Two agents negotiated the terms of a data exchange in under a second, enforced GDPR cross-border rules automatically, and produced a signed audit trail — all without the data ever reaching a party that wasn't supposed to see it.

That is what Concord does.

---

## Run It Yourself

```bash
# Against the live service
./concord/demo.sh https://concord-xybl.onrender.com

# Or locally
pip install -r concord/requirements.txt
uvicorn concord.main:app --port 8000
./concord/demo.sh
```
