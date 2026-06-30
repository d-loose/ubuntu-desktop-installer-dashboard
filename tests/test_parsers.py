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


def test_parse_cdimage_listing_extracts_modified_times_from_table_cells():
    html = """
<tr><td><a href="resolute-desktop-amd64.iso">resolute-desktop-amd64.iso</a></td><td align="right">2026-06-25 08:31  </td><td align="right">6.1G</td></tr>
<tr><td><a href="resolute-desktop-amd64.manifest">resolute-desktop-amd64.manifest</a></td><td align="right">2026-06-25 08:31  </td><td align="right"> 58K</td></tr>
"""

    artifacts = parse_cdimage_listing(html)

    assert artifacts[0].name == "resolute-desktop-amd64.iso"
    assert artifacts[0].modified == "2026-06-25T08:31:00Z"
    assert artifacts[1].name == "resolute-desktop-amd64.manifest"
    assert artifacts[1].modified == "2026-06-25T08:31:00Z"


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
    assert versions.ubuntu_desktop_bootstrap.version is None
    assert versions.ubuntu_desktop_bootstrap.channel == "26.04/stable/ubuntu-26.04.1"
    assert versions.ubuntu_desktop_bootstrap.revision == "42"
    assert versions.snapd_snap is not None
    assert versions.snapd_snap.version is None
    assert versions.snapd_snap.channel == "stable"
    assert versions.snapd_snap.revision == "24718"
    assert versions.snapd_deb is not None
    assert versions.snapd_deb.version == "2.70+ubuntu1"
    assert versions.snapd_deb.channel is None
    assert versions.snapd_deb.revision is None
