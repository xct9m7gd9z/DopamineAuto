# DopamineAuto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clean Dopamine 3.x variant that automatically starts the jailbreak flow after launch, retries one eligible failure, and exits when opened while already jailbroken.

**Architecture:** Keep the upstream jailbreak engine untouched. Add lifecycle and timer orchestration to `DOMainViewController`, expose two preferences through the existing Settings specifier system, and reuse the original Jailbreak button path for automatic execution. Use local source-contract tests on Windows and the upstream macOS GitHub Actions build for final compilation and `.tipa` packaging.

**Tech Stack:** Objective-C/UIKit, Preferences.framework specifiers, XCTest-independent Python `unittest`, GitHub Actions macOS runner, Xcode, Procursus, Theos.

---

## File Map

- Modify `Application/Dopamine/UI/DOMainViewController.m`: lifecycle detection, countdown, shared manual/automatic entry point, retry, and already-jailbroken exit.
- Modify `Application/Dopamine/UI/Settings/DOSettingsController.m`: automatic jailbreak and automatic exit switches.
- Modify `Application/Dopamine/Info.plist`: `DopamineAuto` display name.
- Modify `Application/Dopamine/en.lproj/Localizable.strings`: English UI strings.
- Modify `Application/Dopamine/zh-Hans.lproj/Localizable.strings`: Simplified Chinese UI strings.
- Modify `Application/Dopamine/zh-CN.lproj/Localizable.strings`: Simplified Chinese compatibility strings.
- Modify `Application/Dopamine/zh-TW.lproj/Localizable.strings`: Traditional Chinese UI strings.
- Modify `Application/Dopamine/zh-HK.lproj/Localizable.strings`: Traditional Chinese compatibility strings.
- Create `Tests/test_dopamine_auto.py`: executable source-contract and configuration tests.
- Modify `.github/workflows/main.yml`: run tests and upload `DopamineAuto.tipa`.
- Create `DOPAMINE_AUTO_BUILD.md`: build, installation, configuration, and rollback instructions.

### Task 1: Add Failing Source Contracts

**Files:**
- Create: `Tests/test_dopamine_auto.py`

- [ ] **Step 1: Write tests for the required source contract**

```python
import plistlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Application/Dopamine/UI/DOMainViewController.m"
SETTINGS = ROOT / "Application/Dopamine/UI/Settings/DOSettingsController.m"
INFO = ROOT / "Application/Dopamine/Info.plist"


class DopamineAutoSourceTests(unittest.TestCase):
    def test_display_name(self):
        with INFO.open("rb") as stream:
            self.assertEqual(plistlib.load(stream)["CFBundleDisplayName"], "DopamineAuto")

    def test_settings_are_enabled_by_default(self):
        source = SETTINGS.read_text(encoding="utf-8")
        self.assertIn('setProperty:@"autoJailbreakEnabled" forKey:@"key"', source)
        self.assertIn('setProperty:@"exitWhenJailbroken" forKey:@"key"', source)
        self.assertGreaterEqual(source.count('setProperty:@YES forKey:@"default"'), 2)

    def test_automatic_delays_and_limits(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("DO_AUTO_JAILBREAK_DELAY_SECONDS = 8", source)
        self.assertIn("DO_AUTO_RETRY_DELAY_SECONDS = 30", source)
        self.assertIn("DO_AUTO_EXIT_DELAY_SECONDS = 3", source)
        self.assertIn("DO_AUTO_MAX_ATTEMPTS = 2", source)

    def test_shared_entry_point_and_safety_guards(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("beginJailbreakAutomatically:"), 2)
        self.assertIn("isJailbrokenWithOtherJailbreak", source)
        self.assertIn('boolPreferenceValueForKey:@"removeJailbreakEnabled"', source)
        self.assertIn("enabledPackageManagerKeys", source)
        self.assertIn("UIApplicationStateActive", source)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify the expected failure**

Run:

```powershell
python.exe -m unittest Tests.test_dopamine_auto -v
```

Expected: failures for missing `CFBundleDisplayName`, preferences, constants, and shared entry point.

- [ ] **Step 3: Commit the failing tests**

```powershell
git add Tests/test_dopamine_auto.py
git commit -m "test: define DopamineAuto source contracts"
```

### Task 2: Add Preferences, Name, And Localization

**Files:**
- Modify: `Application/Dopamine/UI/Settings/DOSettingsController.m`
- Modify: `Application/Dopamine/Info.plist`
- Modify: `Application/Dopamine/en.lproj/Localizable.strings`
- Modify: `Application/Dopamine/zh-Hans.lproj/Localizable.strings`
- Modify: `Application/Dopamine/zh-CN.lproj/Localizable.strings`
- Modify: `Application/Dopamine/zh-TW.lproj/Localizable.strings`
- Modify: `Application/Dopamine/zh-HK.lproj/Localizable.strings`

- [ ] **Step 1: Add the two Settings switches**

Insert after the tweak injection specifier:

```objc
PSSpecifier *autoJailbreakSpecifier = [PSSpecifier preferenceSpecifierNamed:DOLocalizedString(@"Settings_Auto_Jailbreak") target:self set:defSetter get:defGetter detail:nil cell:PSSwitchCell edit:nil];
[autoJailbreakSpecifier setProperty:@YES forKey:@"enabled"];
[autoJailbreakSpecifier setProperty:@"autoJailbreakEnabled" forKey:@"key"];
[autoJailbreakSpecifier setProperty:@YES forKey:@"default"];
[specifiers addObject:autoJailbreakSpecifier];

