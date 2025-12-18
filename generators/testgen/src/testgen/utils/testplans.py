##################################
# testplans.py
#
# jcarlin@hmc.edu 5 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Read testplans for riscv-arch-test test generation.
"""

import csv
from dataclasses import dataclass
from pathlib import Path


def get_extensions(testplan_dir: Path) -> list[str]:
    """Get the list of extensions from the testplan directory"""
    extensions: list[str] = []
    for testplan in testplan_dir.glob("*.csv"):
        extension = testplan.stem
        if ("V" not in extension and "Zv" not in extension) or extension in [
            "ZfaZvfh"
        ]:  # TODO: Remove once vector testgen is merged
            extensions.append(extension)
    return extensions


@dataclass
class TestPlanData:
    """
    Data structure for information on a single instruction parsed from a testplan.
    """

    instr_type: str
    rv32: bool
    rv64: bool
    coverpoints: list[str]


def read_testplan(testplan_path: Path) -> dict[str, TestPlanData]:
    """Read a testplan and return a dictionary of instructions and their associated data(type, coverpoints, etc.)"""
    instructions: dict[str, TestPlanData] = {}
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
            del row["Instruction"]
            del row["Type"]
            del row["RV32"]
            del row["RV64"]
            coverpoints: list[str] = []
            for key, value in row.items():
                if type(value) is str and value != "":
                    if (
                        value != "x"
                    ):  # for special entries, append the entry name (e.g. cp_rd_edges becomes cp_rd_edges_lui)
                        key = key + "_" + value
                    coverpoints.append(key)
            instructions[instr] = TestPlanData(instr_type=instr_type, rv32=rv32, rv64=rv64, coverpoints=coverpoints)
    return instructions
