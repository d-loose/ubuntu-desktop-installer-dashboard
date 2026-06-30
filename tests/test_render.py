import json

from iso_dashboard.render import render_dashboard, write_site


def sample_payload():
    return {
        "generated_at": "2026-06-29T12:00:00Z",
        "releases": ["noble"],
        "architectures": ["amd64", "arm64"],
        "records": [
            {
                "release": "noble",
                "architecture": "amd64",
                "iso_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.iso",
                "manifest_url": "https://cdimage.ubuntu.com/noble/daily-live/pending/noble-desktop-amd64.manifest",
                "published_at": "2026-06-29T10:15:00Z",
                "ubuntu_desktop_bootstrap": {"name": "ubuntu-desktop-bootstrap", "version": "1.2.3", "revision": "42", "channel": "26.04/stable/ubuntu-26.04.1"},
                "subiquity_snap": {"name": "subiquity", "version": "26.04+git18.64b0c70", "revision": "1234", "channel": "26.04/stable/ubuntu-26.04.1"},
                "snapd_snap": {"name": "snapd", "version": "2.70", "revision": "24718", "channel": "stable"},
                "snapd_deb": {"name": "snapd", "version": "2.70+ubuntu1", "revision": None, "channel": None},
                "subiquity": {
                    "name": "subiquity",
                    "ref": "64b0c70ec29dcc597a1f554486c61fcd634ce86d",
                    "url": "https://github.com/canonical/subiquity/commit/64b0c70ec29dcc597a1f554486c61fcd634ce86d",
                },
                "secboot": {
                    "name": "secboot",
                    "ref": "v0.0.0-20260302105957-77bc2457cc76",
                    "url": "https://github.com/snapcore/secboot/tree/v0.0.0-20260302105957-77bc2457cc76",
                },
                "warnings": [],
            },
            {
                "release": "noble",
                "architecture": "arm64",
                "iso_url": None,
                "manifest_url": None,
                "published_at": None,
                "ubuntu_desktop_bootstrap": None,
                "snapd_snap": None,
                "snapd_deb": None,
                "subiquity": None,
                "secboot": None,
                "warnings": ["Missing pending ISO for noble arm64"],
            },
            {
                "release": "noble-old",
                "architecture": "amd64",
                "iso_url": "https://cdimage.ubuntu.com/noble-old/daily-live/pending/noble-old-desktop-amd64.iso",
                "manifest_url": "https://cdimage.ubuntu.com/noble-old/daily-live/pending/noble-old-desktop-amd64.manifest",
                "published_at": "2026-06-28T22:05:00Z",
                "ubuntu_desktop_bootstrap": None,
                "snapd_snap": None,
                "snapd_deb": None,
                "subiquity": None,
                "secboot": None,
                "warnings": [],
            },
        ],
    }


def test_render_dashboard_includes_summary_table_and_links():
    html = render_dashboard(sample_payload())

    assert "Ubuntu Desktop ISO Dashboard" in html
    assert "https://assets.ubuntu.com/v1/vanilla-framework-version-" in html
    assert "p-navigation" not in html
    assert "p-strip" in html
    assert "data-architecture-filter" in html
    assert "data-release-filter" not in html
    assert "data-status-filter" not in html
    assert "data-iso-card" in html
    assert "data-architecture-section" in html
    assert "<details" in html
    assert "function filterCards" in html
    assert "DOMContentLoaded" in html
    assert "section.hidden = !hasVisibleCards" in html
    assert '<option value="amd64" selected>amd64</option>' in html
    assert '<option value="arm64">arm64</option>' in html
    assert 'data-architecture="amd64"' in html
    assert 'data-architecture="arm64"' in html
    assert 'data-architecture-section="amd64"' in html
    assert 'data-architecture-section="arm64"' in html
    assert 'data-status="current"' in html
    assert 'data-status="old"' in html
    assert 'data-status="missing"' in html
    assert "const architecture = architectureFilter.value" in html
    assert "card.dataset.architecture === architecture" in html
    assert "card.style.display = visible ? '' : 'none'" in html
    assert "statusFilter" not in html
    assert "Generated: 2026-06-29T12:00:00Z" in html
    assert "29 Jun 2026, 10:15 UTC" in html
    assert "28 Jun 2026, 22:05 UTC" in html
    assert "noble" in html
    assert "amd64" in html
    assert "1.2.3 (channel 26.04/stable/ubuntu-26.04.1, rev 42)" in html
    assert "snapd snap" not in html
    assert "snapd deb" not in html
    assert "subiquity snap" not in html
    assert "subiquity source" not in html
    assert "subiquity check" not in html
    assert "dashboard-detail-list" in html
    assert '<dt>snap</dt><dd>2.70 (channel stable, rev 24718)</dd>' in html
    assert '<dt>deb</dt><dd>2.70+ubuntu1</dd>' in html
    assert '<dt>snap</dt><dd>26.04+git18.64b0c70 (channel 26.04/stable/ubuntu-26.04.1, rev 1234)</dd>' in html
    assert '<dt>source</dt><dd><a href="https://github.com/canonical/subiquity/commit/64b0c70ec29dcc597a1f554486c61fcd634ce86d" title="64b0c70ec29dcc597a1f554486c61fcd634ce86d">64b0c70</a></dd>' in html
    assert "OK match" in html
    assert "Subiquity snap matches source" in html
    assert "2.70 (channel stable, rev 24718)" in html
    assert "2.70+ubuntu1" in html
    assert ">64b0c70<" in html
    assert 'title="64b0c70ec29dcc597a1f554486c61fcd634ce86d"' in html
    assert "https://github.com/canonical/subiquity/commit/64b0c70ec29dcc597a1f554486c61fcd634ce86d" in html
    assert ">77bc245<" in html
    assert 'title="v0.0.0-20260302105957-77bc2457cc76"' in html
    assert "https://github.com/snapcore/secboot/commit/77bc2457cc76" in html
    assert "https://github.com/snapcore/secboot/tree/v0.0.0-20260302105957-77bc2457cc76" not in html
    assert "No warnings" in html
    assert "p-strip--suru" in html
    assert "p-card--highlighted" in html
    assert "p-muted-heading" in html
    assert "p-notification--caution" in html
    assert "p-notification__message" in html
    assert "u-align--right" in html
    assert "is-current-iso" in html
    assert "is-old-iso" in html
    assert "is-missing-iso" in html
    assert "background: #f2fbf3" in html
    assert "background: #fff8e6" in html
    assert "background: #fff2f2" in html
    assert "Records" not in html
    assert "Warnings</p>" not in html
    assert "Releases</p>" not in html


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


