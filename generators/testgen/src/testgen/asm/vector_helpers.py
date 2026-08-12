##################################
# asm/vector_helpers.py
#
# Assembly generation helpers for vector tests
# rwolk@hmc.edu 17 July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from testgen.constants import VLEN_MAX
from testgen.data.params import InstructionParams, PresetMask
from testgen.data.random import random_int
from testgen.data.state import TestData


def _lmul_flag(lmul: float) -> str:
    """
    Simple Helper to Make an LMUL flag for a vset(i)vl(i) instruction.
    """
    if lmul < 1:
        return f"f{int(1 / lmul)}"
    else:
        return str(int(lmul))


def vector_sigupd_bytes(max_bytes: int, test_data: TestData, vdsew: int) -> int:
    sig_stride = max(test_data.xlen, test_data.flen, vdsew) // 8
    offset_bytes = (max_bytes + 4 + 7) & ~7
    return max(1, (offset_bytes + sig_stride - 1) // sig_stride)


def write_sigupd_v(
    test_data: TestData, params: InstructionParams, *, mask_producing: bool = False, widen_vd: bool = False
) -> list[str]:
    """
    Write a base suite SIGUPD macro, correctly handling the use of a different check instruction for mask producing
    instructions and handles the widening of vd in base suite.
    """
    assert params.sew is not None
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"

    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    label = test_data.current_testcase_label
    vdsew = params.sew * (2 if widen_vd else 1)

    # Count the number of bytes the sigupd macro will consume. This is going to be the size of the element
    # group that we are checking in the first index, plus 4 bytes for padding, and then rounded to the nearest
    # multiple of 8 (+7 & ~8) achieves this. This computation is mirrored in RVTEST_SIGUPD_V_ADVANCE
    egs = params.egs if params.egs is not None else 1
    max_bytes = vdsew * egs // 8
    test_data.test_chunk.sigupd_count += vector_sigupd_bytes(max_bytes, test_data, vdsew)

    vtmp, mtmp = test_data.vec_regs.get_registers(2, lmul=1, exclude_regs=[0])

    lines = [
        f"# set SEW={vdsew}, LMUL=1, VL=1 before signature check",
        f"vsetivli x0, 1, e{vdsew}, m1, tu, mu",
    ]

    if mask_producing:
        lines.extend(
            [
                f"# Check if v{params.vd} contains the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.",
                f"# v{mtmp} is a temporary register holding the mask of the comparison result and v{vtmp} will hold the signature result, and {vdsew} is the SEW",
                f"RVTEST_SIGUPD_V(vmxor.mm, x{sig_reg}, x{link_reg}, x{temp_reg}, v{vtmp}, v{mtmp}, {vdsew}, v{params.vd}, {label}, {label}_str)",
            ]
        )
    else:
        lines.extend(
            [
                f"# Check if v{params.vd} contains the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.",
                f"# v{mtmp} is a temporary register holding the mask of the comparison result and v{vtmp} will hold the signature result, and {vdsew} is the SEW",
                f"RVTEST_SIGUPD_V(vmsne.vv, x{sig_reg}, x{link_reg}, x{temp_reg}, v{vtmp}, v{mtmp}, {vdsew}, v{params.vd}, {label}, {label}_str)",
            ]
        )

    test_data.vec_regs.return_registers([vtmp, mtmp])
    return lines


def write_sigupd_v_len(
    test_data: TestData,
    params: InstructionParams,
    segments: int,
    lmul: float,
    *,
    widen_vd: bool = False,
    vcompress: bool = False,
    mask_producing: bool = False,
    scalar_dest: bool = False,
    mask_reg: int = 0,
) -> list[str]:
    """
    Write a length-suite vector SIGUPD macro.

    Args:
        test_data: TestData for the instruction under test
        params: Parameters for the instruction under test (used to extract SEW)
        segments: The number of segments used in the instruction. When there are multiple, the sigupd
            macro may have to be emitted multiple times. (TODO: make this an optional arg)
        lmul: The lmul that this sigupd should check. Note that this can be different from the test lmul

    Optional Args:
        widen_vd: When active, SIGUPD will run with 2*SEW as the element width
        vcompress: Active when the instruction under test is vcompress because vcompress needs special handling
        mask_producing: Active when the instruction under test has a mask as an optional argument
        scalar_dest: Active when vd only contains one element and needs different handling.
        mask_reg: Set to the value where the mask register lies (0 by default). Used when the mask is overwritten
            by the instruction under test.
    """
    assert params.sew is not None
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"

    vdsew = params.sew * (2 if widen_vd else 1)

    # Count the number of bytes the sigupd macro will consume. This is going to be the size of the largest supported
    # VLEN * EMUL, plus 4 bytes for padding, and then rounded to the nearest multiple of 8 (+7 & ~8 achieves this).
    # This computation is mirrored in RVTEST_SIGUPD_V_ADVANCE
    emul_for_bytes = int(max(1, lmul)) if not mask_producing else 8
    max_bytes = VLEN_MAX * emul_for_bytes // 8
    sig_sew = vdsew if mask_producing else 8
    test_data.test_chunk.sigupd_count += vector_sigupd_bytes(max_bytes, test_data, sig_sew)

    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg

    temp_reg2, temp_reg3 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    # We need vtmp (lmul-aligned), mtmp, mtmp2, mtmp3 (mask registers, no overlap, not v0)
    vtmp = test_data.vec_regs.get_register(lmul=int(max(lmul, 1)))
    mtmp, mtmp2, mtmp3 = test_data.vec_regs.get_registers(3, lmul=1, exclude_regs=[0])

    vs1 = params.vs1 if params.vs1 is not None else 0
    label = test_data.current_testcase_label
    masked_flag = 0 if params.maskval is None or scalar_dest else 1
    maskprod_flag = 1 if mask_producing else 0
    vcompress_flag = 1 if vcompress else 0
    scalar_dst_flag = 1 if scalar_dest else 0

    lines = [
        # TODO: SEGMENTS
        f"# Check if v{params.vd} contains the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg}, x{temp_reg2}, and x{temp_reg3} are a temp regs.",
        f"# v{vtmp} will hold the signature result, v{mtmp3}, v{mtmp2}, and v{mtmp} are temporary mask registers holding the masks to aid error detection. v{vs1} was VS1 in the instruction",
        f"# under test and is used to compute the evl for vcompress, v{mask_reg} is the register holding the mask for the instruction under test. In order the flags are: mask_producing,",
        f"# masked and vcompress. VDSEW={vdsew}, signature lmul = {max(1, lmul)}, and finally a flag for if the destinitation register is used as a scalar vector register.",
        f"RVTEST_SIGUPD_V_LEN(x{sig_reg}, x{link_reg}, x{temp_reg}, x{temp_reg2}, x{temp_reg3}, v{vtmp}, v{mtmp3}, v{mtmp2}, v{mtmp}, v{params.vd}, v{vs1}, v{mask_reg}, {maskprod_flag}, {masked_flag}, {vcompress_flag}, {vdsew}, {int(max(lmul, 1))}, {scalar_dst_flag}, {label}, {label}_str)",
    ]

    test_data.int_regs.return_registers([temp_reg2, temp_reg3])
    test_data.vec_regs.return_registers([vtmp, mtmp, mtmp2, mtmp3])

    return lines


def write_sigupd_v_mask_prod(
    test_data: TestData,
    params: InstructionParams,
) -> list[str]:
    """
    Variant of SIGUPD for mask producing operations that nops in self-check and puts an additional value
    in the signature in non-self checking mode. This ensures that we can test both the behavior at vlmax
    and at the test vl, as a valid implementation can do either.
    """
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"

    # We cannot consider only taking an eew=1 worth of bytes here due to the way RVTEST_SIGUPD_V_ADVANCE works
    emul_for_bytes = 8
    worst_bytes = VLEN_MAX * emul_for_bytes // 8
    sig_stride = max(test_data.xlen, test_data.flen, 8) // 8
    offset_bytes = (worst_bytes + 4 + 7) & ~7
    test_data.test_chunk.sigupd_count += max(1, (offset_bytes + sig_stride - 1) // sig_stride)

    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg

    return [
        f"# Special SIGUPD variant that stores a mask in SIGRUN mode and no-ops in SELFCHECK mode. x{sig_reg} is the",
        f"# signature pointer, x{link_reg} is the link register, x{temp_reg} is a temp register, and v{params.vd} is the result of the operation",
        f"RVTEST_SIGUPD_VLMAX_MASK_PROD(x{sig_reg}, x{link_reg}, x{temp_reg}, v{params.vd})",
    ]


def reload_vtype(params: InstructionParams, vl_register_or_imm: str | int) -> str:
    """
    Resets the vtype to the state that prep_base_v left it.
    """
    assert params.lmul is not None, "lmul must be set for vector instructions"
    lmul_flag = "m" + _lmul_flag(params.lmul)

    mask_flags = ""
    mask_flags += ", ta" if params.ta else ", tu"
    mask_flags += ", ma" if params.ma else ", mu"
    flags = lmul_flag + mask_flags

    if isinstance(vl_register_or_imm, str):
        return f"vsetvli x{params.temp_reg}, {vl_register_or_imm}, e{params.sew}, {flags}"
    else:
        return f"vsetivli x{params.temp_reg}, {vl_register_or_imm}, e{params.sew}, {flags}"


def prep_base_v(
    test_data: TestData, params: InstructionParams, registers: list[int], lmul_override: float | None = None
) -> tuple[list[str], str | int]:
    """
    Prepares the vector registers for the test by setting vl appropriately, setting up vtype, and when necessary
    places deterministic values in the tails of vector registers.
    """
    assert (params.ma is None) == (params.ta is None), "ta and ma must either both be present or absent"
    assert params.lmul is not None or lmul_override is not None, "lmul must be set for vector instructions"

    lines = []

    if lmul_override is None:
        assert params.lmul is not None
        lmul_flag = "m" + _lmul_flag(params.lmul)
    else:
        lmul_flag = "m" + _lmul_flag(lmul_override)

    mask_flags = ""
    mask_flags += ", ta" if params.ta else ", tu"
    mask_flags += ", ma" if params.ma else ", mu"

    flags = lmul_flag + mask_flags
    vl_register_or_imm: str | int = 0

    if params.vl == "random":
        temp_reg, vlmax_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

        randomVl = random_int(32, signed=False)
        lines.extend(
            [
                "# Load Vl=Random",
                f"LI(x{temp_reg}, {randomVl})",
                f"vsetvli x{vlmax_reg}, x0, e{params.sew}, {flags}",
                f"remu x{temp_reg}, x{temp_reg}, x{vlmax_reg}",
            ]
        )

        if params.egs != 1 and params.egs is not None:
            raise NotImplementedError("Handle egs != 1 vl=random")
        else:
            lines.append(f"ori x{temp_reg}, x{temp_reg}, 0x2")

        lines.append(f"vsetvli x0, x{temp_reg}, e{params.sew}, {flags}")

        test_data.int_regs.return_registers([vlmax_reg])
        vl_register_or_imm = f"x{temp_reg}"
    elif params.vl == "vlmax":
        lines.extend(
            [
                "# Load Vl=VLMAX",
                f"vsetvli x{params.temp_reg}, x0, e{params.sew}, {flags}",
            ]
        )
        vl_register_or_imm = "x0"
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
                f"LI (x{params.temp_reg}, {vl})",
                f"vsetvli x0, x{params.temp_reg}, e{params.sew}, {flags}",
            ]
        )

        vl_register_or_imm = vl

    if params.vstart is not None:
        lines.extend(
            [
                "# Load Desired vstart",
                f"LI (x{params.temp_reg}, {params.vstart})",
                f"csrw vstart, x{params.temp_reg}",
            ]
        )

    return lines, vl_register_or_imm


