##################################
# priv/extensions/H.py
#
# H privileged extension test generator: HS, VS and VU-mode trap handler,
# T-SBI, and two-stage address translation.
# SPDX-License-Identifier: Apache-2.0
##################################

"""H extension test generator: the HS/VS/VU trap handler, T-SBI and two-stage translation paths."""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "H_cg"
INDENT = "  "

# Both stages identity-map the gigapage holding rvtest_code_begin. The VS-stage also maps
# the gigapage below it without a G-stage mapping, and the gigapage above it to the image.
_GIB = 1 << 30

# G-stage PTEs are always checked as user accesses, so PTE_U must be set.
_G_PERMS = "(PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_A | PTE_D)"
# VS-stage pages belong to the guest supervisor, so PTE_U is clear.
_VS_PERMS = "(PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D)"
# The same pages as VU-mode sees them.
_VU_PERMS = "(PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_A | PTE_D)"

# Bits the hypervisor spec requires to read as zero. hedeleg: environment call
# from HS/VS/M (9, 10, 11), double trap (16) and the guest-page faults and
# virtual instruction exception (20-23), which are only ever taken in HS-mode.
# hideleg: the S-level interrupts (1, 5, 9) and SGEI (12); only the VS-level
# interrupts 2, 6 and 10 are writable.
_HEDELEG_RO_ZERO = hex(sum(1 << b for b in (9, 10, 11, 16, 20, 21, 22, 23)))
_HIDELEG_RO_ZERO = hex(sum(1 << b for b in (1, 5, 9, 12)))

# Bits the spec requires to be writable. hedeleg: the exceptions that can be taken
# in VS/VU mode, less bit 0, whose presence depends on IALIGN. hideleg: the VS-level
# interrupts, which a hypervisor must be able to delegate to the guest.
_HEDELEG_WRITABLE = hex(sum(1 << b for b in (1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 15, 18, 19)))
_HIDELEG_WRITABLE = hex(sum(1 << b for b in (2, 6, 10)))


def _gen_ecall_test(test_data: TestData, check: int, temp: int, bin_name: str) -> list[str]:
    """RVTEST_TSBI_ECALL_TEST, checking it returns the ecall's own address."""
    label = test_data.add_testcase(bin_name, "cp_tsbi_ecall", _CG)
    site = label.rstrip(":") + "_site"
    return [
        label,
        f"{site}:",
        f"{INDENT}RVTEST_TSBI_ECALL_TEST",
        f"{INDENT}LA(x{temp}, {site})",
        f"{INDENT}sub x{check}, a0, x{temp}",
        write_sigupd(check, test_data),
    ]


def _gen_hs_csr_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """HS-mode hypervisor CSR access, before anything has entered a guest."""
    code = [
        "",
        "/////////////////////////////////",
        "// HS-mode hypervisor CSR access",
        "/////////////////////////////////",
        "",
        test_data.add_testcase("bare", "cp_hgatp_mode", _CG),
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}srli x{check}, x{check}, MODE_LSB",
        write_sigupd(check, test_data),
        "",
        test_data.add_testcase("clear", "cp_hstatus_spv", _CG),
        f"{INDENT}csrr x{check}, hstatus",
        f"{INDENT}LI(x{temp}, HSTATUS_SPV)",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        write_sigupd(check, test_data),
        "",
        "# Write all ones to hedeleg and hideleg, then check the required read-only-zero",
        "# and writable bits. Other bits are implementation choices.",
        f"{INDENT}LI(x{temp}, -1)",
        test_data.add_testcase("ro_zero_bits", "cp_hedeleg_warl", _CG),
        f"{INDENT}csrw hedeleg, x{temp}",
        f"{INDENT}csrr x{check}, hedeleg",
        f"{INDENT}LI(x{temp}, {_HEDELEG_RO_ZERO})",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        write_sigupd(check, test_data),
        test_data.add_testcase("required_writable_bits", "cp_hedeleg_warl", _CG),
        f"{INDENT}csrr x{check}, hedeleg",
        f"{INDENT}LI(x{temp}, {_HEDELEG_WRITABLE})",
        f"{INDENT}and x{check}, x{check}, x{temp}   # must read back as the mask itself",
        write_sigupd(check, test_data),
        f"{INDENT}csrw hedeleg, x0",
        "",
        f"{INDENT}LI(x{temp}, -1)",
        test_data.add_testcase("ro_zero_bits", "cp_hideleg_warl", _CG),
        f"{INDENT}csrw hideleg, x{temp}",
        f"{INDENT}csrr x{check}, hideleg",
        f"{INDENT}LI(x{temp}, {_HIDELEG_RO_ZERO})",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        write_sigupd(check, test_data),
        test_data.add_testcase("required_writable_bits", "cp_hideleg_warl", _CG),
        f"{INDENT}csrr x{check}, hideleg",
        f"{INDENT}LI(x{temp}, {_HIDELEG_WRITABLE})",
        f"{INDENT}and x{check}, x{check}, x{temp}   # must read back as the mask itself",
        write_sigupd(check, test_data),
        f"{INDENT}csrw hideleg, x0",
    ]
    return code


