##################################
# vector_helpers.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import dataclasses
import random
import re

from testgen.data.config import TestConfig
from testgen.data.random import random_int

VX_CORNER_NAMES = [
    "zero",
    "one",
    "two",
    "ones",
    "onesm1",
    "min",
    "minm1",
    "max",
    "maxm1",
    "walkeven",
    "walkodd",
    "random",
]

VLS_CORNER_NAMES = ["zero_emul8", "random_within_2vlmax"]

VF_CORNER_NAMES = [
    "vs_corner_f_pos0",
    "vs_corner_f_neg0",
    "vs_corner_f_pos1",
    "vs_corner_f_neg1",
    "vs_corner_f_posminnorm",
    "vs_corner_f_negmaxnorm",
    "vs_corner_f_posinfinity",
    "vs_corner_f_neginfinity",
    "vs_corner_f_pos0p5",
    "vs_corner_f_pos1p5",
    "vs_corner_f_neg2",
    "vs_corner_f_pi",
    "vs_corner_f_twoToEmax",
    "vs_corner_f_onePulp",
    "vs_corner_f_largestsubnorm",
    "vs_corner_f_negSubnormLeadingOne",
    "vs_corner_f_min_subnorm",
    "vs_corner_f_canonicalQNaN",
    "vs_corner_f_negNoncanonicalQNaN",
    "vs_corner_f_sNaN_payload1",
]

fedges = {
    "pos0": 0x00000000,  # 0
    "neg0": 0x80000000,  # -0
    "pos1": 0x3F800000,  # 1.0
    "neg1": 0xBF800000,  # -1.0
    "posminnorm": 0x00800000,  # smallest positive normalized
    "negmaxnorm": 0xFF7FFFFF,  # most negative
    "posinfinity": 0x7F800000,  # positive infinity
    "neginfinity": 0xFF800000,  # negative infinity
    "pos0p5": 0x3F000000,  # 0.5
    "pos1p5": 0x3FC00000,  # 1.5
    "neg2": 0xC0000000,  # 2.0
    "pi": 0x40490FDB,  # pi
    "twoToEmax": 0x7F000000,  # 2^emax
    "onePulp": 0x3F800001,  # 1 + ulp
    "largestsubnorm": 0x007FFFFF,  # largest positive subnorm
    "negSubnormLeadingOne": 0x80400000,  # positive subnorm with leading 1
    "min_subnorm": 0x00000001,  # smallest positive subnorm
    "canonicalQNaN": 0x7FC00000,  # canonical quiet NaN
    "negNoncanonicalQNaN": 0xFFFFFFFF,  # noncanonical quiet NaN
    "sNaN_payload1": 0x7F800001,
}  # signaling NaN with lsb set

fedgesD = {
    "pos0": 0x0000000000000000,  # 0
    "neg0": 0x8000000000000000,  # -0
    "pos1": 0x3FF0000000000000,  # 1.0
    "neg1": 0xBFF0000000000000,  # -1.0
    "posminnorm": 0x0010000000000000,  # smallest positive normalized
    "negmaxnorm": 0xFFEFFFFFFFFFFFFF,  # most negative
    "posinfinity": 0x7FF0000000000000,  # positive infinity
    "neginfinity": 0xFFF0000000000000,  # negative infinity
    "pos0p5": 0x3FE0000000000000,  # 0.5
    "pos1p5": 0x3FF8000000000000,  # 1.5
    "neg2": 0xC000000000000000,  # 2.0
    "pi": 0x400921FB54442D18,  # pi
    "twoToEmax": 0x7FE0000000000000,  # 2^emax
    "onePulp": 0x3FF0000000000001,  # 1 + ulp
    "largestsubnorm": 0x000FFFFFFFFFFFFF,  # largest positive subnorm
    "negSubnormLeadingOne": 0x8008000000000000,  # positive subnorm with leading 1
    "min_subnorm": 0x0000000000000001,  # smallest positive subnorm
    "canonicalQNaN": 0x7FF8000000000000,  # canonical quiet NaN
    "negNoncanonicalQNaN": 0xFFFFFFFFFFFFFFFF,  # noncanonical quiet NaN
    "sNaN_payload1": 0x7FF0000000000001,
}  # signaling NaN with lsb set

fedgesH = {
    "pos0": 0x0000,  # 0
    "neg0": 0x8000,  # -0
    "pos1": 0x3C00,  # 1.0
    "neg1": 0xBC00,  # -1.0
    "posminnorm": 0x0400,  # smallest positive normalized
    "negmaxnorm": 0xFBFF,  # most negative
    "posinfinity": 0x7C00,  # positive infinity
    "neginfinity": 0xFC00,  # negative infinity
    "pos0p5": 0x3800,  # 0.5
    "pos1p5": 0x3E00,  # 1.5
    "neg2": 0xC000,  # 2.0
    "pi": 0x4248,  # pi
    "twoToEmax": 0x7800,  # 2^emax
    "onePulp": 0x3C01,  # 1 + ulp
    "largestsubnorm": 0x03FF,  # largest positive subnorm
    "negSubnormLeadingOne": 0x8200,  # positive subnorm with leading 1
    "min_subnorm": 0x0001,  # smallest positive subnorm
    "canonicalQNaN": 0x7E00,  # canonical quiet NaN
    "negNoncanonicalQNaN": 0xFFFF,  # noncanonical quiet NaN
    "sNaN_payload1": 0x7D01,
}  # signaling NaN with lsb set

