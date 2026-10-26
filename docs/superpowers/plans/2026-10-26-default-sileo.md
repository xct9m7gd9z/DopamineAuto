# Default Sileo and Automatic First Launch

The user requests default Sileo selection so a new TrollStore installation can
start jailbreak without selecting a package manager or opening settings first.

## Design

Initialize the existing `enabledPkgManagers` preference through the existing
DOUIManager setter when the filtered selection is empty. Preserve all saved,
valid choices. Initialize this before the jailbreak button/picker reads the
selection. Permit supported TrollStore installations to enter the existing
automatic flow even when bootstrap has not yet been initialized. Preserve the
automatic switch, remove-jailbreak check and other-jailbreak exclusion. Observe
scene activation as well as application activation and view appearance.

## Implementation and Verification

The user subsequently requested an unattended terminal passcode of `123` for
first bootstrap. The prompt resides in each compressed bootstrap's
`prep_bootstrap.sh`, not the app's first-launch controller. Patch that script
at build time to feed `123` to `pw usermod 501 -h 0` without the alert. Retain
the existing first-bootstrap marker and `NO_PASSWORD_PROMPT` override. Abort
before removing the setup script if changing the password fails, preserving
the initialization retry path. Leave existing bootstraps' passwords unchanged.
Verify shell success/failure paths and all archive members after patching.

The user's final settings change enables `exitWhenJailbroken` by default.
Set the Settings switch default and both timer checks to YES, while respecting
any explicitly saved value. Keep the existing three-second exit delay. Include
the default in build metadata to distinguish this final package.

- [ ] Run the unchanged baseline tests in the isolated `Dopamine-auto-sileo`
  worktree, based on the previously delivered remote commit `a57538b`.
- [ ] Add native Foundation tests that execute the actual DOUIManager selection
  methods and `automaticEnvironmentReady` body with in-memory dependencies.
  Cover missing, empty, obsolete, Zebra, both, relaunch, manual changes,
  uninitialized bootstrap and the existing exclusion switches. Execute on the
  macOS runner before changing production code and capture the failed cases.
- [ ] Add the default via `setPackageManager:enabled:` in DOUIManager init.
  Remove the bootstrap prerequisite, add scene lifecycle callbacks and a unique
  package build marker. Run the native tests and existing source checks again.
- [ ] Compile and verify the actual iOS app using the existing pinned build.
  Inspect packaged identity, marker, executable, Sileo archive and file hashes.
- [ ] Download the final ZIP and TIPA into workspace outputs. Deliver this
  alongside the completed TrollStore helper update, with separate installation
  steps and an explicit note that phone behavior still needs device testing.