def _gen_tsbi_from_hs_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """T-SBI calls made from HS-mode, which reach M-mode as cause 9."""
    return [
        "",
        "/////////////////////////////////",
        "// T-SBI from HS-mode",
        "/////////////////////////////////",
        "",
        *_gen_ecall_test(test_data, check, temp, "from_hs"),
        "",
        "# M-mode reads mstatus while servicing the HS-mode ecall, so MPP reads back as S.",
        test_data.add_testcase("mstatus_mpp_from_hs", "cp_tsbi_csr_read", _CG),
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
        "/////////////////////////////////",
        "",
        f"{INDENT}LA(x{temp}, H_guest_scratch)",
        f"{INDENT}LI(x{check}, 0x5AA5)",
        test_data.add_testcase("roundtrip", "cp_hlv_hsv", _CG),
        "#if __riscv_xlen == 32",
        f"{INDENT}hsv.w x{check}, (x{temp})",
        f"{INDENT}LI(x{check}, 0)",
        f"{INDENT}hlv.w x{check}, (x{temp})",
        "#else",
        f"{INDENT}hsv.d x{check}, (x{temp})",
        f"{INDENT}LI(x{check}, 0)",
        f"{INDENT}hlv.d x{check}, (x{temp})",
        "#endif",
        write_sigupd(check, test_data),
        "",
        "# The same round trip as VS-mode (hstatus.SPVP=1).",
        f"{INDENT}LI(x{temp}, HSTATUS_SPVP)",
        f"{INDENT}csrs hstatus, x{temp}",
        f"{INDENT}LA(x{temp}, H_guest_scratch)",
        f"{INDENT}LI(x{check}, 0xA55A)",
        test_data.add_testcase("roundtrip_spvp", "cp_hlv_hsv", _CG),
        "#if __riscv_xlen == 32",
        f"{INDENT}hsv.w x{check}, (x{temp})",
        f"{INDENT}LI(x{check}, 0)",
        f"{INDENT}hlv.w x{check}, (x{temp})",
        "#else",
        f"{INDENT}hsv.d x{check}, (x{temp})",
        f"{INDENT}LI(x{check}, 0)",
        f"{INDENT}hlv.d x{check}, (x{temp})",
        "#endif",
        write_sigupd(check, test_data),
        f"{INDENT}LI(x{temp}, HSTATUS_SPVP)",
        f"{INDENT}csrc hstatus, x{temp}",
    ]


