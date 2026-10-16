#!/usr/bin/env python3
"""Offline regression harness for the verification scripts of both packages.

Run:  python3 tests/test_verify_failures.py          (standard library only; no PDK, cluster or EDA tools)

It copies each package's verify/ directory into a temporary miniature package, puts fake external
commands at the front of PATH, and checks that a crash, a missing or stale output, an invalid report or a
malformed verdict can never end in PASS. The real wrappers are tested with only their external tools
faked. For the aggregate tests only, the checker scripts are replaced inside the temporary fixture. Nothing
here replaces a production checker in the repository, and nothing it writes is design evidence.

A passing harness shows the failure handling works. It is not a physical verification.
"""
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = ("commercial", "open")

VALID_EMPTY_RDB = """<?xml version="1.0" encoding="utf-8"?>
<report-database>
 <description>SKY130 DRC runset</description>
 <original-file/>
 <generator>drc: script='%(gen)s'</generator>
 <top-cell>picorv32</top-cell>
 <tags>
 </tags>
 <categories>
  <category>
   <name>nwell.1</name>
   <description>nwell.1 : min. nwell width : 0.84um</description>
   <categories>
   </categories>
  </category>
 </categories>
 <cells>
  <cell>
   <name>picorv32</name>
   <variant/>
   <layout-name/>
   <references>
   </references>
  </cell>
 </cells>
 <items>
%(items)s </items>
</report-database>
"""
ITEM = "  <item>\n   <category>'nwell.1'</category>\n   <cell>picorv32</cell>\n   <visited>false</visited>\n   <multiplicity>1</multiplicity>\n   <values>\n   </values>\n  </item>\n"


def rdb(gen="/pdk/sky130A/x.drc", n=0):
    return VALID_EMPTY_RDB % {"gen": gen, "items": ITEM * n}


