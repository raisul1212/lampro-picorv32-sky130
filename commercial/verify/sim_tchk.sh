#!/usr/bin/env bash
# Gate-level simulation with SDF back-annotation AND timing checks
# ($setuphold, $width), with open-source tools only: OSS-CVC 7.00b carrying
# the three local fixes in cvc-local-fixes.patch, and the sky130_fd_sc_hd
# Verilog models with negative limits modelled (negtchk.py). Icarus Verilog,
# which this package's verify/sim.sh uses, does not evaluate timing checks,
# so a setup or hold violation passes there unseen.
#
# usage: sim_tchk.sh <netlist.v> <design.sdf> <tb.v> [period_ns [control_ns]]
#   PDK_ROOT  open_pdks "share/pdk" directory (contains sky130A/)   required
#   CVC       cvc64 built with cvc-local-fixes.patch                  default: cvc64
#   WORK      work and report directory                               default: ./sim_tchk.work
#   SDF_NAME  file name the testbench passes to $sdf_annotate         default: picorv32.sdf
#   SCOPE     hierarchical name of the design in the testbench        default: tb.uut
#
# At period_ns (default 8.25) the run must PASS: the testbench prints
# VERDICT PASS and CVC reports no timing violation. control_ns (default 4) is a negative control: it must
# FAIL with at least one timing violation, which shows the checks are live on
# this design and not only in the self-test. The testbench is expected to
# print "RESULT <x>" and "VERDICT PASS|FAIL", as
# sim/tb_picorv32_golden.v does, and to read +period=<ns>.
#
# Negative limits are modelled as Xcelium -neg_tchk models them, by the
# delayed-net construction of IEEE 1364-2005 15.5.1, done in the inputs
# (negtchk.py). Each flop's or latch's *_delayed nets are driven by a
# transport delay, one per net and edge; the per-instance values are carried
# by copies of the cell (one per set of delays) that a copy of the netlist
# names. The checks ($setuphold, $recrem, and $width on a signal with a
# delayed net) are moved onto those nets, their conditions are read as
# Xcelium reads them, and each instance's SDF limits are shifted to be
# non-negative. The rules are Xcelium's as measured (negtchk.py says how).
# CVC therefore reports a violation in delayed time against the shifted
# limit; WORK/negtchk_map.tsv gives each signal's rise and fall delay per
# instance to convert back (nothing here reads it; the Xcelium comparison's
# converter is kept with the evidence).
#
# Before the design runs, a self-test in WORK/selftest checks the binary, the
# remodelled library and the delay elements on twelve probes. The script
# refuses (exit 2) if any fails, because each failure was found to change the
# answer:
#   delayed   a flop clocked from *_delayed nets captures data (not x)
#   edge      SDF timing-check edges are kept (rising and falling D each get
#             their own limit; the falling probe must be flagged once)
#   keyword   a port named SUM (an SDF keyword) takes its IOPATH delay
#   sign      a negative SDF delay is not read as positive
#   pulse     a 20 ps D pulse inside the window is flagged on both edges
#             (a gate's inertial delay would swallow it)
#   xedge     a 1->x on D takes the same delay as a 0/1 change and is
#             flagged (a gate would take min(rise, fall) and miss it)
#   count     the self-test flags nothing it should not, and a fall 50 ps
#             after the edge (inside a -97 ps hold) is captured cleanly
#   notifier  every flagged flop's Q goes to x
#   negwin    a change inside the negative-hold region is clean and is not
#             captured (the old value is kept), as with Xcelium -neg_tchk
#   checks    a setup inside the window is flagged once, at the shifted limit
#   recrem    a clock 50 ps after a reset release is flagged against the
#             108 ps recovery, and one 70 ps before is clean against the
#             30 ps removal (OSS-CVC's $recrem takes its SDF ports and its
#             two limits the other way round from Xcelium; negtchk.py writes
#             them in CVC's order)
#   cancel    on a net delayed 136 ps rising and 201 ps falling, a fall
#             followed 30 ps later by 0->x gives one change, to x, at
#             +166 ps: the x (rising, so 136 ps) cancels the fall due
#             later, as in Xcelium. A plain per-edge delay ends at 0, and a
#             queue that does not cancel gives the x at +201 ps.
# After compiling the design, cvc_report.py coverage requires that every
# IOPATH, INTERCONNECT and timing-check entry of the SDF was applied to its
# own instance, and that every timing check of every flop in the netlist got
# a limit. Otherwise the run is a FAIL, whatever the testbench prints.
#
# Exit: 0 every check passed, 1 a check failed, 2 the run could not be trusted.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ $# -ge 3 ] && [ $# -le 5 ] || { sed -n '2,22p' "$0" >&2; exit 2; }
NETLIST="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
SDF="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
TB="$(cd "$(dirname "$3")" && pwd)/$(basename "$3")"
PERIOD="${4:-8.25}"
CONTROL="${5:-4}"
[ "$PERIOD" != "$CONTROL" ] || { echo "sim_tchk: period and control are both $PERIOD" >&2; exit 2; }
: "${PDK_ROOT:?PDK_ROOT must point at the open_pdks share/pdk directory}"
CVC="${CVC:-cvc64}"
WORK="${WORK:-$PWD/sim_tchk.work}"
SDF_NAME="${SDF_NAME:-picorv32.sdf}"
SCOPE="${SCOPE:-tb.uut}"
LIBV="$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/verilog"
for f in "$NETLIST" "$SDF" "$TB" "$LIBV/primitives.v" "$LIBV/sky130_fd_sc_hd.v"; do
  [ -f "$f" ] || { echo "sim_tchk: missing $f" >&2; exit 2; }
