#!/usr/bin/env python3
"""Helpers for the verify scripts (the container has no sed/awk, so these live here).
  util.py clean FILE...   replace machine-specific absolute paths in reports
  util.py sta LOG         evaluate one OpenSTA corner log -> "PASS|FAIL|NORES <facts>"
  util.py lyrdb FILE      validate a KLayout report database and count its findings -> "<n> <category xN ...>"
  util.py sanitize-lyrdb FILE  replace machine-specific paths in a report database (XML-aware) and validate it
  util.py layoutspice IN OUT  rewrite the antenna-diode line of the extracted SPICE the way the PDK cell
                          SPICE writes it (D element, pj= instead of X instance, perim=; same values)
"""
import os, re, sys, collections
import xml.etree.ElementTree as ET

def _subs():
    subs = []
    for var, tag in (("PKG", "<pkg>"), ("PDK_ROOT", "<PDK_ROOT>"), ("REPORTS", "<reports>"), ("HOME", "<home>")):
        v = os.environ.get(var, "")
        if len(v) > 1:
            subs.append((v.rstrip("/"), tag))
    subs.sort(key=lambda s: -len(s[0]))      # longest path first
    return subs

def _replace(t, subs):
    for a, b in subs:
        t = t.replace(a, b)
    return t

def clean_lyrdb(f):
    """Replace paths in the text, tail and attribute values of a report database and serialise it with an
    XML library, so the placeholder's angle brackets (and any ampersand) are escaped. The result is
    validated before it replaces the file. Running it twice gives the same file."""
    subs = _subs()
    tree = ET.parse(f)                      # raises ParseError on a malformed input
    for el in tree.getroot().iter():
        if el.text:
            el.text = _replace(el.text, subs)
        if el.tail:
            el.tail = _replace(el.tail, subs)
        for k in list(el.attrib):
            el.set(k, _replace(el.attrib[k], subs))
    tmp = f + ".tmp"
    tree.write(tmp, encoding="utf-8", xml_declaration=True)
    lyrdb_count(tmp)                        # validate before replacing
    os.replace(tmp, f)

def clean(files):
    subs = _subs()
    for f in files:
        if not os.path.isfile(f):
            continue
        if f.endswith(".lyrdb"):
            clean_lyrdb(f)
            continue
        t = open(f, encoding="utf-8", errors="surrogateescape").read()
        open(f, "w", encoding="utf-8", errors="surrogateescape").write(_replace(t, subs))

def sta(log):
    t = open(log, encoding="utf-8", errors="replace").read()
    g = lambda k: (re.search(r"^%s\s+(\S+)" % k, t, re.M) or [None, None])[1]
    s, h = g("STA_SETUP_WORST"), g("STA_HOLD_WORST")
    v = [g("STA_MAX_SLEW_VIOLATIONS"), g("STA_MAX_CAP_VIOLATIONS"), g("STA_MAX_FANOUT_VIOLATIONS")]
    err = re.search(r"^STA_SPEF_ERROR:\s*(.*)$", t, re.M)
    sd = re.search(r"^STA_SPEF_DRIVERS:\s+(-?\d+)\s+(-?\d+)", t, re.M)
    if None in [s, h] + v or not err or not sd:
        print("NORES no result"); return
    total, unann = int(sd.group(1)), int(sd.group(2))
    ann = total - unann
    if err.group(1).strip() != "none":
        print("FAIL SPEF read error: %s" % err.group(1).strip()[:120]); return
    if total <= 0 or unann < 0 or ann <= 0:
        print("FAIL SPEF annotated no drivers (%d of %d)" % (ann, total)); return
    ok = float(s) >= 0 and float(h) >= 0 and all(int(x) == 0 for x in v)
    print("%s setup %s ns, hold %s ns, slew/cap/fanout violations %s/%s/%s, SPEF annotated %d of %d drivers (%d unannotated)"
          % (("PASS" if ok else "FAIL"), s, h, *v, ann, total, unann))

def lyrdb_count(f):
    """Parse a KLayout report database and return (n_items, Counter of categories). Raises ValueError for a
    file that is not a complete report database for the picorv32 top cell; a syntactically valid but
    unrelated or incomplete document is never read as zero findings."""
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError as e:
        raise ValueError("not well-formed XML: %s" % e)
    if root.tag != "report-database":
        raise ValueError("root element is <%s>, not <report-database>" % root.tag)
    top = root.find("top-cell")
    if top is None or (top.text or "").strip() != "picorv32":
        raise ValueError("top-cell is not picorv32")
    for c in ("categories", "cells", "items"):
        if root.find(c) is None:
            raise ValueError("missing <%s> container" % c)
    items = root.find("items").findall("item")
    cats = collections.Counter()
    for i in items:
        c = i.find("category")
        if c is None or not (c.text or "").strip():
            raise ValueError("an item has no category")
        cats[re.sub(r"[\s']", "", c.text)] += 1
    return len(items), cats

def lyrdb(f):
    try:
        n, cats = lyrdb_count(f)
    except (ValueError, OSError) as e:
        print("lyrdb: %s" % e, file=sys.stderr); sys.exit(2)
    print(n, " ".join("%s x%d" % kv for kv in sorted(cats.items())))

def sanitize_lyrdb(f):
    try:
        clean_lyrdb(f)
    except (ValueError, OSError, ET.ParseError) as e:
        print("sanitize-lyrdb: %s" % e, file=sys.stderr); sys.exit(2)

def layoutspice(src, dst):
    """Write Magic's antenna-diode line in the form the PDK cell SPICE uses
    (D element, pj= instead of X instance, perim=); values are unchanged."""
    out = []
    for l in open(src, encoding="utf-8", errors="surrogateescape"):
        if "sky130_fd_pr__diode" in l and not l.startswith("*"):
            l = l.replace(" perim=", " pj=")
            if l.startswith("X"):
                l = "D" + l[1:]
        out.append(l)
    open(dst, "w", encoding="utf-8", errors="surrogateescape").write("".join(out))

if __name__ == "__main__":
    c = sys.argv[1]
    {"clean": lambda: clean(sys.argv[2:]), "sta": lambda: sta(sys.argv[2]), "lyrdb": lambda: lyrdb(sys.argv[2]), "sanitize-lyrdb": lambda: sanitize_lyrdb(sys.argv[2]), "layoutspice": lambda: layoutspice(sys.argv[2], sys.argv[3])}[c]()
