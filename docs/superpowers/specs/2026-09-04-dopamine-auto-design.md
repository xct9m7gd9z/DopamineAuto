# DopamineAuto Design

## Scope

Create a source-only Dopamine variant for an iPhone 12 running iOS 15.0 and
installed through TrollStore. The variant automatically starts the normal
Dopamine jailbreak flow after Shortcuts launches the app.

Power control, reboot detection, Sunlogin integration, and Windows watchdog
software are outside this package.

The deliverable includes the modified source tree, a portable patch, tests that
can run without an iOS device where practical, and build instructions. Producing
the final `.tipa` remains a macOS/Xcode build step because the upstream project
uses Xcode and the iPhoneOS SDK.

## Compatibility

- Upstream base: Dopamine `3.x`.
- Target: iPhone 12 (A14/arm64e), iOS 15.0.
- Installation: TrollStore.
- Bundle identifier: keep `com.opa334.Dopamine` so installation replaces the
  existing app and retains its preferences.
- Display name: change to `DopamineAuto` so the Shortcuts action is unambiguous.

## User Experience

Add an `Automatic Jailbreak` switch to the jailbreak settings group. It is on
by default.

When the main screen becomes visible and automatic jailbreak is enabled, show
an eight-second confirmation countdown. The user can cancel the current launch
without disabling the setting. When the countdown expires, run the same setup
and jailbreak path used by the existing Jailbreak button.

Manual use remains available. Tapping Jailbreak during the countdown cancels
the timer and starts immediately. Opening Settings or moving the app to the
background cancels the pending automatic attempt.

Add an `Exit When Already Jailbroken` switch, enabled by default. If Shortcuts
opens DopamineAuto while Dopamine is already active, wait three seconds and
terminate the app. This prevents repeated charging events from leaving the app
open unnecessarily.

After a new jailbreak succeeds, preserve the upstream `finalize` path. It
performs the required jailbreak finalization and userspace transition, which
closes the app. Do not call `exit` before finalization finishes.

## Eligibility Checks

Automatic execution starts only when all of these conditions are true:

- the app is active and its main view is visible;
- automatic jailbreak is enabled;
- the device and selected exploit combination are supported;
- the device is not already jailbroken by Dopamine or another jailbreak;
- jailbreak removal is not requested;
- package-manager setup is already complete;
- no manual or automatic jailbreak attempt is in progress.

If any condition is false, Dopamine remains on its normal screen and performs no
automatic action. The user can resolve missing package-manager configuration
manually.

## Execution Structure

Extract the existing Jailbreak button handler into one controller method. Both
the button and automatic countdown call that method so they share UI expansion,
logging, package-manager preparation, mutex handling, and the upstream
`DOJailbreaker` implementation.

Keep automatic state in the main view controller:

- whether an automatic attempt was scheduled;
- whether the countdown was cancelled for this app process;
- whether a jailbreak attempt is active;
- automatic attempt number, limited to two.
- whether an already-jailbroken exit was scheduled.

Do not persist the attempt count across app launches. External power automation
may intentionally relaunch the app after a failed or interrupted exploit.

## Retry And Errors

If the first automatic attempt returns a normal exploit error with detailed logs,
keep the log visible and schedule exactly one retry after 30 seconds using a new
`DOJailbreaker` instance. Record the retry in the existing log view.

Do not retry explanatory/configuration errors, removal flows, unsupported states,
or failures that reboot or terminate the process. Those retain upstream behavior.

If the second attempt fails, stop automatic execution and show the normal
Dopamine error/log interface. Manual recovery remains possible after relaunch.

## Safety Properties

- Never invoke the remove-jailbreak path automatically.
- Never terminate the app before successful jailbreak finalization.
- Never start while the app is inactive or backgrounded.
- Cancel timers when the controller disappears.
- Re-check every eligibility condition when the timer fires, not only when it is
  scheduled.
- Use the existing jailbreak mutex and do not run two attempts concurrently.
- Preserve upstream entitlements and exploit selection behavior.
- Do not add network access, telemetry, remote control, or third-party binaries.

## Localization

Add English, Simplified Chinese, and Traditional Chinese strings for the setting,
countdown, cancellation, retry status, and already-jailbroken exit status. Other
locales fall back to English.

## Verification

Static tests will cover the automatic state policy independently of UIKit and the
exploit implementation: eligibility, cancellation, attempt limit, and retry
classification. Source-level checks will verify that the button and automatic
path use the same entry point and that the original bundle identifier and
entitlements remain unchanged.

On a Mac, run the upstream build with all git submodules initialized and verify
that `Dopamine.tipa` is produced. Final device verification must cover:

1. Shortcuts opens DopamineAuto after a charging event.
2. The countdown starts only when eligible.
3. Cancel prevents the current automatic attempt.
4. Countdown expiry starts the normal jailbreak flow.
5. A first retryable failure retries once after 30 seconds.
6. A second failure stops and preserves logs.
7. Successful jailbreak completes the upstream finalize/respring flow.
8. Launching while already jailbroken exits after three seconds when enabled.
9. Disabling already-jailbroken exit leaves the app open normally.
