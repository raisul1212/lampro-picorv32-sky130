# Xcelium gate-level simulation with timing checks, commercial build

Historical run: job 43903862, Xcelium 24.03-s011 (`xrun -64bit -sv -neg_tchk -sdf_verbose`), 7 October 2026,
at clock periods 8.25, 10 and 4 ns. The three tool logs and the job script are published here as scrubbed
copies (`provenance.json` gives the original size and sha256 of each). Nothing here is a new run; rerunning
Xcelium needs a suitable licensed environment. CVC (`../cvc/`) is the open timing-check simulator of record.

| period | verdict | timing-violation diagnostic blocks |
|---|---|---|
| 8.25 ns | VERDICT PASS, RESULT 55 | 0 |
| 10 ns | VERDICT PASS, RESULT 55 | 0 |
| 4 ns (control) | VERDICT FAIL, RESULT timeout | 76 |

SDF annotation table in each log: 50,696 of 50,696 path delays (100.00 %) and 6,228 of 6,228 timing-check
entries (100.00 %): 3,114 `$setuphold` and 3,114 `$width`.

**Parser rule.** A violation is a diagnostic block that begins with the line `Warning!  Timing violation`.
`summary.json` counts those blocks, per log.

**The wrapper's counts are wrong and its output is not published.** The job script ended each period with
`grep -ciE 'timing violation|$setuphold|$setup|$hold|$recrem|$width'` over the log. That pattern also matches
the `$setuphold` and `$width` lines of the SDF annotation table (2 lines in every log) and the
`$setuphold<setup>(...)` line inside each violation block, so it printed 2, 2 and 154 (= 2 + 2 x 76) where the
blocks number 0, 0 and 76. The job's own output file (`job_43903862.out`) repeats those figures and is
withheld for that reason.

**Inputs.** The job recorded these sha256 values: `picorv32.sdf` 0c5f54b5...b42e, `picorv32.powered.v`
5a53364c...d4, `tb_picorv32_golden.v` 418413b4...cff2 (full values in `summary.json`). None is byte-identical
to the shipped `timing/picorv32.sdf`, `timing/picorv32.sim.sdf`, `netlist/picorv32.sim.v` or
`sim/tb_picorv32_golden.v`, which were cleaned after the run (headers removed, buffers renamed). The
annotated timing-check count (6,228) equals the TIMINGCHECK count of the shipped simulation SDF, but byte
correspondence of the run inputs to the shipped files is not established. The older 8 ns run is not part of
this evidence.
