import json
from pathlib import Path

import pytest

from epic_creator_eval import host_runner


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _prepare(
    tmp_path: Path,
    *,
    execute_exit: int = 0,
    collect_exit: int = 0,
    judge_exit: int = 0,
    report_exit: int = 0,
    case_result_text: str | None = None,
    case_diagnostic: str | None = None,
) -> tuple[Path, Path, Path]:
    if case_result_text is None:
        case_result_text = json.dumps(
            {
                "exit_code": 0,
                "cost_usd": 1.5,
                "duration_s": 2.0,
                "per_case": {"case-1": {"exit_code": 0}},
            }
        )
    epic = tmp_path / "epic-creator"
    _write(epic / "eval/profiles/fullsend.yaml", "name: epic-decompose\n")
    harness = tmp_path / "harness"
    _write(harness / "agent_eval/__init__.py", "")
    _write(
        harness / "agent_eval/config.py",
        "class EvalConfig:\n"
        "    @classmethod\n"
        "    def from_yaml(cls, path):\n"
        "        return cls()\n"
        "    def eval_name(self):\n"
        "        return 'demo-suite'\n",
    )
    scripts = harness / "skills/eval-run/scripts"
    _write(
        scripts / "workspace.py",
        "import argparse, pathlib\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--config')\n"
        "p.add_argument('--run-id')\n"
        "a = p.parse_args()\n"
        "ws = pathlib.Path(__file__).parent / 'workspace'\n"
        "ws.mkdir()\n"
        "print(f'WORKSPACE: {ws}')\n",
    )
    _write(
        scripts / "execute.py",
        "import argparse, pathlib\n"
        "p = argparse.ArgumentParser()\n"
        "for flag in ('--config', '--workspace', '--output', '--run-id'):\n"
        "    p.add_argument(flag)\n"
        "a = p.parse_args()\n"
        "out = pathlib.Path(a.output)\n"
        "out.mkdir(parents=True)\n"
        f"(out / 'run_result.json').write_text({case_result_text!r})\n"
        f"diagnostic = {case_diagnostic!r}\n"
        "if diagnostic is not None:\n"
        "    case = pathlib.Path(a.workspace) / 'cases' / 'case-1'\n"
        "    case.mkdir(parents=True, exist_ok=True)\n"
        "    (case / 'diagnostic.txt').write_text(diagnostic)\n"
        f"raise SystemExit({execute_exit})\n",
    )
    _write(
        scripts / "collect.py",
        "import argparse, pathlib, shutil\n"
        "p = argparse.ArgumentParser()\n"
        "for flag in ('--config', '--workspace', '--output'):\n"
        "    p.add_argument(flag)\n"
        "a = p.parse_args()\n"
        "out = pathlib.Path(a.output)\n"
        "(out / 'collection.json').write_text('{}')\n"
        "cases = pathlib.Path(a.workspace) / 'cases'\n"
        "if cases.is_dir():\n"
        "    for case in sorted(c for c in cases.iterdir() if c.is_dir()):\n"
        "        for f in sorted(f for f in case.rglob('*') if f.is_file()):\n"
        "            dest = out / 'cases' / case.name / f.relative_to(case)\n"
        "            dest.parent.mkdir(parents=True, exist_ok=True)\n"
        "            shutil.copy2(f, dest)\n"
        f"raise SystemExit({collect_exit})\n",
    )
    _write(
        scripts / "score.py",
        "import argparse, os, pathlib\n"
        "p = argparse.ArgumentParser()\n"
        "sub = p.add_subparsers(dest='command', required=True)\n"
        "j = sub.add_parser('judges')\n"
        "j.add_argument('--run-id')\n"
        "j.add_argument('--config')\n"
        "a = p.parse_args()\n"
        "run = pathlib.Path(os.environ['AGENT_EVAL_RUNS_DIR']) / 'demo-suite' / a.run_id\n"
        "run.mkdir(parents=True, exist_ok=True)\n"
        "(run / 'summary.yaml').write_text('judges: {}\\n')\n"
        f"raise SystemExit({judge_exit})\n",
    )
    _write(
        scripts / "report.py",
        "import argparse, os, pathlib\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--run-id')\n"
        "p.add_argument('--config')\n"
        "a = p.parse_args()\n"
        "run = pathlib.Path(os.environ['AGENT_EVAL_RUNS_DIR']) / 'demo-suite' / a.run_id\n"
        "(run / 'report.html').write_text('<html></html>')\n"
        f"raise SystemExit({report_exit})\n",
    )
    return epic, harness, tmp_path / "artifacts"


def _run(epic: Path, harness: Path, output: Path) -> int:
    return host_runner.main(
        [
            "--epic-creator",
            str(epic),
            "--harness",
            str(harness),
            "--output",
            str(output),
            "--run-id",
            "run-1",
        ]
    )


def test_success_runs_suite_and_retains_artifacts(tmp_path):
    epic, harness, output = _prepare(tmp_path)

    assert _run(epic, harness, output) == 0

    run_dir = output / "demo-suite" / "run-1"
    assert json.loads((run_dir / "run_result.json").read_text())["cost_usd"] == 1.5
    assert (run_dir / "collection.json").is_file()
    assert (run_dir / "summary.yaml").is_file()
    assert (run_dir / "report.html").is_file()


