# TRACE-V: a PicoRV32 RISC-V core on SKY130, built by agentic AI and verified with independent open-source tools

TRACE-V stands for "Traceable RISC-V: AI-built, Checked, Evidenced". It is a routed,
block-level implementation of [PicoRV32](https://github.com/YosysHQ/picorv32)
(32-bit RISC-V, RV32I, default parameters) in the SkyWater `sky130A` process with the
`sky130_fd_sc_hd` standard-cell library, clocked at 8.25 ns (about 121 MHz). The repository is
https://github.com/raisul1212/trace-v.

Release v2.0 contains two implementations of the same design. The same RTL and the same
constraint file (`constraints/picorv32.sdc`, byte-identical in both folders) were implemented by
a commercial flow (Cadence Genus and Innovus) and by an open flow (Yosys and OpenROAD in LibreLane).
Both builds are verified with the same open-source scripts.

* `commercial/` is the v1.0.1 release, unchanged.
* `open/` is the open-flow build, new in v2.0.

Each folder is a self-contained package with its own `verify/`, `reports/` and `SHA256SUMS`.
Each build was signed off at three corners with 0.25 ns clock uncertainty. DRC was run with two
independent decks, LVS against the routed netlist, and logic equivalence at both synthesis and
routing. Post-layout gate-level simulation was run with flop timing checks, and static IR was
analyzed. The physical, timing and simulation checks can be reproduced from either folder with
open-source tools.

## License

* This package is licensed for **non-commercial academic instruction and research only** (`LICENSE`, copyright 2026 Raisul Islam). Commercial or any other use requires written permission; see Contact below.
* Publications, theses and teaching materials that use these files should cite https://github.com/raisul1212/trace-v.
* The third-party components keep their own licenses: `rtl/picorv32.v` is ISC (copyright 2015 Claire Xenia Wolf, `LICENSES/ISC-picorv32.txt`); the SkyWater SKY130 PDK and cell data are Apache-2.0 (SkyWater Technology Foundry and Google LLC, `LICENSES/Apache-2.0.txt`). `NOTICE` lists all three.

## Contact

This design was implemented and signed off by an agentic chip-design framework. For research collaboration or licensing inquiries about the framework, contact Raisul Islam — raisul@purdue.edu.

## Releases

* v1.0: PicoRV32 at 8 ns from the commercial flow; it remains available at tag v1.0.
* v1.0.1: the 8 ns route was replaced by an 8.25 ns route, which has a wider setup margin at the slow corner.
* v2.0: the v1.0.1 build moved to `commercial/`, unchanged, and an open-flow build of the same RTL under the same constraints was added in `open/`.

## The two builds side by side

Both builds use the constraints in `constraints/picorv32.sdc` (sha256 prefix `14469a66864f3bda`):
an 8.25 ns clock with 0.25 ns uncertainty, a maximum fanout of 10, and a half-period I/O delay of
4.125 ns, because the testbench drives on the falling edge. The ports `mem_la_*`, `pcpi_*`, `eoi`
and `trace_*` are unconstrained.

| | commercial (v1.0.1) | open (v2.0) |
|---|---|---|
| clock / constraints | 8.25 ns, identical SDC | 8.25 ns, identical SDC |
| ss setup (shipped OpenSTA, nominal RC) | +0.280 ns (OpenSTA) / +0.180 ns (signoff timer) | +0.129 ns |
| ff hold | +0.034 ns | +0.054 ns |
| die | 357.42 x 355.64 um | 480.21 x 490.93 um (45 % configured utilization) |
| logic transistors | 87,237 | 144,143 |
| DRC / antenna / LVS | 0 / 0 / match | 0 / 0 / match |
| static IR (worst) | 11.0 / 11.58 mV (Voltus) | 5.55 / 5.57 mV (PSM) |
| equivalence | RTL→netlist→routed (Conformal) | RTL→netlist→routed (Conformal) |

The IR figures come from different tools (Voltus for the commercial build, OpenROAD PSM for the
open build); the PSM method, run on the commercial layout, gives 12.09 / 12.07 mV.

### Step by step: tool and result in each flow

| Step | Commercial: tool, result | Open: tool, result |
|---|---|---|
| Synthesis | Genus 25.11; 8,273 cells in the final layout (7,845 after synthesis) | Yosys 0.62 with ABC; 10,801 logic cells in the final layout |
| Place and route at 8.25 ns | Innovus 25.11; closes | OpenROAD, modified; closes (on the reference configuration with the default SDC, stock OpenROAD ends at −2.053 ns at max_ss with 3,104 slew violations) |
| Timing, shipped OpenSTA script | ss setup +0.280 ns, ff hold +0.032 ns | ss setup +0.129 ns, ff hold +0.054 ns |
| Static IR, worst VPWR | Cadence Voltus; 11.0 mV | OpenROAD PSM, modified; 5.55 mV. On the commercial layout: 12.09 mV (unmodified PSM: 46.4 mV) |
| Logic equivalence (commercial tool in both) | Conformal 24.10; RTL → netlist → routed proven | Conformal 24.10; RTL → netlist → routed proven |
| Simulation with timing checks (commercial tool in both) | Xcelium 24.03; 0 violations, 3,114 checks | Xcelium 24.03; 0 violations, 3,194 checks |
| DRC / antenna / LVS (open tools in both) | Magic, KLayout, Netgen; 0 / 0 / match | Magic, KLayout, Netgen; 0 / 0 / match |

Conformal and Xcelium were used for the open build as well. The open equivalence method did not
prove the RTL-to-netlist step for this design (586 of 1,864 key points; the x-aware sequential proof
was undecided after 2 h), and Icarus Verilog does not evaluate timing checks. The open build's
implementation uses no commercial tool.

## Equivalent tools in the two flows

| Step | Commercial build (v1.0.1) | Open build (v2.0) |
|---|---|---|
| Logic synthesis | Cadence Genus 25.11 | Yosys 0.62 with ABC, inside LibreLane 3.0.14 |
| Floorplan, placement, clock tree, routing, timing repair | Cadence Innovus 25.11 | OpenROAD (upstream `dcf36133`) with private modifications, driven by LibreLane 3.0.14 |
| Parasitic extraction for timing | Innovus, with the typical extraction file of the Cadence sky130 kit (nominal RC) | OpenRCX, inside OpenROAD |
| Signoff static timing | Cadence Tempus 23.10 | OpenSTA inside OpenROAD (upstream `857316ff`), with private modifications |
| Static IR drop | Cadence Voltus | OpenROAD PSM with a private modification |
| Antenna repair | Innovus NanoRoute with an antenna margin | OpenROAD antenna repair, then two diodes added with LibreLane's stock `Odb.InsertECODiodes` step |
| Logic equivalence | Cadence Conformal 24.10 | Cadence Conformal 24.10 (same tool) |
| Gate-level simulation with timing checks | Cadence Xcelium 24.03 | Cadence Xcelium 24.03 (same tool) |
| Release verification (`verify/`) | Magic 8.3.623, KLayout 0.30.7, Netgen 1.5.316, OpenSTA 2.7.0, Icarus Verilog 13.0 | the same unmodified tools |

## Modifications inside the open-source tools

Implementation used OpenROAD with private modifications that are not published. Every check an
outsider runs uses unmodified open-source tools. The modifications are in four places:

1. **OpenROAD Resizer (`rsz`): electrical repair and rebuffering.** After routing, repair uses the
   extracted parasitics, including zero-length shunt capacitances, in place of an estimate that had
   under-counted wire load by 2.2 to 2.4 times on two measured nets. Driver sizing uses the selected
   corner's model and the SDC slew limit, and fanout headroom accounts for antenna-diode loads.
2. **OpenSTA inside OpenROAD: parasitics and SDC.** The SPEF reader and the parasitic store give the
   Resizer the extracted RC network in a form its buffering model can use, and constraint checks
   ignore empty exception entries.
3. **OpenROAD PSM: static IR.** Voltage sources can be placed on a power pin's own routing layer
   as well as on the top layer. With this change, the PSM result on the commercial layout is within
   about 1 mV of Voltus.
4. **LibreLane: flow integration.** A post-route loop repairs electrical, setup and hold violations
   against freshly extracted parasitics, the flow exits with failure when a stated setup target is
   missed, and unchanged detailed wires are preserved.

Yosys and ABC, Magic, KLayout, Netgen and Icarus Verilog were not modified. The antenna repair of the
final layout uses a stock LibreLane step.

## Software developed for this work

The design was implemented and verified by an agentic chip-design framework under the designer's
direction. The software developed for it falls into three groups.

1. **Modifications inside open-source tools**, the four listed above. They are private and not published.
2. **Adapters of the agentic framework.** An adapter drives one tool step, reads its settings back,
   refuses a run it cannot verify, and records the result.
   * Used for this release, commercial flow: adapters for Genus synthesis, Innovus place and route,
     Tempus timing, Voltus static IR and Conformal logic equivalence, behind an evidence registrar
     that writes each result to a ledger and freezes its inputs and outputs with checksums. The
     Xcelium simulation ran as a recorded job.
   * Used for this release, open flow: LibreLane runs with recorded configurations and hashes; the
     Conformal equivalence set-up (flip-flop renaming checked for identical structure, and FSM
     encoding files); PSM runs with a source-feed control and a weakened-grid control; and the
     stock-LibreLane ECO diode run.
   * Used for both builds: the verification scripts shipped in each folder's `verify/`.
   * Developed alongside: an open logic-equivalence adapter over Yosys and ABC, whose run on this
     design is reported here only as the negative result in the step-by-step table (586 of 1,864 key
     points; it did not prove the RTL-to-netlist step); and, not the source of any released number,
     an open static-IR adapter over OpenROAD PSM and a LibreLane runner and pre-flight plugin that read
     back every setting.
3. **Evidence handling.** Every cited result comes from a run whose inputs and outputs are frozen
   with checksums, and each verify script was checked to fail on a deliberately damaged input.

## File map

The two folders have the same structure.

| Path | Content |
|---|---|
| `<flow>/rtl/picorv32.v` | PicoRV32 source, unmodified (ISC license) |
| `<flow>/netlist/picorv32.synth.v` | Gate-level netlist after logic synthesis |
| `<flow>/netlist/picorv32.routed.v` | Post-route netlist (clock tree, repair buffers); used for STA |
| `<flow>/netlist/picorv32.routed.pg.v` | Post-route netlist with power pins; used for LVS |
| `<flow>/netlist/picorv32.sim.v` | Post-route netlist with the cell supplies tied off; used for simulation |
| `<flow>/layout/picorv32.gds` | Final layout (GDSII) |
| `<flow>/layout/picorv32.def` | Final layout (DEF) |
| `<flow>/constraints/picorv32.sdc` | Timing constraints, byte-identical in both folders |
| `<flow>/timing/picorv32.spef` | Extracted parasitics (nominal RC) |
| `<flow>/timing/picorv32.sdf` | Delay file as written by the timing tool |
| `<flow>/timing/picorv32.sim.sdf` | Same delays with the port-ended INTERCONNECT entries removed, for Icarus Verilog |
| `<flow>/sim/tb_picorv32_golden.v` | Testbench: hand-assembled RV32I program summing 1..10, stores 55 to `0x10000000` |
| `<flow>/verify/` | One script per check; `run_all.sh` runs all of them |
| `<flow>/reports/` | Output of `verify/run_all.sh` on that folder |
| `<flow>/SHA256SUMS` | Checksums of every file in the folder except `reports/` and itself |
| `docs/TRACE-V_PicoRV32_SKY130_deck.pdf`, `docs/TRACE-V_PicoRV32_SKY130_whitepaper.pdf` | Presentation and whitepaper |
| `LICENSE`, `LICENSES/`, `NOTICE` | License of this repository, the third-party licenses, and who holds what |

`<flow>` is `commercial` or `open`.

## PDK pin

All checks of both builds use this PDK:

* open_pdks 1.0.471, commit `97d08448b2f813d15d71d3cc183014e9ac7a4f3f`
  ([RTimothyEdwards/open_pdks](https://github.com/RTimothyEdwards/open_pdks))
* `sky130_fd_sc_hd` at commit `4f4cfd106206c21fcd52b59c69749dbc90ccda07`
  ([google/skywater-pdk](https://github.com/google/skywater-pdk))

The open build was implemented with open_pdks `8afc8346`, the version LibreLane 3.0.14 selects, whose
cell LEF and ss/tt timing libraries are byte-identical to those of open_pdks `97d08448`. Both builds
were verified with `97d08448`.

The PDK is installed with [volare](https://github.com/efabless/volare):

```
volare enable --pdk sky130 97d08448b2f813d15d71d3cc183014e9ac7a4f3f
```

`PDK_ROOT` is set to the directory that contains `sky130A/` (for volare,
`$HOME/.volare/volare/sky130/versions/<hash>`; for other installs, the open_pdks
`share/pdk` directory).
The pinned PDK is required. LVS and antenna results depend on the PDK version: with a newer PDK
than the pinned one, the antenna-diode cells of the open build fail LVS.

## Tools

The open-source checkers are available pre-installed in the public container image
`ghcr.io/librelane/librelane:3.0.14` (for example `apptainer pull docker://ghcr.io/librelane/librelane:3.0.14`).
The versions printed inside it, and recorded in `reports/versions.txt` by every run, are:

```
Magic:          8.3.623
Netgen:         Netgen 1.5.316 compiled on Tue Feb 10 11:09:08 UTC 2026
KLayout:        KLayout 0.30.7
OpenSTA:        2.7.0
Icarus Verilog: Icarus Verilog version 13.0 (devel) ()
Python:         Python 3.13.9
```

The same tools can be installed separately. Besides the checkers, the scripts use `bash`, GNU `grep`, `cut`
and `tr`, and `python3`.

## How to verify

The checks for one build are run with:

```
export PDK_ROOT=/path/to/pdk-root          # contains sky130A/
cd <repository>/commercial                 # or <repository>/open
# inside the container (bind mounts adjusted to the system):
apptainer exec -B "$PDK_ROOT" -B "$PWD" librelane_3.0.14.sif bash verify/run_all.sh
# or, with the tools installed locally:
bash verify/run_all.sh
```

`run_all.sh` verifies the folder's `SHA256SUMS`, prints the tool versions, runs every check below,
writes the logs and one `*.result` file per check into that folder's `reports/`, and prints a
summary. Each check can also be run alone (`bash verify/<name>.sh`). A check fails if its input
does not load: an empty layout or an unreadable SPEF is reported as FAIL, not as zero violations.
The scripts are the same in both folders, except for the expected transistor count.

| Script | What it does | Expected |
|---|---|---|
| `verify/drc_magic.sh` | Magic full-chip DRC, `drc(full)` style, on `layout/picorv32.gds` | 0 errors |
| `verify/drc_klayout.sh` | KLayout, SkyWater `sky130A_mr.drc` deck (FEOL, BEOL, off-grid) | 0 findings |
| `verify/antenna_magic.sh` | Magic extraction and `antennacheck`; the feedback entries added by `antennacheck` are counted | 0 violations |
| `verify/lvs.sh` | Magic extraction from the GDS, Netgen LVS against `netlist/picorv32.routed.pg.v` with the PDK setup file; standard cells are also compared at transistor level | `Circuits match uniquely` |
| `verify/sta.sh` (`sta.tcl`) | OpenSTA at ss 100 C 1.60 V, tt 25 C 1.80 V, ff -40 C 1.95 V with the routed netlist, SDC and SPEF, propagated clock; the SPEF annotation is checked | setup and hold slack >= 0, no slew, capacitance or fanout violations, SPEF read without error |
| `verify/sim.sh` | Icarus Verilog gate-level simulation with SDF back-annotation at 8.25 ns, plus a 4.125 ns negative control (half the period) | 8.25 ns: `RESULT 55`, `VERDICT PASS`; 4.125 ns: `VERDICT FAIL` |
| `verify/transistors.sh` | Transistor count: cell instances in `layout/picorv32.def` times the transistors per cell in the PDK cell SPICE | 87237 (commercial), 183139 (open) |

The 4.125 ns control is part of the simulation check: a passing simulation at a clock that the timing
rejects would show that the SDF was not applied. Each verify script was checked to fail on a deliberately damaged input.

## Results: commercial flow (v1.0.1, unchanged)

The commercial build was implemented with Cadence Genus and Innovus; timing and the SDF come from
Tempus, equivalence from Conformal, and IR from Voltus.

### Signoff results (commercial tools, 8.25 ns)

Produced with commercial signoff tools and recorded in the project ledger. The scripts in `commercial/` do not regenerate these numbers.

| Item | Result |
|---|---|
| DRC (Magic) | 0 |
| DRC (KLayout) | 0 |
| Antenna | 0 |
| LVS | matched, 8,492 / 8,492 nets |
| Logic equivalence (RTL to netlist) | equivalent at both steps (1,916 and 1,864 compare points) |
| Setup slack, ss / tt / ff | +0.180 / +2.388 / +2.957 ns |
| Hold slack, ss / tt / ff | +0.716 / +0.214 / +0.034 ns |
| Clock uncertainty | 0.25 ns, included in the slacks above |
| Slew, capacitance, fanout violations | 0 at all corners |
| Gate-level simulation (Icarus Verilog) | passes at 8.25 ns; the control fails |
| Gate-level simulation with timing checks (Xcelium) | 0 violations at 8.25 ns, with 3,114 setup/hold checks applied; the 4 ns control fails with 76 violations |
| Static IR drop | VPWR 11 mV / VGND 11.6 mV against an 80 mV budget |
| Power | 13.0 mW at 20% activity |
| Size | routed block: 8,273 cells and 75,681 um2 of standard cells (the synthesis netlist before placement: 7,845 cells, 71,909 um2); 87,237 transistors; die 357.42 x 355.64 um |

### Reproduced with open-source tools

The checks were run in a fresh copy of `commercial/`, inside the container `ghcr.io/librelane/librelane:3.0.14`, with the PDK above. The script exit status is non-zero while any check fails.

| Check | Status | Detail |
|---|---|---|
| Package checksums | PASS | SHA256SUMS verified |
| Transistor count (DEF x PDK cell SPICE) | PASS | 87237 transistors in 20924 DEF components (136 cell types) |
| Gate-level simulation, 8.25 ns | PASS | RESULT 55, VERDICT PASS |
| Simulation negative control, 4.125 ns | PASS | control fails as expected (RESULT trap) |
| OpenSTA ss (100 C, 1.60 V) | PASS | setup 0.280 ns, hold 0.712 ns, slew/cap/fanout violations 0/0/0, SPEF annotated 8384 of 8557 drivers (173 unannotated) |
| OpenSTA tt (25 C, 1.80 V) | PASS | setup 2.403 ns, hold 0.212 ns, slew/cap/fanout violations 0/0/0, SPEF annotated 8384 of 8557 drivers (173 unannotated) |
| OpenSTA ff (-40 C, 1.95 V) | PASS | setup 2.964 ns, hold 0.032 ns, slew/cap/fanout violations 0/0/0, SPEF annotated 8384 of 8557 drivers (173 unannotated) |
| DRC, Magic | PASS | 0 DRC errors (145 cell types in the top cell) |
| DRC, KLayout sky130A_mr | PASS | 0 findings |
| Antenna, Magic | PASS | 0 antenna violations (20800 gates analyzed.; 1 extraction warning(s)) |
| LVS, Magic + Netgen | PASS | Circuits match uniquely; Circuit 1 contains 8273 devices, Circuit 2 contains 8273 devices. Circuit 1 contains 8492 nets, Circuit 2 contains 8492 nets. |

Notes on this run:

* The ss setup slack is +0.280 ns in OpenSTA and +0.180 ns in the commercial signoff timer; both meet timing. The setup slack is the worst over all paths, including the half-period input and output paths.
* LVS: the antenna diodes are written by Magic as an instance with `perim=`, and by the PDK cell SPICE as a diode element with `pj=`. `verify/lvs.sh` rewrites that one line of the extracted SPICE (same values) before Netgen runs; without it, Netgen fails on every diode cell. LVS compares 8,273 cell instances and 8,492 nets, and each library cell is also compared at transistor level against the PDK SPICE.
* The transistor count is derived from the DEF components, which include tap and filler cells (zero transistors); the cell count in the signoff table is counted differently.
* A gate-level simulation at 4.125 ns (control) must fail; the core traps and `RESULT trap` is printed. At 8.25 ns, `RESULT 55` and `VERDICT PASS` are printed.

### Limitations of the commercial build

* Timing is signed off at nominal RC. An independent re-extraction shows max RC costs 0.21 ns of ss setup; an estimate combining the two extractors puts the margin at about -0.03 ns at max RC, so about 8.3 ns would be needed there. The package holds one SPEF (nominal RC); the three STA corners reuse it.
* The margins are thin: ss setup +0.180 ns and ff hold +0.034 ns, after 0.25 ns of clock uncertainty.

### What was cleaned in `commercial/`

The package was derived from the working run directory without changing the design:

* `layout/picorv32.gds` is copied unmodified (`SHA256SUMS` records its hash).
* Tool header comment lines that carried host names, file paths and commands were removed from the DEF and the Verilog netlists. Nothing else in these files was edited.
* Eight buffer instances named by the flow were renamed `alias_1` to `alias_8` consistently in every netlist, the DEF, the SPEF and the SDFs.
* `constraints/picorv32.sdc`: the leading comment lines were rewritten; every command is byte-identical.
* `sim/tb_picorv32_golden.v`: the leading comment block was rewritten; the code is unchanged.
* `timing/picorv32.sim.sdf` is `timing/picorv32.sdf` with the INTERCONNECT entries ending at a port removed (454 entries; Icarus Verilog cannot annotate them).
* `rtl/picorv32.v` is the upstream file, byte for byte.

## Results: open flow (v2.0)

### Flow

* LibreLane 3.0.14, Classic flow.
* Yosys synthesis, with `SYNTH_ABC_BUFFERING` on and the `DELAY 0` strategy.
* OpenROAD place and route, with private modifications to timing repair.
* Core utilization 45 % (configured), clock-tree buffer spacing 100 um, maximum fanout 10, antenna repair margin 20.
* At 55 % utilization global routing fails with congestion, and at 65 % timing repair fails. At 40 to 45 % without the clock-tree buffer spacing, the root clock buffer drives 16 loads against the limit of 10.
* Two antenna diodes were inserted after routing with LibreLane's stock `Odb.InsertECODiodes` step.

### Size

| Item | Result |
|---|---|
| Die | 480.21 x 490.93 um |
| Standard-cell area | 122,928 um2, of which 3,919 um2 are tap cells (119,009 um2 without them, the figure comparable with the commercial routed block) |
| Cells | 10,801 logic cells, plus 3,132 taps, 494 antenna diodes, 19,498 decap and 11,766 fill |
| Transistors | 183,139, of which 144,143 are in logic cells and 38,996 in decap cells |

### Reproduced with open-source tools

The checks were run in `open/`, inside the container `ghcr.io/librelane/librelane:3.0.14`, with the pinned PDK. The script exit status is non-zero while any check fails.

| Check | Status | Detail |
|---|---|---|
| Package checksums | PASS | SHA256SUMS verified |
| Transistor count (DEF x PDK cell SPICE) | PASS | 183139 transistors in 45691 DEF components (128 cell types) |
| Gate-level simulation, 8.25 ns | PASS | RESULT 55, VERDICT PASS |
| Simulation negative control, 4.125 ns | PASS | control fails as expected (RESULT timeout) |
| OpenSTA ss (100 C, 1.60 V) | PASS | setup 0.129 ns, hold 0.744 ns, slew/cap/fanout violations 0/0/0, SPEF annotated 10696 of 11009 drivers (313 unannotated) |
| OpenSTA tt (25 C, 1.80 V) | PASS | setup 2.028 ns, hold 0.235 ns, slew/cap/fanout violations 0/0/0, SPEF annotated 10696 of 11009 drivers (313 unannotated) |
| OpenSTA ff (-40 C, 1.95 V) | PASS | setup 2.706 ns, hold 0.054 ns, slew/cap/fanout violations 0/0/0, SPEF annotated 10696 of 11009 drivers (313 unannotated) |
| DRC, Magic | PASS | 0 DRC errors (128 cell types in the top cell) |
| DRC, KLayout sky130A_mr | PASS | 0 findings |
| Antenna, Magic | PASS | 0 antenna violations (30900 gates analyzed.; 3 extraction warning(s)) |
| LVS, Magic + Netgen | PASS | Circuits match uniquely; Circuit 1 contains 11237 devices, Circuit 2 contains 11237 devices. Circuit 1 contains 10944 nets, Circuit 2 contains 10944 nets. |

STA uses the shipped `verify/sta.tcl`, the nominal SPEF and the shared SDC. The flow's own
9-corner signoff gives max_ss setup +0.026 ns (max RC), nom_ss setup +0.129 ns and min_ff hold
+0.051 ns, with slew, capacitance and fanout at 0 in every corner.

### Checks with other tools

These results are not regenerated by the scripts in `open/`.

| Check | Result |
|---|---|
| Gate-level simulation with timing checks (Xcelium 24.03, SDF, `-neg_tchk`) | 8.25 ns: VERDICT PASS, RESULT 55, 0 timing violations, 3,194 setup/hold checks annotated (100 %); 10 ns: PASS, 0 violations; 4 ns control: VERDICT FAIL (RESULT timeout), 2 timing violations |
| Logic equivalence, RTL to Yosys netlist (Conformal LEC 24.10) | equivalent; 1,959 compare points, 0 non-equivalent, 0 aborted, 0 unknown |
| Logic equivalence, Yosys netlist to routed netlist (Conformal LEC 24.10) | equivalent; 1,904 compare points, 0 non-equivalent |
| Static IR (OpenROAD PSM, private modifications) | worst VPWR 5.554 mV, VGND 5.573 mV; average 2.85 / 2.75 mV; budget 80 mV (5 % of 1.6 V) |

The Xcelium run uses the harness of the v1.0.1 run.

The RTL-to-netlist comparison required three steps. Flip-flop instances were renamed after their
RTL registers, by a script that asserts identical cells and connections. FSM encoding files were
given for the two state registers that Yosys re-encoded: `cpu_state` from 8-bit one-hot to 7-bit
one-hot, and `mem_wordsize` from 2-bit binary to 3-bit one-hot. Conformal setup analysis merged 77
RTL registers (duplicates and registers the default configuration never uses) and treated 5 as
constants. Without the encoding files, 1,246 points are non-equivalent.

Static IR was analyzed on the final layout at ss 100 C 1.6 V, with 20 % input activity, a power of
22.0 mW and 8 supply pins per net on met4/met5. The controls behave as required: a single source gives 32.2 mV;
resistance x 3 gives 16.7 mV, and resistance x 25 gives 138.9 mV, which is over budget. No Voltus
run exists on the open layout.

## Limitations

* The I/O timing of both builds is set to the testbench's half-cycle protocol: inputs are driven and outputs are sampled on the falling clock edge. The ports `mem_la_*`, `pcpi_*`, `eoi` and `trace_*` are unconstrained.
* The post-layout simulation runs one 9-instruction program covering 6 of 40 RV32I opcodes; LEC and STA cover the whole design.
* Logic equivalence (Conformal) and the timing-checked simulation (Xcelium) use commercial tools and are not regenerated by the open scripts.
* Scope: packaging, electromigration, metal fill, seal ring, pad frame, foundry precheck and dynamic IR were outside the scope of this block-level release.

## Corrections

**v2.0.1.** The commercial build's size was given as 7,845 cells and 71,909 um2 of standard cells. Those are the figures of the synthesis netlist before placement. The routed block that was signed off has 8,273 cells and 75,681 um2 of standard cells, including the 176 clock-tree buffers added in layout; the transistor count, 87,237, was already taken from the routed layout. The open build's 122,928 um2 includes 3,919 um2 of tap cells, so the like-for-like comparison is 119,009 um2 against 75,681 um2. The README, whitepaper and deck now label each figure. No layout, netlist or check result changed.

