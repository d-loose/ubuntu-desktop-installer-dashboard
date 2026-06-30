# Subiquity Snap Channel Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the `subiquity` snap from the bootstrap snap channel and highlight whether it matches the resolved subiquity submodule commit.

**Architecture:** Add channel-based Snapcraft resolution, store `subiquity_snap` in `IsoRecord`, and compare the snap version hash suffix to the `subiquity` source ref at render time.

**Tech Stack:** Python 3.12+, pytest, dataclasses, Snapcraft refresh API, static HTML.

## Global Constraints

- Resolve `subiquity` snap using `ubuntu_desktop_bootstrap.channel` and the same architecture.
- Snapcraft channel resolution POSTs an install action with `channel`, not `revision`.
- Store resolved snap data in `IsoRecord.subiquity_snap` and JSON.
- Preserve existing `IsoRecord.subiquity` as the source submodule commit.
- Render both `subiquity snap` and `subiquity source` separately.
- Compare trailing git hash suffix from `subiquity_snap.version` with `subiquity.ref`.
- Show positive match, caution mismatch, or unknown comparison state.
- Add a warning when subiquity snap channel cannot be resolved.
- Preserve existing ISO status, architecture filter, source-ref formatting, and URL hardening.

---

## File Structure

- Modify `src/iso_dashboard/models.py`: add `subiquity_snap` to `IsoRecord`.
- Modify `src/iso_dashboard/snapcraft.py`: add channel-based resolution.
- Modify `src/iso_dashboard/collector.py`: resolve/store subiquity snap and warnings.
- Modify `src/iso_dashboard/render.py`: display subiquity snap/source and match status.
- Modify tests: `tests/test_snapcraft.py`, `tests/test_collector.py`, `tests/test_config_models.py`, `tests/test_render.py`.

---

### Task 1: Snapcraft Channel Resolution

**Files:**
- Modify: `src/iso_dashboard/snapcraft.py`
- Modify: `tests/test_snapcraft.py`

**Interfaces:**
- Produces: `SnapcraftResolver.resolve_channel(name: str, channel: str | None, architecture: str) -> tuple[PackageVersion | None, tuple[str, ...]]`.

- [ ] **Step 1: Add channel resolution test**

In `tests/test_snapcraft.py`, add:

```python
def test_resolve_channel_uses_snapcraft_refresh_api_request():
    requests = []

    def post_json(url, headers, payload):
        requests.append((url, headers, payload))
        return json.dumps(
            {
                "results": [
                    {
                        "snap": {
                            "name": "subiquity",
                            "version": "26.04-3b3d4a4cc",
                            "revision": 1234,
                        }
                    }
                ]
            }
        )

    resolver = SnapcraftResolver(post_json)

    resolved, warnings = resolver.resolve_channel("subiquity", "26.04/stable/ubuntu-26.04.1", "amd64")

    assert warnings == ()
    assert resolved == PackageVersion("subiquity", "26.04-3b3d4a4cc", "1234", "26.04/stable/ubuntu-26.04.1")
    assert requests == [
        (
            "https://api.snapcraft.io/v2/snaps/refresh",
            {
                "Snap-Device-Series": "16",
                "Snap-Device-Architecture": "amd64",
                "Content-Type": "application/json",
            },
            {
                "context": [],
                "actions": [
                    {
                        "action": "install",
                        "instance-key": "preview",
                        "name": "subiquity",
                        "channel": "26.04/stable/ubuntu-26.04.1",
                    }
                ],
            },
        )
    ]
```

- [ ] **Step 2: Implement channel resolution**

In `src/iso_dashboard/snapcraft.py`, add a shared request helper or a direct `resolve_channel()` method that mirrors `resolve_revision()` and posts `channel` instead of `revision`. Return `PackageVersion(name, version, revision, channel)` when the response includes the snap.

If `channel` is missing, return `(None, ("Cannot resolve <name> snap channel because channel is missing",))`.

- [ ] **Step 3: Run snapcraft tests**

Run: `python3 -m pytest tests/test_snapcraft.py -v`

Expected: PASS.

---

### Task 2: Collect Subiquity Snap

**Files:**
- Modify: `src/iso_dashboard/models.py`
- Modify: `src/iso_dashboard/collector.py`
- Modify: `tests/test_collector.py`
- Modify: `tests/test_config_models.py`

**Interfaces:**
- Produces: `IsoRecord.subiquity_snap: PackageVersion | None`.

- [ ] **Step 1: Add model field and config test expectation**

Add `subiquity_snap: PackageVersion | None` to `IsoRecord` after `ubuntu_desktop_bootstrap`.

Update `tests/test_config_models.py` constructor and expected JSON with a `subiquity_snap` object.

- [ ] **Step 2: Update fake Snapcraft resolver**

