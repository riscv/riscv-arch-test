##################################
# zip_type.py
#
# Zvzip instruction types:
#   VZIPVV - interleaving with a 2xEMUL destination at the same SEW (vzip.vv)
#   VUNZIP - unary extraction with a 2xEMUL source at the same SEW
#            (vunzipe.v, vunzipo.v)
#   VPAIR  - interleaving of even/odd elements with no operand overlap
#            allowed (vpaire.vv, vpairo.vv)
#
# Unlike widening (WVV) instructions, the doubled EMUL keeps the same SEW:
# the register group holds twice as many elements, not wider elements.
#
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.formatters.types.vv_type import format_vv_like_type
from testgen.formatters.types.vvv_type import format_vvv_like_type

# vzip.vv: EVL is 2*VL and the destination EMUL is 2xLMUL. The destination
# group may overlap a source group only in its highest-numbered part, so the
# bottom of vd must not overlap either source.
vzipvv_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd_bottom", "vs1"), ("vd_bottom", "vs2")},
        emul2_regs={"vd"},
    ),
)

# vunzipe.v/vunzipo.v: the source EMUL is 2xLMUL and 2*VL source elements are
# read. The destination group may overlap the source group only in the
# lowest-numbered part of the source group.
vunzip_config = InstructionTypeConfig(
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs2_top")},
        emul2_regs={"vs2"},
    ),
)

# vpaire.vv/vpairo.vv: the destination group cannot overlap either source
# group and, when masked, cannot overlap the mask register.
vpair_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2")},
        masked_constraints={("vd", "v0"), ("vs1", "v0"), ("vs2", "v0")},
    ),
)


@add_instruction_formatter("VZIPVV", vzipvv_config)
def format_vzipvv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    # vd holds 2*VL elements at SEW, so load and check it with 2xLMUL at SEW.
    return format_vvv_like_type(instr_str, test_data, params, "VZIPVV", vd_lmul_multiplier=2)


@add_instruction_formatter("VUNZIP", vunzip_config)
def format_vunzip(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    # vs2 holds 2*VL elements at SEW; preload the full 2x group so that every
    # element the instruction may read is deterministic.
    return format_vv_like_type(
        instr_str, test_data, params, "VUNZIP", vs2_lmul_multiplier=2, vs2_sew_multiplier=0.5, preload_vs2=True
    )


@add_instruction_formatter("VPAIR", vpair_config)
def format_vpair(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvv_like_type(instr_str, test_data, params, "VPAIR")
