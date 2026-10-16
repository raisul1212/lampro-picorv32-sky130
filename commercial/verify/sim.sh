#!/usr/bin/env bash
# Functional gate-level simulation with partial SDF timing (Icarus Verilog). Icarus does not evaluate the
# SDF timing checks and leaves some interconnect annotations unapplied (see README, "Icarus limitations");
# timing checks are the job of sim_tchk.sh / cvc.sh (CVC), not of this script.
# 8.25 ns (the design clock) must complete with RESULT 55 and VERDICT PASS. 4.125 ns (half the period)
# is a delay-sensitivity control for this workload: the testbench must complete and report VERDICT FAIL.
# A crashed or killed simulator, a missing executable, or a missing or contradictory verdict is a FAIL
# of the check, never a pass of the control.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
K1=sim_8.25ns; K2=sim_4.125ns_control
fail_both() { result $K1 FAIL "$1"; result $K2 FAIL "$1"; }
invalidate sim $K1 $K2 || { echo "sim: could not clear earlier results" >&2; exit 2; }
rm -f "$REPORTS/sim_compile.log" "$REPORTS/sim_8.25.log" "$REPORTS/sim_4.125.log" || { fail_both "could not clear earlier logs"; exit 2; }
V="$PDKPATH/libs.ref/sky130_fd_sc_hd/verilog"
W="$(mktemp -d "$REPORTS/sim.work.XXXXXX")" || { fail_both "could not create a work directory"; exit 2; }
cd "$W" || { fail_both "could not enter the work directory"; exit 2; }
# the testbench reads "picorv32.sdf" from cwd
cp "$PKG/timing/picorv32.sim.sdf" picorv32.sdf || { fail_both "could not copy the SDF"; exit 2; }
iverilog -g2005-sv -gspecify -ginterconnect -DUSE_POWER_PINS -o sim.vvp \
  "$PKG/sim/tb_picorv32_golden.v" "$PKG/netlist/picorv32.sim.v" "$V/primitives.v" "$V/sky130_fd_sc_hd.v" \
  > "$REPORTS/sim_compile.log" 2>&1
crc=$?
clean_paths "$REPORTS/sim_compile.log"
if [ $crc != 0 ] || [ ! -s sim.vvp ]; then fail_both "compile failed, status $crc (see reports/sim_compile.log)"; exit 2; fi
rc=0
for p in 8.25 4.125; do
  if [ "$p" = 8.25 ]; then key=$K1; else key=$K2; fi
  vvp sim.vvp +period=$p > "$REPORTS/sim_${p}.log" 2>&1
  vrc=$?
  clean_paths "$REPORTS/sim_${p}.log"
  if [ $vrc != 0 ]; then result $key FAIL "simulator exited with status $vrc (see reports/sim_${p}.log)"; rc=1; continue; fi
  r=$(grep -a '^RESULT' "$REPORTS/sim_${p}.log" | tail -1)
  v=$(grep -a '^VERDICT' "$REPORTS/sim_${p}.log" | tail -1)
  nv=$(grep -a '^VERDICT' "$REPORTS/sim_${p}.log" | sort -u | wc -l | tr -d ' ')
  if [ "$nv" -gt 1 ]; then result $key FAIL "contradictory verdicts in reports/sim_${p}.log"; rc=1; continue; fi
  if [ "$p" = 8.25 ]; then
    if [ "$v" = "VERDICT PASS" ] && [ "$r" = "RESULT 55" ]; then result $key PASS "$r, $v (functional simulation, partial SDF timing)"; else result $key FAIL "${r:-no RESULT}, ${v:-no VERDICT}"; rc=1; fi
  else
    if [ "$v" = "VERDICT FAIL" ] && [ -n "$r" ]; then result $key PASS "control fails as expected ($r)"; else result $key FAIL "control did not complete with a failing verdict: ${r:-none}, ${v:-none}"; rc=1; fi
  fi
done
exit $rc