done
command -v "$CVC" > /dev/null || { echo "sim_tchk: CVC binary '$CVC' not found" >&2; exit 2; }
mkdir -p "$WORK" || exit 2
# An earlier run's verdicts must never stand beside this run's: refuse a WORK
# that already holds any.
if ls "$WORK"/*.result > /dev/null 2>&1; then
  echo "sim_tchk: $WORK holds .result files from an earlier run; use a new WORK" >&2; exit 2
fi
result() { echo "$2 $3" > "$WORK/$1.result"; echo "$1: $2 $3"; }
refuse() { result sim_tchk_selftest REFUSED "$1"; exit 2; }

# 1. the cell library with the delayed-net model (negtchk.py says why)
python3 "$HERE/negtchk.py" lib "$LIBV/sky130_fd_sc_hd.v" "$WORK/cells_neg.v" \
  || refuse "negtchk.py refused the cell library"

# 2. self-test of the simulator, the remodelled library and the delay element
T="$WORK/selftest"; mkdir -p "$T"
cat > "$T/probe.v" <<'EOF'
`timescale 1ns/1ps
module probe(input CLK, input DE, input DH, input DN, input DP, input DX, input A,
             input CLKR, input RB, input DC,
             output QE, output QH, output QN, output QP, output QX,
             output SUM, output COUT, output Y, output QR, output QC);
  sky130_fd_sc_hd__dfxtp_1 ffe (.CLK(CLK), .D(DE), .Q(QE), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__dfxtp_1 ffh (.CLK(CLK), .D(DH), .Q(QH), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__dfxtp_1 ffn (.CLK(CLK), .D(DN), .Q(QN), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__dfxtp_1 ffp (.CLK(CLK), .D(DP), .Q(QP), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__dfxtp_1 ffx (.CLK(CLK), .D(DX), .Q(QX), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__dfrtp_1 ffr (.CLK(CLKR), .D(1'b1), .RESET_B(RB), .Q(QR), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__dfxtp_1 ffc (.CLK(1'b0), .D(DC), .Q(QC), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__fa_1 fa (.A(A), .B(1'b0), .CIN(1'b0), .SUM(SUM), .COUT(COUT), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__inv_1 iv (.A(A), .Y(Y), .VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
endmodule
module selftest;
  reg clk = 0, de = 0, dh = 1, dn = 1, dp = 0, dx = 1, a = 0, clkr = 0, rb = 0, dc = 1;
  real dt = 0.3, sum_at = -1.0, y_at = -1.0;
  integer nc = 0;
  real dct = -1.0;
  reg dcv = 1'b0;
  wire qe, qh, qn, qp, qx, sum, cout, y, qr, qc;
  probe u (.CLK(clk), .DE(de), .DH(dh), .DN(dn), .DP(dp), .DX(dx), .A(a),
           .CLKR(clkr), .RB(rb), .DC(dc),
           .QE(qe), .QH(qh), .QN(qn), .QP(qp), .QX(qx), .SUM(sum), .COUT(cout), .Y(y), .QR(qr), .QC(qc));
  always @(posedge sum) sum_at = $realtime;
  always @(negedge y) y_at = $realtime;
  always @(u.ffc.D_delayed) if ($realtime > 5) begin
    if (nc == 0) begin dct = $realtime; dcv = u.ffc.D_delayed; end
    nc = nc + 1;
  end
  initial begin
    if ($value$plusargs("dt=%f", dt)) ;
    $sdf_annotate("selftest.sdf", u);
    $sdf_annotate("selftest_kw.sdf", u);
    fork                          // absolute times; the clock edge is at 10
      #9.75 dx = 1'bx;            // DX: 1->x 250 ps before: inside (266, -97)
      #9.8 dn = 0;                // DN: falls 200 ps before: inside (266, -97)
      #9.88 dp = 1;               // DP: a 20 ps pulse, rising at -120 ps
      #9.9 dp = 0;                //     and falling at -100 ps: both inside
      #(10.0 - dt) de = 1;        // DE: rises dt ns before the edge
      #10 begin clk = 1; a = 1; end
      #10.05 dh = 0;              // DH: falls 50 ps after the edge
      #15 dc = 0;                 // DC: falls, due 201 ps late,
      #15.03 dc = 1'bx;           //     then 0->x, due 136 ps late: it cancels the fall
      #20 rb = 1;                 // ffr: reset released, then the clock
      #20.05 clkr = 1;            //     50 ps after: inside the 108 ps recovery
      #22 clkr = 0;
      #25 rb = 0;
      #30 clkr = 1;               // ffr: the clock 70 ps before the release:
      #30.07 rb = 1;              //     outside the 30 ps removal
    join
    #5 $display("SELFTEST qe=%b qh=%b qn=%b qp=%b qx=%b sum_at=%0.3f y_at=%0.3f nc=%0d dct=%0.3f dcv=%b",
                qe, qh, qn, qp, qx, sum_at, y_at, nc, dct, dcv);
    $finish;
  end
endmodule
EOF
{
  echo '(DELAYFILE'; echo ' (SDFVERSION "3.0")'; echo ' (DESIGN "selftest")'; echo ' (DIVIDER .)'; echo ' (TIMESCALE 1ns)'
  for f in ffe ffh ffn ffp ffx; do cat <<EOF
 (CELL (CELLTYPE "sky130_fd_sc_hd__dfxtp_1") (INSTANCE $f)
  (DELAY (ABSOLUTE
   (IOPATH (posedge CLK) Q (0.321:0.321:0.321) (0.456:0.456:0.456))
  ))
  (TIMINGCHECK
   (HOLD (posedge D) (posedge CLK) (-0.068:-0.068:-0.068))
   (HOLD (negedge D) (posedge CLK) (-0.097:-0.097:-0.097))
   (SETUP (posedge D) (posedge CLK) (0.137:0.137:0.137))
   (SETUP (negedge D) (posedge CLK) (0.266:0.266:0.266))
  )
 )
EOF
  done
  cat <<EOF
 (CELL (CELLTYPE "sky130_fd_sc_hd__dfrtp_1") (INSTANCE ffr)
  (TIMINGCHECK
   (RECOVERY (posedge RESET_B) (posedge CLK) (0.108:0.108:0.108))
   (REMOVAL (posedge RESET_B) (posedge CLK) (0.030:0.030:0.030))
  )
 )
 (CELL (CELLTYPE "sky130_fd_sc_hd__dfxtp_1") (INSTANCE ffc)
  (TIMINGCHECK
   (HOLD (posedge D) (posedge CLK) (-0.068:-0.068:-0.068))
   (HOLD (negedge D) (posedge CLK) (-0.200:-0.200:-0.200))
   (SETUP (posedge D) (posedge CLK) (0.137:0.137:0.137))
   (SETUP (negedge D) (posedge CLK) (0.266:0.266:0.266))
  )
 )
EOF
  echo ')'
} > "$T/selftest.raw.sdf"
# the keyword and sign probes in a file of their own, annotated second, so a
# lexer that stops at SUM cannot hide the flop probes' delays
cat > "$T/selftest_kw.sdf" <<'EOF'
(DELAYFILE
 (SDFVERSION "3.0")
 (DESIGN "selftest")
 (DIVIDER .)
 (TIMESCALE 1ns)
 (CELL (CELLTYPE "sky130_fd_sc_hd__inv_1") (INSTANCE iv)
  (DELAY (ABSOLUTE
   (IOPATH A Y (-0.2:-0.2:-0.2) (-0.2:-0.2:-0.2))
  ))
 )
 (CELL (CELLTYPE "sky130_fd_sc_hd__fa_1") (INSTANCE fa)
  (DELAY (ABSOLUTE
   (IOPATH A SUM (0.5:0.5:0.5) (0.5:0.5:0.5))
  ))
 )
)
EOF
python3 "$HERE/negtchk.py" design "$LIBV/sky130_fd_sc_hd.v" "$T/probe.v" "$T/selftest.raw.sdf" \
    "$T/selftest.sdf" "$T/probe_neg.v" "$T/variants.v" "$T/map.tsv" > /dev/null \
  || refuse "negtchk.py refused the self-test design"
( cd "$T" && "$CVC" +define+USE_POWER_PINS +sdf_log_file sdf.log -l comp.log \
    probe_neg.v "$LIBV/primitives.v" "$WORK/cells_neg.v" variants.v > comp.out 2>&1 ) \
  || refuse "self-test did not compile (see $T/comp.out)"
( cd "$T" && ./cvcsim +dt=0.3 > clean.log 2>&1 && ./cvcsim +dt=0.1 > live.log 2>&1 \
          && ./cvcsim +dt=0.05 > negwin.log 2>&1 ) || refuse "self-test did not run"
viol() { grep -c '\[566\] timing violation' "$1"; }
on() { grep -c "timing violation in selftest\\.u\\.$1 " "$2"; }
q() { sed -n "s/.*SELFTEST.* $1=\\([01xz]\\).*/\\1/p" "$2"; }
# Order matters: each probe is read before any later one whose answer it would
# change, so that a plant of one defect is refused for that defect.
[ "$(q qe "$T/clean.log")" = 1 ] \
  || refuse "delayed: the probe flops did not capture data (is the remodelled library in use?)"
