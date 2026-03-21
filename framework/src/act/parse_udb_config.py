##################################
# parse_udb_config.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse UDB configuration file
##################################

import importlib.resources
import shutil
import subprocess
import sys
from pathlib import Path

import rich
from ruamel.yaml import YAML


def _find_gemfile() -> Path:
    """Locate the Gemfile bundled with the act package."""
    gemfile_path = Path(str(importlib.resources.files("act"))) / "data" / "Gemfile"
    if not gemfile_path.exists():
        raise RuntimeError(
            "No Gemfile found in act package data. Install the udb gem with 'gem install udb' or reinstall act."
        )
    return gemfile_path


def _ensure_udb_installed() -> None:
    """Ensure the correct version of the UDB gem is installed via bundler.

    Uses `bundle check` to verify that installed gems match Gemfile.lock.
    If gems are missing or out of date, runs `bundle install` to fix them.
    """
    gemfile = _find_gemfile()

    # Check if all gems (including udb) are installed at the correct versions
    try:
        subprocess.run(["bundle", "check"], check=True, cwd=gemfile.parent, capture_output=True, text=True)
        return  # All gems satisfied — correct version is installed
    except FileNotFoundError as e:
        raise RuntimeError(
            "udb command not found and 'bundle' is not available. See the README for installation instructions."
        ) from e
    except subprocess.CalledProcessError:
        pass  # Gems missing or wrong version — need to install (done below)

    print("UDB gem missing or out of date; running 'bundle install'...")
    try:
        subprocess.run(["bundle", "install"], check=True, cwd=gemfile.parent)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("'bundle install' failed. Check Ruby and bundler installation.") from e

    if shutil.which("udb") is None:
        raise RuntimeError("UDB command still not found after 'bundle install'.")


def validate_udb_config(udb_config_file: Path) -> None:
    validate_cmd = ["udb", "validate", "cfg", str(udb_config_file)]
    try:
        subprocess.run(validate_cmd, check=True)
    except subprocess.CalledProcessError:
        rich.print(f"[red][bold]UDB configuration validation failed for {udb_config_file.name}.[/bold][/red]")
        sys.exit(1)


def get_config_params(udb_config_file: Path) -> dict[str, int | bool | str | list[int | str | bool]]:
    yaml = YAML(typ="safe", pure=True)
    udb_config = yaml.load(udb_config_file.read_text())
    config_params = udb_config["params"]
    return config_params


def generate_extension_list(udb_config_file: Path, output_dir: Path) -> None:
    extension_list_file = output_dir / "extensions.txt"
    if not extension_list_file.exists() or (extension_list_file.stat().st_mtime < udb_config_file.stat().st_mtime):
        print(f"Generating extension list for {udb_config_file.stem}")
        generate_cmd = [
            "udb",
            "list",
            "extensions",
            "--config",
            str(udb_config_file),
            "--output",
            str(extension_list_file),
        ]
        subprocess.run(generate_cmd, check=True)


def get_implemented_extensions(extension_list_file: Path) -> set[str]:
    return set(extension_list_file.read_text().splitlines())


def generate_udb_files(udb_config_file: Path, output_dir: Path) -> None:
    if (
        not (output_dir / "extensions.txt").exists()
        or (output_dir / "extensions.txt").stat().st_mtime < udb_config_file.stat().st_mtime
    ):
        _ensure_udb_installed()
        validate_udb_config(udb_config_file)
        generate_extension_list(udb_config_file, output_dir)

    # TODO: Generate DUT specific header file from UDB

    # TODO: Generate Sail config file from UDB
