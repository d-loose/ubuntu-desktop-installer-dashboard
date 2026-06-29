# Ubuntu Desktop ISO Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-only static dashboard showing the latest pending Ubuntu Desktop ISO package and source dependency versions for configured releases and architectures.

**Architecture:** A Python collector fetches cdimage pending listings, parses manifests, resolves upstream GitHub metadata, and writes `data/latest.json`. A Python renderer reads that JSON and writes static HTML/CSS into `site/`. GitHub Actions runs tests, refreshes data daily, builds the static site, and publishes it as Pages artifacts.

**Tech Stack:** Python 3.12, standard library HTTP/HTML/JSON modules, `pytest` for tests, GitHub Actions, GitHub Pages static artifact upload.

## Global Constraints

- Implementation code must use Python only; do not add JavaScript or TypeScript implementation code.
- Data collection must inspect only `https://cdimage.ubuntu.com/<release>/daily-live/pending/`; ignore `current` entirely.
- Configured releases are exactly `noble`, `resolute`, and `stonking` for the first version.
- Configured architectures are exactly `amd64`, `arm64`, and `riscv` for the first version.
- Keep one record per release and architecture pair even when ISO, manifest, or upstream metadata is missing.
- Missing or unresolved per-record data must be represented as warnings in `data/latest.json`, not as whole-job failures.
- The dashboard is latest-only; do not store historical snapshots.
- Browser-side live fetching from cdimage or GitHub is out of scope.
- The generated JSON remains published next to the generated HTML for inspection.

---

## File Structure

- Create `pyproject.toml`: Python packaging, pytest config, console scripts.
- Create `README.md`: local development, data refresh, site build, Pages deployment overview.
- Create `src/iso_dashboard/__init__.py`: package marker and version.
- Create `src/iso_dashboard/config.py`: checked-in release, architecture, and URL configuration.
- Create `src/iso_dashboard/models.py`: dataclasses for package versions, source refs, ISO records, and dashboard data.
- Create `src/iso_dashboard/parsers.py`: pure parsing for cdimage HTML listings and `.manifest` contents.
- Create `src/iso_dashboard/github.py`: GitHub raw/API helpers and upstream source resolution.
- Create `src/iso_dashboard/collector.py`: orchestration that builds dashboard data for all release/architecture pairs.
- Create `src/iso_dashboard/render.py`: Python static HTML/CSS generation from `data/latest.json`.
- Create `src/iso_dashboard/cli.py`: `collect`, `render`, and `build` commands.
- Create `tests/fixtures/cdimage_pending.html`: stable cdimage listing fixture.
- Create `tests/fixtures/example.manifest`: stable manifest fixture with snap and deb entries.
- Create `tests/test_config_models.py`: config and serialization tests.
- Create `tests/test_parsers.py`: cdimage and manifest parser tests.
- Create `tests/test_github.py`: mocked upstream source resolution tests.
- Create `tests/test_collector.py`: orchestration tests using fake clients.
- Create `tests/test_render.py`: static HTML output tests.
- Create `.github/workflows/pages.yml`: scheduled, manual, and Pages publishing workflow.

---

### Task 1: Python Project Scaffold And Data Models

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/iso_dashboard/__init__.py`
- Create: `src/iso_dashboard/config.py`
- Create: `src/iso_dashboard/models.py`
- Create: `tests/test_config_models.py`

**Interfaces:**
- Produces: `iso_dashboard.config.RELEASES: tuple[str, ...]`
- Produces: `iso_dashboard.config.ARCHITECTURES: tuple[str, ...]`
- Produces: `iso_dashboard.config.pending_url(release: str) -> str`
- Produces: `iso_dashboard.models.PackageVersion`
- Produces: `iso_dashboard.models.SourceRef`
- Produces: `iso_dashboard.models.IsoRecord`
- Produces: `iso_dashboard.models.DashboardData`
- Produces: `DashboardData.to_json_dict() -> dict[str, object]`

- [ ] **Step 1: Write the failing model/config tests**

Create `tests/test_config_models.py`:

```python
from iso_dashboard.config import ARCHITECTURES, RELEASES, pending_url
from iso_dashboard.models import DashboardData, IsoRecord, PackageVersion, SourceRef


def test_configured_release_and_architecture_lists_are_exact():
    assert RELEASES == ("noble", "resolute", "stonking")
    assert ARCHITECTURES == ("amd64", "arm64", "riscv")


def test_pending_url_uses_only_pending_location():
    assert pending_url("noble") == "https://cdimage.ubuntu.com/noble/daily-live/pending/"
    assert "current" not in pending_url("noble")


