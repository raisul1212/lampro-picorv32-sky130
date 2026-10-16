#!/usr/bin/env python3
"""Read back what a CVC gate-level run actually did, for sim_tchk.sh.

  cvc_report.py coverage <design.sdf> <sdf.log> <netlist.v> <scope> <cells.v>...
      Two questions, both answered from CVC's own +sdfverbose trace.
      1. Was every entry in the SDF file applied, to the instance it names?
         A trace line counts only if it names this SDF file, and the instance
         it reports is the instance of the SDF CELL the entry sits in. An
         INTERCONNECT whose values are all zero is the one allowed gap,
         because CVC skips zero MIPDs on purpose.
      2. Did every timing check in the design get its limits? The expected
         set comes from the netlist and the library, not from the SDF: every
         instance of a cell whose model (as CVC reads it, with
         USE_POWER_PINS) has timing checks, times every limit of every one of
         those checks (a $setuphold's setup and its hold count separately),
         including each instance of a declaration that names several.
         An SDF that leaves out a flop, or one edge of a flop, leaves those
         checks at their library limits (0 in sky130), and that fails here.
         A design with no timing checks at all is refused, because a gate
         that measures nothing passes on nothing.
      <scope> is the hierarchical name the testbench gives the design (for
      example tb.uut); CVC's trace names instances under it. Every library
      file CVC compiled is given, and a check is known by its file and line.

  cvc_report.py run <sim.log>
      Timing violations by kind and instance, and the testbench's RESULT and
      VERDICT lines.

Prints key=value lines. Exit 0 when coverage holds (coverage) or the log was
read (run), 1 when coverage fails, 2 on bad usage or input that cannot be read.

Why a coverage read-back at all: with stock OSS-CVC the commercial build's
SDF stopped annotating at the first port named SUM (an SDF keyword), at line
109,355 of 124,187, so 40,636 of the 50,696 path delays Xcelium applies were
set, and the simulation still printed PASS. A PASS is evidence only for the
delays that were applied, and only for checks that were given limits.

CVC traces by SDF line, so the read-back needs one entry per line. A file
with two entries on a line is refused (exit 2) rather than half-counted.
CVC prints annotated values rounded to whole ns, so limit values are not
compared here; the self-test probes in sim_tchk.sh check them.
"""
import re
import sys

TRACE = re.compile(r"^\s*SDF \*\*(.+?)\((\d+)\): \((IOPATH|INTERCONNECT|DEVICE|TIMINGCHECK)\b(.*)$")
TCHK_FORMS = ("SETUPHOLD", "SETUP", "HOLD", "RECREM", "RECOVERY", "REMOVAL",
              "WIDTH", "PERIOD", "SKEW", "NOCHANGE")
FORM = re.compile(r"\((IOPATH|INTERCONNECT|DEVICE|%s)\b" % "|".join(TCHK_FORMS))
VALUE = re.compile(r"\(\s*(-?[\d.]*)\s*:\s*(-?[\d.]*)\s*:\s*(-?[\d.]*)\s*\)|\(\s*(-?[\d.]+)\s*\)")
VIOL = re.compile(r"\[566\] timing violation in (.+?) \(diff\. (-?\d+) ps\)")
KIND = re.compile(r"^\s*(\$\w+|(?:setup|hold)\(of setuphold\)|(?:recovery|removal)\(of recrem\))")
# " SETUPHOLD limit set to", " SETUPHOLD 2nd limit set to",
# " HOLD matched to $setuphold limit set to", " WIDTH limit set to"
LIMIT = re.compile(r"\s*(\w+)(?: matched to \$(\w+))? (2nd )?limit set to")
TCHK_STMT = re.compile(r"^\s*\$(setuphold|setup|hold|width|recrem|recovery|removal|period|"
                       r"skew|nochange|fullskew|timeskew)\s*\(")


class Unreadable(Exception):
    pass


# ---------------------------------------------------------------------------
# the SDF file
# ---------------------------------------------------------------------------

def _base(path):
    """The file name of a path written with / or \\ (a run on Windows passes the
    latter; CVC's trace uses the former)."""
    return re.split(r"[\\/]", path)[-1]


def _unescape(s):
    return re.sub(r"\\(.)", r"\1", s.strip())


