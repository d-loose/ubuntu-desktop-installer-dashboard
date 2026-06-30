from __future__ import annotations

import json
import shutil
from html import escape
from pathlib import Path

VANILLA_CSS = "https://assets.ubuntu.com/v1/vanilla-framework-version-1.8.0.min.css"


def _package(value: dict[str, object] | None) -> str:
    if not value or not value.get("version"):
        return "unknown"
    version = escape(str(value["version"]))
    revision = value.get("revision")
    return f"{version} (rev {escape(str(revision))})" if revision else version


def _source(value: dict[str, object] | None) -> str:
    if not value or not value.get("ref"):
        return "unknown"
    ref = escape(str(value["ref"]))
    url = value.get("url")
    if url:
        raw = str(url).strip()
        if raw.lower().startswith("javascript:"):
            return ref
        return f'<a href="{escape(raw, quote=True)}">{ref}</a>'
    return ref


def _warnings(values: list[str]) -> str:
    if not values:
        return "No warnings"
    return "".join(f'<li class="p-list__item is-ticked">{escape(value)}</li>' for value in values)


def _status(value: object) -> str:
    status = escape(str(value or "missing"))
    chip_class = "p-chip--positive" if status == "pending" else "p-chip--negative"
    return f'<span class="{chip_class}">{status}</span>'


def _detail(label: str, value: str) -> str:
    return f"<dt>{escape(label)}</dt><dd>{value}</dd>"


def render_dashboard(payload: dict[str, object]) -> str:
    cards_by_release: dict[str, list[str]] = {}
    records = payload.get("records", [])
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        warnings = record.get("warnings", [])
        assert isinstance(warnings, list)
        release = str(record.get("release", "unknown"))
        architecture = str(record.get("architecture", "unknown"))
        status = str(record.get("iso_source", "missing"))
        warning_count = len(warnings)
        warning_content = _warnings(warnings)
        warning_body = (
            f'<ul class="p-list">{warning_content}</ul>'
            if warnings
            else '<p><span class="p-chip--positive">No warnings</span></p>'
        )
        details = "".join(
            [
                _detail("ubuntu-desktop-bootstrap", _package(record.get("ubuntu_desktop_bootstrap"))),
                _detail("snapd snap", _package(record.get("snapd_snap"))),
                _detail("snapd deb", _package(record.get("snapd_deb"))),
                _detail("subiquity", _source(record.get("subiquity"))),
                _detail("secboot", _source(record.get("secboot"))),
            ]
        )
        card = f"""
          <div class="col-4" data-iso-card data-release="{escape(release, quote=True)}" data-status="{escape(status, quote=True)}">
            <div class="p-card">
              <h3>{escape(architecture)} {_status(status)}</h3>
              <p><strong>Published:</strong> {escape(str(record.get("published_at") or "unknown"))}</p>
              <dl>{details}</dl>
              <details>
                <summary>{warning_count} warnings</summary>
                {warning_body}
              </details>
            </div>
          </div>
"""
        cards_by_release.setdefault(release, []).append(card)

    warning_count = sum(len(record.get("warnings", [])) for record in records if isinstance(record, dict))
    generated_at = escape(str(payload.get("generated_at", "unknown")))
    releases = payload.get("releases", [])
    if not isinstance(releases, list):
        releases = []
    release_options = "".join(f'<option value="{escape(str(release), quote=True)}">{escape(str(release))}</option>' for release in releases)
    sections = "".join(
        f"""
    <section class="p-strip is-shallow" data-release-section="{escape(release, quote=True)}">
      <div class="row"><div class="col-12"><h2>{escape(release)}</h2></div></div>
      <div class="row">{''.join(cards)}</div>
    </section>
"""
        for release, cards in cards_by_release.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ubuntu Desktop ISO Dashboard</title>
  <link rel="stylesheet" href="{VANILLA_CSS}">
</head>
<body>
  <header class="p-navigation">
    <div class="p-navigation__row">
      <div class="p-navigation__banner">
        <div class="p-navigation__tagged-logo">
          <a class="p-navigation__link" href="#">
            <div class="p-navigation__logo-tag"><img class="p-navigation__logo-icon" src="https://assets.ubuntu.com/v1/82818827-CoF_white.svg" alt=""></div>
            <span class="p-navigation__logo-title">Ubuntu Desktop ISO Dashboard</span>
          </a>
        </div>
      </div>
    </div>
  </header>
  <main>
    <section class="p-strip is-shallow">
      <div class="row">
        <div class="col-12">
          <h1>Ubuntu Desktop ISO Dashboard</h1>
          <p>Generated: {generated_at}</p>
          <div class="p-card">
            <p class="p-heading--4">{len(records)} records, {warning_count} warnings</p>
          </div>
          <form class="p-form p-form--inline" aria-label="Dashboard filters">
            <div class="p-form__group">
              <label for="release-filter">Release</label>
              <select id="release-filter" data-release-filter>
                <option value="">All releases</option>
                {release_options}
              </select>
            </div>
            <div class="p-form__group">
              <label for="status-filter">Status</label>
              <select id="status-filter" data-status-filter>
                <option value="">All statuses</option>
                <option value="pending">pending</option>
                <option value="missing">missing</option>
              </select>
            </div>
          </form>
        </div>
      </div>
    </section>
    {sections}
  </main>
  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const releaseFilter = document.querySelector('[data-release-filter]');
      const statusFilter = document.querySelector('[data-status-filter]');
      if (!releaseFilter || !statusFilter) {{
        return;
      }}

      function filterCards() {{
        const release = releaseFilter.value;
        const status = statusFilter.value;
        document.querySelectorAll('[data-iso-card]').forEach((card) => {{
          const releaseMatch = !release || card.dataset.release === release;
          const statusMatch = !status || card.dataset.status === status;
          const visible = releaseMatch && statusMatch;
          card.style.display = visible ? '' : 'none';
        }});
        document.querySelectorAll('[data-release-section]').forEach((section) => {{
          const hasVisibleCards = Array.from(section.querySelectorAll('[data-iso-card]')).some((card) => card.style.display !== 'none');
          section.hidden = !hasVisibleCards;
        }});
      }}

      releaseFilter.addEventListener('change', filterCards);
      statusFilter.addEventListener('change', filterCards);
      filterCards();
    }});
  </script>
</body>
</html>
"""


def write_site(data_path: Path, site_dir: Path) -> None:
    payload = json.loads(data_path.read_text())
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(render_dashboard(payload))
    data_output = site_dir / "data" / "latest.json"
    data_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(data_path, data_output)
