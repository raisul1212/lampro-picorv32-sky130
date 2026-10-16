#!/usr/bin/env bash
# The period run and the control run of sim_tchk.sh, kept in a file of their
# own so that they can be tested with a stub simulator (no CVC needed).
#
# usage: sim_tchk_periods.sh <work> <design dir> <period_ns> <control_ns>
#   Runs <design dir>/cvcsim +period=<p> for each, reads each log with
#   cvc_report.py run, and writes one .result per run into <work>:
#     sim_tchk_<period>ns            PASS when VERDICT PASS and no timing violation
#     sim_tchk_<control>ns_control   PASS when VERDICT FAIL with at least one violation
#   A run whose report cannot be generated is REFUSED under that same key.
#   A key whose .result already exists is refused before anything runs, so an
#   earlier run's verdict can never stand beside this run's refusal.
#
# Exit: 0 both verdicts passed, 1 a verdict failed, 2 a report could not be
# generated or <work> already held a verdict.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ $# -eq 4 ] || { sed -n '2,15p' "$0" >&2; exit 2; }
WORK=$1; D=$2; PERIOD=$3; CONTROL=$4
result() { echo "$2 $3" > "$WORK/$1.result"; echo "$1: $2 $3"; }
KEYS="sim_tchk_${PERIOD}ns sim_tchk_${CONTROL}ns_control"
for k in $KEYS; do
  [ ! -e "$WORK/$k.result" ] || { echo "sim_tchk: $WORK/$k.result is from an earlier run; use a new WORK" >&2; exit 2; }
done
rc=0
for p in "$PERIOD" "$CONTROL"; do
  if [ "$p" = "$PERIOD" ]; then key="sim_tchk_${p}ns"; else key="sim_tchk_${p}ns_control"; fi
  ( cd "$D" && ./cvcsim +period="$p" > "$WORK/sim_$p.log" 2>&1 )
  python3 "$HERE/cvc_report.py" run "$WORK/sim_$p.log" > "$WORK/sim_$p.txt" \
    || { result "$key" REFUSED "run report could not be generated (see $WORK/sim_$p.log)"; exit 2; }
  n=$(sed -n 's/^timing_violations=//p' "$WORK/sim_$p.txt")
  v=$(sed -n 's/^verdict=//p' "$WORK/sim_$p.txt")
  r=$(sed -n 's/^result=//p' "$WORK/sim_$p.txt")
  if [ "$p" = "$PERIOD" ]; then
    if [ "$v" = PASS ] && [ "$n" = 0 ]; then result "$key" PASS "RESULT $r, 0 timing violations"
    else result "$key" FAIL "RESULT $r, VERDICT $v, $n timing violations"; rc=1; fi
  else
    if [ "$v" = FAIL ] && [ "$n" -gt 0 ]; then result "$key" PASS "control fails as expected: RESULT $r, $n timing violations"
    else result "$key" FAIL "control did not fail with violations: VERDICT $v, $n timing violations"; rc=1; fi
  fi
done
exit $rc
