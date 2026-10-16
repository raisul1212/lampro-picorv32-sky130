#!/usr/bin/env bash
# Antenna check with Magic after extraction (same Magic settings as the sign-off run). Antenna
# violations are Magic feedback entries added by antennacheck; feedback already present after
# extraction (extraction warnings) is cleared first and reported separately. Expect 0 violations.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
GDS="${GDS:-$PKG/layout/picorv32.gds}"
invalidate antenna_magic || { echo "antenna_magic: could not clear the earlier result" >&2; exit 2; }
rm -f "$REPORTS/antenna_magic.log" || { result antenna_magic FAIL "could not clear the earlier log"; exit 2; }
W="$(mktemp -d "$REPORTS/antenna_magic.work.XXXXXX")" || { result antenna_magic FAIL "no work directory"; exit 2; }; cd "$W" || exit 2
cat > antenna.tcl <<TCL
crashbackups stop
drc off
gds readonly true
gds rescale false
gds read $GDS
puts "TOP_EXISTS_AFTER_READ: [cellname list exists $TOP]"
load $TOP
select top cell
puts "TOP_EXISTS: [cellname list exists $TOP]"
puts "TOP_CHILDREN: [llength [cellname list children $TOP]]"
extract do local
extract no capacitance
extract no coupling
extract no resistance
extract no adjust
extract unique
extract
puts "ANTENNA_BEGIN"
puts "EXTRACT_WARNINGS: [feedback count]"
feedback clear
antennacheck debug
antennacheck
puts "ANTENNA_VIOLATIONS: [feedback count]"
puts "ANTENNA_END"
quit -noprompt
TCL
magic -dnull -noconsole -rcfile "$PDKPATH/libs.tech/magic/sky130A.magicrc" antenna.tcl > "$REPORTS/antenna_magic.log" 2>&1
mrc=$?
clean_paths "$REPORTS/antenna_magic.log"
if [ $mrc != 0 ]; then result antenna_magic FAIL "magic exited with status $mrc (see reports/antenna_magic.log)"; exit 2; fi
if ! grep -aq ANTENNA_END "$REPORTS/antenna_magic.log"; then result antenna_magic FAIL "check did not complete (see reports/antenna_magic.log)"; exit 2; fi
E=$(grep -a '^TOP_EXISTS_AFTER_READ:' "$REPORTS/antenna_magic.log" | tail -1 | cut -d' ' -f2)
K=$(grep -a '^TOP_CHILDREN:' "$REPORTS/antenna_magic.log" | tail -1 | cut -d' ' -f2)
if [ -z "$E" ] || [ "$E" = 0 ] || [ -z "$K" ] || [ "$K" -le 0 ] 2>/dev/null; then result antenna_magic FAIL "layout did not load (top cell present: ${E:-?}, child cells: ${K:-?})"; exit 2; fi
GATES=$(grep -a 'gates analyzed' "$REPORTS/antenna_magic.log" | tail -1 | tr -s ' ')
N=$(grep -a '^ANTENNA_VIOLATIONS:' "$REPORTS/antenna_magic.log" | tail -1 | cut -d' ' -f2)
W2=$(grep -a '^EXTRACT_WARNINGS:' "$REPORTS/antenna_magic.log" | tail -1 | cut -d' ' -f2)
if [ "$N" = 0 ]; then result antenna_magic PASS "0 antenna violations (${GATES# }; ${W2:-?} extraction warning(s))"; else result antenna_magic FAIL "${N:-unknown} antenna violations"; exit 1; fi
