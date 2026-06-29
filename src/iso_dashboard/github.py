from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
import urllib.error
from collections.abc import Callable

from iso_dashboard.models import PackageVersion, SourceRef

HttpClient = Callable[[str], str]
LOGGER = logging.getLogger(__name__)


def http_get_text(url: str) -> str:
    headers = {
        "User-Agent": "ubuntu-desktop-iso-dashboard",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
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
            except (json.JSONDecodeError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                # preserve diagnostic context for why a candidate failed
                LOGGER.debug("tag lookup failed for %s: %s", url, exc)
                continue
            tag_object = payload.get("object", {})
            sha = tag_object.get("sha")
            if not isinstance(sha, str) or not sha:
                continue
            if tag_object.get("type") != "tag":
                return sha
            commit_sha = self._dereference_tag(owner, repo, sha)
            if commit_sha:
                return commit_sha
        return None

    def _dereference_tag(self, owner: str, repo: str, tag_sha: str) -> str | None:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/tags/{tag_sha}"
        try:
            payload = json.loads(self._http_get(url))
        except (json.JSONDecodeError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            LOGGER.debug("annotated tag dereference failed for %s: %s", url, exc)
            return None
        tag_object = payload.get("object", {})
        commit_sha = tag_object.get("sha")
        if tag_object.get("type") == "commit" and isinstance(commit_sha, str) and commit_sha:
            return commit_sha
        return None

    def _bootstrap_source_ref(self, version: str) -> str | None:
        match = re.search(r"-([0-9a-f]{7,40})$", version)
        if match:
            return match.group(1)
        return self._tag_sha("canonical", "ubuntu-desktop-provision", version)

    def resolve_subiquity(self, bootstrap: PackageVersion | None) -> tuple[SourceRef | None, tuple[str, ...]]:
        if bootstrap is None or bootstrap.version is None:
            return None, ("Cannot resolve subiquity because ubuntu-desktop-bootstrap snap is missing",)

        LOGGER.info("Resolving subiquity for ubuntu-desktop-bootstrap version %s", bootstrap.version)
        source_sha = self._bootstrap_source_ref(bootstrap.version)
        if source_sha is None:
            return None, (f"Cannot map ubuntu-desktop-bootstrap version {bootstrap.version} to a canonical/ubuntu-desktop-provision source ref",)
        LOGGER.info(
            "Using ubuntu-desktop-provision ref %s for ubuntu-desktop-bootstrap version %s",
            source_sha,
            bootstrap.version,
        )

        try:
            tree = json.loads(
                self._http_get(f"https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/{source_sha}")
            )
        except (json.JSONDecodeError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            # keep the public warning unchanged but log the underlying failure for diagnostics
            LOGGER.warning(
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

        LOGGER.info("Resolving secboot for snapd version %s", snapd.version)
        source_sha = self._tag_sha("snapcore", "snapd", snapd.version)
        if source_sha is None:
            return None, (f"Cannot map snapd version {snapd.version} to a snapcore/snapd source ref",)
        LOGGER.info("Using snapd source ref %s for snapd version %s", source_sha, snapd.version)

        try:
            go_mod = self._http_get(f"https://raw.githubusercontent.com/snapcore/snapd/{source_sha}/go.mod")
        except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            # keep the public warning unchanged but preserve context in logs
            LOGGER.warning("Cannot read snapd go.mod at source ref %s: %s", source_sha, exc)
            return None, (f"Cannot read snapd go.mod at source ref {source_sha}",)

        match = re.search(r"github\.com/snapcore/secboot\s+(\S+)", go_mod)
        if not match:
            return None, (f"Cannot find github.com/snapcore/secboot in snapd go.mod at source ref {source_sha}",)

        ref = match.group(1)
        return SourceRef("secboot", ref, f"https://github.com/snapcore/secboot/tree/{ref}"), ()
