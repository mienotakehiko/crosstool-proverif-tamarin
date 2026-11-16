"""Offline safety and semantic regression tests; no real Docker required."""
import ast
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from common import dump, pv_results, pv_verdict, run, sha, tm_verdict
from generate import LEMMAS, ROOT, render
import launch
import run_inside


class KitTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "test_work"
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_generated_sources_and_ascii(self):
        cases = json.loads((ROOT / "cases.json").read_text())
        self.assertEqual(len(cases), 4)
        for case in cases:
            for body, ext in zip(render(case), ("spthy", "pv")):
                self.assertTrue(body.isascii())
                self.assertEqual(body, (ROOT / "models" / (case["id"] + "." + ext)).read_text())
            tm, pv = render(case)
            self.assertNotIn("Out(", tm)
            self.assertNotIn("In(", tm)
            self.assertNotIn("!", pv)
            self.assertIn("new state: channel", pv)
            self.assertIn("OneInit", tm)

    def test_source_code_ascii_and_parse(self):
        for p in ROOT.glob("*.py"):
            body = p.read_text()
            self.assertTrue(body.isascii(), p.name)
            ast.parse(body)
        check = subprocess.run(["bash", "-n", str(ROOT / "run_pinned.sh")], capture_output=True)
        self.assertEqual(check.returncode, 0)

    def test_verdicts_and_nonzero_not_safe(self):
        self.assertEqual(tm_verdict(" honest_reachable (exists-trace): verified (2 steps)", "honest_reachable", 0), "reachable")
        self.assertEqual(tm_verdict(" single_consumption (all-traces): verified (2 steps)", "single_consumption", 0), "holds")
        self.assertEqual(tm_verdict(" bad_reachable (exists-trace): falsified", "bad_reachable", 124), "unknown")
        self.assertEqual(pv_results("RESULT not event(Bad) is true.\n", 1), [])
        self.assertEqual(pv_results("RESULT not event(Bad) is true.\n", 0), ["true"])
        self.assertEqual(pv_verdict("false", "honest_reachable"), "reachable")
        self.assertEqual(pv_verdict("true", "single_consumption"), "holds")
        self.assertEqual(pv_verdict("cannot be proved", "single_consumption"), "unknown")

    def test_capture_nonzero_and_missing(self):
        self.assertEqual(run(self.root, "bad", [sys.executable, "-c", "raise SystemExit(7)"], 1)["rc"], 7)
        self.assertEqual(run(self.root, "missing", [str(self.root / "absent")], 1)["rc"], 127)
        self.assertTrue((self.root / "missing.command.json").is_file())

    def test_timeout_kills_descendant_group(self):
        marker = self.root / "escaped"
        # Parent and child ignore TERM; child must never survive to write marker.
        child = "import signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(1); pathlib.Path(%r).write_text('escaped')" % str(marker)
        parent = "import signal,subprocess,sys,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); subprocess.Popen([sys.executable,'-c',%r]); time.sleep(5)" % child
        result = run(self.root, "timeout", [sys.executable, "-c", parent], 0.15)
        self.assertEqual(result["rc"], 124)
        import time
        time.sleep(1)
        self.assertFalse(marker.exists())

    def test_address_space_enforced(self):
        result = run(self.root, "memory", [sys.executable, "-c", "a=bytearray(200*1024*1024)"], 2, 64)
        self.assertNotEqual(result["rc"], 0)
        self.assertIn("MemoryError", (self.root / "memory.stderr.txt").read_text())

    def test_resource_gate(self):
        launch.resource_gate(json.dumps({"NCPU": 1, "MemTotal": 3 * 1024**3}))
        for info in ({}, {"NCPU": 0, "MemTotal": 4 * 1024**3}, {"NCPU": 8, "MemTotal": 1024**3}):
            with self.assertRaises(RuntimeError):
                launch.resource_gate(json.dumps(info))

    def test_docker_flags_and_image(self):
        cmd = launch.docker_command(self.root / "inputs", self.root, "owned-test")
        for flag in ("--cpus=1", "--memory=2g", "--memory-swap=2g", "--network", "--read-only"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--pull") + 1], "never")
        self.assertIn(launch.IMAGE, cmd)
        self.assertNotIn("build", cmd)
        self.assertNotIn("pull", cmd)

    def test_commit_mismatch_fails_closed(self):
        for k in run_inside.PINS:
            (self.root / k).write_text("wrong")
        with self.assertRaisesRegex(RuntimeError, "commit_mismatch"):
            run_inside.verify(ROOT, self.root, self.root)

    def test_hash_mismatch_fails_closed(self):
        for k, v in run_inside.PINS.items():
            (self.root / k).write_text(v)
        target = self.root / "binary"
        target.write_text("changed")
        (self.root / "tool_sha256_expected.txt").write_text("0" * 64 + "  " + str(target))
        with self.assertRaisesRegex(RuntimeError, "tool_hash_mismatch"):
            run_inside.verify(self.root, self.root, self.root)

    def test_manifest_rejects_unsafe_and_changed(self):
        target = self.root / "input"
        target.write_text("good")
        dump(self.root / "KIT_HASHES.json", {"input": sha(target)})
        launch.verify_inputs(self.root)
        target.write_text("bad")
        with self.assertRaisesRegex(RuntimeError, "kit_hash_mismatch"):
            launch.verify_inputs(self.root)
        dump(self.root / "KIT_HASHES.json", {"../bad": "0" * 64})
        with self.assertRaisesRegex(RuntimeError, "unsafe_manifest_path"):
            launch.verify_inputs(self.root)

    def test_partial_packaging_and_unique_outputs(self):
        (self.root / "payload").write_text("input")
        dump(self.root / "KIT_HASHES.json", {"payload": sha(self.root / "payload")})
        def failed(folder, phase, command, seconds, memory_mb=None):
            dump(Path(folder) / (phase + ".command.json"), command)
            return {"rc": 127}
        with patch.object(launch, "ROOT", self.root), patch.object(launch, "run", failed):
            self.assertEqual(launch.main(), 1)
            self.assertEqual(launch.main(), 1)
        archives = list((self.root / "pinned_runs").glob("*.tar.gz"))
        self.assertEqual(len(archives), 2)
        self.assertNotEqual(archives[0].name, archives[1].name)
        for archive in archives:
            with tarfile.open(archive) as tar:
                names = tar.getnames()
                self.assertTrue(any(n.endswith("launcher_status.json") for n in names))
                self.assertTrue(any(n.endswith("inputs/payload") for n in names))
                self.assertTrue(any(n.endswith("summary.json") for n in names))

    def test_export_failure_never_launches_pv(self):
        commands = []
        def fake_run(folder, phase, command, seconds, memory_mb=None):
            commands.append((phase, command, seconds))
            (folder / (phase + ".stdout.txt")).write_text("")
            return {"rc": 2}
        with patch.object(run_inside, "run", fake_run):
            rows = run_inside.evaluate(ROOT, self.root, None)
        self.assertEqual(len(rows), 16)
        self.assertTrue(all(r["status"] == "REVIEW" and r["translated"] == "not_run" for r in rows))
        self.assertTrue(all(p in ("native", "export") and sec <= 60 for p, c, sec in commands))
        self.assertTrue(all("-M768m" in c and "-N1" in c for p, c, sec in commands))

    def test_pinned_pipeline_mock_preserves_raw_and_polarity(self):
        class Evaluator:
            def extract_translation_flags(self, body):
                return {"timepoints_split": False}

            def reconstruct_proverif_result(self, body, text):
                return True, "mock_only"
        def fake_run(folder, phase, command, seconds, memory_mb=None):
            lemma = folder.name
            if phase == "native":
                quantifier = "all-traces" if lemma == "single_consumption" else "exists-trace"
                text = "%s (%s): verified (1 steps)\n" % (lemma, quantifier)
            elif phase == "export":
                (folder / "translated.pv").write_text("mock_translation")
                text = ""
            else:
                text = "RESULT mock is false.\n"
            (folder / (phase + ".stdout.txt")).write_text(text)
            return {"rc": 0}
        with patch.object(run_inside, "run", fake_run):
            rows = run_inside.evaluate(ROOT, self.root, Evaluator())
        self.assertEqual(len(rows), 16)
        self.assertTrue(all(r["status"] == "MATCH" for r in rows))
        self.assertTrue(all(r["pv_raw"] == ["false"] for r in rows))
        self.assertEqual(rows[3]["translated"], "holds")
        self.assertEqual(rows[0]["translated"], "reachable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