PSSpecifier *exitWhenJailbrokenSpecifier = [PSSpecifier preferenceSpecifierNamed:DOLocalizedString(@"Settings_Exit_When_Jailbroken") target:self set:defSetter get:defGetter detail:nil cell:PSSwitchCell edit:nil];
[exitWhenJailbrokenSpecifier setProperty:@YES forKey:@"enabled"];
[exitWhenJailbrokenSpecifier setProperty:@"exitWhenJailbroken" forKey:@"key"];
[exitWhenJailbrokenSpecifier setProperty:@YES forKey:@"default"];
[specifiers addObject:exitWhenJailbrokenSpecifier];
```

- [ ] **Step 2: Set the application display name**

Add to `Info.plist`:

```xml
<key>CFBundleDisplayName</key>
<string>DopamineAuto</string>
```

- [ ] **Step 3: Add localized strings**

Use these English values and equivalent Simplified/Traditional Chinese translations:

```text
Settings_Auto_Jailbreak = Automatic Jailbreak
Settings_Exit_When_Jailbroken = Exit When Already Jailbroken
Auto_Jailbreak_Title = Automatic Jailbreak
Auto_Jailbreak_Countdown = Jailbreak will start in %ld seconds.
Auto_Jailbreak_Now = Jailbreak Now
Auto_Jailbreak_Cancel_This_Launch = Cancel This Launch
Auto_Jailbreak_Retry = Automatic jailbreak failed. Retrying once in 30 seconds.
Auto_Exit_Already_Jailbroken = Already jailbroken. Closing DopamineAuto.
```

- [ ] **Step 4: Run the tests**

Run:

```powershell
python.exe -m unittest Tests.test_dopamine_auto -v
```

Expected: display-name and preference tests pass; controller contract tests still fail.

- [ ] **Step 5: Commit preferences and localization**

```powershell
git add Application/Dopamine/UI/Settings/DOSettingsController.m Application/Dopamine/Info.plist Application/Dopamine/*.lproj/Localizable.strings
git commit -m "feat: add DopamineAuto preferences and name"
```

### Task 3: Implement Automatic Launch And Exit

**Files:**
- Modify: `Application/Dopamine/UI/DOMainViewController.m`

- [ ] **Step 1: Add constants and controller state**

```objc
static NSInteger const DO_AUTO_JAILBREAK_DELAY_SECONDS = 8;
static NSInteger const DO_AUTO_RETRY_DELAY_SECONDS = 30;
static NSInteger const DO_AUTO_EXIT_DELAY_SECONDS = 3;
static NSInteger const DO_AUTO_MAX_ATTEMPTS = 2;

@property(nonatomic) NSTimer *automaticCountdownTimer;
@property(nonatomic) NSTimer *automaticRetryTimer;
@property(nonatomic) UIAlertController *automaticCountdownAlert;
@property(nonatomic) NSInteger automaticCountdownRemaining;
@property(nonatomic) NSInteger automaticAttemptCount;
@property(nonatomic) BOOL automaticJailbreakCancelled;
@property(nonatomic) BOOL jailbreakAttemptInProgress;
@property(nonatomic) BOOL didScheduleAlreadyJailbrokenExit;
```

- [ ] **Step 2: Observe active/background lifecycle and schedule from `viewDidAppear`**

Register for `UIApplicationWillResignActiveNotification`, cancel timers when the app becomes inactive, and remove the observer in `dealloc`. In `viewDidAppear`, call `scheduleAutomaticActionIfEligible`.

- [ ] **Step 3: Implement eligibility and countdown**

`scheduleAutomaticActionIfEligible` must:

```objc
DOEnvironmentManager *environment = [DOEnvironmentManager sharedManager];
BOOL isJailbroken = environment.isJailbroken;
BOOL exitEnabled = [[DOPreferenceManager sharedManager] boolPreferenceValueForKey:@"exitWhenJailbroken" fallback:YES];

if (isJailbroken && exitEnabled) {
    [self scheduleAlreadyJailbrokenExit];
    return;
}

BOOL autoEnabled = [[DOPreferenceManager sharedManager] boolPreferenceValueForKey:@"autoJailbreakEnabled" fallback:YES];
BOOL removeEnabled = [[DOPreferenceManager sharedManager] boolPreferenceValueForKey:@"removeJailbreakEnabled" fallback:NO];
BOOL hasPackageManager = [DOUIManager sharedInstance].enabledPackageManagerKeys.count > 0;
BOOL active = UIApplication.sharedApplication.applicationState == UIApplicationStateActive;

if (!autoEnabled || removeEnabled || !hasPackageManager || !active ||
    !environment.isSupported || environment.isJailbrokenWithOtherJailbreak ||
    self.jailbreakAttemptInProgress || self.automaticJailbreakCancelled) {
    return;
}
```

Present a countdown alert with `Jailbreak Now` and `Cancel This Launch`. Tick once per second, update the message, dismiss at zero, re-check eligibility, then call `[self beginJailbreakAutomatically:YES]`.

- [ ] **Step 4: Extract the shared jailbreak entry point**

Move the original button handler body into:

```objc
- (void)beginJailbreakAutomatically:(BOOL)automatic
```

The button calls it with `NO`; the countdown calls it with `YES`. The method cancels pending timers, preserves the existing action-menu hiding, button expansion, update-button animation, and calls the refactored jailbreak runner with the automatic flag.

- [ ] **Step 5: Implement one retry and preserve upstream error behavior**

Change the runner signature to:

```objc
- (void)startJailbreakAutomatically:(BOOL)automatic
```

Increment `automaticAttemptCount` only for automatic attempts. When `error && showLogs && automatic && automaticAttemptCount < DO_AUTO_MAX_ATTEMPTS`, do not push the crash controller. Log the retry message, clear `jailbreakAttemptInProgress`, and schedule `automaticRetryTimer` for 30 seconds. Its callback re-checks active state and calls `startJailbreakAutomatically:YES` with a new `DOJailbreaker` instance.

All other error, removal, and success branches retain the upstream implementation. On success, call `completeJailbreak`, `fadeToBlack`, and `[jailbreaker finalize]` without an early `exit`.

- [ ] **Step 6: Implement already-jailbroken exit**

Schedule a cancellable three-second timer. At firing time, re-check the setting, active state, and `isJailbroken`; if all remain true, call `exit(0)`.

- [ ] **Step 7: Run all local tests**

Run:

```powershell
python.exe -m unittest Tests.test_dopamine_auto -v
git diff --check
```

Expected: all tests pass and `git diff --check` prints no errors.

- [ ] **Step 8: Commit controller behavior**

```powershell
git add Application/Dopamine/UI/DOMainViewController.m Tests/test_dopamine_auto.py
git commit -m "feat: automate Dopamine jailbreak lifecycle"
```

### Task 4: Add Reproducible GitHub Build

**Files:**
- Modify: `.github/workflows/main.yml`
- Create: `DOPAMINE_AUTO_BUILD.md`

- [ ] **Step 1: Add the test step before dependencies/build**

```yaml
- name: Test DopamineAuto source contracts
  run: python3 -m unittest Tests.test_dopamine_auto -v
```

- [ ] **Step 2: Upload the TrollStore package with an explicit name**

```yaml
- name: Upload DopamineAuto package
  uses: actions/upload-artifact@v4
  with:
    name: DopamineAuto-${{ env.shorthash }}
    path: ${{ github.workspace }}/Application/Dopamine.tipa
```

- [ ] **Step 3: Document build and installation**

Document repository creation, recursive submodule checkout, `workflow_dispatch`, artifact download, TrollStore installation over the existing bundle identifier, enabling the two settings, Shortcuts charger automation, and rollback to the official Dopamine release.

- [ ] **Step 4: Validate YAML and local tests**

Run:

```powershell
python.exe -c "import pathlib,yaml; yaml.safe_load(pathlib.Path('.github/workflows/main.yml').read_text())"
python.exe -m unittest Tests.test_dopamine_auto -v
git diff --check
```

Expected: YAML parses, all tests pass, and no whitespace errors are reported.

- [ ] **Step 5: Commit build automation**

```powershell
git add .github/workflows/main.yml DOPAMINE_AUTO_BUILD.md
git commit -m "ci: build DopamineAuto tipa"
```

### Task 5: Publish And Verify The Package

**Files:**
- No source changes expected.

- [ ] **Step 1: Create a GitHub repository and push the branch**

Create a repository under the user's authenticated account, add it as a remote, and push `dopamine-auto-source` including submodule references.

- [ ] **Step 2: Run the GitHub Actions workflow**

Trigger `workflow_dispatch` and monitor each test/build step. If the upstream build fails because of a moving dependency, fix only the pinned workflow dependency required to restore the documented build.

- [ ] **Step 3: Inspect the generated artifact**

Download the artifact, calculate SHA-256, unzip it, and verify:

```text
Payload/Dopamine.app/Info.plist contains CFBundleDisplayName=DopamineAuto
Payload/Dopamine.app/Info.plist contains CFBundleIdentifier=com.opa334.Dopamine
Payload/Dopamine.app/Dopamine exists and is non-empty
```

- [ ] **Step 4: Export the deliverables**

Place `DopamineAuto.tipa`, its SHA-256 file, the source archive, the portable patch, and build instructions in the user-facing `outputs` directory.

- [ ] **Step 5: Report device-only verification**

Clearly separate completed static/build verification from tests that require the user's iPhone 12: launch countdown, cancel, automatic jailbreak, retry, successful finalize, and already-jailbroken exit.
