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
    receipt = audit_source_tricks(args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": receipt["passed"], "source_files_verified": receipt["source_files_verified"],
                      "primary_sources_verified": len(receipt["primary_source_files_verified"]),
                      "git_tree_sha": receipt["git_tree_sha"]}))


if __name__ == "__main__":
    main()
