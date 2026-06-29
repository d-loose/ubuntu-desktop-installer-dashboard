# Ubuntu Desktop ISO Dashboard

Python-only static dashboard for pending Ubuntu Desktop ISO package and source dependency versions.

## Local Development

Run tests:

```bash
python3 -m pytest
```

Build data and static HTML:

```bash
python3 -m iso_dashboard.cli build --data data/latest.json --site site
```

The collector reads only `https://cdimage.ubuntu.com/<release>/daily-live/pending/` and writes one record for every configured release and architecture pair.
