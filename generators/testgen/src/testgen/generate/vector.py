##################################
# generate/vector.py
#
# Vector test generation orchestration.
# Bridges the legacy vector-testgen scripts (which still live under
# ``generators/testgen/scripts/``) into the unified ``testgen`` CLI so a
# single invocation generates both scalar and vector tests with shared
# argument parsing, parallel-job dispatch and progress reporting.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Vector test generation entry points used by ``testgen.cli``.

The actual generators are large standalone scripts that pre-date this
package:

* ``generators/testgen/scripts/vector-testgen-unpriv.py``
* ``generators/testgen/scripts/vector-testgen-priv.py``
* ``generators/testgen/scripts/vector_testgen_common.py`` (+ ``priv/``,
  ``custom/`` coverpoint generators)

They depend on top-level imports like ``import vector_testgen_common as
common`` / ``import priv`` / ``from coverpoint_registry import ...`` and
on a ``writeLine`` symbol exported by the driver script, so they cannot
be moved into the package wholesale without changing their import paths.
Instead this module adds the scripts directory to ``sys.path`` once and
exposes thin wrappers that the unified CLI dispatches in place of the
old ``make vector-testgen`` target.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"


def _ensure_scripts_on_path() -> None:
    scripts_dir = str(_SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


def _load_script_module(module_name: str, filename: str):
    """Load a hyphenated script as a Python module via importlib.

    The vector generator scripts use hyphenated filenames (eg.
    ``vector-testgen-unpriv.py``) which can't be ``import``-ed directly.
    """
    _ensure_scripts_on_path()
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def list_unpriv_vector_extensions() -> list[str]:
    """Return the per-SEW vector extensions the unpriv generator can produce.

    Mirrors ``readTestplans()`` expansion (Vx/Vls/Vf split by SEW, Zvbb/Zvkb
    similar). Returned in deterministic order so the CLI extension picker is
    stable.
    """
    _ensure_scripts_on_path()
    common = importlib.import_module("vector_testgen_common")
    return sorted(common.readTestplans().keys())


def list_priv_vector_extensions() -> list[str]:
    """Return the priv vector extensions (ExceptionsV*, MisalignedV, SsstrictV)."""
    _ensure_scripts_on_path()
    common = importlib.import_module("vector_testgen_common")
    return sorted(common.readTestplans(priv=True).keys())


def generate_unpriv_vector_extension(xlen: int, extension: str) -> str:
    """Generate every test file for a single (xlen, extension) pair.

    Thin wrapper around ``vector-testgen-unpriv.generate_extension`` /
    ``_setup_worker``; the heavy lifting (seeding, file IO, sigupd buffer)
    still lives in the legacy script. Suitable for dispatch via
    ``ProcessPoolExecutor``.
    """
    module = _load_script_module("vector_testgen_unpriv", "vector-testgen-unpriv.py")
    module._setup_worker()  # noqa: SLF001 — legacy script API
    return module.generate_extension(xlen, extension)


def generate_all_priv_vector_tests() -> None:
    """Run the priv vector generator end-to-end.

    The priv generator (``vector-testgen-priv.main``) iterates xlens and
    extensions internally and writes one or more ``.S`` files per
    (extension, xlen) chunk. Returns nothing; callers should treat it as
    a single coarse-grained task.
    """
    module = _load_script_module("vector_testgen_priv", "vector-testgen-priv.py")
    module.main()


__all__ = [
    "generate_all_priv_vector_tests",
    "generate_unpriv_vector_extension",
    "list_priv_vector_extensions",
    "list_unpriv_vector_extensions",
]
