# DopamineAuto Strict macOS CI Design

## Status and Scope

This design upgrades `.github/workflows/main.yml` into a reproducible macOS
build pipeline for the existing `dopamine-auto-source` branch. It preserves the
project's source, package format, and trigger model. It does not publish a
release, sign an IPA, or deploy to a device.

The output is one verified `Application/DopamineAuto.tipa` file uploaded as a
GitHub Actions artifact.

## Goals

- Build on a fixed GitHub-hosted macOS image and fixed Xcode release.
- Run the source-contract test suite before installing the expensive build
  toolchain.
- Make every external build dependency immutable or checksum-verified.
- Fail early on missing, truncated, or invalid build inputs and outputs.
- Keep the workflow safe for pull requests and free of repository secrets.
- Make each artifact traceable to its source commit and workflow run.

## Non-goals

- Building on Windows or Linux.
- Producing a signed App Store package.
- Automatically publishing GitHub Releases.
- Caching compiler outputs or package-manager state across runs.

## Trigger and Job Model

Keep the existing push, pull-request, manual-dispatch, and quarterly scheduled
triggers. Use one `build` job so the test result, toolchain, and artifact share
the same checked-out commit and runner state.

The job uses:

- `macos-14`, rather than the moving `macos-latest` label;
- a fixed, compatible Xcode release selected explicitly;
- `permissions: contents: read`;
- a finite job timeout;
- existing per-ref concurrency cancellation.

No secrets are read or written. Pull-request runs only read repository content
and upload their own workflow artifact.

## Immutable Toolchain

The workflow records these values as explicit environment constants:

- the Xcode release;
- the full commit SHA for every GitHub Action, including checkout, Xcode setup,
  Procursus setup, and artifact upload;
- the full THEOS commit SHA;
- the versioned iPhoneOS 16.5 SDK asset URL and its SHA-256;
- each Procursus Bootstrap archive URL and SHA-256.

The workflow must not refer to action branches, `main`, `master`, or `latest`
download URLs. Download commands use HTTPS, fail on HTTP errors, retry bounded
transient failures, and verify SHA-256 before extraction or use.

THEOS is checked out at its recorded commit. Bootstrap downloads remain
source-controlled inputs, but are validated against a versioned checksum
manifest before the project build starts.

## Pipeline

1. Check out the exact triggering commit with recursive submodules.
2. Verify the expected Xcode version and run
   `python3 -m unittest Tests.test_dopamine_auto -v`.
3. Install the pinned Procursus packages, GNU Make, libarchive, THEOS, the
   iPhoneOS SDK, and the trustcache utility.
4. Download and checksum-verify the Bootstrap archives.
5. Set the build timestamp and source SHA, then run the existing `gmake`
   command with `NIGHTLY=1`.
6. Rename the generated `Dopamine.tipa` to `DopamineAuto.tipa`.
7. Verify that the output exists, is non-empty, and passes `unzip -t`.
8. Upload the verified file as
   `DopamineAuto-<short-source-sha>-<run-number>`.

Scripts run with strict Bash error handling. A failed test, download, checksum,
build, or archive check stops the job and prevents artifact upload.

## Artifact and Diagnostics Policy

The upload step uses `if-no-files-found: error`, uploads only the verified
`.tipa`, and retains it for 14 days. It uses zero additional compression
because a `.tipa` is already an archive.

The job summary records the source SHA, fixed Xcode release, THEOS commit, SDK
checksum, Bootstrap checksum-manifest digest, and artifact name. This allows a
failed or successful run to be reproduced from the Actions page without
guessing which dependency versions were used.

## Caching Policy

The first strict version uses no cache. The build, SDK, and Bootstrap inputs are
small enough to favor correctness over cache complexity. A later cache is
allowed only for immutable downloaded archives keyed by the runner image,
dependency versions, and checksum manifest; it must never cache generated
packages, Procursus installation state, or compiler outputs.

## Verification Plan

Before committing the workflow update:

1. Run the existing Python source-contract suite locally.
2. Parse and inspect the workflow to confirm all referenced action revisions
   are full commit SHAs and no moving action or download reference remains.
3. Confirm the workflow still references recursive submodules and the expected
   `DopamineAuto.tipa` output path.

After pushing the workflow update:

1. Dispatch the workflow manually for `dopamine-auto-source`.
2. Confirm the macOS runner completes the source-contract test step.
3. Confirm the build step generates `Application/DopamineAuto.tipa`.
4. Confirm the artifact upload contains one valid, non-empty `.tipa`.
5. Record the completed run URL and artifact name for handoff.

## Failure Handling

Checksum mismatches, missing submodules, unavailable pinned dependencies,
unexpected Xcode versions, failed tests, failed compilation, and invalid
archives are hard failures. The logs and job summary identify the exact stage
and pinned dependency values. Retrying a workflow is appropriate only after a
transient network failure or an intentional dependency-pin update.
