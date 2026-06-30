# Dashboard ISO Current/Old Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify found pending ISOs as `current` or `old` based on publication date and render friendlier timestamps.

**Architecture:** Add collector-side ISO status classification from `iso.modified` and the collector run date. Keep the stored JSON timestamp unchanged, and update the static renderer to map `current`, `old`, and `missing` to status chips, card colors, and friendly UTC timestamp text.

**Tech Stack:** Python 3.12+, pytest, dataclasses, static HTML.

## Global Constraints

- ISO status values are `missing`, `current`, and `old`.
- `missing`: no ISO or no manifest was found; existing missing behavior and warnings stay unchanged.
- `current`: ISO and manifest were found, and ISO publication date matches the collector run date in UTC.
- `old`: ISO and manifest were found, but ISO publication date is older than the collector run date in UTC.
- If ISO and manifest exist but the ISO timestamp is missing or unparsable, classify as `old`.
- Keep `published_at` stored as the existing ISO string in JSON.
- Render valid `published_at` values as `29 Jun 2026, 10:15 UTC`.
- Render missing or unparsable `published_at` values as `unknown`.
- `current` cards use green styling and a positive status chip.
- `old` cards use yellow styling and a caution status chip.
- `missing` cards use red styling and a negative status chip.
- Preserve architecture filter layout, generated timestamp, warning details, source-ref formatting, and URL hardening behavior.

---

## File Structure

- Modify `src/iso_dashboard/models.py`: widen `IsoSource` literal.
- Modify `src/iso_dashboard/collector.py`: classify found pending ISOs as `current` or `old` using `iso.modified` and current run date.
- Modify `src/iso_dashboard/render.py`: map statuses to chips/classes/colors and format timestamps.
- Modify `tests/test_collector.py`: verify `current`, `old`, and missing behavior.
- Modify `tests/test_render.py`: verify status classes/colors/chips and friendly timestamps.

---

### Task 1: Collector Status Classification

**Files:**
- Modify: `src/iso_dashboard/models.py`
- Modify: `src/iso_dashboard/collector.py`
- Modify: `tests/test_collector.py`

**Interfaces:**
- Consumes: `Collector.collect_record(release: str, architecture: str) -> IsoRecord`
- Produces: `IsoRecord.iso_source` values `current`, `old`, or `missing`.

- [ ] **Step 1: Update collector tests for current status**

In `tests/test_collector.py`, update `test_collect_record_builds_complete_pending_record()`:

Replace:

```python
    record = collector.collect_record("noble", "amd64")
```

with:

```python
    record = collector.collect_record("noble", "amd64", now=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc))
```

Replace:

```python
    assert record.iso_source == "pending"
```

with:

```python
    assert record.iso_source == "current"
```

- [ ] **Step 2: Add old status test**

In `tests/test_collector.py`, after `test_collect_record_builds_complete_pending_record()`, add:

```python
def test_collect_record_marks_found_iso_old_when_published_before_run_date():
    responses = {
        PENDING_URL: '<a href="noble-desktop-amd64.iso">noble-desktop-amd64.iso</a> 2026-06-28 23:59\n<a href="noble-desktop-amd64.manifest">noble-desktop-amd64.manifest</a> 2026-06-29 10:16',
        MANIFEST_URL: "snap:ubuntu-desktop-bootstrap 1.2.3 42\nsnap:snapd 2.70 24718\nsnapd 2.70+ubuntu1\n",
    }
    collector = Collector(lambda url: responses[url], FakeResolver(), FakeSnapcraftResolver())

    record = collector.collect_record("noble", "amd64", now=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc))

    assert record.iso_source == "old"
    assert record.published_at == "2026-06-28T23:59:00Z"
```

- [ ] **Step 3: Add unparsable/missing timestamp test**

In `tests/test_collector.py`, after the old status test, add:

```python
def test_collect_record_marks_found_iso_old_when_timestamp_missing():
    responses = {
        PENDING_URL: '<a href="noble-desktop-amd64.iso">noble-desktop-amd64.iso</a>\n<a href="noble-desktop-amd64.manifest">noble-desktop-amd64.manifest</a> 2026-06-29 10:16',
        MANIFEST_URL: "snap:ubuntu-desktop-bootstrap 1.2.3 42\nsnap:snapd 2.70 24718\nsnapd 2.70+ubuntu1\n",
    }
    collector = Collector(lambda url: responses[url], FakeResolver(), FakeSnapcraftResolver())

    record = collector.collect_record("noble", "amd64", now=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc))

    assert record.iso_source == "old"
    assert record.published_at is None
```

