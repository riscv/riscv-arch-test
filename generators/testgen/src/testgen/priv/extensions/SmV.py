##################################
# priv/extensions/SmV.py
#
# SmV machine-mode vector CSR / vsetvl* test generator.
# Drives the SmV_cg covergroup defined in coverpoints/priv/SmV_coverage.svh.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SmV privileged test generator (vector CSR + vset* coverage)."""

from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_CG = "SmV_cg"

_FS_MASK = 3 << 13
_VS_MASK = 3 << 9

_VEC_CSRS_ALL: list[str] = ["vstart", "vxsat", "vxrm", "vcsr", "vl", "vtype", "vlenb"]
_VEC_CSRS_WRITABLE: list[str] = ["vstart", "vxsat", "vxrm", "vcsr"]

# (sew_bits, sew_label) excluding reserved 100/101/110/111
_SEW_VALUES: list[tuple[int, str]] = [(0, "e8"), (1, "e16"), (2, "e32"), (3, "e64")]
# (lmul_bits, lmul_label) excluding reserved 100
_LMUL_VALUES: list[tuple[int, str]] = [
    (0, "m1"),
    (1, "m2"),
    (2, "m4"),
    (3, "m8"),
    (5, "mf8"),
    (6, "mf4"),
    (7, "mf2"),
]


def _set_vs(vs: int, temp_reg: int) -> list[str]:
    """Force mstatus.VS = vs (0..3); leave FS untouched."""
    return [
        f"LI(x{temp_reg}, {_VS_MASK})",
        f"CSRC(mstatus, x{temp_reg})",
        f"LI(x{temp_reg}, {vs << 9})",
        f"CSRS(mstatus, x{temp_reg})",
    ]


def _vec_init(temp_reg: int) -> list[str]:
    """Set VS=Dirty + a legal vtype (e32, m1, vl=1) + clear vstart."""
    return _set_vs(3, temp_reg) + [
        f"vsetivli x{temp_reg}, 1, e32, m1, tu, mu",
        "csrw vstart, x0",
    ]


def _seed_misa(temp_reg: int) -> list[str]:
    return [f"csrr x{temp_reg}, misa  # seed misa to rvvi trace"]


def _vtype_imm(sew: int, lmul: int) -> int:
    """Encode the vsetvli/vsetivli zimm[10:0] field (vtype encoding)."""
    return (sew << 3) | (lmul & 0x7)


# -----------------------------------------------------------------------------
# cp_vcsrrswc + cp_vcsrs_walking1s
# -----------------------------------------------------------------------------
def _gen_vcsr_tests(test_data: TestData) -> list[str]:
    lines: list[str] = [comment_banner("cp_vcsrrswc + cp_vcsrs_walking1s", "Access/walk every vector CSR")]
    for csr in _VEC_CSRS_ALL:
        lines.extend(csr_access_test(test_data, csr, _CG, "cp_vcsrrswc"))
    for csr in _VEC_CSRS_WRITABLE:
        lines.extend(_csrrw_walk_test(test_data, csr, "cp_vcsrs_walking1s"))
    return lines


