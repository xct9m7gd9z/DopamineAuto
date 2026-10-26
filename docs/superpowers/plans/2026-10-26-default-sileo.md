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
