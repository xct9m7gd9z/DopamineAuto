# TrollStore Helper Automatic Refresh

The user approved unconditional refresh on opening Tips. Do not inspect the
registration state of TrollStore or DopamineAuto before refreshing.

## Behavior

On the helper's first visible, active presentation, invoke the existing
`refreshAppRegistrationsPressed` action. Observe app activation as well as view
appearance so that a cold launch cannot miss the trigger. Claim the action on
the main thread before invoking it, so duplicate lifecycle events do not start
multiple refreshes. The existing action refreshes registrations and resprings;
each subsequent launch gets a fresh process and may refresh again.

No countdown, extra tap, registration check, or automatic Dopamine launch is
part of this change. Leave the existing manual buttons available.

## Delivery

Build only the modified PersistenceHelper against the official TrollStore
source and SDK. Replace that binary in the checksum-verified official 2.1.1
TrollStore update archive. Preserve the other archive members byte for byte.
Keep the official app identity and version so existing installation logic can
update its installed system-app helper. Deliver a distinctly named `.tar`
update and build metadata in the workspace outputs directory.

The installer must first have a working TrollStore. If Tips already hosts the
official system persistence helper, installing the custom TrollStore update
also replaces that helper. Otherwise install the persistence helper into Tips
from TrollStore settings after updating. This is an update archive, not an IPA.

## Verification

Run native tests for initial launch, inactive/invisible UI, and duplicate
callbacks. Compile the real iOS helper with its original signing flow. Verify
its arm64 executable, entitlements, build marker, and final archive integrity.
Confirm that all official archive members other than PersistenceHelper are
unchanged. Device launch and refresh still require testing on the user's phone.
