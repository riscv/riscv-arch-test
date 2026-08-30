#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydantic>=2.12.5",
#     "rich>=14.3.4",
#     "ruamel-yaml>=0.18.16",
# ]
# ///
"""Discover CI configurations from config directory and output JSON matrix for GitHub Actions.

Reads config/<simulator>/ci.yaml for simulator-level settings and
config/<simulator>/<config>/run_cmd.txt for per-config run commands. Each
config is fanned out into N shards; the shard count comes from the
simulator's ``shards`` default, optionally overridden per-config via the
``config_shards`` map (e.g. shard the ``gc`` variants of cvw heavily but
leave ``imc`` variants un-sharded). The EXTENSIONS list for each shard is
computed here via weighted Longest-Processing-Time bin-packing over the
testsuites that the config actually implements. Suite weights are the
summed byte size of the ``.S`` files under each suite, which is a much
better proxy for runtime than a raw file count. Run ``make tests`` first
so generated (not checked-in) tests exist and are weighted correctly.

Usage:
    .github/scripts/ci_config.py    # JSON matrix for GitHub Actions
"""

import hashlib
import heapq
import json
import os
import sys
from collections.abc import Mapping
from functools import cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "framework" / "src"))

from act.parse_test_constraints import TestMetadata, generate_test_dict
from act.select_tests import prepare_configs_and_select_tests
from ruamel.yaml import YAML

_DEFAULT_SUITE_WEIGHT = 1  # fallback when a selected test file is missing on disk (run `make tests` first)


@cache
def _full_test_dict(exclude: str) -> dict[str, TestMetadata]:
    """Return the candidate test dict, cached per exclusion list."""
    return generate_test_dict(REPO_ROOT / "tests", "all", exclude)


@cache
def _selected_suite_weights(config_file: Path, exclude: str, workdir: Path) -> tuple[tuple[str, int], ...]:
    """Return selected suite weights for a config using ACT's selection path.

    Uses the same selection pipeline as the act CLI (prepare_configs_and_select_tests).
    Tool validation is skipped because discovery runs before the compiler
    and simulators are installed.

    The cache key includes ``exclude`` because ACT applies exclusions before
    test selection; the same config can legitimately produce different
    suite weights when simulator-level exclusions differ. The selected test
    set is small enough that per-file ``stat`` calls are cheap, and this
    keeps the weighting tied exactly to ACT's selected tests.
    """
    ((_, _, selected_tests),) = prepare_configs_and_select_tests(
        [config_file], _full_test_dict(exclude), workdir, validate_tools=False
    )
    weights: dict[str, int] = {}
    for test_name in selected_tests:
        test_parts = Path(test_name).parts
        if len(test_parts) < 3:
            raise ValueError(f"Selected test path must have layout <bucket>/<suite>/<file>.S, got {test_name}")
        suite = test_parts[-2]
        test_path = REPO_ROOT / "tests" / test_name
        try:
            weight = test_path.stat().st_size
        except FileNotFoundError:
            print(f"Warning: selected test {test_name} not on disk; run 'make tests' first", file=sys.stderr)
            weight = _DEFAULT_SUITE_WEIGHT
        weights[suite] = weights.get(suite, 0) + weight

    return tuple(sorted((suite, weight or _DEFAULT_SUITE_WEIGHT) for suite, weight in weights.items()))


@cache
def _shard_assignments(suite_weights: tuple[tuple[str, int], ...], shard_total: int) -> tuple[tuple[str, ...], ...]:
    """Return the sorted suite tuple for every shard using LPT bin-packing.

    ``suite_weights`` is derived from ACT-selected tests for the config, so
    e.g. an integer-only config doesn't get F/D/V suites scheduled on its
    shards. Suites are sorted by descending selected-test byte size (ties
    broken by suite name for determinism) and each is placed on the
    currently-lightest shard via a min-heap.
    """
    if shard_total < 1:
        raise ValueError(f"shard_total must be >= 1, got {shard_total}")

    weights = dict(suite_weights)
    ordered = sorted(weights, key=lambda s: (-weights[s], s))

    heap: list[tuple[int, int, list[str]]] = [(0, i, []) for i in range(shard_total)]
    heapq.heapify(heap)
    for suite in ordered:
        load, idx, bucket = heapq.heappop(heap)
        bucket.append(suite)
        heapq.heappush(heap, (load + weights[suite], idx, bucket))
    buckets = sorted(heap, key=lambda entry: entry[1])
    return tuple(tuple(sorted(bucket)) for _, _, bucket in buckets)


