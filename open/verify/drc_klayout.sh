#!/usr/bin/env bash
# sky130A_mr.drc (SkyWater maintainers' KLayout deck): FEOL+BEOL+off-grid. Expect 0 findings.
# KLayout must exit 0 and write a new, valid report database with zero items; a report left from an earlier
# run is never read.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
invalidate drc_klayout || { echo "drc_klayout: could not clear the earlier result" >&2; exit 2; }
GDS="${GDS:-$PKG/layout/picorv32.gds}"
FINAL="$REPORTS/klayout_drc.lyrdb"
rm -f "$FINAL" "$REPORTS/drc_klayout.log" || { result drc_klayout FAIL "could not clear earlier outputs"; exit 2; }
W="$(mktemp -d "$REPORTS/drc_klayout.work.XXXXXX")" || { result drc_klayout FAIL "could not create a work directory"; exit 2; }
RDB="$W/klayout_drc.lyrdb"          # does not exist before the run
klayout -b -r "$PDKPATH/libs.tech/klayout/drc/sky130A_mr.drc" \
  -rd input="$GDS" -rd top_cell="$TOP" -rd report="$RDB" \
  -rd feol=true -rd beol=true -rd offgrid=true -rd seal=false -rd floating_met=false \
  -rd thr=2 > "$REPORTS/drc_klayout.log" 2>&1
krc=$?
clean_paths "$REPORTS/drc_klayout.log"
if [ $krc != 0 ]; then result drc_klayout FAIL "klayout exited with status $krc (see reports/drc_klayout.log)"; exit 2; fi
if [ ! -s "$RDB" ]; then result drc_klayout FAIL "no report produced (see reports/drc_klayout.log)"; exit 2; fi
python3 "$PKG/verify/util.py" sanitize-lyrdb "$RDB" > "$W/sanitize.out" 2>&1
src=$?
if [ $src != 0 ]; then result drc_klayout FAIL "report database invalid: $(head -c 200 "$W/sanitize.out" | tr '\n' ' ')"; exit 2; fi
out="$(python3 "$PKG/verify/util.py" lyrdb "$RDB" 2> "$W/lyrdb.err")"
prc=$?
if [ $prc != 0 ] || [ -z "$out" ]; then result drc_klayout FAIL "report database invalid: $(head -c 200 "$W/lyrdb.err" | tr '\n' ' ')"; exit 2; fi
cp "$RDB" "$FINAL" || { result drc_klayout FAIL "could not publish the report"; exit 2; }
N="${out%% *}"; CATS="${out#* }"
if [ "$N" = 0 ]; then result drc_klayout PASS "0 findings"; else result drc_klayout FAIL "$N findings: $CATS"; exit 1; fi
