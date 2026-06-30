<!--
Design self-review:
- No placeholders or TODOs remain.
- Scope includes collector status classification, generated dashboard HTML, and tests.
- The design preserves the existing JSON timestamp field and architecture-filter layout.
-->

# Dashboard ISO Current/Old Status Design

## Goal

Differentiate pending ISO images that were published today from older pending images, and make the published timestamp easier to read in the UI.

## Scope

This change affects ISO status classification, generated dashboard HTML, and tests. It does not change collection targets, parser output shape, scheduled publishing, or add a frontend build step.

## Status Classification

The `iso_source` status values become:

- `missing`: no ISO or no manifest was found; existing missing behavior and warnings stay unchanged.
- `current`: ISO and manifest were found, and the ISO publication date matches the collector run date in UTC.
- `old`: ISO and manifest were found, but the ISO publication date is older than the collector run date in UTC.

The collector already receives the ISO publication timestamp from the pending listing as an ISO UTC string. It will parse that timestamp and compare the date to the collector run date. If the timestamp is missing or unparsable while the ISO and manifest exist, the collector will classify the ISO as `old` rather than `current`.

## UI Behavior

The dashboard keeps the architecture dropdown layout and release cards.

- `current` cards use green styling and a positive status chip.
- `old` cards use yellow styling and a caution status chip.
- `missing` cards keep red styling and a negative status chip.
- `published_at` remains stored as the existing ISO string in JSON.
- The rendered UI formats valid `published_at` values as `29 Jun 2026, 10:15 UTC`.
- Missing or unparsable `published_at` values render as `unknown`.

## Testing

Tests will assert:

- The collector classifies same-day pending ISOs as `current`.
- The collector classifies older pending ISOs as `old`.
- Missing ISO or manifest records remain `missing`.
- JSON serialization accepts the new statuses.
- The renderer displays `current`, `old`, and `missing` status classes/chips.
- The renderer formats valid timestamps in the friendlier UTC format and keeps invalid/missing timestamps as `unknown`.
