# Historical antenna check (commercial development run)

`antenna_43898126.log` is the Magic antenna-check log of run 43898126; line 1151 reads
`Effective antenna ratio 403.853 > limit 400`. The ledger row D-191 (`antenna-ledger-excerpt.md`) records the same
result: 1 violation, worst ratio 403.85, with a known-bad control that reported 1 violation (worst ratio 483.21) and
a strip control that reported 2 violations (worst ratio 546.64).

This is a development-run result, not the check of the shipped layout (`../antenna_magic.log`, 0 violations).
The other numerical examples in the development narrative of the documents (fanout, clock-buffer, insertion-delay,
slack and spacing figures, and the repair to 96 % of the limit) have no located report and are withdrawn.
