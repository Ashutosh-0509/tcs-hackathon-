"""PII detection + masking. Synthetic identifiers only (TECH_STACK.md §26)."""
from __future__ import annotations

import pytest
from app.services.pii import PIIService

pii = PIIService(use_presidio=False)


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ("My PAN is ABCPD1234E for the filing.", "PAN"),
        ("Aadhaar 2345 6789 0123 on record.", "AADHAAR"),
        ("Contact me at john.doe@example.com please.", "EMAIL"),
        ("Call 9876543210 tomorrow.", "PHONE_IN"),
        ("Card 4111 1111 1111 1111 was charged.", "CREDIT_CARD"),
    ],
)
def test_detects_identifier(text, expected_type):
    result = pii.redact(text)
    assert result.detected
    assert expected_type in result.counts()
    assert "[REDACTED" in result.redacted


def test_pan_value_removed_from_redacted_text():
    result = pii.redact("PAN ABCPD1234E")
    assert "ABCPD1234E" not in result.redacted


def test_clean_text_is_untouched():
    result = pii.redact("Who invented Python?")
    assert not result.detected
    assert result.redacted == "Who invented Python?"


def test_invalid_credit_card_not_flagged_as_card():
    # fails Luhn
    result = pii.redact("reference number 1234 5678 9012 3456 7")
    assert "CREDIT_CARD" not in result.counts()


def test_redact_many_aggregates_spans():
    redacted, spans = pii.redact_many(
        ["PAN ABCPD1234E", "email a@b.com", "nothing here"]
    )
    assert len(redacted) == 3
    types = {s.type for s in spans}
    assert {"PAN", "EMAIL"}.issubset(types)