def _gen_vsmode_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """Enter VS-mode, trap out of it, and come back through the T-SBI."""
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
        "# In VS-mode, sstatus accesses vsstatus.",
        f"{INDENT}LI(x{temp}, SSTATUS_SPP)",
        test_data.add_testcase("spp_set", "cp_vsstatus_alias", _CG),
        f"{INDENT}csrs sstatus, x{temp}",
        f"{INDENT}csrr x{check}, sstatus",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        write_sigupd(check, test_data),
        "",
        "# Accessing an HS-mode CSR from VS-mode raises a virtual instruction",
        "# exception (cause 22). The check register keeps its pre-trap value,",
        "# which is how we know the instruction never completed.",
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("hs_csr_from_vs", "cp_virtual_instruction", _CG),
        f"{INDENT}csrr x{check}, hgatp",
        write_sigupd(check, test_data),
        "",
        "# ecall from VS-mode (cause 10) may be taken in HS-mode or M-mode.",
        *_gen_ecall_test(test_data, check, temp, "from_vs"),
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_SMODE   # leave the guest",
        "",
        "# The SPP written by the guest must be in vsstatus, not sstatus.",
        test_data.add_testcase("spp_not_in_hs", "cp_vsstatus_alias", _CG),
        f"{INDENT}csrr x{check}, sstatus",
        f"{INDENT}csrr x{temp}, vsstatus",
        f"{INDENT}xor x{check}, x{check}, x{temp}",
        f"{INDENT}LI(x{temp}, SSTATUS_SPP)",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        f"{INDENT}sltu x{check}, x0, x{check}   # 1 = the guest's SPP stayed in vsstatus",
        write_sigupd(check, test_data),
        "",
        "# GOTO_SMODE clears hstatus.SPV to leave the guest.",
        test_data.add_testcase("after_vs_trap", "cp_hstatus_spv", _CG),
        f"{INDENT}csrr x{check}, hstatus",
        f"{INDENT}LI(x{temp}, HSTATUS_SPV)",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        f"{INDENT}sltu x{check}, x0, x{check}",
        write_sigupd(check, test_data),
    ]
    return code


def _gen_vumode_tests(test_data: TestData, check: int, temp: int) -> list[str]:
    """Enter VU-mode and reach HS-mode and M-mode through the T-SBI."""
    return [
        "",
        "/////////////////////////////////",
        "// VU-mode",
        "//",
        "// A VU ecall is cause 8, the same as a U-mode one, so HS-mode services it.",
        "/////////////////////////////////",
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_VUMODE",
        "",
        "# A supervisor CSR access from VU-mode raises a virtual instruction exception.",
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("s_csr_from_vu", "cp_virtual_instruction", _CG),
        f"{INDENT}csrr x{check}, sscratch",
        write_sigupd(check, test_data),
        "",
        *_gen_ecall_test(test_data, check, temp, "from_vu"),
        "",
        "# The trap from VU-mode sets hstatus.SPV and clears SPVP.",
        test_data.add_testcase("hstatus_from_vu", "cp_tsbi_csr_read", _CG),
        f"{INDENT}RVTEST_TSBI_CSR_READ(CSR_HSTATUS)",
        f"{INDENT}LI(x{temp}, HSTATUS_SPV | HSTATUS_SPVP)",
        f"{INDENT}and x{check}, a0, x{temp}",
        write_sigupd(check, test_data),
        "",
        "# The HS handler forwards M-mode CSR accesses, so mstatus.MPP reads back as S.",
        test_data.add_testcase("mstatus_mpp_from_vu", "cp_tsbi_csr_read", _CG),
        f"{INDENT}RVTEST_TSBI_CSR_READ(CSR_MSTATUS)",
        f"{INDENT}srli x{check}, a0, MPP_LSB",
        f"{INDENT}andi x{check}, x{check}, 0x3",
        write_sigupd(check, test_data),
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_SMODE   # leave the guest",
        "",
        test_data.add_testcase("after_vu_trap", "cp_hstatus_spv", _CG),
        f"{INDENT}csrr x{check}, hstatus",
        f"{INDENT}LI(x{temp}, HSTATUS_SPV)",
        f"{INDENT}and x{check}, x{check}, x{temp}",
        f"{INDENT}sltu x{check}, x0, x{check}",
        write_sigupd(check, test_data),
    ]


def _gib_window(reg: int, gib_delta: int) -> list[str]:
    """Load the base of the gigapage `gib_delta` gigapages from the one holding the image.

    The page-table macros clobber t0-t2, one of which the register allocator may hand out,
    so each window is re-derived immediately before it is used rather than kept in a register.
    """
    return [
        f"{INDENT}LA(x{reg}, rvtest_code_begin)",
        f"{INDENT}srli x{reg}, x{reg}, 30",
        *([f"{INDENT}addi x{reg}, x{reg}, {gib_delta}"] if gib_delta else []),
        f"{INDENT}slli x{reg}, x{reg}, 30",
    ]