def set_lower_xreg_bits(num_bits_reg: int, test_data: TestData) -> list[str]:
    """
    Builds a mask register with the lowest n bits set, where n is held in num_bits_reg.

    Uses the same calculation as the length suite sigupd macro building the tail mask.
    """

    temp_reg, temp_reg2 = test_data.int_regs.get_registers(2, exclude_regs=[0])
    temp_v = test_data.vec_regs.get_register()

    code = [
        "# Calculate the mask value by hand: start with a single whole register zeroed out",
        f"vsetvli x{temp_reg}, x0, e8, m1, ta, ma",
        f"vmv.v.i v{temp_v}, 0",
        "vsetivli x0, 1, e8, m1, tu, ma",
        "# Calculate which bit is the barrier between the ones and zeros",
        f"andi x{temp_reg}, x{num_bits_reg}, 0x7",
        f"addi x{temp_reg2}, x0, 1",
        f"sll x{temp_reg}, x{temp_reg2}, x{temp_reg}",
        "# Get something of the form 0b0011111 to prepare for a slideup",
        f"addi x{temp_reg}, x{temp_reg}, -1",
        f"vmv.v.x v{temp_v}, x{temp_reg}",
        f"vsetvli x{temp_reg}, x0, e8, m1, ta, ma",
        "# Prepare and execute a slide up, filling 0xff",
        f"LI (x{temp_reg}, 0xff)",
        f"vmv.v.x v0, x{temp_reg}",
        f"srli x{temp_reg}, x{num_bits_reg}, 3",
        f"vslideup.vx v0, v{temp_v}, x{temp_reg}",
    ]

    test_data.int_regs.return_registers([temp_reg, temp_reg2])
    test_data.vec_regs.return_register(temp_v)

    return code


