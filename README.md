# Ubuntu Desktop ISO Dashboard

Python-only static dashboard for pending Ubuntu Desktop ISO package and source dependency versions.

## Local Development

Install test dependencies:

```bash
python3 -m pip install -e '.[test]'
```

Run tests:

```bash
python3 -m pytest -v
```

Collect data only:

```bash
python3 -m iso_dashboard.cli collect --data data/latest.json
```

Render static HTML from existing data:

```bash
python3 -m iso_dashboard.cli render --data data/latest.json --site site
```

Collect data and render the site:

```bash
python3 -m iso_dashboard.cli build --data data/latest.json --site site
```

The collector reads only `https://cdimage.ubuntu.com/<release>/daily-live/pending/` and writes one record for every configured release and architecture pair.

## Deployment

`.github/workflows/pages.yml` runs daily at `06:17 UTC`, on manual dispatch, and publishes the generated `site/` directory to GitHub Pages.
