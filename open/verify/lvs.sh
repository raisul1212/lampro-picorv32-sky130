#!/usr/bin/env bash
# LVS: layout (GDS, extracted by Magic) vs netlist/picorv32.routed.pg.v with Netgen.
# Expect "Circuits match uniquely".
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
GDS="${GDS:-$PKG/layout/picorv32.gds}"
NET="${NET:-$PKG/netlist/picorv32.routed.pg.v}"
invalidate lvs || { echo "lvs: could not clear the earlier result" >&2; exit 2; }
rm -f "$REPORTS/lvs_extract.log" "$REPORTS/lvs_netgen.log" "$REPORTS/lvs_report.txt" || { result lvs FAIL "could not clear earlier outputs"; exit 2; }
# a new work directory every run: layout.spice and lvs_report.out are never reused
W="$(mktemp -d "$REPORTS/lvs.work.XXXXXX")" || { result lvs FAIL "no work directory"; exit 2; }; cd "$W" || exit 2
cat > extract.tcl <<TCL
gds read $GDS
load $TOP
select top cell
extract do local
extract no capacitance
extract no coupling
extract no resistance
extract no adjust
extract unique
extract all
ext2spice lvs
ext2spice -o layout.spice
quit -noprompt
TCL
magic -dnull -noconsole -rcfile "$PDKPATH/libs.tech/magic/sky130A.magicrc" extract.tcl > "$REPORTS/lvs_extract.log" 2>&1
mrc=$?
if [ $mrc != 0 ]; then clean_paths "$REPORTS/lvs_extract.log"; result lvs FAIL "magic exited with status $mrc (see reports/lvs_extract.log)"; exit 2; fi
[ -s layout.spice ] || { clean_paths "$REPORTS/lvs_extract.log"; result lvs FAIL "extraction produced no SPICE (see reports/lvs_extract.log)"; exit 2; }
# Magic writes the antenna diode as an X instance with perim=; the PDK cell SPICE writes a D element
# with pj=. Without this rewrite Netgen fails on every antenna-diode cell. Values are unchanged.
python3 "$PKG/verify/util.py" layoutspice layout.spice layout_dform.spice || { clean_paths "$REPORTS/lvs_extract.log"; result lvs FAIL "SPICE rewrite failed"; exit 2; }
STD="$PDKPATH/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
cat > lvs.tcl <<TCL
# layout (circuit 1) vs routed power-pin netlist (circuit 2); the standard cells are read from
# the PDK SPICE, so each cell is also compared at transistor level.
set lay [readnet spice layout_dform.spice]
set sch [readnet spice $STD]
readnet verilog $NET \$sch
lvs [list \$lay $TOP] [list \$sch $TOP] $PDKPATH/libs.tech/netgen/sky130A_setup.tcl lvs_report.out
quit
TCL
netgen -batch source lvs.tcl > "$REPORTS/lvs_netgen.log" 2>&1
nrc=$?
clean_paths "$REPORTS/lvs_extract.log" "$REPORTS/lvs_netgen.log"
if [ $nrc != 0 ]; then result lvs FAIL "netgen exited with status $nrc (see reports/lvs_netgen.log)"; exit 2; fi
cp lvs_report.out "$REPORTS/lvs_report.txt" || { result lvs FAIL "no netgen report (see reports/lvs_netgen.log)"; exit 2; }
clean_paths "$REPORTS/lvs_report.txt"
R="$REPORTS/lvs_report.txt"
[ -s "$R" ] || { result lvs FAIL "no netgen report (see reports/lvs_netgen.log)"; exit 2; }
COUNTS=$(grep -a '^Circuit 1 contains .* nets' "$REPORTS/lvs_netgen.log" | tail -1 | tr -s ' ')
DEVS=$(grep -a '^Circuit 1 contains .* devices' "$REPORTS/lvs_netgen.log" | tail -1 | tr -s ' ')
FINAL=$(grep -a '^Final result' "$R" | tail -1)
if [ "$FINAL" = "Final result: Circuits match uniquely." ]; then
  result lvs PASS "Circuits match uniquely; $DEVS $COUNTS"
else
  result lvs FAIL "${FINAL:-no final result}; $DEVS $COUNTS"; exit 1
fi