def prep_mask_v(
    mask_val: str | PresetMask,
    test_data: TestData,
    params: InstructionParams,
    *,
    clobber_vd: bool = False,
    vd_v0: bool = False,
) -> list[str]:
    """
    Prepares the mask value for an instruction under test.

    Args:
        mask_val: Either a label that has the value for the mask, or value from the PresetMasks enum these values are computed at
          run time, and this generates code for it.
        test_data: Relevant test data, and contains the register files so that we have access to temporary registers.
        params: Gives access to lmul for VLMAX calculation

    Optional Args:
        clobber_vd: When there are not enough registers, this gives the option to use vd as an lmul-aligned temp register.
        vd_v0: When vd = v0, v0 is already taken from the register file, so when this flag is active, we overwrite the value in
            v0 and do not claim it from the register file.
    """
    assert params.lmul is not None, "LMUL is Required When Setting a Mask Value"
    lmul_flag = _lmul_flag(params.lmul)

    if not vd_v0:
        test_data.vec_regs.consume_registers([0])  # Ensure that we can actually use the mask register

    # We need an lmul aligned register for vid.v
    clobbered_vd = False
    try:
        vtmp = test_data.vec_regs.get_register(lmul=int(max(params.lmul, 1)))
    except ValueError:
        if clobber_vd:
            assert params.vd is not None, "vd is required for all vector operations"
            alignment = int(max(params.lmul, 1))
            if params.vd % alignment == 0:
                vtmp = params.vd
                clobbered_vd = True
            else:
                raise ValueError("Not Enough Free Registers to Allocate LMUL-Aligned vtmp For Mask Calculation")
        else:
            raise ValueError(
                "Not Enough Free Registers to Allocate LMUL-Aligned vtmp For Mask Calculation. Try passing clobber_vd=True"
            )

    lines: list[str] = []
    if mask_val == PresetMask.ZEROS:
        lines = [
            f"# Set mask value to zero, x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m1, tu, mu",
            "vmv.v.i v0, 0",
        ]
    elif mask_val == PresetMask.ONES:
        # Note that an approach using temp_reg is flawed because vmsltu can be tail agnostic regardless of vtype
        lines = [
            f"# Set mask value to one, x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m1, tu, mu",
            "# Sign extension makes the vector all ones",
            "vmv.v.i v0, -1",
        ]
    elif mask_val == PresetMask.VLMAX_M1_ONES:
        assert params.temp_reg is not None
        lines = [
            f"# x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{lmul_flag}, tu, mu",
            f"# x{params.temp_reg} = VLMAX - 1",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -1",
            *set_lower_xreg_bits(params.temp_reg, test_data),
        ]
    elif mask_val == PresetMask.VLMAX_D2_P1_ONES:
        assert params.temp_reg is not None
        lines = [
            f"# x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{lmul_flag}, tu, mu",
            f"# x{params.temp_reg} = VLMAX / 2",
            f"srli x{params.temp_reg}, x{params.temp_reg}, 1",
            f"# x{params.temp_reg} = VLMAX / 2 + 1",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 1",
            *set_lower_xreg_bits(params.temp_reg, test_data),
        ]
    else:  # random mask
        lines = [
            f"# x{params.temp_reg} = VLEN",
            f"vsetvli x{params.temp_reg}, x0, e8, m8, tu, mu",
            f"LA(x{params.temp_reg}, {mask_val})",
            "# Load mask value into v0",
            f"vlm.v v0, (x{params.temp_reg})",
        ]

        assert test_data.test_chunk is not None, "Test chunk must be set to prepare mask asm"
        test_data.test_chunk.vector_labels.append((mask_val, *test_data.vector_labels[mask_val]))

    if not clobbered_vd:
        test_data.vec_regs.return_register(vtmp)

    return lines


