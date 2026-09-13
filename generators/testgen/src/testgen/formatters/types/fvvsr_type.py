##################################
# fvvsr_type.py
#
# rwolk@hmc.edu August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import random

from testgen.asm.vector_helpers import handle_vector_fp
from testgen.data.params import InstructionParams
from testgen.data.random import random_int, random_range
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.formatters.types.vvsr_type import format_vvsr_like_type

fvvsr_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(scalar_regs={"vd", "vs1"}),
)
fwvwsr_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vs2", "vs1")}, scalar_regs={"vd", "vs1"}, widened_regs={"vd", "vs1"}
    ),
)


def to_fp_words(integers: list[int], precision: int) -> list[int]:
    fp_biases = {16: 15, 32: 127, 64: 1023}
    fp_mantissa_lengths = {16: 11, 32: 24, 64: 53}
    bias = fp_biases[precision]
    mantissa_length = fp_mantissa_lengths[precision]
    fps = []

    for integer in integers:
        if integer == 0:
            fps.append(0)
            continue

        sign = integer < 0
        integer = abs(integer)
        exponent = integer.bit_length() - 1
        biased_exponent = exponent + bias

        # Align the "fractional" bits of the integer, and remove the leading one
        significand = (integer << (mantissa_length - integer.bit_length())) & ((1 << (mantissa_length - 1)) - 1)
        fp = (sign << (precision - 1)) | (biased_exponent << (mantissa_length - 1)) | significand

        fps.append(fp)

    return fps


# Unordered reductions need special handling for random inputs
def unordered_sum_rng(element_count: int, sew: int, register: str) -> list[int]:
    # We want to avoid ever setting a rounding bit because implementations are allowed to differ
    # on intermediate results for unordered floating point reductions, we only use integers representable
    # as floating point values
    fp_mantissas = {16: 11, 32: 24, 64: 53}
    max_exact_fp_integer = 2 ** fp_mantissas[sew]

    if register == "vs1":
        # We also need to ensure that the value in vs1 doesn't lead to an overflow in what is exactly
        # representable.
        vs1_range = [-max_exact_fp_integer // 4, max_exact_fp_integer // 4]
        final_sequence = [0 for _ in range(element_count)]
        final_sequence[0] = random_range(*vs1_range)
    else:
        if element_count == 1:
            return [random_int(sew)]

        # Get a random positive and negative upper bound for the sum (i.e. with the positive and negative numbers
        # we use, this is the maximum value a reduction tree could reach)

        # These bounds are chosen so that no matter the value in vs1, no reduction tree could reach a value
        # where rounding could happen
        negative_target = random_range(max_exact_fp_integer // 2, max_exact_fp_integer * 3 // 4)
        positive_target = random_range(max_exact_fp_integer // 2, max_exact_fp_integer * 3 // 4)

        # Find numbers that sum to the target by picking random points as barriers between them
        # e.g. insert | into *********** to get ****|*|****|**, meaning 4 + 1 + 4 + 2 = 11
        negative_cuts = sorted(random_range(0, negative_target) for _ in range(math.ceil(element_count / 2)))
        negative_sequence = (
            [negative_cuts[0]]
            + [negative_cuts[i + 1] - negative_cuts[i] for i in range(len(negative_cuts) - 1)]
            + [negative_target - negative_cuts[-1]]
        )
        negative_sequence = [-item for item in negative_sequence]

        positive_cuts = sorted(random_range(0, positive_target) for _ in range(math.floor(element_count / 2)))
        positive_sequence = (
            [positive_cuts[0]]
            + [positive_cuts[i + 1] - positive_cuts[i] for i in range(len(positive_cuts) - 1)]
            + [positive_target - positive_cuts[-1]]
        )

        final_sequence = negative_sequence + positive_sequence
        random.shuffle(final_sequence)

    return to_fp_words(final_sequence, sew)


fvvsru_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(scalar_regs={"vd", "vs1"}, random_element_generator=unordered_sum_rng),
)
fwvwsru_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vs2", "vs1")},
        scalar_regs={"vd", "vs1"},
        widened_regs={"vd", "vs1"},
        random_element_generator=unordered_sum_rng,
    ),
)


@add_instruction_formatter("FVVSR", fvvsr_config)
def format_fvvsr(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvsr_like_type(instr_str, test_data, params, "FVVSR")
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FWVWSR", fwvwsr_config)
def format_fwvwsr(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvsr_like_type(instr_str, test_data, params, "FWVWSR", widen={"vd", "vs1"})
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FVVSRU", fvvsru_config)
def format_fvvsru(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvsr_like_type(instr_str, test_data, params, "FVVSRU")
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FWVWSRU", fwvwsru_config)
def format_fwvwsru(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvsr_like_type(instr_str, test_data, params, "FWVWSRU", widen={"vd", "vs1"})
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check
