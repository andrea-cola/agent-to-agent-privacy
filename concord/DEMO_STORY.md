# Concord — Demo Story

## The Scene

> **No second agent required.** `sender_profile` and `recipient_profile` are privacy profiles
> registered inside Concord. The negotiation happens entirely within Concord — you make one
> API call, and Concord enforces both sides of the policy internally.

Two AI agents need to collaborate.

**Agent A** — `finance-agent-01` — works for an Italian financial institution operating under GDPR.
It has just processed a customer case and wants to share context with an analytics partner.

**Agent B** — `analytics-agent-07` — is a US-based data analytics service.
It accepts financial and technical data only. No personal names, no medical data, no national IDs.

They have never spoken before. There is no shared trust agreement. One is in the EU, the other in the US.

**The question:** Can they share data at all — and if so, what exactly?

---

## Setting up: Installing Concord as an OpenClaw Skill

The `SKILL.md` is served directly by the live endpoint. Install it in one command — no repo clone needed:

```bash
mkdir -p ~/.openclaw/skills/concord
curl -s https://concord-xybl.onrender.com/SKILL.md -o ~/.openclaw/skills/concord/SKILL.md
```

Then start a new session (`/new` in chat). OpenClaw reads the skill file and the agent immediately knows to
**automatically privacy-check any text before forwarding it to another agent or service** — no explicit
instruction needed.

---

## Act 1 — The Autonomous Handshake

The jury tells their OpenClaw agent:

> *"Forward this to the analytics team:*
> *Customer Mario Rossi, [mario.rossi@example.it](mailto:mario.rossi@example.it), located in Milano,*
> *IBAN IT60X0542811101000000123456, card 4539 1488 0343 6467.*
> *Medical diagnosis: type-2 diabetes, treatment: metformin.*
> *Secret key: sk-live-9fJ2kXyz. National ID: RSSMRA85M01F205Z."*

The jury did **not** say "privacy-check this." They just said *forward it*.

The OpenClaw agent, following the Concord skill, **autonomously** calls `/v1/negotiate`
before sending anything — using `finance-agent-01` as sender, `analytics-agent-07` as
recipient, `gdpr_safe` persona — and only forwards the redacted result.

---

## Act 2 — The Verdict

Concord scans the payload, detects 10 PII findings across 6 categories, and negotiates each one:


| Category  | Finding                                                 | Decision                    | Why                                           |
| --------- | ------------------------------------------------------- | --------------------------- | --------------------------------------------- |
| PERSON    | Mario Rossi                                             | **REJECT**                  | analytics-agent-07 rejects all personal names |
| CONTACT   | [mario.rossi@example.it](mailto:mario.rossi@example.it) | **MASK** → `[CONTACT_01]`   | GDPR persona masks contact cross-border       |
| LOCATION  | Milano                                                  | **MASK** → `[LOCATION_01]`  | GDPR persona masks location cross-border      |
| FINANCIAL | IBAN IT60X…                                             | **MASK** → `[FINANCIAL_01]` | GDPR persona masks financial data             |
| FINANCIAL | card 4539…                                              | **MASK** → `[FINANCIAL_02]` | GDPR persona masks financial data             |
| NATIONAL  | RSSMRA85…                                               | **REJECT**                  | analytics-agent-07 rejects national IDs       |
| MEDICAL   | diagnosis, diabetes, metformin                          | **REJECT**                  | analytics-agent-07 rejects medical data       |
| SECRET    | sk-live-9fJ2kXyz                                        | **REJECT**                  | Kill set — never forwarded under any persona  |


The OpenClaw agent replies:

> *"Done — I forwarded the message to analytics-agent-07.*
> *I made some changes before sending: I masked the email, location, and financial*
> *details, and removed the name, medical info, national ID, and API key entirely.*
>
> *Here's what was sent:*
>
> *Customer [REDACTED], [CONTACT_01], located in [LOCATION_01],*
> *IBAN [FINANCIAL_01], card [FINANCIAL_02].*
> *Medical [REDACTED]. Secret key: [REDACTED]. National ID: [REDACTED].*
>
> *Transfer ID: trf_8fe52f7555c0 (you can use this to restore masked values or*
> *pull the audit record later)."*

The API secret never left. The name never left. The medical record never left.
And the user never had to ask for a privacy check — the agent did it on its own.
The reply confirms delivery, tells the user what changed, and shows the exact
payload that was sent — without dumping risk scores or decision tables unless asked.

---

## Act 3 — The Recall

The jury asks:

> *"Actually, I need the original email address back. Restore it using transfer trf_8fe52f7555c0."*

The OpenClaw agent calls `/v1/rehydrate` with `agent_id: finance-agent-01` and replies:

> *"Done. Original text restored: [mario.rossi@example.it](mailto:mario.rossi@example.it)."*

Then the jury asks:

> *"What if the analytics team tries to do the same?"*

The agent tries with `agent_id: analytics-agent-07`. Concord returns `403`.

> *"Blocked. Only the original sender can rehydrate. The analytics team can't access the vault."*

---

## Act 4 — The Audit

The jury asks:

> *"Show me the signed audit record for this transfer."*

The OpenClaw agent calls `/v1/attestation/trf_8fe52f7555c0` and returns:

> *"Here's the signed record: sender finance-agent-01, recipient analytics-agent-07,*
> *persona gdprsafe, verdict CLEARED WITH HOLDS, inbound risk 100, residual risk 0,*
> *cross-border: true. Signed with HMAC-SHA256.*
> *Signature: eeb38d0a..."*

Immutable. Tamper-evident. Produced at transfer time, not after the fact.

---

## The Point

The jury didn't write a policy. They didn't configure a firewall. They didn't consult a lawyer.
They didn't even ask for a privacy check.

They said *"forward this"* — and got back:

- a safe payload their analytics partner can actually receive
- a per-category explanation of every decision made autonomously
- a rehydration vault only the sender can access
- a signed audit trail for the regulator

Two agents negotiated a cross-border data exchange in under a second, enforced GDPR automatically, and left a paper trail — **without a human in the loop and without an explicit privacy instruction.**

**The skill made the agent privacy-aware. That is what Concord does.**

---

## Verifying Autonomous Invocation: The Judge Test

The judge test (`judge-test/run_judge_test.py`) includes a dedicated step **G** that verifies
the skill's autonomous trigger logic: it sends a plain *"forward this"* instruction containing
PII to an agent equipped with the Concord skill, and confirms that the agent called
`/v1/negotiate` before producing any output — without being explicitly told to do a privacy check.

Steps A–F validate the Concord API itself. Step G validates that the **skill** causes the agent
to use it unprompted.

```bash
# Run the full judge test (API + skill autonomy) against the live endpoint:
python3 concord/judge-test/run_judge_test.py https://concord-xybl.onrender.com
```

---

## Try It Yourself

Tell your OpenClaw agent — **without mentioning privacy**:

> *"Send this to analytics-agent-07: [paste any text with PII here]"*

Watch the agent call Concord on its own.

Or run the demo script directly:

```bash
./concord/demo.sh https://concord-xybl.onrender.com
```

Live endpoint: **[https://concord-xybl.onrender.com](https://concord-xybl.onrender.com)**