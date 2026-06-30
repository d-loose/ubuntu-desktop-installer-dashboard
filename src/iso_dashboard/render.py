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
        return '<span class="p-chip--positive">No warnings</span>'
    return "".join(f'<li class="p-list__item is-ticked">{escape(value)}</li>' for value in values)


def _status(value: object) -> str:
    status = escape(str(value or "missing"))
    chip_class = "p-chip--positive" if status == "pending" else "p-chip--negative"
    return f'<span class="{chip_class}">{status}</span>'


def render_dashboard(payload: dict[str, object]) -> str:
    rows = []
    records = payload.get("records", [])
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        warnings = record.get("warnings", [])
        assert isinstance(warnings, list)
        rows.append(
            "<tr>"
            f'<td>{escape(str(record.get("release", "unknown")))}</td>'
            f'<td>{escape(str(record.get("architecture", "unknown")))}</td>'
            f'<td>{_status(record.get("iso_source", "missing"))}<br>{escape(str(record.get("published_at") or "unknown"))}</td>'
            f'<td>{_package(record.get("ubuntu_desktop_bootstrap"))}</td>'
            f'<td>{_package(record.get("snapd_snap"))}</td>'
            f'<td>{_package(record.get("snapd_deb"))}</td>'
            f'<td>{_source(record.get("subiquity"))}</td>'
            f'<td>{_source(record.get("secboot"))}</td>'
            f'<td><ul class="p-list">{_warnings(warnings)}</ul></td>'
            "</tr>"
        )

    warning_count = sum(len(record.get("warnings", [])) for record in records if isinstance(record, dict))
    generated_at = escape(str(payload.get("generated_at", "unknown")))
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
        </div>
      </div>
    </section>
    <section class="p-strip is-shallow">
      <div class="row">
        <div class="col-12">
          <div class="p-table-wrapper">
            <table class="p-table">
              <thead><tr><th>Release</th><th>Architecture</th><th>ISO</th><th>ubuntu-desktop-bootstrap</th><th>snapd snap</th><th>snapd deb</th><th>subiquity</th><th>secboot</th><th>Warnings</th></tr></thead>
              <tbody>{''.join(rows)}</tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  </main>
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
