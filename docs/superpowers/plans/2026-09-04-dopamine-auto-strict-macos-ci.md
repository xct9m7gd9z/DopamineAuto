# DopamineAuto Strict macOS CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the moving macOS build workflow with a pinned, testable pipeline that produces and verifies `DopamineAuto.tipa` before uploading it as an artifact.

**Architecture:** A source-level Python contract test protects the workflow's security and reproducibility properties. The Bootstrap downloader owns archive retrieval and checksum verification, while the workflow owns the fixed macOS/Xcode environment, pinned toolchain setup, compilation, artifact validation, and run summary.

**Tech Stack:** GitHub Actions YAML, macOS 15, Xcode 16.4, Bash, Python `unittest`, THEOS, Procursus, GNU Make.

---

### Task 1: Add the strict-CI contract test

**Files:**
- Create: `Tests/test_ci_workflow.py`
- Test: `Tests/test_ci_workflow.py`

- [ ] **Step 1: Create the failing contract test**

Create `Tests/test_ci_workflow.py` with:

```python
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/main.yml"
BOOTSTRAP_SCRIPT = (
    ROOT / "Application/Dopamine/Resources/download_bootstraps.sh"
)
BOOTSTRAP_CHECKSUMS = (
    ROOT / "Application/Dopamine/Resources/bootstrap-sha256sums.txt"
)

ACTION_PINS = (
    "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
    "maxim-lobanov/setup-xcode@1242409711ff5721add51979e9e11e23ebb7e5a4",
    "dhinakg/procursus-action@4526d5e64410da26bea8073926c0bf8e779293f1",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
)

BOOTSTRAP_HASHES = (
    "a99b39bb0344ee3b42bb961325038dceae7daaec500976f3b822cf36cccf020a  "
    "bootstrap_1800.tar.zst",
    "8354c3aa1ecdad8ebc47d9a76dfca6f830a2b757278068bd33b98bf1d638a9cb  "
    "bootstrap_1900.tar.zst",
)


class StrictMacOSWorkflowTests(unittest.TestCase):
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
            "THEOS_COMMIT: 5280bd038207e14f8bd76f5417aa2fe641c03228",
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

    def test_bootstrap_downloads_are_verified(self):
        self.assertTrue(BOOTSTRAP_CHECKSUMS.is_file())
        checksum_lines = tuple(
            line
            for line in BOOTSTRAP_CHECKSUMS.read_text(encoding="utf-8").splitlines()
            if line
        )
        self.assertEqual(checksum_lines, BOOTSTRAP_HASHES)

        script = BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            "curl --fail --location --retry 3 --retry-delay 2", script
        )
        self.assertIn(
            "shasum -a 256 -c bootstrap-sha256sums.txt", script
        )

    def test_artifact_is_validated_and_retained(self):
        for required in (
            "unzip -t",
            "if-no-files-found: error",
            "retention-days: 14",
            "compression-level: 0",
            "DopamineAuto-${{ env.shorthash }}-${{ github.run_number }}",
        ):
            self.assertIn(required, self.workflow)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test and confirm the old workflow fails it**

Run:

```powershell
python -m unittest Tests.test_ci_workflow -v
```

Expected: failures for the moving runner/action references, missing checksum
manifest, and missing artifact validation settings.

### Task 2: Make Bootstrap retrieval checksum-verified

**Files:**
- Create: `Application/Dopamine/Resources/bootstrap-sha256sums.txt`
- Modify: `Application/Dopamine/Resources/download_bootstraps.sh`
- Test: `Tests/test_ci_workflow.py`

- [ ] **Step 1: Create the immutable checksum manifest**

Create `Application/Dopamine/Resources/bootstrap-sha256sums.txt`:

```text
a99b39bb0344ee3b42bb961325038dceae7daaec500976f3b822cf36cccf020a  bootstrap_1800.tar.zst
8354c3aa1ecdad8ebc47d9a76dfca6f830a2b757278068bd33b98bf1d638a9cb  bootstrap_1900.tar.zst
```

- [ ] **Step 2: Replace the downloader with strict retrieval and verification**

Replace `Application/Dopamine/Resources/download_bootstraps.sh` with:

```bash
#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

curl --fail --location --retry 3 --retry-delay 2 \
  https://apt.procurs.us/bootstraps/1800/bootstrap-iphoneos-arm64.tar.zst \
  --output bootstrap_1800.tar.zst
curl --fail --location --retry 3 --retry-delay 2 \
  https://apt.procurs.us/bootstraps/1900/bootstrap-iphoneos-arm64.tar.zst \
  --output bootstrap_1900.tar.zst

