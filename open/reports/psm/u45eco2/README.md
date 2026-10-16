# OpenROAD PSM on the open layout (u45eco2)

Run 44019556: static IR analysis of the shipped open layout with the modified OpenROAD PSM (image 018; its sha256 is the
first line of `job-44019556.out`). `job.sh` is the job script. The run's Tcl (`run.tcl`), the source-location files
(`P*.loc`, `G*.loc`), the scaled-resistance LEF files and the liberty are inputs that were not among the files supplied for
release, so the corner, the input activity and the number and placement of the supply sources per net are not stated by these
two files.

| case | VPWR worst / avg (mV) | VGND worst / avg (mV) |
|---|---|---|
| all supply sources (`eco_all_pins`) | 5.554 / 2.849 | 5.573 / 2.752 |
| single source (`eco_single`) | 32.173 / 21.271 | 31.516 / 20.892 |
| LEF resistance x 3 (`eco_Rx3`) | 16.663 / 8.548 | 16.720 / 8.256 |
| LEF resistance x 25 (`eco_Rx25`) | 138.858 / 71.235 | 139.333 / 68.796 |

Total power 22.0 mW (`Total power : 2.20e-02 W`); 45,691 instance rows are read per case. The design's stated IR budget is
80 mV (5 % of 1.6 V; that figure is not in these files): the x3 and single-source cases are below it and the x25 case is
above it. This run reports PSM results only; no Voltus run exists on the open layout.
