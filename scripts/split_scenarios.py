#!/usr/bin/env python3
"""Generate one OpenAPI file per request example of selected operations.

GitBook opens an OpenAPI block with the first request example of the operation,
and a block cannot choose another one. To give each scenario its own guide page,
this script writes a small spec per example: the full operation, with only that
example kept, plus the components it references. Each generated file is
registered in GitBook as its own spec and bound to one scenario page.

The generated files are derived data. Regenerate them whenever
netmera-rest-api.yaml changes and commit the result; never edit them by hand.

Usage:
    python3 scripts/split_scenarios.py                      # all scenarios
    python3 scripts/split_scenarios.py sendBulkNotification/targetSingleTag
    python3 scripts/split_scenarios.py --out /tmp/scenarios # other output dir
    python3 scripts/split_scenarios.py --check              # fail if files are stale
"""

import argparse
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "netmera-rest-api.yaml"
OPERATIONS = ["sendBulkNotification", "sendNotification", "createNotificationDefinition"]


def collect_refs(node, components, needed):
    """Record every component reachable from node through $ref."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/components/"):
                _, _, section, name = value.split("/", 3)
                if (section, name) not in needed:
                    needed.add((section, name))
                    collect_refs(components[section][name], components, needed)
            else:
                collect_refs(value, components, needed)
    elif isinstance(node, list):
        for item in node:
            collect_refs(item, components, needed)


def find_operation(spec, operation_id):
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if isinstance(operation, dict) and operation.get("operationId") == operation_id:
                return path, method, operation
    raise KeyError(operation_id)


def build(spec, operation_id, example_key):
    path, method, operation = find_operation(spec, operation_id)
    operation = yaml.safe_load(yaml.safe_dump(operation))  # deep copy
    content = operation["requestBody"]["content"]["application/json"]
    examples = content["examples"]
    content["examples"] = {example_key: examples[example_key]}

    components = spec["components"]
    needed = set()
    collect_refs(operation, components, needed)
    out_components = {"securitySchemes": components["securitySchemes"]}
    for section, name in sorted(needed):
        out_components.setdefault(section, {})[name] = components[section][name]

    tags = [t for t in spec.get("tags", []) if t["name"] in operation.get("tags", [])]
    return {
        "openapi": spec["openapi"],
        "info": {"title": spec["info"]["title"], "version": spec["info"]["version"]},
        "servers": spec["servers"],
        "security": spec["security"],
        "tags": tags,
        "paths": {path: {method: operation}},
        "components": out_components,
    }


def render(doc):
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)


def scenarios(spec):
    for operation_id in OPERATIONS:
        _, _, operation = find_operation(spec, operation_id)
        for key in operation["requestBody"]["content"]["application/json"]["examples"]:
            yield operation_id, key


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("only", nargs="*", help="operationId/exampleKey to generate; default is all")
    parser.add_argument("--out", default=str(ROOT / "scenarios"))
    parser.add_argument("--check", action="store_true", help="exit 1 when a generated file is missing or stale")
    args = parser.parse_args()

    spec = yaml.safe_load(SOURCE.read_text())
    wanted = set(args.only)
    out_dir = pathlib.Path(args.out)
    stale = []
    count = 0
    for operation_id, key in scenarios(spec):
        if wanted and f"{operation_id}/{key}" not in wanted:
            continue
        target = out_dir / operation_id / f"{key}.yaml"
        text = render(build(spec, operation_id, key))
        count += 1
        if args.check:
            if not target.exists() or target.read_text() != text:
                stale.append(str(target.relative_to(out_dir)))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    if args.check:
        if stale:
            print("stale or missing scenario files:", *stale, sep="\n  ")
            return 1
        print(f"{count} scenario files up to date")
        return 0
    print(f"wrote {count} scenario files to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