def test_failed_case_is_nonzero_despite_zero_aggregate(tmp_path, capsys):
    payload = json.dumps(
        {
            "exit_code": 0,
            "per_case": {"case-ok": {"exit_code": 0}, "case-bad": {"exit_code": -1}},
        }
    )
    epic, harness, output = _prepare(tmp_path, case_result_text=payload)

    assert _run(epic, harness, output) != 0

    run_dir = output / "demo-suite" / "run-1"
    assert (run_dir / "run_result.json").is_file()
    assert not (run_dir / "summary.yaml").exists()
    assert not (run_dir / "report.html").exists()
    assert "case-bad" in capsys.readouterr().err


@pytest.mark.parametrize("payload", ['{"exit_code": 0}', "not json"])
def test_missing_or_malformed_case_results_fail(tmp_path, payload):
    epic, harness, output = _prepare(tmp_path, case_result_text=payload)

    assert _run(epic, harness, output) != 0

    run_dir = output / "demo-suite" / "run-1"
    assert not (run_dir / "summary.yaml").exists()
    assert not (run_dir / "report.html").exists()


def test_execution_failure_is_nonzero_and_keeps_diagnostics(tmp_path):
    epic, harness, output = _prepare(tmp_path, execute_exit=3)

    assert _run(epic, harness, output) == 3

    run_dir = output / "demo-suite" / "run-1"
    assert json.loads((run_dir / "run_result.json").read_text())["duration_s"] == 2.0
    assert not (run_dir / "summary.yaml").exists()
    assert not (run_dir / "report.html").exists()


def test_execution_failure_still_collects_case_diagnostics(tmp_path):
    epic, harness, output = _prepare(tmp_path, execute_exit=3, case_diagnostic="runner timed out\n")

    assert _run(epic, harness, output) == 3

    run_dir = output / "demo-suite" / "run-1"
    collected = run_dir / "cases" / "case-1" / "diagnostic.txt"
    assert collected.read_text() == "runner timed out\n"
    assert not (run_dir / "summary.yaml").exists()
    assert not (run_dir / "report.html").exists()


def test_failed_case_still_collects_diagnostics_despite_zero_aggregate(tmp_path):
    payload = json.dumps(
        {
            "exit_code": 0,
            "per_case": {"case-ok": {"exit_code": 0}, "case-bad": {"exit_code": -1}},
        }
    )
    epic, harness, output = _prepare(
        tmp_path, case_result_text=payload, case_diagnostic="launch failed\n"
    )

    assert _run(epic, harness, output) != 0

    run_dir = output / "demo-suite" / "run-1"
    assert (run_dir / "cases" / "case-1" / "diagnostic.txt").read_text() == "launch failed\n"
    assert not (run_dir / "summary.yaml").exists()
    assert not (run_dir / "report.html").exists()


def test_execute_and_collect_failure_keeps_execute_exit_and_diagnostics(tmp_path, capsys):
    epic, harness, output = _prepare(
        tmp_path, execute_exit=3, collect_exit=6, case_diagnostic="partial output\n"
    )

    assert _run(epic, harness, output) == 3

    run_dir = output / "demo-suite" / "run-1"
    assert (run_dir / "cases" / "case-1" / "diagnostic.txt").read_text() == "partial output\n"
    assert not (run_dir / "summary.yaml").exists()
    assert not (run_dir / "report.html").exists()
    err = capsys.readouterr().err
    assert "execute" in err
    assert "collect" in err


def test_collect_failure_after_successful_execution_is_nonzero(tmp_path):
    epic, harness, output = _prepare(tmp_path, collect_exit=6)

    assert _run(epic, harness, output) == 6

    run_dir = output / "demo-suite" / "run-1"
    assert (run_dir / "collection.json").is_file()
    assert not (run_dir / "summary.yaml").exists()
    assert not (run_dir / "report.html").exists()


def test_report_failure_is_nonzero_and_keeps_diagnostics(tmp_path):
    epic, harness, output = _prepare(tmp_path, report_exit=4)

    assert _run(epic, harness, output) == 4

    run_dir = output / "demo-suite" / "run-1"
    assert (run_dir / "summary.yaml").is_file()
    assert (run_dir / "report.html").is_file()


def test_judge_failure_still_writes_report_and_keeps_judge_exit(tmp_path):
    epic, harness, output = _prepare(tmp_path, judge_exit=5)

    assert _run(epic, harness, output) == 5

    run_dir = output / "demo-suite" / "run-1"
    assert (run_dir / "summary.yaml").is_file()
    assert (run_dir / "report.html").is_file()


def test_judge_and_report_failure_keeps_judge_exit_and_reports_both(tmp_path, capsys):
    epic, harness, output = _prepare(tmp_path, judge_exit=5, report_exit=4)

    assert _run(epic, harness, output) == 5

    run_dir = output / "demo-suite" / "run-1"
    assert (run_dir / "summary.yaml").is_file()
    assert (run_dir / "report.html").is_file()
    err = capsys.readouterr().err
    assert "judges" in err
    assert "report" in err


def test_missing_suite_config_fails_before_running(tmp_path):
    epic, harness, output = _prepare(tmp_path)
    (epic / "eval/profiles/fullsend.yaml").unlink()

    assert _run(epic, harness, output) != 0
    assert not (output / "demo-suite").exists()
