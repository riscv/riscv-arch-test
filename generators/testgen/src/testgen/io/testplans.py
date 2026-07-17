##################################
# io/testplans.py
#
# Read testplans for riscv-arch-test test generation.
# jcarlin@hmc.edu 5 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Read testplans for riscv-arch-test test generation."""

import csv
from dataclasses import dataclass
from pathlib import Path


def get_extensions(testplan_dir: Path) -> list[str]:
    """Get the list of extensions from the testplan directory."""
    extensions: list[str] = []
    for testplan in testplan_dir.glob("*.csv"):
        extension = testplan.stem
        if extension.startswith(("V", "Zv")):
            extensions.extend(expand_vector_extension(extension))
        else:
            extensions.append(extension)
    return extensions


def expand_vector_extension(extension: str) -> list[str]:
    """Expands a vector extension by adding SEW suffixes."""

    if not extension.startswith("Vx"):
        # Only Vx is supported for now
        return []

    if extension in ["Vx", "Vls", "Zvbb", "Zvkb"]:
        return [extension + effew for effew in ["8", "16", "32", "64"]]
    elif extension in ["ExceptionsVf", "Vf"]:
        return [extension + effew for effew in ["16", "32", "64"]]
    elif extension == "Zvknhb":
        return [extension + effew for effew in ["32", "64"]]
    else:
        return [extension]


@dataclass
class TestPlanData:
    """Data structure for information on a single instruction parsed from a testplan."""

    instr_name: str
    instr_type: str
    rv32: bool
    rv64: bool
    sews_supported: list[int]
    coverpoints: list[str]


def read_testplan(testplan_path: Path) -> list[TestPlanData]:
    """Read a testplan and return a list of instructions and their associated data (type, coverpoints, etc.)."""
    # Columns that are parsed separately and should not be treated as coverpoints
    non_coverpoint_columns = {"Instruction", "Type", "RV32", "RV64", "EFFEW8", "EFFEW16", "EFFEW32", "EFFEW64"}

    instructions: list[TestPlanData] = []
    with testplan_path.open() as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            instr = row["Instruction"]
            try:
                instr_type = row["Type"]
            except KeyError:
                print(
                    f"Error: 'Type' column missing in testplan {testplan_path}. Make sure you remembered to shrink the CSV."
                )
                raise
            rv32 = row["RV32"].strip().lower() == "x"
            rv64 = row["RV64"].strip().lower() == "x"
            sews = []
            for sew in [8, 16, 32, 64]:
                if f"EFFEW{sew}" in row and row[f"EFFEW{sew}"].strip().lower() == "x":
                    sews.append(sew)
            coverpoints: list[str] = []
            for key, value in row.items():
                if key in non_coverpoint_columns:
                    continue
                if isinstance(value, str) and value != "":
                    if (
                        value != "x"
                    ):  # for special entries, append the entry name (e.g. cp_rd_edges becomes cp_rd_edges_lui)
                        key = key + "_" + value
                    coverpoints.append(key)

            # Some cp_custom coverpoints are
            coverpoints = expand_coverpoints(coverpoints)

            instructions.append(
                TestPlanData(
                    instr_name=instr,
                    instr_type=instr_type,
                    rv32=rv32,
                    rv64=rv64,
                    sews_supported=sews,
                    coverpoints=coverpoints,
                )
            )
    return instructions


