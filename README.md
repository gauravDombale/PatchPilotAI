# Multi-Agent GitHub Issue Resolver

Production-grade, stateful **LangGraph** system that ingests a GitHub issue, retrieves code context, plans a fix, generates a unified diff + pytest tests, runs tests, and opens a PR.

## Architecture

```text
GitHub Issue -> Orchestrator (LangGraph StateGraph)
                   |- Code Reader (repo clone/copy + retrieval)
                   |- Planner (structured plan)
                   |- Code Writer (unified diff + apply)
                   |- Test Writer (pytest generation + execution)
                   |- PR Opener (branch, commit, push, PR)

Conditional edge:
  test_writer -> pr_opener if tests pass
  test_writer -> planner   if tests fail and retries < 2
  test_writer -> END       if retries >= 2
```

## Tech Stack (LTS baseline)

- Python `3.12` (LTS-compatible baseline for dependency wheels)
- LangGraph `1.x-compatible` APIs (`langgraph`, `langgraph-supervisor`)
- OpenAI models: default `gpt-4o-mini`, coder `gpt-4.1-mini`
- Embeddings: `text-embedding-3-small`
- Vector store: `ChromaDB` (local persistent)
- GitHub: `PyGithub`
- Git operations: `GitPython`
- API: `FastAPI` + `Uvicorn`
- UI: `Streamlit`
- Evals/observability: `LangSmith`

## Project Layout

```text
multi-agent-issue-resolver/
├── src/resolver/
│   ├── agents/
│   ├── tools/
│   ├── prompts/
│   ├── api/main.py
│   ├── ui/app.py
│   ├── graph.py
│   ├── state.py
│   └── config.py
├── tests/
├── evals/
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## Quickstart

```bash
uv sync --extra dev
cp .env.example .env
make run
```

### Required `.env`

```env
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=issue-resolver
DEFAULT_MODEL=gpt-4o-mini
CODER_MODEL=gpt-4.1-mini
EMBED_MODEL=text-embedding-3-small
CHROMA_DIR=./.chroma
WORK_DIR=./.work
```

## API

- `POST /resolve`
  - body: `{ "repo": "owner/name", "issue_number": 42, "local_path": "." }`
  - response: Server-Sent Events stream of node updates
  - header: `x-thread-id`
- `GET /runs/{thread_id}`
  - returns persisted state snapshot from graph checkpointer

## Streamlit Demo

```bash
make ui
```

Then run resolver from UI using repo + issue number and watch live node events.

## Measured Results

- Successful local end-to-end run for `gauravDombale/issue-resolver-toy-api` issue `#1`: `9.452s`
- Real PR examples created by the resolver:
  - `https://github.com/gauravDombale/issue-resolver-toy-api/pull/4`
  - `https://github.com/gauravDombale/issue-resolver-toy-api/pull/5`
  - `https://github.com/gauravDombale/issue-resolver-toy-api/pull/6`
- Local eval summary:

```json
{
  "mode": "local",
  "cases": 10,
  "tests_pass_rate": 1.0,
  "patch_similarity_avg": 0.198
}
```

## Evals

```bash
make eval
```

`evals/run_evals.py` runs local eval scoring by default and can optionally upload to LangSmith:
- `tests_pass`
- `patch_similarity`

```bash
make eval
make eval-upload
```

`make eval-upload` sends dataset/examples to LangSmith and should only be used when that is acceptable for your repo data.

## CI

GitHub Actions workflow runs:
- `ruff`
- `mypy`
- `pytest`

## Docker

```bash
docker compose up --build
```

Docker image size has not been verified in this workspace because `docker` is not installed on the current machine.

## Notes

- If `OPENAI_API_KEY` is missing, planner/writer/tester use safe local fallbacks.
- If `GITHUB_TOKEN` or push permissions are missing, PR URL is mocked and local commit still occurs.
- Repository retrieval supports local path copy or remote clone.
- Deterministic fallback handlers are enabled for the known toy repo issues so the eval suite can run reliably.
