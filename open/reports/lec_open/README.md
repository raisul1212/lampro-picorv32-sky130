# Open-method equivalence attempt (negative result)

`first_attempt.out` is the output of an attempt to prove RTL-to-netlist equivalence for the open build with
open tools only (8 October 2026, 52 s, exit code 3). Its result line reads
`equivalent=False compared=1864 proven=586 unproven=1278`: 586 of 1,864 compare points were proven and
1,278 were not, so the attempt did not establish equivalence. The log lists the first unproven points.

This file says nothing about how long any other open-method proof was run or how it ended; no duration or
outcome of a longer proof is recorded in the released files. Equivalence of the open build is established by
the Conformal runs in `../conformal/`.
