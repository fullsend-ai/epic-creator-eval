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

- Manual runs select the requested revision or PR and use the suite's own
  configuration, cases, and models; revisions resolve to an exact commit and PR
  runs use their head.
- Each run records scores, cost, duration, logs, artifacts, source SHA, and pinned versions.

## Manual evaluation

Dispatch the [evaluate workflow](.github/workflows/eval.yml) with an Epic
Creator branch, tag, or commit SHA (default `main`) or a pull request number.
It resolves the request to one commit and runs that commit's suite through
Fullsend on a GitHub-hosted runner.

The selected source runs with evaluation credentials. Dispatch only revisions
and pull requests you trust with those credentials.

Each dispatch pins the Epic Creator commit and the agent evaluation harness
commit, records them with the Fullsend version as `provenance.txt`, and uploads
the run directory, its logs, and provenance on success and on failure. Which
artifacts exist depends on how far the run got: results and logs are kept after
an execution failure, and a judging failure still runs the report step. A failed
case execution fails the run even when the harness's aggregate exit code is
zero. The workload identity credentials file stays in the orchestration
checkout, outside the evaluated source and every evaluation workspace.

**Cost.** The suite's `$80` budget is per case, and the Fullsend runner at the
pinned harness revision accepts `max_budget_usd` as a hint only, so it does not
stop spending. The six-hour job timeout limits duration, not spend. A full run
executes 30 cases sequentially, its runtime is unknown, and the job timeout can
end it with a partial run. No spending guard, sharding, or case selection is
implemented.

The workflow runs the host runner below. To run it yourself with prepared
checkouts and model credentials:

```bash
PYTHONPATH=src <harness-python> -m epic_creator_eval.host_runner \
  --epic-creator /path/to/epic-creator \
  --harness /path/to/agent-eval-harness \
  --output artifacts/manual-run \
  --run-id manual
```

`<harness-python>` must be able to import the harness checkout, for example its
`uv` environment. The caller prepares both checkouts at the revisions under
evaluation and provides model credentials; the runner resolves no revisions,
fetches no data, and handles no credentials. It runs the suite's
`eval/profiles/fullsend.yaml` with suite defaults through the harness's
workspace, execute, collect, judge, and report steps, and exits non-zero if any
of those steps fails or if a case execution failed. Results, logs, cost, and
duration land in `<output>/epic-decompose/<run-id>/`.

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