def load_vxrm(vxrm: str) -> list[str]:
    """
    Generates the instructions to load an individual vxrm.
    """
    vxrm_set_map = {"rod": "0x6", "rdn": "0x4", "rne": "0x2", "rnu": "0x0"}
    return [
        f"# Clear vxrm and vcsr, then set vxrm = {vxrm}",
        "csrci vcsr, 0x6",
        f"csrsi vcsr, {vxrm_set_map[vxrm]}",
    ]


def write_sigupd_vxsat(test_data: TestData) -> list[str]:
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"

    test_data.test_chunk.sigupd_count += 1

    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    label = test_data.current_testcase_label

    return [
        "# Run SIGUPD to see if vxsat was correctly set",
        f"RVTEST_SIGUPD_VXSAT(x{sig_reg}, x{link_reg}, x{temp_reg}, {label}, {label}_str)",
    ]


@dataclass
class VectorLoad:
    """
    Dataclass holding data about a vector load:

    Required:
        reg: Register name for the load

    Optional:
        widen: If true, SEW and LMUL are doubled for the load
        vl: Provides an override value for params.vl
        lmul: Provides an override value for params.lmul
        sew: Provides an override value for params.sew
        no_fractional_load: If true, all loads must be at integer lmuls
    """

    reg: Literal["vd", "vs1", "vs2", "vs3"]
    widen: bool = False
    vl: int | Literal["vlmax", "random"] | None = None
    lmul: int | float | None = None
    sew: int | float | None = None
    no_fractional_load: bool = False


