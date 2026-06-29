import json
import logging

from iso_dashboard import cli


def test_render_command_writes_site_from_existing_json(tmp_path):
    data_path = tmp_path / "data" / "latest.json"
    site_dir = tmp_path / "site"
    data_path.parent.mkdir()
    data_path.write_text(json.dumps({"generated_at": "2026-06-29T12:00:00Z", "records": []}))

    result = cli.main(["render", "--data", str(data_path), "--site", str(site_dir)])

    assert result == 0
    assert (site_dir / "index.html").exists()
    assert (site_dir / "data" / "latest.json").exists()


def test_build_command_collects_json_and_renders_site(monkeypatch, tmp_path):
    class FakeCollector:
        def collect_all(self):
            from iso_dashboard.models import DashboardData

            return DashboardData(generated_at="2026-06-29T12:00:00Z", records=())

    monkeypatch.setattr(cli, "Collector", lambda: FakeCollector())
    data_path = tmp_path / "data" / "latest.json"
    site_dir = tmp_path / "site"

    result = cli.main(["build", "--data", str(data_path), "--site", str(site_dir)])

    assert result == 0
    assert json.loads(data_path.read_text())["generated_at"] == "2026-06-29T12:00:00Z"
    assert (site_dir / "index.html").exists()


def test_verbose_collect_configures_info_logging(monkeypatch, tmp_path):
    configured = []

    class FakeCollector:
        def collect_all(self):
            from iso_dashboard.models import DashboardData

            return DashboardData(generated_at="2026-06-29T12:00:00Z", records=())

    def fake_basic_config(**kwargs):
        configured.append(kwargs)

    monkeypatch.setattr(cli, "Collector", lambda: FakeCollector())
    monkeypatch.setattr(cli.logging, "basicConfig", fake_basic_config)

    result = cli.main(["collect", "--data", str(tmp_path / "latest.json"), "--verbose"])

    assert result == 0
    assert configured == [{"level": logging.INFO, "format": "%(levelname)s:%(name)s:%(message)s"}]


def test_quiet_build_configures_warning_logging(monkeypatch, tmp_path):
    configured = []

    class FakeCollector:
        def collect_all(self):
            from iso_dashboard.models import DashboardData

            return DashboardData(generated_at="2026-06-29T12:00:00Z", records=())

    def fake_basic_config(**kwargs):
        configured.append(kwargs)

    monkeypatch.setattr(cli, "Collector", lambda: FakeCollector())
    monkeypatch.setattr(cli.logging, "basicConfig", fake_basic_config)

    result = cli.main(["build", "--data", str(tmp_path / "latest.json"), "--site", str(tmp_path / "site")])

    assert result == 0
    assert configured == [{"level": logging.WARNING, "format": "%(levelname)s:%(name)s:%(message)s"}]
