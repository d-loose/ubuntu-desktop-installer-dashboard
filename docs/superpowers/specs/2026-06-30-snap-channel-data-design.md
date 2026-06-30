<!--
Design self-review:
- No placeholders or TODOs remain.
- Scope is limited to package metadata parsing, JSON output, rendering, and tests.
- The design keeps existing PackageVersion usage while adding the missing snap channel field.
-->

# Snap Channel Data Design

## Goal

Correctly model snap manifest entries as channel plus revision, and preserve that channel in generated JSON for every snap package.

## Scope

This change affects package metadata parsing, Snapcraft revision resolution, generated JSON, rendered package text, fixtures, and tests. It does not change ISO discovery, source reference resolution, or the dashboard layout.

## Data Model

`PackageVersion` gains an optional `channel` field:

- `name`: package or snap name
- `version`: resolved package version when known
- `revision`: snap revision when applicable
- `channel`: snap channel from the manifest when applicable

For snap manifest lines such as:

```text
snap:ubuntu-desktop-bootstrap 26.04/stable/ubuntu-26.04.1 629
```

the parser stores:

- `name="ubuntu-desktop-bootstrap"`
- `channel="26.04/stable/ubuntu-26.04.1"`
- `revision="629"`
- `version=None`

For deb package lines such as `snapd 2.70+ubuntu1`, the parser stores the deb version in `version` and leaves `channel` and `revision` as `None`.

## Snapcraft Resolution

`SnapcraftResolver.resolve_revision()` continues to resolve a snap revision to an actual snap version. When it returns the resolved package, it preserves the original manifest channel.

## JSON And UI

Generated JSON includes `channel` for package objects through dataclass serialization. Snap package objects have a channel string when parsed from the manifest; deb package objects have `channel: null`.

The renderer displays snap packages with both resolved version and manifest channel when available:

```text
26.04-3b3d4a4cc (channel 26.04/stable/ubuntu-26.04.1, rev 629)
```

Deb package display remains version-only.

## Testing

Tests will assert:

- Manifest fixtures use channel-shaped snap values, not version-like snap values.
- Snap parser output stores manifest channel separately from version.
- Snapcraft resolution preserves `channel` while filling `version`.
- Collector JSON includes channel for snap packages.
- Renderer displays both resolved version and channel for snaps.
