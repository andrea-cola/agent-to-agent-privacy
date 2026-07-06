"""HMAC-SHA256 attestation — signs and stores transfer records."""

from __future__ import annotations

import hashlib
import hmac
import json
import os

ATTESTATIONS: dict[str, dict] = {}

_SECRET_KEY = os.environ.get("ATTESTATION_SECRET", "dev-secret-not-for-production").encode()


def sign_and_store(transfer_id: str, record: dict) -> str:
    """HMAC-sign a transfer record and store it. Returns the hex signature."""
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    sig = hmac.new(_SECRET_KEY, canonical, hashlib.sha256).hexdigest()
    ATTESTATIONS[transfer_id] = {
        **record,
        "signed": True,
        "alg": "hmac-sha256",
        "sig": sig,
    }
    return sig


def get_attestation(transfer_id: str) -> dict | None:
    """Retrieve a signed attestation record by transfer_id."""
    return ATTESTATIONS.get(transfer_id)
