#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "ruamel-yaml>=0.18.16",
# ]
# ///
"""Discover CI configurations from config directory and output JSON matrix for GitHub Actions.

Reads config/<simulator>/ci.yaml for simulator-level settings and
config/<simulator>/<config>/run_cmd.txt for per-config run commands.

Usage:
    .github/scripts/ci_config.py    # JSON matrix for GitHub Actions
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from ruamel.yaml import YAML


def load_simulator_ci_yaml(ci_yaml_path: Path) -> dict:
    """Load a simulator-level ci.yaml file."""
    yaml = YAML()
    with ci_yaml_path.open() as f:
        data = yaml.load(f)
    return data if data else {}


def file_hash(path: Path) -> str:
    """Return the first 12 hex chars of the SHA-256 hash of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def discover_configs(config_dir: Path) -> list[dict]:
    """Discover all CI-enabled configs and return matrix entries."""
    entries: list[dict] = []

    for sim_ci_yaml in sorted(config_dir.rglob("*/ci.yaml")):
        sim_dir = sim_ci_yaml.parent
        sim_name = sim_dir.name

        sim_config = load_simulator_ci_yaml(sim_ci_yaml)

        # Skip simulators that are not enabled for CI
        if not sim_config.get("ci_enabled", True):
            continue

        # Extract settings from ci.yaml
        exclude_extensions = sim_config.get("exclude_extensions", "")
        install_script = sim_config.get("install_script", "")
        exclude_configs: set[str] = set(sim_config.get("exclude_configs", []))

        # Cache key is derived from the install script's content hash.
        # When the script changes (e.g., version bump), the cache automatically invalidates.
        cache_key = ""
        if install_script:
            script_path = Path(install_script)
            if script_path.is_file():
                cache_key = f"{sim_name}-{file_hash(script_path)}"

        # Find all configs with run_cmd.txt
        for run_cmd_file in sorted(sim_dir.rglob("*/run_cmd.txt")):
            config_name = run_cmd_file.parent.name

            # Skip disabled configs
            if config_name in exclude_configs:
                continue

            run_cmd = run_cmd_file.read_text().strip()
            config_file = str(run_cmd_file.parent / "test_config.yaml")

            entries.append(
                {
                    "simulator": sim_name,
                    "config": config_name,
                    "config_file": config_file,
                    "run_cmd": run_cmd,
                    "exclude_extensions": exclude_extensions,
                    "install_script": install_script,
                    "cache_key": cache_key,
                }
            )

    return entries


def main() -> int:
    config_dir = Path("config")
    if not config_dir.is_dir():
        print("Error: config/ directory not found. Run from repo root.", file=sys.stderr)
        return 1

    entries = discover_configs(config_dir)

    matrix = {"include": entries}
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
