# TrollStore Helper Automatic Refresh Implementation Plan

**Goal:** Opening the Tips persistence helper directly refreshes registrations.

**Architecture:** A small native once-per-launch gate coordinates view appearance
and app activation. The controller calls the original refresh button action.
Build a replacement helper and package it into the official update archive.

**Tech Stack:** Objective-C/UIKit, C, Theos, Python tarfile, macOS GitHub Actions.

## Tasks

- [ ] Add `Tests/test_auto_refresh.c` and `TrollHelper/TSHAutoRefreshGate.h`.
  Native assertions must reject inactive/invisible calls, start on the first
  active visible call, reject duplicate callbacks, and permit a new launch.
  Run with `clang -std=c11 -Wall -Wextra -Werror Tests/test_auto_refresh.c -o
  /tmp/test_auto_refresh && /tmp/test_auto_refresh`. First run a no-op gate and
  record the failed start assertion, then implement the claim and rerun.
- [ ] In `TrollHelper/TSHRootViewController.m`, observe
  `UIApplicationDidBecomeActiveNotification` and invoke the same entry point
  from `viewDidAppear:`. At that entry point call the gate using actual app
  activation and view visibility, and call
  `[self refreshAppRegistrationsPressed]` only after a successful claim.
- [ ] Add `.github/workflows/helper-auto-refresh.yml` to run native tests,
  install pinned Theos/SDK, build fastPathSign and the normal persistence
  helper, and package the checksum-verified official TrollStore 2.1.1 archive.
- [ ] Add `scripts/package_update.py` and its tests. Reject malformed binaries,
  absent markers, wrong app identity and missing helpers. On valid input,
  preserve every other official archive member and check the packaged output.
- [ ] Push the isolated `trollstore-auto-refresh` branch to the existing user
  repository, inspect macOS build results, resolve any concrete build errors,
  and download the verified `.tar` and metadata into workspace `outputs`.
- [ ] Provide the exact local file and installation steps. Explicitly separate
  completed build verification from the phone test the user must perform.