shasum -a 256 -c bootstrap-sha256sums.txt
```

- [ ] **Step 3: Run the Bootstrap-specific contract**

Run:

```powershell
python -m unittest Tests.test_ci_workflow.StrictMacOSWorkflowTests.test_bootstrap_downloads_are_verified -v
```

Expected: one test passes.

### Task 3: Replace the workflow with the pinned macOS pipeline

**Files:**
- Modify: `.github/workflows/main.yml`
- Test: `Tests/test_ci_workflow.py`

- [ ] **Step 1: Replace the workflow**

Replace `.github/workflows/main.yml` with:

```yaml
name: "DopamineAuto: test, build, and upload"

on:
  push:
    branches:
      - "*"
    paths-ignore:
      - ".gitignore"
  pull_request:
    branches:
      - "*"
    paths-ignore:
      - ".gitignore"
  workflow_dispatch:
  schedule:
    - cron: "0 0 1 1 *"
    - cron: "0 0 1 4 *"
    - cron: "0 0 30 6 *"
    - cron: "0 0 28 9 *"
    - cron: "0 0 27 12 *"

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: macos-15
    timeout-minutes: 60
    env:
      XCODE_VERSION: "16.4"
      THEOS_COMMIT: 5280bd038207e14f8bd76f5417aa2fe641c03228
      TRUSTCACHE_COMMIT: aa0e8847529cf76576fce8d2dbc9e088c8f1a0df
      IOS_SDK_URL: https://github.com/theos/sdks/releases/download/master-146e41f/iPhoneOS16.5.sdk.tar.xz
      IOS_SDK_SHA256: 5e0fd3f01266cce4ce012d4a99b38eb56578fca40d09edc81cd83dee958202fb

    steps:
      - name: Check out source and submodules
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          submodules: recursive
          fetch-depth: 1

      - name: Select Xcode
        uses: maxim-lobanov/setup-xcode@1242409711ff5721add51979e9e11e23ebb7e5a4
        with:
          xcode-version: "16.4"

      - name: Verify Xcode
        run: |
          set -euo pipefail
          installed_xcode="$(xcodebuild -version | awk '/^Xcode / { print $2 }')"
          test "$installed_xcode" = "$XCODE_VERSION"
          xcodebuild -version

      - name: Test DopamineAuto source contracts
        run: |
          set -euo pipefail
          python3 -m unittest discover -s Tests -p "test_*.py" -v

      - name: Install Procursus
        uses: dhinakg/procursus-action@4526d5e64410da26bea8073926c0bf8e779293f1
        with:
          packages: ldid findutils sed coreutils make

      - name: Install build packages
        run: |
          set -euo pipefail
          brew install make libarchive openssl@3
          echo "PATH=$(brew --prefix make)/libexec/gnubin:$PATH" >> "$GITHUB_ENV"

      - name: Install pinned THEOS and SDK
        run: |
          set -euo pipefail
          export THEOS="$GITHUB_WORKSPACE/theos"

          git clone --no-checkout https://github.com/theos/theos.git "$THEOS"
          git -C "$THEOS" checkout --detach "$THEOS_COMMIT"
          git -C "$THEOS" submodule update --init --recursive

          mkdir -p "$THEOS/sdks"
          sdk_archive="$RUNNER_TEMP/iPhoneOS16.5.sdk.tar.xz"
          curl --fail --location --retry 3 --retry-delay 2 \
            "$IOS_SDK_URL" --output "$sdk_archive"
          printf "%s  %s\n" "$IOS_SDK_SHA256" "$sdk_archive" \
            | shasum -a 256 -c -
          tar -xJf "$sdk_archive" -C "$THEOS/sdks"
          rm -f "$sdk_archive"

      - name: Build pinned trustcache
        run: |
          set -euo pipefail
          git clone --no-checkout https://github.com/CRKatri/trustcache.git trustcache
          git -C trustcache checkout --detach "$TRUSTCACHE_COMMIT"

          openssl_prefix="$(brew --prefix openssl@3)"
          export CFLAGS="${CFLAGS:-} -I$openssl_prefix/include -arch arm64"
          export LDFLAGS="${LDFLAGS:-} -L$openssl_prefix/lib -arch arm64"
          gmake -C trustcache -j"$(sysctl -n hw.logicalcpu)" OPENSSL=1
          sudo cp trustcache/trustcache /opt/procursus/bin/

      - name: Set build metadata
        run: |
          set -euo pipefail
          echo "ctime=$(date -u +'%Y%m%d_%H%M%S')" >> "$GITHUB_ENV"
          echo "ctimestamp=$(date -u +'%s')" >> "$GITHUB_ENV"
          echo "shorthash=$(git rev-parse --short HEAD)" >> "$GITHUB_ENV"

      - name: Download verified Bootstraps
        run: |
          set -euo pipefail
          Application/Dopamine/Resources/download_bootstraps.sh

      - name: Build DopamineAuto
        run: |
          set -euo pipefail
          export BASEDIR="$GITHUB_WORKSPACE"
          export THEOS="$GITHUB_WORKSPACE/theos"
          gmake -j"$(sysctl -n hw.logicalcpu)" NIGHTLY=1
          mv "$BASEDIR/Application/Dopamine.tipa" \
            "$BASEDIR/Application/DopamineAuto.tipa"

      - name: Verify artifact and write summary
        run: |
          set -euo pipefail
          artifact="$GITHUB_WORKSPACE/Application/DopamineAuto.tipa"
          test -s "$artifact"
          unzip -t "$artifact"

          artifact_sha="$(shasum -a 256 "$artifact" | awk '{ print $1 }')"
          bootstrap_manifest="Application/Dopamine/Resources/bootstrap-sha256sums.txt"
          bootstrap_manifest_sha="$(shasum -a 256 "$bootstrap_manifest" | awk '{ print $1 }')"

          {
            echo "## DopamineAuto build"
            echo ""
            echo "- Source: \`$GITHUB_SHA\`"
            echo "- Runner image: \`${ImageOS:-macos-15} ${ImageVersion:-unknown}\`"
            echo "- Xcode: \`$XCODE_VERSION\`"
            echo "- THEOS: \`$THEOS_COMMIT\`"
            echo "- SDK SHA-256: \`$IOS_SDK_SHA256\`"
            echo "- Bootstrap manifest SHA-256: \`$bootstrap_manifest_sha\`"
            echo "- Artifact SHA-256: \`$artifact_sha\`"
          } >> "$GITHUB_STEP_SUMMARY"

      - name: Upload DopamineAuto artifact
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: DopamineAuto-${{ env.shorthash }}-${{ github.run_number }}
          path: ${{ github.workspace }}/Application/DopamineAuto.tipa
          if-no-files-found: error
          retention-days: 14
          compression-level: 0
