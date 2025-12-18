##################################
# edges.py
#
# jcarlin@hmc.edu 5 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Edge value definitions for riscv-arch-test test generation.
"""

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