def _gen_twostage_setup(test_data: TestData, check: int, temp: int, base: int, addr: int) -> list[str]:
    """Build the G-stage and VS-stage page tables and turn both stages on."""
    return [
        "",
        "/////////////////////////////////",
        "// Two-stage address translation",
        "//",
        "// With IMG the gigapage holding rvtest_code_begin:",
        "// G-stage:  GPA IMG         -> PA  IMG           (identity gigapage)",
        "// VS-stage: VA  IMG         -> GPA IMG           (identity gigapage)",
        "//           VA  IMG - 1 GiB -> GPA IMG - 1 GiB   (no G-stage entry: faults)",
        "//           VA  IMG + 1 GiB -> GPA IMG           (non-identity view)",
        "/////////////////////////////////",
        "",
        "# The windows are derived at run time from the gigapage holding rvtest_code_begin.",
        *_gib_window(base, 0),
        f"{INDENT}G_PTE_SETUP_GPA_REG(sv39x4, x{base}, {_G_PERMS}, x{base}, LEVEL2)",
        *_gib_window(base, 0),
        f"{INDENT}VS_PTE_SETUP_VA_REG(sv39, x{base}, {_VS_PERMS}, x{base}, LEVEL2)",
        *_gib_window(base, -1),
        f"{INDENT}VS_PTE_SETUP_VA_REG(sv39, x{base}, {_VS_PERMS}, x{base}, LEVEL2)",
        *_gib_window(base, 0),
        *_gib_window(addr, 1),
        f"{INDENT}VS_PTE_SETUP_VA_REG(sv39, x{base}, {_VS_PERMS}, x{addr}, LEVEL2)",
        f"{INDENT}HGATP_SETUP(sv39x4)",
        # cpp expands ADDR_PA inside assembler comments, so keep it out of this comment.
        f"{INDENT}VSATP_SETUP(sv39, ADDR_PA)   # the guest root table is named by its physical address",
        f"{INDENT}hfence.gvma",
        f"{INDENT}hfence.vvma",
        f"{INDENT}sfence.vma",
        "",
        test_data.add_testcase("sv39x4", "cp_hgatp_mode", _CG),
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}srli x{check}, x{check}, MODE_LSB",
        write_sigupd(check, test_data),
        "",
        test_data.add_testcase("sv39", "cp_vsatp_mode", _CG),
        f"{INDENT}csrr x{check}, vsatp",
        f"{INDENT}srli x{check}, x{check}, MODE_LSB",
        write_sigupd(check, test_data),
    ]


def _gen_twostage_spvp(test_data: TestData, check: int, temp: int, addr: int) -> list[str]:
    """hlv under both stages, with SPVP telling a VS-mode access from a VU-mode one."""
    code = [
        "",
        "/////////////////////////////////",
        "// hstatus.SPVP",
        "//",
        "// The VS-stage maps the image without PTE_U, so the same hlv succeeds when SPVP",
        "// says the guest access is VS-mode and page-faults when it says VU-mode. Both",
        "// stages are live here, so this also exercises hlv through a two-stage walk.",
        "/////////////////////////////////",
        "",
        f"{INDENT}LA(x{addr}, H_guest_data)",
    ]
    for spvp, op, name in ((1, "csrs", "spvp_vs"), (0, "csrc", "spvp_vu")):
        code.extend(
            [
                "",
                f"{INDENT}LI(x{temp}, HSTATUS_SPVP)",
                f"{INDENT}{op} hstatus, x{temp}   # guest accesses are checked as {'VS' if spvp else 'VU'}-mode",
                f"{INDENT}LI(x{check}, -1)",
                test_data.add_testcase(name, "cp_hlv_hsv", _CG),
                f"{INDENT}hlv.d x{check}, (x{addr})",
                write_sigupd(check, test_data),
            ]
        )
    return code


