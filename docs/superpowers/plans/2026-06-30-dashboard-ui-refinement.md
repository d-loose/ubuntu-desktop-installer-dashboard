# Dashboard UI Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the static dashboard UI, shorten source refs, and fix secboot GitHub commit links.

**Architecture:** Keep the existing Python static renderer in `src/iso_dashboard/render.py`. Add small render-time formatting helpers and update generated HTML markup to use more Vanilla Framework components without changing the data schema or collector.

**Tech Stack:** Python 3.12+, pytest, static HTML, Vanilla Framework hotlinked CSS.

## Global Constraints

- Only generated dashboard HTML and render tests change.
- Do not change collection, parsing, data schema, scheduled publishing, or add a frontend build step.
- Commit-like refs display as 7-character hashes.
- `secboot` Go pseudo-versions matching `v0.0.0-<timestamp>-<hash>` display as the final hash component shortened to 7 characters.
- `secboot` pseudo-version GitHub URLs are rewritten from `/tree/<pseudo-version>` to `/commit/<full-hash>`.
- Links keep the original full ref in a `title` attribute when display text differs.
- Unsafe `javascript:` URLs remain suppressed.
- Existing filters and section hiding behavior must keep working.

---

## File Structure

- Modify `src/iso_dashboard/render.py`: source-ref formatting helpers, card markup, summary markup, warning notification markup, Vanilla stylesheet URL.
- Modify `tests/test_render.py`: render tests for shortened refs, secboot link rewrite, security behavior, and Vanilla component classes.
- No new source modules are needed; the renderer is small and already owns HTML formatting.

---

### Task 1: Source Reference Formatting

**Files:**
- Modify: `tests/test_render.py`
- Modify: `src/iso_dashboard/render.py`

**Interfaces:**
- Consumes: `render_dashboard(payload: dict[str, object]) -> str`
- Produces: `_source(value: dict[str, object] | None) -> str` that displays shortened refs and rewritten secboot commit links.

- [ ] **Step 1: Update the sample payload with full source refs**

In `tests/test_render.py`, replace the `subiquity` and `secboot` entries in `sample_payload()` with full-length refs:

```python
                "subiquity": {
                    "name": "subiquity",
                    "ref": "64b0c70ec29dcc597a1f554486c61fcd634ce86d",
                    "url": "https://github.com/canonical/subiquity/commit/64b0c70ec29dcc597a1f554486c61fcd634ce86d",
                },
                "secboot": {
                    "name": "secboot",
                    "ref": "v0.0.0-20260302105957-77bc2457cc76",
                    "url": "https://github.com/snapcore/secboot/tree/v0.0.0-20260302105957-77bc2457cc76",
                },
```

- [ ] **Step 2: Write failing source-format assertions**

In `tests/test_render.py`, update `test_render_dashboard_includes_summary_table_and_links()` by replacing the old source assertions with:

```python
    assert ">64b0c70<" in html
    assert 'title="64b0c70ec29dcc597a1f554486c61fcd634ce86d"' in html
    assert "https://github.com/canonical/subiquity/commit/64b0c70ec29dcc597a1f554486c61fcd634ce86d" in html
    assert ">77bc245<" in html
    assert 'title="v0.0.0-20260302105957-77bc2457cc76"' in html
    assert "https://github.com/snapcore/secboot/commit/77bc2457cc76" in html
    assert "https://github.com/snapcore/secboot/tree/v0.0.0-20260302105957-77bc2457cc76" not in html
```

- [ ] **Step 3: Run the focused test and verify it fails**

Run: `python3 -m pytest tests/test_render.py::test_render_dashboard_includes_summary_table_and_links -v`

Expected: FAIL because the rendered HTML still shows full refs and the old secboot tree URL.

- [ ] **Step 4: Implement source formatting helpers**

In `src/iso_dashboard/render.py`, add this import near the top:

```python
import re
```

Add these constants after `VANILLA_CSS`:

```python
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
SECBOOT_PSEUDO_VERSION_RE = re.compile(r"^v0\.0\.0-\d{14}-([0-9a-f]{12,40})$", re.IGNORECASE)
```

Replace `_source()` with:

```python
def _source(value: dict[str, object] | None) -> str:
    if not value or not value.get("ref"):
        return "unknown"
    raw_ref = str(value["ref"])
    display_ref = raw_ref
    url = value.get("url")
    raw_url = str(url).strip() if url else ""
    pseudo_version = SECBOOT_PSEUDO_VERSION_RE.fullmatch(raw_ref)
    if pseudo_version:
        commit = pseudo_version.group(1)
        display_ref = commit[:7]
        raw_url = f"https://github.com/snapcore/secboot/commit/{commit}"
    elif COMMIT_RE.fullmatch(raw_ref):
        display_ref = raw_ref[:7]

    ref = escape(display_ref)
    title = f' title="{escape(raw_ref, quote=True)}"' if display_ref != raw_ref else ""
    if raw_url:
        if raw_url.lower().startswith("javascript:"):
            return ref
        return f'<a href="{escape(raw_url, quote=True)}"{title}>{ref}</a>'
    return ref
```

- [ ] **Step 5: Run source-format tests and verify they pass**

Run: `python3 -m pytest tests/test_render.py::test_render_dashboard_includes_summary_table_and_links tests/test_render.py::test_escapes_malicious_html_in_warnings_and_source -v`

Expected: PASS. The malicious URL test must still pass because `javascript:` URLs return plain escaped text.

- [ ] **Step 6: Commit source formatting**

Run:

```bash
git add src/iso_dashboard/render.py tests/test_render.py
git commit -m "Fix dashboard source ref display"
```

Expected: commit succeeds if committing is part of the execution workflow. If the user has not requested commits, skip this step.

---

### Task 2: Vanilla UI Components

**Files:**
- Modify: `tests/test_render.py`
- Modify: `src/iso_dashboard/render.py`

**Interfaces:**
- Consumes: `render_dashboard(payload: dict[str, object]) -> str`, `_warnings(values: list[str]) -> str`, `_status(value: object) -> str`, `_detail(label: str, value: str) -> str`
- Produces: dashboard HTML with Suru/hero strip, summary cards, release headers, warning notifications, and existing filter data attributes.

- [ ] **Step 1: Write failing Vanilla UI assertions**

In `tests/test_render.py`, add these assertions to `test_render_dashboard_includes_summary_table_and_links()` after the existing Vanilla class assertions:

```python
    assert "p-strip--suru" in html
    assert "p-card--highlighted" in html
    assert "p-muted-heading" in html
    assert "p-notification--caution" in html
    assert "p-notification__message" in html
    assert "u-align--right" in html
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python3 -m pytest tests/test_render.py::test_render_dashboard_includes_summary_table_and_links -v`

Expected: FAIL because the new Vanilla component classes are not all rendered yet.

- [ ] **Step 3: Update warning notification markup**

In `src/iso_dashboard/render.py`, replace `_warnings()` with:

```python
def _warnings(values: list[str]) -> str:
    if not values:
        return "No warnings"
    return "".join(
        """
        <div class="p-notification--caution is-borderless">
          <div class="p-notification__content">
            <p class="p-notification__message">{message}</p>
          </div>
        </div>
""".format(message=escape(value))
        for value in values
    )
```

- [ ] **Step 4: Update card details and release section markup**

In `src/iso_dashboard/render.py`, replace `_detail()` with:

```python
def _detail(label: str, value: str) -> str:
    return f'<dt class="p-muted-heading">{escape(label)}</dt><dd>{value}</dd>'
```

In `render_dashboard()`, replace the `warning_body` assignment with:

```python
        warning_body = warning_content if warnings else '<p><span class="p-chip--positive">No warnings</span></p>'
```

Replace the `card = f"""..."""` block with:

```python
        card = f"""
          <div class="col-4" data-iso-card data-release="{escape(release, quote=True)}" data-status="{escape(status, quote=True)}">
            <div class="p-card--highlighted">
              <div class="u-clearfix">
                <h3>{escape(architecture)}</h3>
                <p class="u-align--right">{_status(status)}</p>
              </div>
              <p><strong>Published:</strong> {escape(str(record.get("published_at") or "unknown"))}</p>
              <dl>{details}</dl>
              <details>
                <summary>{warning_count} warnings</summary>
                {warning_body}
              </details>
            </div>
          </div>
"""
```

Replace the `sections = "".join(...)` template with:

