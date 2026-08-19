from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from agent_effects.cli import app
from agent_effects.examples.refund import make_refund_case
from agent_effects.schemas import SCHEMA_EXPORTS, export_schemas


def test_schema_export_is_deterministic_and_matches_checked_in_fixtures(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_paths = export_schemas(first)
    second_paths = export_schemas(second)
    fixture_root = Path(__file__).parents[1] / "schemas" / "v1alpha1"

    assert [path.name for path in first_paths] == [path.name for path in second_paths]
    assert len(first_paths) == len(SCHEMA_EXPORTS)
    for first_path, second_path in zip(first_paths, second_paths, strict=True):
        assert first_path.read_bytes() == second_path.read_bytes()
        assert first_path.read_bytes() == (fixture_root / first_path.name).read_bytes()
        payload = json.loads(first_path.read_text(encoding="utf-8"))
        assert "v1alpha1" in payload["$id"]
        assert payload["x-agent-effects-schema-version"] == "v1alpha1"
        assert str(Path.home()) not in first_path.read_text(encoding="utf-8")
        Draft202012Validator.check_schema(payload)


def test_exported_case_schema_validates_a_public_example(tmp_path: Path) -> None:
    output = tmp_path / "schemas"
    export_schemas(output)
    schema = json.loads((output / "test-case.schema.json").read_text(encoding="utf-8"))
    instance = make_refund_case().model_dump(mode="json")

    Draft202012Validator(schema).validate(instance)


def test_schema_export_cli(tmp_path: Path) -> None:
    output = tmp_path / "schemas"
    result = CliRunner().invoke(app, ["schema", "export", "--output", str(output)])

    assert result.exit_code == 0, result.stdout
    assert "exported" in result.stdout
    assert (output / "trial-result.schema.json").is_file()
