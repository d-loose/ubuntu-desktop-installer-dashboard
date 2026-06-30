# Snap Channel Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse snap manifest channel separately from resolved snap version and store that channel in JSON.

**Architecture:** Extend the existing `PackageVersion` dataclass with an optional `channel` field. Parse snap manifest values into `channel`, preserve the channel while Snapcraft fills `version`, and update rendering/tests to show both resolved version and channel.

**Tech Stack:** Python 3.12+, pytest, dataclasses, static HTML.

## Global Constraints

- `PackageVersion` has fields `name`, `version`, `revision`, and optional `channel`.
- Snap manifest lines store the second field as `channel`, not `version`.
- Snap manifest lines store the third field as `revision`.
- Deb manifest lines keep the second field as `version`, with `channel=None` and `revision=None`.
- `SnapcraftResolver.resolve_revision()` preserves the original `channel` while filling resolved `version`.
- JSON includes `channel` for all package objects through dataclass serialization.
- Renderer displays snap packages with resolved version, channel, and revision when available.
- Existing source-ref, ISO status, and architecture filter behavior must remain unchanged.

---

## File Structure

- Modify `src/iso_dashboard/models.py`: add `channel` field to `PackageVersion`.
- Modify `src/iso_dashboard/parsers.py`: parse snap manifest channel into `channel` and leave `version=None`.
- Modify `src/iso_dashboard/snapcraft.py`: preserve channel when returning resolved version.
- Modify `src/iso_dashboard/render.py`: show channel in package display.
- Modify tests and fixture: `tests/fixtures/example.manifest`, `tests/test_parsers.py`, `tests/test_snapcraft.py`, `tests/test_collector.py`, `tests/test_config_models.py`, `tests/test_render.py`.

---

### Task 1: Model And Parser Channel Support

**Files:**
- Modify: `src/iso_dashboard/models.py`
- Modify: `src/iso_dashboard/parsers.py`
- Modify: `tests/fixtures/example.manifest`
- Modify: `tests/test_parsers.py`
- Modify: `tests/test_config_models.py`

**Interfaces:**
- Consumes: `parse_manifest(text: str) -> ManifestVersions`.
- Produces: snap `PackageVersion` objects with `channel` set and `version=None` before Snapcraft resolution.

- [ ] **Step 1: Update manifest fixture**

Replace `tests/fixtures/example.manifest` contents with:

```text
snap:ubuntu-desktop-bootstrap 26.04/stable/ubuntu-26.04.1 42
snap:snapd stable 24718
snapd 2.70+ubuntu1
other-package 1.0
```

- [ ] **Step 2: Update parser expectations**

In `tests/test_parsers.py`, update `test_parse_manifest_extracts_snap_and_deb_versions()` so snap assertions are:

```python
    assert versions.ubuntu_desktop_bootstrap.version is None
    assert versions.ubuntu_desktop_bootstrap.channel == "26.04/stable/ubuntu-26.04.1"
    assert versions.ubuntu_desktop_bootstrap.revision == "42"
    assert versions.snapd_snap is not None
    assert versions.snapd_snap.version is None
    assert versions.snapd_snap.channel == "stable"
    assert versions.snapd_snap.revision == "24718"
```

Keep deb assertions and add:

```python
    assert versions.snapd_deb.channel is None
```

- [ ] **Step 3: Update JSON model test**

In `tests/test_config_models.py`, update PackageVersion constructors to include `channel` for snap package examples and `channel=None` for deb package examples:

```python
ubuntu_desktop_bootstrap=PackageVersion(name="ubuntu-desktop-bootstrap", version="1.2.3", revision="42", channel="26.04/stable/ubuntu-26.04.1"),
snapd_snap=PackageVersion(name="snapd", version="2.70", revision="24718", channel="stable"),
snapd_deb=PackageVersion(name="snapd", version="2.70+ubuntu1", revision=None, channel=None),
```

Update expected JSON package dictionaries to include `channel` keys with those values.

- [ ] **Step 4: Add channel field to model**

In `src/iso_dashboard/models.py`, add `channel` to `PackageVersion`:

```python
@dataclass(frozen=True)
class PackageVersion:
    name: str
    version: str | None
    revision: str | None
    channel: str | None = None
```

- [ ] **Step 5: Parse manifest snap channel**

In `src/iso_dashboard/parsers.py`, replace snap package construction:

```python
ubuntu_desktop_bootstrap = PackageVersion("ubuntu-desktop-bootstrap", parts[1], parts[2])
snapd_snap = PackageVersion("snapd", parts[1], parts[2])
```

with:

```python
ubuntu_desktop_bootstrap = PackageVersion("ubuntu-desktop-bootstrap", None, parts[2], parts[1])
snapd_snap = PackageVersion("snapd", None, parts[2], parts[1])
```

Keep deb parsing as `PackageVersion("snapd", parts[1], None)`.

- [ ] **Step 6: Run parser/model tests**

Run: `python3 -m pytest tests/test_parsers.py tests/test_config_models.py -v`

Expected: PASS.

---

### Task 2: Preserve Channel Through Snapcraft And Collector

**Files:**
- Modify: `src/iso_dashboard/snapcraft.py`
- Modify: `tests/test_snapcraft.py`
- Modify: `tests/test_collector.py`

**Interfaces:**
- Consumes: `SnapcraftResolver.resolve_revision(snap: PackageVersion, architecture: str)`.
- Produces: resolved `PackageVersion` with `version` filled and `channel` preserved.

