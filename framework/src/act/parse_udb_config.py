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
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def validate_udb_config(udb_config_file: Path) -> None:
    validate_udb_config_cmd = [
        "./external/riscv-unified-db/bin/udb",
        "validate",
        "cfg",
        f"cfgs/{udb_config_file.name}",
    ]
    env = os.environ.copy()
    env["PODMAN"] = "true"
    subprocess.run(validate_udb_config_cmd, check=True, env=env)


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
            f"cfgs/{udb_config_file.name}",
            "--output",
            f"{udb_config_file.stem}_extensions.txt",
        ]
        env = os.environ.copy()
        env["PODMAN"] = "true"
        subprocess.run(generate_extensions_list_cmd, check=True, env=env)
        shutil.move(f"./external/riscv-unified-db/{udb_config_file.stem}_extensions.txt", extension_list_file)


def get_implemented_extensions(extension_list_file: Path) -> set[str]:
    return set(extension_list_file.read_text().splitlines())


def generate_udb_files(udb_config_file: Path, output_dir: Path) -> None:
    # TODO: Figure out a more robust way to handle UDB validation
    # Currently only works if using docker as container runtime and requires copying UDB config into riscv-unified-db directory

    copied_udb_config = Path(f"./external/riscv-unified-db/cfgs/{udb_config_file.name}")
    if not copied_udb_config.exists() or not filecmp.cmp(udb_config_file, copied_udb_config):
        shutil.copy(udb_config_file, copied_udb_config)
        validate_udb_config(udb_config_file)
    generate_extension_list(udb_config_file, output_dir)

    # TODO: Generate DUT specific header file from UDB

    # TODO: Generate Sail config file from UDB
