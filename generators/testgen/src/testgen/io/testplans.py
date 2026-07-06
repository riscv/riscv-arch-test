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
