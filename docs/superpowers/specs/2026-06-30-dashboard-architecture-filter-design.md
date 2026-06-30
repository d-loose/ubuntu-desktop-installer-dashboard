<!--
Design self-review:
- No placeholders or TODOs remain.
- Scope is limited to generated dashboard HTML and render tests.
- The design preserves existing data schema, source formatting, URL hardening, and card status colors.
-->

# Dashboard Architecture Filter Design

## Goal

Show a release comparison row for one architecture at a time, defaulting to `amd64`, with release names as card titles.

## Scope

This change affects only generated dashboard HTML and render tests. It does not change collection, parsing, data schema, scheduled publishing, or add a frontend build step.

## UI Changes

- Group cards by architecture instead of release.
- Show only the `amd64` architecture by default when it is present.
- Replace the existing release and status filters with a single `Architecture` dropdown.
- Populate the architecture dropdown from `payload["architectures"]`.
- Select `amd64` by default when available; otherwise select the first configured architecture.
- Change card titles from architecture names to release names.
- Keep the generated timestamp, Suru title strip, status chips, card status colors, and warning details.
- Keep `data-status` for card metadata, but filtering only uses architecture.
- Hide architecture sections with no visible cards after filtering.

## Testing

Render tests will assert:

- `data-architecture-filter` is present.
- `data-release-filter` and `data-status-filter` are absent.
- `amd64` is selected by default when present.
- Cards include `data-architecture` and architecture sections use `data-architecture-section`.
- Card titles contain release names rather than architecture names.
- Filtering JavaScript reads only the architecture dropdown for visibility decisions.
- Existing source-ref formatting, URL hardening, and card status color tests continue to pass.
