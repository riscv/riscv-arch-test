##################################
# parse_udb_config.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse UDB configuration file
##################################

import filecmp
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import rich
from ruamel.yaml import YAML


def update_udb_submodule() -> None:
    """Ensure the riscv-unified-db submodule is initialized and up to date."""
    udb_path = Path("./external/riscv-unified-db/bin/udb")

    if not udb_path.exists():
        print("riscv-unified-db not found; initializing submodule external/riscv-unified-db...")
    else:
        print("Updating riscv-unified-db submodule...")

    try:
        subprocess.run(["git", "submodule", "update", "--init", "--", "external/riscv-unified-db"], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "Failed to initialize/update riscv-unified-db submodule. Please run 'git submodule update --init' manually and try again."
        ) from e


def validate_udb_config(udb_config_file: Path) -> None:
    validate_udb_config_cmd = [
        "./external/riscv-unified-db/bin/udb",
        "validate",
        "cfg",
        f"{udb_config_file}",
        # f"cfgs/{udb_config_file.name}",
    ]
    env = os.environ.copy()
    env["PODMAN"] = "true"
    env["UDB_CONTAINER_BIND"] = str(udb_config_file.parent.resolve())
    try:
        subprocess.run(validate_udb_config_cmd, check=True, env=env)
    except subprocess.CalledProcessError:
        rich.print(f"[red][bold]UDB configuration validation failed for {udb_config_file.name}.[endc]")
        sys.exit(1)


def get_config_params(udb_config_file: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe", pure=True)
    udb_config = yaml.load(udb_config_file.read_text())
    config_params = udb_config["params"]
    return config_params


def generate_extension_list(udb_config_file: Path, output_dir: Path) -> None:
    extension_list_file = output_dir / "extensions.txt"
    if not extension_list_file.exists() or (extension_list_file.stat().st_mtime < udb_config_file.stat().st_mtime):
        print(f"Generating extension list for {udb_config_file.stem}")
        generate_extensions_list_cmd = [
            "./external/riscv-unified-db/bin/udb",
            "list",
            "extensions",
            "--config",
            f"{udb_config_file}",
            "--output",
            f"{udb_config_file.stem}_extensions.txt",
        ]
        env = os.environ.copy()
        env["PODMAN"] = "true"
        env["UDB_CONTAINER_BIND"] = str(udb_config_file.parent.resolve())
        subprocess.run(generate_extensions_list_cmd, check=True, env=env)
        shutil.move(f"./external/riscv-unified-db/{udb_config_file.stem}_extensions.txt", extension_list_file)


def get_implemented_extensions(extension_list_file: Path) -> set[str]:
    return set(extension_list_file.read_text().splitlines())


def generate_udb_files(udb_config_file: Path, output_dir: Path) -> None:
    if (
        not (output_dir / "extensions.txt").exists()
        or (output_dir / "extensions.txt").stat().st_mtime < udb_config_file.stat().st_mtime
    ):
        update_udb_submodule()
        validate_udb_config(udb_config_file)
        generate_extension_list(udb_config_file, output_dir)

    # TODO: Generate DUT specific header file from UDB

    # TODO: Generate Sail config file from UDB
