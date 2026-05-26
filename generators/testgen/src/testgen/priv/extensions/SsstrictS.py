##################################
# priv/extensions/SsstrictS.py
#
# Ssstrict supervisor-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from S-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictS — supervisor-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.

Structure
---------
1. Switch to S-mode via RVTEST_GOTO_LOWER_MODE Smode.
2. CSR sweep from S-mode (all non-skipped CSRs).
   - S-mode CSRs (priv=01) are accessible and exercise S-mode CSR coverage.
   - M-mode CSRs (priv=11) raise illegal-instruction from S-mode.
   - H-mode CSRs (priv=10) are SKIPPED: in HS-mode (S with H extension)
     they would be accessible, so behaviour is config-dependent.
   - satp (0x180) is SKIPPED: reading/writing satp flushes the TLB and
     changes address-translation mode, causing unpredictable side effects.
3. Shadow CSR writes: write mstatus/mie/mip from M-mode, then read
   sstatus/sie/sip from S-mode to cover the M<->S shadow relationship.
4. Return to M-mode via ecall, then run the illegal instruction and
   compressed sweeps (same encoding templates as SsstrictSm, from M-mode
   so the fast handler can advance mepc correctly for every trap).
"""

from random import seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

from .SsstrictCommon import SAFE_REGS, generate_compressed_instr, generate_csr_sweep_body, generate_illegal_instr

# ── CSR skip set (S-mode) ─────────────────────────────────────────────────

_S_CSR_SKIP: frozenset[int] = frozenset(
    [0x180]  # satp  — skip: TLB flush / address-translation mode change
    + [0x104]  # sie   — skip: all-ones write enables S-mode interrupts; covered in shadow test
    + [0x105]  # stvec — skip: breaks the S -> S delegated trap by causing a fetch-fault on the next trap
    + [0x140]  # sscratch — skip: avoid corrupting framework save area
    + [0x144]  # sip   — skip: all-ones write asserts SSIP software interrupt; covered in shadow test
    + [0x105]  # stvec   — skip: stvec not to update itself
    + [0x140]  # sscratch   — skip: sscratch not to update itself
    + [0x5A8]  # scontext — skip: Sail traps (unimplemented Sdtrig), Spike does not; diverges signature
    + list(range(0x200, 0x300))  # H-mode std0 — skip: accessible from HS-mode
    + list(range(0x600, 0x700))  # H-mode std1 — skip: HS-mode ambiguity
    + list(range(0xA00, 0xB00))  # H-mode std2 — skip: HS-mode ambiguity
    + list(range(0xE00, 0xF00))  # H-mode std3 — skip: HS-mode ambiguity
    + list(range(0x5C0, 0x600))  # S-mode custom1
    + list(range(0x6C0, 0x700))  # H-mode custom1
    + list(range(0x9C0, 0xA00))  # S-mode custom2
    + list(range(0xAC0, 0xB00))  # H-mode custom2
    + list(range(0x800, 0x900))  # user custom2
    + list(range(0xCC0, 0xD00))  # user custom3
    + list(range(0xDC0, 0xE00))  # S-mode custom3
    + list(range(0xEC0, 0xF00))  # H-mode custom3
)


# ── S-mode CSR sweep ──────────────────────────────────────────────────────


def _generate_csr_tests_s(test_data: TestData) -> list[str]:
    """cp_csrr / cp_csrw_corners / cp_csrcs from S-mode.

    Switches to S-mode, sweeps all non-skipped CSRs, then returns to
    M-mode via ecall so subsequent sections can use the fast handler.
    """
    covergroup = "SsstrictS_scsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_csrr / cp_csrw_corners / cp_csrcs (S-mode)",
            "Read, write 0s/1s, set, clear every non-skipped CSR from S-mode.\n"
            "M-mode CSRs raise illegal-instruction from S-mode.\n"
            "H-mode CSRs skipped — accessible from HS-mode (config-dependent).\n"
            "satp skipped — TLB flush / address-translation side effects.",
        )
    )

    # Mode switch is handled by _SPLIT_FILE_SMODE_GPR_INIT prepended to every
    # split file by generate/priv.py: each file starts from M-mode, runs
    # RVTEST_GOTO_LOWER_MODE Smode (writing a valid M-mode sp into the framework
    # save area), then reloads GPRs before entering the body.  The body itself
    # stays entirely in S-mode — illegal accesses to M-mode CSRs are caught by
    # the S-mode strap handler (stvec) which writes scause/sepc/stval to the
    # signature and advances sepc.  RVTEST_CODE_END's ecall from S-mode is not
    # delegated (medeleg bit 9 is 0), so it goes to Mtrampoline which restores
    # the saved M-mode sp and ends the test cleanly.
    all_csrs = [a for a in range(4096) if a not in _S_CSR_SKIP]
    lines.extend(generate_csr_sweep_body(test_data, covergroup, all_csrs))
    lines.append("")

    return lines


# ── Shadow CSR writes (M-mode writes, S-mode shadow verification) ─────────


def _generate_shadow_csr(test_data: TestData) -> list[str]:
    """cp_shadow_m / cp_shadow_s — mstatus/mie/mip shadow relationship.

    Writes all-ones and all-zeros to mstatus/mie from M-mode (mip skipped —
    writing MSIP/SSIP with MIE potentially enabled can fire spurious interrupts),
    then reads the S-mode shadow registers sstatus/sie/sip from S-mode.

    Safety invariants:
      M-mode: mie is cleared before any mstatus write so a transient MIE=1
              in mstatus cannot cause interrupt delivery.  Originals for both
              mstatus and mie are saved via csrr and fully restored afterward.
      S-mode: each shadow CSR is saved (csrr), corner-tested, then restored
              (csrw) before the next CSR is touched.  Ordering sstatus → sie →
              sip ensures sstatus.SIE=original(0) whenever sie or sip carry a
              transient all-ones value, so no interrupt can be delivered.
    """
    covergroup = "SsstrictS_scsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_shadow_m / cp_shadow_s",
            "Write mstatus/mie from M-mode (all 0s / all 1s),\n"
            "then read sstatus/sie/sip from S-mode to cover the shadow relationship.\n"
            "mip skipped in M-mode section (MSIP/SSIP write unsafe while MIE may be 1).",
        )
    )

    # Fixed registers for M-mode section (no random sampling — we need specific slots).
    r_sv_mstatus = SAFE_REGS[0]  # x7 — saved mstatus original
    r_sv_mie = SAFE_REGS[1]  # x8 — saved mie original
    r_scratch = SAFE_REGS[2]  # x9 — scratch: li -1, csrrw discard destination

    lines.extend(
        [
            "",
            "# cp_shadow_m: write mstatus/mie from M-mode (originals saved and restored)",
            f"\tcsrr x{r_sv_mstatus}, 0x300",  # save mstatus original
            f"\tcsrr x{r_sv_mie}, 0x304",  # save mie original
            # Disable M-mode interrupts before any mstatus write.  A transient
            # MIE=1 written into mstatus is harmless when mie=0 (no source enabled).
            "\tcsrw 0x304, x0",  # mie = 0
        ]
    )

    # Test mstatus corner values (mie=0 throughout).
    lines.extend(
        [
            f"\t{test_data.add_testcase('mstatus_ones', 'cp_shadow_m', covergroup)}",
            f"\tli x{r_scratch}, -1",
            f"\tcsrrw x{r_scratch}, 0x300, x{r_scratch}",  # write all-ones (mie=0, safe)
            f"\t{test_data.add_testcase('mstatus_zeros', 'cp_shadow_m', covergroup)}",
            f"\tcsrrw x{r_scratch}, 0x300, x0",  # write all-zeros → mstatus.MIE=0
        ]
    )

    # Test mie corner values while mstatus.MIE=0.
    lines.extend(
        [
            f"\t{test_data.add_testcase('mie_ones', 'cp_shadow_m', covergroup)}",
            f"\tli x{r_scratch}, -1",
            f"\tcsrrw x{r_scratch}, 0x304, x{r_scratch}",  # write all-ones (MIE=0, safe)
            f"\t{test_data.add_testcase('mie_zeros', 'cp_shadow_m', covergroup)}",
            f"\tcsrrw x{r_scratch}, 0x304, x0",  # write all-zeros
            f"\tcsrw 0x304, x{r_sv_mie}",  # restore mie original
            f"\tcsrw 0x300, x{r_sv_mstatus}",  # restore mstatus original
        ]
    )

    # Fixed registers for S-mode section.
    r_sv = SAFE_REGS[0]  # x7 — saved CSR original for current iteration
    r_ones = SAFE_REGS[1]  # x8 — all-ones constant, loaded once
    r_rd = SAFE_REGS[2]  # x9 — csrrw destination (result discarded)

    lines.extend(
        [
            "",
            "# cp_shadow_s: write/read sstatus/sie/sip from S-mode",
            "# Each CSR is saved (csrr), corner-tested, then fully restored (csrw)",
            "# before the next CSR is touched — prevents spurious interrupt delivery.",
            "\tRVTEST_GOTO_LOWER_MODE Smode",
            f"\tli x{r_ones}, -1",  # load -1 once, reuse for all three CSRs
        ]
    )

    # Ordering: sstatus → sie → sip.
    for csr_name, csr_addr in [("sstatus", "0x100"), ("sie", "0x104"), ("sip", "0x144")]:
        lines.extend(
            [
                f"\tcsrr x{r_sv}, {csr_addr}",  # save original
                f"\t{test_data.add_testcase(f'{csr_name}_ones', 'cp_shadow_s', covergroup)}",
                f"\tcsrrw x{r_rd}, {csr_addr}, x{r_ones}",  # write all-ones
                f"\t{test_data.add_testcase(f'{csr_name}_zeros', 'cp_shadow_s', covergroup)}",
                f"\tcsrrw x{r_rd}, {csr_addr}, x0",  # write all-zeros
                f"\tcsrw {csr_addr}, x{r_sv}",  # restore original
            ]
        )

    # Return to M-mode
    lines.extend(
        [
            "",
            "\tRVTEST_GOTO_MMODE",
            "",
        ]
    )

    return lines


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictS",
    required_extensions=["S", "Zicsr"],
    march_extensions=[
        # Zcf excluded — RV32-only.
        # Vector excluded — covered by SsstrictV.
        # Zbc/Zacas/Zcb excluded: not in non-max configs, not supported by GCC < 14.
        "I",
        "V",
        "Zicsr",
    ],
)
def make_ssstrictss(test_data: TestData) -> list[str]:
    """SsstrictS — supervisor-mode strict compliance tests."""
    seed(42)
    lines: list[str] = []
    lines.extend(_generate_csr_tests_s(test_data))
    lines.extend(_generate_shadow_csr(test_data))
    lines.extend(generate_illegal_instr(test_data, "SsstrictS_instr_cg"))
    lines.extend(generate_compressed_instr(test_data, "SsstrictS_comp_instr_cg"))
    return lines
