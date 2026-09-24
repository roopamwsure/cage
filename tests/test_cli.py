from pathlib import Path
from importlib.metadata import version
import subprocess
import sys
import tomllib

from cage import CAGE, DecisionState, EvaluationOutcome
from cage.cli import main
from cage.warrants import dump_warrant, export_warrant, load_warrant


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


def test_database_delete_example_exports_summary_warrant(tmp_path, capsys) -> None:
    destination = tmp_path / "delete-warrant.json"
    assert main(["example", "database.delete", "--warrant", str(destination)]) == 0
    output = capsys.readouterr()
    assert "Decision: admitted" in output.out
    assert "Adapter: acknowledged" in output.out
    assert "Verification: verified_bound" in output.out
    assert "Effect: bound" in output.out
    assert output.err == ""
    document = load_warrant(destination)
    assert document.disclosure.value == "summary"
    assert document.effect_state.value == "bound"
    assert document.observation_origin == "adapter"
    assert document.to_dict()["action"]["requested_effect"]["parameters"] is None


def test_example_refuses_existing_destination_without_replacing(tmp_path, capsys) -> None:
    destination = tmp_path / "existing.json"
    destination.write_text("original", encoding="utf-8")
    assert main(["example", "database.delete", "--warrant", str(destination)]) == 1
    output = capsys.readouterr()
    assert "Could not read or write" in output.err
    assert "Traceback" not in output.err
    assert destination.read_text(encoding="utf-8") == "original"


def test_module_entrypoint_runs_example_without_source_script(tmp_path) -> None:
    destination = tmp_path / "warrant.json"
    result = subprocess.run(
        [sys.executable, "-m", "cage.cli", "example", "database.delete",
         "--warrant", str(destination)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Effect: bound" in result.stdout
    assert load_warrant(destination).effect_state.value == "bound"
