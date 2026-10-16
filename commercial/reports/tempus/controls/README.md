# Tempus slew, capacitance and fanout checks and their controls

Historical run: job 43902642, Tempus 23.10-p001_1, at ss, tt and ff. For each corner the ledger rows
(`ledger-excerpt.md`, D-220 to D-222) record three reports:

* the design check, `report_constraint -all_violators` for max_capacitance, max_fanout and max_transition:
  0 / 0 / 0 at ss, tt and ff;
* a library control, in which no design-level limit is set and a 5 pF load is placed on the net of
  `is_lui_auipc_jal_jalr_addi_add_sub_reg/Q`: max_capacitance / max_fanout / max_transition violations
  1 / 0 / 7 at ss and 1 / 0 / 5 at tt and ff;
* a mechanism control with deliberately tight limits (`set_max_transition 0.001`, `set_max_capacitance 0.00001`,
  `set_max_fanout 1`): 8,384 / 3,708 / 30,928 violations at each corner.

Only the ss library-control report (`ss/picorv32.tempus_drv_lib_control.rpt`) was among the files supplied for
release; it lists the 7 transition violations and the 1 capacitance violation. The other eight reports are
described by the ledger rows only (including each report's truncated sha256), and are not published here.

These controls show how the check responds in these runs. They do not show that every checker in the project
detects every damaged input.
