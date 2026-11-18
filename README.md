## How to run

With Python 3.11+, run `python3 -m venv .venv` and `.venv/bin/pip install -e .`. Copy `.env.example` to `.env` and fill in Helpdesk credentials, `FAL_KEY` and, for scoring, `JEV_API_KEY`. Run `make run` to post decisions to the configured helpdesk (or `make run ARGS='--score'` to add Jev scoring, and `make run ARGS='--reset'` to re-open tickets). Run `make test` for automated checks and `.venv/bin/python eval/run_eval.py` for the labelled evaluation.

Preview without posting: `.venv/bin/python scripts/preview_ticket.py T005`. See `src/agent/graph.py` for the workflow, `src/agent/schemas.py` for the output fields, and `prompts/system.md` for the decision rules.

Optional Langfuse tracing: set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` to your project's region or self-hosted URL in `.env`. `LANGFUSE_BASE_URL` is also supported and takes precedence over `LANGFUSE_HOST`. Both preview and delivery graphs attach the callback automatically, and buffered traces flush at process exit. Set `LANGFUSE_TRACING_ENABLED=false` to disable tracing. Traces include graph inputs and outputs, including ticket content; only enable this for data permitted in your Langfuse project.

## Decisions

LangGraph runs a validated Pydantic decision from DeepSeek V4.1 Flash via fal.ai and LiteLLM. It replies from the FAQ in the customer's language (including Dutch), hands off with an English note when required or unsupported, or closes spam. Jev adds optional action confidence; it never changes the decision.

## Reliability

The runner fetches open tickets across pages. It bounds transient model and helpdesk retries, respects rate limits, and checks server state before retrying an uncertain write. Logs contain outcome metadata. Pattern matching masks card and IBAN numbers before model calls and in generated text.

## Eval and fix

Clarifying the difference between compliance review and urgent risk moved priority from 9/10 to 10/10; action, category, and language label stayed at 10/10. E01 still overstates the cause of a crash. The revised run used 18,721 input and 3,427 output tokens. At the same mix, 100 tickets cost 0.18721 × input rate + 0.03427 × output rate (USD per million tokens), plus Jev and retries. Jev adds $0.042 per million input tokens; exact fal rates and Jev token totals were not verified. Codex assisted with implementation, tests, and documentation.

## What I would improve

Measure grounding and actual reply language, especially Dutch; expand the labelled set, improve payment pattern coverage, and record billed usage for both providers.
