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
