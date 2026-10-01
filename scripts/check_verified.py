#!/usr/bin/env python3
"""Guard against silently losing live-verified response documentation.

Every response that has been checked against the live Netmera API carries an
`x-netmera-verified` marker. Those markers are the only record that the response
body was confirmed rather than copied from the Developer Guide, and a spec
regeneration from the guide would drop them without any visible error.

This script compares the working copy of the spec against the version on the
base branch and fails if a marker disappeared, or if a marked response lost the
response content it used to document.

Usage:
    python3 scripts/check_verified.py CURRENT.yaml BASELINE.yaml
    python3 scripts/check_verified.py CURRENT.yaml          # nothing to compare, passes

Exit codes:
    0  no regression
    1  a verified response was dropped or weakened
    2  a file could not be read or parsed
"""

import sys
import yaml

METHODS = ("get", "post", "put", "patch", "delete")

# Verified responses removed on purpose. Error responses are not documented on
# operations; the observed failures are recorded in README under
# "Observed endpoint errors".
RETIRED = {
    ("sendNotification", "400"),
    ("sendEmailAndSms", "400"),
}


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError:
        return None
    except yaml.YAMLError as exc:
        print(f"::error::{path} is not valid YAML: {exc}")
        sys.exit(2)


def verified_responses(spec):
    """Map (operationId, status) -> whether the response carried a body schema."""
    found = {}
    for path, item in (spec.get("paths") or {}).items():
        for method, op in item.items():
            if method not in METHODS:
                continue
            op_id = op.get("operationId") or f"{method.upper()} {path}"
            for status, resp in (op.get("responses") or {}).items():
                if not isinstance(resp, dict):
                    continue
                if resp.get("x-netmera-verified"):
                    found[(op_id, str(status))] = "content" in resp
    return found


def main():
    if len(sys.argv) < 2:
        print("::error::usage: check_verified.py CURRENT.yaml [BASELINE.yaml]")
        sys.exit(2)

    current = load(sys.argv[1])
    if current is None:
        print(f"::error::{sys.argv[1]} not found")
        sys.exit(2)

    now = verified_responses(current)
    print(f"verified responses in this revision: {len(now)}")

    if len(sys.argv) < 3:
        print("no baseline supplied, nothing to compare")
        return

    baseline = load(sys.argv[2])
    if baseline is None:
        print("no baseline found on the base branch, nothing to compare")
        return

    before = verified_responses(baseline)
    print(f"verified responses on the base branch:  {len(before)}")

    failures = []
    for key, had_content in before.items():
        op_id, status = key
        if key in RETIRED and key not in now:
            print(f"{op_id} ({status}) retired on purpose, see README.")
            continue
        if key not in now:
            failures.append(
                f"{op_id} ({status}) lost its x-netmera-verified marker. "
                "This response was confirmed against the live API; do not drop it "
                "without re-verifying."
            )
        elif had_content and not now[key]:
            failures.append(
                f"{op_id} ({status}) is still marked verified but no longer "
                "documents a response body."
            )

    for line in failures:
        print(f"::error::{line}")

    gained = set(now) - set(before)
    if gained:
        print(f"newly verified: {', '.join(sorted(f'{o} ({s})' for o, s in gained))}")

    if failures:
        print(f"\n{len(failures)} verified response(s) regressed.")
        sys.exit(1)

    print("no verified response was dropped.")


if __name__ == "__main__":
    main()
