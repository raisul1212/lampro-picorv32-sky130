#!/usr/bin/env bash
# Hierarchical DRC of the complete PicoRV32 block with Magic (sky130A rules, drc(full) style), on the top cell with its
# whole hierarchy. Expect 0 errors. (Per-cell counts of library cells checked on their own
# are deliberately not used: they are not DRC of this layout.)
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
GDS="${GDS:-$PKG/layout/picorv32.gds}"
invalidate drc_magic || { echo "drc_magic: could not clear the earlier result" >&2; exit 2; }
rm -f "$REPORTS/drc_magic.log" || { result drc_magic FAIL "could not clear the earlier log"; exit 2; }
W="$(mktemp -d "$REPORTS/drc_magic.work.XXXXXX")" || { result drc_magic FAIL "no work directory"; exit 2; }; cd "$W" || exit 2
cat > drc_magic.tcl <<TCL
gds read $GDS
puts "TOP_EXISTS: [cellname list exists $TOP]"
load $TOP
select top cell
expand
puts "TOP_CHILDREN: [llength [cellname list children $TOP]]"
drc style drc(full)
drc euclidean on
drc check
drc catchup
set why [drc listall why]
set boxes 0
foreach {rule locs} \$why { incr boxes [llength \$locs]; puts "DRC_RULE: \$rule ([llength \$locs] locations)" }
puts "DRC_BOXES: \$boxes"
puts "DRC_TOTAL: [drc list count total]"
quit -noprompt
TCL
magic -dnull -noconsole -rcfile "$PDKPATH/libs.tech/magic/sky130A.magicrc" drc_magic.tcl > "$REPORTS/drc_magic.log" 2>&1
mrc=$?
clean_paths "$REPORTS/drc_magic.log"
if [ $mrc != 0 ]; then result drc_magic FAIL "magic exited with status $mrc (see reports/drc_magic.log)"; exit 2; fi
N=$(grep -a '^DRC_TOTAL:' "$REPORTS/drc_magic.log" | tail -1 | cut -d' ' -f2)
B=$(grep -a '^DRC_BOXES:' "$REPORTS/drc_magic.log" | tail -1 | cut -d' ' -f2)
E=$(grep -a '^TOP_EXISTS:' "$REPORTS/drc_magic.log" | tail -1 | cut -d' ' -f2)
K=$(grep -a '^TOP_CHILDREN:' "$REPORTS/drc_magic.log" | tail -1 | cut -d' ' -f2)
if [ -z "$E" ] || [ "$E" = 0 ] || [ -z "$K" ] || [ "$K" -le 0 ] 2>/dev/null; then result drc_magic FAIL "layout did not load (top cell present: ${E:-?}, child cells: ${K:-?})"; exit 2; fi
if [ -z "$N" ]; then result drc_magic FAIL "no count produced (see reports/drc_magic.log)"; exit 2; fi
if [ "$N" = 0 ] && [ "$B" = 0 ]; then result drc_magic PASS "0 DRC errors ($K cell types in the top cell)"; else result drc_magic FAIL "$N DRC errors ($B marked locations)"; exit 1; fi