def test_dashboard_data_serializes_nested_records():
    record = IsoRecord(
        release="noble",
        architecture="amd64",
        iso_source="pending",
        iso_url="https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.iso",
        manifest_url="https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.manifest",
        published_at="2026-06-29T10:00:00Z",
        ubuntu_desktop_bootstrap=PackageVersion(name="ubuntu-desktop-bootstrap", version="1.2.3", revision="42"),
        snapd_snap=PackageVersion(name="snapd", version="2.70", revision="24718"),
        snapd_deb=PackageVersion(name="snapd", version="2.70+ubuntu1", revision=None),
        subiquity=SourceRef(name="subiquity", ref="abc123", url="https://github.com/canonical/subiquity/commit/abc123"),
        secboot=SourceRef(name="secboot", ref="v0.0.0", url="https://github.com/snapcore/secboot/tree/v0.0.0"),
        warnings=("example warning",),
    )
    data = DashboardData(generated_at="2026-06-29T11:00:00Z", records=(record,))

    assert data.to_json_dict() == {
        "generated_at": "2026-06-29T11:00:00Z",
        "releases": ["noble", "resolute", "stonking"],
        "architectures": ["amd64", "arm64", "riscv"],
        "records": [
            {
                "release": "noble",
                "architecture": "amd64",
                "iso_source": "pending",
                "iso_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.iso",
                "manifest_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.manifest",
                "published_at": "2026-06-29T10:00:00Z",
                "ubuntu_desktop_bootstrap": {"name": "ubuntu-desktop-bootstrap", "version": "1.2.3", "revision": "42"},
                "snapd_snap": {"name": "snapd", "version": "2.70", "revision": "24718"},
                "snapd_deb": {"name": "snapd", "version": "2.70+ubuntu1", "revision": None},
                "subiquity": {"name": "subiquity", "ref": "abc123", "url": "https://github.com/canonical/subiquity/commit/abc123"},
                "secboot": {"name": "secboot", "ref": "v0.0.0", "url": "https://github.com/snapcore/secboot/tree/v0.0.0"},
                "warnings": ["example warning"],
            }
        ],
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_config_models.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'iso_dashboard'`.

- [ ] **Step 3: Add project metadata and package files**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "ubuntu-desktop-iso-dashboard"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
test = ["pytest>=8"]

[project.scripts]
iso-dashboard = "iso_dashboard.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `README.md`:

````markdown
# Ubuntu Desktop ISO Dashboard

Python-only static dashboard for pending Ubuntu Desktop ISO package and source dependency versions.

## Local Development

Run tests:

```bash
python3 -m pytest
```

Build data and static HTML:

```bash
python3 -m iso_dashboard.cli build --data data/latest.json --site site
```

The collector reads only `https://cdimage.ubuntu.com/<release>/daily-live/pending/` and writes one record for every configured release and architecture pair.
````

Create `src/iso_dashboard/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/iso_dashboard/config.py`:

```python
CDIMAGE_BASE_URL = "https://cdimage.ubuntu.com"
RELEASES = ("noble", "resolute", "stonking")
ARCHITECTURES = ("amd64", "arm64", "riscv")


def pending_url(release: str) -> str:
    return f"{CDIMAGE_BASE_URL}/{release}/daily-live/pending/"
```

Create `src/iso_dashboard/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from iso_dashboard.config import ARCHITECTURES, RELEASES

IsoSource = Literal["pending", "missing"]


@dataclass(frozen=True)
class PackageVersion:
    name: str
    version: str | None
    revision: str | None


@dataclass(frozen=True)
class SourceRef:
    name: str
    ref: str | None
    url: str | None


@dataclass(frozen=True)
class IsoRecord:
    release: str
    architecture: str
    iso_source: IsoSource
    iso_url: str | None
    manifest_url: str | None
    published_at: str | None
    ubuntu_desktop_bootstrap: PackageVersion | None
    snapd_snap: PackageVersion | None
    snapd_deb: PackageVersion | None
    subiquity: SourceRef | None
    secboot: SourceRef | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class DashboardData:
    generated_at: str
    records: tuple[IsoRecord, ...]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "releases": list(RELEASES),
            "architectures": list(ARCHITECTURES),
            "records": [asdict(record) for record in self.records],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_config_models.py -v`

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src/iso_dashboard/__init__.py src/iso_dashboard/config.py src/iso_dashboard/models.py tests/test_config_models.py
git commit -m "Add Python project scaffold and models"
```

---

### Task 2: Cdimage And Manifest Parsers

**Files:**
- Create: `src/iso_dashboard/parsers.py`
- Create: `tests/fixtures/cdimage_pending.html`
- Create: `tests/fixtures/example.manifest`
- Create: `tests/test_parsers.py`

**Interfaces:**
- Consumes: `PackageVersion`
- Produces: `CdimageArtifact(name: str, href: str, modified: str | None)`
- Produces: `parse_cdimage_listing(html_text: str) -> tuple[CdimageArtifact, ...]`
- Produces: `find_artifact(artifacts: tuple[CdimageArtifact, ...], release: str, architecture: str, suffix: str) -> CdimageArtifact | None`
- Produces: `parse_manifest(text: str) -> ManifestVersions`
- Produces: `ManifestVersions.ubuntu_desktop_bootstrap: PackageVersion | None`
- Produces: `ManifestVersions.snapd_snap: PackageVersion | None`
- Produces: `ManifestVersions.snapd_deb: PackageVersion | None`

- [ ] **Step 1: Add parser fixtures**

Create `tests/fixtures/cdimage_pending.html`:

```html
<!doctype html>
<html>
<body>
<a href="noble-desktop-amd64.iso">noble-desktop-amd64.iso</a> 2026-06-29 10:15  5.1G
<a href="noble-desktop-amd64.manifest">noble-desktop-amd64.manifest</a> 2026-06-29 10:16  92K
<a href="noble-desktop-arm64.iso">noble-desktop-arm64.iso</a> 2026-06-29 09:45  5.0G
</body>
</html>
```

Create `tests/fixtures/example.manifest`:

```text
snap:ubuntu-desktop-bootstrap 1.2.3 42
snap:snapd 2.70 24718
snapd 2.70+ubuntu1
other-package 1.0
```

- [ ] **Step 2: Write failing parser tests**

Create `tests/test_parsers.py`:

```python
from pathlib import Path

from iso_dashboard.parsers import find_artifact, parse_cdimage_listing, parse_manifest


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_cdimage_listing_extracts_artifacts_and_modified_times():
    artifacts = parse_cdimage_listing((FIXTURES / "cdimage_pending.html").read_text())

    assert artifacts[0].name == "noble-desktop-amd64.iso"
    assert artifacts[0].href == "noble-desktop-amd64.iso"
    assert artifacts[0].modified == "2026-06-29T10:15:00Z"
    assert artifacts[1].name == "noble-desktop-amd64.manifest"
    assert artifacts[1].modified == "2026-06-29T10:16:00Z"


def test_find_artifact_matches_release_architecture_and_suffix():
    artifacts = parse_cdimage_listing((FIXTURES / "cdimage_pending.html").read_text())

    iso = find_artifact(artifacts, "noble", "amd64", ".iso")
    manifest = find_artifact(artifacts, "noble", "amd64", ".manifest")
    missing = find_artifact(artifacts, "noble", "riscv", ".iso")

    assert iso is not None
    assert iso.name == "noble-desktop-amd64.iso"
    assert manifest is not None
    assert manifest.name == "noble-desktop-amd64.manifest"
    assert missing is None


def test_parse_manifest_extracts_snap_and_deb_versions():
    versions = parse_manifest((FIXTURES / "example.manifest").read_text())

    assert versions.ubuntu_desktop_bootstrap is not None
    assert versions.ubuntu_desktop_bootstrap.version == "1.2.3"
    assert versions.ubuntu_desktop_bootstrap.revision == "42"
    assert versions.snapd_snap is not None
    assert versions.snapd_snap.version == "2.70"
    assert versions.snapd_snap.revision == "24718"
    assert versions.snapd_deb is not None
    assert versions.snapd_deb.version == "2.70+ubuntu1"
    assert versions.snapd_deb.revision is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_parsers.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'iso_dashboard.parsers'`.

- [ ] **Step 4: Implement parsers**

Create `src/iso_dashboard/parsers.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser

from iso_dashboard.models import PackageVersion


@dataclass(frozen=True)
class CdimageArtifact:
    name: str
    href: str
    modified: str | None


@dataclass(frozen=True)
class ManifestVersions:
    ubuntu_desktop_bootstrap: PackageVersion | None
    snapd_snap: PackageVersion | None
    snapd_deb: PackageVersion | None


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        self._current_href = attrs_dict.get("href")

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self.links.append((self._current_href, data.strip()))
            self._current_href = None


def _modified_for_link(html_text: str, link_text: str) -> str | None:
    pattern = re.compile(re.escape(link_text) + r"</a>\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})")
    match = pattern.search(html_text)
    if not match:
        return None
    parsed = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_cdimage_listing(html_text: str) -> tuple[CdimageArtifact, ...]:
    parser = _LinkParser()
    parser.feed(html_text)
    artifacts = []
    for href, label in parser.links:
        name = label or href.rsplit("/", 1)[-1]
        if name in {"../", "Parent Directory"}:
            continue
        artifacts.append(CdimageArtifact(name=name, href=href, modified=_modified_for_link(html_text, name)))
    return tuple(artifacts)


def find_artifact(artifacts: tuple[CdimageArtifact, ...], release: str, architecture: str, suffix: str) -> CdimageArtifact | None:
    required = (release, "desktop", architecture)
    matches = [
        artifact
        for artifact in artifacts
        if artifact.name.endswith(suffix) and all(part in artifact.name for part in required)
    ]
    return sorted(matches, key=lambda artifact: artifact.name)[-1] if matches else None


def parse_manifest(text: str) -> ManifestVersions:
    ubuntu_desktop_bootstrap: PackageVersion | None = None
    snapd_snap: PackageVersion | None = None
    snapd_deb: PackageVersion | None = None

    for raw_line in text.splitlines():
        parts = raw_line.split()
        if not parts:
            continue
        name = parts[0]
        if name == "snap:ubuntu-desktop-bootstrap" and len(parts) >= 3:
            ubuntu_desktop_bootstrap = PackageVersion("ubuntu-desktop-bootstrap", parts[1], parts[2])
        elif name == "snap:snapd" and len(parts) >= 3:
            snapd_snap = PackageVersion("snapd", parts[1], parts[2])
        elif name == "snapd" and len(parts) >= 2:
            snapd_deb = PackageVersion("snapd", parts[1], None)

    return ManifestVersions(
        ubuntu_desktop_bootstrap=ubuntu_desktop_bootstrap,
        snapd_snap=snapd_snap,
        snapd_deb=snapd_deb,
    )
```

- [ ] **Step 5: Run parser tests**

Run: `python3 -m pytest tests/test_parsers.py -v`

Expected: PASS with `3 passed`.

- [ ] **Step 6: Run all tests**

Run: `python3 -m pytest -v`

Expected: PASS with all current tests passing.

- [ ] **Step 7: Commit**

```bash
git add src/iso_dashboard/parsers.py tests/fixtures/cdimage_pending.html tests/fixtures/example.manifest tests/test_parsers.py
git commit -m "Add cdimage and manifest parsers"
```

---

### Task 3: GitHub Upstream Source Resolution

**Files:**
- Create: `src/iso_dashboard/github.py`
- Create: `tests/test_github.py`

**Interfaces:**
- Consumes: `PackageVersion`
- Consumes: `SourceRef`
- Produces: `HttpClient = Callable[[str], str]`
- Produces: `GithubResolver(http_get: HttpClient)`
- Produces: `GithubResolver.resolve_subiquity(bootstrap: PackageVersion | None) -> tuple[SourceRef | None, tuple[str, ...]]`
- Produces: `GithubResolver.resolve_secboot(snapd: PackageVersion | None) -> tuple[SourceRef | None, tuple[str, ...]]`
- Produces: `http_get_text(url: str) -> str`

- [ ] **Step 1: Write failing GitHub resolver tests**

Create `tests/test_github.py`:

```python
import json

from iso_dashboard.github import GithubResolver
from iso_dashboard.models import PackageVersion


def test_resolve_subiquity_reads_submodule_gitlink_from_matching_tag():
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/ref/tags/1.2.3": json.dumps(
            {"object": {"sha": "provision-sha"}}
        ),
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/provision-sha": json.dumps(
            {"tree": [{"path": "subiquity", "type": "commit", "sha": "subiquity-sha"}]}
        ),
    }
    resolver = GithubResolver(lambda url: responses[url])

    source, warnings = resolver.resolve_subiquity(PackageVersion("ubuntu-desktop-bootstrap", "1.2.3", "42"))

    assert warnings == ()
    assert source is not None
    assert source.name == "subiquity"
    assert source.ref == "subiquity-sha"
    assert source.url == "https://github.com/canonical/subiquity/commit/subiquity-sha"


