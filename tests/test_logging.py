"""Tests for audit logging: format, completeness, and redaction guardrails."""
import json
from pathlib import Path

from agent.nodes.log import log
from agent.redaction import contains_payment_details
from agent.schemas import LLMDecision


def test_log_reply_with_redacted_input_and_decision(tmp_path):
    log_path = tmp_path / "run.jsonl"
    state = {
        "ticket": {
            "id": "T008",
            "subject": "Nieuwe betaalkaart",
            "body": "Nieuwe kaart: 4111 1111 1111 1111, exp: 09/28, CVC: 123",
            "customer_plan": "Plus",
            "channel": "email",
        },
        "outcome": "delivered",
        "decision": LLMDecision(
            action="reply",
            language="nl",
            category="billing",
            priority="P2",
            reason="Betalingsinstructies gestuurd voor kaart 4111 1111 1111 1111.",
            draft_reply="Hoi Jeroen, je kaart 4111 1111 1111 1111 is bijgewerkt.",
            handoff_note=None,
        ),
        "confidence": 0.96,
        "scores": {"action": 0.96, "language": 0.99, "category": 0.95, "priority": 0.92, "grounding": 0.94},
        "usage": {"prompt_tokens": 1200, "completion_tokens": 150, "total_tokens": 1350},
    }

    log(state, log_path)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])

    # Core audit metadata
    assert entry["ticket_id"] == "T008"
    assert entry["outcome"] == "delivered"
    assert entry["action"] == "reply"
    assert "time" in entry

    # Input logged and redacted
    assert entry["input"]["subject"] == "Nieuwe betaalkaart"
    assert entry["input"]["customer_plan"] == "Plus"
    assert entry["input"]["channel"] == "email"
    assert "[payment detail removed]" in entry["input"]["body"]

    # Decision logged and redacted
    decision = entry["decision"]
    assert decision["action"] == "reply"
    assert decision["language"] == "nl"
    assert decision["category"] == "billing"
    assert decision["priority"] == "P2"
    assert decision["handoff_note"] is None
    assert "[payment detail removed]" in decision["reason"]
    assert "[payment detail removed]" in decision["draft_reply"]

    # Scores and usage
    assert entry["confidence"] == 0.96
    assert entry["scores"]["action"] == 0.96
    assert entry["usage"] == {"prompt_tokens": 1200, "completion_tokens": 150, "total_tokens": 1350}

    # Strict payment leak verification across the whole entry
    raw_json = json.dumps(entry)
    assert not contains_payment_details(raw_json)
    assert "4111" not in raw_json
    assert "123" not in raw_json


def test_log_handoff_has_handoff_note_and_null_draft_reply(tmp_path):
    log_path = tmp_path / "run.jsonl"
    state = {
        "ticket": {
            "id": "T002",
            "subject": "Terugbetaling",
            "body": "Kan ik geld terugkrijgen voor augustus?",
            "customer_plan": "Basis",
        },
        "outcome": "delivered",
        "decision": LLMDecision(
            action="handoff",
            language="nl",
            category="billing",
            priority="P2",
            reason="Refund request must be escalated to human support.",
            draft_reply=None,
            handoff_note="Customer asking for refund for August closure; escalate per policy.",
        ),
        "usage": {"prompt_tokens": 800, "completion_tokens": 90, "total_tokens": 890},
    }

    log(state, log_path)

    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["action"] == "handoff"
    assert entry["decision"]["draft_reply"] is None
    assert entry["decision"]["handoff_note"].startswith("Customer asking for refund")
    assert "confidence" not in entry  # Not added if None or not evaluated


def test_log_skipped_ticket_records_safe_metadata_without_decision(tmp_path):
    log_path = tmp_path / "run.jsonl"
    state = {
        "ticket": {"id": "T003"},
        "outcome": "already_handled",
    }

    log(state, log_path)

    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["ticket_id"] == "T003"
    assert entry["outcome"] == "already_handled"
    assert "decision" not in entry
    assert "input" not in entry


def test_log_error_records_safe_error_type_only(tmp_path):
    log_path = tmp_path / "run.jsonl"
    state = {
        "ticket": {"id": "T004", "subject": "Private data 4111 1111 1111 1111"},
        "outcome": "error",
        "error": "RateLimitError",
    }

    log(state, log_path)

    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["ticket_id"] == "T004"
    assert entry["outcome"] == "error"
    assert entry["error"] == "RateLimitError"
    assert "decision" not in entry
    assert "Private" not in json.dumps(entry)
