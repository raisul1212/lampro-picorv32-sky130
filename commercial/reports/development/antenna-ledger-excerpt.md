# Ledger row D-191 (Magic antenna check)

Excerpt of the commercial campaign ledger (`LEDGER.md` of the project, not published whole). Fields kept: id, quantity, value, status and provenance; role, filer, model and timestamp fields are not reproduced. Cluster paths are replaced by `<DEPOT>`. Tool build strings are as recorded.

| id | quantity | value | status | provenance |
|---|---|---|---|---|
| `D-191` | picorv32 process-antenna check (magic, open checker) | clean=False, 1 violation(s), worst ratio 403.85 | MEASURED | magic antennacheck (sky130A, the open checker) over picorv32.gds sha256 06ed2f122c8ac2ba \| negative control first: the frozen known-bad stream picorv32_antenna_bad.gds sha256 2a58cabeffd9139e reported 1 violation(s), worst ratio 483.21 \| strip control: the same stream with its 1 sky130_fd_sc_hd__diode_2 instance(s) removed reported 2 violation(s), worst ratio 546.64 \| genus Version: 25.11-s095_1, built Tue Aug 12 07:59:05 PDT 2025; innovus @(#)CDS: Innovus v25.11-s102_1 (64bit) 08/27/2025 13:03 (Lin; tempus @(#)CDS: Tempus Timing Solution v23.10-p001_1 (64bit) 11/29/ |
