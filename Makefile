.PHONY: check
check:
	python -m compileall -q src tests
	ruff check src tests
	mypy --strict src
	pytest -q