def _gen_twostage_guest(test_data: TestData, check: int, temp: int, addr: int) -> list[str]:
    """Run the guest under both translation stages and take traps from translated guest addresses."""
    ident_label = test_data.add_testcase("load_store", "cp_twostage_access", _CG)
    code = [
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_VSMODE",
        "",
        "# A load and store through both stages.",
        f"{INDENT}LA(x{addr}, H_guest_data)",
        f"{INDENT}LI(x{check}, 0x1234ABCD)",
        ident_label,
        f"{INDENT}SREG x{check}, 0(x{addr})",
        f"{INDENT}LI(x{check}, 0)",
        f"{INDENT}LREG x{check}, 0(x{addr})",
        write_sigupd(check, test_data),
        "",
        "# An exception whose xEPC is a guest virtual address.",
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("translated_guest", "cp_virtual_instruction", _CG),
        f"{INDENT}csrr x{check}, hgatp",
        write_sigupd(check, test_data),
        "",
        "# Jump to the aliased view, where the guest VA differs from the physical address.",
        f"{INDENT}LA(x{addr}, 1f)",
        f"{INDENT}LI(x{temp}, {_GIB})",
        f"{INDENT}add x{addr}, x{addr}, x{temp}",
        f"{INDENT}jr x{addr}",
        "1:",
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("non_identity_guest_va", "cp_virtual_instruction", _CG),
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}addi x{check}, x{check}, 2   # executes only if the handler skipped the csrr",
        write_sigupd(check, test_data),
        "",
        "# The upper halfword of 0x000024F3 (csrr x9, 0x000) is 0x0000, an illegal",
        "# compressed encoding. A handler that misreads the width traps again there.",
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("non_identity_guest_va", "cp_illegal_instruction", _CG),
        f"{INDENT}.word 0x000024F3   # csrr x9, 0x000: an unimplemented CSR, so it always traps",
        f"{INDENT}addi x{check}, x{check}, 3",
        write_sigupd(check, test_data),
        "",
        f"{INDENT}LA(x{addr}, 2f)   # an alias address, since PC is in the alias window",
        f"{INDENT}LI(x{temp}, {_GIB})",
        f"{INDENT}sub x{addr}, x{addr}, x{temp}",
        f"{INDENT}jr x{addr}",
        "2:",
        "",
        "# The hole has a VS-stage mapping but no G-stage mapping, so accesses raise",
        "# guest-page faults and htval holds the guest physical address shifted right by 2.",
        *_gib_window(addr, -1),
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("load", "cp_guest_page_fault", _CG),
        f"{INDENT}LREG x{check}, 0(x{addr})",
        write_sigupd(check, test_data),
        "",
        "# Store guest-page fault (cause 23)",
        *_gib_window(addr, -1),
        f"{INDENT}LI(x{check}, 0x5A5A)",
        test_data.add_testcase("store", "cp_guest_page_fault", _CG),
        f"{INDENT}SREG x{check}, 0(x{addr})",
        write_sigupd(check, test_data),
        "",
        "# Instruction guest-page fault (cause 20). The handler resumes fetch faults at ra.",
        *_gib_window(addr, -1),
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("fetch", "cp_guest_page_fault", _CG),
        f"{INDENT}jalr ra, x{addr}, 0",
        write_sigupd(check, test_data),
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_SMODE   # back to HS-mode",
        "",
        "# The trap signature records htval for each fault. The ecall that left the",
        "# guest does not define htval, so it must now read as zero.",
        test_data.add_testcase("zero_after_ecall", "cp_htval", _CG),
        f"{INDENT}csrr x{check}, htval",
        write_sigupd(check, test_data),
    ]
    return code