def _norm(inst, scope=""):
    """An instance name as CVC or the SDF prints it -> plain text."""
    s = inst.strip()
    if scope and s.startswith(scope + "."):
        s = s[len(scope) + 1:]
    return s.replace("\\", "").strip()


def sdf_entries(lines):
    """({kind: {line number: (text, instance)}}, divider).

    The instance of an INTERCONNECT entry is its destination's instance."""
    div = "."
    for l in lines[:40]:
        m = re.search(r"\(DIVIDER\s+(\S)\s*\)", l)
        if m:
            div = m.group(1)
    out = {"IOPATH": {}, "INTERCONNECT": {}, "DEVICE": {}, "TIMINGCHECK": {}}
    inst = ""
    for n, line in enumerate(lines, 1):
        m = re.search(r"\(INSTANCE\s*([^)]*?)\s*\)", line)
        if m:
            inst = _unescape(m.group(1))
        found = FORM.findall(line)
        if len(found) > 1:
            raise Unreadable(f"SDF line {n} holds {len(found)} entries; coverage is read per line")
        if not found:
            continue
        kind = found[0] if found[0] in ("IOPATH", "INTERCONNECT", "DEVICE") else "TIMINGCHECK"
        where = inst
        if kind == "INTERCONNECT":
            toks = re.findall(r"(?:\\.|[^\s()])+", line.split("INTERCONNECT", 1)[1])
            dst = _unescape(toks[1]) if len(toks) > 1 else ""
            where = dst.rsplit(div, 1)[0] if div in dst else ""
        out[kind][n] = (line, where)
    return out, div


def all_zero(line):
    vals = [v for m in VALUE.finditer(line) for v in m.groups() if v]
    return bool(vals) and all(float(v) == 0.0 for v in vals)


def trace_instance(kind, rest, div="."):
    """The instance a trace line reports. A DEVICE trace names the cell and
    the gate inside it; the SDF names the gate as <cell><divider><gate>."""
    if kind == "INTERCONNECT":
        m = re.search(r"\(in (.+?) type \S+\)", rest)
        return m.group(1) if m else ""
    m = re.search(r" in (.+?)\([\w$]+\)(?: at \*\*.+\(\d+\))?\s*$", rest)
    if not m:
        return ""
    if kind == "DEVICE":
        g = rest.split()
        return m.group(1) + div + g[1] if len(g) > 1 else ""
    return m.group(1)


# ---------------------------------------------------------------------------
# the expected checks: library models x netlist instances
# ---------------------------------------------------------------------------

def preprocess(lines, defines):
    """Active (line number, text) of a Verilog file under `define/`ifdef."""
    defs, stack, out = set(defines), [], []
    for n, line in enumerate(lines, 1):
        s = line.strip()
        m = re.match(r"`(ifdef|ifndef)\s+(\w+)", s)
        if m:
            parent = all(x[0] for x in stack)
            cond = (m.group(2) in defs) == (m.group(1) == "ifdef")
            stack.append((cond and parent, cond, parent))
            continue
        if s.startswith("`else"):
            _, taken, parent = stack[-1]
            stack[-1] = ((not taken) and parent, True, parent)
            continue
        if s.startswith("`endif"):
            stack.pop()
            continue
        if s.startswith("`elsif"):
            raise Unreadable(f"`elsif at line {n} is not read here")
        if stack and not stack[-1][0]:
            continue
        m = re.match(r"`define\s+(\w+)", s)
        if m:
            defs.add(m.group(1))
        out.append((n, line))
    return out


TWO_LIMITS = ("setuphold", "recrem")


def model_checks(lib_lines, defines=("USE_POWER_PINS",), fname=""):
    """{module: [(file, line, limit)]} for every limit of every timing-check
    statement, as CVC reads it. $setuphold and $recrem have two limits (1 and
    2: setup and hold, recovery and removal), every other check one. Each is
    counted on its own."""
    checks, cur = {}, None
    for n, line in preprocess(lib_lines, defines):
        m = re.match(r"\s*module\s+([\w$]+)", line)
        if m:
            cur = m.group(1)
            checks.setdefault(cur, [])
            continue
        if re.match(r"\s*endmodule\b", line):
            cur = None
            continue
        t = TCHK_STMT.match(line)
        if cur and t:
            checks[cur] += [(fname, n, part) for part in ((1, 2) if t.group(1) in TWO_LIMITS else (1,))]
    return {k: v for k, v in checks.items() if v}


