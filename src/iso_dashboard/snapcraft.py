from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable

from iso_dashboard.models import PackageVersion

SNAPCRAFT_REFRESH_URL = "https://api.snapcraft.io/v2/snaps/refresh"
SNAPCRAFT_ARCHITECTURES = {"riscv": "riscv64"}
LOGGER = logging.getLogger(__name__)

JsonPostClient = Callable[[str, dict[str, str], dict[str, object]], str]


def http_post_json(url: str, headers: dict[str, str], payload: dict[str, object]) -> str:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"User-Agent": "ubuntu-desktop-iso-dashboard", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


class SnapcraftResolver:
    def __init__(self, post_json: JsonPostClient = http_post_json) -> None:
        self._post_json = post_json

    def resolve_revision(self, snap: PackageVersion, architecture: str) -> tuple[PackageVersion, tuple[str, ...]]:
        if snap.revision is None:
            return snap, (f"Cannot resolve {snap.name} snap revision because revision is missing",)

        try:
            revision = int(snap.revision)
        except ValueError:
            return snap, (f"Cannot resolve {snap.name} snap revision {snap.revision} because it is not numeric",)

        headers = {
            "Snap-Device-Series": "16",
            "Snap-Device-Architecture": SNAPCRAFT_ARCHITECTURES.get(architecture, architecture),
            "Content-Type": "application/json",
        }
        LOGGER.info("Resolving %s revision %s for %s via Snapcraft", snap.name, snap.revision, architecture)
        payload: dict[str, object] = {
            "context": [],
            "actions": [
                {
                    "action": "install",
                    "instance-key": "preview",
                    "name": snap.name,
                    "revision": revision,
                }
            ],
        }

        try:
            response = json.loads(self._post_json(SNAPCRAFT_REFRESH_URL, headers, payload))
        except (json.JSONDecodeError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            return snap, (f"Cannot resolve {snap.name} snap revision {snap.revision} via Snapcraft: {exc}",)

        for result in response.get("results", []):
            resolved = result.get("snap", {})
            if resolved.get("name") == snap.name and str(resolved.get("revision")) == str(revision):
                version = resolved.get("version")
                if isinstance(version, str) and version:
                    LOGGER.info("Resolved %s revision %s to version %s", snap.name, snap.revision, version)
                    return PackageVersion(snap.name, version, snap.revision, snap.channel), ()

        return snap, (f"Cannot resolve {snap.name} snap revision {snap.revision} via Snapcraft: response did not include snap",)

    def resolve_channel(self, name: str, channel: str | None, architecture: str) -> tuple[PackageVersion | None, tuple[str, ...]]:
        if not channel:
            return None, (f"Cannot resolve {name} snap channel because channel is missing",)

        headers = {
            "Snap-Device-Series": "16",
            "Snap-Device-Architecture": SNAPCRAFT_ARCHITECTURES.get(architecture, architecture),
            "Content-Type": "application/json",
        }
        LOGGER.info("Resolving %s channel %s for %s via Snapcraft", name, channel, architecture)
        payload: dict[str, object] = {
            "context": [],
            "actions": [
                {
                    "action": "install",
                    "instance-key": "preview",
                    "name": name,
                    "channel": channel,
                }
            ],
        }

        try:
            response = json.loads(self._post_json(SNAPCRAFT_REFRESH_URL, headers, payload))
        except (json.JSONDecodeError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            return None, (f"Cannot resolve {name} snap channel {channel} via Snapcraft: {exc}",)

        for result in response.get("results", []):
            resolved = result.get("snap", {})
            if resolved.get("name") == name:
                version = resolved.get("version")
                revision = resolved.get("revision")
                if isinstance(version, str) and version and revision is not None:
                    LOGGER.info("Resolved %s channel %s to version %s revision %s", name, channel, version, revision)
                    return PackageVersion(name, version, str(revision), channel), ()

        return None, (f"Cannot resolve {name} snap channel {channel} via Snapcraft: response did not include snap",)
