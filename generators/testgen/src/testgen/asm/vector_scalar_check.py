##################################
# asm/vector_scalar_check.py
#
# Assembly for scalar self-checking vector tests (e.g. Vx8-scalarcheck). Outside the instruction under test,
# these tests only use vset{i}vl{i} and unmasked unit-stride vle<eew>.v/vse<eew>.v with EEW = SEW.
# Each function replaces setup or reload code that would use other vector instructions.
# The routines and macros they call are in tests/env/rvtest_vector_scalar_check.h.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm import vector_helpers
from testgen.data.state import TestData


def splat_0xd_lines(register: int, sew: int, addr_reg: int) -> list[str]:
    """Fill a register group with 0xD at the current vl by loading a constant buffer."""
    return [f"LA(x{addr_reg}, rvtest_vsc_splat_d_e{sew})", f"vle{sew}.v v{register}, (x{addr_reg})"]


def fill_0xd_lines(registers: list[int], sew: int | None, addr_reg: int | None) -> list[str]:
    """Fill each register with 0xD at the current vl by loading a constant buffer."""
    lines = [f"LA(x{addr_reg}, rvtest_vsc_splat_d_e{sew})"]
    lines.extend(f"vle{sew}.v v{register}, (x{addr_reg})" for register in registers)
    return lines


def copy_mask_reg(test_data: TestData, dest: int, source: int) -> list[str]:
    """Copy a mask register with a store and load through memory."""
    temp_regs = test_data.int_regs.get_registers(3, exclude_regs=[0])
    test_data.int_regs.return_registers(temp_regs)
    t1, t2, t3 = temp_regs
    return [f"RVTEST_VSC_COPY_VREG(v{dest}, v{source}, x{t1}, x{t2}, x{t3})"]


def index_fixup_lines(
    test_data: TestData, vreg: int, eew: int, divisor_reg: int, *, shift: int | None, and_imm: int | None
) -> list[str]:
    """Emulate vremu.vx followed by vsll.vi (shift) or vand.vi (and_imm) on an index register with scalar code."""
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    shift_flag, imm = (1, shift) if shift is not None else (0, and_imm)
    return [f"RVTEST_VSC_INDEX_FIXUP(v{vreg}, {eew}, x{divisor_reg}, {shift_flag}, {imm}, x{link_reg}, x{temp_reg})"]