def mask(text):
    """The text with every comment (// and /* */) and attribute ((* *)) blanked
    to spaces, newlines kept, so every offset still points at the same place in
    the source. Escaped identifiers (\name followed by white space) are copied
    as they are, whatever they contain. An unterminated block comment or
    attribute is refused."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\":                                  # escaped identifier
            while i < n and not text[i].isspace():
                i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                raise Unreadable(f"unterminated /* comment at line {text.count(chr(10), 0, i) + 1} of the netlist")
            j += 2
        elif text.startswith("(*", i) and not text.startswith("(*)", i):
            j = text.find("*)", i + 2)
            if j < 0:
                raise Unreadable(f"unterminated (* attribute at line {text.count(chr(10), 0, i) + 1} of the netlist")
            j += 2
        else:
            i += 1
            continue
        for k in range(i, j):
            if out[k] != "\n":
                out[k] = " "
        i = j
    return "".join(out)


def _skip_ws(text, i):
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def _close(text, i):
    """Index just past the parenthesis that closes the one at text[i], or
    None. A declaration's port list ends at its ';', so the search stops there."""
    depth = 0
    for k in range(i, len(text)):
        if text[k] == "(":
            depth += 1
        elif text[k] == ")":
            depth -= 1
            if depth == 0:
                return k + 1
        elif text[k] == ";":
            return None
    return None


NAME = re.compile(r"\\\S+|[A-Za-z_][\w$]*")


def instance_statements(text, cells):
    """[(cell, cell start, cell end, [(instance, start, end), ...])] for each
    instantiation of a cell in `cells`. One statement may declare several
    instances: `cell a (...), b (...);`.

    Fails closed: comments and attributes are
    masked first, and every statement must parse, instance by instance, to
    its terminating `;`. A statement with anything left over is refused by
    name, rather than accepted for the prefix that parsed."""
    if not cells:
        return []
    t = mask(text)
    pat = re.compile(r"(?<![\w$\\])(%s)(?=[\s#])" %
                     "|".join(re.escape(c) for c in sorted(cells, key=len, reverse=True)))
    out = []
    for m in pat.finditer(t):
        before = t[max(0, m.start() - 64):m.start()].rstrip()   # a window: the whole prefix is quadratic
        if re.search(r"\b(module|macromodule)$", before):
            continue                                   # a definition, not an instance

        def refuse(why, got):
            line = t.count("\n", 0, m.start()) + 1
            raise Unreadable(f"netlist line {line}: {m.group(1)} declaration {why} "
                             f"(instances read so far: {[g[0] for g in got] or 'none'})")
        i = _skip_ws(t, m.end())
        if t.startswith("#", i):
            i = _skip_ws(t, i + 1)
            if not t.startswith("(", i):
                refuse("has '#' without a parameter list", [])
            k = _close(t, i)
            if k is None:
                refuse("has an unbalanced parameter list", [])
            i = _skip_ws(t, k)
        insts = []
        while True:
            nm = NAME.match(t, i)
            if not nm:
                refuse(f"has {t[i:i + 20]!r} where an instance name should be", insts)
            j = _skip_ws(t, nm.end())
            if not t.startswith("(", j):
                refuse(f"has no port list after {nm.group(0)!r}", insts)
            k = _close(t, j)
            if k is None:
                refuse(f"has an unbalanced port list for {nm.group(0)!r}", insts)
            insts.append((nm.group(0).lstrip("\\"), nm.start(), k))
            k = _skip_ws(t, k)
            if t.startswith(";", k):
                break
            if not t.startswith(",", k):
                refuse(f"has {t[k:k + 20]!r} where ',' or ';' should be", insts)
            i = _skip_ws(t, k + 1)
        out.append((m.group(1), m.start(1), m.end(1), insts))
    return out


def netlist_instances(text, cells):
    """[(cell, instance)] for every instance of a cell in `cells`."""
    return [(cell, name) for cell, _, _, insts in instance_statements(text, cells) for name, _, _ in insts]


def expected_checks(netlist_text, libs):
    """{(instance, file, line, limit)}; libs is [(file name, lines)]."""
    model = {}
    for fname, lines in libs:
        model.update(model_checks(lines, fname=_base(fname)))
    return {(inst,) + fl for cell, inst in netlist_instances(netlist_text, model) for fl in model[cell]}


