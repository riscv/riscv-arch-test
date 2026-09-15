##################################
# priv/extensions/H.py
#
# H privileged extension test generator: HS-mode and VS-mode trap handler,
# T-SBI, and two-stage address translation.
# SPDX-License-Identifier: Apache-2.0
##################################

"""H extension test generator: the HS/VS trap handler, T-SBI and two-stage translation paths."""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "H_cg"
INDENT = "  "

# Both stages map TEST_GIB identity so every guest address is numerically what
# HS-mode sees. HOLE_GIB is mapped by the VS-stage and deliberately not by the
# G-stage, so a guest access to it faults in the G-stage and nowhere else.
# ALIAS_GIB is a second, non-identity VS-stage view of TEST_GIB: code running
# there has a guest virtual PC that is not its own physical address.
_TEST_GIB = 0x80000000
_HOLE_GIB = 0x40000000
_ALIAS_GIB = 0xC0000000

# G-stage PTEs are always checked as user accesses, so PTE_U must be set.
_G_PERMS = "(PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_A | PTE_D)"
# VS-stage pages belong to the guest supervisor, so PTE_U is clear.
_VS_PERMS = "(PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D)"


def _case(test_data: TestData, bin_name: str, coverpoint: str) -> str:
    return test_data.add_testcase(bin_name, coverpoint, _CG)


def _gen_hs_csr_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """HS-mode hypervisor CSR access, before anything has entered a guest."""
    code = [
        "",
        "/////////////////////////////////",
        "// HS-mode hypervisor CSR access",
        "//",
        "// These run first, so they also show that the H trap prolog left the",
        "// hypervisor CSRs in a sane state rather than, say, ORing a stale",
        "// pointer into hgatp.",
        "/////////////////////////////////",
        "",
        _case(test_data, "bare", "cp_hgatp_mode"),
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}srli x{check}, x{check}, MODE_LSB   # hgatp.MODE, whatever XLEN says that is",
        write_sigupd(check, test_data),
        "",
        _case(test_data, "clear", "cp_hstatus_spv"),
        f"{INDENT}csrr x{check}, hstatus",
        f"{INDENT}LI(x{temp}, HSTATUS_SPV)",
        f"{INDENT}and x{check}, x{check}, x{temp}   # SPV must be 0: we have never left HS-mode",
        write_sigupd(check, test_data),
        "",
        "# hedeleg and hideleg are WARL. Write all ones and record what sticks.",
        f"{INDENT}LI(x{temp}, -1)",
        _case(test_data, "all_ones", "cp_hedeleg_warl"),
        f"{INDENT}csrw hedeleg, x{temp}",
        f"{INDENT}csrr x{check}, hedeleg",
        write_sigupd(check, test_data),
        f"{INDENT}csrw hedeleg, x0",
        "",
        f"{INDENT}LI(x{temp}, -1)",
        _case(test_data, "all_ones", "cp_hideleg_warl"),
        f"{INDENT}csrw hideleg, x{temp}",
        f"{INDENT}csrr x{check}, hideleg",
        write_sigupd(check, test_data),
        f"{INDENT}csrw hideleg, x0",
    ]
    return code


def _gen_tsbi_from_hs_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """T-SBI calls made from HS-mode, which reach M-mode as cause 9."""
    label = _case(test_data, "from_hs", "cp_tsbi_ecall")
    site = label.rstrip(":") + "_site"
    return [
        "",
        "/////////////////////////////////",
        "// T-SBI from HS-mode",
        "//",
        "// An ecall from HS-mode is cause 9, which RVTEST_BOOT_TO_SMODE leaves",
        "// undelegated so it reaches the M-mode handler. ECALL_TEST returns the",
        "// ecall's own address, four bytes past this label because the macro",
        "// loads a0 first.",
        "/////////////////////////////////",
        "",
        label,
        f"{site}:",
        f"{INDENT}RVTEST_TSBI_ECALL_TEST",
        f"{INDENT}LA(x{temp}, {site})",
        f"{INDENT}sub x{check}, a0, x{temp}",
        write_sigupd(check, test_data),
        "",
        "# Read an M-mode CSR from HS-mode through the T-SBI. The handler runs the",
        "# csrr while servicing our ecall, so mstatus.MPP must read back as S.",
        _case(test_data, "mstatus_mpp_from_hs", "cp_tsbi_csr_read"),
        f"{INDENT}RVTEST_TSBI_CSR_READ(CSR_MSTATUS)",
        f"{INDENT}srli x{check}, a0, MPP_LSB",
        f"{INDENT}andi x{check}, x{check}, 0x3",
        write_sigupd(check, test_data),
    ]


