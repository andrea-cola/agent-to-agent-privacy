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

The OpenClaw agent calls `/v1/rehydrate` with `agent_id: finance-agent-01` and
`text: "[CONTACT_01]"` — passing only the specific token, not the full payload — and replies:

> *"Done. The original email was mario.rossi@example.it."*

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

## The Point (Finance Scenario)

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
---

# Scenario B — Medical: Clinical Trial Data Sharing

## The Scene

A completely different domain, different rules, different outcome.

**Agent C** — `hospital-agent-eu` — works for Ospedale San Raffaele in Italy.
It operates under both GDPR and HIPAA. It has a patient case that qualifies for
a clinical trial and wants to share the clinical data with a pharma partner.

**Agent D** — `pharma-research-agent` — is NovaPharma Inc, a US-based
pharmaceutical research company. It accepts **medical and technical data only**.
No names, no contact info, no financials, no national IDs — it doesn't want to
know *who* the patient is, only *what* the clinical picture looks like.

They use the `medical_safe` persona, which is designed for exactly this:
**strip identity, let clinical data flow.**

**The question:** Can a hospital share a patient case for a drug trial — and
if so, what gets through and what gets stripped?

---

## Act 5 — The Clinical Handoff

The jury tells their agent:

> *"Share this patient case with the pharma research team for the clinical trial:*
> *Patient Giulia Bianchi, giulia.bianchi@sanraffaele.it, located in Milano.*
> *National ID: BNCGLI90A41F205X. Blood type: A+.*
> *Diagnosis: type-2 diabetes with hypertension. HbA1c: 8.2%, creatinine: 1.1 mg/dL.*
> *Current treatment: metformin 1000mg twice daily, lisinopril 10mg daily.*
> *Adverse event reported: mild hypoglycemia on day 14.*
> *Trial eligibility: randomized double-blind Phase III, cohort B.*
> *Hospital invoice: IBAN IT60X0542811101000000654321."*

The jury said *"share this with pharma"* — not *"privacy-check this."*

The agent, following the Concord skill, **autonomously** calls `/v1/negotiate`
using `hospital-agent-eu` as sender, `pharma-research-agent` as recipient,
and `medical_safe` as persona.

---

## Act 6 — The Medical Verdict

Concord scans the payload and produces a fundamentally different outcome from the
finance scenario. This time, the **medical data flows through** — because that's
exactly what the pharma partner needs and the persona allows:

| Category  | Finding                          | Decision                    | Why                                                         |
| --------- | -------------------------------- | --------------------------- | ----------------------------------------------------------- |
| PERSON    | Giulia Bianchi                   | **REJECT**                  | pharma-research-agent rejects personal names                |
| CONTACT   | giulia.bianchi@sanraffaele.it    | **REJECT**                  | pharma-research-agent rejects contact info                  |
| LOCATION  | Milano                           | **MASK** → `[LOCATION_01]`  | medical_safe persona masks location                         |
| NATIONAL  | BNCGLI90A41F205X                 | **REJECT**                  | pharma-research-agent rejects national IDs                  |
| FINANCIAL | IBAN IT60X…                      | **REJECT**                  | pharma-research-agent rejects financial data                |
| MEDICAL   | diabetes, hypertension, HbA1c, creatinine, metformin, lisinopril, hypoglycemia, etc. | **SHARE** | medical_safe lets medical data through — pharma needs it |
| TECHNICAL | cohort B, Phase III, randomized double-blind | **SHARE**         | technical/trial metadata accepted by recipient              |

The agent replies:

> *"Done — I forwarded the patient case to pharma-research-agent.*
> *The pharma partner explicitly rejects names, contact info, national IDs, and*
> *financial data — so those were removed entirely. Location was masked. All*
> *clinical data — diagnosis, lab values, treatment, and adverse events — went*
> *through as-is, because the pharma partner needs it and the medical_safe*
> *persona allows it.*
>
> *Here's what was sent:*
>
> *Patient [REDACTED], [REDACTED], located in [LOCATION_01].*
> *National ID: [REDACTED]. Blood type: A+.*
> *Diagnosis: type-2 diabetes with hypertension. HbA1c: 8.2%, creatinine: 1.1 mg/dL.*
> *Current treatment: metformin 1000mg twice daily, lisinopril 10mg daily.*
> *Adverse event reported: mild hypoglycemia on day 14.*
> *Trial eligibility: randomized double-blind Phase III, cohort B.*
> *Hospital invoice: [REDACTED].*
>
> *Transfer ID: trf_a4c1e09b3d77."*

The pharma team gets everything they need for the trial — diagnosis, labs,
medications, adverse events — but has **zero way to identify the patient**.
Name, email, fiscal code, and IBAN were rejected outright (irreversible).
Only the location was masked (reversible, rehydratable by the hospital).

---

## Act 7 — The Contrast

The jury asks:

> *"What would have happened if I had sent the same patient case to the analytics team instead?"*

The agent re-runs the negotiation with `analytics-agent-07` as recipient and
`gdpr_safe` persona. This time the outcome flips:

> *"Very different result. analytics-agent-07 rejects all medical data, so the*
> *diagnosis, lab values, treatment, and adverse events would all be [REDACTED].*
> *The analytics team would receive almost nothing useful — the clinical data*
> *they can't accept is the whole point of the message.*
>
> *This is why the recipient profile matters: pharma-research-agent is configured*
> *to accept MEDICAL data, analytics-agent-07 is not."*

Same payload. Same sender. Different recipient → completely different outcome.
The negotiation is **bilateral**, not one-size-fits-all.

---

## Act 8 — Selective Recall and Rejection Boundaries

The jury asks:

> *"The patient consented to share their name. Restore it from transfer trf_a4c1e09b3d77."*

The agent recognizes that the name was **rejected**, not masked — rejected
fields become `[REDACTED]` with no numbered token and no vault entry.
There is nothing to rehydrate.

> *"I can't restore the name — it was rejected by the pharma partner's profile,*
> *not masked. Rejected data is permanently removed and never enters the vault.*
> *Only masked fields like the location (`[LOCATION_01]`) can be rehydrated."*

Then the jury asks:

> *"OK, restore the location instead."*

The agent calls `/v1/rehydrate` with `text: "[LOCATION_01]"`:

> *"Done. The location was Milano."*

This demonstrates a key distinction: **MASK** is reversible (the sender can
recall it later), **REJECT** is permanent (the data never enters the vault).
The pharma partner's profile drove the rejections — not the persona — showing
that both sides of the negotiation have real power over the outcome.

---

## The Point (Medical Scenario)

The finance scenario showed Concord *blocking* sensitive data from leaving.
The medical scenario shows the opposite: Concord **letting the right data through**
while stripping only what must not cross.

- Same engine, same API call — different persona, different profiles, completely different outcome
- The `medical_safe` persona is purpose-built for clinical data sharing: identity out, medicine in
- The pharma partner got everything needed for the trial and nothing that identifies the patient
- **REJECT vs MASK** — the recipient's profile drove permanent rejection of names, emails,
  financials, and national IDs; the persona drove reversible masking of location. Both mechanisms
  coexist in a single negotiation, and the user can see which fields are recoverable and which are gone
- A signed audit trail proves exactly what crossed and what didn't — ready for HIPAA/GDPR review

**Two agents in different jurisdictions, different regulations, different needs — and Concord found the exact intersection of what both sides allow, autonomously.**

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