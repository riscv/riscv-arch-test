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
        # TODO: Remove once vector testgen is merged
        if ("V" not in extension and "Zv" not in extension) or extension == "ZfaZvfh":
            extensions.append(extension)
    return extensions


def get_vector_extensions(testplan_dir: Path, *, priv: bool) -> list[str]:
    if priv:
        testplan_dir = testplan_dir / "priv"
    testplans = []
    for file in testplan_dir.glob("*.csv"):
        arch = file.stem
        if priv:
            is_vector = arch.startswith(("ExceptionsV", "SsstrictV", "MisalignedV", "V", "Zv"))
        else:
            is_vector = arch.startswith(("V", "Zv"))

        if not is_vector:
            continue

        elif arch in ["Vx", "Vls", "Zvbb", "Zvkb"]:
            for effew in ["8", "16", "32", "64"]:
                testplans.append(arch + effew)
        elif arch in ["ExceptionsVf", "Vf"]:
            for effew in ["16", "32", "64"]:
                testplans.append(arch + effew)
        elif arch == "Zvknhb":
            for effew in ["32", "64"]:
                testplans.append(arch + effew)
        else:
            testplans.append(arch)
    return testplans


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
