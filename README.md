# epic-creator-eval

This repository is the orchestration layer for evaluating the Epic Creator
agent. Its role is to select the requested Epic Creator revision, run the
existing evaluation suite through Fullsend and the agent evaluation harness,
collect metrics and artifacts, and return reviewable results.

The [Epic Creator repository](https://github.com/fullsend-ai/epic-creator)
remains the source of truth for the agent, evaluation cases, judges, rubric,
configuration, dataset, and Fullsend runner profile. This repository owns the
orchestration around that suite: revision selection, execution, artifact
collection, and reporting.

## Evaluation

- Manual and PR runs select the requested revision or PR, configuration, cases,
  and models; revisions resolve to an exact commit and PR runs use their head.
- Each run records scores, cost, duration, logs, artifacts, source SHA, and pinned versions.

## Development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
make lint
uv build
```

`make lint` checks Python linting, formatting, and types. `make format` rewrites
Python formatting. `make test` runs pytest, which checks the installed package
scaffold. The [checks workflow](.github/workflows/checks.yml) installs locked
dependencies, runs lint and type checks, runs pytest, and builds the package
without launching evaluations.

## Contributing

Keep changes small and focused. When adding orchestration behavior, add tests
that assert observable outcomes rather than internal structure. Follow
[CONTRIBUTING.md](CONTRIBUTING.md) for commit and pull request requirements.
Do not commit credentials or generated output.
