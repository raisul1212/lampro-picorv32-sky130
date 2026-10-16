# Open-flow implementation configuration

`config.json` is the LibreLane configuration of the historical run 44019112 (the shipped open layout plus the ECO
antenna-diode step), as recorded. The placeholders `<WORK>/...` stand for the RTL file (`rtl/picorv32.v`) and the
SDC (`constraints/picorv32.sdc`, equal in content to the commercial v1.0.1 SDC) given as inputs.

Settings it records: `FP_CORE_UTIL` 45 (percent configured core utilisation), `CTS_DISTANCE_BETWEEN_BUFFERS` 100
(um), `GRT_ANTENNA_REPAIR_MARGIN` 20, `MAX_FANOUT_CONSTRAINT` 10, `CLOCK_PERIOD` 8.25 (ns); the maximum fanout of 10 is
also a command in `constraints/picorv32.sdc`.

These are settings, not measured outcomes. This file is not evidence of a utilisation sweep: no report of a run
at 55 % or 65 % utilisation, and no count of root clock-buffer loads at 40 to 45 %, was located, and those
statements are withdrawn.
