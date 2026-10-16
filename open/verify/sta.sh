#!/usr/bin/env bash
# OpenSTA run at ss/tt/ff with the routed netlist, SDC and SPEF.
# Pass: setup and hold slack >= 0 and no slew/cap/fanout violations, all three corners.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
# An STA process or parser that fails is a FAIL of its corner, whatever the log contains.
rc=0
invalidate sta_ss sta_tt sta_ff || { echo "sta: could not clear earlier results" >&2; exit 2; }
for c in ss tt ff; do
  rm -f "$REPORTS/sta_$c.log" || { result "sta_$c" FAIL "could not clear the earlier log"; rc=2; continue; }
  CORNER=$c sta -no_init -exit "$PKG/verify/sta.tcl" > "$REPORTS/sta_$c.log" 2>&1
  src=$?
  clean_paths "$REPORTS/sta_$c.log"
  if [ $src != 0 ]; then result "sta_$c" FAIL "sta exited with status $src (see reports/sta_$c.log)"; rc=2; continue; fi
  out="$(python3 "$PKG/verify/util.py" sta "$REPORTS/sta_$c.log")"
  prc=$?
  if [ $prc != 0 ]; then result "sta_$c" FAIL "log parser exited with status $prc"; rc=2; continue; fi
  st="${out%% *}"; facts="${out#* }"
  case "$st" in
    PASS) result "sta_$c" PASS "$facts";;
    FAIL) result "sta_$c" FAIL "$facts"; rc=1;;
    *) result "sta_$c" FAIL "no result (see reports/sta_$c.log)"; rc=2;;
  esac
done
exit $rc
