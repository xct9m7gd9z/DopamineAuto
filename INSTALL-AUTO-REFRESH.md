# TrollStore Helper Auto Refresh

For iPhone 12 / iOS 15.0. Based on official TrollStore 2.1.1.

## Install

1. Restore working TrollStore using your existing installation method if needed.
2. Transfer `TrollStoreAutoRefresh-2.1.1.tar` to the iPhone without unpacking it.
3. Share the `.tar` file from Files to TrollStore and complete its update flow.
4. If Tips already hosts the system persistence helper, the update also replaces
   that helper. If not, open TrollStore Settings, choose Install Persistence
   Helper, and select Tips.
5. Open Tips once. It must immediately refresh registrations and respring.
6. After the Home Screen returns, test opening TrollStore and DopamineAuto.

Opening Tips always refreshes, regardless of registration state. No countdown
or button tap is required. Duplicate lifecycle callbacks trigger only once per
launch. Refreshing uses the existing upstream button implementation.

This archive updates TrollStore and its persistence helper; it is not a
DopamineAuto IPA. It does not automatically open DopamineAuto after respring.
Installing a later official TrollStore update can replace the custom helper.

## Verify

The helper log contains `auto-refresh-20261026-1`. `build-info.json` contains
the commit, upstream checksum, and SHA-256 of this update archive. The build
checks that every official archive member except PersistenceHelper is unchanged.

To restore the standard manual helper, open the official TrollStore 2.1.1
`TrollStore.tar` in TrollStore and let its update flow replace the custom helper.
