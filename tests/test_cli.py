from fzgpt import cli


def test_parser_rejects_both_modes():
    parser = cli._build_parser()
    args = parser.parse_args(["--voice"])
    assert args.voice is True
    assert args.typed is False


def test_parser_config_set():
    parser = cli._build_parser()
    args = parser.parse_args(["config", "set", "model", "qwen2.5-coder"])
    assert args.subcommand == "config"
    assert args.config_cmd == "set"
    assert args.key == "model"
