##################################
# priv/extensions/SstcHSm.py
#
# Sstc hypervisor tests that run in M-mode: vstimecmp, htimedelta and hip.VSTIP.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SstcHSm test generator.

The suite boots to M-mode, where vstimecmp is always accessible.  time has no reset value, so a check
whose result depends on time compares hip.VSTIP with the comparison computed from a read of time.
"""

from itertools import product

from testgen.asm.csr import csr_access_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import HTIMEDELTAS, read_time, write64
from testgen.priv.extensions.SstcCommon import access_cross, rv32_only, stce_tm, vstimecmp_int_tests
from testgen.priv.registry import add_priv_test_generator

_CG = "SstcHSm_m_cg"
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


def _vstip_check(test_data: TestData, expected_reg: int, tmp_reg: int, count_reg: int) -> list[str]:
    """Read hip until VSTIP equals expected_reg (0 or MIP_VSTIP), for at most RVMODEL_INTERRUPT_LATENCY reads,
    and record the difference.  A change of the timer comparison reaches hip.VSTIP eventually, not at once."""
    return [
        f"LA(x{count_reg}, RVMODEL_INTERRUPT_LATENCY)",
        "1:",
        f"csrr x{tmp_reg}, hip",
        f"andi x{tmp_reg}, x{tmp_reg}, MIP_VSTIP",
        f"xor x{tmp_reg}, x{tmp_reg}, x{expected_reg}",
        f"beqz x{tmp_reg}, 2f",
        f"addi x{count_reg}, x{count_reg}, -1",
        f"bnez x{count_reg}, 1b",
        "2:",
        write_sigupd(tmp_reg, test_data),
    ]


def _vstip_tests(test_data: TestData) -> list[str]:
    """hip.VSTIP is hvip.VSTIP OR the vstimecmp comparison, which counts only with menvcfg.STCE = henvcfg.STCE = 1."""
    tmp_reg, expected_reg, count_reg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_vstip",
            "With htimedelta = 0, menvcfg.STCE and henvcfg.STCE = 0/1, hvip.VSTIP = 0/1 and vstimecmp = 0 or all 1s,\n"
            "hip.VSTIP = hvip.VSTIP | (STCE = 1 in both and vstimecmp = 0).  henvcfg.STCE is read-only 0 when\n"
            "menvcfg.STCE = 0",
        ),
        *write64("htimedelta", 0, tmp_reg),
    ]
    for m_stce, h_stce, vstip, compare in product((0, 1), (0, 1), (0, 1), (0, MASK64)):
        if h_stce > m_stce:
            continue  # henvcfg.STCE is read-only zero while menvcfg.STCE = 0
        expected = vstip or (m_stce and h_stce and compare == 0)
        lines.extend(
            [
                *stce_tm(test_data, m_stce, h_stce, 1, 1, "machine"),
                *write64("vstimecmp", compare, tmp_reg),
                f"LI(x{tmp_reg}, MIP_VSTIP)",
                f"{'csrs' if vstip else 'csrc'} hvip, x{tmp_reg}",
                f"LI(x{expected_reg}, {'MIP_VSTIP' if expected else 0})",
                test_data.add_testcase(
                    f"mstce{m_stce}_hstce{h_stce}_hvip{vstip}_vstimecmp_{'max' if compare else '0'}", "cp_vstip", _CG
                ),
                *_vstip_check(test_data, expected_reg, tmp_reg, count_reg),
            ]
        )
    lines.append("csrw hvip, zero")
    test_data.int_regs.return_registers([tmp_reg, expected_reg, count_reg])
    return lines


def _htimedelta_tests(test_data: TestData) -> list[str]:
    """hip.VSTIP = ((time + htimedelta) mod 2^64 >= vstimecmp), unsigned, with the expected value computed from time."""
    time_reg, time_hi_reg, tmp_reg, expected_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            "cp_htimedelta",
            "With menvcfg.STCE = henvcfg.STCE = 1 and hvip.VSTIP = 0, set htimedelta and vstimecmp to values around\n"
            "+-2^29..2^61.  hip.VSTIP = ((time + htimedelta) mod 2^64 >= vstimecmp), unsigned; the expected value is\n"
            "computed from a read of time",
        ),
        *stce_tm(test_data, 1, 1, 1, 1, "machine"),
        "csrw hvip, zero",
    ]
    for delta_name, delta in HTIMEDELTAS.items():
        lines.extend(write64("htimedelta", delta, tmp_reg))
        for compare_name, compare in COMPARES.items():
            d, c = delta & MASK64, compare & MASK64
            lines.extend(
                [
                    *write64("vstimecmp", c, tmp_reg),
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
                    test_data.add_testcase(f"htimedelta_{delta_name}_vstimecmp_{compare_name}", "cp_htimedelta", _CG),
                    *_vstip_check(test_data, expected_reg, time_reg, time_hi_reg),
                ]
            )
    lines.extend(write64("htimedelta", 0, tmp_reg))
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
        *write64("vstimecmp", MASK64, tmp_reg),
        *access_cross(test_data, "cp_m_vstimecmp_accessible", _CG, "m", ["vstimecmp", "vstimecmph"]),
        comment_banner(
            "cp_m_vstimecmp_accesses",
            "With menvcfg.STCE = 1 and henvcfg.STCE = mcounteren.TM = hcounteren.TM = 0, write 1s and 0s to,\n"
            "set and clear vstimecmp (and vstimecmph)",
        ),
        *stce_tm(test_data, 1, 0, 0, 0, "machine"),
        *csr_access_test(test_data, ("vstimecmp", None), _CG, "cp_m_vstimecmp_accesses"),
        *rv32_only("vstimecmph", csr_access_test(test_data, ("vstimecmph", None), _CG, "cp_m_vstimecmp_accesses")),
        *stce_tm(test_data, 0, 0, 1, 1, "machine"),
    ]
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "SstcHSm",
    required_extensions=["Sm", "H", "Sstc"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_sstchsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SstcHSm suite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "vstip")
    tc.code.extend([*_vstip_tests(test_data), *_htimedelta_tests(test_data)])

    tc = test_data.new_test_chunk(test_chunks, "access")
    tc.code.extend([*_access_tests(test_data), *vstimecmp_int_tests(test_data, _CG, "machine")])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
