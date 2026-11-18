"""Redact sensitive payment details (PCI-DSS & Dutch client privacy requirements)."""
from functools import lru_cache
import re
from typing import Any

REDACTED_PLACEHOLDER = "[payment detail removed]"

# High-precision pattern covering credit cards, IBANs, CVC/CVVs, and expiration dates
PAYMENT_REGEX = re.compile(
    r"(?<!\d)(?:\d[\s-]?){12,18}\d(?!\d)"  # Credit card numbers
    r"|\b[A-Z]{2}\s?\d{2}(?:\s?[A-Z0-9]){11,30}\b"  # IBANs
    r"|\b(?:cvc|cvv|cid|veiligheidscode)\b(?:[\s:=]|is)+[0-9]{3,4}\b"  # CVC / CVV
    r"|\b(?:geldig\s+tot|vervaldatum|exp(?:ires|iry)?)\b(?:[\s:=]|is)+[0-1]?\d[\/-][2-3]\d\b",  # Expiration
    flags=re.IGNORECASE,
)

PAYMENT_ENTITIES = ["CREDIT_CARD", "IBAN_CODE", "CVC", "CARD_EXPIRY"]


@lru_cache(maxsize=1)
def _get_presidio_engines():
    """Lazily initialize Microsoft Presidio with custom payment recognizers."""
    try:
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
        )
        analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])

        cvc_pattern = Pattern(
            name="cvc",
            regex=r"\b(?:cvc|cvv|cid|veiligheidscode)\b(?:[\s:=]|is)+([0-9]{3,4})\b",
            score=0.85,
        )
        analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="CVC", patterns=[cvc_pattern], supported_language="en")
        )

        expiry_pattern = Pattern(
            name="card_expiry",
            regex=r"\b(?:geldig\s+tot|vervaldatum|exp(?:ires|iry)?)\b(?:[\s:=]|is)+([0-1]?\d[\/-][2-3]\d)\b",
            score=0.85,
        )
        analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="CARD_EXPIRY", patterns=[expiry_pattern], supported_language="en"
            )
        )

        anonymizer = AnonymizerEngine()
        operators = {
            entity: OperatorConfig("replace", {"new_value": REDACTED_PLACEHOLDER})
            for entity in PAYMENT_ENTITIES
        }
        return analyzer, anonymizer, operators
    except Exception:
        return None, None, None


def redact(value: Any) -> Any:
    """Mask payment details in text, dicts, or lists."""
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, str):
        return value

    # Try Presidio first
    analyzer, anonymizer, operators = _get_presidio_engines()
    if analyzer and anonymizer:
        try:
            results = analyzer.analyze(text=value, entities=PAYMENT_ENTITIES, language="en")
            if results:
                anonymized = anonymizer.anonymize(
                    text=value, analyzer_results=results, operators=operators
                )
                return anonymized.text
            return value
        except Exception:
            pass

    # High-precision fallback
    return PAYMENT_REGEX.sub(REDACTED_PLACEHOLDER, value)


def contains_payment_details(text: str | None) -> bool:
    """Detect if text contains unredacted payment or card details."""
    if not text or not isinstance(text, str):
        return False
    return bool(PAYMENT_REGEX.search(text))


# Alias for backward compatibility
protect = redact
