# Historical frozen-evidence manifests

Each `<run>/SHA256SUMS.original` is the checksum manifest that was written when that run's inputs and outputs were
frozen. They hash the original historical files, including files that are not distributed in this repository (for
example the project ledger, the Conformal map files, layouts and logs); the files themselves are not here, so these
manifests cannot be verified against this repository.

`reconstruction.tsv` gives the number of entries in each manifest: 4, 11, 9, 9, 16, 6, 11 and 9, which sum to 75
entries (66 in the six implementation and verification sets plus the Voltus set, and 9 in the Xcelium set). This
total is a reconstruction made on 16 October 2026 by counting the lines of the eight manifests; the project did not
state a total of frozen evidence files before. It counts manifest entries, not distinct contents: the eight manifests
hold 60 distinct sha256 values, because the same input file appears in more than one set.
`verification-2026-10-16.md` records the checksum check made on the original files.

Scopes, kept separate: (1) the package manifests `commercial/SHA256SUMS` and `open/SHA256SUMS` list the 33 files outside
`reports/` of each package; (2) `reports/EVIDENCE_SHA256SUMS` lists the files released under `reports/`, including these
manifest copies and the scrubbed evidence, whose hashes differ from the hashes of the originals; (3) the historical
manifests here describe the original, unscrubbed files; (4) `tests/test_verify_failures.py` is the new offline test of the
verification scripts' failure handling.
