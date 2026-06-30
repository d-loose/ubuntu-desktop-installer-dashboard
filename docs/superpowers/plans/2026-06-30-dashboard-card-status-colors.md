# Dashboard Card Status Colors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the dashboard navigation and summary cards while coloring each architecture card by ISO availability.

**Architecture:** Keep the existing Python static renderer in `src/iso_dashboard/render.py`. Add a tiny status-to-card-class helper and inline CSS in the generated HTML; update render tests to lock the simplified header and red/green card behavior.

**Tech Stack:** Python 3.12+, pytest, static HTML, Vanilla Framework hotlinked CSS, small inline CSS.

## Global Constraints

- Only generated dashboard HTML and render tests change.
- Do not change collection, parsing, data schema, scheduled publishing, or add a frontend build step.
- Remove the Vanilla navigation header from the generated page.
- Remove the summary cards for record count, warning count, and release count.
- Keep the Suru title strip with dashboard title and generated timestamp.
- Keep release and status filters in a shallow strip under the title.
- Keep existing card grouping by release and existing filter JavaScript behavior.
- Add `is-existing-iso` for non-missing ISO statuses such as `pending`.
- Add `is-missing-iso` for `missing`.
- Add green-tinted background and border for `is-existing-iso` cards.
- Add red-tinted background and border for `is-missing-iso` cards.
- Preserve existing source-ref formatting and URL hardening behavior.

---

## File Structure

- Modify `src/iso_dashboard/render.py`: card class helper, inline CSS, remove navigation header, remove summary card row, keep filters.
- Modify `tests/test_render.py`: expectations for absent navigation/summary and present status color classes/styles.
- No new modules are needed.

---

### Task 1: Simplify Header And Color Cards

**Files:**
- Modify: `tests/test_render.py`
- Modify: `src/iso_dashboard/render.py`

**Interfaces:**
- Consumes: `render_dashboard(payload: dict[str, object]) -> str`
- Produces: generated HTML without navigation/summary markup and with `is-existing-iso` / `is-missing-iso` classes on card containers.

- [ ] **Step 1: Write failing render assertions**

In `tests/test_render.py`, update `test_render_dashboard_includes_summary_table_and_links()`:

Replace:

```python
    assert "p-navigation" in html
```

with:

```python
    assert "p-navigation" not in html
```

Keep the existing `p-strip` assertion.

After the existing `assert "u-align--right" in html`, add:

```python
    assert "is-existing-iso" in html
    assert "is-missing-iso" in html
    assert "background: #f2fbf3" in html
    assert "background: #fff2f2" in html
    assert "Records" not in html
    assert "Warnings</p>" not in html
    assert "Releases</p>" not in html
```

- [ ] **Step 2: Run focused test and verify it fails**

Run: `python3 -m pytest tests/test_render.py::test_render_dashboard_includes_summary_table_and_links -v`

Expected: FAIL because navigation and summary still render and card status color classes/styles are not present.

- [ ] **Step 3: Add card status helper**

In `src/iso_dashboard/render.py`, after `_status()` add:

```python
def _card_status_class(status: str) -> str:
    return "is-missing-iso" if status == "missing" else "is-existing-iso"
```

- [ ] **Step 4: Apply status classes to cards**

In `src/iso_dashboard/render.py`, inside `render_dashboard()`, after:

```python
        status = str(record.get("iso_source", "missing"))
```

add:

```python
        card_status_class = _card_status_class(status)
```

Then replace the card wrapper line:

```python
          <div class="col-4" data-iso-card data-release="{escape(release, quote=True)}" data-status="{escape(status, quote=True)}">
            <div class="p-card--highlighted">
```

with:

```python
          <div class="col-4" data-iso-card data-release="{escape(release, quote=True)}" data-status="{escape(status, quote=True)}">
            <div class="p-card--highlighted {card_status_class}">
```

- [ ] **Step 5: Add inline card color CSS**

In the returned HTML `<head>` block in `src/iso_dashboard/render.py`, immediately after the Vanilla CSS `<link>`, add:

```html
  <style>
    .is-existing-iso { background: #f2fbf3; border-top: 4px solid #0e8420; }
    .is-missing-iso { background: #fff2f2; border-top: 4px solid #c7162b; }
  </style>
```

- [ ] **Step 6: Remove navigation header**

In `src/iso_dashboard/render.py`, remove the full generated HTML block from:

```html
  <header class="p-navigation">
```

through:

```html
  </header>
```

The `<body>` should contain `<main>` directly.

- [ ] **Step 7: Remove summary cards but keep filters**

In `src/iso_dashboard/render.py`, remove the first `<div class="row">` inside the shallow strip after the Suru title that contains the `Records`, `Warnings`, and `Releases` cards. Keep the following filter form row intact.

Also remove these now-unused values:

```python
    warning_count = sum(len(record.get("warnings", [])) for record in records if isinstance(record, dict))
```

and:

```python
    # count releases for the summary cards
    release_count = len(releases) if isinstance(releases, list) else len(cards_by_release)
```

- [ ] **Step 8: Run render tests**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS.

- [ ] **Step 9: Run full test suite**

Run: `python3 -m pytest -v`

Expected: PASS.

---

### Task 2: Generated Site Smoke Check

**Files:**
- Modify: none expected
- Test: generated dashboard HTML

**Interfaces:**
- Consumes: completed Task 1 render behavior.
- Produces: evidence that generated `data/latest.json` output includes simplified header and status color classes.

- [ ] **Step 1: Generate dashboard site**

Run: `PYTHONPATH=src python3 -m iso_dashboard.cli render --data data/latest.json --site /tmp/opencode/iso-dashboard-site`

Expected: command exits 0 and writes `/tmp/opencode/iso-dashboard-site/index.html`.

- [ ] **Step 2: Inspect generated HTML**

Run: `python3 - <<'PY'
from pathlib import Path
html = Path('/tmp/opencode/iso-dashboard-site/index.html').read_text()
assert 'p-navigation' not in html
assert 'Records</p>' not in html
assert 'Warnings</p>' not in html
assert 'Releases</p>' not in html
assert 'is-existing-iso' in html
assert 'is-missing-iso' in html
assert 'data-release-filter' in html
assert 'data-status-filter' in html
print('generated dashboard simplified header and status colors verified')
PY`

Expected: prints `generated dashboard simplified header and status colors verified`.

---

## Plan Self-Review

- Spec coverage: Task 1 removes navigation, removes summary cards, keeps title and filters, adds status classes, adds red/green styles, and preserves existing tests. Task 2 verifies generated output.
- Placeholder scan: no placeholders, deferred implementation notes, or undefined future work remain.
- Type consistency: all tasks use the existing `render_dashboard(payload: dict[str, object]) -> str` interface and a local `_card_status_class(status: str) -> str` helper.
