##################################
# cp_masking_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import PresetMask
from testgen.data.random import random_int, random_range
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase, get_instruction_type_config
from testgen.instructions.vector import get_base_lmul, parse_vector_instruction_info
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_masking_edges")
def make_mask_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate length suite tests with edge values in the mask register. Edges include zeros, ones, VLMAX-1 Ones,
    VLMAX/2 + 1 Ones, and a random mask
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    config = get_instruction_type_config(instr_type)
    assert config.vector_data is not None
    if not config.vector_data.maskable:
        raise ValueError(f"{coverpoint} requires a maskable instruction, got {instr_name} ({instr_type})")

    cp_masking_edges_data = [
        PresetMask.ONES,
        PresetMask.ZEROS,
        PresetMask.VLMAX_M1_ONES,
        PresetMask.VLMAX_D2_P1_ONES,
        "cp_mask_random",
    ]
    sew = test_data.config.sew
    # Mask element 0 inactive and element 1 active, so the random mask is never zero, all ones,
    # VLMAX-1 ones or VLMAX/2+1 ones, whatever VLMAX is
    random_mask = [random_int(sew) & ((1 << sew) - 1) for _ in range(VLEN_MAX // sew)]
    random_mask[0] = (random_mask[0] & ~0b11) | 0b10
    test_data.register_vector_data("cp_mask_random", sew, elements=random_mask)

    test_chunks = []
    base_lmul = get_base_lmul(instr_name, instr_type, sew)

    for m in cp_masking_edges_data:
        # VLMAX/2+1 ones differs from all ones and VLMAX-1 ones only when VLMAX >= 8, so use the largest LMUL
        lmul = _max_lmul(instr_name, instr_type, sew, base_lmul) if m == PresetMask.VLMAX_D2_P1_ONES else base_lmul
        vma = random_range(0, 1)
        vta = random_range(0, 1)

        desc = f"cp_masking_edges (Test v0 = {m})"
        bin_name = f"cp_masking_edges_maskval_{m}"

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul,
            suite="length",
            masked=True,
            additional_no_overlap={("vs1", "v0"), ("vs2", "v0"), ("vd", "v0"), ("vs3", "v0")},
            maskval=m,
            vl="vlmax",
            ma=vma,
            ta=vta,
        )
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


def _max_lmul(instr_name: str, instr_type: str, sew: int, base_lmul: float) -> float:
    """Return the largest LMUL (at least base_lmul) that keeps every operand's EMUL * NFIELDS <= 8."""
    info = parse_vector_instruction_info(instr_name, instr_type)
    vector_config = get_instruction_type_config(instr_type).vector_data
    if vector_config is None or info.whole_registers is not None or instr_type == "VMVR":
        return base_lmul
    cap = 8 / (max(1, (info.load_store_eew or sew) / sew) * info.segments)
    if info.index_eew is not None:
        cap = min(cap, 8 * sew / info.index_eew)
    if vector_config.widened_regs:
        cap = min(cap, 4)
    lmul = base_lmul
    while lmul * 2 <= cap:
        lmul *= 2
    return lmul
