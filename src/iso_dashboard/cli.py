from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from iso_dashboard.collector import Collector, write_dashboard_json
from iso_dashboard.render import write_site

LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"


def _add_logging_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING, format=LOG_FORMAT)


def _configure_github_token(token: str | None) -> None:
    if token:
        os.environ["GITHUB_TOKEN"] = token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="iso-dashboard")
    subcommands = parser.add_subparsers(dest="command", required=True)

    collect = subcommands.add_parser("collect")
    collect.add_argument("--data", type=Path, default=Path("data/latest.json"))
    collect.add_argument("--github-token", default=None, help="GitHub token for authenticated API requests")
    _add_logging_flag(collect)

    render = subcommands.add_parser("render")
    render.add_argument("--data", type=Path, default=Path("data/latest.json"))
    render.add_argument("--site", type=Path, default=Path("site"))

    build = subcommands.add_parser("build")
    build.add_argument("--data", type=Path, default=Path("data/latest.json"))
    build.add_argument("--site", type=Path, default=Path("site"))
    build.add_argument("--github-token", default=None, help="GitHub token for authenticated API requests")
    _add_logging_flag(build)

    args = parser.parse_args(argv)
    if args.command == "collect":
        _configure_logging(args.verbose)
        _configure_github_token(args.github_token)
        write_dashboard_json(Collector().collect_all(), args.data)
        return 0
    if args.command == "render":
        write_site(args.data, args.site)
        return 0
    if args.command == "build":
        _configure_logging(args.verbose)
        _configure_github_token(args.github_token)
        write_dashboard_json(Collector().collect_all(), args.data)
        write_site(args.data, args.site)
        return 0
    raise AssertionError(f"Unhandled command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