# ---------------------------------------------------------------------------
# coverage
# ---------------------------------------------------------------------------

def coverage(sdf_lines, sdf_name, log_lines, expected, scope):
    if not expected:
        raise Unreadable("the design has no timing checks: there is nothing for this gate to measure")
    entries, div = sdf_entries(sdf_lines)
    traced = {k: set() for k in entries}
    got = set()
    errors = foreign = misplaced = 0
    for line in log_lines:
        if " ERROR** " in line:
            errors += 1
        m = TRACE.match(line)
        if not m:
            continue
        fname, n, kind, rest = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        if _base(fname) != _base(sdf_name):
            foreign += 1
            continue
        inst = _norm(trace_instance(kind, rest, div), scope)
        ent = entries[kind].get(n)
        if ent is None or _norm(ent[1]) != inst:
            misplaced += 1
            continue
        traced[kind].add(n)
        if kind == "TIMINGCHECK":
            ln = re.search(r" at \*\*(.+)\((\d+)\)\s*$", rest)
            lim = LIMIT.match(rest)
            if ln and lim:
                form, matched, second = lim.groups()
                part = 2 if second or (matched in TWO_LIMITS and form in ("HOLD", "REMOVAL")) else 1
                got.add((inst, _base(ln.group(1)), int(ln.group(2)), part))
    rows = [f"sdf_errors={errors}", f"traces_from_other_files={foreign}",
            f"traces_not_on_the_entry_instance={misplaced}"]
    ok = errors == 0 and foreign == 0 and misplaced == 0
    for kind, ents in entries.items():
        if kind == "DEVICE" and not ents:
            continue
        missing = sorted(set(ents) - traced[kind])
        zero = [n for n in missing if kind == "INTERCONNECT" and all_zero(ents[n][0])]
        bad = [n for n in missing if n not in zero]
        rows.append(f"sdf_{kind.lower()}_entries={len(ents)} applied={len(ents) - len(missing)}"
                    f" skipped_zero={len(zero)} unapplied={len(bad)}")
        if bad:
            ok = False
            rows.append(f"sdf_{kind.lower()}_unapplied_first_lines={bad[:5]}")
    lacking = sorted(expected - got)
    rows.append(f"design_timing_checks={len(expected)} given_limits={len(expected) - len(lacking)}"
                f" without_limits={len(lacking)}")
    if lacking:
        ok = False
        rows.append(f"design_checks_without_limits_first={lacking[:5]}")
    return ok, rows


def run(sim_lines):
    kinds, insts = {}, {}
    for i, line in enumerate(sim_lines):
        m = VIOL.search(line)
        if not m:
            continue
        inst = m.group(1).strip()
        insts[inst] = insts.get(inst, 0) + 1
        k = KIND.match(sim_lines[i + 1]) if i + 1 < len(sim_lines) else None
        kind = k.group(1) if k else "?"
        kinds[kind] = kinds.get(kind, 0) + 1
    result = next((l.split(None, 1)[1].strip() for l in sim_lines if l.startswith("RESULT ")), "none")
    verdict = next((l.split(None, 1)[1].strip() for l in sim_lines if l.startswith("VERDICT ")), "none")
    rows = [f"timing_violations={sum(kinds.values())}"]
    rows += [f"violations[{k}]={n}" for k, n in sorted(kinds.items())]
    rows += [f"violating_instances={len(insts)}", f"result={result}", f"verdict={verdict}"]
    return rows


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def main(argv):
    try:
        if len(argv) >= 7 and argv[1] == "coverage":
            sdf, log, net, scope = argv[2:6]
            with open(net, encoding="utf-8", errors="replace") as f:
                expected = expected_checks(f.read(), [(lib, _read(lib)) for lib in argv[6:]])
            ok, rows = coverage(_read(sdf), sdf, _read(log), expected, scope)
            print("\n".join(rows))
            return 0 if ok else 1
        if len(argv) == 3 and argv[1] == "run":
            print("\n".join(run(_read(argv[2]))))
            return 0
    except (OSError, Unreadable) as e:
        print(f"cvc_report: {e}", file=sys.stderr)
        return 2
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
