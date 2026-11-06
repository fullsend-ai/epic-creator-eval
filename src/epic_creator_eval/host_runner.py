"""Run the Epic Creator evaluation through the existing agent eval harness.

The caller prepares an Epic Creator checkout and an agent-eval-harness checkout
at the revisions to evaluate and owns credentials and publication. This module
only drives the suite's own ``eval/profiles/fullsend.yaml`` through the
harness's supported pipeline scripts. Every setup, execution, collection,
judging, and reporting failure stays non-zero, and a judging failure still
attempts the report. Quality results remain in the harness's ``run_result.json``,
``summary.yaml``, and ``report.html``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

CONFIG_RELATIVE = Path("eval/profiles/fullsend.yaml")
SCRIPTS_RELATIVE = Path("skills/eval-run/scripts")

_EVAL_NAME_PROBE = (
    "import sys\n"
    "from agent_eval.config import EvalConfig\n"
    "print(EvalConfig.from_yaml(sys.argv[1]).eval_name())\n"
)


class StepError(Exception):
    """A pipeline step failed; the step's exit code is preserved."""

    def __init__(self, step: str, code: int) -> None:
        super().__init__(f"{step} failed with exit code {code}")
        self.step = step
        self.code = code


def _run_step(
    step: str,
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print(f"==> {step}", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=capture)
    except OSError as exc:
        raise StepError(step, 1) from exc
    if capture:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise StepError(step, proc.returncode)
    return proc


def _suite_name(python: str, harness: Path, config: Path, *, cwd: Path, env: dict[str, str]) -> str:
    """Ask the harness which run directory name this suite uses."""
    proc = _run_step(
        "config",
        [python, "-c", _EVAL_NAME_PROBE, str(config)],
        cwd=cwd,
        env=env,
        capture=True,
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise StepError("config", 1)
    return lines[-1]


def _workspace_path(proc: subprocess.CompletedProcess[str]) -> Path:
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith("WORKSPACE: "):
            workspace = Path(line.removeprefix("WORKSPACE: ").strip())
            if workspace.is_dir():
                return workspace
    raise StepError("workspace", 1)


def _case_exit_failure(run_dir: Path) -> tuple[str, int] | None:
    """Return a diagnostic when a case execution failed.

    ``execute.py`` aggregates case exit codes with ``max``, so a runner launch
    failure or timeout (-1) next to a successful case leaves the run exit code
    at zero.
    """
    result_path = run_dir / "run_result.json"
    try:
        result = json.loads(result_path.read_text())
    except (OSError, ValueError):
        return f"cannot read {result_path}", 1
    per_case = result.get("per_case") if isinstance(result, dict) else None
    if not isinstance(per_case, dict) or not per_case:
        return f"{result_path} has no per-case results", 1
    failed: list[str] = []
    codes: list[int] = []
    for case_id, case in per_case.items():
        code = case.get("exit_code") if isinstance(case, dict) else None
        if not isinstance(code, int) or isinstance(code, bool):
            return f"{result_path}: case {case_id} has no integer exit_code", 1
        if code != 0:
            failed.append(f"{case_id} (exit {code})")
            codes.append(code)
    if not failed:
        return None
    code = max((c for c in codes if c > 0), default=1)
    return f"case execution failed: {', '.join(failed)}", code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m epic_creator_eval.host_runner",
        description="Run Epic Creator's evaluation suite through the agent eval harness.",
    )
    parser.add_argument("--epic-creator", required=True, help="Prepared Epic Creator checkout")
    parser.add_argument("--harness", required=True, help="Prepared agent-eval-harness checkout")
    parser.add_argument("--output", required=True, help="Directory for durable run artifacts")
    parser.add_argument("--run-id", default="manual", help="Run identifier (default: manual)")
    args = parser.parse_args(argv)

    epic_creator = Path(args.epic_creator).resolve()
    harness = Path(args.harness).resolve()
    output = Path(args.output).resolve()
    config = epic_creator / CONFIG_RELATIVE
    scripts = harness / SCRIPTS_RELATIVE
    required = [
        config,
        scripts / "workspace.py",
        scripts / "execute.py",
        scripts / "collect.py",
        scripts / "score.py",
        scripts / "report.py",
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        for path in missing:
            print(f"ERROR: missing required path: {path}", file=sys.stderr)
        return 2

    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["AGENT_EVAL_RUNS_DIR"] = str(output)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(harness), *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])]
    )
    python = sys.executable
    run_id = args.run_id

    run_dir: Path | None = None
    try:
        suite = _suite_name(python, harness, config, cwd=epic_creator, env=env)
        run_dir = output / suite / run_id
        workspace_proc = _run_step(
            "workspace",
            [python, str(scripts / "workspace.py"), "--config", str(config), "--run-id", run_id],
            cwd=epic_creator,
            env=env,
            capture=True,
        )
        workspace = _workspace_path(workspace_proc)
        _run_step(
            "execute",
            [
                python,
                str(scripts / "execute.py"),
                "--config",
                str(config),
                "--workspace",
                str(workspace),
                "--output",
                str(run_dir),
                "--run-id",
                run_id,
            ],
            cwd=epic_creator,
            env=env,
        )
        execute_problem = _case_exit_failure(run_dir)
        if execute_problem:
            message, code = execute_problem
            print(f"ERROR: {message}", file=sys.stderr)
            raise StepError("execute", code)
        _run_step(
            "collect",
            [
                python,
                str(scripts / "collect.py"),
                "--config",
                str(config),
                "--workspace",
                str(workspace),
                "--output",
                str(run_dir),
            ],
            cwd=epic_creator,
            env=env,
        )
        report_cmd = [
            python,
            str(scripts / "report.py"),
            "--run-id",
            run_id,
            "--config",
            str(config),
        ]
        judge_failure: StepError | None = None
        try:
            _run_step(
                "judges",
                [
                    python,
                    str(scripts / "score.py"),
                    "judges",
                    "--run-id",
                    run_id,
                    "--config",
                    str(config),
                ],
                cwd=epic_creator,
                env=env,
            )
        except StepError as exc:
            # A judging failure (threshold breach or judging error) still gets a
            # report attempt, but keeps its own exit status.
            judge_failure = exc
            print(f"ERROR: judges failed (exit {exc.code}); attempting report", file=sys.stderr)
        try:
            _run_step("report", report_cmd, cwd=epic_creator, env=env)
        except StepError as exc:
            if judge_failure is None:
                raise
            print(f"ERROR: report also failed (exit {exc.code})", file=sys.stderr)
        if judge_failure is not None:
            raise judge_failure
    except StepError as exc:
        print(f"FAILED: {exc.step} (exit {exc.code})", file=sys.stderr)
        print(f"DIAGNOSTICS: {run_dir or output}", file=sys.stderr)
        return exc.code or 1

    print(f"RUN_DIR: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
