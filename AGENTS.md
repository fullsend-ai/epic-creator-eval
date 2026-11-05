# Agent guidance

Read [README.md](README.md) before changing this repository.

## Source of truth

- The Epic Creator repository owns the agent, evaluation suite, cases, judges,
  configuration, dataset, and Fullsend runner profile. Do not copy or redefine
  them here.
- Preserve the evaluation rubric. Score and gating changes belong with the
  suite, not in orchestration code.
- Base API, CLI, and configuration claims on the tool's source or official
  documentation. Do not guess supported options.

## Safety

- Never commit credentials, private keys, tokens, or captured secrets.
- The GitHub App private key used for pull request reporting stays on the host.
  It must not enter the evaluation sandbox or the evaluated process.
- Keep host and sandbox credentials separate. Give the sandbox only the
  evaluation-scoped model credentials it needs.
- The evaluation does not write to Jira. Do not pass a production Jira write
  token.
- Keep the evaluation source dataset on an immutable, staged snapshot. Do not
  fetch mutable issue state during a run.

## Changes and tests

- Make the smallest complete change, including affected documentation.
- When adding runtime code, test observable behavior and outcomes. Avoid tests
  tied to internal structure or incidental call order.
- Do not hide a setup or execution failure behind a quality verdict or a
  passing publication status.
- End files with a newline.
- Use `git commit -s` when committing.
