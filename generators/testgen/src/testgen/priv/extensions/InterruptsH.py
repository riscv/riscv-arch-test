##################################
# priv/extensions/InterruptsH.py
#
# Interrupts_cg hypervisor CSR tests that run in HS-mode and VS-mode.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Interrupts hypervisor interrupt CSR test generator (from the hypervisor branch's InterruptsH).

The suite boots to HS-mode, where mideleg delegates the S-level, VS-level and guest external interrupts.
Delegation of the VS-level interrupts to VS-mode is covered by the trigger and priority crosses (Interrupts.py and
InterruptsCommon.py).  The tests here check the hip, hie, vsip and vsie aliases and what VS-mode sees in sip.
"""

from itertools import product

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import IE_CSRS, IP_CSRS, alias_write_tests
from testgen.priv.registry import add_priv_test_generator

_CG = "Interrupts_cg"
# hideleg with no VS-level interrupt delegated, and all three
_HIDELEG = (("none", 0), ("vs", 0x444))


def _vs(combo: int) -> int:
    """VS-level interrupt bits selected by a 3-bit combination: bit 0 VSSI, bit 1 VSTI, bit 2 VSEI."""
    return sum(1 << (4 * i + 2) for i in range(3) if combo >> i & 1)


def _hcsr_tests(test_data: TestData) -> list[str]:
    """hip, hie, vsip and vsie as views of mip, mie, hvip and each other."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        "csrci sstatus, SSTATUS_SIE",
        comment_banner(
            "cp_hip_write",
            "With hideleg = 0 and 0x444, csrw, csrs and csrc each VS-level interrupt bit, and all three, in each of\n"
            "hvip, hip and vsip, starting with the bits clear and set in hvip, and read back hvip, hip, vsip, sip\n"
            "and (through T-SBI) mip.  hvip is writable; in hip and vsip only the VSSIP aliases are, and vsip only\n"
            "where hideleg delegates.  sip never shows the VS-level bits",
        ),
        *alias_write_tests(
            test_data, _CG, "cp_hip_write", IP_CSRS[1:], "hvip", ("hvip", "hip", "vsip", "sip", "mip"), "S", _HIDELEG
        ),
        comment_banner(
            "cp_hie",
            "With hideleg = 0 and 0x444, csrw, csrs and csrc each VS-level interrupt enable bit, and all three, in\n"
            "hie and vsie, starting with the bits clear and set in hie, and read back hie, vsie, sie and (through\n"
            "T-SBI) mie",
        ),
        *alias_write_tests(test_data, _CG, "cp_hie", IE_CSRS[1:], "hie", ("hie", "vsie", "sie", "mie"), "S", _HIDELEG),
    ]
    lines.extend(
        [
            comment_banner(
                "cp_vsip_vsie",
                "For each combination of hideleg.VS*I: read vsie with hie = 0x444, read vsip with hvip = 0x444,\n"
                "write vsie = 0xFFFF and read hie, and write vsip = 0xFFFF and read hvip.  The delegated bits read\n"
                "hie and hip shifted right by 1; the others read zero.  With Sscofpmf, LCOFI is pending and enabled,\n"
                "and vsip.LCOFIP and vsie.LCOFIE read zero because hideleg[13] = 0",
            ),
            "#ifdef SSCOFPMF_SUPPORTED",
            f"LI(x{tmp_reg}, MIP_LCOFIP)",
            f"csrs sie, x{tmp_reg}",
            f"csrs sip, x{tmp_reg}",
            "#endif",
        ]
    )
    for combo in range(8):
        deleg = _vs(combo)
        lines.extend(
            [
                f"LI(x{tmp_reg}, {deleg:#x})",
                f"csrw hideleg, x{tmp_reg}",
                f"LI(x{tmp_reg}, MIP_VS_MASK)",
                f"csrw hie, x{tmp_reg}",
                f"csrw hvip, x{tmp_reg}",
                test_data.add_testcase(f"hideleg_{deleg:03x}_csrr_vsie", "cp_vsip_vsie", _CG),
                f"csrr x{tmp_reg}, vsie",
                write_sigupd(tmp_reg, test_data),
                test_data.add_testcase(f"hideleg_{deleg:03x}_csrr_vsip", "cp_vsip_vsie", _CG),
                f"csrr x{tmp_reg}, vsip",
                write_sigupd(tmp_reg, test_data),
                "csrw hie, zero",
                "csrw hvip, zero",
                f"LI(x{tmp_reg}, 0xFFFF)",
                test_data.add_testcase(f"hideleg_{deleg:03x}_csrw_vsie", "cp_vsip_vsie", _CG),
                f"csrw vsie, x{tmp_reg}",
                f"csrr x{tmp_reg}, hie",
                write_sigupd(tmp_reg, test_data),
                f"LI(x{tmp_reg}, 0xFFFF)",
                test_data.add_testcase(f"hideleg_{deleg:03x}_csrw_vsip", "cp_vsip_vsie", _CG),
                f"csrw vsip, x{tmp_reg}",
                f"csrr x{tmp_reg}, hvip",
                write_sigupd(tmp_reg, test_data),
            ]
        )
    lines.extend(
        [
            "#ifdef SSCOFPMF_SUPPORTED",
            f"LI(x{tmp_reg}, MIP_LCOFIP)",
            f"csrc sip, x{tmp_reg}",
            f"csrc sie, x{tmp_reg}",
            "#endif",
            "csrw hideleg, zero",
            "csrw hie, zero",
            "csrw hvip, zero",
        ]
    )
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _sie_vs_tests(test_data: TestData) -> list[str]:
    """In VS-mode, sip is vsip: it shows the delegated VS-level interrupts and not the pending HS-level ones."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_sie_vs",
            "With sie = 0, sip.SSIP = 1 (pending in HS-mode, not enabled), hideleg = hie = 0x444 and hvip.VSSIP = 0/1,\n"
            "enter VS-mode with vsstatus.SIE = 0, then read sip, or csrs or csrc sip.SSIP and read sip.  sip.SSIP\n"
            "reads and writes hvip.VSSIP, never the HS-level SSIP; back in HS-mode, read hvip and sip.SSIP.\n"
            "With vsstatus.SIE = 1, VS-mode would take VSSI and clear it first (cp_trigger_tsbi)",
        ),
        "#ifdef UDB_SSI_INTR_IMPL",
        "csrw sie, zero",
        "csrsi sip, MIP_SSIP",
        f"LI(x{tmp_reg}, MIP_VS_MASK)",
        f"csrw hideleg, x{tmp_reg}",
        f"csrw hie, x{tmp_reg}",
        f"LI(x{tmp_reg}, SSTATUS_SIE)",
        f"csrc vsstatus, x{tmp_reg}",
    ]
    for vssip, op in product((0, 1), ("csrr", "csrs", "csrc")):
        label = test_data.add_testcase(f"vssip{vssip}_{op}", "cp_sie_vs", _CG)
        access = (
            [label, f"csrr x{tmp_reg}, sip"]
            if op == "csrr"
            else [f"LI(x{tmp_reg}, MIP_SSIP)", label, f"{op} sip, x{tmp_reg}", f"csrr x{tmp_reg}, sip"]
        )
        lines.extend(
            [
                f"LI(x{tmp_reg}, {vssip * 4:#x})",
                f"csrw hvip, x{tmp_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                *access,
                write_sigupd(tmp_reg, test_data),
                "RVTEST_TSBI_GOTO_SMODE",
                f"csrr x{tmp_reg}, hvip",
                write_sigupd(tmp_reg, test_data),
                f"csrr x{tmp_reg}, sip",
                f"andi x{tmp_reg}, x{tmp_reg}, MIP_SSIP",
                write_sigupd(tmp_reg, test_data),
                "csrw hvip, zero",
            ]
        )
    lines.extend(
        [
            "csrci sip, MIP_SSIP",
            "csrw hideleg, zero",
            "csrw hie, zero",
            "#endif // UDB_SSI_INTR_IMPL",
        ]
    )
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "Interrupts",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_interrupts_h(test_data: TestData) -> list[TestChunk]:
    """Interrupts tests of the hypervisor interrupt CSR aliases and of sip in VS-mode."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "h_hcsr")
    tc.code.extend(_hcsr_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "h_vs")
    tc.code.extend(_sie_vs_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
