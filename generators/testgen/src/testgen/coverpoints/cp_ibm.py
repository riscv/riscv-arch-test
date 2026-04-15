##################################
# cp_ibm.py
#
# IBM-defined floating point coverpoint generator. Each instruction has multiple
# IBM coverpoint groups (b1, b2, ...); testcase values are read from per-group
# CSV files bundled with the testgen package at coverpoints/ibm/<instr>_b<N>.csv.
# jcarlin@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""IBM floating point coverpoint generator (cp_ibm_b<N>)."""

import csv
from pathlib import Path

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params
from testgen.formatters.registry import get_instr_type_config

# IBM testcase data files live alongside this generator inside the testgen package.
IBM_DATA_DIR = Path(__file__).resolve().parent / "ibm"

# Valid rounding mode names accepted in the frm column of IBM CSV files.
VALID_FRM_NAMES = frozenset({"rne", "rtz", "rdn", "rup", "rmm"})

# Input operand value columns that may appear in an IBM CSV. The subset actually
# required for a given instruction is determined from its formatter config.
INPUT_VALUE_KEYS = frozenset({"fs1val", "fs2val", "fs3val", "rs1val", "rs2val", "rs3val"})

# Expected-result columns that the CSV may include for DUT verification. These are
# accepted in the header but currently unused by the test generator.
IGNORED_OUTPUT_KEYS = frozenset({"fdval", "rdval", "fflags"})


@add_coverpoint_generator("cp_ibm")
def make_cp_ibm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests from the IBM testcase CSV for this instruction and coverpoint group.

    The ``coverpoint`` argument is of the form ``cp_ibm_b<N>``; testcase values are read from
    ``coverpoints/ibm/<instr_name>_b<N>.csv``. The CSV header names columns after the
    ``generate_random_params`` kwargs (for example ``frm``, ``fs1val``, ``fs2val``,
    ``rs1val``). Each data row produces one testcase. Value cells for operand columns are
    parsed as integers via ``int(cell, 0)``; ``frm`` is a rounding-mode name string (one
    of ``rne``, ``rtz``, ``rdn``, ``rup``, ``rmm``). Expected-result columns (``fdval``,
    ``rdval``, ``fflags``) are accepted in the header but currently ignored.
    """
    if not coverpoint.startswith("cp_ibm_b"):
        raise ValueError(f"cp_ibm coverpoint must be of the form 'cp_ibm_b<N>', got {coverpoint!r}")
    group = coverpoint[len("cp_ibm_") :]  # extract IBM group (b1, b2, etc.)

    required_params = get_instr_type_config(instr_type).required_params or set()
    required_input_cols = INPUT_VALUE_KEYS & required_params

    data_file = IBM_DATA_DIR / instr_name / f"{group}.csv"
    if not data_file.is_file():
        raise FileNotFoundError(f"cp_ibm data file not found for {instr_name} {group}: {data_file}")

    test_chunks: list[TestChunk] = []
    with data_file.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{data_file}: CSV is empty (missing header row)")
        header = [col.strip() for col in reader.fieldnames]
        reader.fieldnames = header

        if "frm" not in header:
            raise ValueError(f"{data_file}: CSV header must include a 'frm' column (got {header})")
        missing = required_input_cols - set(header)
        if missing:
            raise ValueError(
                f"{data_file}: missing required operand columns for {instr_name} ({instr_type}): {sorted(missing)}"
            )
        unknown = set(header) - INPUT_VALUE_KEYS - IGNORED_OUTPUT_KEYS - {"frm"}
        if unknown:
            raise ValueError(f"{data_file}: unrecognized columns in header: {sorted(unknown)}")

        for row in reader:
            lineno = reader.line_num

            frm_mode = (row.get("frm") or "").strip()
            if not frm_mode:
                raise ValueError(f"{data_file}:{lineno}: empty 'frm' cell")
            if frm_mode not in VALID_FRM_NAMES:
                raise ValueError(
                    f"{data_file}:{lineno}: invalid frm value {frm_mode!r} (must be one of {sorted(VALID_FRM_NAMES)})"
                )

            values: dict[str, int] = {}
            for col in INPUT_VALUE_KEYS & set(header):
                cell = (row.get(col) or "").strip()
                if not cell:
                    raise ValueError(f"{data_file}:{lineno}: empty cell for required column '{col}'")
                values[col] = int(cell, 0)

            params = generate_random_params(test_data, instr_type, exclude_regs=[0], frm=frm_mode, **values)

            operand_desc = " ".join(f"{key} = {test_data.flen_format_str.format(v)}" for key, v in values.items())
            desc = f"{coverpoint} ({data_file.name}:{lineno} Test source {operand_desc}, frm = {frm_mode})"
            bin_name = f"{coverpoint}_{lineno}"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks
