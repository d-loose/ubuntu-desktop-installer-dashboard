# Dashboard Architecture Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Group dashboard cards by architecture, default to `amd64`, and use a single architecture dropdown while cards show release names.

**Architecture:** Keep the existing Python static renderer in `src/iso_dashboard/render.py`. Replace release/status filtering with architecture-only filtering by changing rendered data attributes, section grouping, dropdown options, and the inline JavaScript filter function.

**Tech Stack:** Python 3.12+, pytest, static HTML, Vanilla Framework hotlinked CSS, inline JavaScript.

## Global Constraints

- Only generated dashboard HTML and render tests change.
- Do not change collection, parsing, data schema, scheduled publishing, or add a frontend build step.
- Group cards by architecture instead of release.
- Show only the `amd64` architecture by default when it is present.
- Replace the existing release and status filters with a single `Architecture` dropdown.
- Populate the architecture dropdown from `payload["architectures"]`.
- Select `amd64` by default when available; otherwise select the first configured architecture.
- Change card titles from architecture names to release names.
- Keep generated timestamp, Suru title strip, status chips, card status colors, and warning details.
- Keep `data-status` for card metadata, but filtering only uses architecture.
- Hide architecture sections with no visible cards after filtering.
- Preserve existing source-ref formatting and URL hardening behavior.

---

## File Structure

- Modify `src/iso_dashboard/render.py`: group cards by architecture, render architecture dropdown, card title release, architecture-only filter JavaScript.
- Modify `tests/test_render.py`: update sample data to include multiple architectures and assert architecture dropdown/default/filter behavior.
- No new modules are needed.

---

### Task 1: Architecture Grouping And Filter

**Files:**
- Modify: `tests/test_render.py`
- Modify: `src/iso_dashboard/render.py`

**Interfaces:**
- Consumes: `render_dashboard(payload: dict[str, object]) -> str`
- Produces: generated HTML grouped by `data-architecture-section`, cards with release titles, and architecture-only filtering.

- [ ] **Step 1: Write failing render assertions**

In `tests/test_render.py`, update `sample_payload()` top-level architecture list:

```python
        "architectures": ["amd64", "arm64"],
```

In `test_render_dashboard_includes_summary_table_and_links()`, replace filter/section assertions:

```python
    assert "data-release-filter" in html
    assert "data-status-filter" in html
    assert "data-release-section" in html
```

with:

```python
    assert "data-architecture-filter" in html
    assert "data-release-filter" not in html
    assert "data-status-filter" not in html
    assert "data-architecture-section" in html
```

Replace status option assertions:

```python
    assert 'option value="pending">pending</option>' in html
    assert 'option value="missing">missing</option>' in html
```

with:

```python
    assert '<option value="amd64" selected>amd64</option>' in html
    assert '<option value="arm64">arm64</option>' in html
```

Add these assertions near the other data attribute assertions:

```python
    assert 'data-architecture="amd64"' in html
    assert 'data-architecture="arm64"' in html
    assert 'data-architecture-section="amd64"' in html
    assert 'data-architecture-section="arm64"' in html
```

Replace:

```python
    assert "card.style.display = visible ? '' : 'none'" in html
```

with:

```python
    assert "const architecture = architectureFilter.value" in html
    assert "card.dataset.architecture === architecture" in html
    assert "card.style.display = visible ? '' : 'none'" in html
```

Add:

```python
    assert "data-status-filter" not in html
    assert "statusFilter" not in html
```

- [ ] **Step 2: Run focused test and verify it fails**

Run: `python3 -m pytest tests/test_render.py::test_render_dashboard_includes_summary_table_and_links -v`

Expected: FAIL because the renderer still uses release and status filters, release sections, and architecture card titles.

- [ ] **Step 3: Change card grouping and title**

In `src/iso_dashboard/render.py`, rename the section accumulator and group by architecture.

Replace:

```python
    cards_by_release: dict[str, list[str]] = {}
```

with:

```python
    cards_by_architecture: dict[str, list[str]] = {}
```

Replace the card wrapper and title block:

```python
          <div class="col-4" data-iso-card data-release="{escape(release, quote=True)}" data-status="{escape(status, quote=True)}">
            <div class="p-card--highlighted {card_status_class}">
              <div class="u-clearfix">
                <h3>{escape(architecture)}</h3>
                <p class="u-align--right">{_status(status)}</p>
              </div>
```