def test_resolve_subiquity_returns_warning_when_no_bootstrap_version():
    resolver = GithubResolver(lambda url: "{}")

    source, warnings = resolver.resolve_subiquity(None)

    assert source is None
    assert warnings == ("Cannot resolve subiquity because ubuntu-desktop-bootstrap snap is missing",)


def test_resolve_secboot_reads_go_mod_from_matching_snapd_tag():
    responses = {
        "https://api.github.com/repos/snapcore/snapd/git/ref/tags/2.70": json.dumps({"object": {"sha": "snapd-sha"}}),
        "https://raw.githubusercontent.com/snapcore/snapd/snapd-sha/go.mod": "module github.com/snapcore/snapd\nrequire github.com/snapcore/secboot v0.0.0-20260629000000-abcdef123456\n",
    }
    resolver = GithubResolver(lambda url: responses[url])

    source, warnings = resolver.resolve_secboot(PackageVersion("snapd", "2.70", "24718"))

    assert warnings == ()
    assert source is not None
    assert source.name == "secboot"
    assert source.ref == "v0.0.0-20260629000000-abcdef123456"
    assert source.url == "https://github.com/snapcore/secboot/tree/v0.0.0-20260629000000-abcdef123456"


def test_resolver_returns_unknown_warning_when_tag_lookup_fails():
    def failing_get(url: str) -> str:
        raise RuntimeError(f"404 for {url}")

    resolver = GithubResolver(failing_get)

    source, warnings = resolver.resolve_secboot(PackageVersion("snapd", "2.70", "24718"))

    assert source is None
    assert warnings == ("Cannot map snapd version 2.70 to a snapcore/snapd source ref",)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_github.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'iso_dashboard.github'`.

- [ ] **Step 3: Implement GitHub resolver**

Create `src/iso_dashboard/github.py`:

```python
from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Callable

