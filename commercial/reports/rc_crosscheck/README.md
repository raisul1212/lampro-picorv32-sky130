# Independent RC re-extraction cross-check (commercial layout)

Historical run 43903861: the routed commercial layout was re-extracted with OpenROAD RCX (nominal, max and min RC
SPEF files, sizes in `job_43903861.out`) and timed with OpenSTA, next to OpenSTA on the Innovus nominal-RC SPEF.
The job script was not among the files supplied for release; tool versions and input hashes are not recorded in the
output file, so only the output is published. This is a historical re-extraction result, not a new nominal, min and max
SPEF reproduction bundle.

Measured (worst slack, ns; `RESULT <corner> <spef>` blocks of the output):

| corner | SPEF | setup (max) | hold (min) |
|---|---|---|---|
| ss 100 C 1.60 V | Innovus nominal RC | 0.28 | 0.71 |
| ss 100 C 1.60 V | OpenRCX nominal | 0.55 | 0.70 |
| ss 100 C 1.60 V | OpenRCX max RC | 0.34 | 0.71 |
| ff -40 C 1.95 V | Innovus nominal RC | 2.96 | 0.03 |
| ff -40 C 1.95 V | OpenRCX nominal | 3.02 | 0.03 |
| ff -40 C 1.95 V | OpenRCX min RC | 3.07 | 0.03 |

Arithmetic from those numbers: 0.55 - 0.34 = 0.21 ns, the setup cost of max RC in this record (a subtraction of two measured values).

**Estimate, not measurement.** The commercial signoff timer (Tempus, `../tempus/`) reports +0.180 ns at ss with the
Innovus nominal SPEF. Subtracting 0.21 ns gives +0.180 - 0.21 = -0.030 ns; adding that deficit to the 8.25 ns period gives
8.28 ns, about 8.3 ns, if one assumes a one-for-one change of period and slack. This combines results of two different
analyses and is not a measured max-RC timing requirement. The shipped three-corner OpenSTA checks reuse one nominal-RC
SPEF.
