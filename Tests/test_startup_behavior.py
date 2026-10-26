import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def method(source, signature):
    result = re.search(re.escape(signature) + r"\s*\{.*?^\}", source, re.MULTILINE | re.DOTALL)
    if not result:
        raise ValueError(f"production method not found: {signature}")
    return result.group()


@unittest.skipUnless(sys.platform == "darwin", "native Objective-C tests run on the macOS builder")
class NativeStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        folder = Path(cls.temp.name)
        ui = (ROOT / "Application/Dopamine/UI/DOUIManager.m").read_text(encoding="utf-8")
        main = (ROOT / "Application/Dopamine/UI/DOMainViewController.m").read_text(encoding="utf-8")
        methods = "\n".join(method(ui, signature) for signature in (
            "- (id)init", "- (NSArray*)enabledPackageManagerKeys",
            "- (void)setPackageManager:(NSString*)key enabled:(BOOL)enabled",
        ))
        source = (ROOT / "Tests/startup_harness.m").read_text(encoding="utf-8")
        source = source.replace("__UI_METHODS__", methods)
        source = source.replace("__READY_METHOD__", method(main, "- (BOOL)automaticEnvironmentReady"))
        harness = folder / "startup.m"
        harness.write_text(source, encoding="utf-8")
        cls.binary = folder / "startup"
        subprocess.run(["clang", "-fobjc-arc", "-framework", "Foundation", str(harness),
                        "-o", str(cls.binary)], check=True)

    def run_case(self, name):
        managers = ROOT / "Application/Dopamine/UI/PkgManagers/PkgManagers.plist"
        subprocess.run([str(self.binary), name, str(managers)], check=True)

    def test_fresh_install_selects_and_saves_sileo(self): self.run_case("fresh")
    def test_empty_selection_defaults_to_sileo(self): self.run_case("empty")
    def test_obsolete_selection_defaults_to_sileo(self): self.run_case("obsolete")
    def test_existing_zebra_is_preserved(self): self.run_case("zebra")
    def test_existing_both_are_preserved(self): self.run_case("both")
    def test_relaunch_preserves_default_without_rewriting(self): self.run_case("relaunch")
    def test_manual_picker_changes_still_work(self): self.run_case("manual")
    def test_automatic_start_allows_initial_bootstrap(self): self.run_case("ready")
    def test_automatic_start_retains_exclusions(self): self.run_case("exclusions")