- [ ] **Step 4: Run collector tests and verify failure**

Run: `python3 -m pytest tests/test_collector.py -v`

Expected: FAIL because `collect_record()` does not accept `now` and still returns `pending`.

- [ ] **Step 5: Widen model status type**

In `src/iso_dashboard/models.py`, replace:

```python
IsoSource = Literal["pending", "missing"]
```

with:

```python
IsoSource = Literal["current", "old", "missing"]
```

- [ ] **Step 6: Implement collector classification helper**

In `src/iso_dashboard/collector.py`, after `_format_time()`, add:

```python
def _iso_status(published_at: str | None, now: datetime) -> str:
    if not published_at:
        return "old"
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return "old"
    return "current" if published.astimezone(timezone.utc).date() == now.astimezone(timezone.utc).date() else "old"
```

- [ ] **Step 7: Pass run date into collect_record**

In `src/iso_dashboard/collector.py`, change the signature:

```python
    def collect_record(self, release: str, architecture: str) -> IsoRecord:
```

to:

```python
    def collect_record(self, release: str, architecture: str, now: datetime | None = None) -> IsoRecord:
```

After initializing `warnings`, add:

```python
        run_time = now if now is not None else _utc_now()
```

Replace the `iso_source` argument:

```python
            iso_source="pending" if iso and manifest else "missing",
```

with:

```python
            iso_source=_iso_status(iso.modified, run_time) if iso and manifest else "missing",
```

- [ ] **Step 8: Use one run timestamp for collect_all**

In `src/iso_dashboard/collector.py`, replace `collect_all()` body:

```python
        generated_at = _format_time(now if now is not None else _utc_now())
        records = tuple(self.collect_record(release, architecture) for release in RELEASES for architecture in ARCHITECTURES)
```

with:

```python
        run_time = now if now is not None else _utc_now()
        generated_at = _format_time(run_time)
        records = tuple(self.collect_record(release, architecture, now=run_time) for release in RELEASES for architecture in ARCHITECTURES)
```

- [ ] **Step 9: Run collector tests**

Run: `python3 -m pytest tests/test_collector.py -v`

Expected: PASS.

---

### Task 2: Render Status Colors And Friendly Timestamps

**Files:**
- Modify: `src/iso_dashboard/render.py`
- Modify: `tests/test_render.py`

**Interfaces:**
- Consumes: records with `iso_source` values `current`, `old`, and `missing`.
- Produces: generated HTML with green/yellow/red status styling and friendly timestamp text.

- [ ] **Step 1: Update render sample payload statuses**

In `tests/test_render.py`, change the first record status:

```python
                "iso_source": "pending",
```

to:

```python
                "iso_source": "current",
```

Add a third record to `sample_payload()["records"]` after the existing arm64 missing record:

```python
            {
                "release": "noble-old",
                "architecture": "amd64",
                "iso_source": "old",
                "iso_url": "https://cdimage.ubuntu.com/noble-old/daily-live/pending/noble-old-desktop-amd64.iso",
                "manifest_url": "https://cdimage.ubuntu.com/noble-old/daily-live/pending/noble-old-desktop-amd64.manifest",
                "published_at": "2026-06-28T22:05:00Z",
                "ubuntu_desktop_bootstrap": None,
                "snapd_snap": None,
                "snapd_deb": None,
                "subiquity": None,
                "secboot": None,
                "warnings": [],
            },
```

- [ ] **Step 2: Update render assertions**

In `test_render_dashboard_includes_summary_table_and_links()`, replace:

```python
    assert 'data-status="pending"' in html
```

with:

```python
    assert 'data-status="current"' in html
    assert 'data-status="old"' in html
```

Replace:

```python
    assert "Generated: 2026-06-29T12:00:00Z" in html
```

with the same line unchanged; generated timestamp stays raw.

Add assertions near timestamp/status color assertions:

```python
    assert "29 Jun 2026, 10:15 UTC" in html
    assert "28 Jun 2026, 22:05 UTC" in html
    assert "is-current-iso" in html
    assert "is-old-iso" in html
    assert "is-missing-iso" in html
    assert "background: #f2fbf3" in html
    assert "background: #fff8e6" in html
    assert "background: #fff2f2" in html
```

Replace old status/color assertions if present:

```python
    assert "is-existing-iso" in html
```

with no assertion for `is-existing-iso`.

- [ ] **Step 3: Run render tests and verify failure**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: FAIL because renderer still knows `pending` / `is-existing-iso` and raw timestamps.

- [ ] **Step 4: Update status chip and card class mapping**

In `src/iso_dashboard/render.py`, replace `_status()` with:

```python
def _status(value: object) -> str:
    status = escape(str(value or "missing"))
    chip_class = {
        "current": "p-chip--positive",
        "old": "p-chip--caution",
        "missing": "p-chip--negative",
    }.get(status, "p-chip--negative")
    return f'<span class="{chip_class}">{status}</span>'
```

Replace `_card_status_class()` with:

```python
def _card_status_class(status: str) -> str:
    return {
        "current": "is-current-iso",
        "old": "is-old-iso",
        "missing": "is-missing-iso",
    }.get(status, "is-missing-iso")
```

- [ ] **Step 5: Add friendly timestamp helper**

In `src/iso_dashboard/render.py`, ensure `datetime` is imported:

```python
from datetime import datetime, timezone
```

After `_card_status_class()`, add:

```python
def _published_at(value: object) -> str:
    if not value:
        return "unknown"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    return escape(parsed.astimezone(timezone.utc).strftime("%-d %b %Y, %H:%M UTC"))
```

- [ ] **Step 6: Use friendly timestamp helper**

In `src/iso_dashboard/render.py`, replace:

```python
              <p><strong>Published:</strong> {escape(str(record.get("published_at") or "unknown"))}</p>
```

with:

```python
              <p><strong>Published:</strong> {_published_at(record.get("published_at"))}</p>
```

- [ ] **Step 7: Update inline card CSS**

In `src/iso_dashboard/render.py`, replace:

```css
    .is-existing-iso { background: #f2fbf3; border-top: 4px solid #0e8420; }
    .is-missing-iso { background: #fff2f2; border-top: 4px solid #c7162b; }
```

with:

```css
    .is-current-iso { background: #f2fbf3; border-top: 4px solid #0e8420; }
    .is-old-iso { background: #fff8e6; border-top: 4px solid #f99b11; }
    .is-missing-iso { background: #fff2f2; border-top: 4px solid #c7162b; }
```

- [ ] **Step 8: Run render tests**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS.

---

### Task 3: Full Verification And Generated HTML Check

**Files:**
- Modify: none expected
- Test: full suite and generated dashboard HTML

**Interfaces:**
- Consumes: completed Task 1 and Task 2 behavior.
- Produces: verified current/old/missing status behavior.

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Generate dashboard site**

Run: `PYTHONPATH=src python3 -m iso_dashboard.cli render --data data/latest.json --site /tmp/opencode/iso-dashboard-site`

Expected: command exits 0 and writes `/tmp/opencode/iso-dashboard-site/index.html`.

- [ ] **Step 3: Inspect generated HTML**

Run: `python3 - <<'PY'
from pathlib import Path
html = Path('/tmp/opencode/iso-dashboard-site/index.html').read_text()
assert 'data-status="current"' in html or 'data-status="old"' in html or 'data-status="missing"' in html
assert 'is-current-iso' in html or 'is-old-iso' in html or 'is-missing-iso' in html
assert 'Published:</strong> unknown' in html or 'UTC</p>' in html
assert 'is-existing-iso' not in html
print('generated dashboard ISO statuses verified')
PY`

Expected: prints `generated dashboard ISO statuses verified`.

---

## Plan Self-Review

- Spec coverage: Task 1 handles collector status classification and model typing. Task 2 handles UI chip/class/color mapping and friendly timestamps. Task 3 verifies full behavior and generated HTML.
- Placeholder scan: no placeholders, deferred implementation notes, or undefined future work remain.
- Type consistency: `IsoSource` includes `current`, `old`, and `missing`; collector and renderer use those exact strings.
