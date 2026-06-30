import json
from datetime import datetime, timezone
from pathlib import Path

from iso_dashboard.collector import Collector, write_dashboard_json
from iso_dashboard.models import PackageVersion, SourceRef


PENDING_URL = "https://cdimage.ubuntu.com/ubuntu/noble/daily-live/pending/"
MANIFEST_URL = "https://cdimage.ubuntu.com/ubuntu/noble/daily-live/pending/noble-desktop-amd64.manifest"


class FakeResolver:
    def __init__(self):
        self.bootstrap = None
        self.snapd = None

    def resolve_subiquity(self, bootstrap):
        self.bootstrap = bootstrap
        return SourceRef("subiquity", "subiquity-sha", "https://github.com/canonical/subiquity/commit/subiquity-sha"), ()

    def resolve_secboot(self, snapd):
        self.snapd = snapd
        return SourceRef("secboot", "v1", "https://github.com/snapcore/secboot/tree/v1"), ()


class FakeSnapcraftResolver:
    def resolve_revision(self, snap, architecture):
        versions = {
            "ubuntu-desktop-bootstrap": "26.04-3b3d4a4cc",
            "snapd": "2.70.1",
        }
        return PackageVersion(snap.name, versions[snap.name], snap.revision), ()


def test_collect_record_builds_complete_pending_record():
    responses = {
        PENDING_URL: '<a href="noble-desktop-amd64.iso">noble-desktop-amd64.iso</a> 2026-06-29 10:15\n<a href="noble-desktop-amd64.manifest">noble-desktop-amd64.manifest</a> 2026-06-29 10:16',
        MANIFEST_URL: "snap:ubuntu-desktop-bootstrap 1.2.3 42\nsnap:snapd 2.70 24718\nsnapd 2.70+ubuntu1\n",
    }
    resolver = FakeResolver()
    collector = Collector(lambda url: responses[url], resolver, FakeSnapcraftResolver())

    record = collector.collect_record("noble", "amd64")

    assert record.release == "noble"
    assert record.architecture == "amd64"
    assert record.iso_source == "pending"
    assert record.iso_url == "https://cdimage.ubuntu.com/ubuntu/noble/daily-live/pending/noble-desktop-amd64.iso"
    assert record.manifest_url == MANIFEST_URL
    assert record.published_at == "2026-06-29T10:15:00Z"
    assert record.ubuntu_desktop_bootstrap.version == "26.04-3b3d4a4cc"
    assert record.snapd_snap.version == "2.70.1"
    assert record.snapd_deb.version == "2.70+ubuntu1"
    assert resolver.bootstrap == PackageVersion("ubuntu-desktop-bootstrap", "26.04-3b3d4a4cc", "42")
    assert resolver.snapd == PackageVersion("snapd", "2.70.1", "24718")
    assert record.subiquity.ref == "subiquity-sha"
    assert record.secboot.ref == "v1"
    assert record.warnings == ()


def test_collect_record_logs_key_steps(caplog):
    responses = {
        PENDING_URL: '<a href="noble-desktop-amd64.iso">noble-desktop-amd64.iso</a> 2026-06-29 10:15\n<a href="noble-desktop-amd64.manifest">noble-desktop-amd64.manifest</a> 2026-06-29 10:16',
        MANIFEST_URL: "snap:ubuntu-desktop-bootstrap 1.2.3 42\nsnap:snapd 2.70 24718\nsnapd 2.70+ubuntu1\n",
    }
    collector = Collector(lambda url: responses[url], FakeResolver(), FakeSnapcraftResolver())

    with caplog.at_level("INFO", logger="iso_dashboard.collector"):
        collector.collect_record("noble", "amd64")

    assert "Collecting noble amd64 from https://cdimage.ubuntu.com/ubuntu/noble/daily-live/pending/" in caplog.messages
    assert "Fetching manifest https://cdimage.ubuntu.com/ubuntu/noble/daily-live/pending/noble-desktop-amd64.manifest" in caplog.messages


def test_collect_record_keeps_missing_record_when_listing_fetch_fails():
    def failing_get(url: str) -> str:
        raise RuntimeError("network unavailable")

    collector = Collector(failing_get, FakeResolver())

    record = collector.collect_record("noble", "amd64")

    assert record.iso_source == "missing"
    assert record.iso_url is None
    assert record.manifest_url is None
    assert record.warnings == ("Cannot fetch pending listing for noble: network unavailable",)


def test_collect_all_writes_one_record_per_configured_pair():
    collector = Collector(lambda url: "", FakeResolver())

    data = collector.collect_all(datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc))

    assert data.generated_at == "2026-06-29T12:00:00Z"
    assert len(data.records) == 9
    assert {(record.release, record.architecture) for record in data.records} == {
        ("noble", "amd64"), ("noble", "arm64"), ("noble", "riscv"),
        ("resolute", "amd64"), ("resolute", "arm64"), ("resolute", "riscv"),
        ("stonking", "amd64"), ("stonking", "arm64"), ("stonking", "riscv"),
    }


def test_write_dashboard_json_creates_parent_directory_and_json(tmp_path):
    collector = Collector(lambda url: "", FakeResolver())
    data = collector.collect_all(datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc))
    output = tmp_path / "data" / "latest.json"

    write_dashboard_json(data, output)

    payload = json.loads(output.read_text())
    assert payload["generated_at"] == "2026-06-29T12:00:00Z"
    assert len(payload["records"]) == 9