from iso_dashboard.models import PackageVersion, SourceRef

HttpClient = Callable[[str], str]


def http_get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "ubuntu-desktop-iso-dashboard"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


class GithubResolver:
    def __init__(self, http_get: HttpClient = http_get_text) -> None:
        self._http_get = http_get

    def _tag_sha(self, owner: str, repo: str, version: str) -> str | None:
        candidates = (version, f"v{version}")
        for candidate in candidates:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{candidate}"
            try:
                payload = json.loads(self._http_get(url))
            except Exception:
                continue
            sha = payload.get("object", {}).get("sha")
            if isinstance(sha, str) and sha:
                return sha
        return None

    def resolve_subiquity(self, bootstrap: PackageVersion | None) -> tuple[SourceRef | None, tuple[str, ...]]:
        if bootstrap is None or bootstrap.version is None:
            return None, ("Cannot resolve subiquity because ubuntu-desktop-bootstrap snap is missing",)

        source_sha = self._tag_sha("canonical", "ubuntu-desktop-provision", bootstrap.version)
        if source_sha is None:
            return None, (f"Cannot map ubuntu-desktop-bootstrap version {bootstrap.version} to a canonical/ubuntu-desktop-provision source ref",)

        try:
            tree = json.loads(
                self._http_get(f"https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/{source_sha}")
            )
        except Exception:
            return None, (f"Cannot read ubuntu-desktop-provision tree {source_sha} for subiquity submodule",)

        for entry in tree.get("tree", []):
            if entry.get("path") == "subiquity" and entry.get("type") == "commit" and isinstance(entry.get("sha"), str):
                sha = entry["sha"]
                return SourceRef("subiquity", sha, f"https://github.com/canonical/subiquity/commit/{sha}"), ()

        return None, (f"Cannot find subiquity submodule in ubuntu-desktop-provision tree {source_sha}",)

    def resolve_secboot(self, snapd: PackageVersion | None) -> tuple[SourceRef | None, tuple[str, ...]]:
        if snapd is None or snapd.version is None:
            return None, ("Cannot resolve secboot because snapd snap is missing",)

        source_sha = self._tag_sha("snapcore", "snapd", snapd.version)
        if source_sha is None:
            return None, (f"Cannot map snapd version {snapd.version} to a snapcore/snapd source ref",)

        try:
            go_mod = self._http_get(f"https://raw.githubusercontent.com/snapcore/snapd/{source_sha}/go.mod")
        except Exception:
            return None, (f"Cannot read snapd go.mod at source ref {source_sha}",)

        match = re.search(r"github\.com/snapcore/secboot\s+(\S+)", go_mod)
        if not match:
            return None, (f"Cannot find github.com/snapcore/secboot in snapd go.mod at source ref {source_sha}",)

        ref = match.group(1)
        return SourceRef("secboot", ref, f"https://github.com/snapcore/secboot/tree/{ref}"), ()
