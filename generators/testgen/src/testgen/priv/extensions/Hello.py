##################################
# priv/extensions/Hello.py
#
# Hello bring-up suite: smoke tests for a new DUT environment.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Bring-up smoke tests for a DUT environment.

One short test per layer of the contract a DUT has to satisfy, in dependency
order, so the first failing file names the thing to fix. Run this before the
certification suites: it finishes in seconds, where a full run takes hours.

Each testcase is named after the macro or value it exercises, so the framework's
own failure message points at the culprit. The suite claims no functional
coverage -- there is no Hello covergroup and no normative rule maps to it.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Hello_cg"

# Distinct, easy-to-spot values: a wrong signature pointer or stride shows up as
# one of these landing in the wrong slot rather than as an opaque mismatch.
_PATTERNS = (0x0000_0000, 0xFFFF_FFFF, 0xAAAA_5555, 0xDEAD_BEEF, 0x0000_00FF, 0x8000_0001)


def _boot(test_data: TestData) -> list[str]:
    """rvmodel_dut_boot, rvmodel_dut_io_init, rvmodel_io_write_str, rvmodel_halt_pass.

    Reaching the first instruction of the test body already proves boot, the entry
    point and the linker script; writing one signature word proves the halt path
    runs the self-check rather than falling off the end.
    """
    reg = test_data.int_regs.get_registers(1)[0]
    lines = [
        comment_banner("Hello: boot", "Reaching here proves boot, the entry point and act_link.ld"),
        test_data.add_testcase("rvmodel_dut_boot", "cp_boot", _CG),
        f"LI(x{reg}, 0xC0FFEE)",
        write_sigupd(reg, test_data),
    ]
    test_data.int_regs.return_registers([reg])
    return lines


def _signature(test_data: TestData) -> list[str]:
    """The self-check mechanism: signature pointer, stride and region placement."""
    reg = test_data.int_regs.get_registers(1)[0]
    lines = [comment_banner("Hello: signature", "Known values through RVTEST_SIGUPD, in order")]
    for pattern in _PATTERNS:
        lines.extend(
            [
                test_data.add_testcase(f"pattern_{pattern:08x}", "cp_signature", _CG),
                f"LI(x{reg}, {hex(pattern)})",
                write_sigupd(reg, test_data),
            ]
        )
    test_data.int_regs.return_registers([reg])
    return lines


def _trap(test_data: TestData) -> list[str]:
    """Trap entry and return: xtvec install, the trampoline, and the trap signature.

    The handler records mode, cause and xEPC for each trap, so both testcases here
    check the trap words as well as the resumption.
    """
    reg = test_data.int_regs.get_registers(1)[0]
    lines = [
        comment_banner("Hello: trap", "ecall and an illegal instruction, both taken and resumed"),
        test_data.add_testcase("ecall", "cp_trap", _CG),
        "RVTEST_TSBI_ECALL_TEST",
        # 0x00000000 is a guaranteed-illegal encoding on every hart.
        test_data.add_testcase("illegal_instruction", "cp_trap", _CG),
        ".option push",
        ".option norvc",
        ".word 0x00000000",
        ".option pop",
        # Getting here means the handler advanced xEPC past both traps.
        f"LI(x{reg}, 0x7AA97AA9)",
        write_sigupd(reg, test_data),
    ]
    test_data.int_regs.return_registers([reg])
    return lines


def _modes(test_data: TestData) -> list[str]:
    """Privilege transitions through T-SBI, and the trap handler's per-mode save areas.

    An ecall from each mode records that mode in trap signature word 0, so a DUT
    that never leaves M-mode fails here rather than silently running everything
    in M.
    """
    reg = test_data.int_regs.get_registers(1)[0]
    lines = [comment_banner("Hello: modes", "M -> S -> U -> M, with an ecall from each")]
    # A per-mode marker in the signature, so a hart that never left M-mode is caught
    # by the value as well as by the mode recorded in the trap word.
    for mode, guard, marker in (("SMODE", "S_SUPPORTED", 0x1111_0001), ("UMODE", "U_SUPPORTED", 0x1111_0000)):
        lines.extend(
            [
                f"#ifdef {guard}",
                f"RVTEST_TSBI_GOTO_{mode}",
                test_data.add_testcase(f"ecall_from_{mode.lower()}", "cp_modes", _CG),
                "RVTEST_TSBI_ECALL_TEST",
                f"LI(x{reg}, {hex(marker)})",
                write_sigupd(reg, test_data),
                "RVTEST_TSBI_GOTO_MMODE",
                f"#endif // {guard}",
            ]
        )
    test_data.int_regs.return_registers([reg])
    return lines


