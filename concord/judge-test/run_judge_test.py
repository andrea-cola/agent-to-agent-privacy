#!/usr/bin/env python3
"""Concord judge test — runs the six steps (A–F) against a live endpoint.

Usage:
    python3 run_judge_test.py [BASE_URL]

Defaults to http://localhost:8000 if no URL is provided.
"""

from __future__ import annotations

import json
import sys
import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[dict] = []


def step(label: str, desc: str, passed: bool, detail: str = "") -> None:
    tag = PASS if passed else FAIL
    print(f"  [{tag}] {label}: {desc}")
    if detail:
        print(f"         {detail}")
    results.append({"label": label, "desc": desc, "passed": passed, "detail": detail})


def main() -> None:
    print(f"\n  Concord Judge Test — {BASE_URL}\n")
    client = httpx.Client(base_url=BASE_URL, timeout=90.0)

    # -----------------------------------------------------------------------
    # A: Anonymous reject — sender_profile absent → 422
    # -----------------------------------------------------------------------
    r = client.post(
        "/v1/negotiate",
        json={
            "recipient_profile": "analytics-agent-07",
            "persona": "gdpr_safe",
            "payload": "test data",
        },
    )
    step("A", "Anonymous request rejected (422)", r.status_code == 422, f"status={r.status_code}")

    # -----------------------------------------------------------------------
    # B: Full negotiation — real payload with PII
    # -----------------------------------------------------------------------
    payload = (
        "Customer Mario Rossi (mario.rossi@example.it) lives in Milano. "
        "IBAN IT60X0542811101000000123456. Diagnosis: diabetes. "
        "API key: sk-live-abc123xyz456789."
    )
    r = client.post(
        "/v1/negotiate",
        json={
            "sender_profile": "finance-agent-01",
            "recipient_profile": "analytics-agent-07",
            "persona": "gdpr_safe",
            "payload": payload,
        },
    )
    ok_b = r.status_code == 200
    data = r.json() if ok_b else {}
    step("B", "Negotiation succeeds (200)", ok_b, f"verdict={data.get('verdict', 'N/A')}")

    # -----------------------------------------------------------------------
    # C: SECRET category is REJECT'd — never forwarded
    # -----------------------------------------------------------------------
    secret_decisions = [d for d in data.get("decisions", []) if d["category"] == "SECRET"]
    all_rejected = all(d["action"] == "REJECT" for d in secret_decisions) if secret_decisions else False
    secret_not_in_output = "sk-live" not in data.get("outbound_payload", "sk-live")
    step(
        "C",
        "SECRET always rejected + absent from output",
        all_rejected and secret_not_in_output,
        f"secret_decisions={len(secret_decisions)}, in_output={not secret_not_in_output}",
    )

    # -----------------------------------------------------------------------
    # D: Rehydrate — sender retrieves original tokens
    # -----------------------------------------------------------------------
    tid = data.get("transfer_id", "")
    redacted = data.get("outbound_payload", "")
    r = client.post(
        "/v1/rehydrate",
        json={"transfer_id": tid, "text": redacted, "agent_id": "finance-agent-01"},
    )
    ok_d = r.status_code == 200
    rehydrated_text = r.json().get("text", "") if ok_d else ""
    has_original = "mario.rossi@example.it" in rehydrated_text if ok_d else False
    step("D", "Rehydrate restores tokens (200)", ok_d and has_original, f"status={r.status_code}")

    # -----------------------------------------------------------------------
    # E: Rehydrate — wrong agent → 403
    # -----------------------------------------------------------------------
    r = client.post(
        "/v1/rehydrate",
        json={"transfer_id": tid, "text": redacted, "agent_id": "imposter-agent"},
    )
    step("E", "Rehydrate by wrong agent rejected (403)", r.status_code == 403, f"status={r.status_code}")

    # -----------------------------------------------------------------------
    # F: Attestation — signed record retrievable
    # -----------------------------------------------------------------------
    r = client.get(f"/v1/attestation/{tid}")
    att = r.json() if r.status_code == 200 else {}
    ok_f = att.get("signed") is True and "sig" in att
    step("F", "Attestation is signed and retrievable", ok_f, f"alg={att.get('alg', 'N/A')}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n  {'=' * 50}")
    overall = "PASS" if passed == total else "FAIL"
    color = "\033[92m" if passed == total else "\033[91m"
    print(f"  {color}{overall}\033[0m — {passed}/{total} steps passed\n")

    # Output JSON for the HTML UI to consume
    summary = {
        "base_url": BASE_URL,
        "passed": passed,
        "total": total,
        "overall": overall,
        "steps": results,
        "decisions": data.get("decisions", []),
        "inbound_risk": data.get("inbound_risk"),
        "residual_risk": data.get("residual_risk"),
        "verdict": data.get("verdict"),
    }
    with open("results.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("  Results written to results.json\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