def _gen_hlv_hsv_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """hlv/hsv from HS-mode with both translation stages Bare."""
    return [
        "",
        "/////////////////////////////////",
        "// Hypervisor load/store from HS-mode",
        "//",
        "// hlv/hsv access guest memory with the translation the guest would see.",
        "// Both stages are Bare here, so this is a plain physical access, but the",
        "// instructions only decode when H is present and they take the HS-mode",
        "// permission path.",
        "/////////////////////////////////",
        "",
        f"{INDENT}LA(x{temp}, H_guest_scratch)",
        f"{INDENT}LI(x{check}, 0x5AA5)",
        _case(test_data, "roundtrip", "cp_hlv_hsv"),
        "#if __riscv_xlen == 32",
        f"{INDENT}hsv.w x{check}, (x{temp})",
        f"{INDENT}li x{check}, 0",
        f"{INDENT}hlv.w x{check}, (x{temp})",
        "#else",
        f"{INDENT}hsv.d x{check}, (x{temp})",
        f"{INDENT}li x{check}, 0",
        f"{INDENT}hlv.d x{check}, (x{temp})",
        "#endif",
        write_sigupd(check, test_data),
    ]


def _gen_vsmode_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """Enter VS-mode, trap out of it, and come back through the T-SBI."""
    vs_ecall = _case(test_data, "from_vs", "cp_tsbi_ecall")
    vs_site = vs_ecall.rstrip(":") + "_site"
    code = [
        "",
        "/////////////////////////////////",
        "// VS-mode",
        "//",
        "// TSBI_GOTO_VSMODE puts the hart in VS-mode. Everything below runs with",
        "// V=1 until the guest asks to come back.",
        "/////////////////////////////////",
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_VSMODE",
        "",
        "# In VS-mode the S-mode CSR names alias to the VS-mode CSRs, so this",
        "# writes vsstatus. Reading the same bit back in HS-mode below shows the",
        "# two really are different registers.",
        f"{INDENT}LI(x{temp}, SSTATUS_SPP)",
        _case(test_data, "spp_set", "cp_vsstatus_alias"),
        f"{INDENT}csrs sstatus, x{temp}",
        f"{INDENT}csrr x{check}, sstatus",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        write_sigupd(check, test_data),
        "",
        "# Accessing an HS-mode CSR from VS-mode raises a virtual instruction",
        "# exception (cause 22). The check register keeps its pre-trap value,",
        "# which is how we know the instruction never completed.",
        f"{INDENT}li x{check}, -1",
        _case(test_data, "hs_csr_from_vs", "cp_virtual_instruction"),
        f"{INDENT}csrr x{check}, hgatp",
        write_sigupd(check, test_data),
        "",
        "# An ecall from VS-mode is cause 10. Whether it is delegated to HS-mode",
        "# or taken in M-mode is a WARL property of medeleg, so both handlers have",
        "# to recognise it as a T-SBI call for this to work on every DUT.",
        vs_ecall,
        f"{vs_site}:",
        f"{INDENT}RVTEST_TSBI_ECALL_TEST",
        f"{INDENT}LA(x{temp}, {vs_site})",
        f"{INDENT}sub x{check}, a0, x{temp}",
        write_sigupd(check, test_data),
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_SMODE   # leave the guest",
        "",
        "# Back in HS-mode: sstatus is the real sstatus again, so the SPP bit set",
        "# from inside the guest must not be visible here.",
        _case(test_data, "spp_not_in_hs", "cp_vsstatus_alias"),
        f"{INDENT}csrr x{check}, sstatus",
        f"{INDENT}LI(x{temp}, SSTATUS_SPP)",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        write_sigupd(check, test_data),
        "",
        "# GOTO_SMODE had to clear hstatus.SPV to get us out of the guest; had it",
        "# only set sstatus.SPP, the sret would have gone straight back into VS.",
        _case(test_data, "after_vs_trap", "cp_hstatus_spv"),
        f"{INDENT}csrr x{check}, hstatus",
        f"{INDENT}LI(x{temp}, HSTATUS_SPV)",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        f"{INDENT}sltu x{check}, x0, x{check}",
        write_sigupd(check, test_data),
    ]
    return code


