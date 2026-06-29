from __future__ import annotations

import json
import shutil
from html import escape
from pathlib import Path


CSS = """
:root { color-scheme: light; font-family: Ubuntu, Arial, sans-serif; }
body { margin: 0; background: #f7f3ef; color: #111; }
header { background: #2c001e; color: white; padding: 2rem; }
main { padding: 1.5rem; }
table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
th, td { border-bottom: 1px solid #ddd; padding: .75rem; text-align: left; vertical-align: top; }
th { background: #eee7df; }
.status-pending { color: #0b6b2b; font-weight: 700; }
.status-missing { color: #a00000; font-weight: 700; }
.warnings { color: #8a4b00; }
a { color: #06c; }
@media (max-width: 900px) { table, thead, tbody, tr, th, td { display: block; } th { display: none; } td::before { content: attr(data-label); display: block; font-weight: 700; } }
""".strip() + "\n"


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
        # Strip surrounding whitespace from URL and escape it for safe inclusion in href.
        # Additionally, do not render javascript: URLs as active links; render the escaped ref instead.
        raw = str(url).strip()
        lowered = raw.lower()
        if lowered.startswith("javascript:"):
            return ref
        safe_url = escape(raw, quote=True)
        return f'<a href="{safe_url}">{ref}</a>'
    return ref


def _warnings(values: list[str]) -> str:
    if not values:
        return "No warnings"
    return "<br>".join(escape(value) for value in values)


def render_dashboard(payload: dict[str, object]) -> str:
    rows = []
    records = payload.get("records", [])
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        status = escape(str(record.get("iso_source", "missing")))
        warnings = record.get("warnings", [])
        assert isinstance(warnings, list)
        rows.append(
            "<tr>"
            f'<td data-label="Release">{escape(str(record.get("release", "unknown")))}</td>'
            f'<td data-label="Architecture">{escape(str(record.get("architecture", "unknown")))}</td>'
            f'<td data-label="ISO"><span class="status-{status}">{status}</span><br>{escape(str(record.get("published_at") or "unknown"))}</td>'
            f'<td data-label="ubuntu-desktop-bootstrap">{_package(record.get("ubuntu_desktop_bootstrap"))}</td>'
            f'<td data-label="snapd snap">{_package(record.get("snapd_snap"))}</td>'
            f'<td data-label="snapd deb">{_package(record.get("snapd_deb"))}</td>'
            f'<td data-label="subiquity">{_source(record.get("subiquity"))}</td>'
            f'<td data-label="secboot">{_source(record.get("secboot"))}</td>'
            f'<td data-label="Warnings" class="warnings">{_warnings(warnings)}</td>'
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
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header>
    <h1>Ubuntu Desktop ISO Dashboard</h1>
    <p>Generated: {generated_at}</p>
    <p>{len(records)} records, {warning_count} warnings</p>
  </header>
  <main>
    <table>
      <thead><tr><th>Release</th><th>Architecture</th><th>ISO</th><th>ubuntu-desktop-bootstrap</th><th>snapd snap</th><th>snapd deb</th><th>subiquity</th><th>secboot</th><th>Warnings</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </main>
</body>
</html>
"""


def write_site(data_path: Path, site_dir: Path) -> None:
    payload = json.loads(data_path.read_text())
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(render_dashboard(payload))
    (site_dir / "styles.css").write_text(CSS)
    data_output = site_dir / "data" / "latest.json"
    data_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(data_path, data_output)
