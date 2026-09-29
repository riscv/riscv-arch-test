##################################
# priv/extensions/sv/SvSm.py
#
# SvSm suite: virtual-memory behavior that needs M-mode (MPRV, TVM, SBE, M-mode satp access).
# umer@riscv.org September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Sv tests that execute or check state in M-mode."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import (
    PTE_SETUP_ADDR_REG,
    PTE_SETUP_VALUE_REG,
    SV32,
    SV39,
    SV48,
    SV57,
    PteFlags,
    SvMode,
    create_leaf_pte,
    create_page_mapping,
    create_page_walk,
)
from testgen.priv.extensions.sv.Sv import (
    SATP_FIELDS,
    change_pte_to_be,
    emit_access,
    level_header,
    satp_access_ops,
    satp_csr_read,
    satp_mode_value,
)
from testgen.priv.registry import add_priv_test_generator


def _t_mstatus_mprv(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_mstatus_mprv_{mode}")
        style = "mprv_s" if mode == "Smode" else "mprv_u"
        for number, level in enumerate(sv.levels_desc, start=1):
            permissions = PteFlags(user=mode == "Umode")
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: MPRV set, MPP={mode[0]} | RWX bit set | expected = No Fault",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, regs, level, style, f"test{number}", "va_data", "Mmode", "Mmode"),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = 10
        test_chunks.append(end_sv_test(test_data, regs))


def _t_upage_mprv(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for topic, style, faults_per_case in (
        ("upage_mprv_set_sum_set", "mprv_sum_set", 0),
        ("upage_mprv_set_sum_unset", "mprv_sum_unset", 2),
    ):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, "Smode", f"{sv.name}_{topic}_Smode")
        sum_state = "set" if faults_per_case == 0 else "unset"
        expected = "No Fault" if faults_per_case == 0 else "Load & Store page fault"
        for number, level in enumerate(sv.levels_desc, start=1):
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: MPRV set, MPP=S, SUM {sum_state} | U page | expected = {expected}",
                    *create_page_mapping(
                        sv,
                        leaf_level=level,
                        leaf_flags=PteFlags(user=True),
                    ),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, regs, level, style, f"test{number}", "va_data", "Mmode", "Mmode"),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * faults_per_case)
        test_chunks.append(end_sv_test(test_data, regs))


def _sbe_setup(sv: SvMode, with_sum: bool, scratch: int) -> tuple[str, ...]:
    csr, mask = ("mstatush", "MSTATUSH_SBE") if sv.xlen == 32 else ("mstatus", "MSTATUS_SBE")
    lines = [f"  LI(   x{scratch}, {mask})", f"  csrs  {csr}, x{scratch}"]
    if with_sum:
        lines += [f"  LI(   x{scratch}, MSTATUS_SUM)", f"  csrs  mstatus, x{scratch}"]
    return tuple(lines)


def _pte_setup_to_be(sv: SvMode, regs: SvRegs) -> list[str]:
    """Rewrite the PTE that the last PTE_SETUP_* macro wrote big-endian."""
    return change_pte_to_be(sv, regs, PTE_SETUP_VALUE_REG, PTE_SETUP_ADDR_REG)


def _walk_be(sv: SvMode, regs: SvRegs, level: int) -> list[str]:
    lines = []
    for line in create_page_walk(sv, leaf_level=level):
        lines.extend([line, *_pte_setup_to_be(sv, regs)])
    return lines


def _identity_pte_to_be(sv: SvMode, regs: SvRegs, pte_reg: int) -> list[str]:
    shift = sv.page_offset_bits(sv.levels - 1)
    index_mask = "0x3FF" if sv.xlen == 32 else "0x1FF"
    index, entry, pte = f"x{regs.addr}", f"x{regs.scratch}", f"x{pte_reg}"
    return [
        "// The S-mode accesses run from the boot identity map, so its root PTE must be big-endian too.",
        f"LA({index}, rvtest_code_begin)",
        f"srli {index}, {index}, {shift}",
        f"andi {index}, {index}, {index_mask}",
        f"slli {index}, {index}, {2 if sv.xlen == 32 else 3}",
        f"LA({entry}, rvtest_Sroot_pg_tbl)",
        f"add {entry}, {entry}, {index}",
        f"LREG {pte}, 0({entry})",
        *change_pte_to_be(sv, regs, pte_reg, regs.scratch),
    ]


