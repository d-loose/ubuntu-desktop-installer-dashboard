<!--
Design self-review:
- No placeholders or TODOs remain.
- Scope adds subiquity snap channel resolution, JSON storage, and render-time comparison.
- The design preserves existing subiquity submodule resolution and snap channel handling.
-->

# Subiquity Snap Channel Comparison Design

## Goal

Resolve the `subiquity` snap from the same snap channel as `ubuntu-desktop-bootstrap` and highlight whether it matches the `subiquity` submodule commit shipped by the bootstrap source.

## Scope

This change affects Snapcraft lookup, collected JSON, rendered dashboard details, and tests. It does not change ISO discovery, source tree lookup, architecture filtering, or ISO status derivation.

## Data Collection

The collector will use the parsed `ubuntu_desktop_bootstrap.channel` to resolve the `subiquity` snap through Snapcraft for the same architecture.

`SnapcraftResolver` gains `resolve_channel(name, channel, architecture)`. It posts to the existing refresh API with an install action containing `channel` instead of `revision`.

The resolved snap is stored in a new `IsoRecord.subiquity_snap` field as `PackageVersion(name="subiquity", version=<resolved version>, revision=<resolved revision>, channel=<bootstrap channel>)`.

If the bootstrap channel is missing or Snapcraft cannot resolve the channel, `subiquity_snap` is `None` and the collector adds a warning.

## Render Comparison

The existing `subiquity` field remains the source submodule commit. The new `subiquity_snap` field is displayed separately.

The renderer compares:

- trailing git hash suffix from `subiquity_snap.version`
- `subiquity.ref`

If both exist and the source ref starts with the snap suffix, the dashboard shows a positive match chip. If both exist and differ, it shows a caution mismatch chip. If either side is missing, it shows an unknown comparison.

## Testing

Tests will assert:

- Snapcraft channel resolution posts a `channel` action.
- Collector stores `subiquity_snap` and keeps existing `subiquity` source ref behavior.
- Collector reports warnings when the subiquity snap channel cannot be resolved.
- JSON includes `subiquity_snap`.
- Renderer displays `subiquity snap`, `subiquity source`, and match/mismatch/unknown comparison states.