In `tests/test_collector.py`, add `resolve_channel()` to `FakeSnapcraftResolver` returning:

```python
return PackageVersion(name, "26.04-3b3d4a4cc", "1234", channel), ()
```

- [ ] **Step 3: Update collector tests**

In `test_collect_record_builds_complete_pending_record()`, assert:

```python
assert record.subiquity_snap == PackageVersion("subiquity", "26.04-3b3d4a4cc", "1234", "26.04/stable/ubuntu-26.04.1")
```

Update all `IsoRecord(...)` positional calls if needed for the new field.

- [ ] **Step 4: Implement collector resolution**

In `src/iso_dashboard/collector.py`, after resolving bootstrap by revision, call:

```python
subiquity_snap = None
if bootstrap is not None:
    subiquity_snap, subiquity_snap_warnings = self._snapcraft_resolver.resolve_channel("subiquity", bootstrap.channel, architecture)
    warnings.extend(subiquity_snap_warnings)
```

Pass `subiquity_snap=subiquity_snap` to `IsoRecord`.

- [ ] **Step 5: Run model/collector tests**

Run: `python3 -m pytest tests/test_config_models.py tests/test_collector.py -v`

Expected: PASS.

---

### Task 3: Render Comparison

**Files:**
- Modify: `src/iso_dashboard/render.py`
- Modify: `tests/test_render.py`

**Interfaces:**
- Consumes: `subiquity_snap` package object and `subiquity` source ref object.
- Produces: rendered match/mismatch/unknown comparison.

- [ ] **Step 1: Update render fixture and assertions**

In `sample_payload()`, add `subiquity_snap` to records:

```python
"subiquity_snap": {"name": "subiquity", "version": "26.04-64b0c70", "revision": "1234", "channel": "26.04/stable/ubuntu-26.04.1"},
```

Assert these strings exist:

```python
assert "subiquity snap" in html
assert "subiquity source" in html
assert "subiquity match" in html
assert "p-chip--positive" in html
```

Add a mismatch test by changing `subiquity_snap.version` to `26.04-deadbee` and asserting `subiquity mismatch` plus `p-chip--caution`.

- [ ] **Step 2: Add comparison helpers**

In `src/iso_dashboard/render.py`, add helpers:

```python
def _version_hash(value: dict[str, object] | None) -> str | None:
    if not value or not value.get("version"):
        return None
    match = re.search(r"-([0-9a-f]{7,40})$", str(value["version"]))
    return match.group(1) if match else None


def _subiquity_match(source: dict[str, object] | None, snap: dict[str, object] | None) -> str:
    source_ref = str(source.get("ref")) if source and source.get("ref") else ""
    snap_ref = _version_hash(snap)
    if not source_ref or not snap_ref:
        return '<span class="p-chip">subiquity unknown</span>'
    if source_ref.startswith(snap_ref):
        return '<span class="p-chip--positive">subiquity match</span>'
    return '<span class="p-chip--caution">subiquity mismatch</span>'
```

- [ ] **Step 3: Split subiquity detail rows**

In `render_dashboard()`, change details from one `subiquity` row to:

```python
_detail("subiquity snap", _package(record.get("subiquity_snap"))),
_detail("subiquity source", _source(record.get("subiquity"))),
_detail("subiquity check", _subiquity_match(record.get("subiquity"), record.get("subiquity_snap"))),
```

- [ ] **Step 4: Run render tests**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS.

---

### Task 4: Full Verification And Commit

**Files:**
- Modify: none expected beyond previous tasks.
- Test: full suite and generated render smoke check.

- [ ] **Step 1: Run full suite**

Run: `python3 -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Render smoke check**

Run: `PYTHONPATH=src python3 -m iso_dashboard.cli render --data data/latest.json --site /tmp/opencode/iso-dashboard-site`

Expected: command exits 0.

- [ ] **Step 3: Commit**

Run:

```bash
git add src/iso_dashboard/models.py src/iso_dashboard/snapcraft.py src/iso_dashboard/collector.py src/iso_dashboard/render.py tests/test_snapcraft.py tests/test_collector.py tests/test_config_models.py tests/test_render.py docs/superpowers/specs/2026-06-30-subiquity-snap-channel-comparison-design.md docs/superpowers/plans/2026-06-30-subiquity-snap-channel-comparison.md
git commit -m "Compare subiquity snap channel with source ref"
```

Expected: commit succeeds.

---

## Plan Self-Review

- Spec coverage: Task 1 resolves snap channels, Task 2 stores subiquity_snap, Task 3 renders comparison, Task 4 verifies and commits.
- Placeholder scan: no placeholders or deferred work remain.
- Type consistency: `subiquity_snap` uses existing `PackageVersion`; comparison uses source `SourceRef.ref` and snap `PackageVersion.version` suffix.
