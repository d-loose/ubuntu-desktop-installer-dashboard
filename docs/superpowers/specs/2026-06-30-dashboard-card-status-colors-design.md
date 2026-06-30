<!--
Design self-review:
- No placeholders or TODOs remain.
- Scope is limited to generated dashboard HTML and render tests.
- This spec builds on the existing dashboard UI refinement without changing data collection or schema.
-->

# Dashboard Card Status Colors Design

## Goal

Simplify the dashboard header area and make ISO availability visible at a glance by coloring each release architecture card by ISO status.

## Scope

This change affects only generated dashboard HTML and render tests. It does not change collection, parsing, data schema, scheduled publishing, or add a frontend build step.

## UI Changes

- Remove the Vanilla navigation header from the generated page.
- Remove the summary cards for record count, warning count, and release count.
- Keep the Suru title strip with the dashboard title and generated timestamp.
- Keep the release and status filters in a shallow strip under the title.
- Keep existing card grouping by release and the existing filter JavaScript behavior.
- Add status-specific classes to each architecture card:
  - `is-existing-iso` for non-missing ISO statuses such as `pending`.
  - `is-missing-iso` for `missing`.
- Add a small inline style block to color cards:
  - green-tinted background and border for `is-existing-iso`
  - red-tinted background and border for `is-missing-iso`

## Testing

Render tests will assert:

- Navigation markup is not present.
- Summary card labels for records, warnings, and releases are not present.
- The title strip and filters still render.
- `is-existing-iso` and `is-missing-iso` classes render for sample pending and missing records.
- Existing source-ref formatting and URL hardening tests continue to pass.
