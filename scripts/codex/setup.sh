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
--install-system  Optionally install genuinely missing tools using Debian/Ubuntu apt.
--skip-baseline   Deliberately omit baseline preparation; exits 2 when required.
Tools already on PATH and an existing managed venv are reused without sudo/apt.
Existing checkouts are verified and preserved, never reset or cleaned.
COH_CODEX_CACHE_DIR selects the cache; ARMPORT_SERVER_BASELINE_ROOT selects an
existing baseline or a new destination. Proxy and credential settings are retained.
HELP
      exit 0 ;;
    *) printf 'Unknown option: %s\n' "$coh_argument" >&2; exit 2 ;;
  esac
done

coh_install_packages() {
  (( $# )) || return 0
  if (( ! coh_install_system )); then
    printf '%s\n' 'Prepare the missing tools in the Cloud environment, then rerun setup.sh.' \
      'Use --install-system only when Debian/Ubuntu package installation is available.' >&2
    return 2
  fi
  command -v apt-get >/dev/null && command -v apt-cache >/dev/null || {
    printf '%s\n' 'Missing tools require environment preparation; apt is unavailable.' >&2
    return 2
  }
  local -a coh_privilege=()
  local coh_package coh_policy coh_field coh_value coh_rest coh_candidate
  if [[ "$(id -u)" != 0 ]]; then
    command -v sudo >/dev/null && sudo -n true || {
      printf '%s\n' 'Missing tools cannot be installed with apt: root or passwordless sudo is unavailable.' \
        'Prepare those tools through environment setup in a user-writable location, preserve their PATH, and rerun setup.sh.' >&2
      return 2
    }
    coh_privilege=(sudo -n)
  fi
  "${coh_privilege[@]}" apt-get update
  for coh_package in "$@"; do
    coh_policy="$(LC_ALL=C apt-cache policy "$coh_package")" || return "$?"
    coh_candidate=''
    while read -r coh_field coh_value coh_rest; do
      [[ "$coh_field" != 'Candidate:' ]] || coh_candidate="$coh_value"
    done <<< "$coh_policy"
    if [[ -z "$coh_candidate" || "$coh_candidate" == '(none)' ]]; then
      printf 'Package unavailable in configured repositories: %s\n' "$coh_package" >&2
      if [[ "$coh_package" == openjdk-17-jdk-headless ]]; then
        printf '%s\n' 'Prepare JDK 17 through environment setup and persist its PATH/JAVA_HOME. No alternate Java major or repository will be selected.' >&2
      else
        printf '%s\n' 'Prepare the equivalent tool through environment setup, then rerun setup.sh.' >&2
      fi
      return 2
    fi
  done
  "${coh_privilege[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@"
}

# Python is needed to read the repository's pins and configured cache paths.
if ! command -v python3 >/dev/null; then
  printf '%s\n' 'Missing developer tools: python3' >&2
  coh_install_packages python3 python3-venv
fi

source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

coh_create_venv=1
if [[ -e "$COH_CODEX_VENV" || -L "$COH_CODEX_VENV" ]]; then
  if [[ -L "$COH_CODEX_VENV" || ! -f "$COH_CODEX_VENV/pyvenv.cfg" || ! -x "$COH_CODEX_VENV/bin/python" ]]; then
    printf 'Existing venv path is not a usable managed Python environment; preserved: %s\n' "$COH_CODEX_VENV" >&2
    exit 2
  fi
  coh_create_venv=0
fi

# Installed package names do not establish tool availability: Cloud runtimes
# may supply tools outside apt, including user-managed JDKs and Python.
coh_missing=()
coh_packages=()
for coh_tool in "${COH_CODEX_REQUIRED_TOOLS[@]}"; do
  command -v "$coh_tool" >/dev/null && continue
  coh_missing+=("$coh_tool")
  case "$coh_tool" in
    ninja) coh_package=ninja-build ;;
    cc|c++) coh_package=build-essential ;;
    java|javac) coh_package=openjdk-17-jdk-headless ;;
    convert|identify) coh_package=imagemagick ;;
    xz) coh_package=xz-utils ;;
    rg) coh_package=ripgrep ;;
    *) coh_package="$coh_tool" ;;
  esac
  [[ " ${coh_packages[*]} " == *" $coh_package "* ]] || coh_packages+=("$coh_package")
done
if (( coh_create_venv )) && ! "$COH_CODEX_SYSTEM_PYTHON" -c 'import venv, ensurepip' >/dev/null 2>&1; then
  coh_missing+=('Python venv/ensurepip')
  coh_packages+=(python3-venv)
fi
if (( ${#coh_missing[@]} )); then
  printf 'Missing developer tools: %s\n' "${coh_missing[*]}" >&2
  coh_install_packages "${coh_packages[@]}"
  for coh_tool in "${COH_CODEX_REQUIRED_TOOLS[@]}"; do
    command -v "$coh_tool" >/dev/null || {
      printf 'Tool still missing from PATH after installation: %s\n' "$coh_tool" >&2
      exit 2
    }
  done
fi

if (( coh_create_venv )); then
  if ! "$COH_CODEX_SYSTEM_PYTHON" -c 'import venv, ensurepip' >/dev/null 2>&1; then
    printf '%s\n' 'Selected Python still lacks venv/ensurepip. Prepare a Python with venv support in this environment.' >&2
    exit 2
  fi
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
