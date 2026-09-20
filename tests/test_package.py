import subprocess
import sys


def test_module_exposes_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "wx_red_helper", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "Windows 微信红包本地助手" in completed.stdout
