#!/usr/bin/env bash
# Read the current commit's runs or one explicit run. Never dispatch a workflow.
set -euo pipefail
if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
  printf '%s\n' 'Usage: bash scripts/codex/ci-status.sh [RUN_ID]' \
    'With no ID, lists runs for the current exact commit. All calls are read-only.'
  exit 0
fi
if (( $# > 1 )) || { (( $# == 1 )) && [[ ! "$1" =~ ^[1-9][0-9]*$ ]]; }; then
  printf '%s\n' 'Expected one numeric run ID, or no arguments.' >&2
  exit 2
fi
for coh_tool in git gh timeout; do
  command -v "$coh_tool" >/dev/null 2>&1 || { printf 'MISSING: %s\n' "$coh_tool" >&2; exit 2; }
done
coh_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd -- "$coh_root"
if (( $# )); then
  GH_DEBUG= GH_PROMPT_DISABLED=1 timeout 30 gh run view "$1" --repo Russianranger/coh-android \
    --json databaseId,workflowName,headSha,status,conclusion,url
else
  coh_sha=$(git rev-parse HEAD)
  printf 'Runs for exact commit %s\n' "$coh_sha"
  GH_DEBUG= GH_PROMPT_DISABLED=1 timeout 30 gh run list --repo Russianranger/coh-android \
    --commit "$coh_sha" --limit 10 --json databaseId,workflowName,headSha,status,conclusion,url
fi