def expand_coverpoints(coverpoints: list[str]) -> list[str]:
    coverpoint_expansion_map = {
        "cp_custom_wvv": [
            "cp_custom_vdOverlapTopVs2_vd_vs2_lmul1",
            "cp_custom_vdOverlapTopVs1_vd_vs1_lmul1",
            "cp_custom_vdOverlapTopVs2_vd_vs2_lmul2",
            "cp_custom_vdOverlapTopVs1_vd_vs1_lmul2",
            "cp_custom_vdOverlapTopVs2_vd_vs2_lmul4",
            "cp_custom_vdOverlapTopVs1_vd_vs1_lmul4",
        ],
        "cp_custom_wvv_all": [
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1",
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2",
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4",
            "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul1",
            "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul2",
            "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul4",
        ],
        "cp_custom_wwv_all": [
            "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul1",
            "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul2",
            "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul4",
        ],
        "cp_custom_wwv": [
            "cp_custom_vdOverlapTopVs1_vd_vs1_lmul1",
            "cp_custom_vdOverlapTopVs1_vd_vs1_lmul2",
            "cp_custom_vdOverlapTopVs1_vd_vs1_lmul4",
        ],
        "cp_custom_shift_vv": ["cp_custom_vshift_upperbits_vs1_ones"],
        "cp_custom_shift_wv": [
            "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1",
            "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2",
            "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4",
            "cp_custom_vshiftn_upperbits_vs1_ones",
        ],
        "cp_custom_wvx": [
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1",
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2",
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4",
        ],
        "cp_custom_wvx_all": [
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1",
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2",
            "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4",
        ],
        "cp_custom_shift_vx": ["cp_custom_vshift_upperbits_rs1_ones"],
        "cp_custom_shift_wx": [
            "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1",
            "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2",
            "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4",
            "cp_custom_vshiftn_upperbits_rs1_ones",
        ],
        "cp_custom_shift_wi": [
            "cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1",
            "cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul2",
            "cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4",
        ],
        "cp_custom_shift_wi_all": [],  # Generates unique coverage, but not unique testgen
        "cp_custom_vindexVV": ["cp_custom_vindexedges_index_ge_vlmax", "cp_custom_vindexedges_index_gt_vl_lt_vlmax"],
        "cp_custom_vindexVX": [],  # Edge cases for VX-type gather/slide are covered by cp_rs1_edges.
        "cp_custom_maskwrite_masked": ["cp_custom_vmask_write_lmulge1", "cp_custom_vmask_write_v0_masked"],
        "cp_custom_maskwrite_unmasked": ["cp_custom_vmask_write_lmulge1"],
        "cp_custom_red": [
            "cp_custom_element0Masked",
            "cp_custom_vmask_write_v0_masked",
            "cp_custom_voffgroup_vd_lmul2",
            "cp_custom_voffgroup_vd_lmul4",
            "cp_custom_voffgroup_vd_lmul8",
            "cp_custom_voffgroup_vs1_lmul2",
            "cp_custom_voffgroup_vs1_lmul4",
            "cp_custom_voffgroup_vs1_lmul8",
        ],
        "cp_custom_wred": [
            "cp_custom_element0Masked",
            "cp_custom_vmask_write_v0_masked",
            "cp_custom_vreductionw_vd_vs1_emul_16",
            "cp_custom_voffgroup_vd_lmul2",
            "cp_custom_voffgroup_vd_lmul4",
            "cp_custom_voffgroup_vs1_lmul2",
            "cp_custom_voffgroup_vs1_lmul4",
        ],
        "cp_custom_vreductionw": [],  # Generates unique coverage, but not unique testgen
        "cp_custom_vext2": ["cp_custom_vext2_overlapping_vd_vs2"],
        "cp_custom_vext4": ["cp_custom_vext4_overlapping_vd_vs2"],
        "cp_custom_vext8": ["cp_custom_vext8_overlapping_vd_vs2"],
        "cp_custom_gprwrite": ["cp_custom_gprWriting_vstart_eq_vl"],
        "cp_custom_vmv_s_x": [
            "cp_custom_voffgroup_vd_lmul2",
            "cp_custom_voffgroup_vd_lmul4",
            "cp_custom_voffgroup_vd_lmul8",
        ],
        "cp_custom_vmv_x_s": [
            "cp_custom_gprWriting_vstart_eq_vl",
            "cp_custom_voffgroup_vs2_lmul2",
            "cp_custom_voffgroup_vs2_lmul4",
            "cp_custom_voffgroup_vs2_lmul8",
        ],
    }

    expanded_coverpoints = []
    for coverpoint in coverpoints:
        if coverpoint in coverpoint_expansion_map:
            expanded_coverpoints.extend(coverpoint_expansion_map[coverpoint])
        else:
            expanded_coverpoints.append(coverpoint)
    return expanded_coverpoints
