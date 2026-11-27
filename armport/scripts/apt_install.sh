#!/bin/bash
# apt_install.sh <package...>: apt-get update and install for a CI step, with fallback mirrors.
#
# 2026-11-11: GitHub's ARM64 runners could not resolve Canonical's ports.ubuntu.com for
# hours (builds 43038600688, 43040165696, 43045034484, 43049997166 and 43054851770 all
# stopped in "ArmPort test apt", each after eight minutes of failed look-ups). When an
# Ubuntu archive host named in the runner's apt sources does not resolve, or the install
# fails, this points those sources at an independent mirror and tries again.
#
# A mirror serves Canonical's own index files. apt checks their signature against the
# Ubuntu archive key already in the runner image, so a mirror cannot substitute a package;
# at worst it offers an older index that is still signed. The runner's sources are put
# back before the script returns.
set -u
[ $# -gt 0 ] || { echo "usage: apt_install.sh <package...>" >&2; exit 2; }

root=${APT_INSTALL_ROOT:-/etc/apt}
sudo=${APT_INSTALL_SUDO-sudo}
ports_mirrors="https://mirrors.mit.edu/ubuntu-ports https://mirrors.ocf.berkeley.edu/ubuntu-ports https://ftp.tu-chemnitz.de/pub/linux/ubuntu-ports"
archive_mirrors="https://mirrors.mit.edu/ubuntu https://mirrors.ocf.berkeley.edu/ubuntu https://mirrors.kernel.org/ubuntu"
ports_pattern='https\?://\(azure\.\)\?ports\.ubuntu\.com/ubuntu-ports'
archive_pattern='https\?://\(azure\.archive\|archive\|security\)\.ubuntu\.com/ubuntu'

attempt() {
  $sudo apt-get update -qq -o Acquire::Retries=2 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 &&
    $sudo apt-get install -y --no-install-recommends -o Acquire::Retries=2 \
      -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 "$@"
}
resolves() { timeout 20 getent hosts "$1" > /dev/null 2>&1; }
host_of() { echo "$1" | sed 's#^[a-z]*://##; s#/.*##'; }

# The source files that name an Ubuntu archive host, and those hosts.
files=$(grep -rls -e "$ports_pattern" -e "$archive_pattern" \
  "$root/sources.list" "$root/sources.list.d" "$root/apt-mirrors.txt" 2>/dev/null | sort -u)
hosts=$(for file in $files; do grep -o -e "$ports_pattern" -e "$archive_pattern" "$file"; done |
  while read -r url; do host_of "$url"; done | sort -u)

unresolved=''
for host in $hosts; do
  resolves "$host" || unresolved="$unresolved $host"
done
if [ -z "$unresolved" ]; then
  attempt "$@" && exit 0
  echo "apt_install: the runner's own archive failed; trying mirrors" >&2
else
  echo "apt_install: cannot resolve$unresolved; trying mirrors" >&2
fi
[ -n "$files" ] || { echo "apt_install: no Ubuntu archive source found under $root" >&2; exit 100; }

saved=$(mktemp -d)
index=0
for file in $files; do
  index=$((index + 1))
  cp -p "$file" "$saved/$index"
done
restore() {
  index=0
  for file in $files; do
    index=$((index + 1))
    $sudo cp -p "$saved/$index" "$file"
  done
}
trap 'restore; rm -rf "$saved"' EXIT

status=100
count=$(echo "$ports_mirrors" | wc -w)
position=0
while [ $position -lt "$count" ]; do
  position=$((position + 1))
  ports=$(echo "$ports_mirrors" | cut -d' ' -f$position)
  archive=$(echo "$archive_mirrors" | cut -d' ' -f$position)
  resolves "$(host_of "$ports")" || { echo "apt_install: mirror $(host_of "$ports") does not resolve" >&2; continue; }
  restore
  for file in $files; do
    $sudo sed -i -e "s#$ports_pattern#$ports#g" -e "s#$archive_pattern#$archive#g" "$file"
  done
  attempt "$@"
  status=$?
  if [ $status -eq 0 ]; then
    echo "::notice title=apt mirror::Packages came from $(host_of "$ports") (signed by the Ubuntu archive key); the runner's own archive failed:${unresolved:- install error}"
    exit 0
  fi
  echo "apt_install: mirror $(host_of "$ports") failed with $status" >&2
done
exit $status
