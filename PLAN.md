# Helpdesk agent: step-by-step plan

## What we are building

A Python agent, run with one command, that handles Roosterly helpdesk tickets with
one action per ticket: `reply`, `handoff`, or `close`. Replies use only
`knowledge/faq.md`. Gemini through LiteLLM generates the complete structured
decision. LangGraph connects small, independently understandable nodes.

**Jev only adds confidence.** It does not choose the action, rewrite an answer,
trigger a retry, or route tickets based on a threshold. The LLM follows the client
rules when deciding to hand off. Invalid structured output has a separate
validation fallback: retry once, then produce a valid handoff.

We first inspect saved samples and build a local preview. Then we connect scoring,
the graph, and reliable delivery before running against the real helpdesk.

## How we will work

Finish one step, show its output, and review it before starting the next. Each step
below has concrete files, something to inspect, and a completion check. This plan
is not an instruction to implement every step immediately.

Use saved fixtures instead of repeatedly fetching the same tickets. A fake client
and the real client will share an interface, selected through configuration. Keep
the fake client and fixtures after going live for repeatable tests. Example labels
must never be passed to Gemini or Jev.

## Already completed

- [x] Repository and small modules scaffolded.
- [x] Initial Pydantic contracts in `src/agent/schemas.py` and state in `state.py`.
- [x] Environment variables and `config/settings.yaml` configured.
- [x] Helpdesk `/status` checked successfully.
- [x] Status, 10 labelled examples, and 30 practice tickets saved in `fixtures/`.
- [x] Simple live reader in `clients/helpdesk.py` and fixture reader in
  `clients/fixtures.py`; capture
  script reuses the live reader. `scripts/inspect_tickets.py` reads fixtures by
  default. Pagination and fixture filtering have two passing automated tests.

Most processing modules are still placeholders. The helpdesk API check does not
yet verify Gemini generation or the complete agent.

## Step 1 — Inspect samples and define the input

- [ ] Review representative saved tickets: an FAQ question, a mandatory handoff,
  an unsupported problem, spam, and payment information if present.
- [ ] Write `notes/sample_review.md`: customer need, relevant FAQ/client rule,
  and what a useful answer should contain.
- [ ] Define Gemini input: redacted subject/body, relevant ticket metadata, FAQ
  text, and client rules. Exclude API secrets and example labels.
- [ ] Show one input JSON and expected reply, handoff, and close output examples.

**Review:** Understand the tickets and the information the model receives.
**Done when:** We can explain the input and output fields using concrete samples.

## Step 2 — Finalize the structured contract and prompt

- [ ] Refine `src/agent/schemas.py` based on the samples. Use the Pydantic model
  to generate the JSON Schema passed through LiteLLM to Gemini.
- [ ] Enforce action-specific fields: reply needs a reply, handoff needs an English
  note, and close needs neither. Exclude irrelevant fields from API payloads.
- [ ] Decide whether internal FAQ references are useful for inspecting grounding;
  these would stay out of the helpdesk POST body.
- [ ] Write `prompts/system.md`: FAQ-only answers, always-to-human cases,
  priorities, customer-language replies, and ticket text treated as data.

**Review:** Read the prompt beside the sample input/output.
**Done when:** Valid outputs parse, invalid combinations fail validation, and all
three actions are clearly defined without Jev deciding anything.

## Step 3 — Generate and inspect the first Gemini decisions

- [ ] Implement `nodes/redact.py` to mask payment details in subject and body
  before model calls. Check representative IBAN/card examples.
- [ ] Implement `clients/llm.py` and `nodes/draft.py`: Gemini through LiteLLM,
  structured output, Pydantic validation, one retry, then handoff fallback.
- [ ] Add a preview script that reads a saved ticket and writes sanitized input,
  decision, and token usage locally, without posting to the helpdesk.
- [ ] Inspect a small set covering reply, handoff, and close.

**Review:** Show actual model input/output and explain the chosen action.
**Done when:** Decisions validate, fallback is demonstrable, and saved previews
contain no payment details.

## Step 4 — Establish an evaluation baseline

- [ ] Implement `eval/run_eval.py` and `eval/metrics.py` using the 10 examples.
  Give the model ticket fields only; retain supplied labels separately as truth.
- [ ] Save predictions, prompt/model settings, usage, and baseline results under
  `eval/results/`. Report action, category, priority, and language accuracy,
  individual mismatches, and mandatory-handoff failures.
