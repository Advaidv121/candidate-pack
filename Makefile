simulate:
	PYTHONPATH=src .venv/bin/python -m agent $(ARGS)

test:
	PYTHONPATH=src .venv/bin/pytest -q
