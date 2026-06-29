from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
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
        # module-level logger to preserve diagnostic context on failures
        self._logger = logging.getLogger(__name__)

    def _tag_sha(self, owner: str, repo: str, version: str) -> str | None:
        candidates = (version, f"v{version}")
        for candidate in candidates:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{candidate}"
            try:
                payload = json.loads(self._http_get(url))
            except (json.JSONDecodeError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                # preserve diagnostic context for why a candidate failed
                self._logger.debug("tag lookup failed for %s: %s", url, exc)
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
        except (json.JSONDecodeError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            # keep the public warning unchanged but log the underlying failure for diagnostics
            self._logger.warning(
                "Cannot read ubuntu-desktop-provision tree %s for subiquity submodule: %s",
                source_sha,
                exc,
            )
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
        except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            # keep the public warning unchanged but preserve context in logs
            self._logger.warning("Cannot read snapd go.mod at source ref %s: %s", source_sha, exc)
            return None, (f"Cannot read snapd go.mod at source ref {source_sha}",)

        match = re.search(r"github\.com/snapcore/secboot\s+(\S+)", go_mod)
        if not match:
            return None, (f"Cannot find github.com/snapcore/secboot in snapd go.mod at source ref {source_sha}",)

        ref = match.group(1)
        return SourceRef("secboot", ref, f"https://github.com/snapcore/secboot/tree/{ref}"), ()
