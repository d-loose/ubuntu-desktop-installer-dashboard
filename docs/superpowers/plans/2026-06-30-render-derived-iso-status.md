# Render-Derived ISO Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `iso_source` from JSON and derive current/old/missing ISO status only while rendering.

**Architecture:** Simplify `IsoRecord` to factual fields only, remove collector status classification, and add render helpers that derive display status from `iso_url`, `manifest_url`, `published_at`, and dashboard `generated_at`.

**Tech Stack:** Python 3.12+, pytest, dataclasses, static HTML.

## Global Constraints

- `IsoRecord` will no longer include `iso_source`.
- JSON output will not include an `iso_source` field.
- Collector stores only factual ISO fields: `iso_url`, `manifest_url`, `published_at`, package versions, source refs, and warnings.
- Render `missing` when `iso_url` is `null` or `manifest_url` is `null`.
- Render `current` when both URLs are present and `published_at` has the same UTC date as `generated_at`.
- Render `old` when both URLs are present but `published_at` is older, missing, unparsable, or timezone-less.
- Derived status drives `data-status`, status chip text/color, and card color class.
- Keep friendly timestamp rendering and existing architecture filter layout.
- Preserve source-ref formatting and URL hardening behavior.

---

## File Structure

- Modify `src/iso_dashboard/models.py`: remove `IsoSource` and `iso_source` field from `IsoRecord`.
- Modify `src/iso_dashboard/collector.py`: remove `_iso_status`, remove record-level `now`, and stop passing `iso_source`.
- Modify `src/iso_dashboard/render.py`: derive status from record facts and `generated_at`.
- Modify tests in `tests/test_config_models.py`, `tests/test_collector.py`, and `tests/test_render.py`.

---

### Task 1: Remove Status From Model And Collector

**Files:**
- Modify: `src/iso_dashboard/models.py`
- Modify: `src/iso_dashboard/collector.py`
- Modify: `tests/test_config_models.py`
- Modify: `tests/test_collector.py`

**Interfaces:**
- Consumes: `IsoRecord` dataclass and `DashboardData.to_json_dict()`.
- Produces: `IsoRecord` and JSON records without `iso_source`.

- [ ] **Step 1: Update model serialization tests**

In `tests/test_config_models.py`, remove `iso_source="pending",` from the `IsoRecord(...)` constructor and remove the expected JSON line `"iso_source": "pending",`.

- [ ] **Step 2: Update collector tests**

In `tests/test_collector.py`:

- Remove `_iso_status` from the import.
- Remove tests for `current`, `old`, and naive timestamp status classification.
- In `test_collect_record_builds_complete_pending_record()`, call `collector.collect_record("noble", "amd64")` and remove `assert record.iso_source == "current"`.
- In `test_collect_record_keeps_missing_record_when_listing_fetch_fails()`, remove `assert record.iso_source == "missing"` and keep URL/warning assertions.

- [ ] **Step 3: Remove status from model**

In `src/iso_dashboard/models.py`:

- Remove `from typing import Literal` if unused.
- Remove `IsoSource = Literal[...]`.
- Remove `iso_source: IsoSource` from `IsoRecord`.

- [ ] **Step 4: Remove collector classification**

In `src/iso_dashboard/collector.py`:

- Remove `_iso_status()`.
- Change `collect_record(self, release: str, architecture: str, now: datetime | None = None)` back to `collect_record(self, release: str, architecture: str)`.
- Remove `run_time = ...` from `collect_record()`.
- Remove the `iso_source=...` argument from both `IsoRecord(...)` calls.
- In `collect_all()`, keep `run_time` for `generated_at`, but call `self.collect_record(release, architecture)`.

- [ ] **Step 5: Run affected tests**

Run: `python3 -m pytest tests/test_config_models.py tests/test_collector.py -v`

Expected: PASS.

---

### Task 2: Derive Status In Renderer

