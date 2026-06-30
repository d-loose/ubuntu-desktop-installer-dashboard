from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from iso_dashboard.config import ARCHITECTURES, RELEASES, pending_url
from iso_dashboard.github import GithubResolver, HttpClient, http_get_text
from iso_dashboard.models import DashboardData, IsoRecord
from iso_dashboard.parsers import find_artifact, parse_cdimage_listing, parse_manifest
from iso_dashboard.snapcraft import SnapcraftResolver

LOGGER = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class Collector:
    def __init__(
        self,
        http_get: HttpClient = http_get_text,
        resolver: GithubResolver | None = None,
        snapcraft_resolver: SnapcraftResolver | None = None,
    ) -> None:
        self._http_get = http_get
        self._resolver = resolver if resolver is not None else GithubResolver(http_get)
        self._snapcraft_resolver = snapcraft_resolver if snapcraft_resolver is not None else SnapcraftResolver()

    def collect_record(self, release: str, architecture: str) -> IsoRecord:
        base_url = pending_url(release)
        LOGGER.info("Collecting %s %s from %s", release, architecture, base_url)
        warnings: list[str] = []
        try:
            listing = self._http_get(base_url)
        except Exception as exc:
            return IsoRecord(release, architecture, None, None, None, None, None, None, None, None, None, (f"Cannot fetch pending listing for {release}: {exc}",))

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
            LOGGER.info("Fetching manifest %s", manifest_url)
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

        if bootstrap is not None:
            LOGGER.info("Resolving %s snap revision %s for %s", bootstrap.name, bootstrap.revision, architecture)
            bootstrap, bootstrap_warnings = self._snapcraft_resolver.resolve_revision(bootstrap, architecture)
            warnings.extend(bootstrap_warnings)
        subiquity_snap = None
        if bootstrap is not None:
            subiquity_snap, subiquity_snap_warnings = self._snapcraft_resolver.resolve_channel("subiquity", bootstrap.channel, architecture)
            warnings.extend(subiquity_snap_warnings)
        if snapd_snap is not None:
            LOGGER.info("Resolving %s snap revision %s for %s", snapd_snap.name, snapd_snap.revision, architecture)
            snapd_snap, snapd_warnings = self._snapcraft_resolver.resolve_revision(snapd_snap, architecture)
            warnings.extend(snapd_warnings)

        subiquity, subiquity_warnings = self._resolver.resolve_subiquity(bootstrap)
        secboot, secboot_warnings = self._resolver.resolve_secboot(snapd_snap)
        warnings.extend(subiquity_warnings)
        warnings.extend(secboot_warnings)

        return IsoRecord(
            release=release,
            architecture=architecture,
            iso_url=urljoin(base_url, iso.href) if iso else None,
            manifest_url=manifest_url,
            published_at=iso.modified if iso else None,
            ubuntu_desktop_bootstrap=bootstrap,
            subiquity_snap=subiquity_snap,
            snapd_snap=snapd_snap,
            snapd_deb=snapd_deb,
            subiquity=subiquity,
            secboot=secboot,
            warnings=tuple(warnings),
        )

    def collect_all(self, now: datetime | None = None) -> DashboardData:
        run_time = now if now is not None else _utc_now()
        generated_at = _format_time(run_time)
        records = tuple(self.collect_record(release, architecture) for release in RELEASES for architecture in ARCHITECTURES)
        return DashboardData(generated_at=generated_at, records=records)


def write_dashboard_json(data: DashboardData, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.to_json_dict(), indent=2, sort_keys=True) + "\n")
