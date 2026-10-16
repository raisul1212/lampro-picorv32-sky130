# Conformal equivalence checks, open build

Historical run: job 43978613, Conformal 24.10-p100, on the open build's Yosys netlist and routed netlist.
Scrubbed copies of the two tool logs and the setup record (`setup-summary.txt`).

| step | log | compare points | non-equivalent |
|---|---|---|---|
| RTL against the Yosys netlist (FSM encoding files and setup analysis) | `rtl_to_synth.log` | 1,959 | 0 (the closing line reads `compare=1959 noneq=0 abort=0 unknown=0`) |
| Yosys netlist against the routed netlist | `synth_to_routed.log` | 1,904 | 0 (Compare Results block: aborted 0, uncompared 0) |

The 1,959 total is two reported classes: 1,862 compared points (307 outputs and 1,555 flip-flops) and 97
points reported as equivalences of merged flip-flops, 1,862 + 97 = 1,959. The log also notes three golden key
points that were unmapped and not compared. The setup record states 77 flip-flops merged, 5 converted to
constants, and the two controls: without the FSM encoding files, 1,246 non-equivalent points; a stage-1 proof
aid (a netlist synthesised from an RTL copy with `fsm_encoding=none` on the two state registers, which is not
the shipped design) with no setup analysis, 1,202 non-equivalent points, and 1,958 points with setup analysis
and none non-equivalent. The logs of the two control runs were not among the files supplied for release; those
numbers rest on the setup record. These controls are diagnostic configurations and are distinct from the final
equivalence checks above.

Conformal is a commercial tool; the open implementation flow used no commercial tool, but this equivalence
check did. The open scripts do not regenerate it.
