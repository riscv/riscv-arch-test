##################################
# priv/extensions/SscofpmfScountovf.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf scountovf test-case generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sscofpmf scountovf tests: masking by mcounteren, CSR access, and shadowing of the mhpmevent OF bits."""

from collections.abc import Callable

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.SscofpmfCommon import csr_access

NUM_OF_BITS = 29  # mhpmevent3..31


def unknown_of_state() -> list[int | None]:
    """OF state for write_of_pattern() when earlier tests in the file may have changed OF."""
    return [None] * NUM_OF_BITS


def boot_of_state() -> list[int | None]:
    """OF state for write_of_pattern() at the start of a test file: rvtest_setup.h clears
    mhpmevent3..31, and the RV32 high halves that hold OF, at every boot."""
    return [0] * NUM_OF_BITS


def write_of_pattern(
    r_of_bit: int, pattern_name: str, of_bit_fn: Callable[[int], int], mode: str, of_state: list[int | None]
) -> list[str]:
    """Set or clear OF in mhpmevent3..31 per of_bit_fn(counter - 3). of_state holds the OF value
    last written to each counter (None if unknown) and is updated in place, so only the counters
    whose OF changes are written. Below M each write is a T-SBI call."""
    changes = [(i, of_bit_fn(i)) for i in range(NUM_OF_BITS) if of_state[i] != of_bit_fn(i)]
    of_state[:] = [of_bit_fn(i) for i in range(NUM_OF_BITS)]

    def writes(csr_suffix: str, of_bit: int, desc: str) -> list[str]:
        lines = [f"LI(x{r_of_bit}, {hex(of_bit)})   # OF bit ({desc})"]
        for i, of in changes:
            op, action = ("csrs", "set") if of else ("csrc", "clear")
            lines.append(csr_access(f"{op} CSR_MHPMEVENT{i + 3}{csr_suffix}, x{r_of_bit}   # {action} OF", mode))
        return lines

    return [
        f"# --- Write OF pattern: {pattern_name} across mhpmevent3..31 ---",
        "#if __riscv_xlen == 32",
        *writes("H", 1 << 31, "bit 31 of mhpmeventh, RV32"),
        "#else",
        *writes("", 1 << 63, "bit 63 of mhpmevent, RV64"),
        "#endif",
        "",
    ]


# OF patterns for cp_scountovf_mcounteren, indexed by counter - 3.
MCOUNTEREN_OF_PATTERNS: dict[str, Callable[[int], int]] = {
    "all_ones": lambda i: 1,
    "checker_even": lambda i: 1 if i % 2 == 0 else 0,
    "checker_odd": lambda i: 1 if i % 2 == 1 else 0,
}


