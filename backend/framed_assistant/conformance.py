from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


def run(contracts_dir: Path) -> int:
    schemas: dict[str, dict] = {}
    for path in sorted(contracts_dir.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schemas[path.name.removesuffix(".schema.json")] = schema

    fixtures = contracts_dir / "fixtures"
    for path in sorted(fixtures.glob("*.valid.json")):
        contract = path.name.split(".valid.json", 1)[0]
        Draft202012Validator(schemas[contract]).validate(json.loads(path.read_text(encoding="utf-8")))

    for path in sorted(fixtures.glob("*.invalid.json")):
        contract = path.name.split(".invalid.json", 1)[0]
        validator = Draft202012Validator(schemas[contract])
        try:
            validator.validate(json.loads(path.read_text(encoding="utf-8")))
        except ValidationError:
            continue
        raise AssertionError(f"Invalid fixture passed validation: {path.name}")

    examples = contracts_dir.parent / "examples"
    example_count = 0
    for path in sorted((examples / "integrations").glob("*.json")):
        Draft202012Validator(schemas["host-integration-manifest"]).validate(
            json.loads(path.read_text(encoding="utf-8"))
        )
        example_count += 1
    for path in sorted((examples / "plugins").glob("*.json")):
        Draft202012Validator(schemas["plugin-manifest"]).validate(json.loads(path.read_text(encoding="utf-8")))
        example_count += 1

    print(
        f"Validated {len(schemas)} schemas, {len(list(fixtures.glob('*.json')))} fixtures, "
        f"and {example_count} examples."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Framed Assistant public contracts")
    parser.add_argument("contracts_dir", nargs="?", type=Path, default=Path("contracts"))
    arguments = parser.parse_args()
    return run(arguments.contracts_dir)


if __name__ == "__main__":
    raise SystemExit(main())