```

- [ ] **Step 4: Run GitHub tests**

Run: `python3 -m pytest tests/test_github.py -v`

Expected: PASS with `4 passed`.

- [ ] **Step 5: Run all tests**

Run: `python3 -m pytest -v`

Expected: PASS with all current tests passing.

- [ ] **Step 6: Commit**

```bash
git add src/iso_dashboard/github.py tests/test_github.py
git commit -m "Add upstream source resolution"
```

---

### Task 4: Collector Orchestration And JSON Output

**Files:**
- Create: `src/iso_dashboard/collector.py`
- Create: `tests/test_collector.py`

**Interfaces:**
- Consumes: `pending_url(release: str) -> str`
- Consumes: `parse_cdimage_listing`, `find_artifact`, `parse_manifest`
- Consumes: `GithubResolver`
- Produces: `Collector(http_get: HttpClient, resolver: GithubResolver)`
- Produces: `Collector.collect_record(release: str, architecture: str) -> IsoRecord`
- Produces: `Collector.collect_all(now: datetime | None = None) -> DashboardData`
- Produces: `write_dashboard_json(data: DashboardData, path: Path) -> None`

- [ ] **Step 1: Write failing collector tests**

Create `tests/test_collector.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

from iso_dashboard.collector import Collector, write_dashboard_json
from iso_dashboard.models import SourceRef


PENDING_URL = "https://cdimage.ubuntu.com/noble/daily-live/pending/"
MANIFEST_URL = "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.manifest"


class FakeResolver:
    def resolve_subiquity(self, bootstrap):
        return SourceRef("subiquity", "subiquity-sha", "https://github.com/canonical/subiquity/commit/subiquity-sha"), ()

    def resolve_secboot(self, snapd):
        return SourceRef("secboot", "v1", "https://github.com/snapcore/secboot/tree/v1"), ()


def test_collect_record_builds_complete_pending_record():
    responses = {
        PENDING_URL: '<a href="noble-desktop-amd64.iso">noble-desktop-amd64.iso</a> 2026-06-29 10:15\n<a href="noble-desktop-amd64.manifest">noble-desktop-amd64.manifest</a> 2026-06-29 10:16',
        MANIFEST_URL: "snap:ubuntu-desktop-bootstrap 1.2.3 42\nsnap:snapd 2.70 24718\nsnapd 2.70+ubuntu1\n",
    }
    collector = Collector(lambda url: responses[url], FakeResolver())

    record = collector.collect_record("noble", "amd64")

    assert record.release == "noble"
    assert record.architecture == "amd64"
    assert record.iso_source == "pending"
    assert record.iso_url == "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.iso"
    assert record.manifest_url == MANIFEST_URL
    assert record.published_at == "2026-06-29T10:15:00Z"
    assert record.ubuntu_desktop_bootstrap.version == "1.2.3"
    assert record.snapd_snap.version == "2.70"
    assert record.snapd_deb.version == "2.70+ubuntu1"
    assert record.subiquity.ref == "subiquity-sha"
    assert record.secboot.ref == "v1"
    assert record.warnings == ()


def test_collect_record_keeps_missing_record_when_listing_fetch_fails():
    def failing_get(url: str) -> str:
        raise RuntimeError("network unavailable")

    collector = Collector(failing_get, FakeResolver())

    record = collector.collect_record("noble", "amd64")

    assert record.iso_source == "missing"
    assert record.iso_url is None
    assert record.manifest_url is None
    assert record.warnings == ("Cannot fetch pending listing for noble: network unavailable",)


def test_collect_all_writes_one_record_per_configured_pair():
    collector = Collector(lambda url: "", FakeResolver())

    data = collector.collect_all(datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc))

    assert data.generated_at == "2026-06-29T12:00:00Z"
    assert len(data.records) == 9
    assert {(record.release, record.architecture) for record in data.records} == {
        ("noble", "amd64"), ("noble", "arm64"), ("noble", "riscv"),
        ("resolute", "amd64"), ("resolute", "arm64"), ("resolute", "riscv"),
        ("stonking", "amd64"), ("stonking", "arm64"), ("stonking", "riscv"),
    }


