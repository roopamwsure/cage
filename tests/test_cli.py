from pathlib import Path
from importlib.metadata import version
import subprocess
import sys
import tomllib

from cage import CAGE, DecisionState, EvaluationOutcome
from cage.cli import main
from cage.warrants import dump_warrant, export_warrant


def _warrant_file(path: Path) -> None:
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    action = cage.inputs.action(
        action_type="database.delete", principal_id="private-principal",
        agent_id="private-agent", resource_id="private-resource",
        requested_effect={"secret": "private-value"},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="private-key")
    dump_warrant(export_warrant(evaluation), path)


def test_inspect_prints_lifecycle_metadata_without_private_values(tmp_path, capsys) -> None:
    path = tmp_path / "warrant.json"
    _warrant_file(path)
    assert main(["warrant", "inspect", str(path)]) == 0
    output = capsys.readouterr()
    assert "Decision: admitted" in output.out
    assert "Disclosure: summary" in output.out
    assert "Effect: none" in output.out
    assert "Observation origin: none" in output.out
    assert "Warrant ID: " in output.out
    assert "private" not in output.out + output.err


def test_validate_reports_disclosure_and_structural_result(tmp_path, capsys) -> None:
    path = tmp_path / "warrant.json"
    _warrant_file(path)
    assert main(["warrant", "validate", str(path)]) == 0
    output = capsys.readouterr()
    assert "Structural validity: valid" in output.out
    assert "Disclosure: summary" in output.out
    assert "Omitted fields:" in output.out
    assert "action.principal_id" in output.out
    assert "private" not in output.out + output.err


def test_invalid_record_returns_2_and_missing_file_returns_1(tmp_path, capsys) -> None:
    bad = tmp_path / "malformed.json"
    bad.write_text('{"format": "cage.warrant", "format": "duplicate"}', encoding="utf-8")
    assert main(["warrant", "validate", str(bad)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "Invalid portable Warrant" in output.err
    assert "duplicate" not in output.err
    assert main(["warrant", "inspect", str(tmp_path / "missing")]) == 1
    assert "Could not read" in capsys.readouterr().err


def test_module_entrypoint_help_version_and_argument_errors() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["scripts"]["cage"] == "cage.cli:main"
    for argument, code, fragment in (
        ("--help", 0, "warrant"),
        ("--version", 0, version("cage-assurance")),
        ("invalid", 2, "invalid choice"),
    ):
        result = subprocess.run(
            [sys.executable, "-m", "cage.cli", argument],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == code
        assert fragment in result.stdout + result.stderr
