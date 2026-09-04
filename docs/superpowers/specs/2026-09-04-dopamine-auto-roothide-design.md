# DopamineAuto RootHide 2.4.9.x Design

## Scope

Modify only the RootHide `v2.4.9.x` source tree. Preserve the RootHide bundle identifier and RootHide-specific jailbreak flow. Do not modify or package the official 3.0.9 branch.

## Startup Behavior

The main view controller observes app activation and schedules an automatic attempt whenever it becomes visible or active. Eligibility requires:

- the app is installed through TrollStore and the RootHide bootstrap is present;
- the device is supported;
- no other jailbreak is active;
- at least one package manager is selected;
- `autoJailbreakEnabled` is enabled;
- jailbreak removal is not pending.

If startup state is still being initialized, the controller polls on the main run loop at a bounded interval. As soon as all conditions are true, it starts the existing jailbreak entry point directly. There is no countdown UI.

## Retry and Exit

The first failed automatic attempt schedules one retry after 30 seconds. A second failure uses the existing log view. The `exitWhenJailbroken` preference is added with a default of `NO`; when enabled, a successful or already-jailbroken launch may exit Dopamine after a short delay.

Manual jailbreak continues to use the same entry point with automatic mode disabled.

## Testing

Source-contract tests verify the RootHide identity, settings defaults, readiness polling, absence of countdown behavior, and bounded retry behavior. The Windows workspace cannot compile the iOS target; macOS/Xcode and real-device validation remain required before installation.
