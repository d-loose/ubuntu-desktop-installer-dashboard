CDIMAGE_BASE_URL = "https://cdimage.ubuntu.com"
RELEASES = ("noble", "resolute", "stonking")
ARCHITECTURES = ("amd64", "arm64", "riscv")


def pending_url(release: str) -> str:
    return f"{CDIMAGE_BASE_URL}/{release}/daily-live/pending/"
