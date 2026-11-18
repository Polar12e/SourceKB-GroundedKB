#!/usr/bin/env python3
"""Validate GroundedKB contract schemas, examples and OpenAPI structure."""

from __future__ import annotations

import json
import pathlib
import re
import sys

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts" / "schemas"
EXAMPLES = ROOT / "contracts" / "examples"
OPENAPI = ROOT / "contracts" / "openapi.yaml"


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    failures: list[str] = []
    registry = Registry()
    schemas: dict[str, dict] = {}

    for path in sorted(SCHEMAS.glob("*.schema.json")):
        try:
            schema = load_json(path)
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, SchemaError) as exc:
            failures.append(f"{path.name}: invalid schema: {exc}")
            continue

        schema_id = schema.get("$id")
        if not schema_id:
            failures.append(f"{path.name}: missing $id")
            continue

        resource = Resource.from_contents(schema)
        registry = registry.with_resource(schema_id, resource)
        registry = registry.with_resource(path.as_uri(), resource)
        schemas[path.name.removesuffix(".schema.json")] = schema

    example_paths = sorted(EXAMPLES.glob("*.json"))
    for path in example_paths:
        name = path.stem
        schema = schemas.get(name)
        if schema is None:
            failures.append(f"{path.name}: no matching schema")
            continue
        try:
            instance = load_json(path)
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name}: invalid JSON: {exc}")
            continue

        validator = Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
        for error in errors:
            failures.append(f"{path.name}: {error.json_path}: {error.message}")

    if not OPENAPI.exists():
        failures.append("contracts/openapi.yaml: missing")
    else:
        try:
            spec = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            failures.append(f"openapi.yaml: invalid YAML: {exc}")
            spec = None

        if isinstance(spec, dict):
            if spec.get("openapi") != "3.1.0":
                failures.append("openapi.yaml: expected openapi: 3.1.0")
            paths = spec.get("paths", {})
            for required in ("/healthz", "/documents", "/search", "/ask"):
                if required not in paths:
                    failures.append(f"openapi.yaml: missing path {required}")
        elif spec is not None:
            failures.append("openapi.yaml: top-level value must be a mapping")

        for ref in re.findall(r"\$ref:\s*'?(\./schemas/[^'\s]+)'?", OPENAPI.read_text(encoding="utf-8")):
            if not (OPENAPI.parent / ref).resolve().exists():
                failures.append(f"openapi.yaml: missing external ref {ref}")

    if failures:
        print("contract check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(
        f"contracts OK: {len(schemas)} schemas, "
        f"{len(example_paths)} examples, OpenAPI 3.1.0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
