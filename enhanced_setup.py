"""Create a reproducible local ImageProcessorPro environment."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import Sequence


MINIMUM_PYTHON = (3, 11)


def run_command(command: Sequence[str], description: str) -> None:
    """Run a fixed argv command without invoking a shell."""
    print(f"\n{description}\n  {' '.join(command)}")
    subprocess.run(list(command), check=True)


def environment_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create .venv and install pinned ImageProcessorPro dependencies."
    )
    parser.add_argument("--with-pdf", action="store_true", help="Install optional PyMuPDF support")
    parser.add_argument("--with-api", action="store_true", help="Install the localhost API prototype")
    parser.add_argument("--with-azure", action="store_true", help="Install Azure Blob/managed-identity helpers")
    parser.add_argument("--with-build", action="store_true", help="Install the pinned PyInstaller toolchain")
    parser.add_argument("--dev", action="store_true", help="Install tests and dependency auditing tools")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    if sys.version_info < MINIMUM_PYTHON:
        print("Python 3.11 or newer is required.", file=sys.stderr)
        return 2

    project_root = Path(__file__).resolve().parent
    environment = project_root / ".venv"
    if not environment.exists():
        print(f"Creating isolated environment at {environment}")
        venv.EnvBuilder(with_pip=True).create(environment)

    python = environment_python(environment)
    extras = ["gui"]
    for enabled, name in (
        (args.with_pdf, "pdf"),
        (args.with_api, "api"),
        (args.with_azure, "azure"),
        (args.with_build, "build"),
        (args.dev, "dev"),
    ):
        if enabled:
            extras.append(name)

    run_command([str(python), "-m", "pip", "install", "--upgrade", "pip"], "Updating pip")
    target = f".[{','.join(extras)}]"
    run_command([str(python), "-m", "pip", "install", "-e", target], "Installing pinned dependencies")

    for folder in ("input", "output", "logs", "temp", "watermarks"):
        (project_root / folder).mkdir(exist_ok=True)

    print("\nSetup complete.")
    print(f"CLI: {python} cli.py --help")
    print(f"GUI: {python} gui_app.py")
    if args.dev:
        print(f"Tests: {python} -m pytest")
    if not args.with_pdf:
        print("PDF support was not installed. Review PyMuPDF licensing, then rerun with --with-pdf if appropriate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
