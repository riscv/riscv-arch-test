##################################
# priv/extensions/Sstc.py
#
# Sstc privileged extension test generator.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstc stimecmp access tests, with the vstimecmp and htimedelta tests of the H and HSm groups.

``mode`` is "machine", "supervisor" (S-mode or HS-mode) or "user", as in the coverpoint names.  M-mode CSRs are written
directly in machine mode and through T-SBI otherwise; user-mode tests are entered from S-mode with
RVTEST_TSBI_GOTO_UMODE.
"""

from itertools import product

from testgen.asm.csr import csr_access_test, write_stce
from testgen.asm.helpers import comment_banner, write64_csr, write_sigupd
from testgen.asm.tsbi import tsbi_call, tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import HTIMEDELTAS, read_time
from testgen.priv.registry import add_priv_test_generator

_CG = "Sstc_cg"
_CG_SM = "Sstc_Sm_cg"
_CG_H = "Sstc_H_cg"
_CG_HSM = "Sstc_HSm_cg"
# H group: distinct values in the future for stimecmp and vstimecmp, and one VS-mode writes through stimecmp
STIMECMP = 0xAAAAAAAAAAAAAAAA
VSTIMECMP = 0x5555555555555555
VS_STIMECMP = 0x3333333333333333
# HSm group
MASK64 = (1 << 64) - 1
# vstimecmp values of cp_htimedelta
COMPARES = {
    "zero": 0,
    "pos_2p29": 1 << 29,
    "pos_2p31": 1 << 31,
    "pos_2p61": 1 << 61,
    "neg_2p29": -(1 << 29),
    "neg_2p31": -(1 << 31),
    "neg_2p61": -(1 << 61),
}


def csr_op(instr: str, mode: str) -> str:
    """An M-mode CSR instruction, issued directly in machine mode and through T-SBI otherwise."""
    return tsbi_call_or_direct(instr, "M" if mode == "machine" else "S")  # user tests do their setup in S-mode


def mcounteren_tm(test_data: TestData, enable: bool, mode: str) -> list[str]:
    """Set or clear mcounteren.TM."""
    reg = test_data.int_regs.get_register()
    lines = [f"LI(x{reg}, MCOUNTEREN_TIME)", csr_op(f"{'csrs' if enable else 'csrc'} mcounteren, x{reg}", mode)]
    test_data.int_regs.return_register(reg)
    return lines


def stce_tm(test_data: TestData, m_stce: int, h_stce: int, m_tm: int, h_tm: int, mode: str) -> list[str]:
    """Write menvcfg.STCE, henvcfg.STCE, mcounteren.TM and hcounteren.TM from M-mode (machine) or HS-mode (supervisor).

    henvcfg follows menvcfg because henvcfg.STCE is read-only zero while menvcfg.STCE = 0.
    """
    priv = "M" if mode == "machine" else "S"
    reg = test_data.int_regs.get_register()
    lines = [
        *write_stce(test_data, bool(m_stce), priv),
        *write_stce(test_data, bool(h_stce), priv, henvcfg=True),
        *mcounteren_tm(test_data, bool(m_tm), mode),
        f"LI(x{reg}, MCOUNTEREN_TIME)",
        f"{'csrs' if h_tm else 'csrc'} hcounteren, x{reg}",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def rv32_only(csr: str, lines: list[str]) -> list[str]:
    """Wrap lines for an upper-half CSR in #if __riscv_xlen == 32."""
    return ["#if __riscv_xlen == 32", *lines, "#endif"] if csr.endswith("h") else lines


