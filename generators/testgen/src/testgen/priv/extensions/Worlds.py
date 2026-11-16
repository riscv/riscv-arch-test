##################################
# priv/extensions/Worlds.py
#
# RISC-V Worlds (World-ID) test generators: Smwid, Smlwid, Smlwidlist, Smwiddeleg and Sswid.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Worlds privileged test generators.

The RISC-V Worlds extensions tag every memory access of a hart with a World Identifier (WID):
mwid (Smwid) for M-mode, mlwid (Smlwid) for the modes below M, and slwid (Sswid, enabled while
mwiddeleg is non-zero) for the modes below S. The platform limits the usable WIDs (pmwidlist,
pmlwidlist), M-mode can limit them further (mlwidlist with Smlwidlist) and delegate some to S-mode
(mwiddeleg with Smwiddeleg). A mode whose WID is not authorized cannot fetch, load or store: its
first access raises a software-check exception with xtval = illegal world fault (4).

The platform parameters are not visible to the tests, so the tests only write WIDs that are safe
in M-mode (M-mode keeps its reset WID, which the platform must authorize) and let the reference
model decide, for each WID written to mlwid or slwid, whether the lower mode traps. When it does,
the M-mode trap handler returns to M-mode at ra, since the lower mode cannot execute anything.
"""

from itertools import count

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.registry import add_priv_test_generator

CG = "Worlds_cg"

# WIDs written to mlwid and slwid.  NWorlds is typically 2 to 8, so these cover authorized and
# unauthorized WIDs on most platforms.
WIDS = [0, 1, 2, 3]
# Values written to a WID-list CSR (mlwidlist, mwiddeleg): a bit per WID.
LIST_VALUES = ["0", "0x1", "0x2", "0x4", "0x8", "0xF", "0xFF", "-1"]

_labels = count()


def _label(name: str) -> str:
    return f"worlds_{name}_{next(_labels)}"


def _modes(ext: str) -> list[tuple[str, str]]:
    """(mode, guard) pairs of the modes below M that may be entered from M-mode."""
    if ext == "S":
        return [("S", "S_SUPPORTED")]
    return [("S", "S_SUPPORTED"), ("U", "U_SUPPORTED")]


def _undelegate_software_check(tmp: int) -> list[str]:
    """Keep software-check exceptions in M-mode: the M-mode handler returns to M-mode on an illegal world fault."""
    return [
        "#ifdef S_SUPPORTED",
        f"LI(x{tmp}, 1 << CAUSE_SOFTWARE_CHECK_FAULT)",
        f"csrc medeleg, x{tmp}   # software-check exceptions are handled in M-mode",
        "#endif",
    ]


def _csr_write_read(test_data: TestData, csr: str, value: str, cp: str, bin_name: str, val: int, rd: int) -> list[str]:
    """Write value to csr and record what reads back."""
    return [
        f"LI(x{val}, {value})",
        f"csrw {csr}, x{val}",
        test_data.add_testcase(bin_name, cp, CG),
        f"csrr x{rd}, {csr}",
        write_sigupd(rd, test_data),
    ]


def _csr_read(test_data: TestData, csr: str, cp: str, bin_name: str, rd: int) -> list[str]:
    return [test_data.add_testcase(bin_name, cp, CG), f"csrr x{rd}, {csr}", write_sigupd(rd, test_data)]


def _illegal_access(test_data: TestData, csr: str, cp: str, mode: str, guard: str, rd: int) -> list[str]:
    """Read csr from mode, which must raise an illegal instruction exception and leave rd unchanged."""
    return [
        f"#ifdef {guard}",
        f"RVTEST_TSBI_GOTO_{mode}MODE",
        test_data.add_testcase(f"{csr.lower()}_{mode.lower()}", cp, CG),
        f"LI(x{rd}, 42)              # the trapping csrr must leave x{rd} unchanged",
        f"csrr x{rd}, {csr}          # illegal instruction in {mode}-mode",
        write_sigupd(rd, test_data),
        "RVTEST_TSBI_GOTO_MMODE",
        "#endif",
    ]


def _fetch_in_mode(
    test_data: TestData, mode: str, guard: str, cp: str, bin_name: str, rd: int, *, from_s: bool = False
) -> list[str]:
    """Enter mode and record whether its first instruction fetch raises an illegal world fault.

    If it does, the M-mode trap handler returns to M-mode at ra (the resume label). Otherwise the
    code in mode records a marker and returns to M-mode itself. With from_s, the test is already in
    S-mode and returns to M-mode through S-mode.
    """
    resume = _label("resume")
    lines = [
        f"#ifdef {guard}",
        f"LA(x1, {resume})            # the trap handler resumes here in M-mode on an illegal world fault",
        test_data.add_testcase(bin_name, cp, CG),
        f"RVTEST_TSBI_GOTO_{mode}MODE  # first fetch in {mode}-mode: illegal world fault if the WID is unauthorized",
        f"LI(x{rd}, 0x5A)             # reached only when the WID of {mode}-mode is authorized",
        write_sigupd(rd, test_data),
        "RVTEST_TSBI_GOTO_MMODE",
        f"{resume}:",
    ]
    if from_s:
        lines.append("RVTEST_TSBI_GOTO_SMODE")
    lines.append("#endif")
    return lines


def _mprv_access(
    test_data: TestData, mode: str, guard: str, cp: str, bin_name: str, regs: tuple[int, int, int]
) -> list[str]:
    """Load and store from M-mode with mstatus.MPRV=1 and MPP=mode: an illegal world fault if the WID of mode is unauthorized.

    MPRV is cleared right after each access: an mret (including the trap handler's) sets MPP to U, after which any
    further access with MPRV=1 would be made as U-mode.
    """
    tmp, addr, rd = regs
    mpp = {"S": "0x800", "U": "0"}[mode]
    data = _label("data")
    assert test_data.test_chunk is not None
    test_data.test_chunk.raw_data.extend([".balign 8", f"{data}:", ".dword 0x0123456789ABCDEF"])
    set_mprv = [
        f"LI(x{tmp}, MSTATUS_MPP)",
        f"csrc mstatus, x{tmp}",
        f"LI(x{tmp}, {mpp} | MSTATUS_MPRV)",
        f"csrs mstatus, x{tmp}      # loads and stores are made as {mode}-mode",
        f"LI(x{tmp}, MSTATUS_MPRV)",
    ]
    return [
        f"#ifdef {guard}",
        f"LA(x{addr}, {data})",
        *set_mprv,
        test_data.add_testcase(f"{bin_name}_load", cp, CG),
        f"LI(x{rd}, 42)              # a trapping load must leave x{rd} unchanged",
        f"lw x{rd}, 0(x{addr})",
        f"csrc mstatus, x{tmp}",
        write_sigupd(rd, test_data),
        *set_mprv,
        test_data.add_testcase(f"{bin_name}_store", cp, CG),
        f"LI(x{rd}, 0x5A)",
        f"sw x{rd}, 4(x{addr})",
        f"csrc mstatus, x{tmp}",
        f"lw x{rd}, 4(x{addr})       # 0x5A if the store was performed",
        write_sigupd(rd, test_data),
        "#endif",
    ]


# Smwid


@add_priv_test_generator(
    "Worlds",
    required_extensions=["Smwid", "Sm"],
    march_extensions=["Smwid"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smwid(test_data: TestData) -> list[TestChunk]:
    """mwid: reset value, WARL WID field, reserved bits, illegal accesses and the lock bit."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    save, val, rd = test_data.int_regs.get_registers(3)
    tc.code.extend(
        [
            comment_banner(
                "cp_mwid_reset",
                "mwid shows the platform-defined WID of M-mode (pmwid) out of reset and may already be locked.",
            ),
            *_csr_read(test_data, "CSR_MWID", "cp_mwid_reset", "reset", rd),
            f"csrr x{save}, CSR_MWID",
            comment_banner(
                "cp_mwid_warl",
                "Only the WID field and the lock bit of mwid are writable; the reserved bits read as zero.\n"
                "The WID is kept at its reset value, which the platform must authorize: an unauthorized WID in\n"
                "mwid would hang the hart.",
            ),
            f"LI(x{val}, -1)",
            f"srli x{val}, x{val}, 1     # all bits but the lock bit",
            f"or x{val}, x{val}, x{save}",
            f"csrw CSR_MWID, x{val}      # reserved bits must read as zero",
            test_data.add_testcase("reserved_bits", "cp_mwid_warl", CG),
            f"csrr x{rd}, CSR_MWID",
            write_sigupd(rd, test_data),
            f"csrw CSR_MWID, x{save}",
            test_data.add_testcase("restore", "cp_mwid_warl", CG),
            f"csrr x{rd}, CSR_MWID",
            write_sigupd(rd, test_data),
        ]
    )
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    tc.trap_sigupd_count = trap_sigupd_count(2)
    tc.code.append(
        comment_banner("cp_mwid_illegal_access", "mwid is an M-mode CSR: accesses from S-mode and U-mode are illegal.")
    )
    for mode, guard in _modes("SU"):
        tc.code.extend(_illegal_access(test_data, "CSR_MWID", "cp_mwid_illegal_access", mode, guard, rd))
    test_chunks.append(test_data.end_test_chunk())

    # The lock is sticky until reset, so this is the last chunk of its own file.
    tc = test_data.new_test_chunk(test_chunks, "lock")
    tc.code.extend(
        [
            comment_banner(
                "cp_mwid_lock",
                "Setting mwid.L locks mwid: later writes, including attempts to clear L, are ignored.",
            ),
            f"csrr x{save}, CSR_MWID",
            f"LI(x{val}, 1)",
            f"slli x{val}, x{val}, __riscv_xlen - 1",
            f"or x{val}, x{val}, x{save}",
            f"csrw CSR_MWID, x{val}      # lock mwid",
            test_data.add_testcase("locked", "cp_mwid_lock", CG),
            f"csrr x{rd}, CSR_MWID",
            write_sigupd(rd, test_data),
            f"xori x{val}, x{save}, 1   # a different WID",
            f"csrw CSR_MWID, x{val}      # ignored",
            test_data.add_testcase("write_wid_ignored", "cp_mwid_lock", CG),
            f"csrr x{rd}, CSR_MWID",
            write_sigupd(rd, test_data),
            f"csrw CSR_MWID, x{save}     # attempt to clear L: ignored",
            test_data.add_testcase("clear_lock_ignored", "cp_mwid_lock", CG),
            f"csrr x{rd}, CSR_MWID",
            write_sigupd(rd, test_data),
        ]
    )
    test_chunks.append(test_data.end_test_chunk())
    test_data.int_regs.return_registers([save, val, rd])
    return test_chunks


# Smlwid


@add_priv_test_generator(
    "Worlds",
    required_extensions=["Smlwid", "Sm", ["S", "U"]],
    march_extensions=["Smlwid"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smlwid(test_data: TestData) -> list[TestChunk]:
    """mlwid: reset value, WARL WID field, illegal accesses, and the illegal world fault of the modes below M."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    save, val, rd, addr = test_data.int_regs.get_registers(4)
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner("cp_mlwid_reset", "The reset value of mlwid is platform-defined."),
            *_csr_read(test_data, "CSR_MLWID", "cp_mlwid_reset", "reset", rd),
            f"csrr x{save}, CSR_MLWID",
            comment_banner(
                "cp_mlwid_warl",
                "Only the WID field (the low ceil(log2(NWorlds)) bits) of mlwid is writable; the other bits read as zero.\n"
                "Unauthorized WIDs can be written: they only take effect on the next access from a lower mode.",
            ),
        ]
    )
    for value in [*map(str, WIDS), "0xF", "0xFF", "-1"]:
        tc.code.extend(
            _csr_write_read(
                test_data, "CSR_MLWID", value, "cp_mlwid_warl", f"write_{value.replace('-', 'neg')}", val, rd
            )
        )
    tc.code.append(f"csrw CSR_MLWID, x{save}")
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    tc.trap_sigupd_count = trap_sigupd_count(2 * len(WIDS))
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner(
                "cp_mlwid_fetch",
                "With each WID in mlwid, enter S-mode and U-mode (with Sswid disabled, U-mode also uses mlwid).\n"
                "The first instruction fetch raises a software-check exception with xtval = illegal world fault\n"
                "if the WID is not authorized by the platform (pmlwidlist) or by M-mode (mlwidlist).",
            ),
        ]
    )
    for wid in WIDS:
        tc.code.extend([f"LI(x{val}, {wid})", f"csrw CSR_MLWID, x{val}"])
        for mode, guard in _modes("SU"):
            tc.code.extend(_fetch_in_mode(test_data, mode, guard, "cp_mlwid_fetch", f"wid{wid}_{mode.lower()}", rd))
    tc.code.append(f"csrw CSR_MLWID, x{save}")
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    tc.trap_sigupd_count = trap_sigupd_count(4 * len(WIDS))
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner(
                "cp_mlwid_mprv",
                "With each WID in mlwid, load and store from M-mode with mstatus.MPRV=1 and MPP=S or U.\n"
                "The access raises a software-check exception with xtval = illegal world fault if the WID\n"
                "of the lower mode is not authorized; the exception has priority over access faults.",
            ),
        ]
    )
    for wid in WIDS:
        tc.code.extend([f"LI(x{val}, {wid})", f"csrw CSR_MLWID, x{val}"])
        for mode, guard in _modes("SU"):
            tc.code.extend(
                _mprv_access(test_data, mode, guard, "cp_mlwid_mprv", f"wid{wid}_{mode.lower()}", (val, addr, rd))
            )
    tc.code.append(f"csrw CSR_MLWID, x{save}")
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    tc.trap_sigupd_count = trap_sigupd_count(2)
    tc.code.append(
        comment_banner(
            "cp_mlwid_illegal_access", "mlwid is an M-mode CSR: accesses from S-mode and U-mode are illegal."
        )
    )
    for mode, guard in _modes("SU"):
        tc.code.extend(_illegal_access(test_data, "CSR_MLWID", "cp_mlwid_illegal_access", mode, guard, rd))
    test_chunks.append(test_data.end_test_chunk())
    test_data.int_regs.return_registers([save, val, rd, addr])
    return test_chunks


# Smlwidlist


@add_priv_test_generator(
    "Worlds",
    required_extensions=["Smlwidlist", "Smwid", "Smlwid", "Sm", ["S", "U"]],
    march_extensions=["Smlwidlist"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smlwidlist(test_data: TestData) -> list[TestChunk]:
    """mlwidlist: reset value (pmlwidlist), WARL subset of pmlwidlist, effect on the modes below M, and the mwid lock."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    save, val, rd, addr = test_data.int_regs.get_registers(4)
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner("cp_mlwidlist_reset", "mlwidlist shows the platform-defined pmlwidlist out of reset."),
            *_csr_read(test_data, "CSR_MLWIDLIST", "cp_mlwidlist_reset", "reset", rd),
            f"csrr x{save}, CSR_MLWIDLIST",
            comment_banner(
                "cp_mlwidlist_warl",
                "mlwidlist is WARL: a write followed by a read returns the written value ANDed with pmlwidlist.",
            ),
        ]
    )
    for value in LIST_VALUES:
        tc.code.extend(
            _csr_write_read(
                test_data, "CSR_MLWIDLIST", value, "cp_mlwidlist_warl", f"write_{value.replace('-', 'neg')}", val, rd
            )
        )
    tc.code.append(f"csrw CSR_MLWIDLIST, x{save}")
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    tc.trap_sigupd_count = trap_sigupd_count(6)
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner(
                "cp_mlwidlist_restricts",
                "With mlwidlist = 0 no WID is authorized for the modes below M: their first fetch, and loads and\n"
                "stores with MPRV, raise a software-check exception with xtval = illegal world fault.",
            ),
            "csrw CSR_MLWIDLIST, x0",
        ]
    )
    for mode, guard in _modes("SU"):
        tc.code.extend(_fetch_in_mode(test_data, mode, guard, "cp_mlwidlist_restricts", f"fetch_{mode.lower()}", rd))
        tc.code.extend(
            _mprv_access(test_data, mode, guard, "cp_mlwidlist_restricts", f"mprv_{mode.lower()}", (val, addr, rd))
        )
    tc.code.append(f"csrw CSR_MLWIDLIST, x{save}")
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks, "lock")
    tc.code.extend(
        [
            comment_banner("cp_mlwidlist_lock", "mlwidlist is read-only whenever mwid is locked."),
            f"csrr x{save}, CSR_MLWIDLIST",
            f"csrr x{val}, CSR_MWID",
            f"LI(x{rd}, 1)",
            f"slli x{rd}, x{rd}, __riscv_xlen - 1",
            f"or x{val}, x{val}, x{rd}",
            f"csrw CSR_MWID, x{val}      # lock mwid",
            "csrw CSR_MLWIDLIST, x0     # ignored",
            test_data.add_testcase("write_zero_ignored", "cp_mlwidlist_lock", CG),
            f"csrr x{rd}, CSR_MLWIDLIST",
            write_sigupd(rd, test_data),
            f"LI(x{val}, -1)",
            f"csrw CSR_MLWIDLIST, x{val} # ignored",
            test_data.add_testcase("write_ones_ignored", "cp_mlwidlist_lock", CG),
            f"csrr x{rd}, CSR_MLWIDLIST",
            write_sigupd(rd, test_data),
        ]
    )
    test_chunks.append(test_data.end_test_chunk())
    test_data.int_regs.return_registers([save, val, rd, addr])
    return test_chunks


