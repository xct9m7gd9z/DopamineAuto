import plistlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Application/Dopamine/UI/DOMainViewController.m"
SETTINGS = ROOT / "Application/Dopamine/UI/Settings/DOSettingsController.m"
PROJECT = ROOT / "Application/Dopamine.xcodeproj/project.pbxproj"


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


if __name__ == "__main__":
    unittest.main()
