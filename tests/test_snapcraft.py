import json

from iso_dashboard.models import PackageVersion
from iso_dashboard.snapcraft import SnapcraftResolver


def test_resolve_revision_uses_snapcraft_refresh_api_request():
    requests = []

    def post_json(url, headers, payload):
        requests.append((url, headers, payload))
        return json.dumps(
            {
                "results": [
                    {
                        "snap": {
                            "name": "ubuntu-desktop-bootstrap",
                            "version": "26.04-3b3d4a4cc",
                            "revision": 628,
                        }
                    }
                ]
            }
        )

    resolver = SnapcraftResolver(post_json)

    resolved, warnings = resolver.resolve_revision(
        PackageVersion("ubuntu-desktop-bootstrap", None, "628"),
        "amd64",
    )

    assert warnings == ()
    assert resolved == PackageVersion("ubuntu-desktop-bootstrap", "26.04-3b3d4a4cc", "628")
    assert requests == [
        (
            "https://api.snapcraft.io/v2/snaps/refresh",
            {
                "Snap-Device-Series": "16",
                "Snap-Device-Architecture": "amd64",
                "Content-Type": "application/json",
            },
            {
                "context": [],
                "actions": [
                    {
                        "action": "install",
                        "instance-key": "preview",
                        "name": "ubuntu-desktop-bootstrap",
                        "revision": 628,
                    }
                ],
            },
        )
    ]


def test_resolve_revision_returns_original_with_warning_when_lookup_fails():
    def failing_post(url, headers, payload):
        raise RuntimeError("snapcraft unavailable")

    resolver = SnapcraftResolver(failing_post)
    original = PackageVersion("snapd", None, "24718")

    resolved, warnings = resolver.resolve_revision(original, "arm64")

    assert resolved == original
    assert warnings == ("Cannot resolve snapd snap revision 24718 via Snapcraft: snapcraft unavailable",)
