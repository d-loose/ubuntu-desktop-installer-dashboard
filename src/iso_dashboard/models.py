from __future__ import annotations

from dataclasses import asdict, dataclass

from iso_dashboard.config import ARCHITECTURES, RELEASES

@dataclass(frozen=True)
class PackageVersion:
    name: str
    version: str | None
    revision: str | None
    channel: str | None = None


@dataclass(frozen=True)
class SourceRef:
    name: str
    ref: str | None
    url: str | None


@dataclass(frozen=True)
class IsoRecord:
    release: str
    architecture: str
    iso_url: str | None
    manifest_url: str | None
    published_at: str | None
    ubuntu_desktop_bootstrap: PackageVersion | None
    subiquity_snap: PackageVersion | None
    snapd_snap: PackageVersion | None
    snapd_deb: PackageVersion | None
    subiquity: SourceRef | None
    secboot: SourceRef | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class DashboardData:
    generated_at: str
    records: tuple[IsoRecord, ...]

    def to_json_dict(self) -> dict[str, object]:
        records = []
        for record in self.records:
            rd = asdict(record)
            # Convert warnings tuple -> list for JSON friendliness
            rd["warnings"] = list(rd.get("warnings", ()))
            records.append(rd)

        return {
            "generated_at": self.generated_at,
            "releases": list(RELEASES),
            "architectures": list(ARCHITECTURES),
            "records": records,
        }