fedgesBF16 = {
    "pos0": 0x0000,  # 0
    "neg0": 0x8000,  # -0
    "pos1": 0x3F80,  # 1.0
    "neg1": 0xBF80,  # -1.0
    "posminnorm": 0x0080,  # smallest positive normalized
    "negmaxnorm": 0xFF7F,  # most negative
    "posinfinity": 0x7F80,  # positive infinity
    "neginfinity": 0xFF80,  # negative infinity
    "pos0p5": 0x3F00,  # 0.5
    "pos1p5": 0x3FC0,  # 1.5
    "neg2": 0xC000,  # 2.0
    "pi": 0x4049,  # pi
    "twoToEmax": 0x7F00,  # 2^emax
    "onePulp": 0x3F81,  # 1 + ulp
    "largestsubnorm": 0x007F,  # largest positive subnorm
    "negSubnormLeadingOne": 0x8040,  # positive subnorm with leading 1
    "min_subnorm": 0x0001,  # smallest positive subnorm
    "canonicalQNaN": 0x7FC0,  # canonical quiet NaN
    "negNoncanonicalQNaN": 0xFFFF,  # noncanonical quiet NaN
    "sNaN_payload1": 0x7F81,
}  # signaling NaN with lsb set


def get_corner_value(corner: str, suffix: str, sew: int) -> int:
    if suffix == "f":
        if sew == 16:
            return fedgesH[corner]
        elif sew == 32:
            return fedges[corner]
        elif sew == 64:
            return fedgesD[corner]
        else:
            raise ValueError(f"Unsupported Floating Point SEW={sew}")

    if suffix == "f_emul2":
        if sew == 16:
            return fedges[corner]
        elif sew == 32:
            return fedgesD[corner]
        else:
            raise ValueError(f"Unsupported EMUL2 Floating Point SEW={sew}")

    if suffix == "f_bf16":
        return fedgesBF16[corner]

    if suffix == "eew1":
        return _corner_value(corner, 8)

    emul = 1
    if suffix.startswith("emul"):
        emul = int(suffix[len("emul") :])

    return _corner_value(corner, sew * emul)


def _corner_value(corner: str, eew: int) -> int:
    if corner == "zero" or corner == "zero_emul8":
        return 0
    if corner == "one":
        return 1
    if corner == "two":
        return 2
    if corner == "ones":
        return (1 << eew) - 1
    if corner == "onesm1":
        return (1 << eew) - 2
    if corner == "min":
        return 1 << (eew - 1)
    if corner == "minm1":
        return (1 << (eew - 1)) + 1
    if corner == "max":
        return (1 << (eew - 1)) - 1
    if corner == "maxm1":
        return (1 << (eew - 1)) - 2
    if corner == "walkeven":
        return sum(1 << i for i in range(eew) if i % 2 == 0)
    if corner == "walkodd":
        return sum(1 << i for i in range(eew) if i % 2 == 1)
    if corner == "random":
        return random_int(eew)
    if corner == "random_within_2vlmax":
        return random.randint(3, 2 ** (eew - 1 - 3))
    raise ValueError(f"Unknown corner: {corner}")


@dataclasses.dataclass
class InstructionInfo:
    segments: int
    load_store_eew: int | None
    index_eew: int | None
    vext_multiplier: float | None
    widen_vs2: bool
    widen_vd: bool

    def get_size_multiplier(self, register: str, sew: int) -> int | float:
        if self.vext_multiplier and register == "vs2":
            return self.vext_multiplier
        elif self.index_eew and register == "vs2":
            return self.index_eew / sew
        elif self.load_store_eew and register in ["vs3", "vd"]:  # Either one or the other exists for these instructions
            return self.load_store_eew / sew
        elif self.widen_vd and register == "vd" or self.widen_vs2 and register == "vs2":
            return 2
        return 1


def extract_instruction_info(instruction: str, instruction_type: str) -> InstructionInfo:
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

    vd_widen = vs2_widen = False
    if instruction_type in ["WVWSR", "FWVWSR", "WWV", "WWX", "FWWF", "VWV", "VWX", "VWI"]:
        vs2_widen = True
    if instruction_type in ["WVWSR", "FWVWSR", "WVV", "WVX", "WWV", "WVS", "FWVF", "FWWF", "FWCVT"]:
        vd_widen = True

    return InstructionInfo(
        segments=segments,
        load_store_eew=load_store_eew,
        index_eew=index_eew,
        vext_multiplier=vext_multiplier,
        widen_vd=vd_widen,
        widen_vs2=vs2_widen,
    )


def get_legal_lmuls(sew: int, test_config: TestConfig) -> list[int]:
    lmulmin = test_config.sew_min / test_config.elen

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
    """

    if instr_type == "VMVR":
        return int(instruction[3])

    info = extract_instruction_info(instruction, instr_type)
    if info.index_eew is not None and sew < info.index_eew:
        return sew / info.index_eew

    return 1