def test_write_dashboard_json_creates_parent_directory_and_json(tmp_path):
    collector = Collector(lambda url: "", FakeResolver())
    data = collector.collect_all(datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc))
    output = tmp_path / "data" / "latest.json"

    write_dashboard_json(data, output)

    payload = json.loads(output.read_text())
    assert payload["generated_at"] == "2026-06-29T12:00:00Z"
    assert len(payload["records"]) == 9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_collector.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'iso_dashboard.collector'`.

- [ ] **Step 3: Implement collector**

Create `src/iso_dashboard/collector.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from iso_dashboard.config import ARCHITECTURES, RELEASES, pending_url
from iso_dashboard.github import GithubResolver, HttpClient, http_get_text
from iso_dashboard.models import DashboardData, IsoRecord
from iso_dashboard.parsers import find_artifact, parse_cdimage_listing, parse_manifest


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class Collector:
    def __init__(self, http_get: HttpClient = http_get_text, resolver: GithubResolver | None = None) -> None:
        self._http_get = http_get
        self._resolver = resolver if resolver is not None else GithubResolver(http_get)

    def collect_record(self, release: str, architecture: str) -> IsoRecord:
        base_url = pending_url(release)
        warnings: list[str] = []
        try:
            listing = self._http_get(base_url)
        except Exception as exc:
            return IsoRecord(release, architecture, "missing", None, None, None, None, None, None, None, None, (f"Cannot fetch pending listing for {release}: {exc}",))

        artifacts = parse_cdimage_listing(listing)
        iso = find_artifact(artifacts, release, architecture, ".iso")
        manifest = find_artifact(artifacts, release, architecture, ".manifest")
        if iso is None:
            warnings.append(f"Missing pending ISO for {release} {architecture}")
        if manifest is None:
            warnings.append(f"Missing pending manifest for {release} {architecture}")

        manifest_versions = None
        manifest_url = urljoin(base_url, manifest.href) if manifest else None
        if manifest_url:
            try:
                manifest_versions = parse_manifest(self._http_get(manifest_url))
            except Exception as exc:
                warnings.append(f"Cannot fetch or parse manifest for {release} {architecture}: {exc}")

        bootstrap = manifest_versions.ubuntu_desktop_bootstrap if manifest_versions else None
        snapd_snap = manifest_versions.snapd_snap if manifest_versions else None
        snapd_deb = manifest_versions.snapd_deb if manifest_versions else None

        if manifest_versions:
            if bootstrap is None:
                warnings.append("Manifest does not include ubuntu-desktop-bootstrap snap")
            if snapd_snap is None:
                warnings.append("Manifest does not include snapd snap")
            if snapd_deb is None:
                warnings.append("Manifest does not include snapd deb")

        subiquity, subiquity_warnings = self._resolver.resolve_subiquity(bootstrap)
        secboot, secboot_warnings = self._resolver.resolve_secboot(snapd_snap)
        warnings.extend(subiquity_warnings)
        warnings.extend(secboot_warnings)

        return IsoRecord(
            release=release,
            architecture=architecture,
            iso_source="pending" if iso and manifest else "missing",
            iso_url=urljoin(base_url, iso.href) if iso else None,
            manifest_url=manifest_url,
            published_at=iso.modified if iso else None,
            ubuntu_desktop_bootstrap=bootstrap,
            snapd_snap=snapd_snap,
            snapd_deb=snapd_deb,
            subiquity=subiquity,
            secboot=secboot,
            warnings=tuple(warnings),
        )

    def collect_all(self, now: datetime | None = None) -> DashboardData:
        generated_at = _format_time(now if now is not None else _utc_now())
        records = tuple(self.collect_record(release, architecture) for release in RELEASES for architecture in ARCHITECTURES)
        return DashboardData(generated_at=generated_at, records=records)


def write_dashboard_json(data: DashboardData, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.to_json_dict(), indent=2, sort_keys=True) + "\n")
```

- [ ] **Step 4: Run collector tests**

Run: `python3 -m pytest tests/test_collector.py -v`

Expected: PASS with `4 passed`.

- [ ] **Step 5: Run all tests**

Run: `python3 -m pytest -v`

Expected: PASS with all current tests passing.

- [ ] **Step 6: Commit**

```bash
git add src/iso_dashboard/collector.py tests/test_collector.py
git commit -m "Add dashboard data collector"
```

---

### Task 5: Python Static HTML Renderer

**Files:**
- Create: `src/iso_dashboard/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: generated `data/latest.json` dictionary shape.
- Produces: `render_dashboard(payload: dict[str, object]) -> str`
- Produces: `write_site(data_path: Path, site_dir: Path) -> None`

- [ ] **Step 1: Write failing renderer tests**

Create `tests/test_render.py`:

```python
import json

from iso_dashboard.render import render_dashboard, write_site


def sample_payload():
    return {
        "generated_at": "2026-06-29T12:00:00Z",
        "releases": ["noble"],
        "architectures": ["amd64"],
        "records": [
            {
                "release": "noble",
                "architecture": "amd64",
                "iso_source": "pending",
                "iso_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.iso",
                "manifest_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.manifest",
                "published_at": "2026-06-29T10:15:00Z",
                "ubuntu_desktop_bootstrap": {"name": "ubuntu-desktop-bootstrap", "version": "1.2.3", "revision": "42"},
                "snapd_snap": {"name": "snapd", "version": "2.70", "revision": "24718"},
                "snapd_deb": {"name": "snapd", "version": "2.70+ubuntu1", "revision": None},
                "subiquity": {"name": "subiquity", "ref": "subiquity-sha", "url": "https://github.com/canonical/subiquity/commit/subiquity-sha"},
                "secboot": {"name": "secboot", "ref": "v1", "url": "https://github.com/snapcore/secboot/tree/v1"},
                "warnings": [],
            }
        ],
    }


def test_render_dashboard_includes_summary_table_and_links():
    html = render_dashboard(sample_payload())

    assert "Ubuntu Desktop ISO Dashboard" in html
    assert "Generated: 2026-06-29T12:00:00Z" in html
    assert "noble" in html
    assert "amd64" in html
    assert "1.2.3 (rev 42)" in html
    assert "2.70 (rev 24718)" in html
    assert "2.70+ubuntu1" in html
    assert "subiquity-sha" in html
    assert "https://github.com/canonical/subiquity/commit/subiquity-sha" in html
    assert "No warnings" in html
    assert "<script" not in html.lower()


def test_write_site_writes_index_css_and_json_copy(tmp_path):
    data_path = tmp_path / "data" / "latest.json"
    data_path.parent.mkdir()
    data_path.write_text(json.dumps(sample_payload()))

    write_site(data_path, tmp_path / "site")

    assert (tmp_path / "site" / "index.html").exists()
    assert (tmp_path / "site" / "styles.css").exists()
    assert (tmp_path / "site" / "data" / "latest.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'iso_dashboard.render'`.

