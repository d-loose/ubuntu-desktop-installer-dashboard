import json

from iso_dashboard.render import render_dashboard, write_site


def sample_payload():
    return {
        "generated_at": "2026-06-29T12:00:00Z",
        "releases": ["noble"],
        "architectures": ["amd64"],
        "records": [
            {
                "release": "noble",
                "architecture": "amd64",
                "iso_source": "pending",
                "iso_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.iso",
                "manifest_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.manifest",
                "published_at": "2026-06-29T10:15:00Z",
                "ubuntu_desktop_bootstrap": {"name": "ubuntu-desktop-bootstrap", "version": "1.2.3", "revision": "42"},
                "snapd_snap": {"name": "snapd", "version": "2.70", "revision": "24718"},
                "snapd_deb": {"name": "snapd", "version": "2.70+ubuntu1", "revision": None},
                "subiquity": {"name": "subiquity", "ref": "subiquity-sha", "url": "https://github.com/canonical/subiquity/commit/subiquity-sha"},
                "secboot": {"name": "secboot", "ref": "v1", "url": "https://github.com/snapcore/secboot/tree/v1"},
                "warnings": [],
            }
        ],
    }


def test_render_dashboard_includes_summary_table_and_links():
    html = render_dashboard(sample_payload())

    assert "Ubuntu Desktop ISO Dashboard" in html
    assert "https://assets.ubuntu.com/v1/vanilla-framework-version-" in html
    assert "p-navigation" in html
    assert "p-strip" in html
    assert "data-release-filter" in html
    assert "data-status-filter" in html
    assert "data-iso-card" in html
    assert "<details" in html
    assert "function filterCards" in html
    assert "Generated: 2026-06-29T12:00:00Z" in html
    assert "noble" in html
    assert "amd64" in html
    assert "1.2.3 (rev 42)" in html
    assert "2.70 (rev 24718)" in html
    assert "2.70+ubuntu1" in html
    assert "subiquity-sha" in html
    assert "https://github.com/canonical/subiquity/commit/subiquity-sha" in html
    assert "No warnings" in html


def test_escapes_malicious_html_in_warnings_and_source():
    # Malicious content in warning and source ref/url should be escaped
    payload = sample_payload()
    # inject a warning containing a script tag
    payload["records"][0]["warnings"] = ['Found issue <script>alert(1)</script>']
    # inject malicious ref and URL into subiquity
    payload["records"][0]["subiquity"] = {"ref": "bad-ref<script>", "url": " javascript:alert(2) "}

    html = render_dashboard(payload)

    assert "Found issue &lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "bad-ref&lt;script&gt;" in html
    assert "javascript:alert(2)" not in html.lower()


def test_write_site_writes_index_css_and_json_copy(tmp_path):
    data_path = tmp_path / "data" / "latest.json"
    data_path.parent.mkdir()
    data_path.write_text(json.dumps(sample_payload()))

    write_site(data_path, tmp_path / "site")

    assert (tmp_path / "site" / "index.html").exists()
    assert not (tmp_path / "site" / "styles.css").exists()
    assert (tmp_path / "site" / "data" / "latest.json").exists()
