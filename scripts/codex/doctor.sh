#!/usr/bin/env bash
# Read-only checks; --github adds bounded GET requests, never dispatches a run.
set -euo pipefail

coh_check_github=0
case "${1:---local}" in
  --local) ;;
  --github) coh_check_github=1 ;;
  --help|-h)
    printf '%s\n' 'Usage: bash scripts/codex/doctor.sh [--local|--github]' \
      'Exit 0: requested checks passed; 2: local prerequisite missing; 3: GitHub read unavailable.'
    exit 0 ;;
  *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
esac
if (( $# > 1 )); then printf '%s\n' 'Pass only one doctor mode.' >&2; exit 2; fi
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"
coh_activate
cd -- "$COH_CODEX_ROOT"
coh_local_missing=0
coh_remote_missing=0

printf 'Repository: %s\n' "$COH_CODEX_ROOT"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf 'Branch: %s\n' "$(git branch --show-current)"
  printf 'HEAD: %s\n' "$(git rev-parse HEAD)"
  printf '%s\n' 'Working-tree changes (preserved):'
  git status --short
else
  printf '%s\n' 'MISSING: a Git checkout, including history required by the tests.'
  coh_local_missing=1
fi
printf 'Host architecture: %s\n' "$(uname -m)"
printf 'Compiler limit: %s\n' "$CMAKE_BUILD_PARALLEL_LEVEL"
df -h "$COH_CODEX_ROOT"

for coh_tool in git cc c++ cmake ninja java javac convert identify; do
  if ! command -v "$coh_tool" >/dev/null 2>&1; then
    printf 'MISSING: %s\n' "$coh_tool"
    coh_local_missing=1
    continue
  fi
  coh_version_arg=--version
  case "$coh_tool" in java|javac|convert|identify) coh_version_arg=-version ;; esac
  if coh_version=$("$coh_tool" "$coh_version_arg" 2>&1); then
    printf 'OK: %s — %s\n' "$coh_tool" "${coh_version%%$'\n'*}"
  else
    printf 'UNUSABLE: %s failed its version check.\n' "$coh_tool"
    coh_local_missing=1
  fi
done
if "$COH_CODEX_PYTHON" - "$COH_CODEX_PILLOW_VERSION" <<'PY'
import sys
try:
    import PIL
    if PIL.__version__ != sys.argv[1]:
        raise RuntimeError(f"Pillow {PIL.__version__}; expected {sys.argv[1]}")
    print(f"OK: Python {sys.version.split()[0]}, Pillow {PIL.__version__}")
except (ImportError, RuntimeError) as error:
    print(f"MISSING: {error}")
    raise SystemExit(2)
PY
then :; else coh_local_missing=1; fi

if [[ -n "$COH_CODEX_BASELINE_COMMIT" ]]; then
  if coh_validate_baseline; then
    printf 'OK: clean historical baseline %s\n' "$COH_CODEX_BASELINE_COMMIT"
  else
    coh_local_missing=1
  fi
else
  printf '%s\n' 'Baseline: no server baseline pin in this checkout.'
fi

if (( coh_check_github )); then
  if command -v curl >/dev/null 2>&1; then
    if coh_http=$(curl --disable --silent --show-error --connect-timeout 8 --max-time 20 \
        --output /dev/null --write-out '%{http_code}' https://api.github.com); then
      case "$coh_http" in
        2??) printf 'OK: api.github.com transport, HTTP %s\n' "$coh_http" ;;
        *) printf 'NOTE: public API probe returned HTTP %s; authenticated reads below determine GitHub usability.\n' "$coh_http" ;;
      esac
    else
      printf '%s\n' 'UNAVAILABLE: api.github.com transport; inspect the reported proxy/DNS/TLS error.'
      coh_remote_missing=1
    fi
  else
    printf '%s\n' 'MISSING: curl for the independent network check.'
    coh_remote_missing=1
  fi
  if command -v gh >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
    for coh_endpoint in repos/Russianranger/coh-android repos/Russianranger/coh-android/actions/workflows; do
      if GH_DEBUG= GH_PROMPT_DISABLED=1 timeout 30 gh api "$coh_endpoint" >/dev/null; then
        printf 'OK: GitHub API read %s\n' "$coh_endpoint"
      else
        printf 'UNAVAILABLE: GitHub API read %s; inspect the exact error above.\n' "$coh_endpoint"
        coh_remote_missing=1
      fi
    done
  else
    printf '%s\n' 'MISSING: gh and/or timeout for bounded GitHub API reads.'
    coh_remote_missing=1
  fi
  printf '%s\n' 'Workflow dispatch, Git push, signing, and artifact downloads are not exercised by this read-only check.'
fi
if (( coh_local_missing )); then
  printf '%s\n' 'LOCAL SETUP INCOMPLETE: run setup.sh and resolve the listed prerequisites.'
  exit 2
fi
if (( coh_remote_missing )); then
  printf '%s\n' 'GITHUB READS UNAVAILABLE: local work can continue; correct the reported access problem.'
  exit 3
fi
printf '%s\n' 'Requested preflight checks passed. No game tests or device qualification were run.'
