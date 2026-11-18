# Roosterly Support Ticket Agent

## How to run

**Prerequisites:** Python 3.11+.

### 1. Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install core dependencies (zero-dependency regex redaction works out-of-the-box)
pip install -e .

# (Optional) Install Microsoft Presidio & spaCy model for NLP-based entity masking:
# pip install -e ".[presidio]" && python -m spacy download en_core_web_sm

# Configure credentials
cp .env.example .env
# Fill in HELPDESK_API_KEY, HELPDESK_EMAIL, FAL_KEY
# Optional: JEV_API_KEY (for scoring), LANGFUSE_* (for tracing)
```

### 2. Execution Commands
* **Deliver decisions to Helpdesk:** `make run`
* **Deliver with Jev confidence scoring:** `make run ARGS='--score'`
* **Process specific tickets:** `make run ARGS='--ids T001 T005'`
* **Reset practice tickets:** `make run ARGS='--reset'`
* **Dry-run preview (no API posting):** `python scripts/preview_ticket.py T005`
* **Run automated test suite (28 tests):** `make test`
* **Run labelled benchmark evaluation:** `python eval/run_eval.py`

*(Optional)* Langfuse observability is activated automatically when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are populated in `.env`.

---

## Decisions

### The Core Architectural Pillars: LLM, Jev, and Redact

1. **LLM (Decision & Direct Dutch Reasoning):**  
   We use DeepSeek V4.1 Flash via fal.ai and LiteLLM (`src/agent/clients/llm.py`). Rather than a slow, lossy two-step translation loop (NL → EN → NL), the model reasons directly on Dutch tickets against the Help Centre (`knowledge/faq.md`). It produces validated Pydantic outputs (`LLMDecision`), enforcing that `reply` requires a localized `draft_reply` preserving Dutch UI menu names, while `handoff` requires an English `handoff_note`.
2. **JEV (Independent Confidence Scoring):**  
   Evaluates action fit and policy alignment via the TypeSafe SDK (`src/agent/clients/jev.py`). Scoring runs in an isolated subgraph with dedicated retries (`score_with_retries` in `src/agent/graph.py`). Jev confidence is diagnostic and decoupled from execution; scoring failures or timeouts never block ticket delivery.
3. **REDACT (Data Privacy & Guardrails):**  
   Sensitive payment details (credit cards, IBANs, CVCs, expiration dates) are sanitized before prompts reach the LLM and before decisions are written to logs (`src/agent/redaction.py`). Redaction runs out-of-the-box via high-precision patterns and optionally leverages **Microsoft Presidio** if installed. In `src/agent/nodes/deliver.py`, a pre-flight circuit-breaker (`contains_payment_details`) blocks any delivery payload containing leaked payment data.

### Workflow Architecture (LangGraph State Pipeline)
Two state graphs in `src/agent/graph.py` share a typed `TicketState`:

```
[Delivery Graph]
START ──► skip_done ─┬─► (if already handled) ───────────────────────► log ──► END
                     └─► (if open) ──► decide ──► [score] ──► deliver ─┘

[Preview Graph]
START ──► decide ──► [score] ──► END
```

* **`skip_done`**: Checks `GET /tickets/{id}` for handled state to guarantee idempotency.
* **`decide`**: Redacts ticket data → calls LLM with prompt + FAQ → re-sanitizes output → validates `LLMDecision`.
* **`score` (Optional via `--score`)**: Calls Jev API in an isolated fault-tolerant node.
* **`deliver`**: Runs outbound payment leak verification → dispatches to `/reply`, `/handoff`, or `/close` with rate-limiting and retry logic.
* **`log`**: Writes atomic audit logs with token metrics to `logs/live/run.jsonl`.

### AI Tooling & Assumptions
Codex and LLM assistants helped write tests, schema validation, and regexes. Assumed routine billing how-to queries are P4 unless an invoice dispute or contract change is involved; any ticket with multiple requests where at least one requires human attention is escalated in full.

---

## Reliability

* **503 & Network Flakes:** Retried with exponential backoff across HTTP client calls and LangGraph node `RetryPolicy`.
* **429 Rate Limiting:** Enforces an automatic 0.25s pause between requests (≤4 req/sec, safely below the 5 req/sec server limit) and honors `Retry-After` headers.
* **409 Conflicts & Crash Recovery:** Completely crash-safe. If interrupted, subsequent runs inspect server state via `skip_done` and record `already_handled`, preventing duplicate responses.
* **Security & Prompt Injection:** Ticket text is treated as untrusted data; prompt instructions explicitly forbid tickets from overriding rules, priority, or action. API keys are strictly confined to environment variables.

---

## Eval and fix

* **Baseline Eval:** Scored 9/10 on priority because compliance/GDPR review tickets were prematurely marked as P1 urgency regardless of actual customer impact.
* **The Fix:** Clarified in `prompts/system.md` that compliance and specialist reviews (e.g., GDPR/AVG) require evidence of severe operational disruption or legal threat to warrant P1, and belong at P2 otherwise.
* **After Fix:** All 4 fields (`action`, `language`, `category`, `priority`) achieved **10/10 (100% accuracy)** on the labelled benchmark (`eval/results/20261118T060808Z`).
* **Cost per 100 tickets:**
  The 10-ticket evaluation consumed 18,721 input and 3,427 output tokens (average 1,872 input / 343 output per ticket).
  $$\text{Cost}_{100} = (0.18721 \times \text{Input Rate}) + (0.03427 \times \text{Output Rate}) \text{ USD}$$
  At standard flash model rates ($0.14/M input, $0.28/M output), 100 tickets cost approximately **$0.036 USD** (well below €0.05).

---

## What I would improve

1. **Human-in-the-Loop (HITL) Confidence Routing:** Currently, Jev computes an action confidence score, but it is purely diagnostic. My primary next step would be introducing an active confidence threshold in the graph: if confidence falls below 0.75, automatically route a proposed autonomous `reply` to `handoff`. The model's generated answer is preserved as a suggested draft in the English handoff note for human agent review, eliminating the risk of ungrounded responses reaching customers while keeping human workload low.
2. **Refine Client Rule on Policy Inquiries:** The current client policy mandates human escalation for any mention of *refund* or *cancellation*, even for purely informational queries (e.g., *"What is your refund policy?"*). Enabling the agent to answer informational questions from the FAQ directly would reduce unnecessary escalations.
