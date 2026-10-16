# Common settings for the verification scripts. Source, do not execute.
# Required: PDK_ROOT = the open_pdks "share/pdk" directory (contains sky130A/).
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${PDK_ROOT:?PDK_ROOT must point at the open_pdks share/pdk directory}"
export PKG PDK_ROOT
export PDKPATH="$PDK_ROOT/sky130A"
export TOP=picorv32
export REPORTS="${REPORTS:-$PKG/reports}"
mkdir -p "$REPORTS"
# Strip machine-specific absolute paths from files (reports are shipped).
clean_paths() { python3 "$PKG/verify/util.py" clean "$@"; }
# Write the one-line verdict for a check: result <name> PASS|FAIL "<facts>"
result() { printf '%s %s\n' "$2" "$(printf '%s' "$3" | tr '\n' ' ')" > "$REPORTS/$1.result.tmp" && mv "$REPORTS/$1.result.tmp" "$REPORTS/$1.result"; echo "$1: $2 $3"; }
# Remove the previous result files of a check before it runs, so that a stale PASS can never be read
# as this run's verdict. Fails (returns 1) if a file cannot be removed.
invalidate() { local n; for n in "$@"; do rm -f "$REPORTS/$n.result" || return 1; [ ! -e "$REPORTS/$n.result" ] || return 1; done; }
