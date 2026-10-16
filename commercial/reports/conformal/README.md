# Conformal equivalence checks, commercial build

Historical run: job 43902641, Conformal 24.10-p100. Scrubbed copies of the two tool logs.

| step | log | compare points | non-equivalent | aborted | unknown |
|---|---|---|---|---|---|
| RTL against the synthesised netlist | `rtl_to_synth.log` | 1,916 equivalent | 0 | 0 | 0 |
| synthesised netlist against the routed netlist | `synth_to_routed.log` | 1,864 equivalent | 0 | 0 | 0 |

The counts are the "Compare Results" block of each log (EQ, NON-EQ, Aborted, Uncompared) and the closing
`No of compare points / diff points / abort points / unknown points` lines. The routed-netlist comparison
treats the antenna-diode cell as a black box (see the log). Conformal is a commercial tool; the open scripts do
not regenerate these results.