def _csrrw_walk_test(test_data: TestData, csr_name: str, coverpoint: str) -> list[str]:
    """Walking-1s csrrw on csr (the cp_vcsrs_walking1s cross requires opcode csrrw)."""
    from testgen.asm.csr import gen_csr_read_sigupd

    save_reg, walk_reg, check_reg = test_data.int_regs.get_registers(3)
    lines: list[str] = [
        "",
        f"# CSRRW walking-1s on {csr_name}",
        f"CSRR(x{save_reg}, {csr_name})",
        f"LI(x{walk_reg}, 1)",
    ]
    for i in range(32):
        lines.extend(
            [
                "",
                f"CSRRW(x0, {csr_name}, x{walk_reg})",
                test_data.add_testcase(f"{csr_name}_csrrw_b{i}", coverpoint, _CG),
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )
    lines.append("\n#if __riscv_xlen == 64")
    for i in range(32, 64):
        lines.extend(
            [
                "",
                f"CSRRW(x0, {csr_name}, x{walk_reg})",
                test_data.add_testcase(f"{csr_name}_csrrw_b{i}", coverpoint, _CG),
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )
    lines.append("#endif\n")
    lines.append(f"CSRRW(x0, {csr_name}, x{save_reg})")
    test_data.int_regs.return_registers([save_reg, walk_reg, check_reg])
    return lines


# -----------------------------------------------------------------------------
# cp_mstatus_vs_set_dirty_arithmetic / _csr
# cp_mstatus_vs_off_arithmetic       / _csr
# -----------------------------------------------------------------------------
def _gen_mstatus_vs_tests(test_data: TestData, temp_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_mstatus_vs_*", "VS state transitions: Initial/Clean → Dirty, and Off traps")]
    # set_dirty: VS=Initial(1) and VS=Clean(2), execute vadd.vv and vsetvli.
    for vs in (1, 2):
        lines.append(f"\n# VS={vs} → Dirty via vadd.vv")
        lines.extend(_vec_init(temp_reg))  # ensures vill=0, vstart=0, vl=1
        lines.extend(_set_vs(vs, temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vadd_vv_vs{vs}", "cp_mstatus_vs_set_dirty_arithmetic", _CG),
                "vadd.vv v3, v1, v2",
                "nop",
            ]
        )
        lines.append(f"\n# VS={vs} → Dirty via vsetvli")
        lines.extend(_vec_init(temp_reg))
        lines.extend(_set_vs(vs, temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vsetvli_vs{vs}", "cp_mstatus_vs_set_dirty_csr", _CG),
                f"vsetvli x{temp_reg}, x0, e32, m1, tu, mu",
                "nop",
            ]
        )

    # VS=Off: vector-arith and vsetvli must trap. misa.V must be active in trace.
    lines.append("\n# VS=Off: vector arith / vsetvli trap")
    lines.extend(_vec_init(temp_reg))
    lines.extend(_seed_misa(temp_reg))
    lines.extend(_set_vs(0, temp_reg))
    lines.extend(
        [
            test_data.add_testcase("vadd_vv_vs_off", "cp_mstatus_vs_off_arithmetic", _CG),
            "vadd.vv v3, v1, v2  # traps: VS=Off",
            "nop",
        ]
    )
    lines.extend(_set_vs(3, temp_reg))  # restore so we can re-init
    lines.extend(_vec_init(temp_reg))
    lines.extend(_seed_misa(temp_reg))
    lines.extend(_set_vs(0, temp_reg))
    lines.extend(
        [
            test_data.add_testcase("vsetvli_vs_off", "cp_mstatus_vs_off_csr", _CG),
            f"vsetvli x{temp_reg}, x0, e32, m1, tu, mu  # traps: VS=Off",
            "nop",
        ]
    )
    lines.extend(_set_vs(3, temp_reg))
    return lines


# -----------------------------------------------------------------------------
# cp_misa_v_clear_set
# -----------------------------------------------------------------------------
def _gen_misa_v_tests(test_data: TestData, temp_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_misa_v_clear_set", "Try to clear/set misa.V")]
    lines.extend(
        [
            f"LI(x{temp_reg}, {1 << 21})  # misa.V bit",
            test_data.add_testcase("misa_v_csrrc", "cp_misa_v_clear_set", _CG),
            f"CSRC(misa, x{temp_reg})",
            "nop",
            test_data.add_testcase("misa_v_csrrs", "cp_misa_v_clear_set", _CG),
            f"CSRS(misa, x{temp_reg})",
            "nop",
        ]
    )
    return lines


# -----------------------------------------------------------------------------
# cp_sew_lmul_vsetvl + cp_sew_lmul_vset_i_vli
# -----------------------------------------------------------------------------
def _gen_sew_lmul_tests(test_data: TestData, temp_reg: int, vtype_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_sew_lmul_vset*", "All SEW × LMUL combinations via every vset variant")]
    lines.extend(_vec_init(temp_reg))
    lines.append(f"LI(x{temp_reg}, 1)  # AVL=1 for vsetvl/vsetvli")

    # vsetvl: rs2 holds vtype encoding. The cross samples ins.current.rs2_val,
    # so consecutive vsetvls just need different rs2 values.
    for sew, sew_lbl in _SEW_VALUES:
        for lmul, lmul_lbl in _LMUL_VALUES:
            imm = _vtype_imm(sew, lmul)
            lines.extend(
                [
                    f"LI(x{vtype_reg}, {imm})  # vtype = sew={sew_lbl} lmul={lmul_lbl}",
                    test_data.add_testcase(f"vsetvl_{sew_lbl}_{lmul_lbl}", "cp_sew_lmul_vsetvl", _CG),
                    f"vsetvl x0, x{temp_reg}, x{vtype_reg}",
                ]
            )

    # vsetvli: cross samples ins.PREV.insn[25:20]. Issue back-to-back vsetvli's
    # without anything between them so each vsetvli's "prev" is another vsetvli
    # with the desired (sew, lmul) encoded in its insn bits.
    for sew, sew_lbl in _SEW_VALUES:
        for lmul, lmul_lbl in _LMUL_VALUES:
            lines.extend(
                [
                    test_data.add_testcase(f"vsetvli_prev_{sew_lbl}_{lmul_lbl}", "cp_sew_lmul_vset_i_vli", _CG),
                    f"vsetvli x0, x{temp_reg}, {sew_lbl}, {lmul_lbl}, tu, mu",
                ]
            )
    # One extra vsetvli so the LAST one above has a "next" that samples it.
    lines.append("vsetvli x0, x0, e8, m1, tu, mu  # sample for previous")

    # vsetivli: similarly back-to-back.
    for sew, sew_lbl in _SEW_VALUES:
        for lmul, lmul_lbl in _LMUL_VALUES:
            lines.extend(
                [
                    test_data.add_testcase(f"vsetivli_prev_{sew_lbl}_{lmul_lbl}", "cp_sew_lmul_vset_i_vli", _CG),
                    f"vsetivli x0, 1, {sew_lbl}, {lmul_lbl}, tu, mu",
                ]
            )
    lines.append("vsetivli x0, 1, e8, m1, tu, mu  # sample for previous")
    return lines


# -----------------------------------------------------------------------------
# cp_vill_vsetvl, cp_vill_vset_i_vli, cp_vill_vsetvl_rs2_vill
# All want vtype.vill set to 1 BEFORE the instruction; LMUL=8, SEW supported.
# -----------------------------------------------------------------------------
def _set_vtype_vill(temp_reg: int) -> list[str]:
    """Force vtype.vill=1 by issuing vsetvl with rs2 having reserved sew bits."""
    return [
        f"LI(x{temp_reg}, 0x20)  # rs2 with reserved sew=100 -> vill set",
        f"vsetvl x0, x0, x{temp_reg}  # sets vill",
    ]


def _gen_vill_tests(test_data: TestData, temp_reg: int, vtype_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_vill_*", "vill-set start, then vset* with valid sew × lmul=8")]
    for sew, sew_lbl in _SEW_VALUES:
        # vsetvl: rs2 = legal vtype with sew, lmul=8 (3'b011)
        imm = _vtype_imm(sew, 3)
        lines.extend(_set_vtype_vill(temp_reg))
        lines.extend(
            [
                f"LI(x{vtype_reg}, {imm})",
                f"LI(x{temp_reg}, 1)",
                test_data.add_testcase(f"vill_vsetvl_{sew_lbl}_m8", "cp_vill_vsetvl", _CG),
                f"vsetvl x0, x{temp_reg}, x{vtype_reg}",
                "nop",
            ]
        )
        # vsetvli with vill prev, sew, lmul=m8
        lines.extend(_set_vtype_vill(temp_reg))
        lines.extend(
            [
                f"LI(x{temp_reg}, 1)",
                test_data.add_testcase(f"vill_vsetvli_{sew_lbl}_m8", "cp_vill_vset_i_vli", _CG),
                f"vsetvli x0, x{temp_reg}, {sew_lbl}, m8, tu, mu",
                "nop",
            ]
        )
        # vsetivli with vill prev: re-set vill so vsetivli's prev vtype has vill=1
        lines.extend(_set_vtype_vill(temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vill_vsetivli_{sew_lbl}_m8", "cp_vill_vset_i_vli", _CG),
                f"vsetivli x0, 1, {sew_lbl}, m8, tu, mu",
                "nop",
            ]
        )
        # cp_vill_vsetvl_rs2_vill: vill prev, rs2 has vill bit set + legal sew, lmul=8
        lines.extend(_set_vtype_vill(temp_reg))
        lines.extend(
            [
                "#if __riscv_xlen == 64",
                f"LI(x{vtype_reg}, {(1 << 63) | imm})",
                "#else",
                f"LI(x{vtype_reg}, {(1 << 31) | imm})",
                "#endif",
                f"LI(x{temp_reg}, 1)",
                test_data.add_testcase(f"vill_vsetvl_rs2vill_{sew_lbl}_m8", "cp_vill_vsetvl_rs2_vill", _CG),
                f"vsetvl x0, x{temp_reg}, x{vtype_reg}",
                "nop",
            ]
        )
    return lines


# -----------------------------------------------------------------------------
# cp_vsetvl_rs2_vill: vill prev clear, rs2 has vill bit set + legal sew/lmul=1
# -----------------------------------------------------------------------------
def _gen_vsetvl_rs2_vill_tests(test_data: TestData, temp_reg: int, vtype_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_vsetvl_rs2_vill", "rs2 with vill bit + valid sew/lmul=1")]
    for sew, sew_lbl in _SEW_VALUES:
        imm = _vtype_imm(sew, 0)
        lines.extend(_vec_init(temp_reg))  # vill cleared
        lines.extend(
            [
                "#if __riscv_xlen == 64",
                f"LI(x{vtype_reg}, {(1 << 63) | imm})",
                "#else",
                f"LI(x{vtype_reg}, {(1 << 31) | imm})",
                "#endif",
                f"LI(x{temp_reg}, 1)",
                test_data.add_testcase(f"vsetvl_rs2vill_{sew_lbl}", "cp_vsetvl_rs2_vill", _CG),
                f"vsetvl x0, x{temp_reg}, x{vtype_reg}",
                "nop",
            ]
        )
    return lines


# -----------------------------------------------------------------------------
# cp_vtype_vill_set_vl_0: pre vl != 0; rs1 != 0; rs2 has vill bit set.
# -----------------------------------------------------------------------------
def _gen_vill_vl0(test_data: TestData, temp_reg: int, vtype_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_vtype_vill_set_vl_0", "vill -> vl forced to 0")]
    lines.extend(_vec_init(temp_reg))  # vl=1 (nonzero)
    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f"LI(x{vtype_reg}, {1 << 63})",
            "#else",
            f"LI(x{vtype_reg}, {1 << 31})",
            "#endif",
            f"LI(x{temp_reg}, 1)  # rs1 nonzero",
            test_data.add_testcase("vsetvl_vill_to_vl0", "cp_vtype_vill_set_vl_0", _CG),
            f"vsetvl x0, x{temp_reg}, x{vtype_reg}",
            "nop",
        ]
    )
    return lines


# -----------------------------------------------------------------------------
# cp_vsetvl_i_rd_nx0_rs1_x0: vsetvli/vsetvl with rd!=0, rs1=x0; vl != vlmax.
# cp_vsetvl_i_rd_x0_rs1_x0:  rd=x0, rs1=x0; vl != 0; vlmax unchanged.
# -----------------------------------------------------------------------------
def _gen_vsetvl_rd_rs1_tests(test_data: TestData, temp_reg: int, dest_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_vsetvl_i_rd_*_rs1_x0", "rd/rs1 special-case behaviors")]
    # rd!=0, rs1=x0 with all SAMPLE_BEFORE (sew, lmul) combos and vl != vlmax.
    # Strategy: pre-set vtype to (sew, lmul) and vl=1 (small), then issue another
    # vsetvli/vsetvl with rs1=x0 (which sets vl=VLMAX, so we sample it and move on).
    for sew, sew_lbl in _SEW_VALUES:
        for lmul, lmul_lbl in _LMUL_VALUES:
            # Skip illegal (SEW > LMUL*ELEN) combos that would set vill,
            # making SAMPLE_BEFORE vtype != requested (sew, lmul).
            sew_pow = 3 + sew  # e8=8 -> pow=3
            lmul_signed = lmul if lmul < 4 else lmul - 8  # 5,6,7 -> -3,-2,-1
            if sew_pow > lmul_signed + 6:  # ELEN_pow=6 (ELEN=64)
                continue
            # vsetvli form
            lines.extend(
                [
                    f"vsetivli x0, 1, {sew_lbl}, {lmul_lbl}, tu, mu  # vtype=({sew_lbl},{lmul_lbl}), vl=1",
                    test_data.add_testcase(
                        f"vsetvli_rd_nx0_rs1x0_{sew_lbl}_{lmul_lbl}", "cp_vsetvl_i_rd_nx0_rs1_x0", _CG
                    ),
                    f"vsetvli x{dest_reg}, x0, {sew_lbl}, {lmul_lbl}, tu, mu  # rd!=0, rs1=x0 -> vl=VLMAX",
                    "nop",
                ]
            )
            # vsetvl form (rs2 supplies vtype encoding)
            vtype_enc = _vtype_imm(sew, lmul)
            lines.extend(
                [
                    f"vsetivli x0, 1, {sew_lbl}, {lmul_lbl}, tu, mu  # vtype=({sew_lbl},{lmul_lbl}), vl=1",
                    f"LI(x{temp_reg}, {vtype_enc})",
                    test_data.add_testcase(
                        f"vsetvl_rd_nx0_rs1x0_{sew_lbl}_{lmul_lbl}", "cp_vsetvl_i_rd_nx0_rs1_x0", _CG
                    ),
                    f"vsetvl x{dest_reg}, x0, x{temp_reg}  # rd!=0, rs1=x0 -> vl=VLMAX",
                    "nop",
                ]
            )

    # rd=x0, rs1=x0: vl unchanged & vlmax unchanged (use same sew/lmul as current).
    lines.extend(_vec_init(temp_reg))  # vl=1, vtype = e32/m1
    lines.extend(
        [
            test_data.add_testcase("vsetvli_rdx0_rs1x0", "cp_vsetvl_i_rd_x0_rs1_x0", _CG),
            "vsetvli x0, x0, e32, m1, tu, mu",
            f"LI(x{temp_reg}, {_vtype_imm(2, 0)})",
            test_data.add_testcase("vsetvl_rdx0_rs1x0", "cp_vsetvl_i_rd_x0_rs1_x0", _CG),
            f"vsetvl x0, x0, x{temp_reg}",
            "nop",
        ]
    )
    return lines


# -----------------------------------------------------------------------------
# cp_vsetvl_i_avl_*  +  cp_vsetivli_avl_edges
# -----------------------------------------------------------------------------
def _gen_avl_tests(test_data: TestData, temp_reg: int, dest_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_vsetvl_i_avl_*", "AVL edge cases for vsetvl/vsetvli")]
    save_reg, vlmax_reg = test_data.int_regs.get_registers(2)

    lines.extend(_vec_init(temp_reg))
    lines.extend(
        [
            f"vsetvli x{vlmax_reg}, x0, e8, m1, tu, mu  # vlmax of e8/m1",
            f"addi x{save_reg}, x{vlmax_reg}, 0",
            f"LI(x{temp_reg}, 8)  # vtype encoding for e8/m1 (sew=000 lmul=000) is 0; use small valid vtype reg",
        ]
    )
    # encode vtype = e8/m1 = 0 in integer form for vsetvl rs2
    # We pre-set vtype=(e8,m1) via vsetvli; then for each test, do another vsetvli first
    # to ensure SAMPLE_BEFORE matches the (e8,m1) vlmax.

    def _restore_vtype() -> list[str]:
        return [f"vsetvli x0, x{save_reg}, e8, m1, tu, mu  # restore vl=vlmax, vtype=(e8,m1)"]

    # rs1 == 0 (rs1 reg != x0)
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"LI(x{temp_reg}, 0)",
            test_data.add_testcase("avl_eq_zero_vli", "cp_vsetvl_i_avl_eq_zero", _CG),
            f"vsetvli x{dest_reg}, x{temp_reg}, e8, m1, tu, mu",
        ]
    )
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"LI(x{temp_reg}, 0)",
            f"LI(x{vlmax_reg}, 0)  # rs2=vtype encoding for e8/m1",
            test_data.add_testcase("avl_eq_zero_vl", "cp_vsetvl_i_avl_eq_zero", _CG),
            f"vsetvl x{dest_reg}, x{temp_reg}, x{vlmax_reg}",
            "nop",
        ]
    )

    # rs1 == vlmax (vlmax of currently-active e8/m1)
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"add x{temp_reg}, x{save_reg}, x0",
            test_data.add_testcase("avl_eq_vlmax_vli", "cp_vsetvl_i_avl_eq_vlmax", _CG),
            f"vsetvli x{dest_reg}, x{temp_reg}, e8, m1, tu, mu",
        ]
    )
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"add x{temp_reg}, x{save_reg}, x0",
            f"LI(x{vlmax_reg}, 0)",
            test_data.add_testcase("avl_eq_vlmax_vl", "cp_vsetvl_i_avl_eq_vlmax", _CG),
            f"vsetvl x{dest_reg}, x{temp_reg}, x{vlmax_reg}",
            "nop",
        ]
    )

    # vlmax < rs1 < 2*vlmax
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"addi x{temp_reg}, x{save_reg}, 1",
            test_data.add_testcase("avl_lt_2x_vlmax_vli", "cp_vsetvl_i_avl_lt_2x_vlmax", _CG),
            f"vsetvli x{dest_reg}, x{temp_reg}, e8, m1, tu, mu",
        ]
    )
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"addi x{temp_reg}, x{save_reg}, 1",
            f"LI(x{vlmax_reg}, 0)",
            test_data.add_testcase("avl_lt_2x_vlmax_vl", "cp_vsetvl_i_avl_lt_2x_vlmax", _CG),
            f"vsetvl x{dest_reg}, x{temp_reg}, x{vlmax_reg}",
            "nop",
        ]
    )

    # rs1 == 2*vlmax
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"slli x{temp_reg}, x{save_reg}, 1",
            test_data.add_testcase("avl_eq_2x_vlmax_vli", "cp_vsetvl_i_avl_eq_2x_vlmax", _CG),
            f"vsetvli x{dest_reg}, x{temp_reg}, e8, m1, tu, mu",
        ]
    )
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"slli x{temp_reg}, x{save_reg}, 1",
            f"LI(x{vlmax_reg}, 0)",
            test_data.add_testcase("avl_eq_2x_vlmax_vl", "cp_vsetvl_i_avl_eq_2x_vlmax", _CG),
            f"vsetvl x{dest_reg}, x{temp_reg}, x{vlmax_reg}",
            "nop",
        ]
    )

    # rs1 > 2*vlmax (2*vlmax + 1)
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"slli x{temp_reg}, x{save_reg}, 1",
            f"addi x{temp_reg}, x{temp_reg}, 1",
            test_data.add_testcase("avl_gt_2x_vlmax_vli", "cp_vsetvl_i_avl_gt_2x_vlmax", _CG),
            f"vsetvli x{dest_reg}, x{temp_reg}, e8, m1, tu, mu",
        ]
    )
    lines.extend(_restore_vtype())
    lines.extend(
        [
            f"slli x{temp_reg}, x{save_reg}, 1",
            f"addi x{temp_reg}, x{temp_reg}, 1",
            f"LI(x{vlmax_reg}, 0)",
            test_data.add_testcase("avl_gt_2x_vlmax_vl", "cp_vsetvl_i_avl_gt_2x_vlmax", _CG),
            f"vsetvl x{dest_reg}, x{temp_reg}, x{vlmax_reg}",
            "nop",
        ]
    )

    # cp_vsetivli_avl_edges: imm5 × all SEW × lmul=1
    # SAMPLE_BEFORE vtype must have lmul=m1 AND sew∈{e8,e16,e32,e64}, so pre-set
    # vtype to each (sew, m1) before each batch of imm5 tests.
    lines.append("\n# vsetivli imm5 edges × SEW × lmul=1")
    for sew, sew_lbl in _SEW_VALUES:
        for imm5 in range(32):
            # Pre-set vtype to (sew, m1) so SAMPLE_BEFORE matches the cross.
            lines.append(f"vsetvli x0, x{save_reg}, {sew_lbl}, m1, tu, mu  # SAMPLE_BEFORE: ({sew_lbl},m1)")
            lines.extend(
                [
                    test_data.add_testcase(f"vsetivli_imm{imm5}_{sew_lbl}", "cp_vsetivli_avl_edges", _CG),
                    f"vsetivli x0, {imm5}, {sew_lbl}, m1, tu, mu",
                ]
            )

    test_data.int_regs.return_registers([save_reg, vlmax_reg])
    return lines


