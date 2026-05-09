from __future__ import annotations

import argparse
from dataclasses import asdict

from .config import load_config, set_config_value
from .doctor import run_doctor
from .session import InteractiveSession


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fzgpt")
    parser.add_argument("--voice", action="store_true", help="voice-first input mode")
    parser.add_argument("--typed", action="store_true", help="typed-only input mode")

    sub = parser.add_subparsers(dest="subcommand")

    sub.add_parser("doctor", help="check local dependencies and runtime")

    config_parser = sub.add_parser("config", help="view or update config")
    config_sub = config_parser.add_subparsers(dest="config_cmd")

    config_sub.add_parser("show", help="show current config")
    set_parser = config_sub.add_parser("set", help="set config value")
    set_parser.add_argument("key")
    set_parser.add_argument("value")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    config = load_config()

    if args.subcommand == "doctor":
        raise SystemExit(run_doctor(config))

    if args.subcommand == "config":
        if args.config_cmd == "set":
            updated = set_config_value(args.key, args.value)
            print(f"Updated {args.key} = {getattr(updated, args.key)}")
            return
        data = asdict(config)
        for key in sorted(data):
            print(f"{key} = {data[key]}")
        return

    if args.voice and args.typed:
        parser.error("Choose either --voice or --typed, not both")

    if args.voice:
        mode = "voice"
    elif args.typed:
        mode = "typed"
    else:
        mode = "mixed"

    session = InteractiveSession(config=config, mode=mode)
    session.run()


if __name__ == "__main__":
    main()
