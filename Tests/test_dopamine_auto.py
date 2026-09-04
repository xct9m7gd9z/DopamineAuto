import plistlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Application/Dopamine/UI/DOMainViewController.m"
SETTINGS = ROOT / "Application/Dopamine/UI/Settings/DOSettingsController.m"
INFO = ROOT / "Application/Dopamine/Info.plist"


class DopamineAutoSourceTests(unittest.TestCase):
    def test_display_name_is_dopamine_auto(self):
        with INFO.open("rb") as stream:
            info = plistlib.load(stream)

        self.assertEqual(info.get("CFBundleDisplayName"), "DopamineAuto")

    def test_automatic_settings_are_enabled_by_default(self):
        source = SETTINGS.read_text(encoding="utf-8")

        for key in ("autoJailbreakEnabled", "exitWhenJailbroken"):
            pattern = re.compile(
                rf'setProperty:@"{key}" forKey:@"key"\];\s*'
                r'\[[^\n]+ setProperty:@YES forKey:@"default"\]',
                re.MULTILINE,
            )
            self.assertRegex(source, pattern)

    def test_automatic_delays_and_attempt_limit(self):
        source = MAIN.read_text(encoding="utf-8")

        self.assertIn("DO_AUTO_JAILBREAK_DELAY_SECONDS = 8", source)
        self.assertIn("DO_AUTO_RETRY_DELAY_SECONDS = 30", source)
        self.assertIn("DO_AUTO_EXIT_DELAY_SECONDS = 3", source)
        self.assertIn("DO_AUTO_MAX_ATTEMPTS = 2", source)

    def test_manual_and_automatic_flows_share_entry_point(self):
        source = MAIN.read_text(encoding="utf-8")

        self.assertIn("- (void)beginJailbreakAutomatically:(BOOL)automatic", source)
        self.assertIn("[self beginJailbreakAutomatically:NO]", source)
        self.assertIn("[self beginJailbreakAutomatically:YES]", source)

    def test_automatic_flow_has_required_safety_guards(self):
        source = MAIN.read_text(encoding="utf-8")

        required_fragments = (
            "isJailbrokenWithOtherJailbreak",
            'boolPreferenceValueForKey:@"removeJailbreakEnabled"',
            "enabledPackageManagerKeys",
            "UIApplicationStateActive",
            "automaticAttemptCount < DO_AUTO_MAX_ATTEMPTS",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, source)

    def test_already_jailbroken_exit_is_delayed_and_optional(self):
        source = MAIN.read_text(encoding="utf-8")

        self.assertIn('boolPreferenceValueForKey:@"exitWhenJailbroken"', source)
        self.assertIn("scheduleAlreadyJailbrokenExit", source)
        self.assertRegex(source, r"scheduleAlreadyJailbrokenExit[\s\S]+?exit\(0\)")


if __name__ == "__main__":
    unittest.main()
