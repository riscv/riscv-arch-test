##################################
# asm/helpers.py
#
# Assembly generation helpers for test code.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly generation helpers for test code."""

from __future__ import annotations

import random
from typing import Literal

from testgen.constants import INDENT
from testgen.data.params import InstructionParams
from testgen.data.state import TestData


def comment_banner(title: str, description: str | None = None) -> str:
    """
    Generate a comment banner for a test section.

    Args:
        title: The title of the section (e.g., coverpoint name)
        description: Optional multi-line description

    Returns:
        Formatted comment banner string
    """
    lines = [
        "",
        "",
        "/////////////////////////////////",
        f"// {title}",
    ]
    if description:
        lines.extend(f"//   {line}" for line in description.strip().split("\n"))
    lines.append("/////////////////////////////////")
    return "\n".join(lines)


def to_hex(value: int, bits: int) -> str:
    """
    Convert an integer to a hex string for assembly output.

    Args:
        value: The integer value (should already be in correct range)
        bits: Number of bits (used to handle negative values)
    """
    # For negative values, convert to unsigned representation
    if value < 0:
        value = value + (2**bits)
    return f"0x{value:0{bits // 4}x}"


def load_int_reg(name: str, reg: int, val: int, test_data: TestData) -> str:
    """Generate assembly to load an integer register with a specific value."""
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    test_data.test_chunk.data_values.append(val)
    return f"{INDENT}RVTEST_TESTDATA_LOAD_INT(x{test_data.int_regs.data_reg}, x{reg}) # load {name}: x{reg} = {to_hex(val, test_data.xlen)}"


def load_float_reg(
    name: str,
    reg: int,
    val: int,
    test_data: TestData,
    fp_load_type: Literal["single", "double", "half", "quad"] | None = None,
) -> str:
    """Generate assembly to load a floating point register with a specific value."""
    if fp_load_type is None:
        fp_load_type = test_data.fp_load_size

    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    test_data.test_chunk.data_values.append(val)
    fp_load_bits = {"half": 16, "single": 32, "double": 64, "quad": 128}.get(fp_load_type, test_data.flen)
    return f"{INDENT}RVTEST_TESTDATA_LOAD_FLOAT_{fp_load_type.upper()}(x{test_data.int_regs.data_reg}, f{reg}) # load {name}: f{reg} = {to_hex(val & ((1 << fp_load_bits) - 1), fp_load_bits)}"


def write_sigupd(
    check_reg: int | None, test_data: TestData, sig_type: Literal["int", "fflags", "float"] = "int"
) -> str:
    """
    Generate assembly for SIGUPD and increment sigupd_count.
    """
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    fp_temp_reg = test_data.float_regs.temp_reg
    label = test_data.current_testcase_label
    if sig_type == "int":
        if check_reg is None:
            raise ValueError("check_reg must be provided for int sig_type")
        test_data.test_chunk.sigupd_count += 1
        return (
            f"{INDENT}# Check if x{check_reg} contains the expected result. x{sig_reg} is the signature ptr, "
            f"x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            f"{INDENT}RVTEST_SIGUPD(x{sig_reg}, x{link_reg}, x{temp_reg}, x{check_reg}, {label}, {label}_str)"
        )
    elif sig_type == "fflags":
        test_data.test_chunk.sigupd_count += 1
        return (
            f"{INDENT}# Check fflags. x{sig_reg} is the signature ptr, "
            f"x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            f"{INDENT}RVTEST_SIGUPD_FFLAGS(x{sig_reg}, x{link_reg}, x{temp_reg}, {label}, {label}_str)"
        )
    elif sig_type == "float":
        if check_reg is None:
            raise ValueError("check_reg must be provided for float sig_type")
        if test_data.flen > test_data.xlen:
            test_data.test_chunk.sigupd_count += 3
        else:
            test_data.test_chunk.sigupd_count += 2
        return (
            f"{INDENT}# Check if f{check_reg} contains the expected result. Also checks fflags. "
            f"x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} "
            f"is a temp reg, f{fp_temp_reg} is a floating point temp reg.\n"
            f"{INDENT}RVTEST_SIGUPD_F(x{sig_reg}, x{link_reg}, x{temp_reg}, f{fp_temp_reg}, f{check_reg}, {label}, {label}_str)"
        )
    else:
        raise ValueError(f"Unknown sig_type: {sig_type}")


