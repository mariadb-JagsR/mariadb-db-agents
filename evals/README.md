# Evaluation Harness

This directory contains a lightweight LLM-as-judge evaluation setup for the
MariaDB DBA Orchestrator. It runs a dataset of questions against the agent and
scores responses on correctness, completeness, safety, actionability, and
faithfulness to evidence.

## Prerequisites

- Set `OPENAI_API_KEY` in your environment or `.env`
- Configure database credentials if you want full agent tool execution:
  `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_DATABASE`

## Run Evaluations

From `mariadb_db_agents`:

```bash
python -m mariadb_db_agents.scripts.run_evals
```

Limit cases:

```bash
python -m mariadb_db_agents.scripts.run_evals --max-cases 5
```

Use a separate judge model:

```bash
OPENAI_EVAL_MODEL=gpt-4o-mini \
python -m mariadb_db_agents.scripts.run_evals
```

## Dataset Format

Datasets are JSONL with fields:

- `id`
- `question`
- `expectations` (list of key points)
- `category` (optional)
- `audience` (optional)

See `evals/datasets/orchestrator_questions.jsonl` for examples.

## Output

Results are written to `evals/results/eval_results_<timestamp>.json` with:

- Per-case answer + judge scores
- Aggregate summary with averages and pass rate