def unpack_register(reg: Literal["vd", "vs1", "vs2", "vs3"], params: InstructionParams) -> tuple[int, str]:
    match reg:
        case "vd":
            assert params.vd is not None and params.vd_val_pointer is not None, "vd and vd_val_pointer must be provided"
            return (params.vd, params.vd_val_pointer)
        case "vs1":
            assert params.vs1 is not None and params.vs1_val_pointer is not None, (
                "vs1 and vs1_val_pointer must be provided"
            )
            return (params.vs1, params.vs1_val_pointer)
        case "vs2":
            assert params.vs2 is not None and params.vs2_val_pointer is not None, (
                "vs2 and vs2_val_pointer must be provided"
            )
            return (params.vs2, params.vs2_val_pointer)
        case "vs3":
            assert params.vs3 is not None and params.vs3_val_pointer is not None, (
                "vs3 and vs3_val_pointer must be provided"
            )
            return (params.vs3, params.vs3_val_pointer)


def generate_random_vl(params: InstructionParams, test_data: TestData) -> tuple[list[str], str]:
    assert params.lmul is not None, "LMUL must be set for vector operations"

    code = []

    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    randomVl = random_int(32, signed=False)
    code.extend(
        [
            "# Load vl=random",
            f"LI(x{temp_reg}, {randomVl})",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{_lmul_flag(params.lmul)}, tu, mu",
            f"remu x{temp_reg}, x{temp_reg}, x{params.temp_reg}",
        ]
    )

    if params.egs != 1 and params.egs is not None:
        raise NotImplementedError("Handle egs != 1 vl=random")
    else:
        code.append(f"ori x{temp_reg}, x{temp_reg}, 0x2")

    return code, f"x{temp_reg}"


