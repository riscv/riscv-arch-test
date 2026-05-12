"""Generators for MisalignedV LS misaligned coverpoints.

Implements:

- ``cp_misalignedv_ls_element_misaligned`` — element LS with base address
  whose low bits are non-zero.
- ``cp_misalignedv_ls_wholereg_misaligned`` — whole-register LS
  (vl<NF>r<EEW>.v / vs<NF>r.v) with misaligned base address.

Self-contained: copies the small set of helpers it needs from the (not yet
upstreamed) SsstrictV helper module so the MisalignedV PR does not depend
on SsstrictV.
"""

from __future__ import annotations

from random import seed as set_seed
from typing import Iterable

import vector_testgen_common as common
from priv_coverpoint_registry import register


def _emit_vsetvli_str(scratch: int, vl: int, sew: int, lmul_flag: str) -> None:
    """Emit ``vsetivli`` with an arbitrary LMUL flag string (supports ``mf*``)."""
    common.writeLine(
        f"vsetivli x{scratch}, {vl}, e{sew}, {lmul_flag}, tu, mu",
        f"# vill=0, vstart=0, vl={vl}, sew={sew}, lmul={lmul_flag}",
    )


def _init_operand_regs(instruction: str, vec_data: dict, sew: int, scratch: int,
                       *, regs: Iterable[str] = ("vd", "vs2", "vs3"),
                       label: str = "random_mask_0") -> None:
    """Initialize operand vector registers that exist in the instruction's signature."""
    args = common.getInstructionArguments(instruction)
    common.writeLine(f"la x{scratch}, {label}", f"# scratch <- &{label}")
    for r in regs:
        if r in args and r in vec_data:
            reg = vec_data[r]["reg"]
            common.writeLine(f"vle{sew}.v v{reg}, (x{scratch})", f"# init {r} (v{reg})")


def _build_testline(instruction: str, instruction_data: list, *,
                    maskval: str | None = None,
                    override_vd: int | None = None,
                    addr_label: str = "random_mask_0") -> tuple[str, int, int]:
    """Build the assembly mnemonic line. Returns (testline, vd_reg, rd_reg)."""
    args = common.getInstructionArguments(instruction)
    vec_data, scalar_data, fp_data, imm_val = instruction_data

    if override_vd is not None:
        vec_data["vd"]["reg"] = override_vd

    testline = instruction + " "
    for arg in args:
        if arg == "vm":
            if maskval is not None:
                testline += "v0.t"
            else:
                testline = testline[:-2]
        elif arg == "v0":
            testline += "v0"
        elif arg == "imm":
            testline += f"{imm_val}"
        elif arg[0] == "v":
            testline += f"v{vec_data[arg]['reg']}"
        elif arg[0] == "r":
            reg = scalar_data[arg]["reg"]
            if arg == "rs1" and instruction in common.vector_ls_ins:
                common.writeLine(f"la x{reg}, {addr_label}", "# rs1 = valid memory address")
                testline += f"(x{reg})"
            else:
                if reg not in common.PRIV_RESERVED_SCALAR_REGS:
                    common.loadScalarReg(arg, scalar_data)
                testline += f"x{reg}"
        elif arg[0] == "f":
            testline += f"f{fp_data[arg]['reg']}"
        else:
            raise TypeError(f"Unsupported argument type: '{arg}'")
        testline += ", "

    testline = testline[:-2]
    vd = vec_data["vd"]["reg"]
    rd = scalar_data["rd"]["reg"]
    return testline, vd, rd


def _ls_test(instruction: str, cp: str, sew: int, lmul_flag: str, *,
             vl: int = 1,
             override_vd: int | None = None,
             addr_offset: int = 0) -> None:
    """Run one LS test with the given vsetivli + optional address offset."""
    set_seed(common.myhash(instruction + cp + lmul_flag + str(addr_offset) + str(override_vd)))

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {cp} (sew={sew}, lmul={lmul_flag}, vd_off={override_vd}, addr_off={addr_offset})")
    scratch = common.pickPrivScratch(instruction_data[1])

    _emit_vsetvli_str(scratch, vl=vl, sew=sew, lmul_flag=lmul_flag)
    _init_operand_regs(instruction, instruction_data[0], sew, scratch, regs=("vs2", "vs3"))
    _emit_vsetvli_str(scratch, vl=vl, sew=sew, lmul_flag=lmul_flag)

    rs1_reg = None
    if addr_offset:
        rs1_reg = instruction_data[1]["rs1"]["reg"]
    addr_label = "random_mask_0"

    overrides: dict = {}
    if override_vd is not None:
        overrides["override_vd"] = override_vd

    testline, vd, rd = _build_testline(instruction, instruction_data,
                                       addr_label=addr_label, **overrides)

    if addr_offset and rs1_reg is not None:
        common.writeLine(f"addi x{rs1_reg}, x{rs1_reg}, {addr_offset}",
                          f"# misalign rs1 by {addr_offset} bytes")

    common.add_testcase_string(cp, instruction)
    common.writeVecTest(
        instruction, cp, vd, sew, testline,
        test=instruction, rd=rd, vl=vl, lmul=1,
        sig_lmul=1, sig_whole_register_store=True,
        priv=True, skip_sigupd=True,
    )


def _eew(instruction: str) -> int:
    return common.getInstructionEEW(instruction) or 8


# ---------------- ls_element_misaligned ----------------

@register("cp_misalignedv_ls_element_misaligned")
def make_element_misaligned(instruction: str) -> None:
    if instruction not in common.vector_ls_ins:
        return
    eew = _eew(instruction)
    sew = eew if eew else 8
    for off in range(1, 8):
        _ls_test(instruction, "cp_misalignedv_ls_element_misaligned",
                  sew=sew, lmul_flag="m1", addr_offset=off)


# ---------------- ls_wholereg_misaligned ----------------

@register("cp_misalignedv_ls_wholereg_misaligned")
def make_wholereg_misaligned(instruction: str) -> None:
    if instruction not in common.whole_register_ls:
        return
    eew = _eew(instruction)
    sew = eew if eew else 8
    for off in range(1, 8):
        _ls_test(instruction, "cp_misalignedv_ls_wholereg_misaligned",
                  sew=sew, lmul_flag="m1", addr_offset=off)