def test_render_highlights_subiquity_snap_mismatch():
    payload = sample_payload()
    payload["records"][0]["subiquity_snap"]["version"] = "26.04+git18.deadbee"

    html = render_dashboard(payload)

    assert "! mismatch" in html
    assert "Subiquity snap does not match source" in html
    assert "p-chip--caution" in html


def test_render_ignores_legacy_iso_source_field():
    payload = sample_payload()
    payload["records"][0]["iso_source"] = "missing"

    html = render_dashboard(payload)

    assert 'data-status="current"' in html


def test_source_url_scheme_hardening():
    # Ensure unsafe URL schemes are not rendered as links or visible URL text
    payload = sample_payload()
    # set subiquity url to javascript: should not render as link
    payload["records"][0]["subiquity"] = {"ref": "badref", "url": "javascript:alert(1)"}
    # set secboot url to data: should not render as link
    payload["records"][0]["secboot"] = {"ref": "badref2", "url": "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=="}
    # add a vbscript: style URL to the second record
    payload["records"][1]["subiquity"] = {"ref": "badref3", "url": "vbscript:msgbox(1)"}
    # add malformed http(s) source URLs with empty netloc which urlparse accepts
    # but should not be rendered as links (no host present)
    payload["records"][1]["secboot"] = {"ref": "badref4", "url": "http:/nohost"}
    payload["records"].append(
        {
            "release": "noble",
            "architecture": "riscv64",
            "published_at": None,
            "ubuntu_desktop_bootstrap": None,
            "snapd_snap": None,
            "snapd_deb": None,
            "subiquity": {"ref": "badref5", "url": "https:/still-no-host"},
            "secboot": None,
            "warnings": [],
        }
    )

    html = render_dashboard(payload)

    # None of the unsafe schemes should be present in the rendered HTML
    assert "javascript:" not in html.lower()
    assert "data:" not in html.lower()
    assert "vbscript:" not in html.lower()
    # The display refs should still be present (escaped) but not as hrefs
    assert "badref" in html
    assert "badref2" in html
    assert "badref3" in html
    assert "badref4" in html
    assert "badref5" in html
    # The raw malformed http(s) URLs must not be rendered as visible text
    assert "http:/nohost" not in html
    assert "https:/still-no-host" not in html


def test_commit_and_pseudo_version_scoping():
    payload = sample_payload()
    # A 7-char commit ref should display and remain safe
    payload["records"][0]["subiquity"] = {"ref": "abcdef1", "url": "https://example.com/commit/abcdef1"}

    # A secboot pseudo-version should be rewritten to snapcore/secboot commit URL
    payload["records"][0]["secboot"] = {"ref": "v0.0.0-20260302105957-77bc2457cc76", "url": None, "name": "secboot"}

    # A non-secboot package with a similarly shaped pseudo-version must NOT be
    # rewritten away from its own URL; it should show the short 7-char ref.
    payload["records"][1]["subiquity"] = {"ref": "v0.0.0-20260302105957-77bc2457cc76", "url": "https://example.com/other/77bc2457cc76", "name": "notsecboot"}

    html = render_dashboard(payload)

    # 7-char commit ref appears and is linked
    assert ">abcdef1<" in html
    assert 'https://example.com/commit/abcdef1' in html

    # secboot pseudo-version rewrites to snapcore commit URL
    assert 'https://github.com/snapcore/secboot/commit/77bc2457cc76' in html

    # Non-secboot pseudo-version keeps its custom URL and short display.
    assert ">77bc245<" in html
    assert 'https://example.com/other/77bc2457cc76' in html


def test_published_at_without_timezone_renders_unknown():
    payload = sample_payload()
    payload["records"][0]["published_at"] = "2026-06-29T10:15:00"

    html = render_dashboard(payload)

    assert "2026-06-29T10:15:00" not in html
    assert "Published:</strong> unknown" in html


def test_write_site_writes_index_css_and_json_copy(tmp_path):
    data_path = tmp_path / "data" / "latest.json"
    data_path.parent.mkdir()
    data_path.write_text(json.dumps(sample_payload()))

    write_site(data_path, tmp_path / "site")

    assert (tmp_path / "site" / "index.html").exists()
    assert not (tmp_path / "site" / "styles.css").exists()
    assert (tmp_path / "site" / "data" / "latest.json").exists()
