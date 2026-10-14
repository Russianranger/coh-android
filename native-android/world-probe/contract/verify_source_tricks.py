#!/usr/bin/env python3
"""Fail-closed Phase9 material lookup audit over every original source trick blob."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from material_reference import audit_source_tricks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        receipt = audit_source_tricks(args.repo_root)
    except Exception as error:
        # Keep a bounded machine-readable failure artifact even when the audit
        # stops before asset generation. A failure receipt never qualifies a build.
        pins = json.loads(Path(__file__).with_name("source-material-pins.json").read_text())
        failure = {"passed": False, "kind": "complete immutable original trick declaration audit",
                   "stage": getattr(error, "audit_stage", "source-trick-resolution"),
                   "assets_prepared_by_this_audit": False,
                   "source_resolution_qualified": False,
                   "expected_git_tree_sha": pins["tricks_tree"]["git_tree_sha"],
                   "expected_source_file_count": pins["tricks_tree"]["file_count"],
                   "error_type": type(error).__name__, "error": str(error)[:2048]}
        if getattr(error, "filename", None):
            failure["source_file"] = str(error.filename)[:1024]
        if getattr(error, "audit_context", None):
            encoded = json.dumps(error.audit_context)
            failure["source_resolution_context"] = error.audit_context if len(encoded) <= 8192 else encoded[:8192]
        args.output.write_text(json.dumps(failure, indent=2) + "\n")
        raise
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": receipt["passed"], "source_files_verified": receipt["source_files_verified"],
                      "primary_sources_verified": len(receipt["primary_source_files_verified"]),
                      "git_tree_sha": receipt["git_tree_sha"]}))


if __name__ == "__main__":
    main()
