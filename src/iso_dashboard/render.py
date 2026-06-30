from __future__ import annotations

import json
import shutil
import re
from html import escape
from pathlib import Path
from urllib.parse import urlparse

VANILLA_CSS = "https://assets.ubuntu.com/v1/vanilla-framework-version-1.8.0.min.css"

# Accept commit refs between 7 and 40 hex chars. Short 7-char refs are valid
# abbreviated commit identifiers used throughout the renderer and tests.
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
SECBOOT_PSEUDO_VERSION_RE = re.compile(r"^v0\.0\.0-\d{14}-([0-9a-f]{12,40})$", re.IGNORECASE)


def _package(value: dict[str, object] | None) -> str:
    if not value or not value.get("version"):
        return "unknown"
    version = escape(str(value["version"]))
    revision = value.get("revision")
    return f"{version} (rev {escape(str(revision))})" if revision else version


def _source(value: dict[str, object] | None) -> str:
    if not value or not value.get("ref"):
        return "unknown"
    raw_ref = str(value["ref"])
    display_ref = raw_ref
    url = value.get("url")
    raw_url = str(url).strip() if url else ""
    pseudo_version = SECBOOT_PSEUDO_VERSION_RE.fullmatch(raw_ref)
    if pseudo_version:
        commit = pseudo_version.group(1)
        display_ref = commit[:7]
        # If this value specifically refers to secboot (value.get("name")=="secboot"),
        # rewrite the URL to point to the canonical secboot commit page. For other
        # packages that happen to have a pseudo-version-shaped ref, we do NOT
        # rewrite the URL to snapcore/secboot; we only present the shortened
        # 7-character display ref.
        if value.get("name") == "secboot":
            raw_url = f"https://github.com/snapcore/secboot/commit/{commit}"
    elif COMMIT_RE.fullmatch(raw_ref):
        display_ref = raw_ref[:7]

    ref = escape(display_ref)
    title = f' title="{escape(raw_ref, quote=True)}"' if display_ref != raw_ref else ""
    if raw_url:
        # Only allow explicit http(s) URLs. Reject other schemes such as
        # javascript:, data:, vbscript:, file:, etc. When the scheme is not
        # safe, render only the escaped ref text (no href and no URL text).
        parsed = urlparse(raw_url)
        scheme = (parsed.scheme or "").lower()
        # Require a safe http(s) scheme and a non-empty netloc so malformed
        # URLs like "http:/nohost" (which parse with an empty netloc) are not
        # rendered as links. If the URL is unsafe or missing a host, render
        # only the escaped ref text.
        if scheme not in ("http", "https") or not parsed.netloc:
            return ref
        return f'<a href="{escape(raw_url, quote=True)}"{title}>{ref}</a>'
    return ref


def _warnings(values: list[str]) -> str:
    if not values:
        return "No warnings"
    return "".join(
        """
        <div class="p-notification--caution is-borderless">
          <div class="p-notification__content">
            <p class="p-notification__message">{message}</p>
          </div>
        </div>
""".format(message=escape(value))
        for value in values
    )


def _status(value: object) -> str:
    status = escape(str(value or "missing"))
    chip_class = "p-chip--positive" if status == "pending" else "p-chip--negative"
    return f'<span class="{chip_class}">{status}</span>'


def _card_status_class(status: str) -> str:
    return "is-missing-iso" if status == "missing" else "is-existing-iso"


def _detail(label: str, value: str) -> str:
    # NOTE: _detail() accepts `value` as an HTML fragment and does NOT escape
    # it. Callers must ensure `value` is safe (already escaped or intentionally
    # formatted). In this renderer `_package()` and `_source()` produce the
    # HTML fragments passed as `value` (they perform any required escaping);
    # escaping `value` here would break intended links/formatting.
    return f'<dt class="p-muted-heading">{escape(label)}</dt><dd>{value}</dd>'