def reproducible_hash(s: str) -> int:
    """Return a simple hash of a string for use as a random seed.

    Python randomizes hashes by default, but we need a repeatable hash for repeatable test cases.
    """
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h


def return_test_regs(test_data: TestData, params: InstructionParams) -> None:
    """
    Return all registers used in a test case back to the pool.

    Args:
        test_data: TestData object managing the registers
        params: InstructionParams object containing used registers
    """
    test_data.int_regs.return_registers(params.used_int_regs)
    test_data.float_regs.return_registers(params.used_float_regs)
    test_data.vec_regs.return_registers(params.used_vec_regs)


def _lmul_flag(lmul: float) -> str:
    if lmul < 1:
        return f"f{int(1 / lmul)}"
    else:
        return str(lmul)


def load_vec_reg(
    name: str,
    register: int,
    val_pointer: str,
    temp_reg: int,
    sew: int,
    *,
    lmul: float | None = None,
    vl: str | None = None,
) -> list[str]:
    lines = []

    assert (lmul is None) == (vl is None), "When Setting Preload Information, both lmul and vl must be set together"
    # Preloads Require Special Handling for V
    if lmul is not None and vl is not None:
        if vl == "vlmax":
            lines.append(f"vsetvli x{temp_reg}, x0, e{sew}, m{_lmul_flag(lmul)}, tu, mu")
        else:
            lines.append(f"vsetivli x{temp_reg}, {vl}, e{sew}, m{_lmul_flag(lmul)}, tu, mu")

    lines.extend(
        [
            f"LA(x{temp_reg}, {val_pointer})",
            f"vle{sew}.v v{register}, (x{temp_reg})",
        ]
    )

    return lines


def write_sigupd_v(test_data: TestData, params: InstructionParams, *, mask_producing: bool = False) -> list[str]:
    assert params.sew is not None
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"

    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    label = test_data.current_testcase_label

    vtmp, mtmp = test_data.vec_regs.get_registers(2, lmul=1, exclude_regs=[0])

    lines = [
        f"vsetivli x0, 1, e{params.sew}, m1, tu, mu",
        f"# set SEW={params.sew}, LMUL=1, VL=1 before signature check",
        "# RVTEST_SIGUPD_V(_CMP, _SIG_PTR, _LINK_REG, _TEMP_REG, _VTMP, _MTMP, _SEW, _VREG, _INST_PTR, _STR_PTR)",
    ]

    if mask_producing:
        lines.extend(
            [
                f"RVTEST_SIGUPD_V(vmxor.mm, x{sig_reg}, x{link_reg}, x{temp_reg}, v{vtmp}, v{mtmp}, 8, v{params.vd}, {label}, {label}_str",
                f"# Check if v{params.vd} contains the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.",
            ]
        )
    else:
        lines.extend(
            [
                f"RVTEST_SIGUPD_V(vmsne.vv, x{sig_reg}, x{link_reg}, x{temp_reg}, v{vtmp}, v{mtmp}, 8, v{params.vd}, {label}, {label}_str",
                f"# Check if v{params.vd} contains the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.",
            ]
        )

    test_data.vec_regs.return_registers([vtmp, mtmp])
    return lines


