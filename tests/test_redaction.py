"""Tests for payment detail redaction and leak prevention."""
from agent.redaction import contains_payment_details, redact


def test_redact_credit_cards():
    raw = "Mijn creditcardnummer is 4111 1111 1111 1111 voor de betaling."
    redacted = redact(raw)
    assert "4111" not in redacted
    assert "[payment detail removed]" in redacted


def test_redact_t008_complete_payment_details():
    raw = (
        "Willen jullie onze betaalmethode aanpassen naar mijn nieuwe creditcard: "
        "4111 1111 1111 1111, geldig tot 09/28, CVC 123. De oude is geblokkeerd. Groet, Jeroen"
    )
    redacted = redact(raw)
    assert "4111" not in redacted
    assert "09/28" not in redacted
    assert "123" not in redacted
    assert "[payment detail removed]" in redacted


def test_redact_ibans():
    dutch_iban = "Gelieve te storten op NL91 ABNA 0417 1643 00 tnv Roosterly."
    redacted = redact(dutch_iban)
    assert "NL91" not in redacted
    assert "[payment detail removed]" in redacted


def test_redact_dict_structures():
    ticket = {
        "id": "T008",
        "subject": "Nieuwe betaalkaart",
        "body": "Nieuwe kaart: 5500 0000 0000 0004, exp: 11/27",
        "notes": ["CVC: 456"],
    }
    cleaned = redact(ticket)
    assert cleaned["id"] == "T008"
    assert "5500" not in cleaned["body"]
    assert "[payment detail removed]" in cleaned["body"]
    assert "456" not in cleaned["notes"][0]


def test_preserves_benign_ticket_content():
    benign = "Ticket T005: Hoe voeg ik 5 medewerkers toe? Zie artikel F02 op 2026-10-05 om 09:30 voor €4,50."
    assert redact(benign) == benign


def test_contains_payment_details_detection():
    assert contains_payment_details("Creditcard: 4111 1111 1111 1111") is True
    assert contains_payment_details("Mijn IBAN is NL91ABNA0417164300") is True
    assert contains_payment_details("CVC is 123") is True
    assert contains_payment_details("geldig tot 10/28") is True
    assert contains_payment_details("Betaling ontvangen voor [payment detail removed]") is False
    assert contains_payment_details("Alleen een vraag over F02 prijzen van €4,50 per stuk.") is False
