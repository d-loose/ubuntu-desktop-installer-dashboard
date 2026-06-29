from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from iso_dashboard.models import PackageVersion

SNAPCRAFT_REFRESH_URL = "https://api.snapcraft.io/v2/snaps/refresh"
SNAPCRAFT_ARCHITECTURES = {"riscv": "riscv64"}

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
                    return PackageVersion(snap.name, version, snap.revision), ()

        return snap, (f"Cannot resolve {snap.name} snap revision {snap.revision} via Snapcraft: response did not include snap",)