FAKE = {}
FAKE["magic"] = r'''#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then [ "${FAKE_VERSIONS_BAD:-}" = magic ] && exit 3; echo 8.3.623; exit 0; fi
last="${@: -1}"
case "$(basename "$last")" in
  drc_magic.tcl) echo "TOP_EXISTS: 1"; echo "TOP_CHILDREN: 5"; echo "DRC_BOXES: 0"; echo "DRC_TOTAL: 0";;
  antenna.tcl) echo "TOP_EXISTS_AFTER_READ: 1"; echo "TOP_CHILDREN: 5"; echo "EXTRACT_WARNINGS: 1"
               echo "20800 gates analyzed."; echo "ANTENNA_VIOLATIONS: 0"; echo ANTENNA_END;;
  extract.tcl) [ "${FAKE_MAGIC_SPICE:-1}" = 1 ] && printf 'X0 a b sky130_fd_pr__diode perim=1\n' > layout.spice;;
esac
exit "${FAKE_MAGIC_RC:-0}"
'''
FAKE["netgen"] = r'''#!/usr/bin/env bash
if [ "$*" = "-batch quit" ]; then echo "Netgen 1.5.316"; exit "${FAKE_NETGEN_VER_RC:-0}"; fi
echo "Circuit 1 contains 100 devices, Circuit 2 contains 100 devices."
echo "Circuit 1 contains 200 nets, Circuit 2 contains 200 nets."
echo "Final result: Circuits match uniquely." > lvs_report.out
exit "${FAKE_NETGEN_RC:-0}"
'''
FAKE["klayout"] = r'''#!/usr/bin/env bash
if [ "${1:-}" = "-v" ]; then echo "KLayout 0.30.7"; exit 0; fi
rep=""; for a in "$@"; do case "$a" in report=*) rep="${a#report=}";; esac; done
case "${FAKE_KLAYOUT:-valid_empty}" in
  crash) exit 139;;
  zero_nofile) exit 0;;
  nonzero_valid) cp "$FAKE_RDB" "$rep"; exit 1;;
  valid_empty|nonempty) cp "$FAKE_RDB" "$rep"; exit 0;;
  garbage) echo "<root/>" > "$rep"; exit 0;;
esac
'''
FAKE["sta"] = r'''#!/usr/bin/env bash
if [ "${1:-}" = "-version" ]; then echo 2.7.0; exit 0; fi
echo "STA_SPEF_ERROR: none"; echo "STA_SPEF_DRIVERS: 100 10"; echo "STA_CORNER $CORNER"
echo "STA_SETUP_WORST 1.000"; echo "STA_HOLD_WORST 0.100"
echo "STA_MAX_SLEW_VIOLATIONS 0"; echo "STA_MAX_CAP_VIOLATIONS 0"; echo "STA_MAX_FANOUT_VIOLATIONS 0"
exit "${FAKE_STA_RC:-0}"
'''
FAKE["iverilog"] = r'''#!/usr/bin/env bash
if [ "${1:-}" = "-V" ]; then echo "Icarus Verilog version 13.0"; exit 0; fi
[ "${FAKE_IVERILOG:-ok}" = fail ] && { echo "syntax error" >&2; exit 1; }
out=""; prev=""; for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
echo vvp > "$out"; exit 0
'''
FAKE["vvp"] = r'''#!/usr/bin/env bash
echo called >> "$FAKE_VVP_CALLS"
p=""; for a in "$@"; do case "$a" in +period=*) p="${a#+period=}";; esac; done
if [ "$p" = 8.25 ]; then mode="${FAKE_VVP_NOMINAL:-pass}"; else mode="${FAKE_VVP_CONTROL:-trap}"; fi
case "$mode" in
  pass) echo "RESULT 55"; echo "VERDICT PASS"; exit 0;;
  trap) echo "RESULT trap"; echo "VERDICT FAIL"; exit 0;;
  timeout) echo "RESULT timeout"; echo "VERDICT FAIL"; exit 0;;
  crash_after_verdict) echo "RESULT trap"; echo "VERDICT FAIL"; exit 139;;
  crash_after_pass) echo "RESULT 55"; echo "VERDICT PASS"; exit 139;;
  silent) exit 0;;
  contradictory) echo "RESULT 55"; echo "VERDICT PASS"; echo "VERDICT FAIL"; exit 0;;
  wrong) echo "RESULT 54"; echo "VERDICT FAIL"; exit 0;;
  controlpass) echo "RESULT 55"; echo "VERDICT PASS"; exit 0;;
esac
'''

GENERIC_CHECKER = r'''#!/usr/bin/env bash
# fake checker for the aggregate tests: behaviour from FAKE_<NAME>
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
name="$(basename "$0" .sh)"
var="FAKE_$(echo "$name" | tr a-z A-Z)"
mode="${!var:-pass}"
case "$name" in
  sim) stems="sim_8.25ns sim_4.125ns_control";; sta) stems="sta_ss sta_tt sta_ff";; cvc) stems="cvc_8.25ns cvc_control";;
  *) stems="$name";;
esac
case "$mode" in
  pass) for s in $stems; do result $s PASS ok; done; exit 0;;
  crash) exit 139;;
  silent) exit 0;;
  pass_then_crash) for s in $stems; do result $s PASS ok; done; exit 139;;
  pass_then_exit1) for s in $stems; do result $s PASS ok; done; exit 1;;
  partial) set -- $stems; result $1 PASS ok; exit 0;;
  passing) for s in $stems; do printf 'PASSING ok\n' > "$REPORTS/$s.result"; done; exit 0;;
  multiline) for s in $stems; do printf 'PASS ok\nFAIL hidden\n' > "$REPORTS/$s.result"; done; exit 0;;
esac
'''


def write_exec(path, text):
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