def _gen_twostage_vu(test_data: TestData, check: int, temp: int, addr: int, base: int) -> list[str]:
    """Run VU-mode under both translation stages."""
    return [
        "",
        "/////////////////////////////////",
        "// Two-stage translation from VU-mode",
        "//",
        "// VU-mode can only execute VS-stage pages with PTE_U set, which VS-mode can",
        "// never execute, so the identity and hole mappings are rewritten here, after",
        "// the VS-mode tests, rather than shared with them.",
        "/////////////////////////////////",
        "",
        *_gib_window(base, 0),
        f"{INDENT}VS_PTE_SETUP_VA_REG(sv39, x{base}, {_VU_PERMS}, x{base}, LEVEL2)",
        *_gib_window(base, -1),
        f"{INDENT}VS_PTE_SETUP_VA_REG(sv39, x{base}, {_VU_PERMS}, x{base}, LEVEL2)",
        f"{INDENT}hfence.vvma",
        f"{INDENT}RVTEST_TSBI_GOTO_VUMODE",
        "",
        f"{INDENT}LA(x{addr}, H_guest_data)",
        f"{INDENT}LI(x{check}, 0x5678DCBA)",
        test_data.add_testcase("load_store_vu", "cp_twostage_access", _CG),
        f"{INDENT}SREG x{check}, 0(x{addr})",
        f"{INDENT}LI(x{check}, 0)",
        f"{INDENT}LREG x{check}, 0(x{addr})",
        write_sigupd(check, test_data),
        "",
        "# The HS handler reads this ecall's width through the guest's translation at",
        "# VU privilege, which only works because the page is a user page.",
        *_gen_ecall_test(test_data, check, temp, "from_vu_translated"),
        "",
        *_gib_window(addr, -1),
        f"{INDENT}LI(x{check}, -1)",
        test_data.add_testcase("load_vu", "cp_guest_page_fault", _CG),
        f"{INDENT}LREG x{check}, 0(x{addr})",
        write_sigupd(check, test_data),
        "",
        f"{INDENT}RVTEST_TSBI_GOTO_SMODE   # back to HS-mode",
    ]


def _gen_twostage_teardown(test_data: TestData, check: int) -> list[str]:
    """Turn both stages off again so the epilogs run with a plain machine state."""
    return [
        "",
        "# Show hgatp is writable back to Bare on the way out.",
        f"{INDENT}csrw vsatp, zero",
        test_data.add_testcase("back_to_bare", "cp_hgatp_mode", _CG),
        f"{INDENT}csrw hgatp, zero",
        f"{INDENT}csrr x{check}, hgatp",
        f"{INDENT}hfence.gvma",
        write_sigupd(check, test_data),
    ]


@add_priv_test_generator(
    "H",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_h(test_data: TestData) -> list[TestChunk]:
    """Generate the HS, VS and VU-mode trap handler and T-SBI tests."""
    test_chunks: list[TestChunk] = []

    check, temp = test_data.int_regs.get_registers(2)

    tc = test_data.begin_test_chunk("hsmode")
    tc.code.extend(_gen_hs_csr_tests(test_data, check, temp))
    tc.code.extend(_gen_tsbi_from_hs_tests(test_data, check, temp))
    tc.code.extend(_gen_hlv_hsv_tests(test_data, check, temp))
    tc.code.extend(_gen_vsmode_tests(test_data, check, temp))
    tc.code.extend(_gen_vumode_tests(test_data, check, temp))
    tc.raw_data.extend([".p2align 3", "H_guest_scratch:", "  .dword 0"])
    test_chunks.append(test_data.end_test_chunk())

    test_data.int_regs.return_registers([check, temp])
    return test_chunks


@add_priv_test_generator(
    "H",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["MXLEN: 64"],
)
def make_h_twostage(test_data: TestData) -> list[TestChunk]:
    """Generate the two-stage translation tests (Sv39x4 G-stage over Sv39 VS-stage)."""
    test_chunks: list[TestChunk] = []

    check, temp, addr, base = test_data.int_regs.get_registers(4)

    tc = test_data.begin_test_chunk("twostage")
    tc.code.extend(_gen_twostage_setup(test_data, check, temp, base, addr))
    tc.code.extend(_gen_twostage_spvp(test_data, check, temp, addr))
    tc.code.extend(_gen_twostage_guest(test_data, check, temp, addr))
    tc.code.extend(_gen_twostage_vu(test_data, check, temp, addr, base))
    tc.code.extend(_gen_twostage_teardown(test_data, check))
    tc.raw_data.extend([".p2align 3", "H_guest_data:", "  .dword 0"])
    test_chunks.append(test_data.end_test_chunk())

    test_data.int_regs.return_registers([check, temp, addr, base])
    return test_chunks