# Smwiddeleg / Sswid


@add_priv_test_generator(
    "Worlds",
    required_extensions=["Smwiddeleg", "Smlwid", "Sm", "S"],
    march_extensions=["Smwiddeleg"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smwiddeleg(test_data: TestData) -> list[TestChunk]:
    """mwiddeleg and slwid: reset, Sswid enable, WARL behaviour, illegal accesses and the illegal world fault below S."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.trap_sigupd_count = trap_sigupd_count(4)
    save, val, rd, addr = test_data.int_regs.get_registers(4)
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner("cp_mwiddeleg_reset", "mwiddeleg is zero out of reset, so Sswid is disabled."),
            *_csr_read(test_data, "CSR_MWIDDELEG", "cp_mwiddeleg_reset", "reset", rd),
            comment_banner(
                "cp_sswid_disabled",
                "While mwiddeleg is zero, any access to slwid raises an illegal instruction exception, even from M-mode.",
            ),
            test_data.add_testcase("slwid_read_m", "cp_sswid_disabled", CG),
            f"LI(x{rd}, 42)",
            f"csrr x{rd}, CSR_SLWID      # illegal instruction",
            write_sigupd(rd, test_data),
            test_data.add_testcase("slwid_write_m", "cp_sswid_disabled", CG),
            "csrw CSR_SLWID, x0         # illegal instruction",
            f"csrr x{rd}, CSR_MWIDDELEG",
            write_sigupd(rd, test_data),
            *_illegal_access(test_data, "CSR_SLWID", "cp_sswid_disabled", "S", "S_SUPPORTED", rd),
            comment_banner(
                "cp_mwiddeleg_warl",
                "mwiddeleg is WARL: only WIDs that the platform allows to be delegated, and that are authorized\n"
                "in pmlwidlist (and mlwidlist), can be set.",
            ),
        ]
    )
    for value in LIST_VALUES:
        tc.code.extend(
            _csr_write_read(
                test_data, "CSR_MWIDDELEG", value, "cp_mwiddeleg_warl", f"write_{value.replace('-', 'neg')}", val, rd
            )
        )
    tc.code.append("csrw CSR_MWIDDELEG, x0")
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    # Every slwid access traps if no WID is delegatable.
    tc.trap_sigupd_count = trap_sigupd_count(2 * (len(WIDS) + 2) + 4)
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner(
                "cp_slwid_warl",
                "With every delegatable WID in mwiddeleg (Sswid enabled unless none is delegatable), only the WID\n"
                "field of slwid is writable, from M-mode and from S-mode.",
            ),
            f"LI(x{val}, -1)",
            f"csrw CSR_MWIDDELEG, x{val}",
            *_csr_read(test_data, "CSR_MWIDDELEG", "cp_slwid_warl", "mwiddeleg_all", rd),
            *_csr_read(test_data, "CSR_SLWID", "cp_slwid_warl", "slwid_reset", rd),
        ]
    )
    for value in [*map(str, WIDS), "0xFF", "-1"]:
        tc.code.extend(
            _csr_write_read(
                test_data, "CSR_SLWID", value, "cp_slwid_warl", f"write_{value.replace('-', 'neg')}_m", val, rd
            )
        )
    tc.code.extend(
        [
            "RVTEST_TSBI_GOTO_SMODE",
            *_csr_write_read(test_data, "CSR_SLWID", "1", "cp_slwid_warl", "write_1_s", val, rd),
            "RVTEST_TSBI_GOTO_MMODE",
            "csrw CSR_MWIDDELEG, x0",
        ]
    )
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    tc.trap_sigupd_count = trap_sigupd_count(4 * len(WIDS))
    tc.code.extend(
        [
            *_undelegate_software_check(val),
            comment_banner(
                "cp_slwid_fetch",
                "With every delegatable WID in mwiddeleg, S-mode writes each WID to slwid and enters U-mode.\n"
                "The first instruction fetch in U-mode raises a software-check exception with xtval = illegal\n"
                "world fault if the WID is not delegated in mwiddeleg. Loads and stores from M-mode with\n"
                "MPRV=1 and MPP=U are subject to the same check.",
            ),
            f"LI(x{val}, -1)",
            f"csrw CSR_MWIDDELEG, x{val}",
        ]
    )
    for wid in WIDS:
        tc.code.extend(
            [
                "RVTEST_TSBI_GOTO_SMODE",
                f"LI(x{val}, {wid})",
                f"csrw CSR_SLWID, x{val}     # from S-mode (illegal instruction if nothing is delegatable)",
                "RVTEST_TSBI_GOTO_MMODE",
                *_fetch_in_mode(test_data, "U", "U_SUPPORTED", "cp_slwid_fetch", f"wid{wid}_u", rd),
                *_mprv_access(test_data, "U", "U_SUPPORTED", "cp_slwid_fetch", f"wid{wid}_u", (val, addr, rd)),
            ]
        )
    tc.code.extend(
        ["csrw CSR_SLWID, x0         # an authorized WID again, for later U-mode code", "csrw CSR_MWIDDELEG, x0"]
    )
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.new_test_chunk(test_chunks)
    tc.trap_sigupd_count = trap_sigupd_count(4)
    tc.code.extend(
        [
            comment_banner(
                "cp_mwiddeleg_illegal_access",
                "mwiddeleg is an M-mode CSR and slwid an S-mode CSR: accesses from lower modes are illegal.",
            ),
            f"LI(x{val}, -1)",
            f"csrw CSR_MWIDDELEG, x{val}",
            "csrw CSR_SLWID, x0         # WID 0 for U-mode (illegal instruction if nothing is delegatable)",
            *_illegal_access(test_data, "CSR_MWIDDELEG", "cp_mwiddeleg_illegal_access", "S", "S_SUPPORTED", rd),
            *_illegal_access(test_data, "CSR_MWIDDELEG", "cp_mwiddeleg_illegal_access", "U", "U_SUPPORTED", rd),
            *_illegal_access(test_data, "CSR_SLWID", "cp_mwiddeleg_illegal_access", "U", "U_SUPPORTED", rd),
            "csrw CSR_MWIDDELEG, x0",
        ]
    )
    test_chunks.append(test_data.end_test_chunk())
    test_data.int_regs.return_registers([save, val, rd, addr])
    return test_chunks


@add_priv_test_generator(
    "Worlds",
    required_extensions=["Smwiddeleg", "Smlwidlist", "Smwid", "Smlwid", "Sm", "S"],
    march_extensions=["Smwiddeleg", "Smlwidlist"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smwiddeleg_smlwidlist(test_data: TestData) -> list[TestChunk]:
    """mwiddeleg is a subset of mlwidlist, and clearing bits of mlwidlist clears them in mwiddeleg."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    save, val, rd = test_data.int_regs.get_registers(3)
    tc.code.extend(
        [
            comment_banner(
                "cp_mwiddeleg_subset_of_mlwidlist",
                "A WID that is not authorized in mlwidlist cannot be set in mwiddeleg, and de-authorizing a WID in\n"
                "mlwidlist also de-authorizes it in mwiddeleg.",
            ),
            f"csrr x{save}, CSR_MLWIDLIST",
            "csrw CSR_MLWIDLIST, x0",
            *_csr_write_read(
                test_data, "CSR_MWIDDELEG", "-1", "cp_mwiddeleg_subset_of_mlwidlist", "mlwidlist_zero", val, rd
            ),
            f"csrw CSR_MLWIDLIST, x{save}",
            *_csr_write_read(
                test_data, "CSR_MWIDDELEG", "-1", "cp_mwiddeleg_subset_of_mlwidlist", "mlwidlist_reset", val, rd
            ),
            *_csr_write_read(
                test_data, "CSR_MLWIDLIST", "0x1", "cp_mwiddeleg_subset_of_mlwidlist", "mlwidlist_one", val, rd
            ),
            *_csr_read(
                test_data, "CSR_MWIDDELEG", "cp_mwiddeleg_subset_of_mlwidlist", "mwiddeleg_after_mlwidlist_one", rd
            ),
            *_csr_write_read(
                test_data, "CSR_MLWIDLIST", "0", "cp_mwiddeleg_subset_of_mlwidlist", "mlwidlist_zero_again", val, rd
            ),
            *_csr_read(
                test_data, "CSR_MWIDDELEG", "cp_mwiddeleg_subset_of_mlwidlist", "mwiddeleg_after_mlwidlist_zero", rd
            ),
            f"csrw CSR_MLWIDLIST, x{save}",
            "csrw CSR_MWIDDELEG, x0",
        ]
    )
    test_chunks.append(test_data.end_test_chunk())
    test_data.int_regs.return_registers([save, val, rd])
    return test_chunks
