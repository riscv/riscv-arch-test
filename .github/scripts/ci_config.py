#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ruamel-yaml>=0.18.16",
# ]
# ///
"""Discover CI configurations from config directory and output JSON matrix for GitHub Actions.

Reads config/<simulator>/ci.yaml for simulator-level settings and
config/<simulator>/<config>/run_cmd.txt for per-config run commands. Each
config is fanned out into N shards (per the simulator's ``shards`` setting);
the EXTENSIONS list for each shard is computed once here via weighted
Longest-Processing-Time bin-packing over the testsuites.

Usage:
    .github/scripts/ci_config.py    # JSON matrix for GitHub Actions
"""

from __future__ import annotations

import hashlib
import heapq
import json
import subprocess
import sys
from collections import Counter
from functools import cache
from pathlib import Path

from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SUITE_WEIGHT = 1  # for suites that have no checked-in .S files yet


def _list_testsuites() -> list[str]:
    """Return the complete sorted list of testsuites.

    Delegates to testgen so this stays a single source of truth — vector
    filtering, the priv registry, and which CSVs count as testsuites are all
    decided there.
    """
    sys.path.insert(0, str(REPO_ROOT / "generators" / "testgen" / "src"))
    from testgen.io.testplans import get_extensions  # type: ignore[import-not-found]
    from testgen.priv import get_priv_test_extensions  # type: ignore[import-not-found]

    return sorted({*get_extensions(REPO_ROOT / "testplans"), *get_priv_test_extensions()})


def _suite_weights(suites: list[str]) -> dict[str, int]:
    """Estimate per-suite cost by counting tracked .S files under tests/<*>/<suite>/.

    ``git ls-files`` is used so this is deterministic on any clean checkout
    and requires no prior test-generation step in CI.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "tests"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return dict.fromkeys(suites, _DEFAULT_SUITE_WEIGHT)

    suite_set = set(suites)
    counter: Counter[str] = Counter()
    for line in out.splitlines():
        if not line.endswith(".S"):
            continue
        # Layout is tests/<bucket>/<suite>/<file>.S where <bucket> is one of
        # rv32i, rv32e, rv64i, rv64e, priv. The suite name is the
        # second-to-last path component.
        parts = line.split("/")
        if len(parts) < 3:
            continue
        suite = parts[-2]
        if suite in suite_set:
            counter[suite] += 1

    return {suite: counter.get(suite, _DEFAULT_SUITE_WEIGHT) or _DEFAULT_SUITE_WEIGHT for suite in suites}


@cache
def _shard_assignments(shard_total: int, exclude: str = "") -> tuple[tuple[str, ...], ...]:
    """Return the sorted suite tuple for every shard using LPT bin-packing.

    Suites are sorted by descending weight (ties broken by suite name for
    determinism) and each is placed on the currently-lightest shard via a
    min-heap. Excluded suites are dropped from each shard's final list. The
    result is cached because every config under a given simulator shares the
    same ``(shard_total, exclude)`` pair, and the assignment is otherwise pure.
    """
    if shard_total < 1:
        raise ValueError(f"shard_total must be >= 1, got {shard_total}")

    all_suites = _list_testsuites()
    weights = _suite_weights(all_suites)
    ordered = sorted(all_suites, key=lambda s: (-weights[s], s))

    heap: list[tuple[int, int, list[str]]] = [(0, i, []) for i in range(shard_total)]
    heapq.heapify(heap)
    for suite in ordered:
        load, idx, bucket = heapq.heappop(heap)
        bucket.append(suite)
        heapq.heappush(heap, (load + weights[suite], idx, bucket))

    buckets = sorted(heap, key=lambda entry: entry[1])
    exclude_set = {e.strip() for e in exclude.split(",") if e.strip()}
    return tuple(tuple(sorted(s for s in bucket if s not in exclude_set)) for _, _, bucket in buckets)


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
        apt_packages = sim_config.get("apt_packages", "")
        setup_script = sim_config.get("setup_script", "")
        exclude_configs: set[str] = set(sim_config.get("exclude_configs", []))
        # Number of CI runners to split each config across. Defaults to 1
        # (no sharding). Slow simulators / configs benefit from a higher value
        # — the test universe is split into N round-robin chunks by
        # shard_extensions.py and each shard runs as its own matrix entry.
        shards = int(sim_config.get("shards", 1))
        if shards < 1:
            raise ValueError(f"{sim_ci_yaml}: 'shards' must be >= 1, got {shards}")

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

            shard_lists = _shard_assignments(shards, exclude_extensions)

            for shard_index in range(shards):
                # When not sharded, keep the historical entry shape so the job
                # name in the GitHub UI stays as `<sim> (<config>)`.
                shard_suffix = "" if shards == 1 else f"-shard{shard_index + 1}of{shards}"
                entries.append(
                    {
                        "simulator": sim_name,
                        "config": config_name,
                        "config_file": config_file,
                        "run_cmd": run_cmd,
                        "exclude_extensions": exclude_extensions,
                        "install_script": install_script,
                        "apt_packages": apt_packages,
                        "setup_script": setup_script,
                        "cache_key": cache_key,
                        "shard_index": shard_index,
                        "shard_total": shards,
                        "shard_suffix": shard_suffix,
                        "extensions": ",".join(shard_lists[shard_index]),
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