def render_dashboard(payload: dict[str, object]) -> str:
    cards_by_architecture: dict[str, list[str]] = {}
    records = payload.get("records", [])
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        warnings = record.get("warnings", [])
        assert isinstance(warnings, list)
        release = str(record.get("release", "unknown"))
        architecture = str(record.get("architecture", "unknown"))
        status = str(record.get("iso_source", "missing"))
        card_status_class = _card_status_class(status)
        warning_count = len(warnings)
        warning_content = _warnings(warnings)
        warning_body = warning_content if warnings else '<p><span class="p-chip--positive">No warnings</span></p>'
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
          <div class="col-4" data-iso-card data-architecture="{escape(architecture, quote=True)}" data-release="{escape(release, quote=True)}" data-status="{escape(status, quote=True)}">
            <div class="p-card--highlighted {card_status_class}">
              <div class="u-clearfix">
                <h3>{escape(release)}</h3>
                <p class="u-align--right">{_status(status)}</p>
              </div>
              <p><strong>Published:</strong> {escape(str(record.get("published_at") or "unknown"))}</p>
              <dl>{details}</dl>
              <details>
                <summary>{warning_count} warnings</summary>
                {warning_body}
              </details>
            </div>
          </div>
"""
        cards_by_architecture.setdefault(architecture, []).append(card)

    generated_at = escape(str(payload.get("generated_at", "unknown")))
    architectures = payload.get("architectures", [])
    if not isinstance(architectures, list):
        architectures = []
    default_architecture = "amd64" if "amd64" in architectures else (str(architectures[0]) if architectures else "")
    architecture_options = "".join(
        f"<option value=\"{escape(str(architecture), quote=True)}\"{' selected' if str(architecture) == default_architecture else ''}>{escape(str(architecture))}</option>"
        for architecture in architectures
    )
    sections = "".join(
        f"""
    <section class="p-strip is-shallow" data-architecture-section="{escape(architecture, quote=True)}">
      <div class="row">
        <div class="col-12">
          <p class="p-muted-heading">Architecture</p>
          <h2>{escape(architecture)}</h2>
        </div>
      </div>
      <div class="row">{''.join(cards)}</div>
    </section>
"""
        for architecture, cards in cards_by_architecture.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ubuntu Desktop ISO Dashboard</title>
  <link rel="stylesheet" href="{VANILLA_CSS}">
  <style>
    .is-existing-iso {{ background: #f2fbf3; border-top: 4px solid #0e8420; }}
    .is-missing-iso {{ background: #fff2f2; border-top: 4px solid #c7162b; }}
  </style>
</head>
<body>
  <main>
    <section class="p-strip--suru is-dark">
      <div class="row">
        <div class="col-8">
          <h1>Ubuntu Desktop ISO Dashboard</h1>
          <p>Generated: {generated_at}</p>
        </div>
      </div>
    </section>
    <section class="p-strip is-shallow">
      <div class="row">
        <div class="col-12">
          <form class="p-form p-form--inline" aria-label="Dashboard filters">
            <div class="p-form__group">
              <label for="architecture-filter">Architecture</label>
              <select id="architecture-filter" data-architecture-filter>
                {architecture_options}
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
      const architectureFilter = document.querySelector('[data-architecture-filter]');
      if (!architectureFilter) {{
        return;
      }}

      function filterCards() {{
        const architecture = architectureFilter.value;
        document.querySelectorAll('[data-iso-card]').forEach((card) => {{
          const visible = !architecture || card.dataset.architecture === architecture;
          card.style.display = visible ? '' : 'none';
        }});
        document.querySelectorAll('[data-architecture-section]').forEach((section) => {{
          const hasVisibleCards = Array.from(section.querySelectorAll('[data-iso-card]')).some((card) => card.style.display !== 'none');
          section.hidden = !hasVisibleCards;
        }});
      }}

      architectureFilter.addEventListener('change', filterCards);
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
