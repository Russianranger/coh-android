#!/usr/bin/env bash
# Local validation only; native CI and Thor qualification are separate stages.
set -euo pipefail
coh_mode=${1:---armport}
case "$coh_mode" in
  --armport|--lifecycle|--all|--foundation) ;;
  --help|-h)
    printf '%s\n' 'Usage: bash scripts/codex/check.sh [--armport|--lifecycle|--all|--foundation]' \
      '--armport (default): the existing ArmPort Python suite' \
      '--lifecycle: saved-map startup, zoning, and monorail suites' \
      '--all: ArmPort and lifecycle suites, sequentially' \
      '--foundation: disposable-fixture tests of these setup scripts only'
    exit 0 ;;
  *) printf 'Unknown option: %s\n' "$coh_mode" >&2; exit 2 ;;
esac
if (( $# > 1 )); then printf '%s\n' 'Pass only one check mode.' >&2; exit 2; fi
coh_script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ "$coh_mode" == --foundation ]]; then
  exec python3 -m unittest discover -s "$coh_script_dir/tests" -p 'test_*.py' -v
fi
source "$coh_script_dir/common.sh"
coh_activate
cd -- "$COH_CODEX_ROOT"
bash "$coh_script_dir/doctor.sh" --local
git diff --check
coh_run_suite() {
  # Same unittest discovery as CI, with an explicit failure for empty discovery.
  "$COH_CODEX_PYTHON" - "$1" "$2" <<'PY'
import sys
import unittest
suite = unittest.defaultTestLoader.discover(sys.argv[1], pattern=sys.argv[2])
if not suite.countTestCases():
    print(f"MISSING: no tests discovered in {sys.argv[1]} for {sys.argv[2]}", file=sys.stderr)
    raise SystemExit(2)
result = unittest.TextTestRunner().run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
}
if [[ "$coh_mode" == --armport || "$coh_mode" == --all ]]; then
  [[ -d armport/tests ]] || { printf '%s\n' 'MISSING: armport/tests in this checkout.' >&2; exit 2; }
  coh_run_suite armport/tests 'test_*.py'
fi
if [[ "$coh_mode" == --lifecycle || "$coh_mode" == --all ]]; then
  for coh_pattern in test_saved_map_startup.py test_character_zoning.py test_character_monorail.py; do
    [[ -f "tools/android/interactive/$coh_pattern" ]] || {
      printf 'MISSING: tools/android/interactive/%s\n' "$coh_pattern" >&2; exit 2;
    }
    coh_run_suite tools/android/interactive "$coh_pattern"
  done
fi
printf '%s\n' 'Selected local tests passed. Native CI, APK approval, and Thor testing remain separate.'