[ "$(on ffe "$T/clean.log")" = 0 ] \
  || refuse "edge: a 300 ps rising-D setup took the falling-D limit (needs the edge fix)"
[ "$(on ffn "$T/clean.log")" = 1 ] \
  || refuse "edge: a 200 ps falling-D setup against the 266 ps falling-D limit was not flagged once (needs the edge fix)"
grep -q 'selftest\.sdf([0-9]*) ERROR' "$T/sdf.log" \
  && refuse "the remodelled flop SDF did not annotate cleanly (see $T/sdf.log)"
grep -q 'selftest_kw\.sdf([0-9]*) ERROR' "$T/sdf.log" \
  && refuse "keyword: a port named SUM was refused by the SDF reader (needs the SUM port fix)"
grep -q 'sum_at=10.500' "$T/clean.log" || refuse "keyword: SUM did not take its 0.5 ns IOPATH delay"
grep -q 'y_at=10.000' "$T/clean.log" || refuse "sign: a -0.2 ns IOPATH delay was not applied as 0 (needs the sign fix)"
[ "$(on ffp "$T/clean.log")" = 2 ] \
  || refuse "pulse: a 20 ps D pulse inside the window was not flagged on both edges (inertial delayed net?)"
[ "$(on ffx "$T/clean.log")" = 1 ] \
  || refuse "xedge: a 1->x on D 250 ps before the edge was not flagged (the x took another delay?)"