with:

```python
          <div class="col-4" data-iso-card data-architecture="{escape(architecture, quote=True)}" data-release="{escape(release, quote=True)}" data-status="{escape(status, quote=True)}">
            <div class="p-card--highlighted {card_status_class}">
              <div class="u-clearfix">
                <h3>{escape(release)}</h3>
                <p class="u-align--right">{_status(status)}</p>
              </div>
```

Replace:

```python
        cards_by_release.setdefault(release, []).append(card)
```

with:

```python
        cards_by_architecture.setdefault(architecture, []).append(card)
```

- [ ] **Step 4: Render architecture dropdown options**

In `src/iso_dashboard/render.py`, replace the `releases` / `release_options` block:

```python
    releases = payload.get("releases", [])
    if not isinstance(releases, list):
        releases = []
    release_options = "".join(
        f"<option value=\"{escape(str(release), quote=True)}\">{escape(str(release))}</option>"
        for release in releases
    )
```

with:

```python
    architectures = payload.get("architectures", [])
    if not isinstance(architectures, list):
        architectures = []
    default_architecture = "amd64" if "amd64" in architectures else (str(architectures[0]) if architectures else "")
    architecture_options = "".join(
        f"<option value=\"{escape(str(architecture), quote=True)}\"{' selected' if str(architecture) == default_architecture else ''}>{escape(str(architecture))}</option>"
        for architecture in architectures
    )
```

- [ ] **Step 5: Render architecture sections**

In `src/iso_dashboard/render.py`, replace the `sections = "".join(...)` block with:

```python
    sections = "".join(
        f"""
    <section class="p-strip is-shallow" data-architecture-section="{escape(architecture, quote=True)}">
      <div class="row">
        <div class="col-12">
          <p class="p-muted-heading">Architecture</p>
          <h2>{escape(architecture)}</h2>
        </div>
      </div>
      <div class="row">{''.join(cards)}</div>
    </section>
"""
        for architecture, cards in cards_by_architecture.items()
    )
```

- [ ] **Step 6: Replace filters markup**

In `src/iso_dashboard/render.py`, replace the two filter groups with a single architecture group:

```html
            <div class="p-form__group">
              <label for="architecture-filter">Architecture</label>
              <select id="architecture-filter" data-architecture-filter>
                {architecture_options}
              </select>
            </div>
```

- [ ] **Step 7: Replace filter JavaScript**

In `src/iso_dashboard/render.py`, replace the DOMContentLoaded script body with architecture-only filtering:

```javascript
      const architectureFilter = document.querySelector('[data-architecture-filter]');
      if (!architectureFilter) {
        return;
      }

      function filterCards() {
        const architecture = architectureFilter.value;
        document.querySelectorAll('[data-iso-card]').forEach((card) => {
          const visible = !architecture || card.dataset.architecture === architecture;
          card.style.display = visible ? '' : 'none';
        });
        document.querySelectorAll('[data-architecture-section]').forEach((section) => {
          const hasVisibleCards = Array.from(section.querySelectorAll('[data-iso-card]')).some((card) => card.style.display !== 'none');
          section.hidden = !hasVisibleCards;
        });
      }

      architectureFilter.addEventListener('change', filterCards);
      filterCards();
```

- [ ] **Step 8: Run render tests**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS.

---

### Task 2: Full Verification And Generated HTML Check

**Files:**
- Modify: none expected
- Test: full suite and generated dashboard HTML

**Interfaces:**
- Consumes: completed Task 1 render behavior.
- Produces: verified architecture-filter dashboard.

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
assert 'data-architecture-filter' in html
assert 'data-release-filter' not in html
assert 'data-status-filter' not in html
assert 'data-architecture-section="amd64"' in html
assert 'data-architecture="amd64"' in html
assert '<option value="amd64" selected>amd64</option>' in html
assert 'statusFilter' not in html
print('generated dashboard architecture filter verified')
PY`

Expected: prints `generated dashboard architecture filter verified`.

---

## Plan Self-Review

- Spec coverage: Task 1 implements architecture grouping, architecture dropdown, default amd64, release card titles, filter removal, and architecture-only filtering. Task 2 verifies tests and generated HTML.
- Placeholder scan: no placeholders, deferred implementation notes, or undefined future work remain.
- Type consistency: all tasks use the existing `render_dashboard(payload: dict[str, object]) -> str` interface.
