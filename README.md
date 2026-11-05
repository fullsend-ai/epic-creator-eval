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

## Evaluation interface

- Manual and pull request runs select an Epic Creator revision, evaluation
  configuration, cases, and models. Resolve the requested revision to an exact
  commit; a pull request run evaluates its head, never a fallback branch.
- Record the source commit, selected inputs, and harness and runtime versions
  with each result so runs can be reproduced and compared.
- Retain per-case scores, aggregate verdicts, cost, duration, logs, generated
  artifacts, and review evidence. Report setup and execution failures separately
  from quality verdicts; publishing results must not hide the original outcome.
- Keep reporting credentials outside the evaluated process and sandbox. Use
  evaluation-scoped model credentials, perform no Jira writes, and restrict
  access to sensitive run artifacts.

## Contributing

Keep changes small and focused. When adding orchestration behavior, add tests
that assert observable outcomes rather than internal structure. Follow
[CONTRIBUTING.md](CONTRIBUTING.md) for commit and pull request requirements.
Do not commit credentials or generated output.
