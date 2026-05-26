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
config is fanned out into N shards; the shard count comes from the
simulator's ``shards`` default, optionally overridden per-config via the
``config_shards`` map (e.g. shard the ``gc`` variants of cvw heavily but
leave ``imc`` variants un-sharded). The EXTENSIONS list for each shard is
computed here via weighted Longest-Processing-Time bin-packing over the
testsuites that the config actually implements. Suite weights are the
summed byte size of the tracked ``.S`` files under each suite, which is a
much better proxy for runtime than a raw file count.

Usage:
    .github/scripts/ci_config.py    # JSON matrix for GitHub Actions
"""

from __future__ import annotations

import hashlib
import heapq
import json
import subprocess
import sys
from collections.abc import Mapping
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


@cache
def _priv_required_extensions() -> dict[str, frozenset[str]]:
    """Return a mapping of priv testsuite name → required UDB extensions."""
    sys.path.insert(0, str(REPO_ROOT / "generators" / "testgen" / "src"))
    from testgen.priv import (  # type: ignore[import-not-found]
        get_priv_test_extensions,
        get_priv_test_required_extensions,
    )

    return {suite: frozenset(get_priv_test_required_extensions(suite) or []) for suite in get_priv_test_extensions()}


@cache
def _implemented_extensions(udb_config_path: Path) -> frozenset[str]:
    """Return the set of extension names declared in a UDB ``fully configured`` yaml.

    The ACT configs we shard are all ``type: fully configured``, so the
    ``implemented_extensions`` list is the authoritative set of extensions
    that a config implements. We deliberately do not invoke ``udb`` here —
    the discover-configs job is intentionally lightweight (no Ruby), and
    reading the yaml directly is plenty for the shard-grouping heuristic.
    """
    yaml = YAML(typ="safe", pure=True)
    with udb_config_path.open() as f:
        data = yaml.load(f) or {}
    names: set[str] = set()
    for ext in data.get("implemented_extensions") or []:
        if isinstance(ext, dict) and "name" in ext:
            names.add(str(ext["name"]))
        elif isinstance(ext, (list, tuple)) and ext:
            # Spec also allows [name, version] form.
            names.add(str(ext[0]))
        elif isinstance(ext, str):
            names.add(ext)
    return frozenset(names)


def _select_suites_for_config(udb_config_path: Path) -> tuple[str, ...]:
    """Return the sorted suites that a config actually implements.

    Unpriv suites are keyed by extension name, so they're included when the
    extension appears in the UDB config. Priv suites can require several
    extensions at once (e.g. ``InterruptsS`` needs ``Sm``, ``S``, ``I``,
    ``Zicsr``); they're included only when *all* required extensions are
    implemented.
    """
    implemented = _implemented_extensions(udb_config_path)
    priv_required = _priv_required_extensions()
    selected: list[str] = []
    for suite in _list_testsuites():
        if suite in priv_required:
            if priv_required[suite].issubset(implemented):
                selected.append(suite)
        elif suite in implemented:
            selected.append(suite)
    return tuple(sorted(selected))


def _suite_weights(suites: tuple[str, ...]) -> dict[str, int]:
    """Estimate per-suite cost by summing bytes of tracked .S files under tests/<*>/<suite>/.

    File size is a much better runtime proxy than raw file counts because a
    single large test (e.g. a vector or interrupt suite) can dwarf many
    small ones. ``git ls-files`` keeps this deterministic on any clean
    checkout and avoids depending on a prior test-generation step in CI.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "tests"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return dict.fromkeys(suites, _DEFAULT_SUITE_WEIGHT)

    suite_set = set(suites)
    sizes: dict[str, int] = dict.fromkeys(suites, 0)
    for rel_path in out.split("\0"):
        if not rel_path.endswith(".S"):
            continue
        # Layout is tests/<bucket>/<suite>/<file>.S where <bucket> is one of
        # rv32i, rv32e, rv64i, rv64e, priv. The suite name is the
        # second-to-last path component.
        parts = rel_path.split("/")
        if len(parts) < 3:
            continue
        suite = parts[-2]
        if suite not in suite_set:
            continue
        try:
            sizes[suite] += (REPO_ROOT / rel_path).stat().st_size
        except OSError:
            continue

    return {suite: sizes[suite] or _DEFAULT_SUITE_WEIGHT for suite in suites}


@cache
def _shard_assignments(suites: tuple[str, ...], shard_total: int, exclude: str = "") -> tuple[tuple[str, ...], ...]:
    """Return the sorted suite tuple for every shard using LPT bin-packing.

    ``suites`` is the set of testsuites that the *config* implements (so
    e.g. an integer-only config doesn't get F/D/V suites scheduled on its
    shards). They're sorted by descending weight (ties broken by suite name
    for determinism) and each is placed on the currently-lightest shard via
    a min-heap. Excluded suites are dropped from each shard's final list.
    The result is cached because different configs that share the same
    ``(suites, shard_total, exclude)`` tuple get the same answer.
    """
    if shard_total < 1:
        raise ValueError(f"shard_total must be >= 1, got {shard_total}")

    weights = _suite_weights(suites)
    ordered = sorted(suites, key=lambda s: (-weights[s], s))

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


def _resolve_udb_config(test_config_path: Path) -> Path:
    """Return the absolute path to the UDB config referenced by ``test_config.yaml``."""
    yaml = YAML(typ="safe", pure=True)
    with test_config_path.open() as f:
        test_cfg = yaml.load(f) or {}
    udb_config = test_cfg.get("udb_config")
    if not udb_config:
        raise ValueError(f"{test_config_path}: missing required 'udb_config' field")
    udb_path = Path(udb_config)
    if not udb_path.is_absolute():
        udb_path = test_config_path.parent / udb_path
    return udb_path.resolve()


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
            raise TypeError(f"{sim_ci_yaml}: 'config_shards' must be a mapping of config name to shard count")

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

            shards = int(config_shards_override.get(config_name, default_shards))
            if shards < 1:
                raise ValueError(f"{sim_ci_yaml}: 'config_shards[{config_name}]' must be >= 1, got {shards}")

            udb_config_path = _resolve_udb_config(config_file)
            selected_suites = _select_suites_for_config(udb_config_path)
            shard_lists = _shard_assignments(selected_suites, shards, exclude_extensions)

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

    matrix = {"include": entries}
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
