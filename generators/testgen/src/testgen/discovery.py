##################################
# discovery.py
#
# Shared module auto-discovery for decorator-based registries.
# jcarlin@hmc.edu April 4, 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared module auto-discovery for decorator-based registries."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path


def discover_and_import_modules(package_dir: Path, base_module: str, *, exclude: Path | None = None) -> None:
    """Auto-import all Python modules in a directory to trigger decorator registration.

    Recursively finds all .py files in ``package_dir`` (skipping files whose names
    start with ``_``), converts each to a dotted module path relative to
    ``base_module``, and imports it.

    Args:
        package_dir: Directory to scan for Python modules.
        base_module: Dotted base module prefix (e.g. ``"testgen.coverpoints"``).
        exclude: Optional file path to skip (e.g. the calling registry module itself).
    """
    for module_file in package_dir.rglob("*.py"):
        if module_file.stem.startswith("_"):
            continue
        if exclude is not None and module_file == exclude:
            continue
        relative_path = module_file.relative_to(package_dir)
        module_parts = [*list(relative_path.parts[:-1]), relative_path.stem]
        module_name = base_module + "." + ".".join(module_parts)
        import_module(module_name)
