import json
import urllib.error
import urllib.request

from iso_dashboard.github import GithubResolver
from iso_dashboard.github import http_get_text
from iso_dashboard.models import PackageVersion


def test_http_get_text_never_uses_authorization_header(monkeypatch):
    captured = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout):
        captured.append(request)
        return FakeResponse()

    monkeypatch.setenv("GITHUB_TOKEN", "token-value")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert http_get_text("https://api.github.com/example") == "{}"
    assert "Authorization" not in captured[0].headers
    assert captured[0].headers["Accept"] == "application/vnd.github+json"


def test_resolve_subiquity_reads_submodule_gitlink_from_matching_tag():
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/ref/tags/1.2.3": json.dumps(
            {"object": {"sha": "provision-sha"}}
        ),
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/provision-sha?recursive=1": json.dumps(
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


def test_resolve_subiquity_uses_bootstrap_version_hash_suffix_as_source_ref():
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/b4490bc9b?recursive=1": json.dumps(
            {"tree": [{"path": "subiquity", "type": "commit", "sha": "subiquity-sha"}]}
        ),
    }
    resolver = GithubResolver(lambda url: responses[url])

    source, warnings = resolver.resolve_subiquity(
        PackageVersion("ubuntu-desktop-bootstrap", "26.04-b4490bc9b", "628")
    )

    assert warnings == ()
    assert source is not None
    assert source.ref == "subiquity-sha"


def test_resolve_subiquity_reads_source_commit_from_snap_branch_snapcraft_yaml():
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/b4490bc9b?recursive=1": json.dumps(
            {"tree": [{"path": "snap", "type": "tree", "sha": "snap-tree-sha"}]}
        ),
        "https://raw.githubusercontent.com/canonical/ubuntu-desktop-provision/b4490bc9b/snap/snapcraft.yaml": """
parts:
  ubuntu-bootstrap:
    source: .
    source-commit: &commit-ref 7c278ba1b1353b2798caa96d1a536063841d5176
    source-type: git
""",
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/7c278ba1b1353b2798caa96d1a536063841d5176?recursive=1": json.dumps(
            {"tree": [{"path": "packages/subiquity_client/subiquity", "type": "commit", "sha": "subiquity-sha"}]}
        ),
    }
    resolver = GithubResolver(lambda url: responses[url])

    source, warnings = resolver.resolve_subiquity(
        PackageVersion("ubuntu-desktop-bootstrap", "26.04-b4490bc9b", "628")
    )

    assert warnings == ()
    assert source is not None
    assert source.ref == "subiquity-sha"


def test_resolve_subiquity_reports_snap_and_source_refs_when_submodule_missing():
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/b4490bc9b?recursive=1": json.dumps(
            {"tree": [{"path": "snap", "type": "tree", "sha": "snap-tree-sha"}]}
        ),
        "https://raw.githubusercontent.com/canonical/ubuntu-desktop-provision/b4490bc9b/snap/snapcraft.yaml": """
parts:
  ubuntu-bootstrap:
    source-commit: 7c278ba1b1353b2798caa96d1a536063841d5176
""",
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/7c278ba1b1353b2798caa96d1a536063841d5176?recursive=1": json.dumps(
            {"tree": [{"path": "packages/subiquity_client/lib", "type": "tree", "sha": "tree-sha"}]}
        ),
    }
    resolver = GithubResolver(lambda url: responses[url])

    source, warnings = resolver.resolve_subiquity(
        PackageVersion("ubuntu-desktop-bootstrap", "26.04-b4490bc9b", "628")
    )

    assert source is None
    assert warnings == (
        "Cannot find subiquity submodule in ubuntu-desktop-provision tree b4490bc9b or ubuntu-bootstrap source commit 7c278ba1b1353b2798caa96d1a536063841d5176",
    )


def test_resolve_subiquity_dereferences_plain_bootstrap_annotated_tag():
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/ref/tags/26.04": json.dumps(
            {"object": {"sha": "tag-sha", "type": "tag"}}
        ),
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/tags/tag-sha": json.dumps(
            {"object": {"sha": "commit-sha", "type": "commit"}}
        ),
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/commit-sha?recursive=1": json.dumps(
            {"tree": [{"path": "subiquity", "type": "commit", "sha": "subiquity-sha"}]}
        ),
    }
    resolver = GithubResolver(lambda url: responses[url])

    source, warnings = resolver.resolve_subiquity(PackageVersion("ubuntu-desktop-bootstrap", "26.04", "628"))

    assert warnings == ()
    assert source is not None
    assert source.ref == "subiquity-sha"


