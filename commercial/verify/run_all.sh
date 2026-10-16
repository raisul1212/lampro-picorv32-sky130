#!/usr/bin/env bash
# Run every check, write reports/, print a summary. Exit code 0 only if every expected result is a
# fresh PASS and every checker exited successfully.
#   - all earlier top-level reports/*.result files are removed first, so a stale PASS cannot be read;
#   - a checker that exits non-zero has its results marked FAIL, even if it wrote PASS before it crashed;
#   - a checker that exits zero but does not write a required result gets a FAIL for it;
#   - a result must be a single line, "PASS" or "PASS <facts>" (or FAIL ...).
# Set REPORTS to a new directory to keep concurrent runs apart.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/env.sh"
fail=0
if ! rm -f "$REPORTS"/*.result || ! : > "$REPORTS/summary.txt" || ls "$REPORTS"/*.result > /dev/null 2>&1; then
  echo "run_all: could not clear earlier results in $REPORTS" >&2
  echo "SOME CHECKS FAILED"; exit 2
fi
# The result names each script must produce.
stems_of() {
  case "$1" in
    versions) echo versions;;
    sim) echo "sim_8.25ns sim_4.125ns_control";;
    sta) echo "sta_ss sta_tt sta_ff";;
    transistors) echo transistors;;
    drc_magic) echo drc_magic;;
    drc_klayout) echo drc_klayout;;
    antenna_magic) echo antenna_magic;;
    lvs) echo lvs;;
    cvc) echo "cvc_8.25ns cvc_control";;
  esac
}
# A result file is valid when it is one line: PASS or FAIL, then end of line or a space and the facts.
valid_line() {
  case "$1" in
    *$'\n'*) return 1;;
    PASS|FAIL|"PASS "*|"FAIL "*) return 0;;
    *) return 1;;
  esac
}
ORDER="integrity versions transistors sim_8.25ns sim_4.125ns_control sta_ss sta_tt sta_ff drc_magic drc_klayout antenna_magic lvs cvc_8.25ns cvc_control"
# integrity
if ( cd "$PKG" && sha256sum -c SHA256SUMS > "$REPORTS/integrity.log" 2>&1 ); then
  result integrity PASS "SHA256SUMS verified"
else
  result integrity FAIL "see reports/integrity.log"; fail=1
fi
for s in versions sim sta transistors drc_magic drc_klayout antenna_magic lvs cvc; do
  echo "--- $s"
  if [ -f "$HERE/$s.sh" ]; then
    bash "$HERE/$s.sh"; st=$?
  else
    st=127; echo "run_all: $HERE/$s.sh is missing"
  fi
  for n in $(stems_of "$s"); do
    f="$REPORTS/$n.result"
    if [ ! -f "$f" ]; then
      result "$n" FAIL "$s.sh exited $st and wrote no result"; fail=1; continue
    fi
    line="$(cat "$f")"
    if ! valid_line "$line"; then
      result "$n" FAIL "$s.sh wrote an unreadable result"; fail=1
    elif [ "$st" != 0 ]; then
      result "$n" FAIL "$s.sh exited with status $st (it wrote: $line)"; fail=1
    else
      case "$line" in PASS*) ;; *) fail=1;; esac
    fi
  done
done
: > "$REPORTS/summary.txt"
for n in $ORDER; do
  f="$REPORTS/$n.result"
  if [ -f "$f" ]; then line="$(cat "$f")"; else line="FAIL not run"; fi
  valid_line "$line" || line="FAIL unreadable result"
  case "$line" in PASS|"PASS "*) ;; *) fail=1;; esac
  printf '%-18s %s\n' "$n" "$line" >> "$REPORTS/summary.txt"
done
echo; echo "================ SUMMARY ================"; cat "$REPORTS/summary.txt"
[ $fail = 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