- [ ] **Step 3: Implement renderer**

Create `src/iso_dashboard/render.py`:

```python
from __future__ import annotations

import json
import shutil
from html import escape
from pathlib import Path


CSS = """
:root { color-scheme: light; font-family: Ubuntu, Arial, sans-serif; }
body { margin: 0; background: #f7f3ef; color: #111; }
header { background: #2c001e; color: white; padding: 2rem; }
main { padding: 1.5rem; }
table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
th, td { border-bottom: 1px solid #ddd; padding: .75rem; text-align: left; vertical-align: top; }
th { background: #eee7df; }
.status-pending { color: #0b6b2b; font-weight: 700; }
.status-missing { color: #a00000; font-weight: 700; }
.warnings { color: #8a4b00; }
a { color: #06c; }
@media (max-width: 900px) { table, thead, tbody, tr, th, td { display: block; } th { display: none; } td::before { content: attr(data-label); display: block; font-weight: 700; } }
""".strip() + "\n"


def _package(value: dict[str, object] | None) -> str:
    if not value or not value.get("version"):
        return "unknown"
    version = escape(str(value["version"]))
    revision = value.get("revision")
    return f"{version} (rev {escape(str(revision))})" if revision else version


def _source(value: dict[str, object] | None) -> str:
    if not value or not value.get("ref"):
        return "unknown"
    ref = escape(str(value["ref"]))
    url = value.get("url")
    if url:
        safe_url = escape(str(url), quote=True)
        return f'<a href="{safe_url}">{ref}</a>'
    return ref


def _warnings(values: list[str]) -> str:
    if not values:
        return "No warnings"
    return "<br>".join(escape(value) for value in values)


def render_dashboard(payload: dict[str, object]) -> str:
    rows = []
    records = payload.get("records", [])
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        status = escape(str(record.get("iso_source", "missing")))
        warnings = record.get("warnings", [])
        assert isinstance(warnings, list)
        rows.append(
            "<tr>"
            f'<td data-label="Release">{escape(str(record.get("release", "unknown")))}</td>'
            f'<td data-label="Architecture">{escape(str(record.get("architecture", "unknown")))}</td>'
            f'<td data-label="ISO"><span class="status-{status}">{status}</span><br>{escape(str(record.get("published_at") or "unknown"))}</td>'
            f'<td data-label="ubuntu-desktop-bootstrap">{_package(record.get("ubuntu_desktop_bootstrap"))}</td>'
            f'<td data-label="snapd snap">{_package(record.get("snapd_snap"))}</td>'
            f'<td data-label="snapd deb">{_package(record.get("snapd_deb"))}</td>'
            f'<td data-label="subiquity">{_source(record.get("subiquity"))}</td>'
            f'<td data-label="secboot">{_source(record.get("secboot"))}</td>'
            f'<td data-label="Warnings" class="warnings">{_warnings(warnings)}</td>'
            "</tr>"
        )

    warning_count = sum(len(record.get("warnings", [])) for record in records if isinstance(record, dict))
    generated_at = escape(str(payload.get("generated_at", "unknown")))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ubuntu Desktop ISO Dashboard</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header>
    <h1>Ubuntu Desktop ISO Dashboard</h1>
    <p>Generated: {generated_at}</p>
    <p>{len(records)} records, {warning_count} warnings</p>
  </header>
  <main>
    <table>
      <thead><tr><th>Release</th><th>Architecture</th><th>ISO</th><th>ubuntu-desktop-bootstrap</th><th>snapd snap</th><th>snapd deb</th><th>subiquity</th><th>secboot</th><th>Warnings</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </main>
</body>
</html>
"""


def write_site(data_path: Path, site_dir: Path) -> None:
    payload = json.loads(data_path.read_text())
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(render_dashboard(payload))
    (site_dir / "styles.css").write_text(CSS)
    data_output = site_dir / "data" / "latest.json"
    data_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(data_path, data_output)
```

- [ ] **Step 4: Run renderer tests**

Run: `python3 -m pytest tests/test_render.py -v`

Expected: PASS with `2 passed`.

- [ ] **Step 5: Run all tests**

Run: `python3 -m pytest -v`

Expected: PASS with all current tests passing.

- [ ] **Step 6: Commit**

```bash
git add src/iso_dashboard/render.py tests/test_render.py
git commit -m "Add Python static dashboard renderer"
```

---

### Task 6: CLI And GitHub Pages Workflow

