# PSM source placement on the commercial layout (route N): excerpt

Excerpt of the technical content of a development record. Rows for other layouts, probe experiments and the adapter's software identity are not reproduced.

Method line of the record: Stock librelane_3.0.14.sif, OpenROAD dcf36133a369abc8f3c5e5738cd4d82e4903c0e0, ss_100C_1v60 lib, 1.6 V, 20% input activity, budget 80 mV.

| run | dir | VPWR worst | VGND worst | power | note |
|---|---|---|---|---|---|
| route N, adapter default (2 top-layer pins) | routeN-run2 | 46.4 mV | 47.0 mV | 13.7 mW | control x3 139/141; one source 133/134 |
| route N, 4 Voltus pin locations | routeN-run3-voltus-pins | 36.8 | 34.8 | 13.7 | control x4 147/139 |
| route N, first run (pre two-control rewrite, single-source control only) | routeN-run1 | 46.4 | 47.0 | 13.7 | kept |

Voltus (frozen voltus_ir_run7_43903863): VPWR 11.0 mV (min V 1.589), VGND 11.58 mV, avg 8.0, 12.98 mW. (quoted value; see `../voltus/README.md`)

The 2-top-layer-source and 4-Voltus-pin-location rows are experiments with the unmodified PSM on the commercial layout. Source placement is part of each result. The x3 and x4 figures in the notes column are resistance-scaled control runs.