def load_test_vtype(params: InstructionParams, random_vl_reg: str, *, force_vlmax: bool = False) -> str:
    assert params.lmul is not None, "params.lmul must be set for a vector test"
    lmul_flag = "m" + _lmul_flag(params.lmul)

    mask_flags = ""
    mask_flags += ", ta" if params.ta else ", tu"
    mask_flags += ", ma" if params.ma else ", mu"

    flags = lmul_flag + mask_flags

    if params.vl == "vlmax" or force_vlmax:
        return f"vsetvli x{params.temp_reg}, x0, e{params.sew}, {flags}"
    elif params.vl == "random":
        return f"vsetvli x{params.temp_reg}, {random_vl_reg}, e{params.sew}, {flags}"
    else:
        return f"vsetivli x{params.temp_reg}, {params.vl}, e{params.sew}, {flags}"


def load_vec_regs(regs: list[VectorLoad], params: InstructionParams, test_data: TestData) -> tuple[list[str], str]:
    """
    Loads the vector registers in regs according to their configuration, given default values from
    params.
    """

    vtype_code: defaultdict[tuple[Literal["vlmax", "random"] | int, int | float, int | float], list[str]] = defaultdict(
        list
    )

    for reg in regs:
        # What needs to happen for a load: Either the tail needs to be deterministically loaded, then the register needs to be loaded at vl
        # or it needs to be loaded at vlmax

        reg_num, val_pointer = unpack_register(reg.reg, params)

        vl = params.vl if reg.vl is None else reg.vl
        assert vl is not None, "vl must be provided either through VectorLoad.vl or params.vl for load_vec_regs"

        sew = params.sew if reg.sew is None else reg.sew
        assert sew is not None, "sew must be provided either through VectorLoad.sew or params.sew for load_vec_regs"

        lmul = params.lmul if reg.lmul is None else reg.lmul
        assert lmul is not None, "lmul must be provided either through VectorLoad.lmul or params.lmul for load_vec_regs"

        if reg.widen:
            sew *= 2
            lmul *= 2

        if reg.no_fractional_load:
            lmul = max(lmul, 1)

        # Load what is required at the right vl
        vtype_code[(vl, sew, lmul)].extend(
            [
                f"LA (x{params.temp_reg}, {val_pointer})",
                f"vle{sew}.v v{reg_num}, (x{params.temp_reg})",
            ]
        )

        if vl != "vlmax":
            # Create a deterministic tail at vlmax
            vtype_code[("vlmax", sew, max(lmul, 1))].append(
                f"vmv.v.i v{reg_num}, 0xd",
            )

    code: list[str] = []
    # First handle everything at vlmax
    vlmax_vtypes = [vtype for vtype in vtype_code if vtype[0] == "vlmax"]
    for vl, sew, lmul in vlmax_vtypes:
        code.append(
            f"vsetvli x{params.temp_reg}, x0, e{sew}, m{_lmul_flag(lmul)}, tu, mu",
        )
        code.extend(vtype_code[(vl, sew, lmul)])

    # Then handle a random vl
    random_vtypes = [vtype for vtype in vtype_code if vtype[0] == "random"]

    random_vl_reg = ""
    if len(random_vtypes) != 0 or params.vl == "random":
        random_code, random_vl_reg = generate_random_vl(params, test_data)
        code.extend(random_code)

    for vl, sew, lmul in random_vtypes:
        code.append(
            f"vsetvli x{params.temp_reg}, {random_vl_reg}, e{sew}, m{_lmul_flag(lmul)}, tu, mu",
        )
        code.extend(vtype_code[(vl, sew, lmul)])

    # Now integer vls
    integer_vtypes = [vtype for vtype in vtype_code if isinstance(vtype[0], int)]
    for vl, sew, lmul in integer_vtypes:
        code.append(
            f"vsetivli x{params.temp_reg}, {vl}, e{sew}, m{_lmul_flag(lmul)}, tu, mu",
        )
        code.extend(vtype_code[(vl, sew, lmul)])

    return code, random_vl_reg


def handle_lmul_ifdef(lmul: float, setup: list[str], check: list[str]) -> None:
    """
    Modifies setup and check in place to ensure that the test is only run if the lmul is supported.
    """

    match lmul:
        case 0.5:
            setup.insert(0, "#ifdef TEST_LMULf2_SUPPORTED")
            check.append("#endif")
        case 0.25:
            setup.insert(0, "#ifdef TEST_LMULf4_SUPPORTED")
            check.append("#endif")
        case 0.125:
            setup.insert(0, "#ifdef TEST_LMULf8_SUPPORTED")
            check.append("#endif")
