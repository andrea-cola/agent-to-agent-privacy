"""PII detection engine — regex + heuristic detectors, no ML dependency.

Limitations stated upfront:
- Name detection uses a capitalised-token heuristic, not NER. Recall is imperfect.
- Location detection uses a small city gazetteer sized for the demo dataset.
- Medical/biometric detection uses keyword lists — not exhaustive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Finding:
    category: str
    text: str
    start: int
    end: int
    detector: str
    confidence: float


# ---------------------------------------------------------------------------
# Individual detectors
# ---------------------------------------------------------------------------

def _detect_email(text: str) -> list[Finding]:
    return [
        Finding("CONTACT", m.group(), m.start(), m.end(), "email_regex", 0.95)
        for m in re.finditer(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", text)
    ]


def _detect_phone(text: str) -> list[Finding]:
    return [
        Finding("CONTACT", m.group(), m.start(), m.end(), "phone_regex", 0.85)
        for m in re.finditer(r"\+?\d[\d\s\-()]{7,}\d", text)
    ]


def _luhn_check(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _detect_credit_card(text: str) -> list[Finding]:
    results: list[Finding] = []
    for m in re.finditer(r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b", text):
        digits = re.sub(r"[\s\-]", "", m.group())
        if len(digits) == 16 and _luhn_check(digits):
            results.append(
                Finding("FINANCIAL", m.group(), m.start(), m.end(), "credit_card_luhn", 0.95)
            )
    return results


def _detect_iban(text: str) -> list[Finding]:
    return [
        Finding("FINANCIAL", m.group(), m.start(), m.end(), "iban_regex", 0.90)
        for m in re.finditer(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", text)
    ]


def _detect_national_id(text: str) -> list[Finding]:
    results: list[Finding] = []
    # Italian codice fiscale: 16 alphanumeric characters
    for m in re.finditer(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b", text):
        results.append(
            Finding("NATIONAL", m.group(), m.start(), m.end(), "codice_fiscale", 0.90)
        )
    # US SSN pattern
    for m in re.finditer(r"\b\d{3}-\d{2}-\d{4}\b", text):
        results.append(
            Finding("NATIONAL", m.group(), m.start(), m.end(), "ssn_pattern", 0.80)
        )
    return results


def _detect_ip(text: str) -> list[Finding]:
    return [
        Finding("TECHNICAL", m.group(), m.start(), m.end(), "ip_address", 0.80)
        for m in re.finditer(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
            text,
        )
    ]


_SECRET_PREFIXES = ("sk-", "sk-live", "ghp_", "AKIA", "xox", "glpat-")
_SECRET_RE = re.compile(
    r"(?:" + "|".join(re.escape(p) for p in _SECRET_PREFIXES) + r")[A-Za-z0-9_\-]{8,}"
)


def _detect_secret(text: str) -> list[Finding]:
    return [
        Finding("SECRET", m.group(), m.start(), m.end(), "secret_prefix", 0.95)
        for m in _SECRET_RE.finditer(text)
    ]


_MEDICAL_KEYWORDS = [
    "diabetes", "insulin", "hypertension", "cancer", "tumor", "chemotherapy",
    "diagnosis", "treatment", "prescription", "medication", "surgery", "biopsy",
    "hiv", "hepatitis", "asthma", "allergy", "cardiac", "therapy", "psychiatric",
    "depression", "anxiety", "epilepsy", "dialysis", "transplant",
    "metformin", "lisinopril", "atorvastatin", "omeprazole", "amoxicillin",
    "ibuprofen", "paracetamol", "warfarin", "prednisone", "azithromycin",
    "clinical trial", "adverse event", "dosage", "efficacy", "placebo",
    "randomized", "double-blind", "cohort", "biomarker", "pathology",
    "remission", "relapse", "prognosis", "anemia", "arrhythmia",
    "cholesterol", "glycemia", "hba1c", "creatinine", "hemoglobin",
]
_MEDICAL_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _MEDICAL_KEYWORDS) + r")\b", re.IGNORECASE
)


def _detect_medical(text: str) -> list[Finding]:
    return [
        Finding("MEDICAL", m.group(), m.start(), m.end(), "medical_keyword", 0.75)
        for m in _MEDICAL_RE.finditer(text)
    ]


_BIOMETRIC_KEYWORDS = [
    "fingerprint", "retina", "iris scan", "face recognition", "voiceprint",
    "facial geometry", "biometric", "dna sample", "palm print",
]
_BIOMETRIC_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _BIOMETRIC_KEYWORDS) + r")\b", re.IGNORECASE
)


def _detect_biometric(text: str) -> list[Finding]:
    return [
        Finding("BIOMETRIC", m.group(), m.start(), m.end(), "biometric_keyword", 0.75)
        for m in _BIOMETRIC_RE.finditer(text)
    ]


_CITIES = [
    "Milano", "Roma", "Rome", "Napoli", "Torino", "Firenze", "Bologna", "Palermo",
    "Genova", "Venezia", "Verona", "New York", "London", "Paris", "Berlin",
    "Tokyo", "Shanghai", "Mumbai", "São Paulo", "Los Angeles", "Chicago",
    "San Francisco", "Boston", "Amsterdam", "Brussels", "Zurich", "Geneva",
    "Madrid", "Barcelona", "Lisbon", "Dublin", "Sydney", "Melbourne",
    "Toronto", "Vancouver", "Singapore", "Hong Kong", "Seoul", "Bangkok",
]
_CITIES_LOWER = {c.lower(): c for c in _CITIES}


def _detect_location(text: str) -> list[Finding]:
    results: list[Finding] = []
    for city_lower, city_orig in _CITIES_LOWER.items():
        for m in re.finditer(re.escape(city_orig), text, re.IGNORECASE):
            results.append(
                Finding("LOCATION", m.group(), m.start(), m.end(), "city_gazetteer", 0.70)
            )
    return results


_NAME_RE = re.compile(r"\b[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}\b")

_NAME_EXCLUDE = {c for c in _CITIES} | {
    "Customer", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday", "January", "February", "March", "April", "May",
    "June", "July", "August", "September", "October", "November", "December",
}


_MULTI_CAP_RE = re.compile(r"\b[A-Z][a-z]{1,20}\b")


def _detect_name(text: str) -> list[Finding]:
    results: list[Finding] = []
    tokens = list(_MULTI_CAP_RE.finditer(text))
    i = 0
    while i < len(tokens) - 1:
        t1, t2 = tokens[i], tokens[i + 1]
        w1, w2 = t1.group(), t2.group()
        gap = text[t1.end():t2.start()]
        if gap.strip() == "" and len(gap) <= 3:
            if w1 not in _NAME_EXCLUDE and w2 not in _NAME_EXCLUDE:
                full = text[t1.start():t2.end()]
                results.append(
                    Finding("PERSON", full, t1.start(), t2.end(), "name_heuristic", 0.60)
                )
                i += 2
                continue
        i += 1
    return results


_ALL_DETECTORS = [
    _detect_email,
    _detect_credit_card,
    _detect_iban,
    _detect_national_id,
    _detect_phone,
    _detect_ip,
    _detect_secret,
    _detect_medical,
    _detect_biometric,
    _detect_location,
    _detect_name,
]

_PRIORITY = {
    "credit_card_luhn": 10, "iban_regex": 10, "codice_fiscale": 9,
    "ssn_pattern": 9, "email_regex": 8, "secret_prefix": 8,
    "phone_regex": 3, "ip_address": 3, "name_heuristic": 2,
    "city_gazetteer": 2, "medical_keyword": 5, "biometric_keyword": 5,
}


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    """Remove overlapping findings, keeping the highest-priority / longest match."""
    findings.sort(key=lambda f: (f.start, -_PRIORITY.get(f.detector, 0), -(f.end - f.start)))
    result: list[Finding] = []
    last_end = -1
    for f in findings:
        if f.start >= last_end:
            result.append(f)
            last_end = f.end
    return result


def detect(text: str) -> list[Finding]:
    """Run all detectors and return de-duplicated findings sorted by position."""
    all_findings: list[Finding] = []
    for detector_fn in _ALL_DETECTORS:
        all_findings.extend(detector_fn(text))
    return _deduplicate(all_findings)
