##################################
# priv/extensions/SmV.py
#
# SmV privileged test generator.
# Vector CSR access, vsetvl* behavior, vill, vstart, mstatus.VS, misa.V.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SmV privileged test generator: vector CSRs and vtype/vl/vstart behavior in M-mode."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_CG = "SmV_cg"

_VS_MASK = 3 << 9  # mstatus.VS = bits [10:9]


def _set_vs(vs: int, temp_reg: int) -> list[str]:
    """Force mstatus.VS=vs (0..3)."""
    return [
        f"LI(x{temp_reg}, {_VS_MASK})",
        f"CSRC(mstatus, x{temp_reg})  # clear VS",
        f"LI(x{temp_reg}, {vs << 9})",
        f"CSRS(mstatus, x{temp_reg})  # VS={vs}",
    ]


def _vector_setup(temp_reg: int) -> list[str]:
    """Configure a legal vtype/vl (SEW=8, LMUL=1, vl=1) and clear vstart."""
    return [
        f"vsetivli x{temp_reg}, 1, e8, m1, tu, mu  # vill=0, vl=1",
        "csrw vstart, x0",
    ]


# All 7 vector CSRs (writable + read-only)
_VECTOR_CSRS = ("vstart", "vxsat", "vxrm", "vcsr", "vl", "vtype", "vlenb")
# Writable subset (used for walking-1s)
_VECTOR_CSRS_WR = ("vstart", "vxsat", "vxrm", "vcsr")


def _gen_vcsrrswc(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vcsrrswc: csrrs/csrrc/csrrw against each of the 7 vector CSRs."""
    coverpoint = "cp_vcsrrswc"
    lines = [
        comment_banner(
            coverpoint, "csrrs/csrrc/csrrw against each vector CSR (vstart, vxsat, vxrm, vcsr, vl, vtype, vlenb)"
        ),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    save_reg = test_data.int_regs.get_register()
    lines.append(f"LI(x{save_reg}, -1)  # all 1s mask for csr ops")
    for csr in _VECTOR_CSRS:
        for op_name, op in (("csrrs", "CSRS"), ("csrrc", "CSRC"), ("csrrw", "CSRW")):
            lines.append(test_data.add_testcase(f"{csr}_{op_name}", coverpoint, _CG))
            lines.append(f"{op}({csr}, x{save_reg})  # {op_name} {csr}")
            lines.append("nop")
    test_data.int_regs.return_registers([save_reg])
    return lines


def _gen_vcsrs_walking1s(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vcsrs_walking1s: csrrw with walking-1s rs1 against each writable vector CSR."""
    coverpoint = "cp_vcsrs_walking1s"
    lines = [
        comment_banner(
            coverpoint, "csrrw walking-1s into vstart/vxsat/vxrm/vcsr (covers walking_ones_rs1 bins 0..XLEN-1)"
        ),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    walk_reg, mask_reg = test_data.int_regs.get_registers(2)
    for csr in _VECTOR_CSRS_WR:
        lines.append(f"# walking-1s on {csr}")
        lines.append(f"LI(x{mask_reg}, -1)  # all 1s")
        lines.append(f"LI(x{walk_reg}, 1)   # one-hot starting at bit 0")
        # We need to walk all XLEN bits; emit for both 32 and 64 via #if
        lines.append(".rept __riscv_xlen")
        # Note: .rept doesn't access __riscv_xlen as a number; emit per-bit explicitly with #if guard
        lines.append(".endr")
    # Replace the .rept stub with explicit unroll: emit bit-by-bit with #if for RV64 high bits
    lines = lines[
        : lines.index(
            comment_banner(
                coverpoint, "csrrw walking-1s into vstart/vxsat/vxrm/vcsr (covers walking_ones_rs1 bins 0..XLEN-1)"
            )
        )
        + 1
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    for csr in _VECTOR_CSRS_WR:
        lines.append(f"# walking-1s on {csr}")
        lines.append(f"LI(x{mask_reg}, -1)  # all 1s")
        lines.append(f"LI(x{walk_reg}, 1)   # one-hot starting at bit 0")
        for i in range(32):
            lines.append(f"CSRC({csr}, x{mask_reg})  # clear all bits")
            lines.append(test_data.add_testcase(f"{csr}_bit_{i}", coverpoint, _CG))
            lines.append(f"CSRW({csr}, x{walk_reg})  # walking-1 bit {i}")
            lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")
        lines.append("#if __riscv_xlen == 64")
        for i in range(32, 64):
            lines.append(f"CSRC({csr}, x{mask_reg})  # clear all bits")
            lines.append(test_data.add_testcase(f"{csr}_bit_{i}", coverpoint, _CG))
            lines.append(f"CSRW({csr}, x{walk_reg})  # walking-1 bit {i}")
            lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")
        lines.append("#endif")
    test_data.int_regs.return_registers([walk_reg, mask_reg])
    return lines


def _gen_mstatus_vs_dirty(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_mstatus_vs_set_dirty_arithmetic / cp_mstatus_vs_set_dirty_csr."""
    lines = [
        comment_banner(
            "cp_mstatus_vs_set_dirty_arithmetic",
            "VS=Initial(1)/Clean(2) -> vadd.vv -> expect Dirty",
        ),
    ]
    for vs in (1, 2):
        lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
        lines.extend(_vector_setup(temp_reg))
        lines.append("vmv.v.i v1, 1")
        lines.append("vmv.v.i v2, 2")
        lines.extend(_set_vs(vs=vs, temp_reg=temp_reg))
        lines.append(test_data.add_testcase(f"vadd_vs{vs}", "cp_mstatus_vs_set_dirty_arithmetic", _CG))
        lines.append("vadd.vv v3, v1, v2")
        lines.append("nop")

    lines.append(comment_banner("cp_mstatus_vs_set_dirty_csr", "VS=Initial/Clean -> vsetvli -> expect Dirty"))
    for vs in (1, 2):
        lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
        lines.extend(_vector_setup(temp_reg))
        lines.extend(_set_vs(vs=vs, temp_reg=temp_reg))
        lines.append(test_data.add_testcase(f"vsetvli_vs{vs}", "cp_mstatus_vs_set_dirty_csr", _CG))
        lines.append(f"vsetvli x{temp_reg}, x0, e16, m2, tu, mu")
        lines.append("nop")
    return lines


def _gen_mstatus_vs_off(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_mstatus_vs_off_arithmetic / cp_mstatus_vs_off_csr — both should trap."""
    lines = [
        comment_banner(
            "cp_mstatus_vs_off_arithmetic",
            "VS=Off + misa.V active -> vector arithmetic traps illegal-instruction",
        ),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    lines.append("vmv.v.i v1, 1")
    lines.append("vmv.v.i v2, 2")
    # Ensure misa.V set (best effort)
    lines.append(f"LI(x{temp_reg}, 0x200000)  # misa.V mask")
    lines.append(f"CSRS(misa, x{temp_reg})    # set misa.V if writable")
    lines.extend(_set_vs(vs=0, temp_reg=temp_reg))
    lines.append(test_data.add_testcase("vadd_vs_off", "cp_mstatus_vs_off_arithmetic", _CG))
    lines.append("vadd.vv v3, v1, v2  # traps: VS=Off")
    lines.append("nop")
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))

    lines.append(comment_banner("cp_mstatus_vs_off_csr", "VS=Off -> vsetvli traps illegal-instruction"))
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    lines.append(f"LI(x{temp_reg}, 0x200000)")
    lines.append(f"CSRS(misa, x{temp_reg})")
    lines.extend(_set_vs(vs=0, temp_reg=temp_reg))
    lines.append(test_data.add_testcase("vsetvli_vs_off", "cp_mstatus_vs_off_csr", _CG))
    lines.append(f"vsetvli x{temp_reg}, x0, e8, m1, tu, mu  # traps: VS=Off")
    lines.append("nop")
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    return lines


def _gen_misa_v(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_misa_v_clear_set: csrrs/csrrc misa with rs1[21]=1."""
    coverpoint = "cp_misa_v_clear_set"
    lines = [
        comment_banner(coverpoint, "csrrs/csrrc misa with rs1[21]=1 to attempt to clear/set V"),
    ]
    lines.append(f"LI(x{temp_reg}, 0x200000)  # misa.V")
    lines.append(test_data.add_testcase("misa_v_csrrc", coverpoint, _CG))
    lines.append(f"CSRC(misa, x{temp_reg})")
    lines.append(test_data.add_testcase("misa_v_csrrs", coverpoint, _CG))
    lines.append(f"CSRS(misa, x{temp_reg})")
    lines.append("nop")
    return lines


# All (sew, lmul) combinations matching the coverage definition
# sew encoding: 000=8, 001=16, 010=32, 011=64
# lmul encoding: 000=1, 001=2, 010=4, 011=8, 101=1/8, 110=1/4, 111=1/2 (100=reserved)
_SEW_VALUES = (("e8", 0), ("e16", 1), ("e32", 2), ("e64", 3))
_LMUL_VALUES = (("m1", 0), ("m2", 1), ("m4", 2), ("m8", 3), ("mf8", 5), ("mf4", 6), ("mf2", 7))


def _gen_sew_lmul_vsetvl(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_sew_lmul_vsetvl: vsetvl over all (sew, lmul) pairs via rs2."""
    coverpoint = "cp_sew_lmul_vsetvl"
    lines = [
        comment_banner(coverpoint, "vsetvl over all (sew, lmul) pairs via rs2"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg, rs2_reg = test_data.int_regs.get_registers(2)
    lines.append(f"LI(x{rs1_reg}, 1)  # vl = 1")
    for sew_name, sew_v in _SEW_VALUES:
        for lmul_name, lmul_v in _LMUL_VALUES:
            vtype = (sew_v << 3) | lmul_v
            lines.append(f"LI(x{rs2_reg}, 0x{vtype:02x})  # SEW={sew_name}, LMUL={lmul_name}")
            lines.append(test_data.add_testcase(f"vsetvl_{sew_name}_{lmul_name}", coverpoint, _CG))
            lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
    test_data.int_regs.return_registers([rs1_reg, rs2_reg])
    return lines


def _gen_sew_lmul_vset_i_vli(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_sew_lmul_vset_i_vli: vsetvli/vsetivli over all (sew, lmul) immediate combos."""
    coverpoint = "cp_sew_lmul_vset_i_vli"
    lines = [
        comment_banner(coverpoint, "vsetvli/vsetivli over all (sew, lmul) immediate combos"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg = test_data.int_regs.get_register()
    lines.append(f"LI(x{rs1_reg}, 1)  # vl = 1")
    for sew_name, _ in _SEW_VALUES:
        for lmul_name, _ in _LMUL_VALUES:
            lines.append(test_data.add_testcase(f"vsetvli_{sew_name}_{lmul_name}", coverpoint, _CG))
            lines.append(f"vsetvli x{temp_reg}, x{rs1_reg}, {sew_name}, {lmul_name}, tu, mu")
            lines.append(test_data.add_testcase(f"vsetivli_{sew_name}_{lmul_name}", coverpoint, _CG))
            lines.append(f"vsetivli x{temp_reg}, 1, {sew_name}, {lmul_name}, tu, mu")
    test_data.int_regs.return_registers([rs1_reg])
    return lines


def _gen_vill_vsetvl(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vill_vsetvl: vsetvl from vill=1 with each supported sew, lmul=8."""
    coverpoint = "cp_vill_vsetvl"
    lines = [
        comment_banner(coverpoint, "vsetvl from vill=1 with each supported sew, lmul=8"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg, rs2_reg = test_data.int_regs.get_registers(2)
    lines.append(f"LI(x{rs1_reg}, 1)")
    for sew_name, sew_v in _SEW_VALUES:
        # set vill via illegal vtype (SEW=64, LMUL=1/8 -> 0x1D)
        lines.append(f"LI(x{rs2_reg}, 0x1D)  # illegal vtype to set vill")
        lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
        # now vsetvl with desired sew, lmul=8
        vtype = (sew_v << 3) | 0b011  # lmul=8
        lines.append(f"LI(x{rs2_reg}, 0x{vtype:02x})  # SEW={sew_name}, LMUL=8")
        lines.append(test_data.add_testcase(f"vill_vsetvl_{sew_name}", coverpoint, _CG))
        lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
    test_data.int_regs.return_registers([rs1_reg, rs2_reg])
    return lines


def _gen_vill_vset_i_vli(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vill_vset_i_vli: vsetvli/vsetivli from vill=1 with each supported sew, lmul=8."""
    coverpoint = "cp_vill_vset_i_vli"
    lines = [
        comment_banner(coverpoint, "vsetvli/vsetivli from vill=1 with each supported sew, lmul=8"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg, rs2_reg = test_data.int_regs.get_registers(2)
    lines.append(f"LI(x{rs1_reg}, 1)")
    for sew_name, _ in _SEW_VALUES:
        # set vill
        lines.append(f"LI(x{rs2_reg}, 0x1D)  # illegal vtype to set vill")
        lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
        lines.append(test_data.add_testcase(f"vill_vsetvli_{sew_name}", coverpoint, _CG))
        lines.append(f"vsetvli x{temp_reg}, x{rs1_reg}, {sew_name}, m8, tu, mu")
        # set vill again
        lines.append(f"LI(x{rs2_reg}, 0x1D)")
        lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
        lines.append(test_data.add_testcase(f"vill_vsetivli_{sew_name}", coverpoint, _CG))
        lines.append(f"vsetivli x{temp_reg}, 1, {sew_name}, m8, tu, mu")
    test_data.int_regs.return_registers([rs1_reg, rs2_reg])
    return lines


def _gen_vill_vsetvl_rs2_vill(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vill_vsetvl_rs2_vill: vsetvl with rs2[XLEN-1]=1 starting from vill=1."""
    coverpoint = "cp_vill_vsetvl_rs2_vill"
    lines = [
        comment_banner(coverpoint, "vsetvl with rs2[XLEN-1]=1 + valid lower bits, starting from vill=1"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg, rs2_reg, msb_reg = test_data.int_regs.get_registers(3)
    lines.append(f"LI(x{rs1_reg}, 1)")
    lines.append("#if __riscv_xlen == 32")
    lines.append(f"LI(x{msb_reg}, 0x80000000)")
    lines.append("#else")
    lines.append(f"LI(x{msb_reg}, 0x8000000000000000)")
    lines.append("#endif")
    for sew_name, sew_v in _SEW_VALUES:
        # set vill first
        lines.append(f"LI(x{rs2_reg}, 0x1D)")
        lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
        # rs2[XLEN-1]=1 + valid sew/lmul=8
        vtype_low = (sew_v << 3) | 0b011
        lines.append(f"LI(x{rs2_reg}, 0x{vtype_low:02x})")
        lines.append(f"or x{rs2_reg}, x{rs2_reg}, x{msb_reg}  # set MSB")
        lines.append(test_data.add_testcase(f"vill_rs2_vill_{sew_name}", coverpoint, _CG))
        lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
    test_data.int_regs.return_registers([rs1_reg, rs2_reg, msb_reg])
    return lines


def _gen_vsetvl_rs2_vill(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vsetvl_rs2_vill: vsetvl with rs2[XLEN-1]=1 + lmul=1, supported sew, vill_prev=0."""
    coverpoint = "cp_vsetvl_rs2_vill"
    lines = [
        comment_banner(coverpoint, "vsetvl with rs2 vill bit set + valid (sew, lmul=1), starting from vill=0"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg, rs2_reg, msb_reg = test_data.int_regs.get_registers(3)
    lines.append(f"LI(x{rs1_reg}, 1)")
    lines.append("#if __riscv_xlen == 32")
    lines.append(f"LI(x{msb_reg}, 0x80000000)")
    lines.append("#else")
    lines.append(f"LI(x{msb_reg}, 0x8000000000000000)")
    lines.append("#endif")
    for sew_name, sew_v in _SEW_VALUES:
        # clear vill: try every supported sew with lmul=1 to find one that sticks
        for try_sew in (0, 1, 2, 3):
            vt = try_sew << 3
            lines.append(f"LI(x{rs2_reg}, 0x{vt:02x})  # try clear vill with SEW={try_sew}")
            lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
        # Now vsetvl with rs2_vill_set + valid sew+lmul=1
        vtype_low = sew_v << 3
        lines.append(f"LI(x{rs2_reg}, 0x{vtype_low:02x})")
        lines.append(f"or x{rs2_reg}, x{rs2_reg}, x{msb_reg}  # set MSB (vill bit in rs2)")
        lines.append(test_data.add_testcase(f"rs2_vill_{sew_name}", coverpoint, _CG))
        lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")
    test_data.int_regs.return_registers([rs1_reg, rs2_reg, msb_reg])
    return lines


def _gen_vtype_vill_set_vl_0(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vtype_vill_set_vl_0: vsetvl with rs2 vill bit set; expect vl=0."""
    coverpoint = "cp_vtype_vill_set_vl_0"
    lines = [
        comment_banner(coverpoint, "vsetvl with rs2 vill bit set (rs1!=0 nonzero AVL); expect vl=0"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))  # ensure vl != 0 before
    rs1_reg, rs2_reg = test_data.int_regs.get_registers(2)
    lines.append(f"LI(x{rs1_reg}, 1)  # nonzero AVL")
    lines.append("#if __riscv_xlen == 32")
    lines.append(f"LI(x{rs2_reg}, 0x80000000)")
    lines.append("#else")
    lines.append(f"LI(x{rs2_reg}, 0x8000000000000000)")
    lines.append("#endif")
    lines.append(test_data.add_testcase("vill_set_vl_0", coverpoint, _CG))
    lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}  # rs2 vill set -> vl=0")
    test_data.int_regs.return_registers([rs1_reg, rs2_reg])
    return lines


def _gen_vsetvl_i_rd_rs1(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vsetvl_i_rd_nx0_rs1_x0 and cp_vsetvl_i_rd_x0_rs1_x0."""
    cp1 = "cp_vsetvl_i_rd_nx0_rs1_x0"
    cp2 = "cp_vsetvl_i_rd_x0_rs1_x0"
    lines = [
        comment_banner(cp1, "vsetvli/vsetvl with rs1=x0, rd!=x0 over all (sew, lmul) combos"),
    ]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs2_reg = test_data.int_regs.get_register()
    # First, ensure vl != vlmax for the new config: load a small vl, then run with rs1=x0 to set vl=vlmax
    for sew_name, sew_v in _SEW_VALUES:
        for lmul_name, lmul_v in _LMUL_VALUES:
            # Force vl != vlmax: set vl=1 with the same SEW/LMUL ratio first using vsetivli imm=1
            lines.append(f"vsetivli x{temp_reg}, 1, {sew_name}, {lmul_name}, tu, mu  # set vl=1")
            # vsetvli with rs1=x0, rd!=x0 -> vl=vlmax
            lines.append(test_data.add_testcase(f"vsetvli_rdnx0_{sew_name}_{lmul_name}", cp1, _CG))
            lines.append(f"vsetvli x{temp_reg}, x0, {sew_name}, {lmul_name}, tu, mu")
            # Reset vl != vlmax again
            lines.append(f"vsetivli x{temp_reg}, 1, {sew_name}, {lmul_name}, tu, mu")
            # vsetvl with rs1=x0, rd!=x0
            vtype = (sew_v << 3) | lmul_v
            lines.append(f"LI(x{rs2_reg}, 0x{vtype:02x})")
            lines.append(test_data.add_testcase(f"vsetvl_rdnx0_{sew_name}_{lmul_name}", cp1, _CG))
            lines.append(f"vsetvl x{temp_reg}, x0, x{rs2_reg}")

    lines.append(comment_banner(cp2, "vsetvli/vsetvl with rs1=x0, rd=x0 -> keep vl unchanged when vlmax matches"))
    # Set vl != 0 via vsetivli, then run rd=x0/rs1=x0 with same SEW/LMUL ratio
    lines.append(f"vsetivli x{temp_reg}, 1, e8, m1, tu, mu  # vl=1")
    lines.append(test_data.add_testcase("vsetvli_rdx0", cp2, _CG))
    lines.append("vsetvli x0, x0, e8, m1, tu, mu  # rd=x0/rs1=x0; vlmax matches")
    # Same with vsetvl. Use rs2=x0 so insn[25:20]=000000 (SEW=8/LMUL=1),
    # which is what vset_i_vli_vlmax_unchanged compares against (it reads
    # SEW/LMUL from insn[25:20], not rs2_val).
    lines.append(f"vsetivli x{temp_reg}, 1, e8, m1, tu, mu  # vl=1")
    lines.append(test_data.add_testcase("vsetvl_rdx0", cp2, _CG))
    lines.append("vsetvl x0, x0, x0  # rs2=x0 makes insn-encoded SEW/LMUL = e8/m1")
    test_data.int_regs.return_registers([rs2_reg])
    return lines


def _gen_avl_corners(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vsetvl_i_avl_eq_zero / eq_vlmax / lt_2x_vlmax / eq_2x_vlmax / gt_2x_vlmax."""
    lines = [comment_banner("cp_vsetvl_i_avl_*", "AVL corner cases for vsetvli and vsetvl")]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg, rs2_reg = test_data.int_regs.get_registers(2)

    # AVL = 0
    cp = "cp_vsetvl_i_avl_eq_zero"
    lines.append(f"# {cp}")
    lines.append(f"LI(x{rs1_reg}, 0)")
    lines.append(test_data.add_testcase("vsetvli_avl0", cp, _CG))
    lines.append(f"vsetvli x{temp_reg}, x{rs1_reg}, e8, m1, tu, mu")
    lines.append(f"LI(x{rs2_reg}, 0x00)")
    lines.append(test_data.add_testcase("vsetvl_avl0", cp, _CG))
    lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")

    # AVL = VLMAX (sew=8, lmul=1: VLMAX = VLEN/8)
    cp = "cp_vsetvl_i_avl_eq_vlmax"
    lines.append(f"# {cp}")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m1, tu, mu  # rs1 = VLMAX")
    lines.append(test_data.add_testcase("vsetvli_avl_eq", cp, _CG))
    lines.append(f"vsetvli x{temp_reg}, x{rs1_reg}, e8, m1, tu, mu")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m1, tu, mu  # reload VLMAX")
    lines.append(f"LI(x{rs2_reg}, 0x00)")
    lines.append(test_data.add_testcase("vsetvl_avl_eq", cp, _CG))
    lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")

    # AVL between VLMAX and 2*VLMAX (use sew=8, lmul=2 to ensure VLMAX>=2)
    cp = "cp_vsetvl_i_avl_lt_2x_vlmax"
    lines.append(f"# {cp}")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m2, tu, mu  # VLMAX")
    lines.append(f"addi x{rs1_reg}, x{rs1_reg}, 1  # VLMAX+1 (between VLMAX and 2*VLMAX)")
    lines.append(test_data.add_testcase("vsetvli_avl_lt2x", cp, _CG))
    lines.append(f"vsetvli x{temp_reg}, x{rs1_reg}, e8, m2, tu, mu")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m2, tu, mu")
    lines.append(f"addi x{rs1_reg}, x{rs1_reg}, 1")
    lines.append(f"LI(x{rs2_reg}, 0x01)  # SEW=8, LMUL=2")
    lines.append(test_data.add_testcase("vsetvl_avl_lt2x", cp, _CG))
    lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")

    # AVL = 2 * VLMAX
    cp = "cp_vsetvl_i_avl_eq_2x_vlmax"
    lines.append(f"# {cp}")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m2, tu, mu")
    lines.append(f"slli x{rs1_reg}, x{rs1_reg}, 1  # 2*VLMAX")
    lines.append(test_data.add_testcase("vsetvli_avl_eq2x", cp, _CG))
    lines.append(f"vsetvli x{temp_reg}, x{rs1_reg}, e8, m2, tu, mu")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m2, tu, mu")
    lines.append(f"slli x{rs1_reg}, x{rs1_reg}, 1")
    lines.append(f"LI(x{rs2_reg}, 0x01)")
    lines.append(test_data.add_testcase("vsetvl_avl_eq2x", cp, _CG))
    lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")

    # AVL > 2 * VLMAX
    cp = "cp_vsetvl_i_avl_gt_2x_vlmax"
    lines.append(f"# {cp}")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m2, tu, mu")
    lines.append(f"slli x{rs1_reg}, x{rs1_reg}, 1")
    lines.append(f"addi x{rs1_reg}, x{rs1_reg}, 1  # 2*VLMAX+1")
    lines.append(test_data.add_testcase("vsetvli_avl_gt2x", cp, _CG))
    lines.append(f"vsetvli x{temp_reg}, x{rs1_reg}, e8, m2, tu, mu")
    lines.append(f"vsetvli x{rs1_reg}, x0, e8, m2, tu, mu")
    lines.append(f"slli x{rs1_reg}, x{rs1_reg}, 1")
    lines.append(f"addi x{rs1_reg}, x{rs1_reg}, 1")
    lines.append(f"LI(x{rs2_reg}, 0x01)")
    lines.append(test_data.add_testcase("vsetvl_avl_gt2x", cp, _CG))
    lines.append(f"vsetvl x{temp_reg}, x{rs1_reg}, x{rs2_reg}")

    test_data.int_regs.return_registers([rs1_reg, rs2_reg])
    return lines


def _gen_vsetivli_avl_edges(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vsetivli_avl_edges: vsetivli with all 32 imm5 values, lmul=1, all supported sew."""
    coverpoint = "cp_vsetivli_avl_edges"
    lines = [comment_banner(coverpoint, "vsetivli imm5 across [0..31] for each supported sew, lmul=1")]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    for sew_name, _ in _SEW_VALUES:
        for imm in range(32):
            lines.append(test_data.add_testcase(f"vsetivli_imm{imm}_{sew_name}", coverpoint, _CG))
            lines.append(f"vsetivli x{temp_reg}, {imm}, {sew_name}, m1, tu, mu")
    # Cross bin <vsetivli, sixtyfour, auto[0], one> requires BEFORE vtype = (e64, m1)
    # with imm=0. The loop above never produces this because imm=0 is always the first
    # iteration of each sew block (so BEFORE vtype.SEW reflects the prior sew).
    # Run one more vsetivli imm=0,e64,m1 after the e64 block has set vtype=(e64,m1).
    lines.append(test_data.add_testcase("vsetivli_imm0_e64_after", coverpoint, _CG))
    lines.append(f"vsetivli x{temp_reg}, 0, e64, m1, tu, mu")
    return lines


def _gen_vstart_oob(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vstart_out_of_bounds: csrrw vstart with rs1 = 2^16."""
    coverpoint = "cp_vstart_out_of_bounds"
    lines = [comment_banner(coverpoint, "csrrw vstart with rs1 = 2^16 (above max VLEN-1)")]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    rs1_reg = test_data.int_regs.get_register()
    lines.append(f"LI(x{rs1_reg}, 0x10000)  # 2^16")
    lines.append(test_data.add_testcase("vstart_oob", coverpoint, _CG))
    lines.append(f"CSRW(vstart, x{rs1_reg})")
    test_data.int_regs.return_registers([rs1_reg])
    return lines


def _gen_vl_walking1s_sew_lmul(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vl_walking1s_sew_lmul: csrrw vl walking-1s after vsetivli for each (sew, lmul)."""
    coverpoint = "cp_vl_walking1s_sew_lmul"
    lines = [comment_banner(coverpoint, "csrrw vl walking-1s after vsetivli for each (sew, lmul)")]
    lines.extend(_set_vs(vs=3, temp_reg=temp_reg))
    walk_reg = test_data.int_regs.get_register()
    for sew_name, _ in _SEW_VALUES:
        for lmul_name, _ in _LMUL_VALUES:
            lines.append(f"# {sew_name}, {lmul_name}")
            lines.append(f"LI(x{walk_reg}, 1)")
            for i in range(32):
                # vsetivli must be the immediately-preceding instruction of the CSRW
                # so that ins.prev.insn == vsetivli at sample time.
                lines.append(f"vsetivli x{temp_reg}, 1, {sew_name}, {lmul_name}, tu, mu")
                lines.append(test_data.add_testcase(f"vl_walk_{sew_name}_{lmul_name}_b{i}", coverpoint, _CG))
                lines.append(f"CSRW(vl, x{walk_reg})  # bit {i}")
                lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")
            lines.append("#if __riscv_xlen == 64")
            for i in range(32, 64):
                lines.append(f"vsetivli x{temp_reg}, 1, {sew_name}, {lmul_name}, tu, mu")
                lines.append(test_data.add_testcase(f"vl_walk_{sew_name}_{lmul_name}_b{i}", coverpoint, _CG))
                lines.append(f"CSRW(vl, x{walk_reg})  # bit {i}")
                lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")
            lines.append("#endif")
    test_data.int_regs.return_registers([walk_reg])
    return lines


@add_priv_test_generator(
    "SmV",
    required_extensions=["Sm", "I", "M", "V", "Zicsr"],
    march_extensions=["I", "M", "V", "Zicsr"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_smv(test_data: TestData) -> list[str]:
    """Generate SmV tests (vector CSRs, vsetvl* behavior, vill, vstart, mstatus.VS, misa.V)."""
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines: list[str] = []
    lines.extend(_gen_vcsrrswc(test_data, temp_reg))
    lines.extend(_gen_vcsrs_walking1s(test_data, temp_reg))
    lines.extend(_gen_mstatus_vs_dirty(test_data, temp_reg))
    lines.extend(_gen_mstatus_vs_off(test_data, temp_reg))
    lines.extend(_gen_misa_v(test_data, temp_reg))
    lines.extend(_gen_sew_lmul_vsetvl(test_data, temp_reg))
    lines.extend(_gen_sew_lmul_vset_i_vli(test_data, temp_reg))
    lines.extend(_gen_vill_vsetvl(test_data, temp_reg))
    lines.extend(_gen_vill_vset_i_vli(test_data, temp_reg))
    lines.extend(_gen_vill_vsetvl_rs2_vill(test_data, temp_reg))
    lines.extend(_gen_vsetvl_rs2_vill(test_data, temp_reg))
    lines.extend(_gen_vtype_vill_set_vl_0(test_data, temp_reg))
    lines.extend(_gen_vsetvl_i_rd_rs1(test_data, temp_reg))
    lines.extend(_gen_avl_corners(test_data, temp_reg))
    lines.extend(_gen_vsetivli_avl_edges(test_data, temp_reg))
    lines.extend(_gen_vstart_oob(test_data, temp_reg))
    lines.extend(_gen_vl_walking1s_sew_lmul(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg])
    return lines