class Fixture:
    """A miniature package with the real verify/ code, a dummy PDK, and fake tools on PATH."""

    def __init__(self, tc, pkg, generic_checkers=False):
        self.tmp = tempfile.mkdtemp(prefix="tv_harness_")
        tc.addCleanup(shutil.rmtree, self.tmp, True)
        self.pkgname = pkg
        self.pkg = os.path.join(self.tmp, "pkg")
        self.rep = os.path.join(self.tmp, "rep")
        self.pdk = os.path.join(self.tmp, "pdk")
        self.bin = os.path.join(self.tmp, "bin")
        for d in (self.pkg, self.rep, self.bin, os.path.join(self.pkg, "timing"), os.path.join(self.pkg, "sim"),
                  os.path.join(self.pkg, "netlist"), os.path.join(self.pkg, "layout"), os.path.join(self.pkg, "constraints"),
                  os.path.join(self.pdk, "sky130A", "libs.ref", "sky130_fd_sc_hd", "verilog")):
            os.makedirs(d)
        shutil.copytree(os.path.join(ROOT, pkg, "verify"), os.path.join(self.pkg, "verify"))
        for rel in ("timing/picorv32.sim.sdf", "timing/picorv32.sdf", "sim/tb_picorv32_golden.v",
                    "netlist/picorv32.sim.v", "layout/picorv32.gds"):
            with open(os.path.join(self.pkg, rel), "w") as f:
                f.write("dummy %s\n" % rel)
        for name, text in FAKE.items():
            write_exec(os.path.join(self.bin, name), text)
        if shutil.which("sha256sum") is None:
            write_exec(os.path.join(self.bin, "sha256sum"), '#!/bin/sh\nexec shasum -a 256 "$@"\n')
        self.rdb_file = os.path.join(self.tmp, "valid.lyrdb")
        self.write_rdb(0)
        self.calls = os.path.join(self.tmp, "vvp.calls")
        if generic_checkers:
            for n in ("versions", "sim", "sta", "transistors", "drc_magic", "drc_klayout", "antenna_magic", "lvs", "cvc"):
                write_exec(os.path.join(self.pkg, "verify", n + ".sh"), GENERIC_CHECKER)
        self.write_manifest()
        self.env = dict(os.environ)
        self.env.update({"PATH": self.bin + os.pathsep + os.environ["PATH"], "PDK_ROOT": self.pdk,
                         "REPORTS": self.rep, "FAKE_RDB": self.rdb_file, "FAKE_VVP_CALLS": self.calls})
        for k in list(self.env):
            if k.startswith("FAKE_") and k not in ("FAKE_RDB", "FAKE_VVP_CALLS"):
                del self.env[k]

    def write_rdb(self, n):
        with open(self.rdb_file, "w") as f:
            f.write(rdb(n=n))

    def write_manifest(self):
        lines = []
        for dp, dn, fn in os.walk(self.pkg):
            for n in fn:
                p = os.path.join(dp, n)
                rel = "./" + os.path.relpath(p, self.pkg)
                if rel.startswith("./reports/") or rel == "./SHA256SUMS" or "__pycache__" in rel:
                    continue
                lines.append("%s  %s\n" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), rel))
        with open(os.path.join(self.pkg, "SHA256SUMS"), "w") as f:
            f.writelines(sorted(lines, key=lambda s: s.split("  ")[1]))

    def run(self, script, **fake):
        env = dict(self.env)
        env.update({k: str(v) for k, v in fake.items()})
        p = subprocess.run(["bash", os.path.join(self.pkg, "verify", script)], env=env, cwd=self.tmp,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        return p.returncode, p.stdout

    def result(self, name):
        p = os.path.join(self.rep, name + ".result")
        return open(p).read() if os.path.exists(p) else None

    def seed(self, names, text="PASS old run\n"):
        for n in names:
            with open(os.path.join(self.rep, n + ".result"), "w") as f:
                f.write(text)

    def vvp_calls(self):
        return open(self.calls).read().count("called") if os.path.exists(self.calls) else 0


ALL_STEMS = ["integrity", "versions", "transistors", "sim_8.25ns", "sim_4.125ns_control", "sta_ss", "sta_tt", "sta_ff",
             "drc_magic", "drc_klayout", "antenna_magic", "lvs", "cvc_8.25ns", "cvc_control"]


class PerPackage:
    pkg = None

    def fx(self, **kw):
        return Fixture(self, self.pkg, **kw)

    def assertFailed(self, rc, out, name=None, fx=None):
        self.assertNotEqual(rc, 0, out)
        self.assertNotIn("ALL CHECKS PASSED", out)
        if name:
            r = fx.result(name)
            self.assertTrue(r is not None and r.startswith("FAIL"), "%s result: %r\n%s" % (name, r, out))

    def assertPassed(self, rc, out, name, fx):
        self.assertEqual(rc, 0, out)
        r = fx.result(name)
        self.assertTrue(r is not None and r.startswith("PASS"), "%s result: %r\n%s" % (name, r, out))

    # ---- aggregate --------------------------------------------------------------------------
    def test_aggregate_all_pass(self):
        f = self.fx(generic_checkers=True)
        rc, out = f.run("run_all.sh")
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL CHECKS PASSED", out)
        for s in ALL_STEMS:
            self.assertTrue(f.result(s).startswith("PASS"), s)

    def test_aggregate_integrity_mismatch(self):
        f = self.fx(generic_checkers=True)
        with open(os.path.join(f.pkg, "sim", "tb_picorv32_golden.v"), "a") as fh:
            fh.write("changed\n")
        rc, out = f.run("run_all.sh")
        self.assertFailed(rc, out, "integrity", f)

    def test_aggregate_missing_manifest_entry_file(self):
        f = self.fx(generic_checkers=True)
        os.remove(os.path.join(f.pkg, "layout", "picorv32.gds"))
        rc, out = f.run("run_all.sh")
        self.assertFailed(rc, out, "integrity", f)

    def test_aggregate_crash_with_old_pass_seeded(self):
        for checker, stems in (("versions", ["versions"]), ("sim", ["sim_8.25ns", "sim_4.125ns_control"]),
                               ("sta", ["sta_ss", "sta_tt", "sta_ff"]), ("drc_klayout", ["drc_klayout"]),
                               ("lvs", ["lvs"]), ("cvc", ["cvc_8.25ns", "cvc_control"])):
            for mode in ("crash", "silent"):
                with self.subTest(checker=checker, mode=mode):
                    f = self.fx(generic_checkers=True)
                    f.seed(ALL_STEMS)
                    rc, out = f.run("run_all.sh", **{"FAKE_" + checker.upper(): mode})
                    self.assertFailed(rc, out, None, f)
                    for s in stems:
                        self.assertTrue(f.result(s).startswith("FAIL"), "%s: %r" % (s, f.result(s)))

    def test_aggregate_pass_then_crash_or_nonzero(self):
        for mode in ("pass_then_crash", "pass_then_exit1"):
            with self.subTest(mode=mode):
                f = self.fx(generic_checkers=True)
                rc, out = f.run("run_all.sh", FAKE_DRC_MAGIC=mode)
                self.assertFailed(rc, out, "drc_magic", f)

    def test_aggregate_partial_multi_result(self):
        for checker, omitted in (("sim", "sim_4.125ns_control"), ("sta", "sta_tt"), ("cvc", "cvc_control")):
            with self.subTest(checker=checker):
                f = self.fx(generic_checkers=True)
                f.seed(ALL_STEMS)
                rc, out = f.run("run_all.sh", **{"FAKE_" + checker.upper(): "partial"})
                self.assertFailed(rc, out, omitted, f)

    def test_aggregate_malformed_verdicts(self):
        for mode in ("passing", "multiline"):
            with self.subTest(mode=mode):
                f = self.fx(generic_checkers=True)
                rc, out = f.run("run_all.sh", FAKE_LVS=mode)
                self.assertFailed(rc, out, "lvs", f)

    def test_aggregate_missing_checker_script(self):
        f = self.fx(generic_checkers=True)
        os.remove(os.path.join(f.pkg, "verify", "cvc.sh"))
        f.write_manifest()
        rc, out = f.run("run_all.sh")
        self.assertFailed(rc, out, "cvc_8.25ns", f)

    # ---- sim.sh -----------------------------------------------------------------------------
    def test_sim_pass_and_control(self):
        f = self.fx()
        rc, out = f.run("sim.sh")
        self.assertEqual(rc, 0, out)
        self.assertTrue(f.result("sim_8.25ns").startswith("PASS RESULT 55"))
        self.assertTrue(f.result("sim_4.125ns_control").startswith("PASS"))
        self.assertIsNone(f.result("sim"))
        rc, out = f.run("sim.sh", FAKE_VVP_CONTROL="timeout")
        self.assertEqual(rc, 0, out)

    def test_sim_compile_failure_uses_no_stale_files(self):
        f = self.fx()
        f.seed(["sim_8.25ns", "sim_4.125ns_control", "sim"])
        old = os.path.join(f.rep, "sim.work")
        os.makedirs(old)
        open(os.path.join(old, "sim.vvp"), "w").write("stale")
        rc, out = f.run("sim.sh", FAKE_IVERILOG="fail")
        self.assertFailed(rc, out, "sim_8.25ns", f)
        self.assertTrue(f.result("sim_4.125ns_control").startswith("FAIL"))
        self.assertEqual(f.vvp_calls(), 0)
        self.assertIsNone(f.result("sim"))

    def test_sim_input_copy_failure(self):
        f = self.fx()
        f.seed(["sim_8.25ns", "sim_4.125ns_control"])
        os.remove(os.path.join(f.pkg, "timing", "picorv32.sim.sdf"))
        rc, out = f.run("sim.sh")
        self.assertFailed(rc, out, "sim_8.25ns", f)
        self.assertTrue(f.result("sim_4.125ns_control").startswith("FAIL"))
        self.assertEqual(f.vvp_calls(), 0)

    def test_sim_runtime_crash_despite_plausible_markers(self):
        f = self.fx()
        rc, out = f.run("sim.sh", FAKE_VVP_NOMINAL="crash_after_pass")
        self.assertFailed(rc, out, "sim_8.25ns", f)
        f = self.fx()
        rc, out = f.run("sim.sh", FAKE_VVP_CONTROL="crash_after_verdict")
        self.assertFailed(rc, out, "sim_4.125ns_control", f)
        self.assertTrue(f.result("sim_8.25ns").startswith("PASS"))

    def test_sim_verdict_problems(self):
        for nom, ctl, which in (("silent", "trap", "sim_8.25ns"), ("contradictory", "trap", "sim_8.25ns"),
                                ("wrong", "trap", "sim_8.25ns"), ("pass", "silent", "sim_4.125ns_control"),
                                ("pass", "contradictory", "sim_4.125ns_control"), ("pass", "controlpass", "sim_4.125ns_control")):
            with self.subTest(nom=nom, ctl=ctl):
                f = self.fx()
                rc, out = f.run("sim.sh", FAKE_VVP_NOMINAL=nom, FAKE_VVP_CONTROL=ctl)
                self.assertFailed(rc, out, which, f)

    # ---- drc_klayout.sh ---------------------------------------------------------------------
    def test_klayout_fresh_valid_empty_passes(self):
        f = self.fx()
        rc, out = f.run("drc_klayout.sh")
        self.assertPassed(rc, out, "drc_klayout", f)
        self.assertTrue(os.path.getsize(os.path.join(f.rep, "klayout_drc.lyrdb")) > 0)

    def test_klayout_nonempty_fails(self):
        f = self.fx()
        f.write_rdb(2)
        rc, out = f.run("drc_klayout.sh", FAKE_KLAYOUT="nonempty")
        self.assertFailed(rc, out, "drc_klayout", f)
        self.assertIn("2 findings", f.result("drc_klayout"))

    def test_klayout_crash_or_no_report_with_old_valid_report(self):
        for mode in ("crash", "zero_nofile"):
            with self.subTest(mode=mode):
                f = self.fx()
                open(os.path.join(f.rep, "klayout_drc.lyrdb"), "w").write(rdb())
                f.seed(["drc_klayout"])
                rc, out = f.run("drc_klayout.sh", FAKE_KLAYOUT=mode)
                self.assertFailed(rc, out, "drc_klayout", f)

    def test_klayout_nonzero_status_with_valid_empty_report_fails(self):
        f = self.fx()
        rc, out = f.run("drc_klayout.sh", FAKE_KLAYOUT="nonzero_valid")
        self.assertFailed(rc, out, "drc_klayout", f)

    def test_klayout_unrelated_xml_fails(self):
        f = self.fx()
        rc, out = f.run("drc_klayout.sh", FAKE_KLAYOUT="garbage")
        self.assertFailed(rc, out, "drc_klayout", f)

    # ---- nearby wrappers --------------------------------------------------------------------
    def test_sta_pass_and_failures(self):
        f = self.fx()
        rc, out = f.run("sta.sh")
        self.assertEqual(rc, 0, out)
        for c in ("ss", "tt", "ff"):
            self.assertTrue(f.result("sta_" + c).startswith("PASS"))
        f = self.fx()
        f.seed(["sta_ss", "sta_tt", "sta_ff"])
        rc, out = f.run("sta.sh", FAKE_STA_RC=3)
        self.assertFailed(rc, out, "sta_ss", f)
        self.assertTrue(f.result("sta_ff").startswith("FAIL"))

    def test_magic_status_after_plausible_markers(self):
        for script, name in (("drc_magic.sh", "drc_magic"), ("antenna_magic.sh", "antenna_magic")):
            with self.subTest(script=script):
                f = self.fx()
                rc, out = f.run(script)
                self.assertPassed(rc, out, name, f)
                f = self.fx()
                f.seed([name])
                rc, out = f.run(script, FAKE_MAGIC_RC=1)
                self.assertFailed(rc, out, name, f)

    def test_lvs(self):
        f = self.fx()
        rc, out = f.run("lvs.sh")
        self.assertPassed(rc, out, "lvs", f)
        # stale extraction/report from an earlier run must not be reused
        f = self.fx()
        f.seed(["lvs"])
        open(os.path.join(f.rep, "lvs_report.txt"), "w").write("Final result: Circuits match uniquely.\n")
        old = os.path.join(f.rep, "lvs.work")
        os.makedirs(old)
        open(os.path.join(old, "layout.spice"), "w").write("old\n")
        open(os.path.join(old, "lvs_report.out"), "w").write("Final result: Circuits match uniquely.\n")
        rc, out = f.run("lvs.sh", FAKE_MAGIC_SPICE=0)
        self.assertFailed(rc, out, "lvs", f)
        self.assertFalse(os.path.exists(os.path.join(f.rep, "lvs_report.txt")))
        # failed magic / netgen after plausible output
        f = self.fx()
        rc, out = f.run("lvs.sh", FAKE_MAGIC_RC=1)
        self.assertFailed(rc, out, "lvs", f)
        f = self.fx()
        rc, out = f.run("lvs.sh", FAKE_NETGEN_RC=1)
        self.assertFailed(rc, out, "lvs", f)

    def test_versions(self):
        f = self.fx()
        rc, out = f.run("versions.sh")
        self.assertPassed(rc, out, "versions", f)
        f = self.fx()
        f.seed(["versions"])
        rc, out = f.run("versions.sh", FAKE_VERSIONS_BAD="magic")
        self.assertFailed(rc, out, "versions", f)
        f = self.fx()
        os.remove(os.path.join(f.bin, "klayout"))
        env_path = f.env["PATH"]
        f.env["PATH"] = f.bin + os.pathsep + "/usr/bin" + os.pathsep + "/bin"
        rc, out = f.run("versions.sh")
        self.assertFailed(rc, out, "versions", f)
        f.env["PATH"] = env_path

    def test_transistors_python_failure(self):
        f = self.fx()
        f.seed(["transistors"])
        rc, out = f.run("transistors.sh")      # no DEF in the fixture: transistors.py fails
        self.assertFailed(rc, out, "transistors", f)

    # ---- cvc.sh -----------------------------------------------------------------------------
    def _fake_sim_tchk(self, f, body):
        write_exec(os.path.join(f.pkg, "verify", "sim_tchk.sh"), "#!/usr/bin/env bash\nR=\"$WORK\"; mkdir -p \"$R\"\n" + body)

    PASSBODY = ('echo "PASS 12 probes" > "$R/sim_tchk_selftest.result"\n'
                'echo "PASS sdf_iopath_entries=1" > "$R/sim_tchk_sdf.result"\n'
                'echo "PASS RESULT 55, 0 timing violations" > "$R/sim_tchk_8.25ns.result"\n'
                'echo "PASS control fails as expected: RESULT trap, 3 timing violations" > "$R/sim_tchk_4.125ns_control.result"\n')

    def test_cvc_wrapper(self):
        cases = [
            ("ok", self.PASSBODY + "exit 0\n", {}, True),
            ("no_binary", self.PASSBODY + "exit 0\n", {"CVC": "no-such-cvc"}, False),
            ("crash", "exit 139\n", {}, False),
            ("pass_then_crash", self.PASSBODY + "exit 139\n", {}, False),
            ("no_selftest", self.PASSBODY.replace("sim_tchk_selftest", "x") + "exit 0\n", {}, False),
            ("selftest_refused", self.PASSBODY.replace('"PASS 12 probes"', '"REFUSED nope"') + "exit 2\n", {}, False),
            ("no_control_verdict", self.PASSBODY.replace("sim_tchk_4.125ns_control", "x") + "exit 0\n", {}, False),
            ("control_not_failing", self.PASSBODY.replace('"PASS control', '"FAIL control') + "exit 1\n", {}, False),
        ]
        for name, body, env, ok in cases:
            with self.subTest(case=name):
                f = self.fx()
                write_exec(os.path.join(f.bin, "cvc64"), "#!/bin/sh\nexit 0\n")
                self._fake_sim_tchk(f, body)
                f.seed(["cvc_8.25ns", "cvc_control"])
                rc, out = f.run("cvc.sh", **env)
                if ok:
                    self.assertEqual(rc, 0, out)
                    self.assertTrue(f.result("cvc_8.25ns").startswith("PASS"))
                    self.assertTrue(f.result("cvc_control").startswith("PASS"))
                else:
                    self.assertNotEqual(rc, 0, out)
                    self.assertTrue(f.result("cvc_8.25ns").startswith("FAIL") or f.result("cvc_control").startswith("FAIL"))
                    if name != "control_not_failing":
                        self.assertTrue(f.result("cvc_8.25ns").startswith("FAIL") or name in ("no_control_verdict",))
                        self.assertTrue(f.result("cvc_control").startswith("FAIL"))

    # ---- util.py ----------------------------------------------------------------------------
    def util(self, f, *args, env=None):
        e = dict(f.env)
        e.update(env or {})
        p = subprocess.run([sys.executable, os.path.join(f.pkg, "verify", "util.py"), *args], env=e,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return p.returncode, p.stdout, p.stderr

    def test_lyrdb_validation(self):
        f = self.fx()
        d = f.tmp

        def w(name, text):
            p = os.path.join(d, name)
            open(p, "w").write(text)
            return p
        rc, o, _ = self.util(f, "lyrdb", w("zero.lyrdb", rdb()))
        self.assertEqual((rc, o.split()[0]), (0, "0"))
        rc, o, _ = self.util(f, "lyrdb", w("two.lyrdb", rdb(n=2)))
        self.assertEqual((rc, o.strip()), (0, "2 nwell.1 x2"))
        self.assertNotEqual(self.util(f, "lyrdb", w("bad.lyrdb", rdb(gen="<PDK_ROOT>/x")))[0], 0)   # the shipped defect
        self.assertNotEqual(self.util(f, "lyrdb", w("unrelated.lyrdb", "<root/>\n"))[0], 0)
        self.assertNotEqual(self.util(f, "lyrdb", w("noitems.lyrdb", rdb().replace(" <items>\n </items>\n", "")))[0], 0)
        self.assertNotEqual(self.util(f, "lyrdb", w("othertop.lyrdb", rdb().replace("picorv32</top-cell>", "other</top-cell>")))[0], 0)
        self.assertNotEqual(self.util(f, "lyrdb", w("nocat.lyrdb", rdb(n=1).replace("<category>'nwell.1'</category>", "")))[0], 0)
        self.assertNotEqual(self.util(f, "lyrdb", os.path.join(d, "missing.lyrdb"))[0], 0)

    def test_lyrdb_sanitization_escapes_and_is_idempotent(self):
        f = self.fx()
        for n in (0, 3):
            p = os.path.join(f.tmp, "s%d.lyrdb" % n)
            open(p, "w").write(rdb(gen=f.pdk + "/sky130A/a&amp;b.drc", n=n))
            before = self.util(f, "lyrdb", p)[1]
            rc, _, err = self.util(f, "sanitize-lyrdb", p)
            self.assertEqual(rc, 0, err)
            text = open(p).read()
            self.assertIn("&lt;PDK_ROOT&gt;/sky130A/a&amp;b.drc", text)
            self.assertNotIn(f.pdk, text)
            self.assertEqual(self.util(f, "lyrdb", p)[1], before)
            first = open(p, "rb").read()
            self.assertEqual(self.util(f, "sanitize-lyrdb", p)[0], 0)
            self.assertEqual(open(p, "rb").read(), first)
        # a malformed input is refused and left untouched
        bad = os.path.join(f.tmp, "bad.lyrdb")
        open(bad, "w").write(rdb(gen="<PDK_ROOT>/x"))
        self.assertNotEqual(self.util(f, "sanitize-lyrdb", bad)[0], 0)
        self.assertIn("<PDK_ROOT>/x", open(bad).read())

    def test_shipped_reports_parse(self):
        f = self.fx()
        p = os.path.join(ROOT, self.pkg, "reports", "klayout_drc.lyrdb")
        rc, o, err = self.util(f, "lyrdb", p)
        self.assertEqual((rc, o.split()[0]), (0, "0"), err)


class CommercialTests(PerPackage, unittest.TestCase):
    pkg = "commercial"


class OpenTests(PerPackage, unittest.TestCase):
    pkg = "open"


class PackagesAgree(unittest.TestCase):
    def test_verify_code_identical_except_transistor_count(self):
        names = sorted(n for n in os.listdir(os.path.join(ROOT, "commercial", "verify")) if n != "__pycache__")
        self.assertEqual(names, sorted(n for n in os.listdir(os.path.join(ROOT, "open", "verify")) if n != "__pycache__"))
        for n in names:
            with open(os.path.join(ROOT, "commercial", "verify", n), "rb") as fa:
                a = fa.read()
            with open(os.path.join(ROOT, "open", "verify", n), "rb") as fb:
                b = fb.read()
            if n == "transistors.sh":
                self.assertEqual(a.replace(b"87237", b"183139"), b)
            elif n == "sta.tcl" or n == "transistors.py":
                continue
            else:
                self.assertEqual(a, b, n)


if __name__ == "__main__":
    unittest.main(verbosity=1)