[ "$(viol "$T/clean.log")" = 5 ] && [ "$(q qh "$T/clean.log")" = 1 ] \
  || refuse "count: the self-test flagged a violation it should not (or a fall 50 ps after the edge was not captured cleanly)"
[ "$(q qn "$T/clean.log")$(q qp "$T/clean.log")$(q qe "$T/live.log")" = xxx ] \
  || refuse "notifier: a flagged flop's Q did not go to x"
[ "$(on ffe "$T/negwin.log")" = 0 ] && [ "$(q qe "$T/negwin.log")" = 0 ] \
  || refuse "negwin: a rise 50 ps before the edge, inside the -68 ps hold, was flagged or captured"
[ "$(on ffe "$T/live.log")" = 1 ] && grep -q 'setup(of setuphold)((posedge D_delayed[^)]*).*, 39 ps)' "$T/live.log" \
  || refuse "checks: a 100 ps setup inside the (137, -68) window was not flagged once, at the shifted 39 ps (137 - 98)"
[ "$(on ffr "$T/clean.log")" = 1 ] && grep -q 'now 20050 ps \[566\] timing violation in selftest\.u\.ffr ' "$T/clean.log" \
  || refuse "recrem: a clock 50 ps after a reset release was not the one recrem violation (are the RECREM ports or limits the wrong way round?)"