**Files:**
- Modify: `src/iso_dashboard/render.py`
- Modify: `tests/test_render.py`

**Interfaces:**
- Consumes: JSON records without `iso_source`.
- Produces: rendered cards with derived `current`, `old`, and `missing` status.

- [ ] **Step 1: Update render fixture**

In `tests/test_render.py`, remove every `"iso_source": ...` line from `sample_payload()`. Keep URL and timestamp fields.

- [ ] **Step 2: Add stale iso_source regression assertion**

In `test_render_dashboard_includes_summary_table_and_links()`, keep the existing expected `data-status="current"`, `old`, and `missing` assertions. Add a new test after it:

```python
def test_render_ignores_legacy_iso_source_field():
    payload = sample_payload()
    payload["records"][0]["iso_source"] = "missing"

    html = render_dashboard(payload)

    assert 'data-status="current"' in html
```

- [ ] **Step 3: Implement render status helper**

In `src/iso_dashboard/render.py`, after `_published_at()`, add:

```python
def _parse_utc(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso_status(record: dict[str, object], generated_at: datetime | None) -> str:
    if not record.get("iso_url") or not record.get("manifest_url"):
        return "missing"
    published = _parse_utc(record.get("published_at"))
    if published is None or generated_at is None:
        return "old"
    return "current" if published.date() == generated_at.date() else "old"
```

- [ ] **Step 4: Reuse parse helper in `_published_at()`**

Replace `_published_at()` parsing logic with:

```python
def _published_at(value: object) -> str:
    parsed = _parse_utc(value)
    if parsed is None:
        return "unknown"
    return escape(parsed.strftime("%-d %b %Y, %H:%M UTC"))
```

- [ ] **Step 5: Use generated_at for derived status**

In `render_dashboard()`:

- Compute `generated_at_raw = payload.get("generated_at", "unknown")`, `generated_at = escape(str(generated_at_raw))`, and `generated_at_dt = _parse_utc(generated_at_raw)` before looping records.
- Replace `status = str(record.get("iso_source", "missing"))` with `status = _iso_status(record, generated_at_dt)`.
- Keep `data-status` and card classes based on `status`.

- [ ] **Step 6: Run render tests**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS.

---

### Task 3: Full Verification And Commit

**Files:**
- Modify: none expected beyond Tasks 1-2.
- Test: full suite and generated HTML.

**Interfaces:**
- Consumes: completed model/collector/render behavior.
- Produces: committed changes.

- [ ] **Step 1: Run full suite**

Run: `python3 -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Generate and inspect site**

Run: `PYTHONPATH=src python3 -m iso_dashboard.cli render --data data/latest.json --site /tmp/opencode/iso-dashboard-site`

Expected: command exits 0.

Run: `python3 - <<'PY'
from pathlib import Path
html = Path('/tmp/opencode/iso-dashboard-site/index.html').read_text()
assert 'data-status="' in html
assert 'is-current-iso' in html or 'is-old-iso' in html or 'is-missing-iso' in html
print('render-derived ISO status verified')
PY`

Expected: prints `render-derived ISO status verified`.

- [ ] **Step 3: Commit**

Run:

```bash
git add src/iso_dashboard/models.py src/iso_dashboard/collector.py src/iso_dashboard/render.py tests/test_config_models.py tests/test_collector.py tests/test_render.py docs/superpowers/specs/2026-06-30-render-derived-iso-status-design.md docs/superpowers/plans/2026-06-30-render-derived-iso-status.md
git commit -m "Derive ISO status when rendering dashboard"
```

Expected: commit succeeds.

---

## Plan Self-Review

- Spec coverage: Task 1 removes `iso_source` from model/collector/JSON. Task 2 derives status in render and ignores stale legacy fields. Task 3 verifies and commits.
- Placeholder scan: no placeholders, deferred implementation notes, or undefined future work remain.
- Type consistency: renderer helper `_iso_status(record, generated_at)` returns exact status strings `missing`, `current`, and `old`.
