import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows 微信红包本地助手")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("run", "collect-template", "show-config"),
    )
    parser.parse_args()
    return 0
