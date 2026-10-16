#!/usr/bin/env bash
# Print the version of every tool the checks use into reports/versions.txt.
# A tool that is missing or whose version command fails is a FAIL, not a version string.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
invalidate versions || { echo "versions: could not clear the earlier result" >&2; exit 2; }
bad=""
# ver <label> <filter-command...>: run the command, keep the first matching line
ver() {
  local label=$1; shift
  local out; out="$("$@" 2>&1)"; local rc=$?
  if [ $rc != 0 ] || [ -z "$out" ]; then bad="$bad $label"; out="UNAVAILABLE (status $rc)"; fi
  printf '%-15s %s\n' "$label:" "$(printf '%s\n' "$out" | head -1)"
}
netgen_v() {
  local out rc
  out="$(netgen -batch quit 2>&1)"; rc=$?
  [ $rc = 0 ] || { printf '%s\n' "$out" | head -1; return $rc; }
  printf '%s\n' "$out" | grep -a 'Netgen' | head -1 | grep -a .
}
{
  ver Magic magic --version
  ver Netgen netgen_v
  ver KLayout klayout -v
  ver OpenSTA sta -version
  ver "Icarus Verilog" iverilog -V
  ver Python python3 --version
} > "$REPORTS/versions.txt"
cat "$REPORTS/versions.txt"
if [ -n "$bad" ]; then result versions FAIL "version command failed for:$bad"; exit 1; fi
result versions PASS "$(tr -s ' ' < "$REPORTS/versions.txt" | tr '\n' ';')"
