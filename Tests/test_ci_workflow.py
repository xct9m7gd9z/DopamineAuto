import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/roothide.yml"

ACTION_PINS = (
    "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
    "maxim-lobanov/setup-xcode@1242409711ff5721add51979e9e11e23ebb7e5a4",
    "dhinakg/procursus-action@4526d5e64410da26bea8073926c0bf8e779293f1",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
)


class StrictRootHideMacOSWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_fixed_runner_permissions_and_timeout(self):
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertIn("runs-on: macos-15", self.workflow)
        self.assertIn("timeout-minutes: 60", self.workflow)
        self.assertIn('XCODE_VERSION: "16.4"', self.workflow)

    def test_all_actions_are_immutable_commits(self):
        action_uses = tuple(
            re.findall(r"^\s*uses:\s*(\S+)\s*$", self.workflow, re.MULTILINE)
        )
        self.assertEqual(action_uses, ACTION_PINS)
        self.assertNotRegex(self.workflow, r"@(?:main|master|v\d+)\b")

    def test_toolchain_and_sdk_are_pinned(self):
        self.assertIn(
            "THEOS_REPOSITORY: https://github.com/roothide/theos.git",
            self.workflow,
        )
        self.assertIn(
            "THEOS_COMMIT: 88506b2c22e9e07dd4ed055f23c9e398a117a2c7",
            self.workflow,
        )
        self.assertIn(
            "TRUSTCACHE_COMMIT: aa0e8847529cf76576fce8d2dbc9e088c8f1a0df",
            self.workflow,
        )
        self.assertIn(
            "https://github.com/theos/sdks/releases/download/"
            "master-146e41f/iPhoneOS16.5.sdk.tar.xz",
            self.workflow,
        )
        self.assertIn(
            "IOS_SDK_SHA256: "
            "5e0fd3f01266cce4ce012d4a99b38eb56578fca40d09edc81cd83dee958202fb",
            self.workflow,
        )
        self.assertNotIn("/releases/latest/", self.workflow)
        self.assertNotIn("xcode-version: latest-stable", self.workflow)

    def test_current_checkout_and_root_hide_build_are_used(self):
        self.assertIn("actions/checkout@", self.workflow)
        self.assertIn("submodules: recursive", self.workflow)
        self.assertNotIn("git clone --recursive https://github.com/roothide/Dopamine2-roothide", self.workflow)
        self.assertIn('gmake -j"$(sysctl -n hw.logicalcpu)" NIGHTLY=1', self.workflow)
        self.assertIn("Application/Dopamine.tipa", self.workflow)

    def test_workflow_preserves_sdk_headers_for_makefile_detection(self):
        self.assertNotIn("/usr/include/xpc.modulemap", self.workflow)
        self.assertNotIn("/usr/include/XPC.modulemap", self.workflow)

    def test_makefile_detects_both_xpc_modulemap_casings(self):
        makefile = (ROOT / "BaseBin/Makefile").read_text(encoding="utf-8")
        self.assertIn("/usr/include/xpc.modulemap", makefile)
        self.assertIn("/usr/include/XPC.modulemap", makefile)
        self.assertIn("rm -rf .include/xpc", makefile)

    def test_roothidehooks_allows_private_iOS_api_availability(self):
        makefile = (ROOT / "BaseBin/roothidehooks/Makefile").read_text(encoding="utf-8")
        self.assertIn("roothidehooks_CFLAGS = -Werror -Wno-availability", makefile)
        self.assertIn(
            "roothidehooks_OBJCFLAGS = -Wno-availability "
            "-Wno-unguarded-availability -Wno-unguarded-availability-new",
            makefile,
        )

    def test_identity_is_inspected_before_upload(self):
        for required in (
            'com.opa334.Dopamine-roothide',
            'DopamineAuto',
            'CFBundleExecutable',
            'unzip -t',
            'if-no-files-found: error',
            'retention-days: 14',
            'compression-level: 0',
            'DopamineAuto-roothide-2.4.9-${{ env.shorthash }}-${{ github.run_number }}',
        ):
            self.assertIn(required, self.workflow)


if __name__ == "__main__":
    unittest.main()