def _gen_twostage_setup(test_data: TestData, check: int, temp: int) -> list[str]:
    """Build the G-stage and VS-stage page tables and turn both stages on."""
    return [
        "",
        "/////////////////////////////////",
        "// Two-stage address translation",
        "//",
        f"// G-stage:  GPA 0x{_TEST_GIB:08X} -> PA  0x{_TEST_GIB:08X}   (identity gigapage)",
        f"// VS-stage: VA  0x{_TEST_GIB:08X} -> GPA 0x{_TEST_GIB:08X}   (identity gigapage)",
        f"//           VA  0x{_HOLE_GIB:08X} -> GPA 0x{_HOLE_GIB:08X}   (no G-stage entry: faults)",
        f"//           VA  0x{_ALIAS_GIB:08X} -> GPA 0x{_TEST_GIB:08X}   (non-identity view)",
        "/////////////////////////////////",
        "",
        f"{INDENT}LI(t0, 0x{_TEST_GIB:08X})",
        f"{INDENT}G_PTE_SETUP_PA_REG(sv39x4, t0, {_G_PERMS}, 0x{_TEST_GIB:08X}, LEVEL2)",
        f"{INDENT}VS_PTE_SETUP(sv39, GPA, 0x{_TEST_GIB:08X}, {_VS_PERMS}, 0x{_TEST_GIB:08X}, LEVEL2)",
        f"{INDENT}VS_PTE_SETUP(sv39, GPA, 0x{_HOLE_GIB:08X}, {_VS_PERMS}, 0x{_HOLE_GIB:08X}, LEVEL2)",
        f"{INDENT}VS_PTE_SETUP(sv39, GPA, 0x{_TEST_GIB:08X}, {_VS_PERMS}, 0x{_ALIAS_GIB:08X}, LEVEL2)",
        f"{INDENT}HGATP_SETUP(sv39x4)",
        # The trailing comment must not contain the tokens PA or GPA: they are
        # object-like macros, and cpp expands them inside a `#` assembler
        # comment because it has no idea the line is a comment.
        f"{INDENT}VSATP_SETUP(sv39, PA)   # the guest root table is named by its physical address",
        f"{INDENT}hfence.gvma",
        f"{INDENT}hfence.vvma",
        f"{INDENT}sfence.vma",
        "",
        "# Both stages are live, but HS-mode is unaffected: the G-stage only",
        "# applies with V=1. Record the modes so a mismatch below points at",
        "# hgatp/vsatp rather than at anything the guest did.",
        _case(test_data, "sv39x4", "cp_hgatp_mode"),
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}srli x{check}, x{check}, MODE_LSB",
        write_sigupd(check, test_data),
        "",
        _case(test_data, "sv39", "cp_vsatp_mode"),
        f"{INDENT}csrr x{check}, vsatp",
        f"{INDENT}srli x{check}, x{check}, MODE_LSB",
        write_sigupd(check, test_data),
    ]


