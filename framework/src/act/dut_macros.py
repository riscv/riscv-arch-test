##################################
# dut_macros.py
#
# Jordan Carlin jcarlin@hmc.edu May 2026
# SPDX-License-Identifier: Apache-2.0
#
# Generate the SystemVerilog rvmodel_macros.svh from the DUT-provided
# rvmodel_macros.h so values are not duplicated across both files.
##################################

"""Derive a minimal rvmodel_macros.svh from rvmodel_macros.h."""

from __future__ import annotations

import re
from pathlib import Path

# Defines mirrored from rvmodel_macros.h into rvmodel_macros.svh. Each entry is
# the macro name; only macros with an active (non-commented) #define are emitted.
_MIRRORED_DEFINES: list[str] = [
    "RVMODEL_ACCESS_FAULT_ADDRESS",
]

_DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)\s+(0[xX][0-9a-fA-F]+|\d+)\b")


def _scan_h_defines(h_path: Path, names: list[str]) -> dict[str, str]:
    """Return the value (as written) for each requested macro found in h_path.

    Only matches lines that begin (after whitespace) with `#define NAME VALUE`.
    Lines starting with `//`, `/*`, or any other prefix are ignored, so commented-out
    defines are skipped. If a name is defined more than once, the last wins.
    """
    found: dict[str, str] = {}
    wanted = set(names)
    for line in h_path.read_text().splitlines():
        match = _DEFINE_RE.match(line)
        if match is None:
            continue
        name, value = match.group(1), match.group(2)
        if name in wanted:
            found[name] = value
    return found


def generate_rvmodel_svh(dut_include_dir: Path, output_dir: Path) -> None:
    """Generate rvmodel_macros.svh in output_dir derived from rvmodel_macros.h.

    Emits a `define for each macro in _MIRRORED_DEFINES that has an active
    `#define` in the input header.
    """
    input_h = dut_include_dir / "rvmodel_macros.h"
    output_svh = output_dir / "rvmodel_macros.svh"
    if not input_h.exists():
        raise FileNotFoundError(f"rvmodel_macros.h not found at {input_h}")

    defines = _scan_h_defines(input_h, _MIRRORED_DEFINES)

    guard = f"_RVMODEL_MACROS_SVH_{dut_include_dir.name.upper().replace('-', '_')}_"
    lines = [
        "// Auto-generated from rvmodel_macros.h by act (do not edit)",
        "// SPDX-License-Identifier: Apache-2.0",
        "",
        f"`ifndef {guard}",
        f"`define {guard}",
        "",
    ]
    for name in _MIRRORED_DEFINES:
        if name in defines:
            value = defines[name]
            hex_value = value[2:] if value.lower().startswith("0x") else f"{int(value):x}"
            lines.append(f"`define {name} 64'h{hex_value}")
    lines += ["", f"`endif // {guard}", ""]

    output_svh.write_text("\n".join(lines))