def _t_mstatus_sbe(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    for topic, with_sum in (("mstatus_sbe_set", False), ("mstatus_sbe_and_sum_set", True)):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(
            test_data,
            regs,
            sv,
            "Smode",
            f"{sv.name}_{topic}_Smode",
            setup_asm=_sbe_setup(sv, with_sum, regs.scratch),
        )
        pte_reg = test_data.int_regs.get_register(exclude_regs=[0])
        chunk.code.extend([*_pte_setup_to_be(sv, regs), *_identity_pte_to_be(sv, regs, pte_reg)])
        test_data.int_regs.return_register(pte_reg)
        for number, level in enumerate(sv.levels_desc, start=1):
            extra = ("PTE_SOFT",) if sv.xlen == 32 and level == 0 else ()
            permissions = PteFlags(user=with_sum, extra=extra)
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: Big-endian PTE | Test in S-Mode | RWX bit set | expected = No Fault",
                    *_walk_be(sv, regs, level),
                    create_leaf_pte(sv, level=level, flags=permissions),
                    *_pte_setup_to_be(sv, regs),
                    "sfence.vma",
                    "",
                    *emit_access(
                        test_data,
                        sv,
                        regs,
                        level,
                        "sl" if with_sum else "rwx",
                        f"test{number}",
                        "va_data",
                        "Smode",
                        "Mmode",
                    ),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = 10
        test_chunks.append(end_sv_test(test_data, regs))
    return test_chunks


def _t_satp_access(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    # Sv48/Sv57 configs also implement Sv39, so one M-mode satp test per xlen is enough.
    if sv.name not in ("sv32", "sv39"):
        return
    value_reg, bit_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])
    chunk = test_data.begin_test_chunk(f"{sv.name}_satp_access_Mmode")
    chunk.section_header = comment_banner("cp_satp_access")
    # MODE = sv with PPN = 0 (M-mode is not translated), then set and clear the lowest ASID bit.
    asid_shift = SATP_FIELDS[sv.name][2]
    chunk.code.extend([*satp_mode_value(sv, value_reg, bit_reg, root=False), f"LI(x{bit_reg}, 1 << {asid_shift})"])
    chunk.code.extend(
        [*satp_access_ops(test_data, "Mmode", (value_reg, bit_reg, bit_reg), check_reg), "csrw satp, zero"]
    )
    test_data.int_regs.return_registers([value_reg, bit_reg, check_reg])
    test_chunks.append(test_data.end_test_chunk())


def _make_svsm(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    _t_mstatus_mprv(test_data, test_chunks, sv)
    _t_upage_mprv(test_data, test_chunks, sv)
    _t_satp_access(test_data, test_chunks, sv)
    return test_chunks


@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv32"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svsm(test_data, SV32)


@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv39"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svsm(test_data, SV39)


@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv48"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svsm(test_data, SV48)


@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv57"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svsm(test_data, SV57)


# TODO: drop NORUN once a DUT and the reference model implement big-endian implicit
# page-table accesses (mstatus.SBE=1); until then no configuration can run this test.
@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv32", "NORUN"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv32_sbe(test_data: TestData) -> list[TestChunk]:
    return _t_mstatus_sbe(test_data, SV32)


# TODO: drop NORUN once a DUT and the reference model implement big-endian implicit
# page-table accesses (mstatus.SBE=1); until then no configuration can run this test.
@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv39", "NORUN"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv39_sbe(test_data: TestData) -> list[TestChunk]:
    return _t_mstatus_sbe(test_data, SV39)


# TODO: drop NORUN once a DUT and the reference model implement big-endian implicit
# page-table accesses (mstatus.SBE=1); until then no configuration can run this test.
@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv48", "NORUN"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv48_sbe(test_data: TestData) -> list[TestChunk]:
    return _t_mstatus_sbe(test_data, SV48)


# TODO: drop NORUN once a DUT and the reference model implement big-endian implicit
# page-table accesses (mstatus.SBE=1); until then no configuration can run this test.
@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "Sv57", "NORUN"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_sv57_sbe(test_data: TestData) -> list[TestChunk]:
    return _t_mstatus_sbe(test_data, SV57)


@add_priv_test_generator(
    "SvSm",
    required_extensions=["Sm", "S"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svsm_mstatus_tvm(test_data: TestData) -> list[TestChunk]:
    value_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    chunk = test_data.begin_test_chunk("sv_mstatus_tvm_test")
    chunk.section_header = comment_banner("cp_satp_access")
    chunk.code.extend(
        [
            f"LI(x{value_reg}, MSTATUS_TVM)",
            f"csrs mstatus, x{value_reg}",
            *satp_csr_read(test_data, "tvm", check_reg, "mstatus"),
        ]
    )
    chunk.code.extend(
        [
            # TVM does not restrict M-mode, so all three accesses complete here.
            f"li x{value_reg}, 0",
            *satp_access_ops(test_data, "Mmode", (value_reg, value_reg, value_reg), check_reg),
            "sfence.vma",
            "RVTEST_TSBI_GOTO_SMODE",
            "csrw satp, zero",
            "csrs satp, zero",
            "csrc satp, zero",
            "sfence.vma",
            "RVTEST_TSBI_GOTO_MMODE",
        ]
    )
    chunk.trap_sigupd_count = 30
    test_data.int_regs.return_registers([value_reg, check_reg])
    return [test_data.end_test_chunk()]
