#!/usr/bin/env bash
# Shared read-only configuration. Source this file from the other Cloud helpers.

COH_CODEX_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)" || return 1
COH_CODEX_SYSTEM_PYTHON="$(command -v python3)" || {
  printf '%s\n' 'Missing python3. Run setup.sh --install-system in the Cloud setup environment.' >&2
  return 1
}

# Read literals, without importing project modules or running project code.
COH_CODEX_BASELINE_COMMIT="$("$COH_CODEX_SYSTEM_PYTHON" - "$COH_CODEX_ROOT" <<'PY'
import ast
from pathlib import Path
import re
import sys
path = Path(sys.argv[1]) / 'armport/app/server_package.py'
if path.is_file():
    values = [ast.literal_eval(node.value) for node in ast.parse(path.read_text()).body
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'BASELINE_COMMIT'
                      for target in node.targets)]
    if len(values) != 1 or not isinstance(values[0], str) or not re.fullmatch(r'[0-9a-f]{40}', values[0]):
        sys.exit('Expected one literal 40-character BASELINE_COMMIT in server_package.py')
    print(values[0])
PY
)" || return 1
COH_CODEX_PILLOW_VERSION="$("$COH_CODEX_SYSTEM_PYTHON" - "$COH_CODEX_ROOT" <<'PY'
from pathlib import Path
import re
import sys
text = (Path(sys.argv[1]) / '.github/workflows/armport-build.yml').read_text()
pins = set(re.findall(r'\bpillow==([0-9]+(?:\.[0-9]+)+)\b', text, flags=re.I))
if len(pins) != 1:
    sys.exit('Expected one Pillow version pin in armport-build.yml')
print(pins.pop())
PY
)" || return 1

COH_CODEX_CACHE_DIR="${COH_CODEX_CACHE_DIR:-${XDG_CACHE_HOME:-${HOME:?HOME is required}/.cache}/coh-codex}"
COH_CODEX_CACHE_DIR="$("$COH_CODEX_SYSTEM_PYTHON" -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$COH_CODEX_CACHE_DIR")" || return 1
COH_CODEX_VENV="$COH_CODEX_CACHE_DIR/venv"
COH_CODEX_BASELINE="${ARMPORT_SERVER_BASELINE_ROOT:-}"
if [[ -n "$COH_CODEX_BASELINE_COMMIT" && -z "$COH_CODEX_BASELINE" ]]; then
  COH_CODEX_BASELINE="$COH_CODEX_CACHE_DIR/baselines/$COH_CODEX_BASELINE_COMMIT"
fi
if [[ -n "$COH_CODEX_BASELINE" ]]; then
  # abspath deliberately preserves the final symlink so validation can reject it.
  COH_CODEX_BASELINE="$("$COH_CODEX_SYSTEM_PYTHON" -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$COH_CODEX_BASELINE")" || return 1
fi
COH_CODEX_PYTHON="$COH_CODEX_SYSTEM_PYTHON"
[[ ! -x "$COH_CODEX_VENV/bin/python" ]] || COH_CODEX_PYTHON="$COH_CODEX_VENV/bin/python"
COH_CODEX_REQUIRED_TOOLS=(git python3 curl gh cmake ninja cc c++ clang java javac convert identify pkg-config unzip xz rg)

coh_validate_baseline() {
  [[ -n "$COH_CODEX_BASELINE_COMMIT" ]] || return 0
  local coh_path="${1:-$COH_CODEX_BASELINE}" coh_physical coh_top coh_head coh_dirty
  if [[ ! -d "$coh_path" || -L "$coh_path" ]]; then
    printf 'Baseline must be an existing directory, not a symlink: %s\n' "$coh_path" >&2
    return 1
  fi
  coh_physical="$(cd -- "$coh_path" && pwd -P)" || return 1
  coh_top="$(git -C "$coh_path" rev-parse --show-toplevel 2>/dev/null)" || {
    printf 'Baseline is not a Git checkout: %s\n' "$coh_path" >&2; return 1;
  }
  if [[ "$coh_top" != "$coh_physical" ]]; then
    printf 'Baseline path must be its own Git root: %s\n' "$coh_path" >&2; return 1
  fi
  coh_head="$(git -C "$coh_path" rev-parse --verify HEAD)" || return 1
  if [[ "$coh_head" != "$COH_CODEX_BASELINE_COMMIT" ]]; then
    printf 'Baseline HEAD must be %s; found %s. Existing files were preserved.\n' "$COH_CODEX_BASELINE_COMMIT" "$coh_head" >&2
    return 1
  fi
  coh_dirty="$(git -C "$coh_path" status --porcelain --untracked-files=normal)" || return 1
  if [[ -n "$coh_dirty" ]]; then
    printf 'Baseline contains modified or untracked files: %s. Preserve that work and supply a clean checkout.\n' "$coh_path" >&2
    return 1
  fi
}

coh_activate() {
  if [[ -x "$COH_CODEX_VENV/bin/python" ]]; then
    export PATH="$COH_CODEX_VENV/bin:$PATH"
    COH_CODEX_PYTHON="$COH_CODEX_VENV/bin/python"
  fi
  if [[ -n "$COH_CODEX_BASELINE_COMMIT" ]]; then
    export ARMPORT_SERVER_BASELINE_ROOT="$COH_CODEX_BASELINE"
  fi
  export CMAKE_BUILD_PARALLEL_LEVEL=2
  export PYTHONDONTWRITEBYTECODE=1
}