**Files:**
- Create: `src/iso_dashboard/cli.py`
- Create: `.github/workflows/pages.yml`
- Modify: `README.md`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `Collector.collect_all()`
- Consumes: `write_dashboard_json(data: DashboardData, path: Path) -> None`
- Consumes: `write_site(data_path: Path, site_dir: Path) -> None`
- Produces: `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
import json

from iso_dashboard import cli


def test_render_command_writes_site_from_existing_json(tmp_path):
    data_path = tmp_path / "data" / "latest.json"
    site_dir = tmp_path / "site"
    data_path.parent.mkdir()
    data_path.write_text(json.dumps({"generated_at": "2026-06-29T12:00:00Z", "records": []}))

    result = cli.main(["render", "--data", str(data_path), "--site", str(site_dir)])

    assert result == 0
    assert (site_dir / "index.html").exists()
    assert (site_dir / "data" / "latest.json").exists()


def test_build_command_collects_json_and_renders_site(monkeypatch, tmp_path):
    class FakeCollector:
        def collect_all(self):
            from iso_dashboard.models import DashboardData

            return DashboardData(generated_at="2026-06-29T12:00:00Z", records=())

    monkeypatch.setattr(cli, "Collector", lambda: FakeCollector())
    data_path = tmp_path / "data" / "latest.json"
    site_dir = tmp_path / "site"

    result = cli.main(["build", "--data", str(data_path), "--site", str(site_dir)])

    assert result == 0
    assert json.loads(data_path.read_text())["generated_at"] == "2026-06-29T12:00:00Z"
    assert (site_dir / "index.html").exists()
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run: `python3 -m pytest tests/test_cli.py -v`

Expected: FAIL with `ImportError` or `ModuleNotFoundError` for `iso_dashboard.cli`.

- [ ] **Step 3: Implement CLI**

Create `src/iso_dashboard/cli.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from iso_dashboard.collector import Collector, write_dashboard_json
from iso_dashboard.render import write_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="iso-dashboard")
    subcommands = parser.add_subparsers(dest="command", required=True)

    collect = subcommands.add_parser("collect")
    collect.add_argument("--data", type=Path, default=Path("data/latest.json"))

    render = subcommands.add_parser("render")
    render.add_argument("--data", type=Path, default=Path("data/latest.json"))
    render.add_argument("--site", type=Path, default=Path("site"))

    build = subcommands.add_parser("build")
    build.add_argument("--data", type=Path, default=Path("data/latest.json"))
    build.add_argument("--site", type=Path, default=Path("site"))

    args = parser.parse_args(argv)
    if args.command == "collect":
        write_dashboard_json(Collector().collect_all(), args.data)
        return 0
    if args.command == "render":
        write_site(args.data, args.site)
        return 0
    if args.command == "build":
        write_dashboard_json(Collector().collect_all(), args.data)
        write_site(args.data, args.site)
        return 0
    raise AssertionError(f"Unhandled command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add GitHub Pages workflow**

Create `.github/workflows/pages.yml`:

```yaml
name: Build and publish dashboard

on:
  schedule:
    - cron: "17 6 * * *"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install test dependencies
        run: python -m pip install -e '.[test]'
      - name: Run tests
        run: python -m pytest -v
      - name: Build dashboard
        run: python -m iso_dashboard.cli build --data data/latest.json --site site
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 5: Update README with exact commands**

Replace `README.md` with:

````markdown
# Ubuntu Desktop ISO Dashboard

Python-only static dashboard for pending Ubuntu Desktop ISO package and source dependency versions.

## Local Development

Install test dependencies:

```bash
python3 -m pip install -e '.[test]'
```

Run tests:

```bash
python3 -m pytest -v
```

Collect data only:

```bash
python3 -m iso_dashboard.cli collect --data data/latest.json
```

Render static HTML from existing data:

```bash
python3 -m iso_dashboard.cli render --data data/latest.json --site site
```

Collect data and render the site:

```bash
python3 -m iso_dashboard.cli build --data data/latest.json --site site
```

The collector reads only `https://cdimage.ubuntu.com/<release>/daily-live/pending/` and writes one record for every configured release and architecture pair.

## Deployment

`.github/workflows/pages.yml` runs daily at `06:17 UTC`, on manual dispatch, and publishes the generated `site/` directory to GitHub Pages.
````

- [ ] **Step 6: Run CLI tests**

Run: `python3 -m pytest tests/test_cli.py -v`

Expected: PASS with `2 passed`.

- [ ] **Step 7: Run all tests**

Run: `python3 -m pytest -v`

Expected: PASS with all tests passing.

- [ ] **Step 8: Run local static render using fixture-like empty generated data**

Run: `python3 -m iso_dashboard.cli render --data data/latest.json --site site`

Expected if `data/latest.json` does not exist: FAIL with `FileNotFoundError`.

Run: `python3 -m iso_dashboard.cli build --data data/latest.json --site site`

Expected: Completes with exit code `0` when network access to cdimage and GitHub is available. If live network access is unavailable, keep this result as a verification note and rely on the mocked test suite.

- [ ] **Step 9: Commit**

```bash
git add src/iso_dashboard/cli.py .github/workflows/pages.yml README.md tests/test_cli.py
git commit -m "Add CLI and Pages workflow"
```

---

### Task 7: Final Verification And Generated Artifact Policy

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Consumes: all previous task outputs.
- Produces: explicit policy for generated local artifacts.

- [ ] **Step 1: Add `.gitignore` test by inspection**

Create `.gitignore`:

```gitignore
__pycache__/
.pytest_cache/
*.egg-info/
.venv/
site/
data/latest.json
```

- [ ] **Step 2: Update README artifact policy**

Append to `README.md`:

```markdown

## Generated Files

Local `data/latest.json` and `site/` outputs are ignored by git. The GitHub Actions workflow publishes them as Pages artifacts instead of committing generated data back to the repository.
```

- [ ] **Step 3: Run complete verification**

Run: `python3 -m pytest -v`

Expected: PASS with all tests passing.

- [ ] **Step 4: Confirm no JavaScript or TypeScript implementation files exist**

Run: `git ls-files '*.js' '*.jsx' '*.ts' '*.tsx'`

Expected: no output.

- [ ] **Step 5: Confirm pending-only implementation**

Run: `git grep -n "daily-live/current\|current/" -- src tests .github README.md`

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add .gitignore README.md
git commit -m "Document generated artifact policy"
```
