# PSM on the commercial layout (route N): method and measured values (excerpt)

Excerpt of the technical content of a development record (section 1 of the original; lines 2 and 4 to 13). Agent comparison and narrative are removed; the table keeps the measured values and the Voltus values as quoted in the record.

Image 018 sha256 verified = 90b6a94b4d407cc97516332bd031f4ac493640c62d9204790e5427c1dc1202e5 (sha256sum of the .sif, in the job 43937397 log).

Method: probe script run.tcl, 5-field vsrc `x,y,size,V,layer`. Job 43937397. Inputs: probe0/picorv32.novirt.def, inputs-routeN SPEF and SDC, PDK ss_100C_1v60 liberty, 1.6 V, 20% input activity.

| case | PSM VPWR / VGND worst (mV) | Voltus VPWR / VGND (mV), as quoted in the record |
|---|---|---|
| four pins on own layers (met3 x2, met2 x2) | 12.088 / 12.068 (CSV); avg 8.38 / 8.46 | 11.0 / 11.58 |
| single source (first pin) | 133.406 / 134.193 |  |
| R x3 (all LEF RESISTANCE x3) | 36.265 / 36.205 (3.0001x, 3.0000x) |  |

Total power 13.7 mW (Voltus 12.98 mW).

Route N is the commercial-flow routed layout that the record compares with Voltus run 43903863. This table is not a measurement of the shipped open layout; that is `open/reports/psm/u45eco2/`.
