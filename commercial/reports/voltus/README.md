# Voltus static power report (commercial build)

Run 43903863 (Voltus 23.10-p001_1, `report_power`, power view av_ss, rail VPWR at 1.6 V, 100 C). The published
file is the scrubbed power report, gzip-compressed (`provenance.json` gives original and published hashes).

What this report contains: primary input activity 0.2 (20 %), and the per-cell internal, switching and total
power of 8,273 cells; the total is 12.98 mW (internal 8.833, switching 4.1, leakage 0.04497, units 1 mW).

What it does not contain: the static IR-drop figures. The report has no maximum or average IR drop and no clock
period. The IR-drop values used in the documents (VPWR 11.0 mV with minimum voltage 1.589 V, VGND 11.58 mV,
average about 8 mV) are quoted from this run in the PSM comparison records (`../psm/`); the IR-drop report
file listed in the run's manifest was not among the files supplied for release, and the run's job script was
not either. Those IR-drop values are secondary quoted records, not figures read from a released Voltus IR report.
