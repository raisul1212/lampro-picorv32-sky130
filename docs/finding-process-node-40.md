# Finding: the September PicoRV32 commercial route was run with `setDesignMode -process 40`

Recorded 25 October 2026. Status: open finding, effect on results not measured.

**What.** The place-and-route script of the September commercial PicoRV32 campaign run sets the process node to 40: line 17 of its `work/pnr_picorv32_tc/pnr.tcl` is `setDesignMode -process 40`, and Innovus ran with it (the run's `innovus.log`). The kit is sky130, a 130 nm process. 40 is another foundry's node name and has no place on sky130.

**Cause.** The Innovus adapter of the campaign framework had a literal default of 40 for the process node, used whenever nothing named one. The September run named none, so the default reached the tool.

**Fixed by.** Campaign commit 3bbb810 (1 October 2026), "cadence_digital: a route with no process named is refused, not given 40": a route with no process named now refuses instead of using a default. The later removal of hard-coded values from the framework (25 October 2026) extends the same rule to every flow.

**Effect on the September results.** NOT MEASURED. Nobody re-ran the September route with a different node, so no figure shows what the setting changed in area, timing, routing or extraction, or whether it changed anything. Until that is measured, read every routed-layout figure of that campaign run as "routed with process node 40 set".

**Why the open checks cannot see it.** The open checkers (DRC, LVS, antenna and the like) read the finished layout and netlist. None of them knows which node the placer was told to assume, so a clean report says nothing about this setting.

**Scope not established by this note.** This note concerns the campaign run's own route. Whether the commercial-tool evidence files published in this repository were produced by that same script is not established here.

**Rerun.** The owner has said the rerun names the node explicitly as 130 (the sky130 node) at submission of the place-and-route stage, through a registrar setting; that stage has not run yet at the time of writing. When it has, its result and this finding's measured effect belong in a follow-up note.
