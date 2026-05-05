.PHONY: run ui test lint typecheck eval

run:
	uv run uvicorn resolver.api.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	uv run streamlit run src/resolver/ui/app.py

test:
	uv run pytest -q

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

eval:
	uv run python evals/run_evals.py
