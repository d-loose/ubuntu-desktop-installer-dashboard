<!--
Design self-review:
- No placeholders or TODOs remain.
- Scope removes derived ISO status from JSON and moves age classification to rendering.
- The design preserves factual collector output, friendly timestamp rendering, and card status UI.
-->

# Render-Derived ISO Status Design

## Goal

Remove derived ISO status from generated JSON and derive display status when rendering the dashboard.

## Scope

This change affects the data model, collector JSON output, renderer, and tests. It does not change collection targets, pending listing parsing, scheduled publishing, or add a frontend build step.

## Data Model

`IsoRecord` will no longer include `iso_source`. The JSON output will not include an `iso_source` field. The collector stores only factual ISO fields:

- `iso_url`
- `manifest_url`
- `published_at`
- package versions, source refs, and warnings

## Render-Time Status

The renderer derives card status from record facts and the dashboard `generated_at` timestamp.

- `missing`: `iso_url` is `null` or `manifest_url` is `null`.
- `current`: both URLs are present and `published_at` has the same UTC date as `generated_at`.
- `old`: both URLs are present, but `published_at` is older, missing, unparsable, or timezone-less.

The derived status drives:

- `data-status`
- status chip text and color
- card color class

The rendered `published_at` text remains friendly UTC output like `29 Jun 2026, 10:15 UTC`, with `unknown` for missing, unparsable, or timezone-less timestamps.

## Compatibility

The renderer may tolerate legacy payloads that still include `iso_source`, but it will ignore that field and derive status from URLs and timestamps.

## Testing

Tests will assert:

- Collector-created records no longer expose or serialize `iso_source`.
- Missing records are still identifiable through `iso_url is None` and `manifest_url is None`.
- JSON serialization omits `iso_source`.
- Renderer derives `current`, `old`, and `missing` statuses from URLs, `published_at`, and `generated_at`.
- Renderer ignores stale or legacy `iso_source` values when deriving status.
- Existing architecture filtering, friendly timestamps, source-ref formatting, and URL hardening remain intact.
