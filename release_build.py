#!/usr/bin/env python3
"""
Bump application version and build the executable with PyInstaller.

Examples:
  python release_build.py --bump patch
  python release_build.py --set-version 2.0.0
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_LINE_PATTERN = re.compile(
    r'^(?P<prefix>\s*VERSION\s*=\s*")(?P<version>\d+\.\d+\.\d+)(")',
    re.MULTILINE,
)


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = SEMVER_PATTERN.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Invalid semantic version '{value}'. Expected format: X.Y.Z")
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def bump(self, part: str) -> "SemVer":
        if part == "major":
            return SemVer(self.major + 1, 0, 0)
        if part == "minor":
            return SemVer(self.major, self.minor + 1, 0)
        if part == "patch":
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unsupported bump type: {part}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump version in main.py and build the executable."
    )

    bump_group = parser.add_mutually_exclusive_group(required=True)
    bump_group.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        help="Increment semantic version part.",
    )
    bump_group.add_argument(
        "--set-version",
        help="Set an explicit semantic version (X.Y.Z).",
    )

    parser.add_argument(
        "--main-file",
        default="main.py",
        help="File containing VERSION constant (default: main.py).",
    )
    parser.add_argument(
        "--spec",
        default="build.spec",
        help="PyInstaller spec file to use (default: build.spec).",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete build/ and dist/ before building.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Only bump version, do not run PyInstaller.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without editing files or building.",
    )

    return parser.parse_args()


def resolve_path(root: Path, path_arg: str) -> Path:
    path = Path(path_arg)
    return path if path.is_absolute() else root / path


def read_current_version(main_file: Path) -> tuple[SemVer, str]:
    if not main_file.exists():
        raise FileNotFoundError(f"Main file not found: {main_file}")

    content = main_file.read_text(encoding="utf-8")
    match = VERSION_LINE_PATTERN.search(content)
    if not match:
        raise RuntimeError(f'Could not find a line like VERSION = "X.Y.Z" in {main_file}')

    return SemVer.parse(match.group("version")), content


def write_new_version(main_file: Path, content: str, new_version: SemVer) -> None:
    updated_content, count = VERSION_LINE_PATTERN.subn(
        rf'\g<prefix>{new_version}"',
        content,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Expected to update exactly one VERSION line, but that failed.")
    main_file.write_text(updated_content, encoding="utf-8")


def clean_build_artifacts(project_root: Path) -> None:
    for rel_path in ("build", "dist"):
        path = project_root / rel_path
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"Removed {path}")


def run_pyinstaller(project_root: Path, spec_file: Path) -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError(
            "PyInstaller is not installed in this interpreter. "
            "Install it with: python -m pip install pyinstaller"
        )
    command = [sys.executable, "-m", "PyInstaller", str(spec_file)]
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=project_root, check=True)


def print_artifact_summary(project_root: Path) -> None:
    dist_dir = project_root / "dist"
    if not dist_dir.exists():
        print("Build finished, but no dist/ directory was found.")
        return

    exes = sorted(dist_dir.rglob("*.exe"))
    if not exes:
        print(f"Build finished. Artifacts are in {dist_dir}")
        return

    print("Build artifacts:")
    for exe in exes:
        print(f"  - {exe}")


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent

    main_file = resolve_path(project_root, args.main_file)
    spec_file = resolve_path(project_root, args.spec)

    if not spec_file.exists() and not args.skip_build:
        raise FileNotFoundError(f"Spec file not found: {spec_file}")

    current_version, content = read_current_version(main_file)
    target_version = (
        current_version.bump(args.bump) if args.bump else SemVer.parse(args.set_version)
    )

    print(f"Current version: {current_version}")
    print(f"Target version:  {target_version}")

    if args.dry_run:
        print("Dry run: no files changed and no build started.")
        return 0

    if target_version != current_version:
        write_new_version(main_file, content, target_version)
        print(f"Updated {main_file} to version {target_version}")
    else:
        print("Version unchanged.")

    if args.skip_build:
        print("Skip-build enabled. Done.")
        return 0

    if not args.no_clean:
        clean_build_artifacts(project_root)

    run_pyinstaller(project_root, spec_file)
    print_artifact_summary(project_root)
    print("Release build completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Build command failed with exit code {exc.returncode}")
        raise SystemExit(exc.returncode)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error: {exc}")
        raise SystemExit(1)
