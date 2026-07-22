##################################
# sail_config.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Generate and validate the Sail reference-model config from the UDB config.
##################################

"""Derive ``sail.json`` from the UDB config instead of hand-maintaining it.

Motivation: test *selection* reads UDB (``extensions.txt``), while the reference
model reads ``sail.json``. When those two disagree, tests get selected for an
extension the reference model is not modelling, and the golden signature is
produced by the wrong machine. Nothing catches that today -- the run simply
produces a confidently wrong answer.

Approach (template + overlay, chosen over full generation because UDB does not
express every Sail knob -- PMP addressing modes being the known example):

1. Start from a maintained baseline ``sail_template.json``.
2. Set ``base.xlen`` from the config's MXLEN param.
3. Set every ``extensions.<Name>.supported`` from UDB's implemented-extension
   list. This is the bulk of the file and the part that silently drifts.
4. Apply the handful of genuinely DUT-specific scalars from the config's
   ``sail_overrides`` block (misaligned behaviour, archid, vlen, ...).

Names match between UDB and Sail for 90 of Sail's 99 extension keys; the
remainder are listed in ``_EXTENSION_ALIASES`` / ``_NOT_IN_UDB``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

# Sail extension keys that UDB spells differently.
_EXTENSION_ALIASES: dict[str, str] = {
    "Stateen": "Smstateen",
}

# Sail extension keys UDB does not know about at all. Left at whatever the
# template says rather than being force-disabled, because "UDB has no opinion"
# is not the same as "the DUT does not implement it". Revisit as UDB catches up.
_NOT_IN_UDB: frozenset[str] = frozenset({"Zibi", "Zvabd"})

# Sail keys that are XLEN-determined rather than UDB-determined.
_XLEN_ONLY: dict[str, int] = {"Sv32": 32, "Zcf": 32}


def _strip_jsonc(text: str) -> str:
    """Drop whole-line // comments so the JSONC config parses as JSON."""
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def load_sail_json(path: Path) -> dict[str, Any]:
    """Parse a sail.json (JSONC) file."""
    return json.loads(_strip_jsonc(path.read_text()))


def read_sail_overrides(udb_config_file: Path) -> dict[str, Any]:
    """Return the config's ``sail_overrides`` block as {dotted.path: value}."""
    yaml = YAML(typ="safe", pure=True)
    config = yaml.load(udb_config_file.read_text()) or {}
    block = config.get("sail_overrides") or {}
    if not isinstance(block, dict):
        raise TypeError(f"sail_overrides must be a mapping in {udb_config_file}")
    return block


def _set_path(tree: dict[str, Any], dotted: str, value: Any) -> None:  # noqa: ANN401
    """Set tree["a"]["b"] = value for "a.b", requiring the path to already exist.

    Requiring it to exist means a typo'd override is an error rather than a new
    field Sail will ignore.
    """
    parts = dotted.split(".")
    node: Any = tree
    for p in parts[:-1]:
        if not isinstance(node, dict) or p not in node:
            raise KeyError(f"sail_overrides path '{dotted}' does not exist in the template")
        node = node[p]
    if not isinstance(node, dict) or parts[-1] not in node:
        raise KeyError(f"sail_overrides path '{dotted}' does not exist in the template")
    node[parts[-1]] = value


def check_extension_agreement(sail_cfg: dict[str, Any], implemented: set[str]) -> list[str]:
    """Report where sail.json's extension flags disagree with UDB.

    Returns human-readable discrepancy lines; empty means consistent. Extensions
    Sail does not model at all are not reported -- that is a Sail capability
    limit, not a config error.
    """
    problems: list[str] = []
    for name, body in sorted(sail_cfg.get("extensions", {}).items()):
        if not isinstance(body, dict) or "supported" not in body:
            continue
        if name in _NOT_IN_UDB or name in _XLEN_ONLY:
            continue
        udb_name = _EXTENSION_ALIASES.get(name, name)
        supported = bool(body["supported"])
        in_udb = udb_name in implemented
        if in_udb and not supported:
            problems.append(
                f"{name}: UDB implements it but sail.json disables it -- tests requiring "
                f"{name} would be selected, then run against a model that lacks it"
            )
        elif supported and not in_udb:
            problems.append(f"{name}: sail.json enables it but UDB does not implement it")
    return problems


def generate_sail_config(
    template_file: Path,
    udb_config_file: Path,
    extensions_file: Path,
    output_file: Path,
    xlen: int,
) -> None:
    """Write sail.json for one config: template + UDB extensions + overrides."""
    cfg = load_sail_json(template_file)
    implemented = set(extensions_file.read_text().split())

    cfg.setdefault("base", {})["xlen"] = xlen

    for name, body in cfg.get("extensions", {}).items():
        if not isinstance(body, dict) or "supported" not in body:
            continue
        if name in _NOT_IN_UDB:
            continue
        if name in _XLEN_ONLY:
            body["supported"] = xlen == _XLEN_ONLY[name]
            continue
        body["supported"] = _EXTENSION_ALIASES.get(name, name) in implemented

    for dotted, value in read_sail_overrides(udb_config_file).items():
        _set_path(cfg, dotted, value)

    output_file.write_text(
        "// Auto-generated from the UDB config by act (do not edit)\n"
        "// Edit the UDB config's sail_overrides block instead.\n" + json.dumps(cfg, indent=2) + "\n"
    )
