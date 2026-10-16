#!/usr/bin/env python3
"""Negative timing-check limits for a simulator that does not model them, by
the delayed-net construction of IEEE 1364-2005 15.5.1, done in the inputs.

OSS-CVC applies a negative $setuphold or $recrem limit as 0. A sky130 flop's
hold limit is negative (about -0.07 to -0.8 ns), so CVC's window runs up to
the clock edge where Xcelium -neg_tchk ends it |hold| before, and a data
change in that last stretch is a violation in CVC and a clean capture of the
old value in Xcelium.

The standard's construction: delay the reference by dR and the data by dD so
that every limit becomes non-negative, check the DELAYED signals against the
shifted limits, and clock the cell's state from the delayed signals. With a
reference r, data d and limits (s, h), the window (t_r - s, t_r + h) is the
same set of events as the window (t'_r - s', t'_r + h') on delayed times when
    s' = s + dR - dD,   h' = h - dR + dD.
A $recrem(R, C, recovery, removal) is the same construction with R as the
reference, C as the data, removal in the place of setup and recovery in the
place of hold: a negative recovery delays C, a negative removal delays R.

The delays follow Xcelium -neg_tchk as measured on a cluster (stock sky130 hd
models, xrun 24.03): on dfxtp (2026-10-11), and on one instance of each of the
33 sky130_fd_sc_hd families whose checks name delayed nets, under 200,000
random input changes (2026-10-12). The rule below reproduces every delay
Xcelium gave those 33 instances, 115 delayed nets, rise and fall each. Per
instance, per min/typ/max field, with a 1 ps tick, a delay per net per edge
(dly[n][rise], dly[n][fall]) is the fixed point of:
  - for a data edge e of net n, over the checks on it:
      L_e = max(0, dly[r][er] - h + tick, where that is > 0)
      U_e = min(dly[r][er] + s - tick)
    The edge's window is empty when some check on it has s + h < 0.
  - net[n] = the largest L_e over n's edges whose windows are not empty, and
    at least push[n] (below).
  - dly[n][e] = max(L_e, min(net[n], U_e)) for an edge with checks and a
    non-empty window (the hold side wins when the two cross); min(net[n],
    U_e) for an edge whose window is empty; net[n] for an edge with no check.
  - push[r] = dly[d][e] - s + tick for every check with s < 0 and a
    non-empty window, so that a
    negative setup (or removal) delays the reference past the data.
That is: one delay for every edge of a net, the largest any of its non-empty
windows needs plus a tick, unless a data edge's own setup (minus a tick) is
smaller, in which case that edge gets that. Checks the SDF gives no limit
(sky130's SET_B/RESET_B $setuphold, which has none in liberty) are left out,
as Xcelium leaves them out. One part of the rule was not exercised by the
measurement and is assumed: the tick on a lower bound from a POSITIVE hold
(dly[r] - h > 0).

When a net's rise and fall delays differ, events can cross: a fall 801 ps
late after a rise 335 ps late. Xcelium keeps them in order of arrival and an
event cancels every event of the same net due at or after it (VHDL's
transport rule); this reproduced Xcelium's delayed-net waveform exactly on the
five nets measured for it (1,630 to 1,801 events each, three of them with
crossings), and on a probe of x and z transitions. A plain intra-assignment
delay would not cancel, and a Verilog gate would swallow every pulse narrower
than its delay, so the element is
a queue (`lampro_tdly_<r>_<f>ps`). When the two delays are equal no event can
cross and the element is the plain transport delay (`lampro_tdly_<n>ps`).

An edge whose window is empty (s + h < 0) has its negative limit set to 0
before the shift, as Xcelium does (*W,SANGL2 "the negative limit will be set
to zero"; nine such edges in the measurement, every one flagged where its
zeroed window put it). A shifted limit that still comes out negative is
written as 0, which is what CVC would make of it. The map counts both.

The rest of what -neg_tchk does, as measured on the same design, and done here
in the inputs because OSS-CVC does it differently:
- A $width on a signal that has a delayed net is checked on the delayed net:
  a CLK pulse whose delayed fall came after its &&& condition went to 0 was
  not flagged, the same pulse with the condition held was.
- Conditions: every sky130 $setuphold/$recrem gives the same timestamp and
  timecheck condition (`awake`, `cond0`, ...). OSS-CVC ignores those two
  arguments, so `lib` puts the condition on both events as `&&& cond`, which
  IEEE 1364 defines to mean the same when the two are equal. Xcelium skips a
  check whose condition is x and makes one whose condition is z; OSS-CVC
  makes both. So every `&&& c` becomes `&&& lampro_c_c`, a wire that is 1
  when c is 1 or z. It matters: sky130 dfrbp declares `awake` and never
  drives it, so its `cond1 = awake && ...` is x.
- OSS-CVC matches the SECOND port of an SDF RECREM to the first argument of
  the Verilog $recrem, and applies the RECREM's first limit (recovery) to a
  data event before the reference, where IEEE 1364 and Xcelium apply
  recovery to one after it. The RECREM
  written here is therefore in CVC's port order with removal first; CVC's
  report then calls a removal violation "recovery" and the reverse.
On that design (33 families, 200,000 random input changes without
same-instant changes, OpenSTA SDF at ss 100C 1.60 V), CVC reported the 355
violations Xcelium did, each the same check at the same undelayed times.

Why cell copies and not parameters: OSS-CVC 7.00b gives the wrong value to a
parameter of a module nested in a cell when the cell is instantiated more
than three times. Six instances given 0.090 to 0.095 ns by defparam (or by a
cell parameter passed down) ran with 0.090, 0.091, 0.092, 0.090, 0.091,
0.092 (measured 2026-10-11). A delay therefore lives in a module's text: one
module per delay value, and one copy of a cell per set of delays.

  negtchk.py lib <cells.v> <out.v>
      Appends `lampro_tdly`, a zero-delay element. In each cell, each delayed
      net named by a $setuphold/$recrem is driven by an instance
      `lampro_dly_<net>` of it; the check's reference and data terminals,
      and a $width's terminal, become the delayed nets; and every condition
      is put on its events through a `lampro_c_<cond>` wire.
  negtchk.py design <cells.v> <netlist.v> <in.sdf> <out.sdf> <out_netlist.v> <variants.v> <map.tsv>
      For each instance of a cell whose checks use delayed nets: every
      SETUP/HOLD/SETUPHOLD entry becomes an edge-specific SETUPHOLD on the
      delayed nets with (s', h'), every RECOVERY/REMOVAL/RECREM entry an
      edge-specific RECREM in CVC's order, and every WIDTH on such a signal
      names its delayed net; the instance's delays (the typ
      field, as CVC selects by default) pick a copy of the cell,
      <cell>__lampro_<delays>, whose elements are the delay modules.
      variants.v holds those copies and modules. The netlist and SDF copies
      name the copy instead of the cell, and nothing else in them changes.
      map.tsv gives each delayed signal's typ rise and fall delay per
      instance, so that a report can give violations in undelayed time, and
      the number of limits set to 0.

Refuses (exit 1, naming the cell or SDF line) anything it does not model:
- a COND entry on such a cell;
- a delayed net named for two signals;
- a check whose two condition arguments differ or are not one identifier,
  or that has both &&& and a condition argument;
- an SDF entry naming a terminal, or a pair of terminals, the cell's checks
  do not have, or a reference edge other than the check's;
- an edge given a setup limit without a hold limit, or the reverse (the same
  for recovery and removal);
- a limit finer than the 1 ps tick, or delays that do not settle;
- a remodelled instance that the netlist does not name exactly once, or
  names in a declaration together with other instances, or an SDF instance
  path with a hierarchy divider in it.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cvc_report import Unreadable, instance_statements, preprocess  # noqa: E402  (the readers coverage uses)

CHECK = re.compile(r"\$(setuphold|recrem)\s*\((.*?)\)\s*;", re.S)
MODULE = re.compile(r"\bmodule\s+(\w+)(.*?)\bendmodule\b", re.S)
SPECIFY = re.compile(r"^\s*specify\b", re.M)
EVENT = re.compile(r"^\s*((?:posedge|negedge)\s+)?(\w+)(.*)$", re.S)


class Refused(Exception):
    pass


def split_args(s):
    out, depth, cur = [], 0, []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


# ---------------------------------------------------------------------------
# the cell library
# ---------------------------------------------------------------------------

def cell_checks(body):
    """[(kind, ref_edge, ref_sig, data_edge, data_sig, delayed_ref, delayed_data)]
    for one module's $setuphold/$recrem checks that name delayed nets; an edge
    is "posedge", "negedge" or None."""
    out = []
    for m in CHECK.finditer(body):
        a = [x.strip() for x in split_args(m.group(2))]
        dref = a[7] if len(a) > 7 else ""
        ddat = a[8] if len(a) > 8 else ""
        if not (dref or ddat):
            continue
        r, d = EVENT.match(a[0]), EVENT.match(a[1])
        out.append((m.group(1), (r.group(1) or "").strip() or None, r.group(2),
                    (d.group(1) or "").strip() or None, d.group(2), dref, ddat))
    return out


WIDTH = re.compile(r"\$width\s*\((.*?)\)\s*;", re.S)
COND = re.compile(r"&&&\s*(\w+)")


def cond_helper(c):
    return f"lampro_c_{c}"


def lib_module(name, body):
    checks = cell_checks(body)
    if not checks:
        return conditions_only(name, body), {}
    want = {}
    for _, _, r, _, d, dref, ddat in checks:
        for sig, dn in ((r, dref), (d, ddat)):
            if dn and want.setdefault(dn, sig) != sig:
                raise Refused(f"{name}: {dn} names both {want[dn]} and {sig}")

    def retarget(m):
        a = split_args(m.group(2))
        c1 = a[5].strip() if len(a) > 5 else ""
        c2 = a[6].strip() if len(a) > 6 else ""
        if c1 != c2:
            raise Refused(f"{name}: ${m.group(1)} with timestamp condition '{c1}' and timecheck "
                          f"condition '{c2}' is not modelled")
        if c1 and not re.fullmatch(r"\w+", c1):
            raise Refused(f"{name}: ${m.group(1)} condition '{c1}' is not one identifier")
        for i, di in ((0, 7), (1, 8)):
            dn = a[di].strip() if len(a) > di else ""
            e = EVENT.match(a[i])
            if c1 and "&&&" in e.group(3):
                raise Refused(f"{name}: ${m.group(1)} has both &&& and a condition argument")
            sig = dn or e.group(2)
            cond = f" &&& {c1}" if c1 else ""
            a[i] = f" {e.group(1) or ''}{sig}{e.group(3).rstrip()}{cond} "
        return f"${m.group(1)} ({','.join(a)});"

    body = CHECK.sub(retarget, body)
    s = SPECIFY.search(body)
    if s is None:
        raise Refused(f"{name}: delayed nets named but no specify block")
    # a $width on a signal that has a delayed net is checked on that net, as
    # Xcelium -neg_tchk checks it: a CLK pulse whose delayed fall came after
    # its &&& condition went to 0 was not flagged, the same pulse with the
    # condition held was (2026-10-12)
    delayed = {v: d for d, v in want.items()}

    def width(m):
        a = split_args(m.group(1))
        e = EVENT.match(a[0])
        if e.group(2) in delayed:
            a[0] = f" {e.group(1) or ''}{delayed[e.group(2)]}{e.group(3)}"
        return f"$width ({','.join(a)});"

    body = body[:s.start()] + WIDTH.sub(width, body[s.start():])
    bufs = "".join(f"    lampro_tdly lampro_dly_{d} (.Y({d}), .A({v})); // delayed-net model, IEEE 1364-2005 15.5.1\n"
                   for d, v in sorted(want.items()))
    body = body[:s.start()] + "\n" + bufs + body[s.start():].lstrip("\n")
    return conditions_only(name, body), want


def conditions_only(name, body):
    """Each `&&& c` in the specify block becomes `&&& lampro_c_c`, a wire that
    is 1 when c is 1 or z and 0 when c is 0 or x. Xcelium skips a check whose
    condition is x and makes one whose condition is z; OSS-CVC makes both
    (measured 2026-10-12, a $width and a $setuphold with c = 1, 0, x, z). It
    matters in sky130: dfrbp declares `awake` and never drives it, so its
    `awake` is z and its `cond1 = awake && ...` is x."""
    s = SPECIFY.search(body)
    if s is None:
        return body
    spec = body[s.start():]
    conds = sorted(set(COND.findall(spec)))
    if not conds:
        return body
    for c in conds:
        if re.search(r"\b%s\b" % re.escape(cond_helper(c)), body):
            raise Refused(f"{name}: already has a net named {cond_helper(c)}")
    spec = COND.sub(lambda m: f"&&& {cond_helper(m.group(1))}", spec)
    wires = "".join(f"    wire {cond_helper(c)} = ({c} === 1'b1) || ({c} === 1'bz); // condition as Xcelium reads it\n"
                    for c in conds)
    return body[:s.start()] + "\n" + wires + spec.lstrip("\n")


TDLY = """
`timescale 1ns/1ps
// Delayed-net element for negtchk.py (Lampro AI), zero delay. A remodelled
// instance uses a copy of its cell whose elements are lampro_tdly_<n>ps.
module lampro_tdly (Y, A);
  output Y; input A;
  reg Y;
  always @(A) Y <= A;
endmodule
"""


def tdly_module(ps):
    """A transport delay of `ps` picoseconds: every event kept, in order."""
    return (f"module lampro_tdly_{ps}ps (Y, A);\n  output Y; input A;\n  reg Y;\n"
            f"  always @(A) Y <= #({ps / 1000:.3f}) A;\nendmodule\n")


def tdly2_module(r, f):
    """A transport delay of `r` ps for a rising transition and `f` ps for a
    falling one, as Xcelium classes them (measured 2026-10-12): to 1, or 0
    to x/z, is rising; to 0, or 1 to x/z, is falling; x to z took the
    falling delay, and z to x is assumed to. An event cancels every pending
    event due at or after it. Pending events are a queue whose due times
    increase from the oldest to the newest, so cancelling is popping the
    newest. The queue holds at most max(r, f) + 1 events at 1 ps resolution;
    a fuller one stops the run rather than drop an event."""
    n = max(r, f) + 2
    return f"""`timescale 1ps/1ps
