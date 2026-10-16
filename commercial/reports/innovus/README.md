# Innovus clock-tree statistics (excerpt)

Run 43902639 (the ss implementation run), Innovus v25.11-s102_1. `cts-excerpt.log` holds the tool identity and the
complete clock-tree statistics block of the post-route clock optimisation step: 176 clock buffers, 1,557 sinks,
and `insertion delay [min=0.862, max=0.963, avg=0.916 ...]` for skew group `clk/cm_func`, both in the "PRO
initial state" and "PRO final" summaries. The rounded figures used in the documents are 0.86 to 0.96 ns and
0.92 ns. Other clock-tree stages of the same log report other insertion delays (for example 0.837 to 0.901 ns
and 0.957 to 1.044 ns at earlier stages); the excerpt is the block that the release figure was taken from.
These are Innovus measurements and are distinct from the OpenSTA results shipped in `reports/`.
