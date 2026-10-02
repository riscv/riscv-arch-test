##################################
# build_cache.py
#
# Jordan Carlin jcarlin@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
#
# Content-hash based staleness for the build DAG, robust against the mtime
# changes that occur when a work dir is restored from a CI cache.
##################################

"""Recipe-hash staleness tracking and the per-config manifest it persists to.

Each task gets a "recipe hash": a Merkle hash over the content of its real source
inputs plus its action, folded with the recipe hashes of its dependencies. Because
it never reads intermediate output files, the recipe hash stays valid after build/
dirs are deleted (CLEAN_INTERMEDIATES) and is unaffected by mtime changes.
"""

from __future__ import annotations

import contextlib
import functools
import hashlib
import json
from pathlib import Path

from act.build_types import BuildAction, BuildTask, PythonAction, SubprocessAction, SymlinkAction

_RECIPE_CACHE_NAME = ".act_build_cache.json"  # one manifest per config dir
_NUL = b"\x00"  # field delimiter so concatenated fields cannot ambiguously merge
_DIGEST_HEX = 32  # truncate to 16 bytes; collisions irrelevant for staleness


def _new_hash() -> hashlib._Hash:
    """SHA-256 digest. Hardware-accelerated (SHA-NI), faster here than blake2b."""
    return hashlib.sha256()


def _digest(h: hashlib._Hash) -> str:
    """Truncated hex digest; 16 bytes keeps manifests compact, ample for staleness."""
    return h.hexdigest()[:_DIGEST_HEX]


# ---------------------------------------------------------------------------
# Recipe hashing
# ---------------------------------------------------------------------------


@functools.cache
def _content_hash(path: Path) -> str:
    """Digest of a file's content. Cleared per build via _compute_recipe_hashes."""
    digest = _new_hash()
    digest.update(path.read_bytes())
    return _digest(digest)


def _action_repr(action: BuildAction) -> str:
    """Stable string identity of an action for hashing."""
    if isinstance(action, SubprocessAction):
        return "subprocess\x00" + "\x00".join(action.cmd) + "\x00cwd=" + str(action.cwd)
    if isinstance(action, PythonAction):
        fn = action.fn
        qual = getattr(fn, "__qualname__", repr(fn))
        mod = getattr(fn, "__module__", "")
        return "python\x00" + f"{mod}.{qual}" + "\x00" + "\x00".join(str(a) for a in action.args)
    if isinstance(action, SymlinkAction):
        return "symlink\x00" + str(action.src) + "\x00" + str(action.dst)
    raise TypeError(f"Unknown build action type: {type(action)}")


def _compute_recipe_hashes(task_map: dict[Path, BuildTask]) -> dict[Path, str]:
    """Recipe hash per task: Merkle over source-input content, action, and dep recipes."""
    _content_hash.cache_clear()

    @functools.cache
    def recipe_for(key: Path) -> str:
        task = task_map[key]
        h = _new_hash()
        h.update(_action_repr(task.action).encode())
        for inp in sorted(task.extra_inputs):
            h.update(_NUL + b"i" + str(inp).encode() + b"=" + _content_hash(inp).encode())
        for dep in sorted(task.deps):
            if dep not in task_map:
                raise KeyError(f"Task {key} depends on {dep}, which is not produced by any task in the build plan")
            h.update(_NUL + b"d" + recipe_for(dep).encode())
        return _digest(h)

    return {key: recipe_for(key) for key in task_map}


# ---------------------------------------------------------------------------
# Per-config manifest persistence
# ---------------------------------------------------------------------------


def _load_manifest(path: Path) -> dict[str, str]:
    """Load a per-config recipe manifest; {} on missing or unreadable."""
    if not path.exists():
        return {}
    with contextlib.suppress(OSError, ValueError, json.JSONDecodeError):
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return data
    return {}


def _save_manifest(path: Path, entries: dict[str, str]) -> None:
    """Atomically write a per-config recipe manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(entries))
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Build cache: decides what runs, records successes, persists manifests
# ---------------------------------------------------------------------------


class BuildCache:
    """Per-run staleness cache for one build() invocation.

    Holds each task's recipe hash and the per-config manifests it loads lazily; decides
    which tasks must run, records successful builds, and writes the manifests back. The
    manifest for a config lives at <config_dir>/.act_build_cache.json and survives
    CLEAN_INTERMEDIATES (which only removes build/ subdirs).
    """

    def __init__(self, cache_root: Path, task_map: dict[Path, BuildTask], *, clean_intermediates: bool = False) -> None:
        # cache_root's immediate children are config dirs; every output is below one.
        self._cache_root = cache_root
        self._task_map = task_map
        self._clean_intermediates = clean_intermediates
        self._recipe_hashes = _compute_recipe_hashes(task_map)
        self._manifests: dict[Path, dict[str, str]] = {}
        self._updated_configs: set[Path] = set()

    def _config_dir(self, key: Path) -> Path:
        return self._cache_root / key.relative_to(self._cache_root).parts[0]

    def _manifest(self, config_dir: Path) -> dict[str, str]:
        manifest = self._manifests.get(config_dir)
        if manifest is None:
            manifest = _load_manifest(config_dir / _RECIPE_CACHE_NAME)
            self._manifests[config_dir] = manifest
        return manifest

    def _is_satisfied(self, key: Path) -> bool:
        """True when all outputs exist and the stored recipe hash matches."""
        task = self._task_map[key]
        if not all(out.exists() for out in task.outputs):
            return False
        config_dir = self._config_dir(key)
        return self._manifest(config_dir).get(str(key.relative_to(config_dir))) == self._recipe_hashes[key]

    def _demand_roots(self) -> set[Path]:
        """Tasks that should be checked directly for freshness."""
        dependency_keys = {dep for task in self._task_map.values() for dep in task.deps}
        return {
            key
            for key, task in self._task_map.items()
            if task.is_deliverable(clean_intermediates=self._clean_intermediates) or key not in dependency_keys
        }

    def needed_tasks(self) -> set[Path]:
        """Tasks that must run: unsatisfied deliverables/sinks plus their unsatisfied deps.

        Demand roots are deliverables and sinks (no dependents); each pulls in its unsatisfied
        dependencies transitively, stopping at satisfied ones. A task counts as disposable (not a
        deliverable) only when it is intermediate and build/ will be cleaned, so a satisfied
        deliverable is skipped even when its intermediates are gone. Without cleaning, intermediates
        are deliverables too and are rebuilt when missing.
        """
        satisfied = {key: self._is_satisfied(key) for key in self._task_map}
        needed: set[Path] = set()

        def add_unsatisfied_deps(key: Path) -> None:
            if key in needed or satisfied[key]:
                return
            needed.add(key)
            for dep in self._task_map[key].deps:
                add_unsatisfied_deps(dep)

        for root_key in self._demand_roots():
            add_unsatisfied_deps(root_key)

        return needed

    def record_success(self, key: Path) -> None:
        """Store the recipe hash of a task that just built successfully."""
        config_dir = self._config_dir(key)
        self._manifest(config_dir)[str(key.relative_to(config_dir))] = self._recipe_hashes[key]
        self._updated_configs.add(config_dir)

    def save(self) -> None:
        """Persist every config manifest that gained a recorded success."""
        for config_dir in self._updated_configs:
            _save_manifest(config_dir / _RECIPE_CACHE_NAME, self._manifests[config_dir])
        self._updated_configs.clear()