def write_sigupd_v_len(test_data: TestData, params: InstructionParams, segments: int, lmul: int) -> list[str]:
    assert params.sew is not None
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"

    maxVLEN = 1024

    emul_for_bytes = int(params.lmul) if params.lmul is not None and params.lmul >= 1 else 1
    worst_bytes = maxVLEN * emul_for_bytes // 8
    sig_stride = max(test_data.xlen, test_data.flen, params.sew) // 8 if test_data.flen > 0 else test_data.xlen // 8
    offset_bytes = (worst_bytes + 4 + 7) & ~7
    test_data.test_chunk.sigupd_count += max(1, (offset_bytes + sig_stride - 1) // sig_stride) * segments

    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg

    temp_reg2, temp_reg3 = test_data.int_regs.get_registers(2)

    # We need vtmp (lmul-aligned), mtmp, mtmp2, mtmp3 (mask registers, no overlap, not v0)
    vtmp = test_data.vec_regs.get_register(lmul=lmul)
    mtmp, mtmp2, mtmp3 = test_data.vec_regs.get_registers(3, lmul=1, exclude_regs=[0])

    vs1 = params.vs1 if params.vs1 is not None else 0
    label = test_data.current_testcase_label
    masked_flag = params.maskval is not None

    lines = [
        # TODO: VCOMPRESS, SCALAR_DST, MASK_PROD
        f"RVTEST_SIGUPD_V_LEN(x{sig_reg}, x{link_reg}, x{temp_reg}, x{temp_reg2}, x{temp_reg3}, v{vtmp}, v{mtmp3}, v{mtmp2}, v{mtmp}, v{params.vd}, v{vs1}, 0, {masked_flag}, 0, {params.sew}, {lmul}, 0, {label}, {label}_str)",
        f"# Check if v{params.vd} contains the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.",
    ]

    test_data.int_regs.return_registers([temp_reg2, temp_reg3])
    test_data.vec_regs.return_registers([vtmp, mtmp, mtmp2, mtmp3])

    return lines


def prep_base_v(test_data: TestData, params: InstructionParams, registers: list[int]) -> list[str]:
    assert (params.ma is None) == (params.ta is None), "ta and ma must either both be present or absent"
    assert params.lmul is not None

    lines = []

    lmul_flag = "m" + _lmul_flag(params.lmul)

    mask_flags = ""
    if params.ma is not None:
        mask_flags += ", ma" if params.ma else ", mu"
    if params.ta is not None:
        mask_flags += ", ta" if params.ta else ", tu"

    flags = lmul_flag + mask_flags

    if params.vl == "random":
        temp_reg, vlmax_reg = test_data.int_regs.get_registers(2)

        randomVl = random.getrandbits(32)
        lines.extend(
            [
                "# Load Vl=Random",
                f"li {temp_reg}, {randomVl}",
                f"vsetvli x{vlmax_reg}, x0, e{params.sew}, {flags}",
                f"remu x{temp_reg}, x{temp_reg}, x{vlmax_reg}",
            ]
        )

        if params.egs != 1:
            raise NotImplementedError("Handle egs != 1 vl=random")
        else:
            lines.append(f"ori x{temp_reg}, x{temp_reg}, 0x2")
    elif params.vl == "vlmax":
        lines.extend(["# Load Vl=VLMAX", f"vsetvli x{params.temp_reg}, x0, e{params.sew}, {flags}"])
    else:
        vl = params.vl if params.vl is not None else 1

        lines.extend(
            [
                "# Set Registers to Deterministic Values (0xD)",
                f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m1, tu, mu",
            ]
        )

        for register in registers:
            lines.append(f"vmv.v.i v{register}, 13")

        lines.extend(
            [
                "# Load Desired VL",
                f"li x{params.temp_reg}, {vl}",
                f"vsetvli x0, x{params.temp_reg}, e{params.sew}, {flags}",
            ]
        )

    if params.vstart is not None:
        lines.extend(
            ["# Load Desired Vstart", f"li x{params.temp_reg}, {params.vstart}", f"csrw vstart, x{params.temp_reg}"]
        )

    return lines
