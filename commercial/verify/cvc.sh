#!/usr/bin/env bash
# Timing-check simulation with OSS-CVC (the timing simulation of record for this package): runs sim_tchk.sh
# on this package's netlist, full SDF and testbench, at the design period and at a negative-control period,
# and maps its verdicts to cvc_8.25ns and cvc_control. A missing CVC binary, a refused self-test or SDF
# coverage check, a crash, or a missing verdict is a FAIL of both results: the timing check is then not
# done, and is reported as not done.
#   CVC      cvc64 built with verify/cvc-local-fixes.patch      default: cvc64
#   CVC_CONTROL  negative-control period in ns                 default: 4
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
CONTROL="${CVC_CONTROL:-4}"
fail_both() { result cvc_8.25ns FAIL "$1"; result cvc_control FAIL "$1"; }
invalidate cvc_8.25ns cvc_control || { echo "cvc: could not clear earlier results" >&2; exit 2; }
CVC="${CVC:-cvc64}"
command -v "$CVC" > /dev/null || { fail_both "CVC binary '$CVC' not found; timing-check simulation not run"; exit 2; }
W="$(mktemp -d "$REPORTS/cvc.work.XXXXXX")" || { fail_both "could not create a work directory"; exit 2; }
NETLIST="${CVC_NETLIST:-$PKG/netlist/picorv32.sim.v}"
SDF="${CVC_SDF:-$PKG/timing/picorv32.sdf}"
WORK="$W/run" CVC="$CVC" bash "$PKG/verify/sim_tchk.sh" "$NETLIST" "$SDF" "$PKG/sim/tb_picorv32_golden.v" 8.25 "$CONTROL" > "$W/sim_tchk.out" 2>&1
rc=$?
clean_paths "$W/sim_tchk.out"
R="$W/run"
for k in sim_tchk_selftest sim_tchk_sdf; do
  if [ ! -f "$R/$k.result" ] || ! grep -q '^PASS' "$R/$k.result"; then
    fail_both "$k did not pass (status $rc; see reports/$(basename "$W")/sim_tchk.out)"; exit 2
  fi
done
one() {  # one <key> <result-file>
  if [ -f "$2" ] && [ "$(wc -l < "$2" | tr -d ' ')" = 1 ] && grep -q '^\(PASS\|FAIL\) ' "$2" && [ $rc -le 1 ]; then
    result "$1" "$(cut -d' ' -f1 "$2")" "$(cut -d' ' -f2- "$2")"
  else
    result "$1" FAIL "no verdict from sim_tchk.sh (status $rc)"; return 1
  fi
}
one cvc_8.25ns "$R/sim_tchk_8.25ns.result" || rc=2
one cvc_control "$R/sim_tchk_${CONTROL}ns_control.result" || rc=2
[ $rc = 0 ] || exit $rc
exit 0
