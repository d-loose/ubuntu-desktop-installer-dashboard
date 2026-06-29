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
