import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

import zstandard
from scripts.prepare_unattended_bootstrap import (
    BUILD_MARKER, ORIGINAL_PASSWORD_BLOCK, patch_archive, patch_script,
)


ROOT = Path(__file__).resolve().parents[1]


class BootstrapPasswordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.script = ("#!/bin/sh\n" + ORIGINAL_PASSWORD_BLOCK + '\nrm -f "$TEST_MARKER"\n').encode()

    def shell_run(self, result=0, skip=False):
        shell = shutil.which("sh") if sys.platform != "win32" else r"C:\Program Files\Git\bin\bash.exe"
        if not shell or not Path(shell).is_file():
            self.skipTest("a POSIX shell is needed for this test")
        marker = self.folder / "setup-pending"
        marker.touch()
        capture = self.folder / "password-input"
        env = os.environ.copy()
        env.pop("NO_PASSWORD_PROMPT", None)
        if skip:
            env["NO_PASSWORD_PROMPT"] = "1"
        env["TEST_MARKER"] = marker.as_posix()
        env["TEST_CAPTURE"] = capture.as_posix()
        env["TEST_PW_RESULT"] = str(result)
        patched = patch_script(self.script)
        self.assertNotIn(b"uialert", patched, "interactive prompt must be removed before executing")
        replacement = patched.decode().replace("/usr/sbin/pw", "test_pw")
        prelude = 'test_pw() { [ "$*" = "usermod 501 -h 0" ] || return 91; cat > "$TEST_CAPTURE"; return "$TEST_PW_RESULT"; }\n'
        process = subprocess.run([shell, "-c", prelude + replacement], env=env,
                                 capture_output=True, text=True, timeout=10)
        return process, marker, capture

    def test_removes_the_password_dialog(self):
        result = patch_script(self.script)
        self.assertNotIn(b"/usr/bin/uialert", result)
        self.assertIn(BUILD_MARKER.encode(), result)

    def test_initial_setup_sets_123_and_continues(self):
        process, marker, capture = self.shell_run()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(capture.read_bytes(), b"123\n")
        self.assertFalse(marker.exists())

    def test_password_failure_stops_and_keeps_setup_pending(self):
        process, marker, capture = self.shell_run(result=19)
        self.assertEqual(process.returncode, 19, process.stderr)
        self.assertEqual(capture.read_bytes(), b"123\n")
        self.assertTrue(marker.exists())

    def test_explicit_upstream_no_password_flag_is_preserved(self):
        process, marker, capture = self.shell_run(skip=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertFalse(capture.exists())
        self.assertFalse(marker.exists())

    def test_unknown_script_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "password block"):
            patch_script(b"#!/bin/sh\necho unknown\n")

    def test_patching_is_idempotent(self):
        patched = patch_script(self.script)
        self.assertEqual(patch_script(patched), patched)

    def test_only_setup_script_changes_inside_archive(self):
        base = self.folder / "base.tar.zst"
        output = self.folder / "auto.tar.zst"
        plain = io.BytesIO()
        with tarfile.open(fileobj=plain, mode="w") as archive:
            for name, data in (("./prep_bootstrap.sh", self.script), ("./keep", b"untouched")):
                info = tarfile.TarInfo(name)
                info.mode = 0o755
                info.uid = 501
                info.gid = 501
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            link = tarfile.TarInfo("./keep-link")
            link.type = tarfile.SYMTYPE
            link.linkname = "keep"
            archive.addfile(link)
        base.write_bytes(zstandard.ZstdCompressor().compress(plain.getvalue()))
        patch_archive(base, output)
        with output.open("rb") as compressed:
            with zstandard.ZstdDecompressor().stream_reader(compressed) as reader:
                with tarfile.open(fileobj=reader, mode="r|") as archive:
                    members = []
                    for member in archive:
                        members.append(member.name)
                        if member.name == "./prep_bootstrap.sh":
                            self.assertEqual(archive.extractfile(member).read(), patch_script(self.script))
                            self.assertEqual((member.mode, member.uid, member.gid), (0o755, 501, 501))
                        elif member.name == "./keep":
                            self.assertEqual(archive.extractfile(member).read(), b"untouched")
                        else:
                            self.assertTrue(member.issym())
                            self.assertEqual(member.linkname, "keep")
                    self.assertEqual(members, ["./prep_bootstrap.sh", "./keep", "./keep-link"])

    def test_both_bundled_bootstrap_scripts_match_the_expected_input(self):
        for name in ("bootstrap_1800.tar.zst", "bootstrap_1900.tar.zst"):
            with (ROOT / "Application/Dopamine/Resources" / name).open("rb") as compressed:
                with zstandard.ZstdDecompressor().stream_reader(compressed) as reader:
                    with tarfile.open(fileobj=reader, mode="r|") as archive:
                        for member in archive:
                            if member.name == "./prep_bootstrap.sh":
                                script = archive.extractfile(member).read()
                                self.assertEqual(script.count(ORIGINAL_PASSWORD_BLOCK.encode()), 1, name)
                                break
                        else:
                            self.fail(f"no setup script in {name}")
