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

# Values mirrored from the dut_environment block into rvmodel_macros.svh.
_MIRRORED_DEFINES: list[str] = [
    "RVMODEL_ACCESS_FAULT_ADDRESS",
]


def generate_rvmodel_svh(udb_config_file: Path, output_dir: Path) -> None:
    """Generate rvmodel_macros.svh in output_dir from the config's dut_environment block.

    Emits a `define for each macro in _MIRRORED_DEFINES that the block sets.
    """
    block = read_dut_environment(udb_config_file)
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
        value = block.get(name)
        if isinstance(value, int) and not isinstance(value, bool):
            lines.append(f"`define {name} 64'h{value:x}")
    lines += ["", f"`endif // {guard}", ""]

    output_svh.write_text("\n".join(lines))
