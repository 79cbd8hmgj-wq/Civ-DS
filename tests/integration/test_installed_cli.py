from pathlib import Path
import os
import subprocess
import sys


def test_cli_loads_packaged_registry_outside_repository(tmp_path: Path) -> None:
    environment = os.environ.copy()
    # Exercise resource lookup from an unrelated directory. CI separately installs
    # the wheel; the source path keeps this regression runnable without setuptools.
    source = Path(__file__).resolve().parents[2] / "src"
    environment["PYTHONPATH"] = str(source)
    result = subprocess.run(
        [sys.executable, "-m", "civds", "--help"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "validate-rom" in result.stdout