def _gen_twostage_guest(test_data: TestData, check: int, temp: int, addr: int) -> list[str]:
    """Run the guest under both translation stages and trap it three ways."""
    alias_delta = _ALIAS_GIB - _TEST_GIB
    ident_label = _case(test_data, "load_store", "cp_twostage_access")
    code = [
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_VSMODE",
        "",
        "# A load and store through both stages. Reaching the next instruction at",
        "# all means the guest's fetches are translating too.",
        f"{INDENT}LA(x{addr}, H_guest_data)",
        f"{INDENT}LI(x{check}, 0x1234ABCD)",
        ident_label,
        f"{INDENT}SREG x{check}, 0(x{addr})",
        f"{INDENT}li x{check}, 0",
        f"{INDENT}LREG x{check}, 0(x{addr})",
        write_sigupd(check, test_data),
        "",
        "# An exception whose xEPC is a guest virtual address. The HS handler has",
        "# to read this instruction's low halfword to learn its width, which means",
        "# reading at a guest VA.",
        f"{INDENT}li x{check}, -1",
        _case(test_data, "translated_guest", "cp_virtual_instruction"),
        f"{INDENT}csrr x{check}, hgatp",
        write_sigupd(check, test_data),
        "",
        "# Jump to the aliased view, where the guest's PC is no longer its own",
        "# physical address. A host-side load at xEPC now reads the wrong memory.",
        f"{INDENT}LA(x{addr}, 1f)",
        f"{INDENT}LI(x{temp}, 0x{alias_delta:08X})",
        f"{INDENT}add x{addr}, x{addr}, x{temp}",
        f"{INDENT}jr x{addr}",
        "1:",
        f"{INDENT}li x{check}, -1",
        _case(test_data, "non_identity_guest_va", "cp_virtual_instruction"),
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}addi x{check}, x{check}, 2   # reached only if the handler skipped four bytes",
        write_sigupd(check, test_data),
        "",
        "# The same thing with an instruction chosen so that a short skip is",
        "# visible rather than merely wrong. 0x000024F3 is 'csrr x9, 0x000', whose",
        "# upper halfword is 0x0000 -- the defined illegal compressed encoding. A",
        "# handler that misreads the width resumes two bytes in, lands on that",
        "# halfword and takes a second trap that shows up in the trap signature.",
        f"{INDENT}li x{check}, -1",
        _case(test_data, "non_identity_guest_va", "cp_illegal_instruction"),
        f"{INDENT}.word 0x000024F3",
        f"{INDENT}addi x{check}, x{check}, 3",
        write_sigupd(check, test_data),
        "",
        f"{INDENT}LA(x{addr}, 2f)   # an alias address, since PC is in the alias window",
        f"{INDENT}LI(x{temp}, 0x{alias_delta:08X})",
        f"{INDENT}sub x{addr}, x{addr}, x{temp}",
        f"{INDENT}jr x{addr}",
        "2:",
        "",
        f"# A guest-page fault. 0x{_HOLE_GIB:08X} resolves in the VS-stage and has no",
        "# G-stage entry, so this load raises a load guest-page fault (cause 21)",
        "# and htval takes the faulting guest physical address, shifted right by 2.",
        f"{INDENT}LI(x{addr}, 0x{_HOLE_GIB:08X})",
        f"{INDENT}li x{check}, -1",
        _case(test_data, "load", "cp_guest_page_fault"),
        f"{INDENT}LREG x{check}, 0(x{addr})",
        write_sigupd(check, test_data),
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_SMODE   # back to HS-mode",
        "",
        "# The faulting guest physical address is not read back here. htval is",
        "# per-trap state and every trap into HS-mode rewrites it, including the",
        "# ecall that just brought us out of the guest, so by the time HS-mode code",
        "# runs the fault's htval is already gone. The framework captures it while",
        "# it is still live, in word 4 of the trap signature entry. What is",
        "# checkable here is the other half of the rule: htval reads as zero after",
        "# a trap whose cause does not define it.",
        _case(test_data, "zero_after_ecall", "cp_htval"),
        f"{INDENT}csrr x{check}, htval",
        write_sigupd(check, test_data),
        "",
        "# Turn the guest's translation off again so the epilogs run with a plain",
        "# machine state, and show hgatp is writable back to Bare.",
        f"{INDENT}csrw vsatp, zero",
        _case(test_data, "back_to_bare", "cp_hgatp_mode"),
        f"{INDENT}csrw hgatp, zero",
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}hfence.gvma",
        write_sigupd(check, test_data),
    ]
    return code


# Invisible trap emulation cannot yet handle traps from VS or VU mode, so
# check_defines.h rejects it on a hypervisor build. It is enabled whenever the
# time CSR is emulated, which is what TIME_CSR_IMPLEMENTED=false means.
_PARAMS = ["TIME_CSR_IMPLEMENTED: true"]


@add_priv_test_generator(
    "H",
    required_extensions=["S", "H"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=_PARAMS,
)
def make_h(test_data: TestData) -> list[TestChunk]:
    """Generate the HS-mode and VS-mode trap handler and T-SBI tests."""
    test_chunks: list[TestChunk] = []

    check, temp = test_data.int_regs.get_registers(2)

    tc = test_data.begin_test_chunk("hsmode")
    tc.code.extend(_gen_hs_csr_tests(test_data, check, temp))
    tc.code.extend(_gen_tsbi_from_hs_tests(test_data, check, temp))
    tc.code.extend(_gen_hlv_hsv_tests(test_data, check, temp))
    tc.code.extend(_gen_vsmode_tests(test_data, check, temp))
    tc.raw_data.extend([".p2align 3", "H_guest_scratch:", "  .dword 0"])
    test_chunks.append(test_data.end_test_chunk())

    test_data.int_regs.return_registers([check, temp])
    return test_chunks


@add_priv_test_generator(
    "H",
    required_extensions=["S", "H"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=[*_PARAMS, "MXLEN: 64"],
)
def make_h_twostage(test_data: TestData) -> list[TestChunk]:
    """Generate the two-stage translation tests (Sv39x4 G-stage over Sv39 VS-stage)."""
    test_chunks: list[TestChunk] = []

    check, temp, addr = test_data.int_regs.get_registers(3)

    tc = test_data.begin_test_chunk("twostage")
    tc.code.extend(_gen_twostage_setup(test_data, check, temp))
    tc.code.extend(_gen_twostage_guest(test_data, check, temp, addr))
    tc.raw_data.extend([".p2align 3", "H_guest_data:", "  .dword 0"])
    test_chunks.append(test_data.end_test_chunk())

    test_data.int_regs.return_registers([check, temp, addr])
    return test_chunks