def access_cross(test_data: TestData, coverpoint: str, covergroup: str, mode: str, csrs: list[str]) -> list[str]:
    """Read each CSR in mode (m, hs, vs, vu or u) for every value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM
    and hcounteren.TM.  Mode m is in the HSm group, which boots to M-mode; the others are in the H group, which
    boots to HS-mode.  henvcfg.STCE = 1 with menvcfg.STCE = 0 is skipped because henvcfg.STCE is read-only zero then."""
    rd = test_data.int_regs.get_register()
    boot = "machine" if mode == "m" else "supervisor"
    lower = mode not in ("m", "hs")
    lines = []
    for m_stce, h_stce, m_tm, h_tm in product((0, 1), repeat=4):
        if h_stce > m_stce:
            continue
        lines.extend(stce_tm(test_data, m_stce, h_stce, m_tm, h_tm, boot))
        lines.extend([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if lower else [])
        for csr in csrs:
            bin_name = f"{csr}_mstce{m_stce}_hstce{h_stce}_mtm{m_tm}_htm{h_tm}"
            lines.extend(
                rv32_only(
                    csr,
                    [
                        f"LI(x{rd}, 42)",
                        test_data.add_testcase(bin_name, coverpoint, covergroup),
                        f"csrr x{rd}, {csr}",
                        write_sigupd(rd, test_data),
                    ],
                )
            )
        lines.extend(["RVTEST_TSBI_GOTO_SMODE"] if lower else [])
    lines.extend(stce_tm(test_data, 0, 0, 1, 1, boot))
    test_data.int_regs.return_register(rd)
    return lines


def access_stimecmp(test_data: TestData) -> list[str]:
    """Read stimecmp, and stimecmph on RV32, to check whether the reads are permitted; the values are discarded."""
    reg = test_data.int_regs.get_register()
    lines = [
        f"csrr x{reg}, stimecmp",
        "#if __riscv_xlen == 32",
        f"csrr x{reg}, stimecmph",
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def tm_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with mcounteren.TM = 0/1 and STCE = 1; user mode also crosses scounteren.TM = 0/1.

    Below M-mode, TM = 0 makes the read trap; coverage is sampled at the csrr before the trap.  The suite rests
    with mcounteren.TM = scounteren.TM = 1 and STCE = 0, and these tests restore that state.
    """
    coverpoint = f"cp_{mode}_tm"
    user = mode == "user"
    lines = [
        comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: mcounteren.TM = 0/1, STCE = 1"),
        "",
        *write_stce(test_data, True, mode[0].upper()),
    ]
    for tm_val in (0, 1):
        lines += mcounteren_tm(test_data, bool(tm_val), mode)
        for stm_val in (1, 0) if user else (1,):
            lines += [
                "",
                f"# {coverpoint}: TM = {tm_val}" + (f", scounteren.TM = {stm_val}" if user else ""),
                *([] if stm_val else ["csrci scounteren, 0x2"]),
                *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
                test_data.add_testcase(f"tm{tm_val}_stm{stm_val}" if user else f"tm{tm_val}", coverpoint, covergroup),
                *access_stimecmp(test_data),
                *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
                *([] if stm_val else ["csrsi scounteren, 0x2"]),
            ]
    return [*lines, "", *write_stce(test_data, False, mode[0].upper())]


def stce_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with menvcfg.STCE = 0/1; mcounteren.TM = scounteren.TM = 1 from the suite's resting state.

    Below M-mode, STCE = 0 makes the read trap; coverage is sampled at the csrr before the trap.
    """
    coverpoint = f"cp_{mode}_stce"
    user = mode == "user"
    lines = [comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: menvcfg.STCE = 0/1"), ""]
    for stce_val in (0, 1):
        lines += [
            "",
            f"# {coverpoint}: STCE = {stce_val}",
            *write_stce(test_data, bool(stce_val), mode[0].upper()),
            *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
            test_data.add_testcase(f"stce{stce_val}", coverpoint, covergroup),
            *access_stimecmp(test_data),
            *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
        ]
    return [*lines, "", *write_stce(test_data, False, mode[0].upper())]


def _tsbi_stimecmp_max(test_data: TestData) -> list[str]:
    """stimecmp = -1 through T-SBI, for use while STCE = 0 makes stimecmp inaccessible below M-mode."""
    reg = test_data.int_regs.get_register()
    lines = [
        f"LI(x{reg}, -1)",
        "#if __riscv_xlen == 32",
        tsbi_call(f"csrw stimecmph, x{reg}"),
        "#endif",
        tsbi_call(f"csrw stimecmp, x{reg}"),
    ]
    test_data.int_regs.return_register(reg)
    return lines


def emit_lower_tests(test_data: TestData, covergroup: str, mode: str) -> list[TestChunk]:
    """All Sstc tests for one lower mode as one chunk; starts and ends in S-mode."""
    tc = test_data.begin_test_chunk()
    tc.code = [
        comment_banner("Sstc", f"Supervisor timer (Sstc) stimecmp access tests from {mode} mode"),
        "",
        "# Boot state: mcounteren=-1, scounteren=-1, STCE=0, so S-mode can access stimecmp once",
        "# STCE=1 and only mcounteren.TM/STCE gate U-mode reads. stimecmp has no reset value, so",
        "# park it at -1 before any test sets STCE.",
        *_tsbi_stimecmp_max(test_data),
        "",
    ]
    tc.code += tm_tests(test_data, covergroup, mode)
    tc.code += stce_tests(test_data, covergroup, mode)
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Sstc",
    required_extensions=["Sstc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sstc(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Sstc coverpoints."""
    test_chunks: list[TestChunk] = []
    for mode in ("supervisor", "user"):
        test_chunks.extend(emit_lower_tests(test_data, _CG, mode))
    return test_chunks


@add_priv_test_generator(
    "Sstc",
    required_extensions=["Sm", "Sstc"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_sstcsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Sm-group Sstc coverpoints; the group boots to and stays in M-mode."""
    tc = test_data.begin_test_chunk("Sm")
    tc.code = [
        comment_banner("Sstc_Sm", "Supervisor timer (Sstc) stimecmp access tests from M-mode"),
        "",
    ]
    tc.code += tm_tests(test_data, _CG_SM, "machine")
    tc.code += stce_tests(test_data, _CG_SM, "machine")
    return [test_data.end_test_chunk()]


# H group: boots to HS-mode and writes menvcfg and mcounteren through T-SBI.  An access that menvcfg.STCE or
# mcounteren.TM forbids raises illegal instruction; one that only henvcfg.STCE or hcounteren.TM forbids raises
# virtual instruction.  Both are taken in HS-mode.


def _setup_timecmps(test_data: TestData) -> list[str]:
    """Give stimecmp and vstimecmp distinct values; needs menvcfg.STCE = mcounteren.TM = 1 for the HS-mode writes."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        *stce_tm(test_data, 1, 1, 1, 1, "supervisor"),
        *write64_csr("stimecmp", STIMECMP, tmp_reg),
        *write64_csr("vstimecmp", VSTIMECMP, tmp_reg),
    ]
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _hs_tests(test_data: TestData) -> list[str]:
    """vstimecmp from HS-mode: access control by menvcfg.STCE and mcounteren.TM, and every access type.

    H cp_hcsrwalk walks vstimecmp.
    """
    lines = [
        comment_banner(
            "cp_hs_vstimecmp_accessible",
            "Read vstimecmp (and vstimecmph) for each value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM and\n"
            "hcounteren.TM.  Illegal instruction when menvcfg.STCE = 0 or mcounteren.TM = 0",
        ),
        *_setup_timecmps(test_data),
        *access_cross(test_data, "cp_hs_vstimecmp_accessible", _CG_H, "hs", ["vstimecmp", "vstimecmph"]),
        comment_banner(
            "cp_hs_vstimecmp_accesses",
            "With menvcfg.STCE = mcounteren.TM = 1 and henvcfg.STCE = hcounteren.TM = 0, write 1s and 0s to, set and\n"
            "clear vstimecmp (and vstimecmph)",
        ),
        *stce_tm(test_data, 1, 0, 1, 0, "supervisor"),
        *csr_access_test(test_data, ("vstimecmp", None), _CG_H, "cp_hs_vstimecmp_accesses"),
        *rv32_only("vstimecmph", csr_access_test(test_data, ("vstimecmph", None), _CG_H, "cp_hs_vstimecmp_accesses")),
        *stce_tm(test_data, 0, 0, 1, 1, "supervisor"),
    ]
    return lines


def _vs_tests(test_data: TestData) -> list[str]:
    """stimecmp in VS-mode is vstimecmp; vstimecmp by its own name is not accessible there."""
    tmp_reg, rd = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_vs_stimecmp_accessible",
            "With stimecmp and vstimecmp holding different values, read stimecmp (and stimecmph) in VS-mode for each\n"
            "value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM and hcounteren.TM.  Illegal instruction when\n"
            "menvcfg.STCE = 0 or mcounteren.TM = 0, else virtual instruction when henvcfg.STCE = 0 or\n"
            "hcounteren.TM = 0, else the read returns vstimecmp",
        ),
        *_setup_timecmps(test_data),
        *access_cross(test_data, "cp_vs_stimecmp_accessible", _CG_H, "vs", ["stimecmp", "stimecmph"]),
        comment_banner(
            "cp_vs_vstimecmp_inaccessible",
            "Read vstimecmp (and vstimecmph) in VS-mode for each value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM\n"
            "and hcounteren.TM.  Illegal instruction when HS-mode could not access it, else virtual instruction",
        ),
        *access_cross(test_data, "cp_vs_vstimecmp_inaccessible", _CG_H, "vs", ["vstimecmp", "vstimecmph"]),
        comment_banner(
            "cp_vs_stimecmp_accesses",
            "With menvcfg.STCE = henvcfg.STCE = mcounteren.TM = hcounteren.TM = 1, write 1s and 0s to, set and clear\n"
            "stimecmp (and stimecmph) in VS-mode, then write it and check from HS-mode that vstimecmp changed and\n"
            "stimecmp did not",
        ),
        *stce_tm(test_data, 1, 1, 1, 1, "supervisor"),
        "RVTEST_TSBI_GOTO_VSMODE",
        *csr_access_test(test_data, ("stimecmp", None), _CG_H, "cp_vs_stimecmp_accesses"),
        *rv32_only("stimecmph", csr_access_test(test_data, ("stimecmph", None), _CG_H, "cp_vs_stimecmp_accesses")),
        test_data.add_testcase("write_then_read_from_hs", "cp_vs_stimecmp_accesses", _CG_H),
        *write64_csr("stimecmp", VS_STIMECMP, tmp_reg),
        "RVTEST_TSBI_GOTO_SMODE",
    ]
    for csr in ("vstimecmp", "vstimecmph", "stimecmp", "stimecmph"):
        lines.extend(rv32_only(csr, [f"csrr x{rd}, {csr}", write_sigupd(rd, test_data)]))
    lines.extend(stce_tm(test_data, 0, 0, 1, 1, "supervisor"))
    test_data.int_regs.return_registers([tmp_reg, rd])
    return lines


def _user_tests(test_data: TestData) -> list[str]:
    """stimecmp and vstimecmp are never accessible from VU-mode or U-mode."""
    csrs = ["stimecmp", "stimecmph", "vstimecmp", "vstimecmph"]
    return [
        comment_banner(
            "cp_vu_timecmp_inaccessible",
            "Read stimecmp and vstimecmp (and the upper halves) in VU-mode for each value of menvcfg.STCE,\n"
            "henvcfg.STCE, mcounteren.TM and hcounteren.TM.  Illegal instruction when HS-mode could not access\n"
            "them, else virtual instruction",
        ),
        *_setup_timecmps(test_data),
        *access_cross(test_data, "cp_vu_timecmp_inaccessible", _CG_H, "vu", csrs),
        comment_banner(
            "cp_u_timecmp_inaccessible",
            "Read stimecmp and vstimecmp (and the upper halves) in U-mode for each value of menvcfg.STCE,\n"
            "henvcfg.STCE, mcounteren.TM and hcounteren.TM.  Always illegal instruction",
        ),
        *access_cross(test_data, "cp_u_timecmp_inaccessible", _CG_H, "u", csrs),
    ]


@add_priv_test_generator(
    "Sstc",
    required_extensions=["S", "H", "Sstc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sstch(test_data: TestData) -> list[TestChunk]:
    """Generate tests for H-group Sstc coverpoints; the group boots to HS-mode."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "H_hs")
    tc.code.extend(_hs_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "H_vs")
    tc.code.extend(_vs_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "H_vu")
    tc.code.extend(_user_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "H_vstip")
    tc.code.extend([*_vstip_tests(test_data, _CG_H, "supervisor"), *_htimedelta_tests(test_data, _CG_H, "supervisor")])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


# hip.VSTIP tests, run from HS-mode in the H group and from M-mode in the HSm group.  time has no reset value, so a
# check whose result depends on time compares hip.VSTIP with the comparison computed from a read of time.


def _vstip_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """hip.VSTIP is hvip.VSTIP OR the vstimecmp comparison, which counts only with menvcfg.STCE = henvcfg.STCE = 1.

    vstimecmp is written with both STCE and TM bits set, which HS-mode needs to reach it.
    """
    tmp_reg, expected_reg, count_reg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_vstip",
            "With htimedelta = 0, menvcfg.STCE and henvcfg.STCE = 0/1, hvip.VSTIP = 0/1 and vstimecmp = 0 or all 1s,\n"
            "hip.VSTIP = hvip.VSTIP | (STCE = 1 in both and vstimecmp = 0).  henvcfg.STCE is read-only 0 when\n"
            "menvcfg.STCE = 0",
        ),
        *write64_csr("htimedelta", 0, tmp_reg),
    ]
    for m_stce, h_stce, vstip, compare in product((0, 1), (0, 1), (0, 1), (0, MASK64)):
        if h_stce > m_stce:
            continue  # henvcfg.STCE is read-only zero while menvcfg.STCE = 0
        expected = vstip or (m_stce and h_stce and compare == 0)
        lines.extend(
            [
                *stce_tm(test_data, 1, 1, 1, 1, mode),
                *write64_csr("vstimecmp", compare, tmp_reg),
                *stce_tm(test_data, m_stce, h_stce, 1, 1, mode),
                f"LI(x{tmp_reg}, MIP_VSTIP)",
                f"{'csrs' if vstip else 'csrc'} hvip, x{tmp_reg}",
                f"LI(x{expected_reg}, {'MIP_VSTIP' if expected else 0})",
                test_data.add_testcase(
                    f"mstce{m_stce}_hstce{h_stce}_hvip{vstip}_vstimecmp_{'max' if compare else '0'}",
                    "cp_vstip",
                    covergroup,
                ),
                f"RVTEST_IDLE_FOR_INTERRUPT(x{count_reg}) # let the comparison reach hip.VSTIP",
                f"csrr x{tmp_reg}, hip",
                f"andi x{tmp_reg}, x{tmp_reg}, MIP_VSTIP",
                f"xor x{tmp_reg}, x{tmp_reg}, x{expected_reg}    # 0 when hip.VSTIP is as expected",
                write_sigupd(tmp_reg, test_data),
            ]
        )
    lines.append("csrw hvip, zero")
    test_data.int_regs.return_registers([tmp_reg, expected_reg, count_reg])
    return lines


def _htimedelta_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """hip.VSTIP = ((time + htimedelta) mod 2^64 >= vstimecmp), unsigned, with the expected value computed from time."""
    time_reg, time_hi_reg, tmp_reg, expected_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            "cp_htimedelta",
            "With menvcfg.STCE = henvcfg.STCE = 1 and hvip.VSTIP = 0, set htimedelta and vstimecmp to values around\n"
            "+-2^29..2^61.  hip.VSTIP = ((time + htimedelta) mod 2^64 >= vstimecmp), unsigned; the expected value is\n"
            "computed from a read of time",
        ),
        *stce_tm(test_data, 1, 1, 1, 1, mode),
        "csrw hvip, zero",
    ]
    for delta_name, delta in HTIMEDELTAS.items():
        lines.extend(write64_csr("htimedelta", delta, tmp_reg))
        for compare_name, compare in COMPARES.items():
            d, c = delta & MASK64, compare & MASK64
            lines.extend(
                [
                    *write64_csr("vstimecmp", c, tmp_reg),
                    *read_time(time_reg, time_hi_reg, tmp_reg),
                    "#if __riscv_xlen == 64",
                    f"LI(x{tmp_reg}, {d:#x})",
                    f"add x{time_reg}, x{time_reg}, x{tmp_reg}    # time + htimedelta",
                    f"LI(x{tmp_reg}, {c:#x})",
                    f"sltu x{expected_reg}, x{time_reg}, x{tmp_reg}",
                    "#else",
                    f"LI(x{tmp_reg}, {d & 0xFFFFFFFF:#x})",
                    f"add x{time_reg}, x{time_reg}, x{tmp_reg}",
                    f"sltu x{tmp_reg}, x{time_reg}, x{tmp_reg}    # carry into the upper word",
                    f"add x{time_hi_reg}, x{time_hi_reg}, x{tmp_reg}",
                    f"LI(x{tmp_reg}, {d >> 32:#x})",
                    f"add x{time_hi_reg}, x{time_hi_reg}, x{tmp_reg}    # time + htimedelta",
                    f"LI(x{tmp_reg}, {c >> 32:#x})",
                    f"sltu x{expected_reg}, x{time_hi_reg}, x{tmp_reg}",
                    f"bne x{time_hi_reg}, x{tmp_reg}, 2f",
                    f"LI(x{tmp_reg}, {c & 0xFFFFFFFF:#x})",
                    f"sltu x{expected_reg}, x{time_reg}, x{tmp_reg}",
                    "2:",
                    "#endif",
                    f"xori x{expected_reg}, x{expected_reg}, 1    # time + htimedelta >= vstimecmp",
                    f"slli x{expected_reg}, x{expected_reg}, IRQ_VS_TIMER",
                    test_data.add_testcase(
                        f"htimedelta_{delta_name}_vstimecmp_{compare_name}", "cp_htimedelta", covergroup
                    ),
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{time_hi_reg}) # let the comparison reach hip.VSTIP",
                    f"csrr x{time_reg}, hip",
                    f"andi x{time_reg}, x{time_reg}, MIP_VSTIP",
                    f"xor x{time_reg}, x{time_reg}, x{expected_reg}    # 0 when hip.VSTIP is as expected",
                    write_sigupd(time_reg, test_data),
                ]
            )
    lines.extend(write64_csr("htimedelta", 0, tmp_reg))
    test_data.int_regs.return_registers([time_reg, time_hi_reg, tmp_reg, expected_reg])
    return lines


def _access_tests(test_data: TestData) -> list[str]:
    """M-mode reaches vstimecmp whatever menvcfg.STCE, henvcfg.STCE, mcounteren.TM and hcounteren.TM hold."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_m_vstimecmp_accessible",
            "Read vstimecmp (and vstimecmph) for each value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM and\n"
            "hcounteren.TM",
        ),
        *write64_csr("vstimecmp", MASK64, tmp_reg),
        *access_cross(test_data, "cp_m_vstimecmp_accessible", _CG_HSM, "m", ["vstimecmp", "vstimecmph"]),
        comment_banner(
            "cp_m_vstimecmp_accesses",
            "With menvcfg.STCE = 1 and henvcfg.STCE = mcounteren.TM = hcounteren.TM = 0, write 1s and 0s to,\n"
            "set and clear vstimecmp (and vstimecmph)",
        ),
        *stce_tm(test_data, 1, 0, 0, 0, "machine"),
        *csr_access_test(test_data, ("vstimecmp", None), _CG_HSM, "cp_m_vstimecmp_accesses"),
        *rv32_only("vstimecmph", csr_access_test(test_data, ("vstimecmph", None), _CG_HSM, "cp_m_vstimecmp_accesses")),
        *stce_tm(test_data, 0, 0, 1, 1, "machine"),
    ]
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "Sstc",
    required_extensions=["Sm", "H", "Sstc"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_sstchsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for HSm-group Sstc coverpoints; the group boots to and stays in M-mode."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "HSm_vstip")
    tc.code.extend([*_vstip_tests(test_data, _CG_HSM, "machine"), *_htimedelta_tests(test_data, _CG_HSM, "machine")])

    tc = test_data.new_test_chunk(test_chunks, "HSm_access")
    tc.code.extend(_access_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
