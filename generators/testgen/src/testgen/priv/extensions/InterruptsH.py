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
With Sscofpmf, they also clear mideleg[13] through T-SBI and check that bit 13 of hideleg, hie and hip is then
read-only zero.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Interrupts_cg"


def _vs(combo: int) -> int:
    """VS-level interrupt bits selected by a 3-bit combination: bit 0 VSSI, bit 1 VSTI, bit 2 VSEI."""
    return sum(1 << (4 * i + 2) for i in range(3) if combo >> i & 1)


def _hcsr_tests(test_data: TestData) -> list[str]:
    """hip, hie, vsip and vsie as views of mip, mie, hvip and each other."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        "csrci sstatus, SSTATUS_SIE",
        comment_banner("cp_hip_write", "Write hip = 0xFFFF and 0, and read hvip and hip: only VSSIP is writable"),
        "csrw hie, zero",
        "csrw hvip, zero",
    ]
    for name, value in (("ones", 0xFFFF), ("zeros", 0)):
        lines.extend(
            [
                f"LI(x{tmp_reg}, {value:#x})",
                test_data.add_testcase(name, "cp_hip_write", _CG),
                f"csrw hip, x{tmp_reg}",
                f"csrr x{tmp_reg}, hvip",
                write_sigupd(tmp_reg, test_data),
                f"csrr x{tmp_reg}, hip",
                write_sigupd(tmp_reg, test_data),
            ]
        )
    lines.extend(
        [
            comment_banner("cp_hie", "With mie = 0x444 and 0x1444 (if GEILEN > 0), read hie"),
            "RVTEST_TSBI_CSR_WRITE(CSR_MIE, MIP_VS_MASK)",
            test_data.add_testcase("mie_444", "cp_hie", _CG),
            f"csrr x{tmp_reg}, hie",
            write_sigupd(tmp_reg, test_data),
            # SGEIE is writable when GEILEN > 0; otherwise mideleg[12] and so SGEIE are implementation-defined
            "#if UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= 1",
            "RVTEST_TSBI_CSR_WRITE(CSR_MIE, MIP_HS_MASK)",
            test_data.add_testcase("mie_1444", "cp_hie", _CG),
            f"csrr x{tmp_reg}, hie",
            write_sigupd(tmp_reg, test_data),
            "#endif",
            "RVTEST_TSBI_CSR_WRITE(CSR_MIE, 0)",
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


def _hroz_tests(test_data: TestData) -> list[str]:
    """With mideleg[13] = 0, bit 13 (LCOFI) of hideleg, hie and hip is read-only zero.

    Sscofpmf makes mideleg[13] writable, and the suite boots with it set.  HS-mode clears it through T-SBI, writes 1
    to bit 13 of each CSR and reads it back, then sets mideleg[13] again.
    """
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_hideleg_lcofi_roz",
            "With mideleg[13] = 0 (cleared through T-SBI), write 1 to bit 13 of hideleg, hie and hip and read it back.\n"
            "Each reads 0",
        ),
        "#ifdef SSCOFPMF_SUPPORTED",
        f"LI(x{tmp_reg}, MIP_LCOFIP)",
        tsbi_call_or_direct(f"csrc mideleg, x{tmp_reg} # mideleg[13] = 0", "S"),
    ]
    for csr in ("hideleg", "hie", "hip"):
        lines.extend(
            [
                f"LI(x{tmp_reg}, MIP_LCOFIP)",
                test_data.add_testcase(f"mideleg_lcofi0_{csr}", "cp_hideleg_lcofi_roz", _CG),
                f"csrw {csr}, x{tmp_reg} # {csr}[13] = 1 is ignored",
                f"csrr x{tmp_reg}, {csr}",
                write_sigupd(tmp_reg, test_data),
                f"csrw {csr}, zero",
            ]
        )
    lines.extend(
        [
            f"LI(x{tmp_reg}, MIP_LCOFIP)",
            tsbi_call_or_direct(f"csrs mideleg, x{tmp_reg} # restore mideleg[13] = 1", "S"),
            "#endif // SSCOFPMF_SUPPORTED",
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
            "enter VS-mode with vsstatus.SIE = 0 and read sip.  sip.SSIP reads hvip.VSSIP, never the HS-level SSIP.\n"
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
    for vssip in (0, 1):
        lines.extend(
            [
                f"LI(x{tmp_reg}, {vssip * 4:#x})",
                f"csrw hvip, x{tmp_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                test_data.add_testcase(f"vssip{vssip}", "cp_sie_vs", _CG),
                f"csrr x{tmp_reg}, sip",
                write_sigupd(tmp_reg, test_data),
                "RVTEST_TSBI_GOTO_SMODE",
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
    tc.code.extend([*_hcsr_tests(test_data), *_hroz_tests(test_data)])

    tc = test_data.new_test_chunk(test_chunks, "h_vs")
    tc.code.extend(_sie_vs_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
