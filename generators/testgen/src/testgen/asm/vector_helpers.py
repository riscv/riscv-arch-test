##################################
# asm/vector_helpers.py
#
# Assembly generation helpers for vector tests
# rwolk@hmc.edu 17 July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

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


def load_vec_reg(
    register: int,
    val_pointer: str,
    params: InstructionParams,
    *,
    sew_override: int | None = None,
    lmul: float | None = None,
    vl_register_or_imm: str | int | None = None,
) -> list[str]:
    """
    Load a vector register.

    Args:
        register: The number register to load
        val_pointer: A string that points to a label where the load data exists
        params: The InstructionParams generated for this instruction. Gives data about default sew and lmul

    Optional Args:
        sew_override: If we are loading at a different sew than the instruction sew (e.g. vrgatherei16), the load
            sew is provided so that an additional vsetvli instruction can be generated to load at the right sew.
        lmul: If the load lmul is not the default lmul, it is provided here and an additional vsetvli will be
            generated so the load happens at the appropriate lmul
        vl_register_or_imm: Either a register containing vl or vl as an immediate. Used to specify what vl to use
            when lmul changes or other special cases.
    """
    lines = []

    sew = params.sew if sew_override is None else sew_override

    # Preloads Require Special Handling for V
    if lmul is not None and vl_register_or_imm is None:
        lines.append(f"vsetvli x{params.temp_reg}, x0, e{sew}, m{_lmul_flag(lmul)}, tu, mu")
    elif lmul is not None:
        if isinstance(vl_register_or_imm, str):
            lines.append(f"vsetvli x{params.temp_reg}, {vl_register_or_imm}, e{sew}, m{_lmul_flag(lmul)}, tu, mu")
        else:
            lines.append(f"vsetivli x{params.temp_reg}, {vl_register_or_imm}, e{sew}, m{_lmul_flag(lmul)}, tu, mu")

    lines.extend(
        [
            f"LA(x{params.temp_reg}, {val_pointer})",
            f"vle{sew}.v v{register}, (x{params.temp_reg})",
        ]
    )

    return lines


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
    emul_for_bytes = int(max(1, lmul))
    max_bytes = VLEN_MAX * emul_for_bytes // 8
    test_data.test_chunk.sigupd_count += vector_sigupd_bytes(max_bytes, test_data, vdsew)

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
    assert params.sew is not None, "SEW must be set for vector tests"
    assert params.lmul is not None, "LMUL must be set for vector tests"
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"

    # We cannot consider only taking an eew=1 worth of bytes here due to the way RVTEST_SIGUPD_V_ADVANCE works
    emul_for_bytes = int(params.lmul) if params.lmul is not None and params.lmul >= 1 else 1
    worst_bytes = VLEN_MAX * emul_for_bytes // 8
    sig_stride = max(test_data.xlen, test_data.flen, params.sew) // 8
    offset_bytes = (worst_bytes + 4 + 7) & ~7
    test_data.test_chunk.sigupd_count += max(1, (offset_bytes + sig_stride - 1) // sig_stride)

    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg

    return [
        "# RVTEST_SIGUPD_VLMAX_MASK_PROD(_SIG_PTR, _LINK_REG, _TEMP_REG, _VR, _VD_EEW, _LMUL)",
        f"RVTEST_SIGUPD_VLMAX_MASK_PROD(x{sig_reg}, x{link_reg}, x{temp_reg}, v{params.vd}, {params.sew}, 1)",
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
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{lmul_flag}, tu, mu",
            "vmv.v.i v0, 0",
        ]
    elif mask_val == PresetMask.ONES:
        # Note that an approach using temp_reg is flawed because vmsltu can be tail agnostic regardless of vtype
        lines = [
            f"# Set mask value to one, x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{lmul_flag}, tu, mu",
            "# Sign extension makes the vector all ones",
            "vmv.v.i v0, -1",
        ]
    elif mask_val == PresetMask.VLMAX_M1_ONES:
        lines = [
            f"# x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{lmul_flag}, tu, mu",
            f"# x{params.temp_reg} = VLMAX - 1",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -1",
            f"# v{vtmp} = [0,1,2,...]",
            f"vid.v v{vtmp}",
            "# Reset mask value to 0",
            "vmv.v.i v0, 0",
            "# v0[i] = (i < VLMAX-1) ? 1 : 0",
            f"vmsltu.vx v0, v{vtmp}, x{params.temp_reg}",
        ]
    elif mask_val == PresetMask.VLMAX_D2_P1_ONES:
        lines = [
            f"# x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{lmul_flag}, tu, mu",
            f"# x{params.temp_reg} = VLMAX / 2",
            f"srli x{params.temp_reg}, x{params.temp_reg}, 1",
            f"# x{params.temp_reg} = VLMAX / 2 + 1",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 1",
            f"# v{vtmp} = [0,1,2,...]",
            f"vid.v v{vtmp}",
            "# Reset mask value to 0",
            "vmv.v.i v0, 0",
            "# v0[i] = (i < VLMAX/2+1) ? 1 : 0",
            f"vmsltu.vx v0, v{vtmp}, x{params.temp_reg}",
        ]
    else:  # random mask
        lines = [
            f"# x{params.temp_reg} = VLMAX",
            f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{lmul_flag}, tu, mu",
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