[ "$(sed -n 's/.*SELFTEST.* nc=\([0-9]*\) dct=\([0-9.]*\) dcv=\([01xz]\).*/\1 \2 \3/p' "$T/clean.log")" = "1 15.166 x" ] \
  || refuse "cancel: a 0->x due before an earlier fall did not cancel it, as one change to x at +166 ps (no cancellation?)"
result sim_tchk_selftest PASS "12 probes ($("$CVC" 2>&1 | head -1 | cut -d' ' -f1))"

# 3. remodel the SDF, compile the design once; the period is a run-time plusarg
D="$WORK/design"; mkdir -p "$D"
python3 "$HERE/negtchk.py" design "$LIBV/sky130_fd_sc_hd.v" "$NETLIST" "$SDF" "$D/$SDF_NAME" \
    "$WORK/netlist_neg.v" "$WORK/variants.v" "$WORK/negtchk_map.tsv" \
  || { result sim_tchk_sdf FAIL "negtchk.py refused the design"; exit 2; }
( cd "$D" && "$CVC" +define+USE_POWER_PINS +sdfverbose +sdf_log_file sdf.log -l comp.log \
    "$TB" "$WORK/netlist_neg.v" "$LIBV/primitives.v" "$WORK/cells_neg.v" "$WORK/variants.v" > comp.out 2>&1 ) \
  || { result sim_tchk_compile FAIL "compile failed (see $D/comp.out)"; exit 2; }
python3 "$HERE/cvc_report.py" coverage "$D/$SDF_NAME" "$D/sdf.log" "$WORK/netlist_neg.v" "$SCOPE" \
  "$WORK/cells_neg.v" "$WORK/variants.v" > "$WORK/sdf_coverage.txt"
bash "$HERE/sim_tchk_sdf_summary.sh" "$WORK" "$?" || exit $?

# 4. the period, then the control (sim_tchk_periods.sh, testable on its own)
bash "$HERE/sim_tchk_periods.sh" "$WORK" "$D" "$PERIOD" "$CONTROL"