def emulated_load_lines(
    test_data: TestData,
    *,
    vd: int,
    eew: int,
    emul: float,
    base_reg: int,
    segments: int = 1,
    masked: bool = False,
    stride_reg: int | None = None,
    index_reg: int | None = None,
    index_eew: int | None = None,
    index_emul: float | None = None,
    mask_load: bool = False,
) -> list[str]:
    """
    Emulate a vector load that reloads stored data for checking (vle, vlse, vluxei/vloxei, their segment forms,
    and vlm.v) with vse/vle at EEW = SEW and a scalar gather routine. Elements that the load would not write keep
    their values. Preserves vl and vtype.
    """
    get_lmul_flag = vector_helpers.get_lmul_flag
    link = f"x{test_data.int_regs.link_reg}"
    temp = f"x{test_data.int_regs.temp_reg}"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])
    addr = f"x{addr_reg}"

    if index_reg is not None:
        mode = "VSC_G_INDEXED"
    elif stride_reg is not None:
        mode = "VSC_G_STRIDED"
    else:
        mode = "VSC_G_UNIT"
    flags = f"({mode} | VSC_G_MASKED)" if masked else mode
    eew_log = (eew // 8).bit_length() - 1
    reg_step = int(max(1, emul))

    lines = [
        "# Emulate the reload with a scalar gather",
        f"LA({temp}, rvtest_vsc_ctx)",
        f"csrr {link}, vl",
        f"SREG {link}, VSC_VL({temp})",
    ]
    if mask_load:
        lines.extend([f"addi {link}, {link}, 7", f"srli {link}, {link}, 3"])
    lines.extend(
        [
            f"SREG {link}, VSC_ORIGVL({temp})",
            f"csrr {link}, vtype",
            f"SREG {link}, VSC_VTYPE({temp})",
            f"SREG x{base_reg}, VSC_EXP({temp})",
            f"SREG x{stride_reg if stride_reg is not None else 0}, VSC_EXP2({temp})",
            f"LI({link}, {flags})",
            f"SREG {link}, VSC_FLAGS({temp})",
            f"LI({link}, {eew_log})",
            f"SREG {link}, VSC_EEWLOG({temp})",
            f"LI({link}, {segments})",
            f"SREG {link}, VSC_NELEM({temp})",
        ]
    )
    if index_reg is not None:
        assert index_eew is not None and index_emul is not None
        lines.extend(
            [
                f"LI({link}, {(index_eew // 8).bit_length() - 1})",
                f"SREG {link}, VSC_G_IEEWLOG({temp})",
                f"vsetvli {link}, x0, e{index_eew}, m{get_lmul_flag(index_emul)}, ta, ma",
                f"VSC_ADDI({link}, {temp}, VSC_OFF_IDX)",
                f"vse{index_eew}.v v{index_reg}, ({link})",
            ]
        )
    if masked:
        lines.extend(
            [
                f"vsetvli {link}, x0, e8, m1, ta, ma",
                f"VSC_ADDI({link}, {temp}, VSC_OFF_V0)",
                f"vse8.v v0, ({link})",
            ]
        )
    lines.extend(
        [
            f"vsetvli {link}, x0, e{eew}, m{get_lmul_flag(emul)}, tu, mu",
            f"slli {link}, {link}, {eew_log}",
            f"SREG {link}, VSC_NBYTES({temp})",
            f"VSC_ADDI({addr}, {temp}, VSC_OFF_ACT)",
        ]
    )
    for i in range(segments):
        lines.extend([f"vse{eew}.v v{vd + i * reg_step}, ({addr})", f"add {addr}, {addr}, {link}"])
    lines.extend(
        [
            f"jal {link}, rvtest_vsc_gather_{link}_{temp}",
            f"LA({temp}, rvtest_vsc_ctx)",
            f"LREG {link}, VSC_NBYTES({temp})",
            f"VSC_ADDI({addr}, {temp}, VSC_OFF_ACT)",
        ]
    )
    for i in range(segments):
        lines.extend([f"vle{eew}.v v{vd + i * reg_step}, ({addr})", f"add {addr}, {addr}, {link}"])
    lines.extend(
        [
            f"LREG {link}, VSC_VL({temp})",
            f"LREG {addr}, VSC_VTYPE({temp})",
            f"vsetvl x0, {link}, {addr}",
        ]
    )

    test_data.int_regs.return_register(addr_reg)
    return lines


def whole_register_load_lines(test_data: TestData, *, vd: int, nregs: int, sew: int, base_reg: int) -> list[str]:
    """Load nregs whole registers starting at vd with vle<sew>.v at VLMAX. Preserves vl and vtype."""
    t1, t2, t3 = test_data.int_regs.get_registers(3, exclude_regs=[0])
    test_data.int_regs.return_registers([t1, t2, t3])
    return [
        f"csrr x{t1}, vl",
        f"csrr x{t2}, vtype",
        f"vsetvli x{t3}, x0, e{sew}, m{nregs}, ta, ma",
        f"vle{sew}.v v{vd}, (x{base_reg})",
        f"vsetvl x0, x{t1}, x{t2}",
    ]


def set_lower_xreg_bits(num_bits_reg: int, test_data: TestData) -> list[str]:
    """Set the lowest x{num_bits_reg} bits of v0 and clear the rest with scalar stores and a load."""
    temp_regs = test_data.int_regs.get_registers(3, exclude_regs=[0])
    test_data.int_regs.return_registers(temp_regs)
    t1, t2, t3 = temp_regs
    return [
        "# Build the mask with scalar stores and load it into v0",
        f"RVTEST_VSC_LOWER_BITS_MASK(x{num_bits_reg}, x{t1}, x{t2}, x{t3})",
    ]


def preset_mask_lines(ones: bool, temp_reg: int | None, sew: int | None) -> list[str]:
    """Set v0 to all ones or all zeros by loading a constant buffer. Leaves x{temp_reg} = VLMAX at SEW, LMUL=1."""
    buffer = "rvtest_vsc_ones" if ones else "rvtest_vsc_zeros"
    return [
        f"# Set mask value to {'one' if ones else 'zero'}, x{temp_reg} = VLMAX",
        f"vsetvli x{temp_reg}, x0, e8, m1, tu, mu",
        f"LA(x{temp_reg}, {buffer})",
        f"vle8.v v0, (x{temp_reg})",
        f"vsetvli x{temp_reg}, x0, e{sew}, m1, tu, mu",
    ]


def random_mask_lines(mask_val: str, temp_reg: int | None) -> list[str]:
    """Load a mask from data with vle8.v in place of vlm.v. Leaves x{temp_reg} = VLEN, as vlm.v setup does."""
    return [
        f"# x{temp_reg} = VLEN/8",
        f"vsetvli x{temp_reg}, x0, e8, m1, tu, mu",
        f"LA(x{temp_reg}, {mask_val})",
        "# Load mask value into v0",
        f"vle8.v v0, (x{temp_reg})",
        f"vsetvli x{temp_reg}, x0, e8, m8, tu, mu",
    ]
