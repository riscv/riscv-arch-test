##################################
# dut_macros.py
#
# Jordan Carlin jcarlin@hmc.edu May 2026
# SPDX-License-Identifier: Apache-2.0
#
# Generate the SystemVerilog rvmodel_macros.svh from the config's
# dut_environment block so values are not duplicated across both files.
##################################

"""Derive a minimal rvmodel_macros.svh from the dut_environment block."""

from pathlib import Path

from act.dut_environment import read_dut_environment

_ACCESS_FAULT_ADDRESS = "RVMODEL_ACCESS_FAULT_ADDRESS"
_ACCESS_FAULT_VARIANTS: list[str] = [
    f"{_ACCESS_FAULT_ADDRESS}_{kind}" for kind in ("LOAD", "STORE", "FETCH", "AMO", "LRSC")
]

# Values mirrored from the dut_environment block into rvmodel_macros.svh, as 64-bit hex.
_MIRRORED_DEFINES: list[str] = [
    _ACCESS_FAULT_ADDRESS,
    *_ACCESS_FAULT_VARIANTS,
]

# Values mirrored as plain decimal numbers, so SystemVerilog can paste them into a name.
_MIRRORED_INDEX_DEFINES: list[str] = [
    "RVMODEL_HPM_COUNTER",
]


def generate_rvmodel_svh(udb_config_file: Path, output_dir: Path) -> None:
    """Generate rvmodel_macros.svh in output_dir from the config's dut_environment block.

    Emits a `define for each macro in _MIRRORED_DEFINES and _MIRRORED_INDEX_DEFINES that
    the block sets.
    """
    block = read_dut_environment(udb_config_file)
    values = {name: value for name, value in block.items() if isinstance(value, int) and not isinstance(value, bool)}
    # Same defaults as tests/env/check_defines.h: each undefined variant takes the general value.
    if _ACCESS_FAULT_ADDRESS in values:
        for name in _ACCESS_FAULT_VARIANTS:
            values.setdefault(name, values[_ACCESS_FAULT_ADDRESS])

    output_svh = output_dir / "rvmodel_macros.svh"
    guard = f"_RVMODEL_MACROS_SVH_{output_dir.name.upper().replace('-', '_')}_"
    lines = [
        "// Auto-generated from the UDB config's dut_environment block by act (do not edit)",
        "// SPDX-License-Identifier: Apache-2.0",
        "",
        f"`ifndef {guard}",
        f"`define {guard}",
        "",
    ]
    for name in _MIRRORED_DEFINES:
        if name in values:
            lines.append(f"`define {name} 64'h{values[name]:x}")
    for name in _MIRRORED_INDEX_DEFINES:
        if name in values:
            lines.append(f"`define {name} {values[name]}")
    lines += ["", f"`endif // {guard}", ""]

    output_svh.write_text("\n".join(lines))
