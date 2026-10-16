# PSM comparison records on the commercial layout

Two excerpts of development records. `route_n-comparison.md` gives the modified PSM on the commercial layout
(route N): worst drops 12.088 mV on VPWR and 12.068 mV on VGND, total power 13.7 mW, with the single-source and
resistance x3 controls. `source-placement.md` gives the unmodified PSM with two top-layer sources (46.4 / 47.0 mV)
and with four sources at Voltus pin locations (36.8 / 34.8 mV). Both quote Voltus values (VPWR 11.0 mV, VGND
11.58 mV) as the reference; the released Voltus report (`../voltus/`) is a power report and does not itself show
those IR-drop values. These records do not establish general agreement between PSM and Voltus, and the comparison
layout is not the shipped open layout.
