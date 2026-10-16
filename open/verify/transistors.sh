#!/usr/bin/env bash
# Transistor count from layout/picorv32.def and the PDK cell SPICE. Expect 183139.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
invalidate transistors || { echo "transistors: could not clear the earlier result" >&2; exit 2; }
out="$(python3 "$PKG/verify/transistors.py" "${EXPECTED_TRANSISTORS:-183139}")"
prc=$?
if [ $prc != 0 ] && [ "${out%% *}" != FAIL ]; then result transistors FAIL "transistors.py exited with status $prc"; exit 2; fi
st="${out%% *}"; facts="${out#* }"
if [ "$st" = PASS ]; then result transistors PASS "$facts"; else result transistors FAIL "$facts"; exit 1; fi
