##################################
# vector_helpers.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import re
from dataclasses import dataclass

from testgen.constants import ELEN_MAX, MIN_SEW_MIN
from testgen.data.edges import get_vector_edge
from testgen.data.state import TestData
from testgen.formatters.registry import get_instr_type_config


def make_and_register_edge_label(reg_name: str, edge_name: str, suffix: str, test_data: TestData) -> str:
    """
    Makes an edge data label out of the reg_name, edge_name, and suffix in the form of
    (reg_name)_edge_(edge_name)_(suffix). Then it registers the appropriate data for the emul found in the
    suffix, the sew in test_data, and the edge_name.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector operations"
    sew = test_data.config.sew

    emul: float = 1

    emulf_match = re.search(r"emulf(\d+)", suffix)
    if emulf_match is not None:
        emul = 1 / int(emulf_match.group(1))

    emul_match = re.search(r"emul(\d+)", suffix)
    if emul_match is not None:
        emul = int(emul_match.group(1))

    label = f"{reg_name}_edge_{edge_name}_{suffix}"
    # Don't overwrite the random edge, other edge overwrites are allowed as a correctness check:
    # register_vector_data will check that the value doesn't change when we reregister a label. This
    # ensures that the data we expect is present at the label we generate
    if not ("random" in label and label in test_data.vector_labels):
        eew = int(sew * emul)
        test_data.register_vector_data(label, eew, elements=[get_vector_edge(edge_name, suffix, sew)])

    return label


@dataclass
class InstructionInfo:
    """
    Information about individual vector instructions.

    This information can be derived from the instruction name alone, and is general information
    necessary for randomization and test generation. This includes the number of segments in a
    segmented load/store or the eew of an index register.

    Attributes
        segments: The number of segments that this instruction uses (e.g. 5 for vlseg5e8.v)
        load_store_eew: The eew of the data for this instruction (e.g. 8 for vle8.v)
        index_eew: The eew of the index register (e.g. 16 for vrgatherei16.vv)
        vext_multiplier: The fractional value that a vext instruction uses to calculate its eew
            (e.g. 0.125 for vzext.vf8)
        widen_vs2: Boolean for whether or not vs2 is widened
        widen_vs1: Boolean for whether or not vs1 is widened
        widen_vd: Boolean for whether or not vd is widened
    """

    segments: int
    load_store_eew: int | None
    index_eew: int | None
    vext_multiplier: float | None
    widened_regs: set[str]

    def get_size_multiplier(self, register: str, sew: int) -> int | float:
        """
        Get the size multiplier for a given register relative to the sew.
            e.g. the index register for vrgatherei16 has a size_multiplier of 1/2 at SEW=32

        Args:
            register: String containing which register it is (vs1, vs2, etc.)
            sew: Integer SEW for the test (should 8, 16, 32, or 64)
        """
        if self.vext_multiplier and register == "vs2":
            return self.vext_multiplier
        elif self.index_eew and register == "vs2":
            return self.index_eew / sew
        elif self.load_store_eew and register in ["vs3", "vd"]:  # Either one or the other exists for these instructions
            return self.load_store_eew / sew
        elif register in self.widened_regs:
            return 2
        return 1


def extract_instruction_info(instruction: str, instruction_type: str) -> InstructionInfo:
    """
    Construct and InstructionInfo object for a given instruction, given its type

    Args:
        instruction: The name of the instruction under test
        instruction_type: The type of the instruction under test. This should be the correct type
    """
    # Extract Segments
    # Generally, a segmented load/store looks like: vl___seg<nf>__.v or vl<nf>re_.v
    segmented_ls_match = re.search(r"v[ls]\w*seg(\d+)\w*.v", instruction)
    segments = int(segmented_ls_match.group(1)) if segmented_ls_match is not None else 1
    if segments < 1 or segments > 8:
        raise ValueError(f"Invalid Number of Segments in Instruction: {instruction}, Parsed {segments} segments")

    # Load/Store EEW: Ends with e<eew>.v, e<eew>ff.v,
    load_store_eew_match = re.search(r"v[ls]\w*e(\d+)(?:ff)?.v", instruction)
    load_store_eew = int(load_store_eew_match.group(1)) if load_store_eew_match is not None else None
    if load_store_eew not in [8, 16, 32, 64, None]:
        raise ValueError(f"Invalid EEW Parsed from Instruction: {instruction}, Parsed {load_store_eew} EEW")

    # index EEW: Ends with ei<eew>.v (also matches vrgatherei16.v)
    index_eew_match = re.search(r"v\w*ei(\d+).v", instruction)
    index_eew = int(index_eew_match.group(1)) if index_eew_match is not None else None
    if index_eew not in [8, 16, 32, 64, None]:
        raise ValueError(f"Invalid Index EEW Parsed from Instruction: {instruction}, Parsed {index_eew} EEW")

    vext_multiplier = 1 / int(instruction[-1]) if instruction_type == "VEXT" else None

    instr_type_config = get_instr_type_config(instruction_type)
    assert instr_type_config.vector_data is not None, "vector_data must be provided for a vector instruction type"

    widened_regs = instr_type_config.vector_data.widened_regs

    return InstructionInfo(
        segments=segments,
        load_store_eew=load_store_eew,
        index_eew=index_eew,
        vext_multiplier=vext_multiplier,
        widened_regs=widened_regs,
    )


def get_legal_lmuls(sew: int) -> list[int]:
    """
    Get all of the LMUL values guaranteed to be allowed at a given SEW.

    Args:
        sew: The SEW used to determine what LMULs are available. (e.g. often 2 is available at SEW=32, but not SEW=64)
    """
    lmulmin = MIN_SEW_MIN / ELEN_MAX

    legalvlmuls = [0, 1, 2, 3]
    # A given supported fractional LMUL setting must support SEW settings between SEWMIN and LMUL * ELEN
    if (lmulmin <= 0.5) and (sew in [8, 16, 32]):
        legalvlmuls.append(-1)
    if (lmulmin <= 0.25) and (sew in [8, 16]):
        legalvlmuls.append(-2)
    if (lmulmin <= 0.125) and (sew == 8):
        legalvlmuls.append(-3)

    return legalvlmuls


def get_base_lmul(instruction: str, instr_type: str, sew: int) -> float | int:
    """
    Gives an LMUL that ensures a whole register move is aligned, and keeps an indexed operation
    from having an index register with lmul greater than one.

    Args:
        instruction: Name of the instruction under test
        instr_type: Type of the instruction under test (these should match)
        sew: The SEW currently being tested. This is necessary for certain indexed operations
    """

    if instr_type == "VMVR":
        return int(instruction[3])

    info = extract_instruction_info(instruction, instr_type)
    if info.index_eew is not None and sew < info.index_eew:
        return sew / info.index_eew

    return 1
