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
_ACCESS_FAULT_ADDRESS = "RVMODEL_ACCESS_FAULT_ADDRESS"
_ACCESS_FAULT_VARIANTS: list[str] = [
    f"{_ACCESS_FAULT_ADDRESS}_{kind}" for kind in ("LOAD", "STORE", "FETCH", "AMO", "LRSC")
]

_MIRRORED_DEFINES: list[str] = [
    _ACCESS_FAULT_ADDRESS,
    *_ACCESS_FAULT_VARIANTS,
]

# Defines mirrored as plain decimal numbers, so SystemVerilog can paste them into a name.
_MIRRORED_INDEX_DEFINES: list[str] = [
    "RVMODEL_HPM_COUNTER",
]

# Defines emitted without a value, so coverpoints can test them with `ifdef. Each is emitted when
# rvmodel_macros.h defines any of its listed macros, with any value or parameters.
_MIRRORED_FLAG_DEFINES: dict[str, list[str]] = {
    # The DUT raises SEI through a supervisor external interrupt controller, not only through mip.SEIP
    "RVMODEL_SEXT_INT_EXTERNAL": ["RVMODEL_SET_SEXT_INT", "RVMODEL_SET_SEXT_INT_M"],
}

_DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)\s+(0[xX][0-9a-fA-F]+|\d+)\b")
_DEFINE_NAME_RE = re.compile(r"^\s*#define\s+(\w+)\b")


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


def _scan_h_define_names(h_path: Path) -> set[str]:
    """Return the name of every macro that h_path defines, with the same line rules as _scan_h_defines."""
    return {match.group(1) for line in h_path.read_text().splitlines() if (match := _DEFINE_NAME_RE.match(line))}


def generate_rvmodel_svh(dut_include_dir: Path, output_dir: Path) -> None:
    """Generate rvmodel_macros.svh in output_dir derived from rvmodel_macros.h."""
    input_h = dut_include_dir / "rvmodel_macros.h"
    output_svh = output_dir / "rvmodel_macros.svh"
    if not input_h.exists():
        raise FileNotFoundError(f"rvmodel_macros.h not found at {input_h}")

    defines = _scan_h_defines(input_h, _MIRRORED_DEFINES + _MIRRORED_INDEX_DEFINES)
    # Same defaults as tests/env/check_defines.h: each undefined variant takes the general value.
    if _ACCESS_FAULT_ADDRESS in defines:
        for name in _ACCESS_FAULT_VARIANTS:
            defines.setdefault(name, defines[_ACCESS_FAULT_ADDRESS])

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
    for name in _MIRRORED_INDEX_DEFINES:
        if name in defines:
            lines.append(f"`define {name} {int(defines[name], 0)}")
    defined_names = _scan_h_define_names(input_h)
    for name, sources in _MIRRORED_FLAG_DEFINES.items():
        if defined_names.intersection(sources):
            lines.append(f"`define {name}")
    lines += ["", f"`endif // {guard}", ""]

    output_svh.write_text("\n".join(lines))