```python
    sections = "".join(
        f"""
    <section class="p-strip is-shallow" data-release-section="{escape(release, quote=True)}">
      <div class="row">
        <div class="col-12">
          <p class="p-muted-heading">Release</p>
          <h2>{escape(release)}</h2>
        </div>
      </div>
      <div class="row">{''.join(cards)}</div>
    </section>
"""
        for release, cards in cards_by_release.items()
    )
```

- [ ] **Step 5: Update hero and summary markup**

In `src/iso_dashboard/render.py`, after the existing `releases` type check block, add:

```python
    release_count = len(releases) if isinstance(releases, list) else len(cards_by_release)
```

In `render_dashboard()`, replace the first main `<section class="p-strip is-shallow">...</section>` with:

```python
    <section class="p-strip--suru is-dark">
      <div class="row">
        <div class="col-8">
          <h1>Ubuntu Desktop ISO Dashboard</h1>
          <p>Generated: {generated_at}</p>
        </div>
      </div>
    </section>
    <section class="p-strip is-shallow">
      <div class="row">
        <div class="col-4">
          <div class="p-card--highlighted">
            <p class="p-muted-heading">Records</p>
            <p class="p-heading--2">{len(records)}</p>
          </div>
        </div>
        <div class="col-4">
          <div class="p-card--highlighted">
            <p class="p-muted-heading">Warnings</p>
            <p class="p-heading--2">{warning_count}</p>
          </div>
        </div>
        <div class="col-4">
          <div class="p-card--highlighted">
            <p class="p-muted-heading">Releases</p>
            <p class="p-heading--2">{release_count}</p>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <form class="p-form p-form--inline" aria-label="Dashboard filters">
            <div class="p-form__group">
              <label for="release-filter">Release</label>
              <select id="release-filter" data-release-filter>
                <option value="">All releases</option>
                {release_options}
              </select>
            </div>
            <div class="p-form__group">
              <label for="status-filter">Status</label>
              <select id="status-filter" data-status-filter>
                <option value="">All statuses</option>
                <option value="pending">pending</option>
                <option value="missing">missing</option>
              </select>
            </div>
          </form>
        </div>
      </div>
    </section>
```

- [ ] **Step 6: Run render tests and verify they pass**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS.

- [ ] **Step 7: Commit Vanilla UI refinements**

Run:

```bash
git add src/iso_dashboard/render.py tests/test_render.py
git commit -m "Improve dashboard Vanilla UI"
```

Expected: commit succeeds if committing is part of the execution workflow. If the user has not requested commits, skip this step.

---

### Task 3: Full Verification

**Files:**
- Modify: none expected
- Test: full repository test suite

**Interfaces:**
- Consumes: all previous tasks.
- Produces: verified working dashboard render behavior.

- [ ] **Step 1: Run all tests**

Run: `python3 -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Generate the dashboard locally**

Run: `PYTHONPATH=src python3 -m iso_dashboard.cli render --data data/latest.json --site /tmp/opencode/iso-dashboard-site`

Expected: command exits 0 and writes `/tmp/opencode/iso-dashboard-site/index.html`.

- [ ] **Step 3: Inspect generated HTML for source refs**

Run: `python3 - <<'PY'
from pathlib import Path
html = Path('/tmp/opencode/iso-dashboard-site/index.html').read_text()
assert 'v0.0.0-20260302105957-77bc2457cc76</a>' not in html
assert 'https://github.com/snapcore/secboot/commit/77bc2457cc76' in html
assert '>77bc245<' in html
print('generated dashboard source refs verified')
PY`

Expected: prints `generated dashboard source refs verified`.

- [ ] **Step 4: Check git diff**

Run: `git diff -- src/iso_dashboard/render.py tests/test_render.py docs/superpowers/specs/2026-06-30-dashboard-ui-refinement-design.md docs/superpowers/plans/2026-06-30-dashboard-ui-refinement.md`

Expected: diff only contains the intended render, test, spec, and plan changes.

---

## Plan Self-Review

- Spec coverage: Task 1 covers source shortening, secboot pseudo-version cleanup, link rewrite, title attributes, and unsafe URL suppression. Task 2 covers Vanilla visual hierarchy, summary cards, warning notifications, release headers, and preserving filters. Task 3 covers full verification and generated HTML inspection.
- Placeholder scan: no placeholders, deferred implementation notes, or undefined future work remain.
- Type consistency: all tasks use the existing `render_dashboard(payload: dict[str, object]) -> str` interface and local helper functions in `src/iso_dashboard/render.py`.
