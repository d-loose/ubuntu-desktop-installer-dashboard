<!--
Design self-review:
- No placeholders or TODOs remain.
- Scope is limited to render-time source formatting, link correction, and Vanilla UI refinements.
- The formatter responsibilities match the existing static-render architecture.
-->

# Dashboard UI Refinement Design

## Goal

Improve the static Ubuntu Desktop ISO dashboard so source references are easier to scan, secboot links resolve correctly, and the page uses more Vanilla Framework components and visual hierarchy.

## Scope

This change affects only generated dashboard HTML and render tests. It does not change collection, parsing, data schema, scheduled publishing, or introduce a frontend build step.

## Source Reference Formatting

The renderer will normalize source references before escaping and linking them.

- Commit-like refs display as 7-character hashes.
- `subiquity` refs are shortened to 7 characters when they look like commit hashes.
- `secboot` Go pseudo-versions such as `v0.0.0-20260302105957-77bc2457cc76` display as the final hash component shortened to 7 characters.
- `secboot` pseudo-version GitHub URLs are rewritten from `/tree/<pseudo-version>` to `/commit/<full-hash>`, fixing broken links for commit refs.
- Links keep the original full ref in a `title` attribute when the display text differs.
- Unsafe `javascript:` URLs remain suppressed.

## UI Refinement

The dashboard keeps the current responsive card layout and filters. It will add more Vanilla Framework structure and color through existing component classes rather than custom styling.

- Use a Suru/hero-style top strip for the page title and generated timestamp.
- Replace the single summary card with a row of summary cards for record count, warning count, and release count.
- Keep status chips on architecture cards.
- Render warning details as Vanilla caution notifications inside each card.
- Give release sections clearer headers and retain card grouping by release.
- Keep all filtering in the existing inline JavaScript.

## Testing

Render tests will assert:

- Vanilla stylesheet and core Vanilla classes are present.
- Existing filters and section hiding still render.
- `subiquity` commit refs display as 7 characters while linking to the original URL.
- `secboot` pseudo-version refs display as 7 characters and link to `/commit/<full-hash>`.
- Malicious source refs and JavaScript URLs remain escaped or suppressed.