```

- [ ] **Step 2: Run the complete Python test suite**

Run:

```powershell
python -m unittest discover -s Tests -p "test_*.py" -v
```

Expected: all DopamineAuto source and CI contract tests pass.

- [ ] **Step 3: Run repository integrity checks**

Run:

```powershell
git diff --check
git status --short
git diff -- .github/workflows/main.yml Application/Dopamine/Resources/download_bootstraps.sh Application/Dopamine/Resources/bootstrap-sha256sums.txt Tests/test_ci_workflow.py
```

Expected: no whitespace errors; only the four planned implementation files and
this plan are changed.

- [ ] **Step 4: Commit the tested implementation**

Run:

```powershell
git add -- .github/workflows/main.yml Application/Dopamine/Resources/download_bootstraps.sh Application/Dopamine/Resources/bootstrap-sha256sums.txt Tests/test_ci_workflow.py docs/superpowers/plans/2026-09-04-dopamine-auto-strict-macos-ci.md
git commit -m "ci: make macOS build reproducible"
```

Expected: one commit containing the workflow, checksum inputs, contract test,
and implementation plan.

### Task 4: Push and verify a real GitHub Actions run

**Files:**
- Verify: `.github/workflows/main.yml`

- [ ] **Step 1: Push the implementation branch**

Run:

```powershell
git -c http.proxy=http://127.0.0.1:11304 -c http.version=HTTP/1.1 push origin dopamine-auto-source
```

Expected: `dopamine-auto-source` advances to the implementation commit.

- [ ] **Step 2: Confirm the push-triggered run exists**

Run:

```powershell
$run = & "C:\Program Files\GitHub CLI\gh.exe" run list --repo xct9m7gd9z/DopamineAuto --workflow main.yml --branch dopamine-auto-source --event push --limit 1 --json databaseId,headSha,status,conclusion,url | ConvertFrom-Json
$run | Format-List
```

Expected: the newest run's `headSha` equals local `git rev-parse HEAD`.

- [ ] **Step 3: Wait for the macOS job**

Run:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run watch $run.databaseId --repo xct9m7gd9z/DopamineAuto --exit-status
```

Expected: the run exits successfully after tests, build, archive validation, and
artifact upload.

- [ ] **Step 4: Verify the artifact metadata**

Run:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" api "repos/xct9m7gd9z/DopamineAuto/actions/runs/$($run.databaseId)/artifacts" --jq ".artifacts[] | [.name, .expired, .size_in_bytes] | @tsv"
```

Expected: one non-expired `DopamineAuto-<short-sha>-<run-number>` artifact with
 a positive byte size. The job's earlier `unzip -t` step proves the uploaded
 source file is a valid archive.