- [ ] **Step 1: Update snapcraft tests**

In `tests/test_snapcraft.py`, update PackageVersion inputs and expected outputs to include channel:

```python
PackageVersion("ubuntu-desktop-bootstrap", None, "628", "26.04/stable/ubuntu-26.04.1")
```

and:

```python
assert resolved == PackageVersion("ubuntu-desktop-bootstrap", "26.04-3b3d4a4cc", "628", "26.04/stable/ubuntu-26.04.1")
```

For snapd tests, use `PackageVersion("snapd", None, "24718", "stable")` and expect the same channel to be preserved.

- [ ] **Step 2: Preserve channel in Snapcraft resolver**

In `src/iso_dashboard/snapcraft.py`, replace:

```python
return PackageVersion(snap.name, version, snap.revision), ()
```

with:

```python
return PackageVersion(snap.name, version, snap.revision, snap.channel), ()
```

- [ ] **Step 3: Update collector manifest fixtures and assertions**

In `tests/test_collector.py`, replace inline manifest text with channel-shaped snap values:

```text
snap:ubuntu-desktop-bootstrap 26.04/stable/ubuntu-26.04.1 42
snap:snapd stable 24718
snapd 2.70+ubuntu1
```

Update assertions:

```python
assert record.ubuntu_desktop_bootstrap.version == "26.04-3b3d4a4cc"
assert record.ubuntu_desktop_bootstrap.channel == "26.04/stable/ubuntu-26.04.1"
assert record.snapd_snap.version == "2.70.1"
assert record.snapd_snap.channel == "stable"
assert resolver.bootstrap == PackageVersion("ubuntu-desktop-bootstrap", "26.04-3b3d4a4cc", "42", "26.04/stable/ubuntu-26.04.1")
assert resolver.snapd == PackageVersion("snapd", "2.70.1", "24718", "stable")
```

Update `FakeSnapcraftResolver.resolve_revision()` to preserve channel:

```python
return PackageVersion(snap.name, versions[snap.name], snap.revision, snap.channel), ()
```

- [ ] **Step 4: Run snapcraft/collector tests**

Run: `python3 -m pytest tests/test_snapcraft.py tests/test_collector.py -v`

Expected: PASS.

---

### Task 3: Render Channel Values

**Files:**
- Modify: `src/iso_dashboard/render.py`
- Modify: `tests/test_render.py`

**Interfaces:**
- Consumes: package dictionaries with `version`, `revision`, and `channel`.
- Produces: HTML package text that includes channel for snap packages.

- [ ] **Step 1: Update render sample payload and expectations**

In `tests/test_render.py`, update snap package dictionaries:

```python
"ubuntu_desktop_bootstrap": {"name": "ubuntu-desktop-bootstrap", "version": "1.2.3", "revision": "42", "channel": "26.04/stable/ubuntu-26.04.1"},
"snapd_snap": {"name": "snapd", "version": "2.70", "revision": "24718", "channel": "stable"},
"snapd_deb": {"name": "snapd", "version": "2.70+ubuntu1", "revision": None, "channel": None},
```

Replace assertions:

```python
assert "1.2.3 (rev 42)" in html
assert "2.70 (rev 24718)" in html
```

with:

```python
assert "1.2.3 (channel 26.04/stable/ubuntu-26.04.1, rev 42)" in html
assert "2.70 (channel stable, rev 24718)" in html
```

- [ ] **Step 2: Update package renderer**

In `src/iso_dashboard/render.py`, replace `_package()` with:

```python
def _package(value: dict[str, object] | None) -> str:
    if not value or not value.get("version"):
        return "unknown"
    version = escape(str(value["version"]))
    revision = value.get("revision")
    channel = value.get("channel")
    details = []
    if channel:
        details.append(f"channel {escape(str(channel))}")
    if revision:
        details.append(f"rev {escape(str(revision))}")
    return f"{version} ({', '.join(details)})" if details else version
```

- [ ] **Step 3: Run render tests**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS.

---

### Task 4: Full Verification And Commit

**Files:**
- Modify: none expected beyond previous tasks.
- Test: full suite and generated site smoke check.

**Interfaces:**
- Consumes: completed channel parsing/resolution/render behavior.
- Produces: committed changes.

- [ ] **Step 1: Run full suite**

Run: `python3 -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Generate site smoke check**

Run: `PYTHONPATH=src python3 -m iso_dashboard.cli render --data data/latest.json --site /tmp/opencode/iso-dashboard-site`

Expected: command exits 0.

- [ ] **Step 3: Commit**

Run:

```bash
git add src/iso_dashboard/models.py src/iso_dashboard/parsers.py src/iso_dashboard/snapcraft.py src/iso_dashboard/render.py tests/fixtures/example.manifest tests/test_parsers.py tests/test_snapcraft.py tests/test_collector.py tests/test_config_models.py tests/test_render.py docs/superpowers/specs/2026-06-30-snap-channel-data-design.md docs/superpowers/plans/2026-06-30-snap-channel-data.md
git commit -m "Store snap channels in dashboard data"
```

Expected: commit succeeds.

---

## Plan Self-Review

- Spec coverage: Task 1 adds channel to model/parser/JSON, Task 2 preserves it through Snapcraft/collector, Task 3 renders it, Task 4 verifies and commits.
- Placeholder scan: no placeholders, deferred implementation notes, or undefined future work remain.
- Type consistency: `PackageVersion(name, version, revision, channel=None)` is used consistently across parser, resolver, collector, and tests.