module lampro_tdly_{r}_{f}ps (Y, A);
  output Y; input A;
  reg Y, p;
  reg v [0:{n - 1}];
  time due [0:{n - 1}];
  integer head, tail, seq, tok;
  time t;
  initial begin head = 0; tail = 0; seq = 0; tok = 0; p = 1'bx; end
  always @(A) begin
    t = $time + ((A === 1'b1 || (A !== 1'b0 && p === 1'b0)) ? {r} : {f});
    p = A;
    while (tail != head && due[(tail - 1) % {n}] >= t) tail = tail - 1;
    if (tail - head >= {n}) begin
      $display("LAMPRO_TDLY_OVERFLOW %m at %0t", $time); $finish;
    end
    v[tail % {n}] = A; due[tail % {n}] = t; tail = tail + 1;
    seq = seq + 1;
    tok <= #(t - $time) seq;
  end
  always @(tok)
    while (head != tail && due[head % {n}] <= $time) begin
      Y <= v[head % {n}]; head = head + 1;
      // keep head below n and tail below 2n, so neither overflows;
      // tail >= head, so tail stays >= 0
      if (head >= {n}) begin head = head - {n}; tail = tail - {n}; end
    end
endmodule
`timescale 1ns/1ps
"""


def lib(text):
    """(new text, {cell: {signal: delayed net}})."""
    out, pos, cells = [], 0, {}
    for m in MODULE.finditer(text):
        out.append(text[pos:m.start()])
        body, want = lib_module(m.group(1), m.group(0))
        out.append(body)
        if want:
            cells[m.group(1)] = {v: d for d, v in want.items()}
        pos = m.end()
    out.append(text[pos:])
    if cells:
        out.append(TDLY)
    return "".join(out), cells


def lib_checks(text):
    """{cell: [(kind, ref_edge, ref, data_edge, data)]} as cell_checks reads them."""
    return {m.group(1): [c[:5] for c in cell_checks(m.group(0))]
            for m in MODULE.finditer(text) if cell_checks(m.group(0))}


# ---------------------------------------------------------------------------
# the delays
# ---------------------------------------------------------------------------

TICK = 1000      # fs: one tick at the 1 ps precision of the runs (see the docstring)
EDGES = ("posedge", "negedge")


def solve(checks, where):
    """{net: {edge: delay}} in fs for one instance and one field. checks:
    [(ref, ref_edge, data, data_edge, s, h)] in fs. The rule is the
    docstring's, iterated from zero to its fixed point."""
    nets = sorted({c[0] for c in checks} | {c[2] for c in checks})
    dly = {n: {e: 0 for e in EDGES} for n in nets}
    on = {(n, e): [c for c in checks if c[2] == n and c[3] == e] for n in nets for e in EDGES}
    for _ in range(4 * len(nets) + 8):
        before = {n: dict(v) for n, v in dly.items()}
        push = dict.fromkeys(nets, 0)
        for r, er, d, de, s, h in checks:
            if s < 0 and s + h >= 0:
                # an empty window's negative limit is set to 0 first (sdf()),
                # so it pushes nothing
                push[r] = max(push[r], dly[d][de] - s + TICK)
        for n in nets:
            low, up, empty = {}, {}, {}
            for e in EDGES:
                cs = on[(n, e)]
                low[e] = max([0] + [dly[r][er] - h + TICK for r, er, _, _, s, h in cs if dly[r][er] - h > 0])
                up[e] = min([dly[r][er] + s - TICK for r, er, _, _, s, h in cs], default=None)
                empty[e] = any(s + h < 0 for *_, s, h in cs)
            net = max([push[n]] + [low[e] for e in EDGES if on[(n, e)] and not empty[e]])
            for e in EDGES:
                if not on[(n, e)]:
                    v = net
                elif empty[e]:
                    v = max(0, min(net, up[e]))
                else:
                    v = max(low[e], min(net, up[e]))
                dly[n][e] = max(v, push[n])
        if dly == before:
            return dly
    raise Refused(f"{where}: the delays did not settle (windows that need a reference delayed past its data)")


# ---------------------------------------------------------------------------
# the SDF file
# ---------------------------------------------------------------------------

TRIPLE = r"\(\s*(-?[\d.]*)\s*:\s*(-?[\d.]*)\s*:\s*(-?[\d.]*)\s*\)"
TERM = r"(?:\((posedge|negedge)\s+(\w+)\)|(\w+))"
KINDS = "SETUPHOLD|SETUP|HOLD|RECREM|RECOVERY|REMOVAL"
ENTRY = re.compile(r"^(\s*)\((%s)\s+%s\s+%s\s+%s(?:\s+%s)?\s*\)\s*$" % (KINDS, TERM, TERM, TRIPLE, TRIPLE))
FAMILY = {"SETUPHOLD": "setuphold", "SETUP": "setuphold", "HOLD": "setuphold",
          "RECREM": "recrem", "RECOVERY": "recrem", "REMOVAL": "recrem"}
OTHER_TCHK = re.compile(r"\((COND)\b")
WIDTH_ENTRY = re.compile(r"^\s*\(WIDTH\s+(?:\((?:posedge|negedge)\s+(\w+)\)|(\w+))")


def _fs(x, where):
    if x in ("", None):
        return 0
    v = float(x) * 1e6
    if abs(v - round(v / TICK) * TICK) > 1e-3:
        raise Refused(f"{where}: limit {x} is finer than the 1 ps tick")
    return int(round(v))


def _fmt(v):
    """fs as ns text."""
    v = v / 1e6
    return f"{v:.6f}".rstrip("0").rstrip(".") if v else "0"


def sdf(text, cells, checks_of):
    """(lines, edits, map rows, delays) for design(): the SDF's lines; the
    edits {line index: replacement lines} that remodel each instance's
    checks; the map.tsv rows; and {instance: (cell, {delayed net: (rise ps,
    fall ps)}, index of its CELLTYPE line)}, from which design() names the
    cell copies and renames each CELLTYPE. cells is lib()'s, checks_of
    lib_checks()'s."""
    lines = text.splitlines(True)
    div = "/" if re.search(r"\(DIVIDER\s+/\s*\)", text) else "."
    mapping = []
    cell_re = re.compile(r'\(CELLTYPE\s+"([^"]+)"\)')
    inst_re = re.compile(r"\(INSTANCE\s*([^)]*?)\s*\)")
    blocks = []                                  # (start, end, celltype, instance)
    starts = [n for n, l in enumerate(lines) if re.match(r"^\s*\(CELL\b", l)]
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else len(lines)
        head = "".join(lines[st:min(st + 4, en)])
        ct, ins = cell_re.search(head), inst_re.search(head)
        blocks.append((st, en, ct.group(1) if ct else "", ins.group(1) if ins else ""))
    edits, delays = {}, {}
    for st, en, ct, ins in blocks:
        if ct not in cells:
            continue
        sig2d = cells[ct]
        # the cell's $width on such a signal is on its delayed net (lib)
        for n in range(st, en):
            w = WIDTH_ENTRY.match(lines[n])
            g = (1 if w.group(1) else 2) if w else 0
            if w and w.group(g) in sig2d:
                edits[n] = [lines[n][:w.start(g)] + sig2d[w.group(g)] + lines[n][w.end(g):]]
        known = {}                             # (family, ref, data) -> {data edge or None: ref edge}
        for kind, rer, r, de, d in checks_of[ct]:
            known.setdefault((kind, r, d), {})[de] = rer
        lim = {}                                 # (family, ref, ref_edge, data, data_edge) -> [s3, h3]
        have = {}                                # which halves the SDF gave
        idx = []
        for n in range(st, en):
            l = lines[n]
            where = f"SDF line {n + 1}"
            if OTHER_TCHK.search(l):
                raise Refused(f"{where}: {OTHER_TCHK.search(l).group(1)} on {ct} not modelled")
            m = ENTRY.match(l)
            if not m:
                if re.search(r"\((%s)\b" % KINDS, l):
                    raise Refused(f"{where}: timing check entry not in the form read here")
                continue
            g = m.groups()
            kind = g[1]
            fam = FAMILY[kind]
            e1, p1 = (g[2], g[3]) if g[3] else (None, g[4])
            e2, p2 = (g[5], g[6]) if g[6] else (None, g[7])
            # SDF names a setup/hold pair data first; a recovery/removal pair
            # in the order of the Verilog $recrem (CVC reads it so, v_sdf.c)
            if fam == "setuphold":
                (d_edge, d), (r_edge, r) = (e1, p1), (e2, p2)
            else:
                (r_edge, r), (d_edge, d) = (e1, p1), (e2, p2)
            for sig in (d, r):
                if sig not in sig2d:
                    raise Refused(f"{where}: {ct} has no delayed net for {sig}")
            if (fam, r, d) not in known:
                raise Refused(f"{where}: {ct} has no ${fam} on reference {r} and data {d}")
            v1 = [_fs(x, where) for x in g[8:11]]
            v2 = [_fs(x, where) for x in g[11:14]] if g[11] is not None else None
            for e in [d_edge] if d_edge else list(EDGES):
                cell_rer = known[(fam, r, d)].get(e, known[(fam, r, d)].get(None, "missing"))
                if cell_rer == "missing":
                    raise Refused(f"{where}: {ct} has no ${fam} on {e} {d}")
                if cell_rer is None or (r_edge and r_edge != cell_rer):
                    raise Refused(f"{where}: {ct} ${fam} on {d} has reference edge {cell_rer}, "
                                  f"the SDF {r_edge or 'none'}")
                key = (fam, r, cell_rer, d, e)
                cur = lim.setdefault(key, [[0] * 3, [0] * 3])
                got = have.setdefault(key, set())
                if kind in ("SETUP", "REMOVAL"):
                    cur[0] = v1
                    got.add("s")
                elif kind in ("HOLD", "RECOVERY"):
                    cur[1] = v1
                    got.add("h")
                elif kind == "SETUPHOLD":
                    cur[0], cur[1] = v1, v2
                    got.update("sh")
                else:                            # RECREM: recovery, then removal
                    cur[1], cur[0] = v1, v2
                    got.update("sh")
            idx.append(n)
        if not lim:
            continue
        # a half the SDF did not give would be written as 0 and then pass
        # coverage as a check "with a limit": refuse instead
        for key, got in sorted(have.items(), key=str):
            if got != {"s", "h"}:
                names = ("setup", "hold") if key[0] == "setuphold" else ("removal", "recovery")
                gave, lacks = (names[0], names[1]) if "s" in got else (names[1], names[0])
                raise Refused(f"{ct} {ins}: {key[4]} {key[3]} has a {gave} limit and no {lacks} limit in the SDF")
        dl = [solve([(r, rer, d, e, s3[f], h3[f]) for (fam, r, rer, d, e), (s3, h3) in lim.items()],
                    f"{ct} {ins}") for f in range(3)]
        ind = re.match(r"^(\s*)", lines[idx[0]]).group(1)
        new, clamped, zeroed = [], 0, 0
        for (fam, r, rer, d, e), (s3, h3) in sorted(lim.items(), key=lambda kv: (kv[0][3], kv[0][4], kv[0][0])):
            s2, h2 = [], []
            for f in range(3):
                dR, dD = dl[f][r][rer], dl[f][d][e]
                s, h = s3[f], h3[f]
                if s + h < 0:
                    # an empty window: Xcelium sets its negative limit to 0
                    # before the shift (*W,SANGL2, 2026-10-12)
                    s, h = max(s, 0), max(h, 0)
                    zeroed += 1
                for out, v in ((s2, s + dR - dD), (h2, h - dR + dD)):
                    clamped += v < 0
                    out.append(max(0, v))
            rt, dt = f"({rer} {sig2d[r]})", f"({e} {sig2d[d]})"
            if fam == "setuphold":
                new.append(f"{ind}(SETUPHOLD {dt} {rt} ({':'.join(_fmt(x) for x in s2)}) "
                           f"({':'.join(_fmt(x) for x in h2)}))\n")
            else:
                # OSS-CVC matches the SECOND port of an SDF RECREM (and of a
                # RECOVERY or REMOVAL) to the first argument of the Verilog
                # $recrem (v_sdf.c, bld_match_tchk(ctmdp, &dattct, &reftct,
                # ...)); Xcelium and OpenSTA put the $recrem's first argument
                # first. This SDF is CVC's alone, so it is written in CVC's
                # order, and as one RECREM: CVC tries a RECOVERY or REMOVAL as
                # a $recovery/$removal first and logs an ERROR for each
                # before it finds the $recrem. CVC's $recrem is mirrored as
                # well: it applies its first limit ("recovery") to a data
                # event BEFORE the reference and its second ("removal") to
                # one after, where IEEE 1364 and Xcelium apply removal before
                # and recovery after (measured 2026-10-12: CVC flagged a CLK
                # 30 ps after RESET_B against a 149 ps "removal"). So the
                # removal limit goes first and the recovery limit second,
                # and CVC's report names each the other's name.
                new.append(f"{ind}(RECREM {dt} {rt} ({':'.join(_fmt(x) for x in s2)}) "
                           f"({':'.join(_fmt(x) for x in h2)}))\n")
        edits[idx[0]] = new
        for n in idx[1:]:
            edits[n] = []
        if re.search(r"(?<!\\)" + re.escape(div), ins):
            raise Refused(f"SDF instance {ins}: a hierarchical path is not rewritten here")
        # the delays of the typ field (CVC's default selection), in ps
        typ = dl[1]
        dly = {sig2d[n]: (typ[n]["posedge"] // TICK, typ[n]["negedge"] // TICK)
               for n in sorted(typ) if typ[n]["posedge"] or typ[n]["negedge"]}
        ctl = next(n for n in range(st, en) if cell_re.search(lines[n]))
        delays[ins] = (ct, dly, ctl)
        for n in sorted(typ):
            mapping.append((ins, n, _fmt(typ[n]["posedge"]), _fmt(typ[n]["negedge"])))
        if zeroed:
            mapping.append((ins, "(empty windows, negative limit set to 0)", str(zeroed), ""))
        if clamped:
            mapping.append((ins, "(shifted limits below 0, written as 0)", str(clamped), ""))
    return lines, edits, mapping, delays


def _unescape(s):
    return re.sub(r"\\(.)", r"\1", s.strip())


def _short(n):
    return n[:-len("_delayed")] if n.endswith("_delayed") else n


def variant_name(cell, dly):
    return cell + "__lampro_" + "_".join(f"{_short(n)}{r}" if r == f else f"{_short(n)}{r}r{f}f"
                                        for n, (r, f) in sorted(dly.items()))


def delay_module(r, f):
    return f"lampro_tdly_{r}ps" if r == f else f"lampro_tdly_{r}_{f}ps"


def active_modules(lib_text, names):
    """{name: text} of each named module as CVC reads it (USE_POWER_PINS)."""
    act = preprocess(lib_text.splitlines(), ("USE_POWER_PINS",))
    out, cur, buf = {}, None, []
    for _, line in act:
        m = re.match(r"\s*module\s+([\w$]+)", line)
        if m and m.group(1) in names:
            cur, buf = m.group(1), []
        if cur:
            buf.append(line)
            if re.match(r"\s*endmodule\b", line):
                out[cur] = "\n".join(buf) + "\n"
                cur = None
    return out


def design(lib_text, netlist_text, sdf_text):
    """(SDF, netlist, variants, map rows) for one design; see the docstring."""
    base, cells = lib(lib_text)
    lines, edits, mapping, delays = sdf(sdf_text, cells, lib_checks(lib_text))
    # the netlist: each remodelled instance named exactly once, by its cell
    found = {}
    try:
        statements = instance_statements(netlist_text, cells)
    except Unreadable as e:
        raise Refused(str(e))
    for cell, cs, ce, insts in statements:
        for name, _, _ in insts:
            found.setdefault(name, []).append((cell, cs, ce, len(insts)))
    variants, wanted = {}, {}
    for ins, (ct, dly, _) in delays.items():
        if not dly:
            continue
        hits = found.get(_unescape(ins), [])
        if len(hits) != 1 or hits[0][0] != ct:
            raise Refused(f"SDF instance {ins} ({ct}) is named {len(hits)} times in the netlist "
                          f"{'as a ' + hits[0][0] if hits else ''}".rstrip())
        cell, cs, ce, n_in_stmt = hits[0]
        if n_in_stmt > 1:
            # renaming the cell would rename every instance the statement declares
            raise Refused(f"SDF instance {ins} ({ct}) is declared in one statement with "
                          f"{n_in_stmt - 1} other instance(s); split the declaration")
        v = variant_name(ct, dly)
        variants[v] = (ct, dly)
        wanted[cs] = (ce, v)
    net_out, pos = [], 0
    for start in sorted(wanted):
        end, v = wanted[start]
        net_out += [netlist_text[pos:start], v]
        pos = end
    net_out.append(netlist_text[pos:])
    # the SDF: CELLTYPE of each remodelled instance names its copy
    for ins, (ct, dly, ctl) in delays.items():
        if dly:
            edits.setdefault(ctl, [lines[ctl].replace(f'"{ct}"', f'"{variant_name(ct, dly)}"')])
    sdf_out = "".join(x for n, l in enumerate(lines) for x in edits.get(n, [l]))
    # the copies and the delay modules
    mods = active_modules(base, {ct for ct, _ in variants.values()})
    out = ["`timescale 1ns/1ps\n// negtchk.py: one copy of a cell per set of delays, and one delay module per value\n"]
    for r, f in sorted({rf for _, dly in variants.values() for rf in dly.values()}):
        out.append(tdly_module(r) if r == f else tdly2_module(r, f))
    for v, (ct, dly) in sorted(variants.items()):
        text = re.sub(r"(\bmodule\s+)%s\b" % re.escape(ct), r"\g<1>" + v, mods[ct], count=1)
        for net, (r, f) in dly.items():
            a = f"lampro_tdly lampro_dly_{net} ("
            if text.count(a) != 1:
                raise Refused(f"{ct}: element for {net} not found once in the cell text")
            text = text.replace(a, f"{delay_module(r, f)} lampro_dly_{net} (")
        out.append("`celldefine\n`default_nettype none\n" + text + "`default_nettype wire\n`endcelldefine\n")
    return sdf_out, "".join(net_out), "".join(out), mapping


def main(argv):
    try:
        if len(argv) == 4 and argv[1] == "lib":
            with open(argv[2], encoding="utf-8") as f:
                text, cells = lib(f.read())
            with open(argv[3], "w", encoding="utf-8") as f:
                f.write(text)
            print(f"negtchk lib: {sum(len(v) for v in cells.values())} delayed nets in {len(cells)} cells -> {argv[3]}")
            return 0
        if len(argv) == 9 and argv[1] == "design":
            lib_p, net_p, sdf_p, sdf_o, net_o, var_o, map_o = argv[2:9]
            with open(lib_p, encoding="utf-8") as f:
                lib_text = f.read()
            with open(net_p, encoding="utf-8", errors="replace") as f:
                net_text = f.read()
            with open(sdf_p, encoding="utf-8", errors="replace") as f:
                sdf_text = f.read()
            sdf_out, net_out, var_out, mapping = design(lib_text, net_text, sdf_text)
            for path, text in ((sdf_o, sdf_out), (net_o, net_out), (var_o, var_out)):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            with open(map_o, "w", encoding="utf-8") as f:
                f.write("instance\tsignal\trise_typ_ns\tfall_typ_ns\n")
                f.writelines("\t".join(r) + "\n" for r in mapping)
            print(f"negtchk design: {len({r[0] for r in mapping})} instances remodelled, "
                  f"{var_out.count('endmodule')} variant and delay modules -> {var_o}")
            return 0
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"negtchk: {e}", file=sys.stderr)
        return 2
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
