import plistlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Application/Dopamine/UI/DOMainViewController.m"
SETTINGS = ROOT / "Application/Dopamine/UI/Settings/DOSettingsController.m"
PROJECT = ROOT / "Application/Dopamine.xcodeproj/project.pbxproj"
BAD_RECOVERY = ROOT / "Application/Dopamine/Exploits/badRecovery/badRecovery.m"
FUGU14 = ROOT / "BaseBin/libjailbreak/src/kcall_Fugu14.c"
ARM64 = ROOT / "BaseBin/libjailbreak/src/kcall_arm64.c"
JAILBREAKER = ROOT / "Application/Dopamine/Jailbreak/DOJailbreaker.m"


class DopamineAutoRootHideSourceTests(unittest.TestCase):
    def test_root_hide_bundle_identity_is_preserved(self):
        project = PROJECT.read_text(encoding="utf-8")
        self.assertIn("PRODUCT_BUNDLE_IDENTIFIER = com.opa334.Dopamine-roothide;", project)
        self.assertIn("MARKETING_VERSION = 2.4.9;", project)

    def test_automatic_settings_have_expected_defaults(self):
        source = SETTINGS.read_text(encoding="utf-8")

        for key, default in (("autoJailbreakEnabled", "YES"), ("exitWhenJailbroken", "NO")):
            pattern = re.compile(
                rf'setProperty:@?YES forKey:@"enabled"[\s\S]+?'
                rf'setProperty:@"{key}" forKey:@"key"[\s\S]+?'
                rf'setProperty:@{default} forKey:@"default"',
                re.MULTILINE,
            )
            self.assertRegex(source, pattern)

    def test_startup_uses_readiness_polling_without_countdown(self):
        source = MAIN.read_text(encoding="utf-8")

        self.assertIn("scheduleAutomaticActionIfEligible", source)
        self.assertIn("automaticEligibilityTimer", source)
        self.assertIn("UIApplicationDidBecomeActiveNotification", source)
        self.assertIn("isBootstrapped", source)
        self.assertIn("enabledPackageManagerKeys", source)
        self.assertIn("beginJailbreakAutomatically:YES", source)
        self.assertNotIn("DO_AUTO_JAILBREAK_DELAY_SECONDS", source)
        self.assertNotIn("Auto_Jailbreak_Countdown", source)

    def test_automatic_retry_is_bounded_and_exit_defaults_off(self):
        source = MAIN.read_text(encoding="utf-8")

        self.assertIn("DO_AUTO_RETRY_DELAY_SECONDS", source)
        self.assertIn("DO_AUTO_MAX_ATTEMPTS", source)
        self.assertIn("automaticAttemptCount < DO_AUTO_MAX_ATTEMPTS", source)
        self.assertIn('boolPreferenceValueForKey:@"exitWhenJailbroken" fallback:NO', source)

    def test_bad_recovery_has_bounded_waits_and_failure_cleanup(self):
        source = BAD_RECOVERY.read_text(encoding="utf-8")

        self.assertIn("BAD_RECOVERY_STAGE_TIMEOUT_NS", source)
        self.assertIn("badRecoveryDeadline", source)
        self.assertIn("badRecoveryTimedOut", source)
        self.assertIn("cleanupFailedBreakCFI", source)
        self.assertIn("deinitFugu15PACBypass", source)
        self.assertRegex(source, r"while \([^\n]+\)[\s\S]{0,500}badRecoveryTimedOut")

    def test_bad_recovery_propagates_kcall_init_failure(self):
        source = BAD_RECOVERY.read_text(encoding="utf-8")

        self.assertIn("if (fugu14_kcall_init", source)
        self.assertIn("return -1;", source)

    def test_bad_recovery_deinit_cleans_temporary_thread(self):
        source = BAD_RECOVERY.read_text(encoding="utf-8")

        self.assertRegex(source, r"int exploit_deinit\(void\)[\s\S]{0,300}cleanupFailedBreakCFI")

    def test_bad_recovery_retries_transient_pac_setup_failure(self):
        source = BAD_RECOVERY.read_text(encoding="utf-8")

        self.assertIn("BAD_RECOVERY_MAX_ATTEMPTS", source)
        self.assertRegex(source, r"for \([^\n]+BAD_RECOVERY_MAX_ATTEMPTS[\s\S]{0,1200}breakCFI\(\)")
        self.assertRegex(source, r"breakCFI\(\)[\s\S]{0,1800}cleanupFailedBreakCFI")

    def test_pac_failure_cleans_loaded_pac_exploit(self):
        source = JAILBREAKER.read_text(encoding="utf-8")

        self.assertRegex(source, r"if \(\[pacBypass run\] != 0\).*?\[pacBypass cleanup\].*?\[kernelExploit cleanup\]",
                         re.DOTALL)

    def test_fugu14_kcall_cannot_wait_forever(self):
        source = FUGU14.read_text(encoding="utf-8")

        self.assertIn("KCALL_RETURN_TIMEOUT_NS", source)
        self.assertIn("kcallDeadline", source)
        self.assertIn("kcallTimedOut", source)
        self.assertRegex(source, r"while \(!gUserReturnDidHappen\)[\s\S]{0,500}kcallTimedOut")

    def test_arm64_kcall_cannot_wait_forever(self):
        source = ARM64.read_text(encoding="utf-8")

        self.assertIn("KCALL_RETURN_TIMEOUT_NS", source)
        self.assertIn("kcallDeadline", source)
        self.assertIn("kcallTimedOut", source)
        self.assertRegex(source, r"while \(!gUserReturnDidHappen\)[\s\S]{0,500}kcallTimedOut")


if __name__ == "__main__":
    unittest.main()
