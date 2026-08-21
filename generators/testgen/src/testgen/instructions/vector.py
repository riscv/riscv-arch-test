##################################
# instructions/vector.py
#
# rwolk@hmc.edu June 2026
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Pure vector instruction parsing and LMUL helpers."""

import re
from dataclasses import dataclass

from testgen.constants import ELEN_MAX, MIN_SEW_MIN


@dataclass
class VectorInstructionInfo:
    """
    Information about individual vector instructions derived from instruction names.

    This information can only be derived from the instruction name, and is general information
    necessary for randomization and test generation. This includes the number of segments in a
    segmented load/store or the eew of an index register.

    Attributes
        segments: The number of segments that this instruction uses (e.g. 5 for vlseg5e8.v)
        load_store_eew: The eew of the data for this instruction (e.g. 8 for vle8.v)
        index_eew: The eew of the index register (e.g. 16 for vrgatherei16.vv)
        vext_multiplier: The fractional value that a vext instruction uses to calculate its eew
            (e.g. 0.125 for vzext.vf8)
        widened_regs: Set of registers that are widened
    """

    segments: int
    load_store_eew: int | None
    index_eew: int | None
    vext_multiplier: float | None
    whole_registers: int | None

    def get_size_multiplier(self, register: str, sew: int, widened_regs: set[str]) -> int | float:
        """Return a register's size multiplier relative to SEW."""
        if self.vext_multiplier and register == "vs2":
            return self.vext_multiplier
        if self.index_eew and register == "vs2":
            return self.index_eew / sew
        if self.load_store_eew and register in ["vs3", "vd"]:
            return self.load_store_eew / sew
        if register in widened_regs:
            return 2
        return 1


def parse_vector_instruction_info(instruction: str, instruction_type: str) -> VectorInstructionInfo:
    """Parse vector instruction facts encoded in an instruction name."""

    # Extract Segments
    # Generally, a segmented load/store looks like: vl___seg<nf>__.v or vl<nf>re_.v
    segmented_ls_match = re.search(r"v[ls]\w*seg(\d+)\w*.v", instruction)
    segments = int(segmented_ls_match.group(1)) if segmented_ls_match is not None else 1
    if segments < 1 or segments > 8:
        raise ValueError(f"Invalid Number of Segments in Instruction: {instruction}, Parsed {segments} segments")

    # Load/Store EEW: Ends with e<eew>.v, e<eew>ff.v,
    load_store_eew_match = re.search(r"v[ls]\w*e(\d+)(?:ff)?.v", instruction)
    load_store_eew = int(load_store_eew_match.group(1)) if load_store_eew_match is not None else None
    if instruction in ["vlm.v", "vsm.v"]:
        load_store_eew = 8  # Special case that needs to be hardcoded
    if load_store_eew not in [8, 16, 32, 64, None]:
        raise ValueError(f"Invalid EEW Parsed from Instruction: {instruction}, Parsed {load_store_eew} EEW")

    # index EEW: Ends with ei<eew>.v (also matches vrgatherei16.v)
    index_eew_match = re.search(r"v\w*ei(\d+).v", instruction)
    index_eew = int(index_eew_match.group(1)) if index_eew_match is not None else None
    if index_eew not in [8, 16, 32, 64, None]:
        raise ValueError(f"Invalid Index EEW Parsed from Instruction: {instruction}, Parsed {index_eew} EEW")

    vext_multiplier = 1 / int(instruction[-1]) if instruction_type == "VEXT" else None

    whole_register_match = re.search(r"v[ls](\d)r", instruction)
    whole_registers = int(whole_register_match.group(1)) if whole_register_match else None

    return VectorInstructionInfo(
        segments=segments,
        load_store_eew=load_store_eew,
        index_eew=index_eew,
        vext_multiplier=vext_multiplier,
        whole_registers=whole_registers,
    )


def get_legal_lmuls(sew: int) -> list[int]:
    """Return the LMUL values guaranteed to be legal for an SEW."""
    lmulmin = MIN_SEW_MIN / ELEN_MAX

    legal_lmuls = [0, 1, 2, 3]
    if lmulmin <= 0.5 and sew in [8, 16, 32]:
        legal_lmuls.append(-1)
    if lmulmin <= 0.25 and sew in [8, 16]:
        legal_lmuls.append(-2)
    if lmulmin <= 0.125 and sew == 8:
        legal_lmuls.append(-3)

    return legal_lmuls


def get_base_lmul(instruction: str, instr_type: str, sew: int) -> float | int:
    """Return an LMUL that satisfies whole-register and indexed-operation constraints."""
    if instr_type == "VMVR":
        return int(instruction[3])

    info = parse_vector_instruction_info(instruction, instr_type)
    if info.index_eew is not None and sew < info.index_eew:
        return sew / info.index_eew
    elif info.load_store_eew is not None and sew < info.load_store_eew:
        return sew / info.load_store_eew

    return 1