# -----------------------------------------------------------------------------
# cp_vstart_out_of_bounds
# -----------------------------------------------------------------------------
def _gen_vstart_oob(test_data: TestData, temp_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_vstart_out_of_bounds", "Write 2^16 to vstart")]
    lines.extend(
        [
            f"LI(x{temp_reg}, {1 << 16})",
            test_data.add_testcase("vstart_oob", "cp_vstart_out_of_bounds", _CG),
            f"CSRW(vstart, x{temp_reg})",
            "nop",
        ]
    )
    return lines


# -----------------------------------------------------------------------------
# cp_vl_walking1s_sew_lmul: vsetivli sets sew/lmul, then csrrw vl with walking-1s.
# Note: vl is read-only normally; the walking-1s csrrw is expected to be ignored
# but the coverpoint just samples the prev vsetivli + this csrrw + rs1 walking.
# -----------------------------------------------------------------------------
def _gen_vl_walking1s(test_data: TestData, temp_reg: int) -> list[str]:
    lines: list[str] = [comment_banner("cp_vl_walking1s_sew_lmul", "vsetivli (sew,lmul) then csrrw vl walking-1s")]
    for sew, sew_lbl in _SEW_VALUES:
        for lmul, lmul_lbl in _LMUL_VALUES:
            lines.append(f"\n# sew={sew_lbl} lmul={lmul_lbl}")
            for i in range(32):
                lines.extend(
                    [
                        f"LI(x{temp_reg}, {1 << i})",
                        f"vsetivli x0, 1, {sew_lbl}, {lmul_lbl}, tu, mu",
                        test_data.add_testcase(f"vl_walk_{sew_lbl}_{lmul_lbl}_b{i}", "cp_vl_walking1s_sew_lmul", _CG),
                        f"csrrw x0, vl, x{temp_reg}",
                        "nop  # padding for trap handler skip-8",
                    ]
                )
            lines.append("#if __riscv_xlen == 64")
            for i in range(32, 64):
                lines.extend(
                    [
                        f"LI(x{temp_reg}, 1)",
                        f"slli x{temp_reg}, x{temp_reg}, {i}",
                        f"vsetivli x0, 1, {sew_lbl}, {lmul_lbl}, tu, mu",
                        test_data.add_testcase(f"vl_walk_{sew_lbl}_{lmul_lbl}_b{i}", "cp_vl_walking1s_sew_lmul", _CG),
                        f"csrrw x0, vl, x{temp_reg}",
                        "nop  # padding for trap handler skip-8",
                    ]
                )
            lines.append("#endif")
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
    """Generate SmV machine-mode vector CSR + vset* tests."""
    temp_reg, vtype_reg, dest_reg = test_data.int_regs.get_registers(3)

    lines: list[str] = []
    # Make sure VS is on so vset* doesn't trap unintentionally.
    lines.extend(_set_vs(3, temp_reg))
    lines.extend(_gen_vcsr_tests(test_data))
    lines.extend(_gen_mstatus_vs_tests(test_data, temp_reg))
    lines.extend(_gen_misa_v_tests(test_data, temp_reg))
    # restore VS=Dirty + good vtype
    lines.extend(_vec_init(temp_reg))
    lines.extend(_gen_sew_lmul_tests(test_data, temp_reg, vtype_reg))
    lines.extend(_gen_vill_tests(test_data, temp_reg, vtype_reg))
    lines.extend(_gen_vsetvl_rs2_vill_tests(test_data, temp_reg, vtype_reg))
    lines.extend(_gen_vill_vl0(test_data, temp_reg, vtype_reg))
    lines.extend(_gen_vsetvl_rd_rs1_tests(test_data, temp_reg, dest_reg))
    lines.extend(_gen_avl_tests(test_data, temp_reg, dest_reg))
    lines.extend(_gen_vstart_oob(test_data, temp_reg))
    lines.extend(_gen_vl_walking1s(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, vtype_reg, dest_reg])
    return lines
