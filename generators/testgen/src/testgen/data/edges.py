##################################
# edges.py
#
# jcarlin@hmc.edu 5 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Edge value definitions for riscv-arch-test test generation.
"""

from typing import ClassVar

from testgen.data.random import random_int, random_range

# ==============================================================================
# Immediate Values
# ==============================================================================


class IMMEDIATE_EDGES:
    """Edge values for immediates of various widths."""

    # 6-bit signed immediate (compressed instructions)
    imm_6bit = (0, 1, 2, 3, 4, 8, 16, 30, 31, -32, -31, -2, -1)

    # 12-bit signed immediate (I-type, S-type)
    imm_12bit = (0, 1, 2, 3, 4, 8, 16, 32, 64, 128, 256, 512, 1023, 1024, 1795, 2047, -2048, -2047, -2, -1)

    # 20-bit immediate (U-type)
    imm_20bit = (
        0,
        1,
        2,
        3,
        4,
        8,
        16,
        32,
        64,
        128,
        256,
        512,
        1024,
        2048,
        4096,
        8192,
        16384,
        32768,
        65536,
        131072,
        262144,
        524286,
        524287,
        524288,
        524289,
        1048574,
        1048575,
    )

    # 32-bit compressed shift immediates
    imm_32_c = (1, 2, 3, 4, 8, 14, 15, 16, 17, 30, 31)

    # 64-bit compressed shift immediates
    imm_64_c = (*imm_32_c, 32, 33, 48, 62, 63)

    # Unsigned immediate for word operations
    imm_uimmw = (0, 1, 19, 30, 31)

    # Unsigned immediate for doubleword operations
    imm_uimm = (*imm_uimmw, 32, 33, 45, 62, 63)

    # 5-bit Signed Immediates (Vector Instructions)
    imm_5bit = (0, 1, 2, 14, 15, -1, -2, -15, -16)

    # 5-bit Unsigned Immediates (Vector Instructions)
    imm_5bit_u = (0, 1, 2, 15, 16, 30, 31)


# ==============================================================================
# Integer Register Values
# ==============================================================================


class INTEGER_EDGES:
    """Edge values for integer register operands of various widths."""

    # 6-bit values
    bits_6 = (
        0,
        1,
        2,
        2**5,
        2**5 + 1,
        2**5 - 1,
        2**5 - 2,
        2**6 - 1,
        2**6 - 2,
        0b101010,
        0b010101,
        0b010110,
    )

    # 8-bit values
    bits_8 = (
        0,
        1,
        2,
        2**7,
        2**7 + 1,
        2**7 - 1,
        2**7 - 2,
        2**8 - 1,
        2**8 - 2,
        0b01010101,
        0b10101010,
        0b01011011,
        0b11011011,
    )

    # 16-bit values
    bits_16 = (
        0,
        1,
        2,
        2**15,
        2**15 + 1,
        2**15 - 1,
        2**15 - 2,
        2**16 - 1,
        2**16 - 2,
        0b0101010101010101,
        0b1010101010101010,
        0b0101101110111100,
        0b1101101110111100,
    )

    # 20-bit values (for upper immediate patterns)
    bits_20 = (
        0,
        0b11111111111111111111000000000000,
        0b10000000000000000000000000000000,
        0b00000000000000000001000000000000,
        0b01001010111000100000000000000000,
    )

    # 32-bit values
    bits_32 = (
        0,
        1,
        2,
        2**31,
        2**31 + 1,
        2**31 - 1,
        2**31 - 2,
        2**32 - 1,
        2**32 - 2,
        0b10101010101010101010101010101010,
        0b01010101010101010101010101010101,
        0b01100011101011101000011011110111,
        0b11100011101011101000011011110111,
    )

    # sraiw values
    sraiw = (
        0b0000000000000000000000000000000000000000000000000000000000000000,
        0b0000000000000000000000000000000000000000000000000000000000000001,
        0b1111111111111111111111111111111111111111111111111111111111111111,
        0b0000000000000000000000000000000001111111111111111111111111111111,
        0b1111111111111111111111111111111110000000000000000000000000000000,
    )

    # c.slli edges for RV32
    c_slli_32 = (
        0,
        1,
        0b01000000000000000000000000000000,
        0b00111111111111111111111111111111,
        0b01111111111111111111111111111111,
        0b01010101010101010101010101010101,
        0b00101101110111100100010000111011,
    )

    # c.slli edges for RV64
    c_slli_64 = (
        0,
        1,
        0x4000000000000000,
        0x0000000007FFFFFFF,
        0x000000080000000,
        0x3FFFFFFFFFFFFFFF,
        0x7FFFFFFFFFFFFFFF,
        0x5555555555555555,
        0x2DDE443BB1D7437B,
    )

    # c.srli edges for RV32
    c_srli_32 = (
        0,
        2,
        4,
        0b11111111111111111111111111111110,
        0b11111111111111111111111111111100,
        0b10101010101010101010101010101010,
        0b10110111011110010001000011101110,
    )

    # c.srli edges for RV64
    c_srli_64 = (
        0,
        2,
        4,
        0x00000001FFFFFFFE,
        0x00000001FFFFFFFC,
        0x0000000200000000,
        0x0000000200000002,
        0xFFFFFFFFFFFFFFFE,
        0xFFFFFFFFFFFFFFFC,
        0xAAAAAAAAAAAAAAAA,
        0xB77910EEC75D0DEE,
    )

    # c.srai edges for RV32
    c_srai_32 = (
        0,
        2,
        4,
        0b11111111111111111111111111111110,
        0b00110111011110010001000011101110,
    )

    # c.srai edges for RV64
    c_srai_64 = (
        0,
        2,
        4,
        0x00000001FFFFFFFE,
        0x00000001FFFFFFFC,
        0x0000000200000000,
        0x0000000200000002,
        0xFFFFFFFFFFFFFFFE,
        0xFFFFFFFFFFFFFFFC,
        0x377910EEC75D0DEE,
    )


# ==============================================================================
# Memory Values
# ==============================================================================


class MEMORY_EDGES:
    """Edge values for memory operations of various widths."""

    byte = (0, 1, 0x7F, 0x80, 0xFF)
    hword = (0, 1, 0x7FFF, 0x8000, 0xFFFF)
    word = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
    double = (0, 1, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000, 0xFFFFFFFFFFFFFFFF)


# ==============================================================================
# Floating-Point Values
# ==============================================================================


class FLOAT_EDGES:
    """Edge values for floating-point numbers."""

    single = (
        0x00000000,  # 0
        0x80000000,  # -0
        0x3F800000,  # 1.0
        0xBF800000,  # -1.0
        0x3FC00000,  # 1.5
        0xBFC00000,  # -1.5
        0x40000000,  # 2.0
        0xC0000000,  # -2.0
        0x00800000,  # smallest positive normalized
        0x80800000,  # smallest negative normalized
        0x7F7FFFFF,  # most positive
        0xFF7FFFFF,  # most negative
        0x007FFFFF,  # largest positive subnorm
        0x807FFFFF,  # largest negative subnorm
        0x00400000,  # positive subnorm with leading 1
        0x80400000,  # negative subnorm with leading 1
        0x00000001,  # smallest positive subnorm
        0x80000001,  # smallest negative subnorm
        0x7F800000,  # positive infinity
        0xFF800000,  # negative infinity
        0x7FC00000,  # canonical quiet NaN
        0x7FFFFFFF,  # noncanonical quiet NaN
        0xFFFFFFFF,  # noncanonical quiet NaN with sign bit set
        0x7F800001,  # signaling NaN with lsb set
        0x7FBFFFFF,  # signaling NaN with all mantissa bits set
        0xFFBFFFFF,  # signaling Nan with all mantissa bits and sign bit set
        0x7EF8654F,  # random positive 1.65087e+38
        0x813D9AB0,  # random negative -3.48248e-38
    )

    double = (
        0x0000000000000000,  # 0.0
        0x8000000000000000,  # -0.0
        0x3FF0000000000000,  # 1.0
        0xBFF0000000000000,  # -1.0
        0x3FF8000000000000,  # 1.5
        0xBFF8000000000000,  # -1.5
        0x4000000000000000,  # 2.0
        0xC000000000000000,  # -2.0
        0x0010000000000000,  # smallest positive normalized
        0x8010000000000000,  # smallest negative normalized
        0x7FEFFFFFFFFFFFFF,  # most positive normalized
        0xFFEFFFFFFFFFFFFF,  # most negative normalized
        0x000FFFFFFFFFFFFF,  # largest positive subnorm
        0x800FFFFFFFFFFFFF,  # largest negative subnorm
        0x0008000000000000,  # mid positive subnorm
        0x8008000000000000,  # mid negative subnorm
        0x0000000000000001,  # smallest positive subnorm
        0x8000000000000001,  # smallest negative subnorm
        0x7FF0000000000000,  # positive infinity
        0xFFF0000000000000,  # negative infinity
        0x7FF8000000000000,  # canonical quiet NaN
        0x7FFFFFFFFFFFFFFF,  # noncanonical quiet NaN
        0xFFF8000000000000,  # noncanonical quiet NaN with sign bit set
        0x7FF0000000000001,  # signaling NaN with lsb set
        0x7FF7FFFFFFFFFFFF,  # signaling NaN with all mantissa bits set
        0xFFF0000000000001,  # signaling NaN with lsb and sign bits set
        0x5A392534A57711AD,  # 4.25535e126 random positive
        0xA6E895993737426C,  # -2.97516e-121 random negative
    )

    half = (
        0x0000,  # 0.0
        0x8000,  # -0.0
        0x3C00,  # 1.0
        0xBC00,  # -1.0
        0x3E00,  # 1.5
        0xBE00,  # -1.5
        0x4000,  # 2.0
        0xC000,  # -2.0
        0x0400,  # smallest normalized
        0x8400,  # smallest negative normalized
        0x7BFF,  # most positive normalized
        0xFBFF,  # most negative normalized
        0x03FF,  # largest positive subnorm
        0x83FF,  # largest negative subnorm
        0x0200,  # positive subnorm with leading 1
        0x8200,  # negative subnorm with leading 1
        0x0001,  # smallest positive subnorm
        0x8001,  # smallest negative subnorm
        0x7C00,  # positive infinity
        0xFC00,  # negative infinity
        0x7E00,  # canonical quiet NaN
        0x7FFF,  # noncanonical quiet NaN
        0xFE00,  # noncanonical quiet NaN with sign bit set
        0x7C01,  # signaling NaN with lsb set
        0x7DFF,  # signaling NaN with all mantissa bits set
        0xFC01,  # signaling NaN with lsb and sign bits set
        0x58B4,  # 150.5 random positive
        0xC93A,  # -10.4531 random negative
    )

    bf16 = (
        0x0000,  # 0
        0x8000,  # -0
        0x3F80,  # 1.0
        0xBF80,  # -1.0
        0x3FC0,  # 1.5
        0xBFC0,  # -1.5
        0x4000,  # 2.0
        0xC000,  # -2.0
        0x0080,  # smallest positive normalized
        0x8080,  # smallest negative normalized
        0x7F7F,  # most positive
        0xFF7F,  # most negative
        0x007F,  # largest positive subnorm
        0x807F,  # largest negative subnorm
        0x0040,  # positive subnorm with leading 1
        0x8040,  # negative subnorm with leading 1
        0x0001,  # smallest positive subnorm
        0x8001,  # smallest negative subnorm
        0x7F80,  # positive infinity
        0xFF80,  # negative infinity
        0x7FC0,  # canonical quiet NaN
        0x7FFF,  # noncanonical quiet NaN
        0xFFFF,  # noncanonical quiet NaN with sign bit set
        0x7F81,  # signaling NaN with lsb set
        0x7FBF,  # signaling NaN with all mantissa bits set
        0xFFBF,  # signaling Nan with all mantissa bits and sign bit set
        0x7EF8,  # random positive 1.6482427e+38
        0x813D,  # random negative -3.4713818e-38
    )

    # Bad NaN-boxing: Double register holding Single value
    bad_NaN_double_single = (
        0xFFFFEFFF00000000,
        0xAAAAAAAA80000000,
        0x000000003F800000,
        0xDEADBEEFBF800000,
        0xA1B2C3D400800000,
        0xFFFFFFEF80800000,
        0xFEFFFFEF7F7FFFFF,
        0x7E7E7E7EFF7FFFFF,
        0x7FFFFFFF7F800000,
        0xFFFFFFFEFF800000,
        0xFEEDBEE57FC00000,
        0xFFC0DEFF7FFFFFFF,
        0xFEFFFFFF7F800001,
        0xFFFFFEFF7FBFFFFF,
    )

    # Bad NaN-boxing: Double register holding Half value
    bad_NaN_double_half = (
        0xFFFFFFFF00000000,
        0xFFFFFFFFFFFE8000,
        0x7FFFFFFFFFFF3C00,
        0xFEEDBEE5BEEFBC00,
        0xFFFFFFEFFFFF0400,
        0x00000000FFFF8400,
        0xEFFFFFFFFFFF7BFF,
        0xC0DEC0DEC0DEFBFF,
        0xA83EF1CC4F1A7C00,
        0xFFFFFFFF0FFFFC00,
        0xFFFEFFFFFFFF7E00,
        0xFFFFFFEFFFFF7FFF,
        0xA1B2C3D4E5F67C01,
        0xFFFFFFFCFFFF7DFF,
    )

    # Bad NaN-boxing: Single register holding Half value
    bad_NaN_single_half = (
        0x00000000,
        0xFFFE8000,
        0x7FFF3C00,
        0xBEEFBC00,
        0xFEFF0400,
        0x0FFF8400,
        0xEFFF7BFF,
        0xC0DEFBFF,
        0x4F1A7C00,
        0x0FFFFC00,
        0xFFEF7E00,
        0xFEEF7FFF,
        0xA1B27C01,
        0x4FD77DFF,
    )


class VECTOR_EDGES:
    vx_edges = (
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
    )

    vls_edges = ("zero_emul8", "random_within_2vlmax")

    vf_edges = (
        "vs_edge_f_pos0",
        "vs_edge_f_neg0",
        "vs_edge_f_pos1",
        "vs_edge_f_neg1",
        "vs_edge_f_posminnorm",
        "vs_edge_f_negmaxnorm",
        "vs_edge_f_posinfinity",
        "vs_edge_f_neginfinity",
        "vs_edge_f_pos0p5",
        "vs_edge_f_pos1p5",
        "vs_edge_f_neg2",
        "vs_edge_f_pi",
        "vs_edge_f_twoToEmax",
        "vs_edge_f_onePulp",
        "vs_edge_f_largestsubnorm",
        "vs_edge_f_negSubnormLeadingOne",
        "vs_edge_f_min_subnorm",
        "vs_edge_f_canonicalQNaN",
        "vs_edge_f_negNoncanonicalQNaN",
        "vs_edge_f_sNaN_payload1",
    )

    f32: ClassVar = {
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
        "sNaN_payload1": 0x7F800001,  # signaling NaN with lsb set
    }

    f64: ClassVar = {
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
        "sNaN_payload1": 0x7FF0000000000001,  # signaling NaN with lsb set
    }

    f16: ClassVar = {
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
        "sNaN_payload1": 0x7D01,  # signaling NaN with lsb set
    }

    bf16: ClassVar = {
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
        "sNaN_payload1": 0x7F81,  # signaling NaN with lsb set
    }

    @staticmethod
    def edge_value(edge: str, eew: int) -> int:
        if edge == "zero" or edge == "zero_emul8":
            return 0
        if edge == "one":
            return 1
        if edge == "two":
            return 2
        if edge == "ones":
            return (1 << eew) - 1
        if edge == "onesm1":
            return (1 << eew) - 2
        if edge == "min":
            return 1 << (eew - 1)
        if edge == "minm1":
            return (1 << (eew - 1)) + 1
        if edge == "max":
            return (1 << (eew - 1)) - 1
        if edge == "maxm1":
            return (1 << (eew - 1)) - 2
        if edge == "walkeven":
            return sum(1 << i for i in range(eew) if i % 2 == 0)
        if edge == "walkodd":
            return sum(1 << i for i in range(eew) if i % 2 == 1)
        if edge == "random":
            random_val = 0
            conflict = True
            while conflict:
                random_val = random_int(eew, signed=False)
                conflict = False
                for edge2 in VECTOR_EDGES.vx_edges:
                    if "random" in edge2:
                        continue
                    if random_val == VECTOR_EDGES.edge_value(edge2, eew) or random_val == 0x81:
                        conflict = True
                        break
            return random_val
        if edge == "random_within_2vlmax":
            random_val = 0
            conflict = True
            while conflict:
                conflict = False
                random_val = random_range(3, 2 ** (eew - 1 - 3))
                for edge2 in VECTOR_EDGES.vls_edges:
                    if "random" in edge2:
                        continue
                    if random_val == VECTOR_EDGES.edge_value(edge2, eew):
                        conflict = True
                        break
            return random_val
        raise ValueError(f"Unknown edge: {edge}")


# ==============================================================================
# XLEN-Dependent Edge Generation Functions
# ==============================================================================


def get_general_edges(xlen: int) -> tuple[int, ...]:
    """Get general edge values for integer registers based on XLEN."""
    base_edges = (
        0,
        1,
        2,
        2 ** (xlen - 1),
        2 ** (xlen - 1) + 1,
        2 ** (xlen - 1) - 1,
        2 ** (xlen - 1) - 2,
        2**xlen - 1,
        2**xlen - 2,
    )

    if xlen == 32:
        # Add 32-bit specific patterns
        base_edges += (
            0b01011011101111001000100001110010,  # random pattern
            0b10101010101010101010101010101010,  # walking odd
            0b01010101010101010101010101010101,  # walking even
        )
    else:  # xlen == 64
        # Add 64-bit specific patterns
        base_edges += (
            0b0101101110111100100010000111011101100011101011101000011011110010,  # random
            0b1010101010101010101010101010101010101010101010101010101010101010,  # walking odd
            0b0101010101010101010101010101010101010101010101010101010101010101,  # walking even
            0b0000000000000000000000000000000011111111111111111111111111111111,  # Wmax
            0b0000000000000000000000000000000011111111111111111111111111111110,  # Wmaxm1
            0b0000000000000000000000000000000100000000000000000000000000000000,  # Wmaxp1
            0b0000000000000000000000000000000100000000000000000000000000000001,  # Wmaxp2
        )

    return base_edges


# TODO: Do we really need these extra edges for orcb?
def get_orcb_edges(xlen: int) -> tuple[int, ...]:
    """
    Get edge values for orcb (OR combine bytes) instruction.
    """
    base = get_general_edges(xlen)

    if xlen == 32:
        base += (0x01020408, 0x10204080, 0x02040801, 0x20408010)
    else:  # xlen == 64
        base += (0x1020408001020408, 0x2040801002040801, 0x4080102004080102, 0x8010204008010204)

    return base


def get_vector_edge(edge: str, suffix: str, sew: int) -> int:
    """
    Look up the value of a vector edge for a given name, suffix, and sew
    """
    if suffix == "f":
        if sew == 16:
            return VECTOR_EDGES.f16[edge]
        elif sew == 32:
            return VECTOR_EDGES.f32[edge]
        elif sew == 64:
            return VECTOR_EDGES.f64[edge]
        else:
            raise ValueError(f"Unsupported Floating Point SEW={sew}")

    if suffix == "f_emul2":
        if sew == 16:
            return VECTOR_EDGES.f32[edge]
        elif sew == 32:
            return VECTOR_EDGES.f64[edge]
        else:
            raise ValueError(f"Unsupported EMUL2 Floating Point SEW={sew}")

    if suffix == "f_bf16":
        return VECTOR_EDGES.bf16[edge]

    if suffix == "eew1":
        return VECTOR_EDGES.edge_value(edge, 8)

    emul: int | float = 1
    if suffix.startswith("emulf"):
        # Fractional emul (e.g. vext cases)
        emul = 1 / int(suffix[len("emulf") :])
    elif suffix.startswith("emul"):
        emul = int(suffix[len("emul") :])

    return VECTOR_EDGES.edge_value(edge, int(sew * emul))