def load_simulator_ci_yaml(ci_yaml_path: Path) -> dict:
    """Load a simulator-level ci.yaml file."""
    yaml = YAML()
    with ci_yaml_path.open() as f:
        data = yaml.load(f)
    return data if data else {}


def file_hash(path: Path) -> str:
    """Return the first 12 hex chars of the SHA-256 hash of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _warm_udb_outputs(config_dir: Path, workdir: Path) -> None:
    """Generate UDB outputs for every CI-enabled config in one parallel pass.

    UDB resolution dominates discovery time and is independent of the
    per-simulator exclusion lists, so prepare all configs up front with full
    parallelism. The per-config selection calls in ``_selected_suite_weights``
    then skip the UDB work via the build cache. The empty test dict makes the
    selection part of this warm-up call a no-op.
    """
    config_files: list[Path] = []
    for sim_ci_yaml in sorted(config_dir.rglob("*/ci.yaml")):
        sim_config = load_simulator_ci_yaml(sim_ci_yaml)
        if not sim_config.get("ci_enabled", True):
            continue
        exclude_configs: set[str] = set(sim_config.get("exclude_configs", []))
        for run_cmd_file in sorted(sim_ci_yaml.parent.rglob("*/run_cmd.txt")):
            if run_cmd_file.parent.name not in exclude_configs:
                config_files.append(run_cmd_file.parent / "test_config.yaml")

    if config_files:
        prepare_configs_and_select_tests(config_files, {}, workdir, jobs=os.cpu_count() or 1, validate_tools=False)


def discover_configs(config_dir: Path, workdir: Path | None = None) -> list[dict]:
    """Discover all CI-enabled configs and return matrix entries."""
    entries: list[dict] = []
    if workdir is None:
        workdir = REPO_ROOT / "work" / "ci-config"

    _warm_udb_outputs(config_dir, workdir)

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
        # (no sharding). Slow simulators / configs benefit from a higher
        # value — the testsuites are split into N bin-packed shards and
        # each runs as its own matrix entry. ``config_shards`` overrides
        # the default per-config so that, e.g., only the heavy ``gc``
        # configs of cvw are sharded and the lighter ``imc`` config still
        # runs as a single job.
        default_shards = int(sim_config.get("shards", 1))
        if default_shards < 1:
            raise ValueError(f"{sim_ci_yaml}: 'shards' must be >= 1, got {default_shards}")
        config_shards_override = sim_config.get("config_shards") or {}
        if not isinstance(config_shards_override, Mapping):
            raise TypeError(
                f"{sim_ci_yaml}: 'config_shards' must be a mapping of config name to shard count, "
                f"got {type(config_shards_override).__name__}"
            )
        config_shards: dict[str, int] = {}
        for config_name, shard_count in config_shards_override.items():
            try:
                config_shards[str(config_name)] = int(shard_count)
            except (TypeError, ValueError) as e:
                raise TypeError(
                    f"{sim_ci_yaml}: 'config_shards[{config_name}]' must be a positive integer, got {shard_count!r}"
                ) from e
            if config_shards[str(config_name)] < 1:
                raise ValueError(
                    f"{sim_ci_yaml}: 'config_shards[{config_name}]' must be >= 1, got {config_shards[str(config_name)]}"
                )

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
            config_file = run_cmd_file.parent / "test_config.yaml"

            shards = config_shards.get(config_name, default_shards)
            if shards < 1:
                raise ValueError(f"{sim_ci_yaml}: 'config_shards[{config_name}]' must be >= 1, got {shards}")

            suite_weights = _selected_suite_weights(config_file, exclude_extensions, workdir)
            shard_lists = _shard_assignments(suite_weights, shards)

            for shard_index in range(shards):
                # When not sharded, keep the historical entry shape so the job
                # name in the GitHub UI stays as `<sim> (<config>)`.
                shard_suffix = "" if shards == 1 else f"-shard{shard_index + 1}of{shards}"
                entries.append(
                    {
                        "simulator": sim_name,
                        "config": config_name,
                        "config_file": str(config_file),
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
    matrix = json.dumps({"include": entries}, separators=(",", ":"))

    # In GitHub Actions, write the matrix straight to GITHUB_OUTPUT so stdout
    # stays free for logs (UDB progress, bundle install, etc.). Locally,
    # print it (after any progress output).
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a") as f:
            f.write(f"matrix={matrix}\n")
    else:
        print(matrix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
