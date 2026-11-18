.PHONY: run test

run:
	PYTHONPATH=src .venv/bin/python -m agent $(ARGS)

test:
	PYTHONPATH=src .venv/bin/pytest -q
