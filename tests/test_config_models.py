from iso_dashboard.config import ARCHITECTURES, RELEASES, pending_url
from iso_dashboard.models import DashboardData, IsoRecord, PackageVersion, SourceRef


def test_configured_release_and_architecture_lists_are_exact():
    assert RELEASES == ("noble", "resolute", "stonking")
    assert ARCHITECTURES == ("amd64", "arm64", "riscv")


def test_pending_url_uses_only_pending_location():
    assert pending_url("noble") == "https://cdimage.ubuntu.com/ubuntu/noble/daily-live/pending/"
    assert "current" not in pending_url("noble")


def test_dashboard_data_serializes_nested_records():
    record = IsoRecord(
        release="noble",
        architecture="amd64",
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