def generate_scountovf_mcounteren_tests(
    test_data: TestData, mode: str, of_state: list[int | None], of_names: list[str]
) -> list[str]:
    """cp_scountovf_mcounteren: scountovf masked by mcounteren."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_scountovf_mcounteren"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            f"scountovf masked by mcounteren -- mode = {mode}.\n"
            f"Write OF patterns ({'/'.join(of_names)}) across\n"
            "mhpmevent3..31.OF, walk mcounteren, read scountovf.",
        ),
        "",
    ]

    indent = ""

    for of_name in of_names:
        of_bit_fn = MCOUNTEREN_OF_PATTERNS[of_name]
        r_of_bit = test_data.int_regs.get_register(exclude_regs=[0, 31])
        lines.extend(write_of_pattern(r_of_bit, of_name, of_bit_fn, mode, of_state))
        test_data.int_regs.return_registers([r_of_bit])

        walk_coverpoint = f"{coverpoint}_{of_name}_{mode.lower()}"

        if mode == "Sm":
            lines.extend(
                csr_walk_test(
                    test_data,
                    csr=("mcounteren", 0xFFFFFFF8),
                    covergroup=covergroup,
                    coverpoint=walk_coverpoint,
                    start_bit=3,
                    walk_zeros=True,
                )
            )

            r_scountovf = test_data.int_regs.get_register(exclude_regs=[0, 31])
            lines.append(test_data.add_testcase(f"scountovf_{of_name}_{mode.lower()}", coverpoint, covergroup))
            lines.append(csr_access(f"csrr x{r_scountovf}, scountovf   # sample point", mode))
            lines.append(write_sigupd(r_scountovf, test_data))
            lines.append("")
            test_data.int_regs.return_registers([r_scountovf])
        else:
            r_mcounteren, r_scountovf = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

            for state_name, val in [("all_zeros", 0), ("all_ones", 0xFFFFFFF8)]:
                binname = f"mcounteren_{state_name}"
                lines.extend(
                    [
                        f"{indent}LI(x{r_mcounteren}, {hex(val)})",
                        f"{indent}{csr_access(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                        f"{indent}{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                        f"{indent}{csr_access(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                        f"{indent}{write_sigupd(r_scountovf, test_data)}",
                        "",
                    ]
                )

            for bit in range(3, 32):
                binname = f"mcounteren_walk_bit_{bit}"
                lines.extend(
                    [
                        f"{indent}LI(x{r_mcounteren}, {1 << bit})",
                        f"{indent}{csr_access(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                        f"{indent}{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                        f"{indent}{csr_access(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                        f"{indent}{write_sigupd(r_scountovf, test_data)}",
                        "",
                    ]
                )

            lines.append(f"{indent}{csr_access('csrw mcounteren, zero', mode)}")
            lines.append("")
            test_data.int_regs.return_registers([r_mcounteren, r_scountovf])

    return lines


def generate_sscofpmf_access_tests(test_data: TestData, mode: str) -> list[str]:
    if mode == "U":
        return []

    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_sscofpmf_access"
    ######################################

    access_types = ["read", "write_ones", "write_zeros", "set", "clear"]
    r_val = test_data.int_regs.get_register(exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            f"Attempt to read, write 1s, write 0s, set, clear from mode = {mode}:\n"
            "scountovf\nIf RV32: mhpmeventh3...31",
        ),
        "",
    ]

    def emit_accesses(csr_name: str) -> None:
        for access in access_types:
            binname = f"sscofpmf_access_{csr_name}_{access}_{mode.lower()}"
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            if access == "read":
                lines.append(csr_access(f"csrr x{r_val}, {csr_name}", mode))
            elif access == "write_ones":
                lines.extend([f"LI(x{r_val}, -1)", csr_access(f"csrw {csr_name}, x{r_val}", mode)])
            elif access == "write_zeros":
                lines.append(csr_access(f"csrw {csr_name}, zero", mode))
            elif access == "set":
                lines.extend([f"LI(x{r_val}, -1)", csr_access(f"csrs {csr_name}, x{r_val}", mode)])
            elif access == "clear":
                lines.extend([f"LI(x{r_val}, -1)", csr_access(f"csrc {csr_name}, x{r_val}", mode)])
            lines.append("")

    emit_accesses("scountovf")

    if mode == "Sm":  # mhpmeventh3..31 sweep is M-mode only per spec
        lines.append("#if __riscv_xlen == 32")
        for n in range(3, 32):
            emit_accesses(f"CSR_MHPMEVENT{n}H")
        lines.append("#endif")

    test_data.int_regs.return_registers([r_val])
    return lines


def _walking_one(walk_idx: int) -> Callable[[int], int]:
    return lambda i: 1 if i == walk_idx else 0


# OF patterns for cp_scountovf_shadow, keyed by the S-mode test file that runs them.
# all_0s runs first so each walking pattern after it changes at most two OF bits.
SHADOW_PATTERNS: dict[str, list[tuple[str, Callable[[int], int]]]] = {
    "shadow_walk_lo": [("all_0s", lambda i: 0), *((f"walking1_{w}", _walking_one(w)) for w in range(15))],
    "shadow_walk_hi": [(f"walking1_{w}", _walking_one(w)) for w in range(15, NUM_OF_BITS)],
    "shadow_all_1s": [("all_1s", lambda i: 1)],
}


def generate_scountovf_shadow_tests(
    test_data: TestData,
    priv_mode: str,
    of_state: list[int | None],
    patterns: list[tuple[str, Callable[[int], int]]],
) -> list[str]:
    if priv_mode == "U":
        return []

    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_scountovf_shadow"
    ######################################

    indent = ""

    lines = [
        comment_banner(
            coverpoint,
            f"scountovf shadows OF bits of mhpmevent3:31, mode = {priv_mode}.\n"
            "mcounteren = all 1s (fixed for this coverpoint). Write patterns to\n"
            "mhpmevent3...31.OF: all 0s, walking 1s, all 1s. Read scountovf.\n",
        ),
        "",
    ]

    r_mcounteren = test_data.int_regs.get_register(exclude_regs=[0, 31])
    lines.extend(
        [
            f"{indent}LI(x{r_mcounteren}, -1)",
            f"{indent}{csr_access(f'csrw mcounteren, x{r_mcounteren}   # mcounteren = all 1s (fixed for this coverpoint)', priv_mode)}",
            "",
        ]
    )
    test_data.int_regs.return_registers([r_mcounteren])

    def emit_pattern(pattern_name: str, of_bit_fn: Callable[[int], int]) -> None:
        r_of_bit, r_scountovf = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])
        lines.extend(write_of_pattern(r_of_bit, pattern_name, of_bit_fn, priv_mode, of_state))
        test_data.int_regs.return_registers([r_of_bit])

        binname = f"scountovf_shadow_{priv_mode.lower()}_{pattern_name}"
        lines.append(f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}")
        lines.append(
            f"{indent}{csr_access(f'csrr x{r_scountovf}, scountovf   # sample point -- must match OF pattern', priv_mode)}"
        )
        lines.append(f"{indent}{write_sigupd(r_scountovf, test_data)}")
        lines.append("")

        test_data.int_regs.return_registers([r_scountovf])

    for pattern_name, of_bit_fn in patterns:
        emit_pattern(pattern_name, of_bit_fn)

    return lines