def _interrupts(test_data: TestData) -> list[str]:
    """The software and external interrupt entry points, and the in-handler clears.

    Guarded on the UDB parameters that say the platform can raise each one, the same
    way the Interrupts suites are. A macro implemented as a no-op leaves the interrupt
    pending, so the idle loop never completes.
    """
    r_idle, reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner("Hello: interrupts", "Software and external interrupt, taken then cleared"),
        "# Enable every interrupt source, then unmask globally",
        f"LI(x{reg}, -1)",
        f"csrw mie, x{reg}",
        "csrsi mstatus, 8    # mstatus.MIE = 1",
    ]
    for kind, guard in (("MSW", "UDB_MSI_INTR_IMPL"), ("MEXT", "UDB_MEI_INTR_IMPL")):
        lines.extend(
            [
                f"#ifdef {guard}",
                test_data.add_testcase(f"rvtest_set_{kind.lower()}_int", "cp_interrupts", _CG),
                f"RVTEST_SET_{kind}_INT_M",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_idle})",
                f"RVTEST_CLR_{kind}_INT_M",
                f"#endif // {guard}",
            ]
        )
    lines.extend(
        [
            "csrci mstatus, 8    # mstatus.MIE = 0",
            f"LI(x{reg}, 0x17171717)",
            write_sigupd(reg, test_data),
        ]
    )
    test_data.int_regs.return_registers([r_idle, reg])
    return lines


def _timer(test_data: TestData) -> list[str]:
    """RVMODEL_MTIME_ADDRESS, RVMODEL_MTIMECMP_ADDRESS and the interrupt timings.

    RVTEST_SET_MTIME_INT_SOON_M arms mtimecmp through those addresses and the
    configured delay, so wrong device addresses show up as an interrupt that never
    arrives.
    """
    r_idle, reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner("Hello: timer", "Arm mtimecmp through the model's device addresses"),
        "#ifdef UDB_MTI_INTR_IMPL",
        f"LI(x{reg}, -1)",
        f"csrw mie, x{reg}",
        "csrsi mstatus, 8    # mstatus.MIE = 1",
        test_data.add_testcase("mtimecmp", "cp_timer", _CG),
        "RVTEST_SET_MTIME_INT_SOON_M",
        f"RVTEST_IDLE_FOR_INTERRUPT(x{r_idle})",
        "RVTEST_CLR_MTIME_INT_M",
        "csrci mstatus, 8    # mstatus.MIE = 0",
        "#endif // UDB_MTI_INTR_IMPL",
    ]
    test_data.int_regs.return_registers([r_idle, reg])
    return lines


def _access_fault(test_data: TestData) -> list[str]:
    """RVMODEL_ACCESS_FAULT_ADDRESS: the address the config promises will fault.

    If it points at mapped memory the load succeeds, no trap is recorded, and the
    trap signature diverges -- which is the whole point of checking it here rather
    than discovering it across a dozen suites later.
    """
    addr, dest = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner("Hello: access fault", "A load from the model's fault address must trap"),
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        f"LI(x{addr}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        f"LI(x{dest}, 0x1BAD0BAD)",
        test_data.add_testcase("rvmodel_access_fault_address", "cp_access_fault", _CG),
        f"lw x{dest}, 0(x{addr})",
        write_sigupd(dest, test_data),
        "#endif // RVMODEL_ACCESS_FAULT_ADDRESS",
    ]
    test_data.int_regs.return_registers([addr, dest])
    return lines


@add_priv_test_generator(
    "Hello",
    required_extensions=["Sm"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_hello(test_data: TestData) -> list[TestChunk]:
    """One file per layer, in the order a DUT has to satisfy them."""
    chunks: list[TestChunk] = []
    for name, body in (
        ("boot", _boot),
        ("signature", _signature),
        ("trap", _trap),
        ("modes", _modes),
        ("interrupts", _interrupts),
        ("timer", _timer),
        ("fault", _access_fault),
    ):
        tc = test_data.begin_test_chunk(split_name=name)
        tc.code = body(test_data)
        chunks.append(test_data.end_test_chunk())
    return chunks