def test_resolve_subiquity_logs_version_resolution(caplog):
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/b4490bc9b?recursive=1": json.dumps(
            {"tree": [{"path": "subiquity", "type": "commit", "sha": "subiquity-sha"}]}
        ),
    }
    resolver = GithubResolver(lambda url: responses[url])

    with caplog.at_level("INFO", logger="iso_dashboard.github"):
        resolver.resolve_subiquity(PackageVersion("ubuntu-desktop-bootstrap", "26.04-b4490bc9b", "628"))

    assert "Resolving subiquity for ubuntu-desktop-bootstrap version 26.04-b4490bc9b" in caplog.messages
    assert "Using ubuntu-desktop-provision ref b4490bc9b for ubuntu-desktop-bootstrap version 26.04-b4490bc9b" in caplog.messages


def test_resolver_caches_github_fetches_for_repeated_refs():
    calls = []
    responses = {
        "https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/b4490bc9b?recursive=1": json.dumps(
            {"tree": [{"path": "subiquity", "type": "commit", "sha": "subiquity-sha"}]}
        ),
    }

    def http_get(url):
        calls.append(url)
        return responses[url]

    resolver = GithubResolver(http_get)

    resolver.resolve_subiquity(PackageVersion("ubuntu-desktop-bootstrap", "26.04-b4490bc9b", "628"))
    resolver.resolve_subiquity(PackageVersion("ubuntu-desktop-bootstrap", "26.04-b4490bc9b", "629"))

    assert calls == ["https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/b4490bc9b?recursive=1"]


def test_resolver_stops_github_requests_after_rate_limit():
    calls = []

    def http_get(url):
        calls.append(url)
        raise urllib.error.HTTPError(url, 403, "rate limit exceeded", {}, None)

    resolver = GithubResolver(http_get)

    first_source, first_warnings = resolver.resolve_subiquity(
        PackageVersion("ubuntu-desktop-bootstrap", "26.04-b4490bc9b", "628")
    )
    second_source, second_warnings = resolver.resolve_secboot(PackageVersion("snapd", "2.75.2", "24718"))

    assert first_source is None
    assert first_warnings == ("Cannot read ubuntu-desktop-provision tree b4490bc9b for subiquity submodule",)
    assert second_source is None
    assert second_warnings == ("Skipping GitHub lookup for snapd version 2.75.2 because GitHub rate limit was already reached",)
    assert calls == ["https://api.github.com/repos/canonical/ubuntu-desktop-provision/git/trees/b4490bc9b?recursive=1"]


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
    assert source.ref == "abcdef123456"
    assert source.url == "https://github.com/snapcore/secboot/commit/abcdef123456"


def test_resolve_secboot_dereferences_annotated_snapd_tag_to_commit():
    responses = {
        "https://api.github.com/repos/snapcore/snapd/git/ref/tags/2.75.2": json.dumps(
            {"object": {"sha": "tag-sha", "type": "tag"}}
        ),
        "https://api.github.com/repos/snapcore/snapd/git/tags/tag-sha": json.dumps(
            {"object": {"sha": "commit-sha", "type": "commit"}}
        ),
        "https://raw.githubusercontent.com/snapcore/snapd/commit-sha/go.mod": "module github.com/snapcore/snapd\nrequire github.com/snapcore/secboot v0.0.0-20260629000000-abcdef123456\n",
    }
    resolver = GithubResolver(lambda url: responses[url])

    source, warnings = resolver.resolve_secboot(PackageVersion("snapd", "2.75.2", "24718"))

    assert warnings == ()
    assert source is not None
    assert source.ref == "abcdef123456"


def test_resolver_returns_unknown_warning_when_tag_lookup_fails():
    def failing_get(url: str) -> str:
        raise RuntimeError(f"404 for {url}")

    resolver = GithubResolver(failing_get)

    source, warnings = resolver.resolve_secboot(PackageVersion("snapd", "2.70", "24718"))

    assert source is None
    assert warnings == ("Cannot map snapd version 2.70 to a snapcore/snapd source ref",)
