#!/usr/bin/env bash
set -euo pipefail

coh_install_system=0
coh_skip_baseline=0
for coh_argument in "$@"; do
  case "$coh_argument" in
    --install-system) coh_install_system=1 ;;
    --skip-baseline) coh_skip_baseline=1 ;;
    --help|-h)
      cat <<'HELP'
Usage: bash scripts/codex/setup.sh [--install-system] [--skip-baseline]
Prepare the Python environment and exact historical test baseline.
--install-system  Install missing Debian/Ubuntu developer packages using apt.
--skip-baseline   Deliberately omit baseline preparation; exits 2 when required.
Existing checkouts are verified and preserved, never reset or cleaned.
COH_CODEX_CACHE_DIR selects the cache; ARMPORT_SERVER_BASELINE_ROOT selects an
existing baseline or a new destination. Proxy and credential settings are retained.
HELP
      exit 0 ;;
    *) printf 'Unknown option: %s\n' "$coh_argument" >&2; exit 2 ;;
  esac
done

if (( coh_install_system )); then
  command -v apt-get >/dev/null && command -v dpkg-query >/dev/null || {
    printf '%s\n' '--install-system requires a Debian/Ubuntu apt environment.' >&2; exit 2;
  }
  coh_packages=(python3 python3-venv git gh curl cmake ninja-build build-essential clang
    openjdk-17-jdk-headless imagemagick pkg-config unzip xz-utils ca-certificates ripgrep)
  coh_missing=()
  for coh_package in "${coh_packages[@]}"; do
    [[ "$(dpkg-query -W -f='${Status}' "$coh_package" 2>/dev/null || true)" == 'install ok installed' ]] || coh_missing+=("$coh_package")
  done
  if (( ${#coh_missing[@]} )); then
    coh_privilege=()
    if [[ "$(id -u)" != 0 ]]; then
      command -v sudo >/dev/null && sudo -n true || {
        printf '%s\n' 'Installing system dependencies needs root or passwordless sudo in the setup environment.' >&2; exit 2;
      }
      coh_privilege=(sudo -n)
    fi
    "${coh_privilege[@]}" apt-get update
    "${coh_privilege[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${coh_missing[@]}"
  fi
fi

source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
coh_missing=()
for coh_tool in "${COH_CODEX_REQUIRED_TOOLS[@]}"; do
  command -v "$coh_tool" >/dev/null || coh_missing+=("$coh_tool")
done
if (( ${#coh_missing[@]} )); then
  printf 'Missing developer tools: %s\nRun setup.sh --install-system, or install equivalent tools in this environment.\n' "${coh_missing[*]}" >&2
  exit 2
fi

if [[ -e "$COH_CODEX_VENV" || -L "$COH_CODEX_VENV" ]]; then
  if [[ -L "$COH_CODEX_VENV" || ! -f "$COH_CODEX_VENV/pyvenv.cfg" || ! -x "$COH_CODEX_VENV/bin/python" ]]; then
    printf 'Existing venv path is not a usable managed Python environment; preserved: %s\n' "$COH_CODEX_VENV" >&2
    exit 2
  fi
else
  mkdir -p -- "$COH_CODEX_CACHE_DIR"
  "$COH_CODEX_SYSTEM_PYTHON" -m venv "$COH_CODEX_VENV"
fi
coh_activate
coh_installed_pillow="$("$COH_CODEX_PYTHON" -c 'from importlib.metadata import version; print(version("Pillow"))' 2>/dev/null || true)"
if [[ "$coh_installed_pillow" != "$COH_CODEX_PILLOW_VERSION" ]]; then
  "$COH_CODEX_PYTHON" -m pip install --disable-pip-version-check "pillow==$COH_CODEX_PILLOW_VERSION"
fi
"$COH_CODEX_PYTHON" -c 'from PIL import Image; print("Pillow import: OK")'

coh_setup_tmp=''
trap 'if [[ -n "$coh_setup_tmp" && -d "$coh_setup_tmp" ]]; then rm -rf -- "$coh_setup_tmp"; fi' EXIT
coh_git() {
  GIT_LFS_SKIP_SMUDGE=1 GIT_TERMINAL_PROMPT=0 git \
    -c filter.lfs.smudge= -c filter.lfs.process= -c filter.lfs.required=false "$@"
}

if [[ -n "$COH_CODEX_BASELINE_COMMIT" ]]; then
  if (( coh_skip_baseline )); then
    printf '%s\n' 'PARTIAL SETUP: historical baseline intentionally omitted. Full ArmPort tests are not ready.' >&2
    exit 2
  fi
  if [[ -e "$COH_CODEX_BASELINE" || -L "$COH_CODEX_BASELINE" ]]; then
    coh_validate_baseline
  else
    mkdir -p -- "$(dirname -- "$COH_CODEX_BASELINE")"
    coh_setup_tmp="$(mktemp -d "$(dirname -- "$COH_CODEX_BASELINE")/.coh-baseline.XXXXXX")"
    coh_git -C "$coh_setup_tmp" init -q
    coh_git -C "$coh_setup_tmp" remote add origin https://github.com/Russianranger/coh-android.git
    if git -C "$COH_CODEX_ROOT" cat-file -e "$COH_CODEX_BASELINE_COMMIT^{commit}" 2>/dev/null; then
      coh_git -C "$coh_setup_tmp" fetch --depth=1 --no-tags "$COH_CODEX_ROOT" "$COH_CODEX_BASELINE_COMMIT"
    else
      coh_git -C "$coh_setup_tmp" config remote.origin.promisor true
      coh_git -C "$coh_setup_tmp" config remote.origin.partialclonefilter blob:none
      coh_git -C "$coh_setup_tmp" fetch --depth=1 --no-tags --filter=blob:none origin "$COH_CODEX_BASELINE_COMMIT"
    fi
    # Match the historical validator inputs retained by armport-build.yml.
    coh_git -C "$coh_setup_tmp" sparse-checkout set --no-cone --stdin <<'PATTERNS'
/.gitignore
/tools/
/android/guest/
/database/
/patches/
/upstream-lock.json
/docs/source-manifest.json
/docs/android-evidence/client-map-startup-0.13.32-publication.json
/docs/android-evidence/mapserver-progress-package-36630872719.json
/upstream/ouroboros/
PATTERNS
    coh_git -C "$coh_setup_tmp" checkout --detach "$COH_CODEX_BASELINE_COMMIT"
    coh_validate_baseline "$coh_setup_tmp"
    mv -T --no-clobber -- "$coh_setup_tmp" "$COH_CODEX_BASELINE"
    if [[ -d "$coh_setup_tmp" ]]; then
      printf 'Baseline destination appeared during setup; it was preserved: %s\n' "$COH_CODEX_BASELINE" >&2
      exit 2
    fi
    coh_setup_tmp=''
    coh_validate_baseline
  fi
  printf 'Historical baseline: %s\n' "$COH_CODEX_BASELINE_COMMIT"
fi
printf 'Host dependencies prepared. Run bash scripts/codex/doctor.sh next.\nCache: %s\n' "$COH_CODEX_CACHE_DIR"
