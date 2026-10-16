#!/usr/bin/env bash
# Record sim_tchk.sh's coverage verdict, testable without CVC.
# usage: sim_tchk_sdf_summary.sh <work> <coverage exit status>
set -u
WORK=$1; cov=$2
result() { echo "$1 $2" > "$WORK/sim_tchk_sdf.result"; echo "sim_tchk_sdf: $1 $2"; }
if [ "$cov" != 0 ] && [ "$cov" != 1 ]; then
  result REFUSED "coverage could not be read (see $WORK/sdf_coverage.txt)"; exit 2
fi
# Preserve CVC's counts verbatim. An absent INTERCONNECT row is no evidence
# of application; it must never become an invented percentage.
summary=$(awk '
  BEGIN {
    n = split("sdf_iopath_entries sdf_interconnect_entries sdf_timingcheck_entries design_timing_checks", keys, " ")
    rows["sdf_interconnect_entries"] = "sdf_interconnect_entries=NOT_MEASURED"
  }
  /^(sdf_(iopath|interconnect|timingcheck)_entries|design_timing_checks)=/ {
    split($0, fields, "=")
    rows[fields[1]] = $0
  }
  END {
    for (i = 1; i <= n; i++)
      if (keys[i] in rows) printf "%s;", rows[keys[i]]
  }
' "$WORK/sdf_coverage.txt")
if [ "$cov" = 0 ]; then
  result PASS "$summary"
else
  result FAIL "$summary SDF not fully applied, or checks left without limits (see $WORK/sdf_coverage.txt)"; exit 1
fi
