# Xcelium gate-level simulation with timing checks, open build

Historical run: job 44019555, Xcelium 24.03-s011 (`xrun -64bit -sv -neg_tchk -sdf_verbose`), 9 October 2026,
at clock periods 8.25, 10 and 4 ns. The three tool logs are published as scrubbed copies (`provenance.json`
gives the original size and sha256 of each). The job script of this run was not among the files supplied for
release and is not published. Nothing here is a new run; rerunning Xcelium needs a suitable licensed
environment. CVC (`../cvc/`) is the open timing-check simulator of record.

| period | verdict | timing-violation diagnostic blocks |
|---|---|---|
| 8.25 ns | VERDICT PASS, RESULT 55 | 0 |
| 10 ns | VERDICT PASS, RESULT 55 | 0 |
| 4 ns (control) | VERDICT FAIL, RESULT timeout | 2 |

SDF annotation table in each log: 76,271 of 76,271 path delays (100.00 %) and 6,388 of 6,388 timing-check
entries (100.00 %): 3,194 `$setuphold` and 3,194 `$width`. These are the open package's own counts; the
commercial package's counts are not transferred to it.

**Parser rule.** A violation is a diagnostic block that begins with the line `Warning!  Timing violation`.
`summary.json` counts those blocks, per log.

**The wrapper's counts are wrong and its output is not published.** The job script counted lines with
`grep -ciE 'timing violation|$setuphold|$setup|$hold|$recrem|$width'`. That pattern also matches the two
`$setuphold` and `$width` lines of the SDF annotation table and the `$setuphold<setup>(...)` line inside
each violation block, so it printed 2, 2 and 6 (= 2 + 2 x 2) where the blocks number 0, 0 and 2. The job's
own output file (`job_44019555.out`) repeats those figures and is withheld for that reason.

**Inputs.** The job recorded sha256 values for `picorv32.sdf`, `picorv32.powered.v` and
`tb_picorv32_golden.v` (see `summary.json`). They equal the sha256 of the shipped `open/timing/picorv32.sim.sdf`,
`open/netlist/picorv32.sim.v` and `open/sim/tb_picorv32_golden.v`.