- [ ] Review reply usefulness and FAQ grounding, including unsupported claims.
- [ ] Initially work directly in the customer's language. Check Dutch instructions,
  menu names, numbers, and claims against the FAQ. Use an English back-translation
  for review if needed; treat it as a review aid, not proof of correctness, and
  record any additional model cost.

**Review:** Inspect failures and choose one concrete improvement.
**Done when:** We have a reproducible baseline and a documented issue to fix.

## Step 5 — Add Jev as an independent score

- [ ] Read the TypeSafe integration skill and current Jev documentation.
- [ ] Configure `JEV_API_KEY` and define the scoring question in
  `config/jev_questions.yaml`: confidence that the proposed decision is supported
  by the FAQ and follows the client rules. Verify what the returned score means.
- [ ] Implement `clients/jev.py` and `nodes/score.py`. Supply the redacted ticket,
  FAQ/rules, and validated decision; attach only confidence.
- [ ] Bound scoring retries. If scoring fails, record the failure and omit optional
  confidence; do not invent a score or change the decision.

**Review:** Show the same decision before and after scoring.
**Done when:** Only confidence is added; no graph edge or action depends on it.
**Dependency:** A working Jev key is required to verify real scoring.

## Step 6 — Connect the local LangGraph flow

- [ ] Implement a fake helpdesk adapter backed by fixtures and a separate store of
  simulated outcomes. Keep source fixtures unchanged.
- [ ] Wire `graph.py`, `state.py`, and the nodes; `main.py` iterates ticket IDs.
- [ ] Add preview mode that stops before posting, and simulation mode that sends
  actions only to the fake client.
- [ ] Write sanitized per-ticket logs, including skips and failures. Check replies,
  notes, reasons, and exception logs for payment details before saving/posting.

```text
START → fetch → skip_done
                 ├─ already handled → log → END
                 └─ open → redact → draft → score → act → log → END
```

`draft` includes validation/retry/fallback. `score` adds information. `act` selects
the endpoint using the action already present in the decision.

**Review:** Inspect a complete trace and a simulation of the saved 30 tickets.
**Done when:** The graph works locally and every attempted ticket has a sanitized
log entry.

## Step 7 — Add reliable delivery and the real helpdesk client

- [ ] Extend the read-only `clients/helpdesk.py` with action posting and request
  pacing below the API limit. Add and test bounded 503 backoff and 429
  `Retry-After` handling in `retry.py`, including transport failures. Treat 409
  as already handled; do not retry it. Surface permanent errors.
- [ ] Add `src/agent/ledger.py` for durable tracking. Also check server handled
  state: a local ledger alone cannot prove whether a timed-out POST was saved.
- [ ] Reconcile uncertain POST outcomes before resending. Test interruption,
  restart, and rerun behavior with the fake client.
- [ ] Separate simulation/live ledger state. Explicit practice resets must start
  new run state so stale entries cannot skip reopened tickets.
- [ ] Add explicit live mode and verify read-only access before live actions.

**Review:** Demonstrate 503, 429, 409, and uncertain POST recovery.
**Done when:** Restart/rerun checks produce no duplicate customer replies,
pagination is complete, and failures remain visible.

## Step 8 — Apply one measured fix

- [ ] Apply the improvement chosen from the baseline, with an explainable change.
- [ ] Rerun the same 10 examples with the same model/settings except for the fix.
  Save before/after results and inspect regressions.
- [ ] Record model and Jev usage/cost. Calculate cost per 100 tickets, stating
  pricing assumptions and including retries/translation calls where applicable.

**Review:** Compare actual baseline and revised outputs.
**Done when:** One fix has a documented before/after result and explicit limitations.
The 10-example evaluation does not establish broad accuracy.

## Step 9 — Final run and delivery documentation

- [ ] Finish CLI/Makefile commands for preview, simulation, eval, and live run.
- [ ] Confirm candidate identity, configuration, and final preview.
- [ ] Explicitly reset practice tickets, run all 30 live, then rerun and verify
  that it posts nothing. Save sanitized evidence and final status.
- [ ] Write a README of at most one page with the required headings: **How to run**,
  **Decisions**, **Reliability**, **Eval and fix**, **What I would improve**.
  Explain Dutch handling, Jev's score-only role, cost calculation, and AI
  assistance used to build the project.
- [ ] Verify tracked files contain no keys or payment details.

**Review:** Run command, final status, rerun evidence, evaluation, and README.
**Done when:** The assignment runs with one command and its behavior is explainable.

## Next step

**Step 1: inspect saved samples and agree on the exact Gemini input.** Use those
examples to shape the contract and prompt before implementing the full client,
graph, or Jev integration.
