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

import re
from pathlib import Path

# Defines mirrored from rvmodel_macros.h into rvmodel_macros.svh. Each entry is
# the macro name; only macros with an active (non-commented) #define are emitted.
_MIRRORED_DEFINES: list[str] = [
    "RVMODEL_ACCESS_FAULT_ADDRESS",
]

# Defines mirrored as plain decimal numbers, so SystemVerilog can paste them into a name.
_MIRRORED_INDEX_DEFINES: list[str] = [
    "RVMODEL_HPM_COUNTER",
]

# Defines emitted without a value, only so coverpoints can test them with `ifdef. Each is emitted when any of
# its listed rvmodel_macros.h macros has an active #define, whatever its value or parameters.
_MIRRORED_FLAG_DEFINES: dict[str, list[str]] = {
    # The value may be any expression, such as (CLINT_BASE_ADDRESS + 0x0)
    "RVMODEL_MSIP_ADDRESS": ["RVMODEL_MSIP_ADDRESS"],
}

_DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)(?:\s+(0[xX][0-9a-fA-F]+|\d+)\b)?")


def _scan_h_defines(h_path: Path, names: list[str]) -> dict[str, str | None]:
    """Return the value (as written) for each requested macro found in h_path, or None if the
    value is not an integer literal.

    Only matches lines that begin (after whitespace) with `#define NAME`.
    Lines starting with `//`, `/*`, or any other prefix are ignored, so commented-out
    defines are skipped. If a name is defined more than once, the last wins.
    """
    found: dict[str, str | None] = {}
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
    """Generate rvmodel_macros.svh in output_dir derived from rvmodel_macros.h."""
    input_h = dut_include_dir / "rvmodel_macros.h"
    output_svh = output_dir / "rvmodel_macros.svh"
    if not input_h.exists():
        raise FileNotFoundError(f"rvmodel_macros.h not found at {input_h}")

    flag_sources = [source for sources in _MIRRORED_FLAG_DEFINES.values() for source in sources]
    defines = _scan_h_defines(input_h, _MIRRORED_DEFINES + _MIRRORED_INDEX_DEFINES + flag_sources)

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
        value = defines.get(name)
        if value is not None:
            hex_value = value[2:] if value.lower().startswith("0x") else f"{int(value):x}"
            lines.append(f"`define {name} 64'h{hex_value}")
    for name in _MIRRORED_INDEX_DEFINES:
        value = defines.get(name)
        if value is not None:
            lines.append(f"`define {name} {int(value, 0)}")
    for name, sources in _MIRRORED_FLAG_DEFINES.items():
        if any(source in defines for source in sources):
            lines.append(f"`define {name}")
    lines += ["", f"`endif // {guard}", ""]

    output_svh.write_text("\n".join(lines))
