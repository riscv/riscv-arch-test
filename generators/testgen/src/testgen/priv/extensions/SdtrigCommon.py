##################################
# SdtrigCommon.py
#
# Sdtrig (debug triggers) shared test-case generators.
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Sdtrig debug-trigger test-case generators."""

from random import seed

from testgen.asm.helpers import comment_banner, reproducible_hash, write_sigupd
from testgen.asm.tsbi import tsbi_call, tsbi_call_or_direct
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.InterruptsCommon import guard_symbol
from testgen.priv.registry import add_priv_test_generator

# data
PERM_XSL = ("exec", "store", "load")
SIZE_ALL = ("any", "b8", "b16", "b32", "b48", "b64", "b128")
# The tests cover tselect 0 to SDTRIG_MAX_TRIGGERS - 1, each guarded by #if UDB_SDTRIG_NUM_TRIGGERS > n.
# 16 covers every configuration here (the optional Sail profiles and QEMU have 16 triggers).
SDTRIG_MAX_TRIGGERS = 16
TRIGGERS = range(SDTRIG_MAX_TRIGGERS)
NOP = 0x00000013
C_NOP = 0x0001
ADDI_HINT = 0x00008013  # TODO Uses because U mode calls trigger on nops emitted by tsbi callss
TDATA2_NOFIRE = 0x2
TDATA_CSRS = ("tdata1", "tdata2", "tdata3")
# tdata1.type values
TRIG_TYPE_ICOUNT = 3
TRIG_TYPE_ITRIGGER = 4
TRIG_TYPE_ETRIGGER = 5
MCONTROL6_TYPE = 6
TDATA1_TYPE_DISABLED = 15
# types cp_csr_access_common bins (the testplan's {3, 4, 5, 6, 15}); the others are legacy, reserved or custom
ACCESS_TYPES = (TRIG_TYPE_ICOUNT, TRIG_TYPE_ITRIGGER, TRIG_TYPE_ETRIGGER, MCONTROL6_TYPE, TDATA1_TYPE_DISABLED)
# mcontrol6 mode bits; with all five set, bits 26:0 match priv_bits in SdtrigSm_trig_module_reg_cg
MCONTROL6_VS = 1 << 24
MCONTROL6_VU = 1 << 23
MCONTROL6_M = 1 << 6
MCONTROL6_S = 1 << 4
MCONTROL6_U = 1 << 3
MCONTROL6_ALL_PRIV = MCONTROL6_VS | MCONTROL6_VU | MCONTROL6_M | MCONTROL6_S | MCONTROL6_U
MODE_PRIVBIT = {"Sm": 0b10000, "S": 0b01000, "U": 0b00100, "Vs": 0b00010, "Vu": 0b00001}
MODE_UDB_LETTER = {"Sm": "M", "S": "S", "U": "U", "Vs": "VS", "Vu": "VU"}
# tdata2 values for the CBO tests, which operate on the block at scratch. scratch is .p2align 8 (rvtest_setup.h),
# so for any cache block of at most 256 bytes it is the block base, and the three compare values that
# norm:Sdtrig_cache_compare allows (every byte of the block / block base / effective address) all match
# tdata2=scratch and none matches scratch-1 or the next block.
CBO_TDATA2 = (
    ("scratch", "scratch"),
    ("below", "scratch-1"),
    ("next_block", "scratch+UDB_CACHE_BLOCK_SIZE"),
    ("0", 0),
)

_PAGE_FAULT_CODES = (12, 13, 15)
# Page faults need translation: Sv39 on RV64, Sv32 on RV32. A hart without it may have no satp (no S-mode), and
# VA_TARGET is then a physical address that may be RAM (it is on rv32 harts), so no page fault can be raised.
_PAGING_GUARD = "#if (__riscv_xlen == 64 && defined(SV39_SUPPORTED)) || (__riscv_xlen == 32 && defined(SV32_SUPPORTED))"

# MPRV=1, MPP=U: next M-mode load/store is translated as U-mode (needed for codes 13/15 when mode="Sm").
_MSTATUS_MPP_MASK = 0x1800
_MSTATUS_MPRV = 0x20000

VA_TARGET_RV32 = 0x90407000
VA2_TARGET_RV32 = 0x90807000
VA_TARGET_RV64 = 0x140802000
VA2_TARGET_RV64 = 0x180802000

_PTE_INVALID = "PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R"  # no PTE_V
_PTE_UPAGE = "PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V"

# Codes where the exception itself is raised (match case) in every mode. ipf is not raisable in Sm.
_ETRIGGER_BASE_CODES = (1, 2, 5, 7, 12, 13, 15)
# Codes tested with a mismatch case only (an illegal instruction is raised while tdata2 selects the code),
# because the code itself cannot be raised portably:
#   0 iam: jalr clears bit 0, and with Zca it cannot occur. 3 bp: medeleg[3]=0 sends ebreak to M.
#   4/6 lam/sam: Spike, Sail and Whisper handle misaligned accesses in hardware.
_ETRIGGER_MISMATCH_ONLY_CODES = (0, 3, 4, 6)
_ETRIGGER_ECALL_CODE = {"Sm": 11, "S": 9, "U": 8}  # each mode raises only its own ecall
_ETRIGGER_NOT_DELEGATABLE = (3, 11)  # medeleg[3] must stay 0 (trigger breakpoint goes to M); medeleg[11] is read-only 0

# maps mcause exception code -> short mnemonic used in binnames / ifdef names
ETRIGGER_EXCODE_NAMES = {
    0: "iam",  # instruction address misaligned
    1: "iacc",  # instruction access fault
    2: "ill",  # illegal instruction
    3: "bp",  # breakpoint
    4: "lam",  # load address misaligned
    5: "lacc",  # load access fault
    6: "sam",  # store/AMO address misaligned
    7: "sacc",  # store access fault
    8: "ecu",  # ecall from U-mode
    9: "ecs",  # ecall from S-mode
    11: "ecm",  # ecall from M-mode
    12: "ipf",  # instruction page fault
    13: "lpf",  # load page fault
    15: "spf",  # store/AMO page fault
}

# Test-framework behavior, not DUT parameters. The other Sdtrig defines come from the DUT's UDB configuration.
SDTRIG_DEFINES = [
    # Sims that do not follow Suggested Trigger Timing in spec or fires several cycles after will mismatch MEPC in trap handler
    "#define SDTRIG_IMPRECISE_XEPC",
    # itrigger/etrigger fire after the trap is taken, so xEPC is inside the S trap vector; the handler must not advance it
    "#define SDTRIG_XEPC_IN_VECTOR",
]

XSL_UDB_NAMES = ("LOAD", "STORE", "EXECUTE")  # mcontrol6 xsl bits 0, 1, 2
_TYPE_PARAM = {
    TRIG_TYPE_ICOUNT: "ICOUNT",
    TRIG_TYPE_ITRIGGER: "ITRIGGER",
    TRIG_TYPE_ETRIGGER: "ETRIGGER",
    MCONTROL6_TYPE: "MCONTROL6",
}


def _num_guard(trig_num: int) -> str:
    """``#if`` that trigger ``trig_num`` exists."""
    return f"#if UDB_SDTRIG_NUM_TRIGGERS > {trig_num}"


def _mode_writable(mode: str) -> str:
    """Define saying the m/s/u/vs/vu bit of ``mode`` can be set in the trigger types that have one."""
    return f"UDB_SDTRIG_{MODE_UDB_LETTER[mode]}_WRITABLE"


def _match_legal(match: int) -> str:
    return f"UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_{match}"


def _size_legal(size: int) -> str:
    return f"UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_{size}"


_SIZE_BITS = {1: 8, 2: 16, 3: 32, 4: 48, 5: 64, 6: 128}  # mcontrol6.size encodings


def _size_open(size: int) -> list[str]:
    """Gates for writing mcontrol6.size = ``size`` (nothing for 0, which every hart supports): the DUT supports it,
    and it is at most XLEN bits, because Sail 0.16, the reference model, turns a trigger with a larger size into a
    disabled one. Close them with _size_close()."""
    if not size:
        return []
    gates = [f"#ifdef {_size_legal(size)}"]
    if _SIZE_BITS[size] > 32:
        gates.append(f"#if __riscv_xlen >= {_SIZE_BITS[size]} // Sail 0.16 accepts sizes up to XLEN")
    return gates


def _size_close(size: int) -> list[str]:
    return [f"#endif // size {size}"] * len(_size_open(size))


# Per-trigger type availability for the textra cases, with the defines for trigger {trig_num} armed in {mode_letter}
_TEXTRA_TYPE_GUARDS = {
    "icount": ["#ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}", "#ifdef UDB_SDTRIG_{mode_letter}_WRITABLE"],
    # the mcontrol6 cases use a data (select=1) store (xsl=010) match enabled in the running mode
    "mcontrol6": [
        "#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}",
        "#ifdef UDB_SDTRIG_{mode_letter}_WRITABLE",
        "#ifdef UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE",
        "#ifdef UDB_SDTRIG_MCONTROL6_STORE_WRITABLE",
    ],
}

_TEXTRA_DATA = 0x12345678  # the textra mcontrol6 cases' store data match (_xlen_value widens it on RV64)
# Context and textra values are assembler expressions masked to the implemented mhvalue (MHVALUE_LEN) and svalue
# (SVALUE_LEN) bits, so a case expected to match still matches when fewer bits are implemented.
_MHVALUE_MASK = "((1 << UDB_SDTRIG_TEXTRA_MHVALUE_LEN) - 1)"
_SVALUE_MASK = "((1 << UDB_SDTRIG_TEXTRA_SVALUE_LEN) - 1)"
_MCONTEXT_TEST_VALUE_RV32 = 0b010101
_MCONTEXT_TEST_VALUE_RV64 = 0x1555
_SCONTEXT_TEST_VALUE_RV32 = 0x1234
_SCONTEXT_TEST_VALUE_RV64 = 0x12345678
# cp_textra_scontext (#2591): svalue x sbytemask; a masked byte is ignored in the compare
_TEXTRA_SCONTEXT_RV32 = [(sv, m) for sv in (0x0000, 0x0034, 0x1200, 0x1234) for m in (0b00, 0b01, 0b10, 0b11)]
_TEXTRA_SCONTEXT_RV64 = [
    (sv, m)
    for sv in (0x00000000, 0x12345600, 0x12340078, 0x12005678, 0x00345678, 0x12345678)
    for m in (0b0000, 0b0001, 0b0010, 0b0100, 0b1000, 0b1111)
]
# cp_textra_double_context (#2646): mcontext and scontext matched together
_DOUBLE_MCONTEXT = (0b111111, 0x1FFF)
_DOUBLE_SCONTEXT = (0xFFFF, 0xFFFFFFFF)

# cp_textra_asid: satp.ASID = X = 2^ASID_WIDTH - 2, and svalue (an assembler expression in X and ASIDMAX, which
# is 9 on RV32 and 16 on RV64) gives a match, a miss, a near miss, and a match whose svalue bits above ASIDMAX
# are ignored (norm:Sdtrig_textra32_sselect_asid3)
_ASID_X = "((1 << UDB_ASID_WIDTH) - 2)"
_TEXTRA_ASID_CASES = (
    ("match", "X", False),
    ("zero", "0", False),
    ("bit0_flipped", "(X ^ 1)", False),
    ("above_asidmax", "(X | (1 << ASIDMAX))", False),
    # sbytemask = all ones is ignored with sselect=2 (norm:Sdtrig_textra32_byte_mask_applies), so it hides no mismatch
    ("match_sbytemask", "X", True),
    ("bit0_flipped_sbytemask", "(X ^ 1)", True),
)

# (case name, rv32 mhvalue, rv64 mhvalue), per the test plan. mcontext holds the match value; "other" differs from it
# in bit 0, so it still differs with a single implemented mhvalue bit.
_TEXTRA_MCONTEXT_CASES = (
    ("match", _MCONTEXT_TEST_VALUE_RV32, _MCONTEXT_TEST_VALUE_RV64),
    ("zero", 0, 0),
    ("other", _MCONTEXT_TEST_VALUE_RV32 ^ 1, _MCONTEXT_TEST_VALUE_RV64 ^ 1),
)


def _type_guard(trig_type: int, trig_num: int) -> str | None:
    """The define saying trigger ``trig_num`` supports ``trig_type``; None for type 15 (disabled), which every trigger has.

    Each SDTRIG_<TYPE>_SUPPORTED_TRIGGERS array has one entry per trigger, so the define also implies the trigger exists.
    """
    name = _TYPE_PARAM.get(trig_type)
    return f"UDB_SDTRIG_{name}_SUPPORTED_TRIGGERS_{trig_num}" if name else None


def _mcontrol6_gates(trig_num: int, mode: str, *, select: int = 0) -> list[str]:
    """``#ifdef``s for an mcontrol6 arm on ``trig_num`` from ``mode``: the trigger supports mcontrol6, the mode's
    m/s/u bit is writable and, for select=1, data matching is. Close them with _close_gates().

    Writing an unsupported WARL value has an unpredictable result, so no field value is written outside its gate.
    """
    gates = [f"UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}", _mode_writable(mode)]
    if select:
        gates.append("UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
    return [f"\n#ifdef {gates[0]}", *(f"#ifdef {g}" for g in gates[1:])]


def _close_gates(gates: list[str]) -> list[str]:
    """``#endif``s for the ``#ifdef`` lines in ``gates``, innermost first."""
    return [f"#endif // {g.split()[-1]}" for g in reversed(gates)]


def _xsl_ifdefs(xsl: int) -> list[str]:
    """One ``#ifdef`` per mcontrol6 x/s/l capability ``xsl`` uses; empty list when xsl == 0."""
    ifdefs: list[str] = []
    if xsl > 0:
        for i, name in enumerate(XSL_UDB_NAMES):
            if xsl >> i & 1:
                prefix = "\n" if not ifdefs else ""
                ifdefs.append(f"{prefix}#ifdef UDB_SDTRIG_MCONTROL6_{name}_WRITABLE")
    return ifdefs


INSTR_IFDEFS = {
    "sb": [],
    "sh": [],
    "sw": [],
    "lb": [],
    "lbu": [],
    "lh": [],
    "lhu": [],
    "lw": [],
    "lr.w": [],
    "sc.w": [],
    "amoswap.w": [],
    "amoadd.w": [],
    "amoand.w": [],
    "amoor.w": [],
    "amoxor.w": [],
    "amomax.w": [],
    "amomaxu.w": [],
    "amomin.w": [],
    "amominu.w": [],
    "lr.d": ["#if __riscv_xlen == 64"],
    "sc.d": ["#if __riscv_xlen == 64"],
    "amoswap.d": ["#if __riscv_xlen == 64"],
    "amoadd.d": ["#if __riscv_xlen == 64"],
    "amoand.d": ["#if __riscv_xlen == 64"],
    "amoor.d": ["#if __riscv_xlen == 64"],
    "amoxor.d": ["#if __riscv_xlen == 64"],
    "amomax.d": ["#if __riscv_xlen == 64"],
    "amomaxu.d": ["#if __riscv_xlen == 64"],
    "amomin.d": ["#if __riscv_xlen == 64"],
    "amominu.d": ["#if __riscv_xlen == 64"],
    "sd": ["#if __riscv_xlen == 64"],
    "lwu": ["#if __riscv_xlen == 64"],
    "ld": ["#if __riscv_xlen == 64"],
    "fsw": ["#ifdef F_SUPPORTED"],
    "flw": ["#ifdef F_SUPPORTED"],
    "fsd": ["#ifdef D_SUPPORTED"],
    "fld": ["#ifdef D_SUPPORTED"],
    "fsh": ["#ifdef ZFH_SUPPORTED"],
    "flh": ["#ifdef ZFH_SUPPORTED"],
    "fsq": ["#ifdef Q_SUPPORTED"],
    "flq": ["#ifdef Q_SUPPORTED"],
    "c.sw": ["#ifdef ZCA_SUPPORTED"],
    "c.lw": ["#ifdef ZCA_SUPPORTED"],
    "c.swsp": ["#ifdef ZCA_SUPPORTED"],
    "c.lwsp": ["#ifdef ZCA_SUPPORTED"],
    "c.sd": ["#ifdef ZCA_SUPPORTED", "#if __riscv_xlen == 64"],
    "c.ld": ["#ifdef ZCA_SUPPORTED", "#if __riscv_xlen == 64"],
    "c.sdsp": ["#ifdef ZCA_SUPPORTED", "#if __riscv_xlen == 64"],
    "c.ldsp": ["#ifdef ZCA_SUPPORTED", "#if __riscv_xlen == 64"],
    "c.sb": ["#ifdef ZCB_SUPPORTED"],
    "c.sh": ["#ifdef ZCB_SUPPORTED"],
    "c.lbu": ["#ifdef ZCB_SUPPORTED"],
    "c.lh": ["#ifdef ZCB_SUPPORTED"],
    "c.lhu": ["#ifdef ZCB_SUPPORTED"],
    "c.fsw": ["#ifdef ZCF_SUPPORTED"],
    "c.flw": ["#ifdef ZCF_SUPPORTED"],
    "c.fswsp": ["#ifdef ZCF_SUPPORTED"],
    "c.flwsp": ["#ifdef ZCF_SUPPORTED"],
    "c.fsd": ["#ifdef ZCD_SUPPORTED"],
    "c.fld": ["#ifdef ZCD_SUPPORTED"],
    "c.fsdsp": ["#ifdef ZCD_SUPPORTED"],
    "c.fldsp": ["#ifdef ZCD_SUPPORTED"],
}

ZAAMO_OPS = (
    "amoswap",
    "amoadd",
    "amoand",
    "amoor",
    "amoxor",
    "amomax",
    "amomaxu",
    "amomin",
    "amominu",
)


def _add_tc(test_data: TestData, binname: str, coverpoint: str, covergroup: str) -> str:
    """Register a testcase with a new line in front of it."""
    # Leading newline gives every testcase a blank separator line in the emitted asm.
    return "\n" + test_data.add_testcase(binname, coverpoint, covergroup)


def _csr_access(instr: str, mode: str) -> str:
    """Accesses a CSR using an T-SBI or CSR operation based on mode"""
    return tsbi_call_or_direct(instr, MODE_UDB_LETTER[mode])


def _csr_access_m(instr: str, mode: str) -> str:
    """Access a CSR from M-mode: directly in SdtrigSm, through T-SBI otherwise, also for the S-level context CSRs."""
    return instr if mode == "Sm" else tsbi_call(instr)


def _load_tdata1(reg: int, trig_type: int, mode: str, lowfields: int = 0) -> list[str]:
    """Load tdata1 = (type << top) | lowfields into x{reg} and write it to tdata1."""
    lines = [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, 0x{(trig_type << 60) | lowfields:x})",
        "#else",
        f"LI(x{reg}, 0x{(trig_type << 28) | lowfields:x})",
        "#endif",
    ]
    lines.append(_csr_access(f"csrw tdata1, x{reg} # write trigger type", mode))
    return lines


def _if_implemented(csr: str, line: str) -> list[str]:
    """``line`` under ``#ifdef UDB_<CSR>_IMPLEMENTED`` for tdata2 and tdata3, which a hart need not implement."""
    if csr in ("tdata2", "tdata3"):
        return [f"#ifdef UDB_{csr.upper()}_IMPLEMENTED", line, "#endif"]
    return [line]


def _arm_type(reg: int, trig_type: int, mode: str) -> list[str]:
    """Set tdata1.type = trig_type the way Sdtrig.adoc says a debugger should.

    Write 0 to tdata1, then a tdata2 legal for every type, then tdata1. A trigger
    that already holds another type may legally ignore a direct type change
    (Sail keeps it), and an access to tdata1 itself changes the type, so the
    type is re-armed before every access that the coverage samples.
    """
    return [
        _csr_access("csrw tdata1, x0 # disable trigger", mode),
        *_if_implemented("tdata2", _csr_access("csrw tdata2, x0 # tdata2 legal for every type", mode)),
        *_load_tdata1(reg, trig_type, mode),
    ]


def _global_ie(mode: str, enable: bool) -> list[str]:
    """Arm or disarm action=0 triggers in ``mode``.

    Harts gate these triggers on mstatus.MIE/SIE or, in M-mode, on tcontrol.mte (the two Sdtrig reentrancy options,
    SDTRIG_BREAKPOINT_REENTRANCY). Set the bit each option uses.
    """
    op, why = ("csrsi", "arm") if enable else ("csrci", "disarm")
    if mode == "Sm":
        return [
            f"{op} mstatus, 0x8 # MIE={int(enable)} to {why} M-mode triggers",
            "#ifdef UDB_SDTRIG_BREAKPOINT_REENTRANCY_USE_TCONTROL",
            f"{op} tcontrol, 0x8 # MTE={int(enable)} to {why} M-mode triggers",
            "#endif",
        ]
    if mode == "S":
        return [f"{op} sstatus, 0x2 # SIE={int(enable)} to {why} S-mode triggers"]
    return []


def _load_reg(reg: int, val: int | str) -> str:
    """Emit a load of ``val`` into x{reg}: ints via LI (constant), symbols via LA (address)."""
    return f"LA(x{reg}, {val})" if isinstance(val, str) else f"LI(x{reg}, 0x{val:x})"


def _sigupd_masked(data_reg: int, temp_reg: int, mask: int, test_data: TestData, comment: str = "") -> list[str]:
    """Clear ``mask`` bits in x{data_reg} (optional/non-portable fields), then sigupd it."""
    note = f" # {comment}" if comment else ""
    return [
        f"LI(x{temp_reg}, 0x{mask:x}){note}",
        f"not x{temp_reg}, x{temp_reg}",
        f"and x{data_reg}, x{data_reg}, x{temp_reg} # mask out",
        write_sigupd(data_reg, test_data),
    ]


def _arch_guard(instr: str, exts: list[str]) -> list[str]:
    """Bracket a single instruction with `.option arch, +ext...` (no-op if exts empty)."""
    if not exts:
        return [instr]
    adds = ", ".join(f"+{e.strip().lower()}" for e in exts)
    return [".option push", f".option arch, {adds}", instr, ".option pop"]


def _ifdef_guard(instr: str, closing: bool = False) -> list[str]:
    """Emit the opening #ifdef guards for instr (or matching #endif when closing)."""
    ifdefs = INSTR_IFDEFS[instr]
    if closing:
        return ["#endif"] * len(ifdefs)
    return list(ifdefs)


def _select_trigger(reg: int, trig_num: int, mode: str) -> list[str]:
    """Select trigger ``trig_num`` once at the start of its block, and disable it.

    The _config_* helpers expect the selected trigger to be disabled, and every case disables it again at its end
    with _disable_trigger. tdata1 resets to an UNDEFINED_LEGAL value, so the trigger may be armed out of reset.
    """
    return [
        f"\n# select and disable trigger {trig_num}",
        _load_reg(reg, trig_num),
        _csr_access(f"csrw tselect, x{reg}", mode),
        _csr_access("csrw tdata1, x0 # disable", mode),
    ]


def _disable_trigger(mode: str) -> list[str]:
    """Disable the selected trigger at the end of a case, so the next _config_* finds it disabled."""
    return [_csr_access("csrw tdata1, x0 # disable trigger", mode)]


def _mprv_as_umode_setup(scratch_reg: int) -> list[str]:
    """MPRV=1, MPP=U: next load/store is translated as if from U-mode."""
    return [
        f"LI(x{scratch_reg}, {hex(_MSTATUS_MPP_MASK)})",
        f"csrc mstatus, x{scratch_reg} # MPP=U",
        f"LI(x{scratch_reg}, {hex(_MSTATUS_MPRV)})",
        f"csrs mstatus, x{scratch_reg} # MPRV=1",
    ]


def _mprv_as_umode_clear(scratch_reg: int) -> list[str]:
    """Clear MPRV, restoring normal M-mode (untranslated) access."""
    return [
        f"LI(x{scratch_reg}, {hex(_MSTATUS_MPRV)})",
        f"csrc mstatus, x{scratch_reg} # MPRV=0",
    ]


def _set_medeleg(reg: int, code: int, enable: bool) -> list[str]:
    """Set or clear medeleg[code]."""
    op = "csrs" if enable else "csrc"
    return [
        f"LI(x{reg}, 0x{1 << code:x})",
        f"{op} medeleg, x{reg} # medeleg[{code}]={int(enable)}",
    ]


def pf_data_section() -> list[str]:
    """Backing page the invalid target PTE points at."""
    return [
        ".pushsection .data",
        ".p2align 12",
        "pf_target_page:",
        "jr ra",
        ".zero 4096",
        ".popsection",
    ]


def pf_mode_arm(mode: str) -> list[str]:
    """Point satp at an invalid target PTE. U-mode also elevates to S first,
    maps its own code page, and drops back to U at the end. Nothing without paging (no satp)."""

    if mode not in ("Sm", "S", "U"):
        raise ValueError(f"pf_mode_arm: mode must be 'Sm', 'S' or 'U', got {mode!r}")

    lines = [f"\n# pf_mode_arm: set up page-fault PTEs for {mode}-mode", _PAGING_GUARD]
    if mode == "U":
        lines.append("RVTEST_TSBI_GOTO_SMODE")
    lines += [
        "#if __riscv_xlen == 64",
        "#ifdef SV39_SUPPORTED",
        f"SUPERPAGE_PTE_SETUP_SV39(pf_target_page, ({_PTE_INVALID}), 0x{VA_TARGET_RV64:x}, LEVEL2)",
    ]
    if mode == "U":
        lines += [
            f"SUPERPAGE_PTE_SETUP_SV39(rvtest_code_begin, ({_PTE_UPAGE}), 0x{VA2_TARGET_RV64:x}, LEVEL2)",
            "LA(a0, Mtramptbl_sv)",
            f"SAVE_AREA_SETUP(0x{VA2_TARGET_RV64:x}, rvtest_code_begin, code, LEVEL2)",
        ]
    lines += [
        "SATP_SETUP_RV64(sv39)",
        "sfence.vma",
        "#endif",
        "#else",
        "#ifdef SV32_SUPPORTED",
        f"SUPERPAGE_PTE_SETUP_SV32(pf_target_page, ({_PTE_INVALID}), 0x{VA_TARGET_RV32:x}, LEVEL1)",
    ]
    if mode == "U":
        lines += [
            f"SUPERPAGE_PTE_SETUP_SV32(rvtest_code_begin, ({_PTE_UPAGE}), 0x{VA2_TARGET_RV32:x}, LEVEL1)",
            "LA(a0, Mtramptbl_sv)",
            f"SAVE_AREA_SETUP(0x{VA2_TARGET_RV32:x}, rvtest_code_begin, code, LEVEL1)",
        ]
    lines += [
        "SATP_SETUP_SV32",
        "sfence.vma",
        "#endif",
        "#endif",
    ]
    if mode == "U":
        lines.append("RVTEST_TSBI_GOTO_UMODE")
    lines.append("#endif // paging")
    return lines


def pf_mode_disarm(mode: str) -> list[str]:
    """Clear satp. U-mode elevates to S first since U can't touch satp itself. Nothing without paging."""
    if mode not in ("Sm", "S", "U"):
        raise ValueError(f"pf_mode_disarm: mode must be 'Sm', 'S' or 'U', got {mode!r}")

    lines = [f"\n# pf_mode_disarm: clear page tables for {mode}-mode", _PAGING_GUARD]
    if mode == "U":
        lines.append("RVTEST_TSBI_GOTO_SMODE")
    lines.extend(
        [
            "csrwi satp, 0",
            "sfence.vma",
        ]
    )
    if mode == "U":
        lines.extend(
            [
                "LA(a0, Mtramptbl_sv)",
                "LA(t0, rvtest_code_begin)",
                "SREG t0, code_bgn_off+1*sv_area_sz(a0)",
                "RVTEST_TSBI_GOTO_UMODE",
            ]
        )
    lines.append("#endif // paging")
    return lines


def _etrigger_codes_to_test(mode: str, cross_priv: bool = False) -> dict[int, bool]:
    """Return {code: raisable} for every exception code tested from ``mode``.

    raisable=True : match case and mismatch case.
    raisable=False: the code cannot be raised here, so mismatch case only.
    """
    valid_modes = ("S", "U") if cross_priv else ("Sm", "S", "U")
    if mode not in valid_modes:
        raise ValueError(f"Unsupported {'target ' if cross_priv else ''}mode: {mode}")

    raisable = set(_ETRIGGER_BASE_CODES) | {_ETRIGGER_ECALL_CODE[mode]}
    if mode == "Sm":
        raisable.discard(12)  # M-mode fetches are never translated

    generated = set(_ETRIGGER_BASE_CODES) | set(_ETRIGGER_MISMATCH_ONLY_CODES) | set(_ETRIGGER_ECALL_CODE.values())
    return {code: code in raisable for code in sorted(generated)}


def _cause_exception(
    code: int,
    mode: str,
    addr_reg: int | None = None,
    data_reg: int | None = None,
    *,
    mprv_scratch_reg: int | None = None,
) -> list[str]:
    """Emit assembly that synchronously raises mcause exception ``code``."""

    if code == 1:  # instruction access fault
        if addr_reg is None:
            raise ValueError("addr_reg is required for instruction access fault")

        return [
            f"la x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS",
            f"jalr ra, 0(x{addr_reg})",
            "nop # spacer; trap handler returns here",
        ]

    if code == 2:  # illegal instruction
        return [".word 0xffffffff # illegal instruction"]

    if code == 5:  # load access fault
        if addr_reg is None:
            raise ValueError("addr_reg is required for load access fault")

        return [
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"lw x{data_reg}, 0(x{addr_reg}) # load access fault",
        ]

    if code == 7:
        if addr_reg is None or data_reg is None:
            raise ValueError("addr_reg and data_reg are required for store access fault")
        return [
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"sw x0, 0(x{addr_reg}) # store access fault",
            "nop # spacer; trap handler returns here",
        ]

    if code in (8, 9, 11):  # Ecall from U-mode, S-mode, M-mode
        return [f"RVTEST_TSBI_ECALL_TEST # ecall from {mode}-mode"]

    if code == 12:
        if addr_reg is None:
            raise ValueError("addr_reg is required for instruction page fault")

        if mode == "Sm":
            raise ValueError(
                "_cause_exception: code 12 cannot be raised with mode='Sm' M-mode fetches are never translated"
            )

        return [
            "#if __riscv_xlen == 64",
            f"LI(x{addr_reg}, 0x{VA_TARGET_RV64:x})",
            "#else",
            f"LI(x{addr_reg}, 0x{VA_TARGET_RV32:x})",
            "#endif",
            f"jalr ra, 0(x{addr_reg}) # instruction page fault",
            "nop # spacer; trap handler returns here",
        ]

    if code == 13:  # load page fault
        if addr_reg is None or data_reg is None:
            raise ValueError("addr_reg and data_reg are required for load page fault")

        lines = [
            "#if __riscv_xlen == 64",
            f"LI(x{addr_reg}, 0x{VA_TARGET_RV64:x})",
            "#else",
            f"LI(x{addr_reg}, 0x{VA_TARGET_RV32:x})",
            "#endif",
        ]
        if mode == "Sm":
            assert mprv_scratch_reg is not None
            lines.extend(_mprv_as_umode_setup(mprv_scratch_reg))
        lines.append(f"lw x{data_reg}, 0(x{addr_reg}) # load page fault")
        lines.append("nop # spacer; trap handler returns here")
        if mode == "Sm":
            assert mprv_scratch_reg is not None
            lines.extend(_mprv_as_umode_clear(mprv_scratch_reg))
        return lines

    if code == 15:  # store/AMO page fault
        if addr_reg is None or data_reg is None:
            raise ValueError("addr_reg and data_reg are required for store page fault")

        lines = [
            "#if __riscv_xlen == 64",
            f"LI(x{addr_reg}, 0x{VA_TARGET_RV64:x})",
            "#else",
            f"LI(x{addr_reg}, 0x{VA_TARGET_RV32:x})",
            "#endif",
            f"LI(x{data_reg}, 0xDEADBEEF)",
        ]
        if mode == "Sm":
            assert mprv_scratch_reg is not None
            lines.extend(_mprv_as_umode_setup(mprv_scratch_reg))
        lines.append(f"sw x{data_reg}, 0(x{addr_reg}) # store page fault")
        lines.append("nop # spacer; trap handler returns here")
        if mode == "Sm":
            assert mprv_scratch_reg is not None
            lines.extend(_mprv_as_umode_clear(mprv_scratch_reg))
        return lines

    raise ValueError(
        f"_cause_exception: exception code {code} ({ETRIGGER_EXCODE_NAMES.get(code, '?')}) not implemented yet"
    )


def _cause_interrupt(code: int, mode: str, r1: int) -> list[str]:
    """Emit assembly that makes interrupt ``code`` (mcause interrupt code) pending."""
    flavor = "M" if mode == "Sm" else mode
    if code == 1:  # supervisor software interrupt (SSIP)
        return [f"LI(x{r1}, 0x2) # SSIP", _csr_access(f"csrs mip, x{r1}", mode)]
    if code == 5:  # supervisor timer interrupt (STIP)
        return [f"LI(x{r1}, 0x20) # STIP", _csr_access(f"csrs mip, x{r1}", mode)]
    if code == 9:  # supervisor external interrupt (SEIP)
        return [f"LI(x{r1}, 0x200) # SEIP", _csr_access(f"csrs mip, x{r1}", mode)]
    if code == 13:  # local counter overflow interrupt (LCOFIP)
        return [f"LI(x{r1}, 0x2000) # LCOFIP", _csr_access(f"csrs mip, x{r1}", mode)]
    if code == 3:  # machine software interrupt (CLINT MSIP; M-mode only)
        return [f"RVTEST_SET_MSW_INT_{flavor}"]
    if code == 7:  # machine timer interrupt (mtimecmp = mtime; M-mode only)
        return [f"RVTEST_SET_MTIME_INT_{flavor}"]
    if code == 11:  # machine external interrupt (PLIC MEIP; M-mode only)
        return [f"RVTEST_SET_MEXT_INT_{flavor}"]
    raise ValueError(f"unsupported interrupt code {code}")


_INT_MACRO = {
    1: "SSW",
    3: "MSW",
    5: "STIME",
    7: "MTIME",
    9: "SEXT",
    11: "MEXT",
    13: "LCOFI",
}
_INT_TYPE = {
    1: "SSI",
    3: "MSI",
    5: "STI",
    7: "MTI",
    9: "SEI",
    11: "MEI",
    13: "LCOFI",
}


def _clear_interrupt(code: int, mode: str) -> list[str]:
    """Clear interrupt ``code`` using the standard ACT4 interrupt macro."""
    int_type = _INT_TYPE[code]
    guard = guard_symbol(int_type)
    macro = _INT_MACRO[code]
    priv = "M" if mode == "Sm" else mode

    return [
        f"#ifdef {guard}",
        f"RVTEST_CLR_{macro}_INT_{priv} # clear interrupt {code}",
        f"#endif // {guard}",
    ]


def _config_mcontrol6(
    reg: int,
    tselect: int,
    tdata2: int | str | list[str],
    mode: str,
    *,
    privbits: int | None = None,
    xsl: int = 0b000,
    select: int = 0,
    size: int = 0,
    match: int = 0,
    chain: int = 0,
    action: int = 0,
    tdata3: int | str | list[str] = 0,
) -> list[str]:
    """Emit assembly configuring trigger ``tselect`` as an mcontrol6 trigger.

    Expects ``tselect`` to be selected (_select_trigger) and disabled: the previous case ended with _disable_trigger.
    """
    if privbits is None:
        privbits = MODE_PRIVBIT[mode]

    m = (privbits >> 4) & 1
    s = (privbits >> 3) & 1
    u = (privbits >> 2) & 1
    vs = (privbits >> 1) & 1
    vu = privbits & 1
    lowfields = (
        (vs << 24)
        | (vu << 23)
        | (select << 21)
        | ((size & 0b111) << 16)
        | (action << 12)
        | (chain << 11)
        | ((match & 0xF) << 7)
        | (m << 6)
        | (s << 4)
        | (u << 3)
        | (xsl & 0b111)
    )
    mcontrol6 = 6  # tdata1.type
    lines: list[str] = []
    lines.extend(
        [
            f"# configure trigger {tselect} as mcontrol6 (already selected and disabled)",
            *_load_value_or_lines(reg, tdata2),
            *_if_implemented("tdata2", _csr_access(f"csrw tdata2, x{reg} # match value", mode)),
            *_write_tdata3(reg, tdata3, mode),
            f"# tdata1: type={mcontrol6} priv={privbits:05b} xsl={xsl:03b} select={select} size={size} match={match} chain={chain}",
            *_load_tdata1(reg, mcontrol6, mode, lowfields),  # load data in tdata1
        ]
    )
    return lines


def _config_icount(
    reg: int,
    tselect: int,
    count: int,
    mode: str,
    *,
    privbits: int | None = None,
    pending: int = 0,
    action: int = 0,
    tdata3: int | str | list[str] = 0,
) -> list[str]:
    """Emit assembly configuring trigger ``tselect`` as an icount trigger.

    Expects ``tselect`` to be selected (_select_trigger) and disabled: the previous case ended with _disable_trigger.
    """
    if privbits is None:
        privbits = MODE_PRIVBIT[mode]

    m = (privbits >> 4) & 1
    s = (privbits >> 3) & 1
    u = (privbits >> 2) & 1
    vs = (privbits >> 1) & 1
    vu = privbits & 1
    lowfields = (
        (vs << 26)
        | (vu << 25)
        | ((count & 0x3FFF) << 10)
        | (m << 9)
        | (pending << 8)
        | (s << 7)
        | (u << 6)
        | (action & 0x3F)
    )
    icount = 3  # tdata1.type
    lines: list[str] = []
    lines.extend(
        [
            f"# configure trigger {tselect} as icount (already selected and disabled)",
            *_write_tdata3(reg, tdata3, mode),
            f"# tdata1: type={icount} priv={privbits:05b} count={count} pending={pending} action={action}",
            *_load_tdata1(reg, icount, mode, lowfields),  # load data in tdata1
        ]
    )
    return lines


def _config_itrigger(
    reg: int,
    tselect: int,
    tdata2: int | str,
    mode: str,
    *,
    privbits: int | None = None,
    nmi: int = 0,
    action: int = 0,
    tdata3: int | str | list[str] = 0,
) -> list[str]:
    """Emit assembly configuring trigger ``tselect`` as an itrigger.

    Expects ``tselect`` to be selected (_select_trigger) and disabled: the previous case ended with _disable_trigger.
    """
    if privbits is None:
        privbits = MODE_PRIVBIT[mode]

    m = (privbits >> 4) & 1
    s = (privbits >> 3) & 1
    u = (privbits >> 2) & 1
    vs = (privbits >> 1) & 1
    vu = privbits & 1
    lowfields = (vs << 12) | (vu << 11) | (nmi << 10) | (m << 9) | (s << 7) | (u << 6) | (action & 0x3F)
    itrigger = 4  # tdata1.type
    lines: list[str] = []
    lines.extend(
        [
            f"# configure trigger {tselect} as itrigger (already selected and disabled)",
            _load_reg(reg, tdata2),
            *_if_implemented("tdata2", _csr_access(f"csrw tdata2, x{reg} # interrupt-cause mask", mode)),
            _csr_access(f"csrs mie, x{reg} # enable masked interrupt(s)", mode),
            *_write_tdata3(reg, tdata3, mode),
            f"# tdata1: type={itrigger} priv={privbits:05b} nmi={nmi} action={action}",
            *_load_tdata1(reg, itrigger, mode, lowfields),  # load data in tdata1
        ]
    )
    return lines


def _config_etrigger(
    reg: int,
    tselect: int,
    tdata2: int | str,
    mode: str,
    *,
    privbits: int | None = None,
    action: int = 0,
    tdata3: int | str | list[str] = 0,
) -> list[str]:
    """Emit assembly configuring trigger ``tselect`` as an etrigger.

    Expects ``tselect`` to be selected (_select_trigger) and disabled: the previous case ended with _disable_trigger.
    """
    if privbits is None:
        privbits = MODE_PRIVBIT[mode]

    m = (privbits >> 4) & 1
    s = (privbits >> 3) & 1
    u = (privbits >> 2) & 1
    vs = (privbits >> 1) & 1
    vu = privbits & 1
    lowfields = (vs << 12) | (vu << 11) | (m << 9) | (s << 7) | (u << 6) | (action & 0x3F)
    etrigger = 5  # tdata1.type
    lines: list[str] = []
    lines.extend(
        [
            f"# configure trigger {tselect} as etrigger (already selected and disabled)",
            _load_reg(reg, tdata2),
            *_if_implemented("tdata2", _csr_access(f"csrw tdata2, x{reg} # exception-cause mask", mode)),
            *_write_tdata3(reg, tdata3, mode),
            f"# tdata1: type={etrigger} priv={privbits:05b} action={action}",
            *_load_tdata1(reg, etrigger, mode, lowfields),  # load data in tdata1
        ]
    )
    return lines


# Trigger types _fire_supported_trigger can fire, with the defines that enable each on trigger {trig_num}
# armed for the running mode {mode_letter} (mcontrol6 writes that mode's m/s/u bit and a store match)
_FIRE_TYPE_GUARDS = {
    "mcontrol6": [
        "#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}",
        "#ifdef UDB_SDTRIG_{mode_letter}_WRITABLE",
        "#ifdef UDB_SDTRIG_MCONTROL6_STORE_WRITABLE",
    ],
    "icount": ["#ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}", "#ifdef UDB_SDTRIG_{mode_letter}_WRITABLE"],
}


def _fire_supported_trigger(
    trig_type: str, trig_num: int, mode: str, cfg_reg: int, addr_reg: int, data_reg: int
) -> list[str]:
    """Arm trig_num, already selected and disabled, as trig_type for ``mode``, make it fire once, and disable it.

    The trailing spacers are the instructions the trap handler skips, wherever the breakpoint is taken.
    """
    if trig_type == "mcontrol6":  # watch &scratch, fire with a store to it
        return [
            *_config_mcontrol6(cfg_reg, trig_num, "scratch", mode, xsl=0b010, select=0),
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{data_reg}, 0x{random_int(32, signed=False):x})",
            f"sw x{data_reg}, 0(x{addr_reg}) # fire mcontrol6",
            "nop # spacer (an address match may fire after the store)",
            *_disable_trigger(mode),
        ]
    if trig_type == "icount":  # count=1: fires on the next retired instruction
        return [
            *_config_icount(cfg_reg, trig_num, 1, mode),
            "nop # icount: count reaches 0 and pending is set",
            "nop # spacer: the instruction the breakpoint is taken on",
            *_disable_trigger(mode),
        ]
    raise ValueError(f"unsupported trigger type: {trig_type}")


def _textra3(
    xlen: int, *, mhselect: int = 0, mhvalue: int = 0, sselect: int = 0, svalue: int = 0, sbytemask: int = 0
) -> int:
    """Encode textra32/textra64 (tdata3) from its fields."""
    if xlen == 64:
        return (
            ((mhvalue & 0x1FFF) << 51)
            | ((mhselect & 0x7) << 48)
            | ((sbytemask & 0xF) << 36)
            | ((svalue & 0xFFFFFFFF) << 2)
            | (sselect & 0x3)
        )
    return (
        ((mhvalue & 0x3F) << 26)
        | ((mhselect & 0x7) << 23)
        | ((sbytemask & 0x3) << 18)
        | ((svalue & 0xFFFF) << 2)
        | (sselect & 0x3)
    )


def _xlen_li(reg: int, val32: int, val64: int) -> list[str]:
    """XLEN-guarded LI of val64 (RV64) or val32 (RV32)."""
    return ["#if __riscv_xlen == 64", f"LI(x{reg}, 0x{val64:x})", "#else", f"LI(x{reg}, 0x{val32:x})", "#endif"]


def _xlen_li_expr(reg: int, expr32: str, expr64: str) -> list[str]:
    """XLEN-guarded LI of an assembler expression."""
    return ["#if __riscv_xlen == 64", f"LI(x{reg}, {expr64})", "#else", f"LI(x{reg}, {expr32})", "#endif"]


def _mhvalue(val: int) -> str:
    """mhvalue (and the mcontext it is compared with) limited to the SDTRIG_TEXTRA_MHVALUE_LEN implemented bits."""
    return f"(0x{val:x} & {_MHVALUE_MASK})"


def _svalue(val: int | str) -> str:
    """svalue (and the scontext it is compared with) limited to the SDTRIG_TEXTRA_SVALUE_LEN implemented bits."""
    return f"(({val if isinstance(val, str) else hex(val)}) & {_SVALUE_MASK})"


def _textra_expr(
    xlen: int, *, mhselect: int = 0, mhvalue: str = "0", sselect: int = 0, svalue: str = "0", sbytemask: int = 0
) -> str:
    """textra32/textra64 (tdata3) as a parenthesized assembler expression, with mhvalue and svalue expressions."""
    if xlen == 64:
        fields = [f"(({mhvalue}) << 51)", f"({mhselect & 7} << 48)", f"({sbytemask & 0xF} << 36)", f"(({svalue}) << 2)"]
    else:
        fields = [f"(({mhvalue}) << 26)", f"({mhselect & 7} << 23)", f"({sbytemask & 0x3} << 18)", f"(({svalue}) << 2)"]
    return f"({' | '.join(fields)} | {sselect & 3})"


def _xlen_value(val32: int) -> tuple[int, int]:
    """(RV32, RV64) data values for a select = data match: val32, and on RV64 val32 with its complement above it.

    With size = 0 (any) a data match is only well-defined when the access is XLEN wide (norm:Sdtrig_mcontrol6_size_any),
    so these are stored and loaded with SREG/LREG, and the upper half on RV64 makes the whole register count.
    """
    return val32, ((~val32 & 0xFFFFFFFF) << 32) | val32


def _config_textra(reg: int, trig_num: int, trig_type: str, tdata3_lines: list[str], mode: str) -> list[str]:
    """Configure trig_num as trig_type with the given tdata3 load, reusing each type's own configurator."""
    if trig_type == "icount":
        return _config_icount(reg, trig_num, 1, mode, tdata3=tdata3_lines)
    if trig_type == "mcontrol6":
        tdata2 = _xlen_li(reg, *_xlen_value(_TEXTRA_DATA))
        return _config_mcontrol6(reg, trig_num, tdata2, mode, xsl=0b010, select=1, tdata3=tdata3_lines)
    raise ValueError(f"unsupported textra trigger type: {trig_type}")


def _fire_textra_trigger(trig_type: str, mode: str, cfg_reg: int, addr_reg: int, data_reg: int) -> list[str]:
    """Perform trig_type's action; the trailing spacer is the instruction the trap handler skips."""
    if trig_type == "icount":
        return [
            "nop # icount: decrement count and test context match",
            "nop # spacer: the instruction the breakpoint is taken on",
        ]
    if trig_type == "mcontrol6":
        return [
            f"LA(x{addr_reg}, scratch)",
            *_xlen_li(data_reg, *_xlen_value(_TEXTRA_DATA)),
            f"SREG x{data_reg}, 0(x{addr_reg}) # mcontrol6 XLEN-wide data-store trigger",
            "nop # spacer (data match fires after)",
        ]
    raise ValueError(f"unsupported textra trigger type: {trig_type}")


def _sign_trap_count(temp_reg: int, test_data: TestData) -> list[str]:
    """Sign rvtest_trap_count so each case's fire/no-fire is checked in place, not only the total trap count."""
    return [
        f"LA(x{temp_reg}, rvtest_trap_count)",
        f"LREG x{temp_reg}, 0(x{temp_reg}) # traps taken so far",
        write_sigupd(temp_reg, test_data),
    ]


def _load_value_or_lines(reg: int, val: int | str | list[str]) -> list[str]:
    """Load val into x{reg}; a list is spliced in as-is, otherwise falls back to _load_reg."""
    return val if isinstance(val, list) else [_load_reg(reg, val)]


def _write_tdata3(reg: int, tdata3: int | str | list[str], mode: str) -> list[str]:
    """Write tdata3 (textra context matching) where the hart implements it."""
    return [
        "#ifdef UDB_TDATA3_IMPLEMENTED",
        *_load_value_or_lines(reg, tdata3),
        _csr_access(f"csrw tdata3, x{reg} # textra context matching", mode),
        "#endif",
    ]


### COVERPOINTS


def _generate_access_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate common trigger-CSR access tests.

    Only SdtrigSm has cp_csr_access_common. Through T-SBI, SdtrigS would make the same M-mode accesses, which
    SdtrigSm already covers on every hart with S, at about 150 times the cost. SdtrigS and SdtrigU have only the
    direct accesses of _generate_access_trap_tests.
    """
    if mode != "Sm":
        return _generate_access_trap_tests(test_data, mode)
    covergroup = f"Sdtrig{mode}_access_cg"
    chunks: list[TestChunk] = []

    ######################################
    coverpoint = "cp_csr_access_common"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "Access every trigger CSR across all triggers and the types {3, 4, 5, 6, 15} each supports\n"
            "Should not cause any illegal instruction exceptions on implemented triggers",
        )
    )
    # tdata1 and tinfo exist whenever Sdtrig is tested; the rest are optional (UDB_<CSR>_IMPLEMENTED).
    csrs = ("tdata1", "tdata2", "tdata3", "tinfo", "tcontrol", "scontext", "mcontext", "hcontext")
    optional_csrs = ("tdata2", "tdata3", "tcontrol", "scontext", "mcontext", "hcontext")

    type_reg, save_reg, temp_reg = test_data.int_regs.get_registers(
        3, exclude_regs=[10, 11]
    )  # exclude a0, a1 because they are used in SBI

    for trig_num in TRIGGERS:
        for trig_type in ACCESS_TYPES:
            guard = _type_guard(trig_type, trig_num)
            lines.append(f"\n#ifdef {guard}" if guard else f"\n{_num_guard(trig_num)}")
            for csr in csrs:
                if csr in optional_csrs:
                    lines.append(f"#ifdef UDB_{csr.upper()}_IMPLEMENTED")
                binname = f"tselect_{trig_num}_type_{trig_type}_csr_{csr}"
                lines.extend(
                    [
                        _add_tc(test_data, binname, coverpoint, covergroup),
                        f"LI x{temp_reg}, {trig_num} # load trig_num value",
                        _csr_access(f"csrw tselect, x{temp_reg} # set tselect = trig_num", mode),
                        *_arm_type(type_reg, trig_type, mode),
                        f"LI x{temp_reg}, -1 # load all 1's value",
                        _csr_access_m(f"csrr x{save_reg}, {csr} # save original value", mode),
                        _csr_access_m(f"csrw {csr}, x{temp_reg} # write all-1s", mode),
                        *_arm_type(type_reg, trig_type, mode),
                        _csr_access_m(f"csrw {csr}, x0 # write all-0s", mode),
                        *_arm_type(type_reg, trig_type, mode),
                        _csr_access_m(f"csrs {csr}, x{temp_reg} # set all-1s", mode),
                        *_arm_type(type_reg, trig_type, mode),
                        _csr_access_m(f"csrc {csr}, x{temp_reg} # clear all-1s", mode),
                        _csr_access_m(f"csrw {csr}, x{save_reg} # write back original value", mode),
                    ]
                )
                if csr in optional_csrs:
                    lines.append("#endif")
            lines.append(f"#endif // {guard or 'UDB_SDTRIG_NUM_TRIGGERS'}")

    test_data.int_regs.return_registers([type_reg, save_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _generate_access_trap_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """SdtrigS/U access tests: a direct S/U-mode read or write of an M-level trigger CSR raises an illegal-instruction exception.

    scontext and hcontext are S/H-level and gated by mstateen0.CONTEXT; Smstateen/Ssstateen test those.
    """
    covergroup = f"Sdtrig{mode}_access_cg"
    chunks: list[TestChunk] = []

    ######################################
    coverpoint = f"cp_csr_access_trap_{mode.lower()}"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint, f"Direct {mode}-mode reads and writes of the M-level trigger CSRs raise illegal instruction"
        )
    )
    (data_reg,) = test_data.int_regs.get_registers(1, exclude_regs=[10, 11])
    for csr in ("tselect", "tdata1", "tdata2", "tdata3", "tinfo", "tcontrol", "mcontext"):
        optional = csr in ("tcontrol", "mcontext")
        if optional:
            lines.append(f"#ifdef UDB_{csr.upper()}_IMPLEMENTED")
        lines.extend(
            [
                _add_tc(test_data, csr, coverpoint, covergroup),
                f"LI(x{data_reg}, 0)",
                f"csrr x{data_reg}, {csr} # illegal from {mode}-mode",
                f"csrw {csr}, x{data_reg} # illegal from {mode}-mode",
            ]
        )
        if optional:
            lines.append("#endif")
    test_data.int_regs.return_registers([data_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _generate_native_triggers_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate native-trigger breakpoint-delegation tests (S and U suites).

    Each supported trigger type fires once from ``mode`` with medeleg[3] clear and once with it set. The trap
    record names the mode the breakpoint was handled in, and rvtest_trap_count is signed after each case.
    SIE stays 1 in the S suite: with medeleg[3]=1, harts using the interrupt-enable re-entrancy option do not
    fire S-mode triggers while SIE=0.
    """
    covergroup = f"Sdtrig{mode}_cg"
    seed(reproducible_hash(covergroup))
    chunks: list[TestChunk] = []

    ######################################
    coverpoint = f"cp_breakpoint_delegate_{mode.lower()}"
    ######################################
    lines = test_data.new_test_chunk(chunks, "breakpoint_delegate").code
    lines.append(
        comment_banner(
            coverpoint,
            f"Breakpoint from a trigger fired in {mode}-mode: taken in M with medeleg[3]=0, delegated to S\n"
            "with medeleg[3]=1 (M on a hart that hard-wires medeleg[3] to 0)",
        )
    )
    cfg_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        4, exclude_regs=[2, 10, 11], reg_range=list(range(8, 16))
    )
    for delegate in (0, 1):
        # T-SBI does not write medeleg, so change it in M-mode
        lines.extend(
            [
                "RVTEST_TSBI_GOTO_MMODE",
                *_set_medeleg(temp_reg, 3, bool(delegate)),
                f"RVTEST_TSBI_GOTO_{mode}MODE",
                *_global_ie(mode, True),
            ]
        )
        for trig_num in TRIGGERS:
            lines.extend([f"\n{_num_guard(trig_num)}", *_select_trigger(cfg_reg, trig_num, mode)])
            for trig_type, type_guards in _FIRE_TYPE_GUARDS.items():
                guards = [g.format(trig_num=trig_num, mode_letter=MODE_UDB_LETTER[mode]) for g in type_guards]
                lines.extend(
                    [
                        *guards,
                        _add_tc(
                            test_data, f"trig_num_{trig_num}_{trig_type}_delegate_{delegate}", coverpoint, covergroup
                        ),
                        *_fire_supported_trigger(trig_type, trig_num, mode, cfg_reg, addr_reg, data_reg),
                        *_sign_trap_count(data_reg, test_data),
                        *(["#endif"] * len(guards)),
                    ]
                )
            lines.append(f"#endif // UDB_SDTRIG_NUM_TRIGGERS > {trig_num}")
    lines.extend(_global_ie(mode, False))  # medeleg[3] stays 1, as the suite boots

    test_data.int_regs.return_registers([cfg_reg, addr_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


LRSC_SENTINEL = 0xBAD5EED  # preloaded into the lr/sc rd: no load of scratch or SC result writes it
LRSC_SIG_KEY = 0x5A5A5A5A  # xor'd into recorded lr/sc words so none equals 0 or dataval, which a data trigger may watch


def _lrsc_pair(
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    bins: tuple[str, str],
    regs: tuple[int, int, int, int, int],
    width: str,
    comments: tuple[str, str],
    *,
    data_match: bool = False,
) -> list[str]:
    """Emit one lr; nop; sc; nop sequence (an LR bin and an SC bin) after the trigger is configured.

    The LR and SC stay contiguous, so the pair is a constrained LR/SC sequence. Afterwards the signature
    records LR's result (the sentinel if the trigger skipped the LR) and whether the trigger skipped the SC
    (its rd still holds the sentinel). The SC result itself is not recorded: after a skipped or trapped LR
    it is implementation-defined.

    Address matches fire before the access on every hart (the suggested timing), so the skips tell an LR
    fire from an SC fire. A data match may fire before or after the access (Whisper fires load data before,
    Sail after), so with ``data_match`` a skipped LR records the value it would have loaded, and the SC flag
    is not recorded; the trap records still count the fires.
    """
    lr_reg, sc_reg, addr_reg, data_reg, temp_reg = regs
    lines = [
        f"LI(x{lr_reg}, 0x{LRSC_SENTINEL:x}) # sentinel: still here if the trigger skips the lr",
        f"LI(x{sc_reg}, 0x{LRSC_SENTINEL:x}) # sentinel: still here if the trigger skips the sc",
        _add_tc(test_data, bins[0], coverpoint, covergroup),
    ]
    lr_label = test_data.current_testcase_label
    lines.extend(
        [
            *_arch_guard(f"lr.{width} x{lr_reg}, (x{addr_reg}) # {comments[0]}", ["zalrsc"]),
            "nop # spacer (lands here after a trigger that fires after the lr)",
            _add_tc(test_data, bins[1], coverpoint, covergroup),
            *_arch_guard(f"sc.{width} x{sc_reg}, x{data_reg}, (x{addr_reg}) # {comments[1]}", ["zalrsc"]),
            "nop # spacer (lands here after a trigger that fires after the sc)",
        ]
    )
    if data_match:
        lines.extend(
            [
                f"LI(x{temp_reg}, 0x{LRSC_SENTINEL:x})",
                f"bne x{lr_reg}, x{temp_reg}, 1f # lr ran",
                f"mv x{lr_reg}, x{data_reg} # data matches use XLEN-wide lr only, so lr loads all of dataval",
                f"1: # x{lr_reg} = what lr loaded, whether the trigger fired before or after it",
            ]
        )
    lines.extend(
        [
            f"LI(x{temp_reg}, 0x{LRSC_SIG_KEY:x}) # key for the recorded words",
            f"xor x{lr_reg}, x{lr_reg}, x{temp_reg} # lr result ^ key",
            write_sigupd(lr_reg, test_data, label=lr_label),
        ]
    )
    if not data_match:
        lines.extend(
            [
                f"LI(x{lr_reg}, 0x{LRSC_SENTINEL:x})",
                f"sub x{sc_reg}, x{sc_reg}, x{lr_reg}",
                f"seqz x{sc_reg}, x{sc_reg} # 1 = trigger skipped the sc",
                f"xor x{sc_reg}, x{sc_reg}, x{temp_reg} # sc-skipped flag ^ key",
                write_sigupd(sc_reg, test_data),
            ]
        )
    return lines


def _generate_zalrsc_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate lr/sc matching tests."""
    covergroup = f"Sdtrig{mode}_a_cg"
    seed(reproducible_hash(covergroup))
    chunks: list[TestChunk] = []

    # setup registers
    lr_reg, sc_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        5, exclude_regs=[2], reg_range=list(range(8, 16))
    )
    regs = (lr_reg, sc_reg, addr_reg, data_reg, temp_reg)

    # bit 31 set so lr.w on RV64 shows the sign extension of the loaded word
    dataval = random_int(32, signed=False, nonzero=True) << 32 | random_int(32, signed=False) | 0x80000000
    recorded = {LRSC_SIG_KEY, LRSC_SIG_KEY ^ 1, LRSC_SENTINEL ^ LRSC_SIG_KEY}
    assert not recorded & {0, dataval & 0xFFFFFFFF}, "a recorded lr/sc word would fire a data trigger"
    perms = (0b100, 0b010, 0b001)  # exec / store / load

    ######################################
    coverpoint = "cp_lrsc_addr"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when lr/sc address == tdata2 (select=address)",
        )
    )
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch) # x{addr_reg} = &scratch",
            _load_reg(data_reg, dataval),
            f"SREG x{data_reg}, 0(x{addr_reg}) # scratch = dataval before any trigger is armed; sc only rewrites it",
        ]
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend([*gates, *_select_trigger(temp_reg, trig_num, mode)])
        for tdata2 in ("scratch", 0):
            for perm in perms:  # perm_xsl
                lines.extend(_xsl_ifdefs(perm))
                for width in ("w", "d"):
                    lines.extend(_ifdef_guard(f"lr.{width}"))
                    lines.extend(
                        [
                            f"\n# trigger {trig_num}: tdata2={tdata2} xsl={perm:03b} on lr.{width}/sc.{width}",
                            f"LA(x{addr_reg}, scratch) # x{addr_reg} = &scratch",
                            _load_reg(data_reg, dataval),
                            *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=perm, select=0),
                            *_lrsc_pair(
                                test_data,
                                coverpoint,
                                covergroup,
                                (
                                    f"trig_num_{trig_num}_td2_{tdata2}_lr_{width}_perm_{perm:03b}",
                                    f"trig_num_{trig_num}_td2_{tdata2}_sc_{width}_perm_{perm:03b}",
                                ),
                                regs,
                                width,
                                (
                                    "fire iff addr==tdata2 and xsl has load bit",
                                    "fire iff addr==tdata2 and xsl has store bit",
                                ),
                            ),
                            *_disable_trigger(mode),
                        ]
                    )
                    lines.extend(_ifdef_guard(f"lr.{width}", closing=True))
                lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(perm)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_lrsc_data"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when lr/sc data == tdata2 (select=data)",
        )
    )
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch) # x{addr_reg} = &scratch",
            _load_reg(data_reg, dataval),
            f"SREG x{data_reg}, 0(x{addr_reg}) # load scratch with XLEN-wide dataval",
        ]
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode, select=1)
        lines.extend([*gates, *_select_trigger(temp_reg, trig_num, mode)])
        for td2_name, td2_base in (("dataval", dataval), ("zero", 0)):
            for perm in perms:  # perm_xsl
                lines.extend(_xsl_ifdefs(perm))
                for width in ("w", "d"):
                    tdata2 = td2_base & 0xFFFFFFFF if width == "w" else td2_base
                    lines.extend(_ifdef_guard(f"lr.{width}"))
                    if width == "w":  # size=0 data matches are defined only for XLEN-wide accesses
                        lines.append("#if __riscv_xlen == 32 // norm:Sdtrig_mcontrol6_size_any")
                    lines.extend(
                        [
                            f"\n# trigger {trig_num}: tdata2={td2_name} xsl={perm:03b} on lr.{width}/sc.{width} data",
                            f"LA(x{addr_reg}, scratch) # x{addr_reg} = &scratch",
                            _load_reg(data_reg, dataval),
                            *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=perm, select=1),
                            *_lrsc_pair(
                                test_data,
                                coverpoint,
                                covergroup,
                                (
                                    f"trig_num_{trig_num}_td2_{td2_name}_lr_{width}_perm_{perm:03b}",
                                    f"trig_num_{trig_num}_td2_{td2_name}_sc_{width}_perm_{perm:03b}",
                                ),
                                regs,
                                width,
                                (
                                    "fire iff data==tdata2 and xsl has load bit",
                                    "fire iff data==tdata2 and xsl has store bit",
                                ),
                                data_match=True,
                            ),
                            *_disable_trigger(mode),
                        ]
                    )
                    if width == "w":
                        lines.append("#endif // __riscv_xlen == 32")
                    lines.extend(_ifdef_guard(f"lr.{width}", closing=True))
                lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(perm)))
        lines.extend(_close_gates(gates))

    test_data.int_regs.return_registers([lr_reg, sc_reg, addr_reg, data_reg, temp_reg])

    chunks.append(test_data.end_test_chunk())
    for chunk in chunks:  # each section is its own file and enables MIE/SIE at its start
        chunk.code.extend(_global_ie(mode, False))
    return chunks


def _generate_zaamo_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate AMO matching tests."""
    covergroup = f"Sdtrig{mode}_a_cg"
    seed(reproducible_hash(covergroup))
    chunks: list[TestChunk] = []

    # setup registers
    dest_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        4, exclude_regs=[2], reg_range=list(range(8, 16))
    )

    dataval = random_int(32, signed=False, nonzero=True) << 32 | random_int(32, signed=False, nonzero=True)
    perms = (0b100, 0b010, 0b001)  # exec / store / load

    ######################################
    coverpoint = "cp_amo"
    ######################################
    randval = random_int(32, signed=False, nonzero=True)
    for op in ZAAMO_OPS:  # one file per op keeps the S/U files under 100k dynamic instructions
        lines = test_data.new_test_chunk(chunks, f"amo_{op}").code
        lines.extend(_global_ie(mode, True))
        lines.append(
            comment_banner(
                coverpoint,
                f"mcontrol6 fires when {op} address == tdata2 (select=address)",
            )
        )
        for trig_num in TRIGGERS:
            gates = _mcontrol6_gates(trig_num, mode)
            lines.extend([*gates, *_select_trigger(temp_reg, trig_num, mode)])
            for tdata2 in ("scratch", 0):
                for perm in perms:  # perm_xsl
                    lines.extend(_xsl_ifdefs(perm))
                    for width in ("w", "d"):
                        insn = f"{op}.{width}"
                        lines.extend(_ifdef_guard(insn))
                        binname = f"trig_num_{trig_num}_td2_{tdata2}_{op}_{width}_perm_{perm:03b}"
                        lines.extend(
                            [
                                _add_tc(test_data, binname, coverpoint, covergroup),
                                f"LA(x{addr_reg}, scratch) # x{addr_reg} = &scratch",
                                _load_reg(data_reg, dataval),
                                f"LI(x{dest_reg}, 0x{randval:x}) # data for sigupd",
                                *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=perm, select=0),
                                *_arch_guard(
                                    f"{insn} x{dest_reg}, x{data_reg}, (x{addr_reg}) # fire iff addr==tdata2 and xsl has load or store bit",
                                    ["zaamo"],
                                ),
                                "nop # spacer",
                                *_disable_trigger(mode),
                                write_sigupd(dest_reg, test_data),
                            ]
                        )
                        lines.extend(_ifdef_guard(insn, closing=True))
                    lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(perm)))
            lines.extend(_close_gates(gates))

    test_data.int_regs.return_registers([dest_reg, addr_reg, data_reg, temp_reg])

    chunks.append(test_data.end_test_chunk())
    for chunk in chunks:  # each section is its own file and enables MIE/SIE at its start
        chunk.code.extend(_global_ie(mode, False))
    return chunks


def _generate_vector_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate vector load/store matching tests."""
    covergroup = f"Sdtrig{mode}_combined_accesses_cg"
    chunks: list[TestChunk] = []

    addr_reg, temp_reg = test_data.int_regs.get_registers(2, exclude_regs=[2], reg_range=list(range(8, 16)))
    vreg = 8
    vsews = (8, 16, 32, 64)
    vops = {"load": ("vle", 0b001), "store": ("vse", 0b010)}

    def chunk_prologue(coverpoint: str, description: str) -> list[str]:
        lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
        lines.extend(_global_ie(mode, True))
        lines.append(comment_banner(coverpoint, description))
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                *_arch_guard("vsetivli x0, 16, e8, m1, ta, ma", ["v"]),
                *_arch_guard(f"vle8.v v{vreg}, (x{addr_reg}) # preload vector register before arming triggers", ["v"]),
            ]
        )
        return lines

    def vector_access(vinstr: str, sew: int, avl: int, comment: str, masked: bool = False) -> list[str]:
        policy = "mu" if masked else "ma"
        vm = ", v0.t" if masked else ""
        return [
            f"LA(x{addr_reg}, scratch) # vector access base address",
            *_arch_guard(f"vsetivli x0, {avl}, e{sew}, m4, ta, {policy}", ["v"]),  # m4: scratch+8 in vl at VLEN=32
            *_arch_guard(f"{vinstr}{sew}.v v{vreg}, (x{addr_reg}){vm} # {comment}", ["v"]),
            "nop # spacer",
        ]

    ######################################
    coverpoint = "cp_vector_load_store"
    ######################################
    lines = chunk_prologue(
        coverpoint, "mcontrol6 matches a vector load/store as if it performed a load/store of size SEW"
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for vperm, (vinstr, xsl) in vops.items():
            lines.extend(_xsl_ifdefs(xsl))
            for tdata2 in ("scratch", 0):
                for size in range(7):
                    if size > 0:
                        lines.extend(_size_open(size))
                    lines.extend(_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=xsl, select=0, size=size))
                    for sew in vsews:
                        lines.extend(["#ifdef ZVE64X_SUPPORTED"] if sew == 64 else [])
                        binname = f"trig_num_{trig_num}_td2_{tdata2}_size_{size}_sew{sew}_{vperm}"
                        lines.append(_add_tc(test_data, binname, coverpoint, covergroup))
                        lines.extend(vector_access(vinstr, sew, 1, "fire iff addr==tdata2 and size in (0, SEW)"))
                        lines.extend(["#endif // ZVE64X_SUPPORTED"] if sew == 64 else [])
                    lines.extend(_disable_trigger(mode))
                    if size > 0:
                        lines.extend(_size_close(size))
            lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(xsl)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_vector_accesses"
    ######################################
    lines = chunk_prologue(
        coverpoint,
        "mcontrol6 matches each element of a vector load/store as if it were an individual access\n"
        "(scratch+8 only fires when vl covers it)",
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for vperm, (vinstr, xsl) in vops.items():
            lines.extend(_xsl_ifdefs(xsl))
            for tdata2_name, tdata2 in (("scratch", "scratch"), ("scratch8", "scratch+8"), ("0", 0)):
                lines.extend(_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=xsl, select=0))
                for avl in (1, 9):
                    for sew in vsews:
                        lines.extend(["#ifdef ZVE64X_SUPPORTED"] if sew == 64 else [])
                        binname = f"trig_num_{trig_num}_td2_{tdata2_name}_vl_{avl}_sew{sew}_{vperm}"
                        lines.append(_add_tc(test_data, binname, coverpoint, covergroup))
                        lines.extend(vector_access(vinstr, sew, avl, "fire iff an accessed element addr==tdata2"))
                        lines.extend(["#endif // ZVE64X_SUPPORTED"] if sew == 64 else [])
                lines.extend(_disable_trigger(mode))
            lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(xsl)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_vector_mask"
    ######################################
    lines = chunk_prologue(
        coverpoint,
        "mcontrol6 does not match a masked-off vector element\n"
        "(tdata2 = scratch+8; v0 makes the element at scratch+8 active or masked off)",
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for vperm, (vinstr, xsl) in vops.items():
            lines.extend(_xsl_ifdefs(xsl))
            lines.extend(_config_mcontrol6(temp_reg, trig_num, "scratch+8", mode, xsl=xsl, select=0))
            for state in ("active", "masked"):
                for sew in vsews:
                    elem = 8 // (sew // 8)  # index of the element at scratch+8
                    mask = 0xFFFF if state == "active" else 0xFFFF & ~(1 << elem)
                    binname = f"trig_num_{trig_num}_td2_scratch8_{state}_sew{sew}_{vperm}"
                    lines.extend(["#ifdef ZVE64X_SUPPORTED"] if sew == 64 else [])
                    lines.extend(
                        [
                            _add_tc(test_data, binname, coverpoint, covergroup),
                            f"LI(x{temp_reg}, 0x{mask:x}) # element {elem} {state}",
                            *_arch_guard("vsetivli x0, 1, e16, m1, ta, ma", ["v"]),
                            *_arch_guard(f"vmv.s.x v0, x{temp_reg}", ["v"]),
                            *vector_access(vinstr, sew, 9, "fire iff the element at tdata2 is active", masked=True),
                        ]
                    )
                    lines.extend(["#endif // ZVE64X_SUPPORTED"] if sew == 64 else [])
            lines.extend(_disable_trigger(mode))
            lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(xsl)))
        lines.extend(_close_gates(gates))

    test_data.int_regs.return_registers([addr_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    for chunk in chunks:  # each coverpoint is its own file and enables MIE/SIE at its start
        chunk.code.extend(_global_ie(mode, False))
    return chunks


def _generate_zcmp_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate cm.push/cm.pop matching tests."""
    covergroup = f"Sdtrig{mode}_combined_accesses_cg"
    chunks: list[TestChunk] = []

    ######################################
    coverpoint = "cp_cm_pop_push"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 matches each XLEN store of cm.push / cm.pop",
        )
    )
    for trig_num in TRIGGERS:
        for addrval in ("marker", "marker8", "zero"):
            for insn in ("cm_push", "cm_pop"):
                for size in SIZE_ALL:
                    for perm in ("store", "load"):
                        binname = f"trig_num_{trig_num}_addr_{addrval}_{insn}_size_{size}_{perm}"
                        lines.extend(
                            [
                                _add_tc(test_data, binname, coverpoint, covergroup),
                            ]
                        )

    chunks.append(test_data.end_test_chunk())
    return chunks


def _generate_zicbom_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate cbo.clean/flush/inval matching tests."""
    covergroup = f"Sdtrig{mode}_cache_operations_cg"
    addr_reg, temp_reg = test_data.int_regs.get_registers(2, exclude_regs=[2], reg_range=list(range(8, 16)))

    ######################################
    coverpoint = "cp_cache_zicbom"
    ######################################
    lines = test_data.begin_test_chunk("cache_zicbom").code
    lines.extend(
        [
            *_global_ie(mode, True),
            comment_banner(coverpoint, "cbo.clean/flush/inval match as stores"),
            f"LA(x{addr_reg}, scratch) # cache block address",
        ]
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for td2_name, tdata2 in CBO_TDATA2:
            for select in (0, 1):
                if select:
                    lines.append("#ifdef UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
                for size in range(7):
                    if size:
                        lines.extend(_size_open(size))
                    for perm in (0b100, 0b010, 0b001):  # exec / store / load
                        lines.extend(_xsl_ifdefs(perm))
                        lines.extend(
                            _config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=perm, select=select, size=size)
                        )
                        for insn in ("clean", "flush", "inval"):
                            binname = f"trig_num_{trig_num}_td2_{td2_name}_select_{select}_size_{size}_perm_{perm:03b}_cbo_{insn}"
                            lines.extend(
                                [
                                    _add_tc(test_data, binname, coverpoint, covergroup),
                                    *_arch_guard(
                                        f"cbo.{insn} (x{addr_reg}) # fire iff addr==tdata2, store, size=0, select=0",
                                        ["zicbom"],
                                    ),
                                    "nop # spacer",
                                ]
                            )
                        lines.extend(_disable_trigger(mode))
                        lines.append("#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE")
                    if size:
                        lines.extend(_size_close(size))
                if select:
                    lines.append("#endif // UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
        lines.extend(_close_gates(gates))

    lines.extend(_global_ie(mode, False))
    test_data.int_regs.return_registers([addr_reg, temp_reg])
    return [test_data.end_test_chunk()]


def _generate_zicboz_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate cbo.zero matching tests."""
    covergroup = f"Sdtrig{mode}_cache_operations_cg"
    addr_reg, temp_reg = test_data.int_regs.get_registers(2, exclude_regs=[2], reg_range=list(range(8, 16)))

    ######################################
    coverpoint = "cp_cache_zicboz"
    ######################################
    lines = test_data.begin_test_chunk("cache_zicboz").code
    lines.extend(
        [
            *_global_ie(mode, True),
            comment_banner(coverpoint, "cbo.zero matches as a store"),
            f"LA(x{addr_reg}, scratch) # cache block address",
        ]
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for td2_name, tdata2 in CBO_TDATA2:
            for select in (0, 1):
                if select:
                    lines.append("#ifdef UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
                for size in range(7):
                    if size:
                        lines.extend(_size_open(size))
                    for perm in (0b100, 0b010, 0b001):  # exec / store / load
                        binname = (
                            f"trig_num_{trig_num}_td2_{td2_name}_select_{select}_size_{size}_perm_{perm:03b}_cbo_zero"
                        )
                        lines.extend(
                            [
                                *_xsl_ifdefs(perm),
                                *_config_mcontrol6(
                                    temp_reg, trig_num, tdata2, mode, xsl=perm, select=select, size=size
                                ),
                                _add_tc(test_data, binname, coverpoint, covergroup),
                                *_arch_guard(
                                    f"cbo.zero (x{addr_reg}) # fire iff addr==tdata2, store, size=0, select=0",
                                    ["zicboz"],
                                ),
                                "nop # spacer",
                                *_disable_trigger(mode),
                                "#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE",
                            ]
                        )
                    if size:
                        lines.extend(_size_close(size))
                if select:
                    lines.append("#endif // UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
        lines.extend(_close_gates(gates))

    lines.extend(_global_ie(mode, False))
    test_data.int_regs.return_registers([addr_reg, temp_reg])
    return [test_data.end_test_chunk()]


def _generate_zicbop_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate prefetch matching tests."""
    covergroup = f"Sdtrig{mode}_cache_operations_cg"
    addr_reg, temp_reg = test_data.int_regs.get_registers(2, exclude_regs=[2], reg_range=list(range(8, 16)))

    ######################################
    coverpoint = "cp_cache_zicbop"
    ######################################
    xsl_ifdefs = _xsl_ifdefs(0b011)
    lines = test_data.begin_test_chunk("cache_zicbop").code
    lines.extend(
        [
            *_global_ie(mode, True),
            comment_banner(coverpoint, "prefetch.i/r/w (HINTs) do not match as loads or stores"),
            f"LA(x{addr_reg}, scratch) # prefetch address",
        ]
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(xsl_ifdefs)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for td2_name, tdata2 in (("scratch", "scratch"), ("zero", 0)):
            for select in (0, 1):
                if select:
                    lines.append("#ifdef UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
                lines.extend(_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b011, select=select))
                for p in ("i", "r", "w"):
                    binname = f"trig_num_{trig_num}_td2_{td2_name}_select_{select}_prefetch_{p}"
                    lines.extend(
                        [
                            _add_tc(test_data, binname, coverpoint, covergroup),
                            *_arch_guard(f"prefetch.{p} 0(x{addr_reg}) # never matches as a load or store", ["zicbop"]),
                            "nop # spacer",
                        ]
                    )
                lines.extend(_disable_trigger(mode))
                if select:
                    lines.append("#endif // UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(xsl_ifdefs))
        lines.extend(_close_gates(gates))

    lines.extend(_global_ie(mode, False))
    test_data.int_regs.return_registers([addr_reg, temp_reg])
    return [test_data.end_test_chunk()]


# cp_tdata2_translate: (name, XLEN, VA width, satp setup, superpage PTE macro, root level, alias VA, superpage shift).
# The alias is the last root slot, so it is a negative (sign-extended) VA and never the boot identity map's slot.
_XLATE_MODES = (
    ("sv39", 64, 39, "SATP_SETUP_RV64(sv39)", "SUPERPAGE_PTE_SETUP_SV39", "LEVEL2", 0xFFFFFFFFC0000000, 30),
    ("sv48", 64, 48, "SATP_SETUP_RV64(sv48)", "SUPERPAGE_PTE_SETUP_SV48", "LEVEL3", 0xFFFFFF8000000000, 39),
    ("sv57", 64, 57, "SATP_SETUP_RV64(sv57)", "SUPERPAGE_PTE_SETUP_SV57", "LEVEL4", 0xFFFF000000000000, 48),
    ("sv32", 32, 32, "SATP_SETUP_SV32", "SUPERPAGE_PTE_SETUP_SV32", "LEVEL1", 0xFFC00000, 22),
)
_PTE_SPAGE = "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V"


def _xlate_guard(name: str, xlen: int) -> list[str]:
    return [f"#if __riscv_xlen == {xlen}", f"#ifdef {name.upper()}_SUPPORTED"]


def _generate_address_matches_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate tdata2 address-storage / translation tests."""
    covergroup = f"Sdtrig{mode}_address_matches_cg"
    chunks: list[TestChunk] = []
    cfg_reg, va_reg, pa_reg, temp_reg = test_data.int_regs.get_registers(
        4, exclude_regs=[2, 10, 11], reg_range=list(range(8, 16))
    )

    ######################################
    coverpoint = "cp_tdata2_translate"
    ######################################
    # An address trigger's tdata2 must read back every valid address exactly (norm:Sdtrig_tdata2_addr_sz1): the
    # largest VA with the sign bit clear and the smallest with it set for each supported mode, and the largest PA.
    # Each is written with satp in that mode (Bare for the PA). A trigger with no mode bits set never fires.
    # SdtrigS writes satp directly in S-mode, which the boot identity map keeps executing, and tdata2 through T-SBI.
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "tdata2 of an mcontrol6 address trigger reads back the extreme sign-extended VAs of each\n"
            "supported translation mode and the zero-extended maximum PA exactly",
        )
    )
    max_pa = [
        "#if UDB_PHYS_ADDR_WIDTH >= __riscv_xlen",
        *_xlen_li(temp_reg, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF),
        "#else",
        f"LI(x{temp_reg}, ((1 << UDB_PHYS_ADDR_WIDTH) - 1)) # largest PA, zero-extended",
        "#endif",
    ]
    blocks: list[tuple[str, list[str], list[str], list[tuple[str, list[str]]]]] = [
        ("bare", [], ["#ifdef S_SUPPORTED", "csrw satp, x0 # Bare", "#endif"], [("max_pa", max_pa)])
    ]
    for name, xlen, va_bits, satp_setup, _, _, _, _ in _XLATE_MODES:
        half = 1 << (va_bits - 1)
        values = [
            ("msb_0", [f"LI(x{temp_reg}, 0x{half - 1:x}) # largest VA with the sign bit clear"]),
            ("msb_1", [f"LI(x{temp_reg}, 0x{(1 << xlen) - half:x}) # smallest VA with the sign bit set"]),
        ]
        blocks.append((name, _xlate_guard(name, xlen), [satp_setup, "sfence.vma"], values))
    for satp, guards, satp_lines, values in blocks:
        lines.extend([f"\n# satp.MODE = {satp}", *guards, *satp_lines])
        for trig_num in TRIGGERS:
            lines.append(f"#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")
            lines.extend(_xsl_ifdefs(0b100))
            lines.extend(_select_trigger(cfg_reg, trig_num, mode))
            for value_name, value_lines in values:
                lines.extend(
                    [
                        _add_tc(test_data, f"trig_num_{trig_num}_satp_{satp}_{value_name}", coverpoint, covergroup),
                        *_config_mcontrol6(cfg_reg, trig_num, 0, mode, privbits=0, xsl=0b100),
                        *value_lines,
                        _csr_access(f"csrw tdata2, x{temp_reg} # address to hold", mode),
                        _csr_access(f"csrr x{cfg_reg}, tdata2 # must read back exactly", mode),
                        write_sigupd(cfg_reg, test_data),
                        *_disable_trigger(mode),
                    ]
                )
            lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b100)))
            lines.append(f"#endif // UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")
        if guards:
            lines.extend(["csrw satp, x0 # back to Bare", "sfence.vma", "#endif", "#endif"])

    ######################################
    coverpoint = "cp_tdata2_translate_exec"
    ######################################
    # S-mode runs sdtrig_xlate_target through an alias superpage in the last root slot (a negative VA). An S-mode
    # execute trigger on that VA fires; one on the target's PA, which is also its identity-mapped VA, does not.
    # SdtrigSm takes the breakpoint into M (medeleg[3]=0); SdtrigS runs in S-mode and takes it into S as it boots.
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "S-mode execute trigger on code run at a translated VA different from its PA: it fires when\n"
            "tdata2 is the VA and not when tdata2 is the PA",
        )
    )
    lines.extend(
        [
            "#ifdef S_SUPPORTED",
            "#ifdef UDB_SDTRIG_S_WRITABLE",
            "#ifdef UDB_SDTRIG_MCONTROL6_EXECUTE_WRITABLE",
            ".pushsection .data",
            ".p2align 2",
            "sdtrig_xlate_target:",
            "nop # the execute trigger watches this instruction",
            "jr ra",
            ".popsection",
            # the breakpoint is taken into M in SdtrigSm; into S in SdtrigS, where SIE=1 lets the trigger fire
            *(_set_medeleg(temp_reg, 3, False) if mode == "Sm" else _global_ie(mode, True)),
        ]
    )
    for name, xlen, _, satp_setup, pte_macro, level, alias, shift in _XLATE_MODES:
        slot = ((alias >> shift) & (0x1FF if xlen == 64 else 0x3FF)) << (3 if xlen == 64 else 2)
        lines.extend(
            [
                f"\n# {name}: sdtrig_xlate_target's superpage aliased at 0x{alias:x}",
                *_xlate_guard(name, xlen),
                f"{pte_macro}(sdtrig_xlate_target, ({_PTE_SPAGE}), 0x{alias:x}, {level})",
                satp_setup,
                "sfence.vma",
                f"LA(x{pa_reg}, sdtrig_xlate_target) # PA, and its identity-mapped VA",
                f"LI(x{temp_reg}, 0x{(1 << shift) - 1:x})",
                f"and x{va_reg}, x{pa_reg}, x{temp_reg} # offset in the superpage",
                f"LI(x{temp_reg}, 0x{alias:x})",
                f"or x{va_reg}, x{va_reg}, x{temp_reg} # alias VA",
            ]
        )
        for trig_num in TRIGGERS:
            lines.append(f"#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")
            lines.extend(_select_trigger(cfg_reg, trig_num, mode))
            for case, reg in (("va", va_reg), ("pa", pa_reg)):
                lines.extend(
                    [
                        _add_tc(test_data, f"trig_num_{trig_num}_satp_{name}_tdata2_{case}", coverpoint, covergroup),
                        *_config_mcontrol6(
                            cfg_reg, trig_num, [f"mv x{cfg_reg}, x{reg}"], mode, privbits=MODE_PRIVBIT["S"], xsl=0b100
                        ),
                        *(["RVTEST_TSBI_GOTO_SMODE"] if mode == "Sm" else []),
                        f"jalr ra, 0(x{va_reg}) # run sdtrig_xlate_target at its alias VA",
                        *(["RVTEST_TSBI_GOTO_MMODE"] if mode == "Sm" else []),
                        *_disable_trigger(mode),
                        *_sign_trap_count(temp_reg, test_data),
                    ]
                )
            lines.append(f"#endif // UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")
        lines.extend(
            [
                "csrw satp, x0 # back to Bare",
                "sfence.vma",
                f"LA(x{temp_reg}, rvtest_Sroot_pg_tbl)",
                f"LI(x{cfg_reg}, 0x{slot:x})",
                f"add x{temp_reg}, x{temp_reg}, x{cfg_reg}",
                f"SREG x0, 0(x{temp_reg}) # remove the alias",
                "sfence.vma",
                "#endif",
                "#endif",
            ]
        )
    if mode == "S":
        lines.extend(_global_ie(mode, False))
    lines.extend(
        [
            "#endif // UDB_SDTRIG_MCONTROL6_EXECUTE_WRITABLE",
            "#endif // UDB_SDTRIG_S_WRITABLE",
            "#endif // S_SUPPORTED",
        ]
    )

    test_data.int_regs.return_registers([cfg_reg, va_reg, pa_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _li_xlen(reg: int, rv64: int, rv32: int, comment: str) -> list[str]:
    """LI an XLEN-dependent constant."""
    return [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, 0x{rv64:x}) # {comment}",
        "#else",
        f"LI(x{reg}, 0x{rv32:x}) # {comment}",
        "#endif",
    ]


def _write_tselect(reg: int, trig_num: int, mode: str) -> list[str]:
    """Write tselect = trig_num."""
    return [
        f"LI(x{reg}, {trig_num})",
        _csr_access(f"csrw tselect, x{reg} # tselect = {trig_num}", mode),
    ]


def _clear_tdata(mode: str) -> list[str]:
    """Disable the selected trigger (tdata1 = 0 first, so any tdata2/3 value is then legal) and zero tdata2/3."""
    return [
        _csr_access("csrw tdata1, x0 # disable trigger", mode),
        *_if_implemented("tdata2", _csr_access("csrw tdata2, x0", mode)),
        *_if_implemented("tdata3", _csr_access("csrw tdata3, x0", mode)),
    ]


def _generate_csr_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate trigger-module register (tselect, tdata1-3, tinfo and the global trigger CSRs) tests.

    The signature records only what the Debug spec and the DUT's parameters pin down: an implemented tselect index
    reads back as written, tinfo has info != 1 and exactly the types 3-6 the trigger supports, tinfo.version is at
    least 1 on a trigger that supports mcontrol6 (norm:Sdtrig_mcontrol6_dependence), a nonexistent trigger that
    tselect keeps reads tinfo.info = 1 and tdata1 = 0, a write to one tdata register leaves the other two and the
    other trigger's tdata registers unchanged and a write to tinfo has no effect (before ^ after = 0), a disabled
    trigger takes tdata2 = tdata3 = 0, an mcontrol6 tdata1 keeps type and the writable mode bits while the others
    read 0, and dmode reads 0 after an M-mode write of 1. Values that are WARL choices are not recorded: Sail 0.16, Spike, Whisper and Imperas differ
    on tselect after an all-ones write, on the ignored bits of an all-ones tdata1 (type 15), and on whether tinfo
    has type 2.
    """
    covergroup = f"Sdtrig{mode}_trig_module_reg_cg"
    chunks: list[TestChunk] = []
    data_reg, temp_reg, ones_reg, old1_reg, old2_reg = test_data.int_regs.get_registers(
        5, exclude_regs=[10, 11]
    )  # exclude a0, a1 because they are used in SBI

    ######################################
    coverpoint = "cp_tselect_trigs"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "Select each trigger 0..UDB_SDTRIG_NUM_TRIGGERS-1: tselect reads back the index (triggers start at 0\n"
            "and are contiguous), tinfo.info != 1 (the trigger exists) and tinfo bits 3-6 are exactly the types\n"
            "UDB_SDTRIG_<TYPE>_SUPPORTED_TRIGGERS gives the trigger",
        )
    )
    for trig_num in TRIGGERS:
        lines.extend(
            [
                f"\n{_num_guard(trig_num)}",
                _add_tc(test_data, f"trig_num_{trig_num}", coverpoint, covergroup),
                *_write_tselect(temp_reg, trig_num, mode),
                _csr_access(f"csrr x{data_reg}, tselect # an implemented index reads back as written", mode),
                write_sigupd(data_reg, test_data),
                _csr_access(f"csrr x{old1_reg}, tinfo", mode),
                f"LI(x{data_reg}, 0xffff)",
                f"and x{data_reg}, x{old1_reg}, x{data_reg} # tinfo.info",
                f"addi x{data_reg}, x{data_reg}, -1",
                f"seqz x{data_reg}, x{data_reg} # 1 if info == 1 (no trigger here)",
                write_sigupd(data_reg, test_data),
                f"LI(x{ones_reg}, 0) # tinfo bits of the types this trigger supports",
            ]
        )
        for trig_type in ACCESS_TYPES[:-1]:  # the types with a per-trigger parameter (not 15, disabled)
            guard = _type_guard(trig_type, trig_num)
            lines.extend([f"#ifdef {guard}", f"ori x{ones_reg}, x{ones_reg}, 0x{1 << trig_type:x}", "#endif"])
        lines.extend(
            [
                f"andi x{data_reg}, x{old1_reg}, 0x78 # tinfo bits 3-6 (icount, itrigger, etrigger, mcontrol6)",
                f"xor x{data_reg}, x{data_reg}, x{ones_reg} # 0 if they are exactly the supported types",
                write_sigupd(data_reg, test_data),
                # mcontrol6 as specified needs tinfo.version >= 1 (norm:Sdtrig_mcontrol6_dependence)
                f"#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}",
                f"srli x{data_reg}, x{old1_reg}, 24",
                f"andi x{data_reg}, x{data_reg}, 0xff",
                f"snez x{data_reg}, x{data_reg} # 1 if tinfo.version >= 1",
                write_sigupd(data_reg, test_data),
                "#endif",
                "#endif // UDB_SDTRIG_NUM_TRIGGERS",
            ]
        )

    ######################################
    coverpoint = "cp_tselect_nonexistent"
    ######################################
    # Same file as cp_tselect_trigs. tselect is WARL, so a write of the first unimplemented index may leave it
    # holding another index (Sail 0.16 legalizes it to the last trigger). Only when it keeps the index is there a
    # nonexistent trigger to check: tinfo.info = 1 (norm:Sdtrig_tinfo_no_trigger) and tdata1 = 0, that is type 0
    # with dmode and data hard-wired to 0 (norm:Sdtrig_tdata1_dmode_type_0, norm:Sdtrig_tdata1_data), also after
    # writing dmode = 1. The signature word is 0 on every hart that meets these rules.
    lines.append(
        comment_banner(
            coverpoint,
            "Write tselect = UDB_SDTRIG_NUM_TRIGGERS, the first unimplemented index. If tselect keeps it, tinfo.info\n"
            "reads 1 and tdata1 reads 0 (type 0), also after a write of dmode = 1",
        )
    )
    lines.extend(
        [
            "#if __riscv_xlen == 64 || UDB_SDTRIG_NUM_TRIGGERS < 0x100000000",
            _add_tc(test_data, "first_unimplemented", coverpoint, covergroup),
            f"LI(x{temp_reg}, UDB_SDTRIG_NUM_TRIGGERS) # the first index past the last trigger",
            _csr_access(f"csrw tselect, x{temp_reg}", mode),
            _csr_access(f"csrr x{old1_reg}, tselect", mode),
            f"xor x{old1_reg}, x{old1_reg}, x{temp_reg} # 0 if tselect kept the nonexistent index",
            f"bnez x{old1_reg}, 1f # another index: nothing to check",
            *_li_xlen(data_reg, 1 << 59, 1 << 27, "tdata1.dmode = 1, type 0"),
            _csr_access(f"csrw tdata1, x{data_reg} # type 0: dmode stays hard-wired to 0", mode),
            "1:",
            _csr_access(f"csrr x{old2_reg}, tinfo", mode),
            f"LI(x{data_reg}, 0xffff)",
            f"and x{old2_reg}, x{old2_reg}, x{data_reg}",
            f"xori x{old2_reg}, x{old2_reg}, 1 # 0 if tinfo.info == 1",
            _csr_access(f"csrr x{data_reg}, tdata1", mode),
            f"or x{data_reg}, x{data_reg}, x{old2_reg} # 0 if info == 1 and tdata1 == 0",
            f"seqz x{old1_reg}, x{old1_reg} # 1 if the index was kept",
            f"neg x{old1_reg}, x{old1_reg} # all ones if kept, 0 if not",
            f"and x{data_reg}, x{data_reg}, x{old1_reg} # checked only when the index was kept",
            write_sigupd(data_reg, test_data),
            _csr_access("csrw tselect, x0 # back to a valid index", mode),
            "#endif",
        ]
    )

    ######################################
    coverpoint = "cp_csr_access_global"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "Write all 0s and all 1s to tselect and to each implemented global trigger CSR from M-mode.\n"
            "All 1s is past the trigger count of any hart. tselect is WARL and the Debug spec leaves what it\n"
            "then holds open (Sail 0.16 reads 3, Spike/Whisper/Imperas 0), so only the absence of a trap and\n"
            "the restore to index 0 are checked",
        )
    )
    lines.extend(
        [
            f"LI(x{ones_reg}, -1) # all 1s",
            _add_tc(test_data, "tselect", coverpoint, covergroup),
            _csr_access("csrw tselect, x0 # write all 0s", mode),
            _csr_access(f"csrr x{data_reg}, tselect", mode),
            write_sigupd(data_reg, test_data),
            _csr_access(f"csrw tselect, x{ones_reg} # write all 1s: past the trigger count", mode),
            _csr_access("csrw tselect, x0 # back to a valid index", mode),
            _csr_access(f"csrr x{data_reg}, tselect", mode),
            write_sigupd(data_reg, test_data),
        ]
    )
    for csr in ("tcontrol", "mcontext", "scontext", "hcontext"):
        lines.extend(
            [
                f"\n#ifdef UDB_{csr.upper()}_IMPLEMENTED",
                _add_tc(test_data, csr, coverpoint, covergroup),
                _csr_access_m(f"csrr x{old1_reg}, {csr} # save", mode),
                _csr_access_m(f"csrw {csr}, x0 # write all 0s", mode),
                _csr_access_m(f"csrw {csr}, x{ones_reg} # write all 1s (WARL: not checked)", mode),
                _csr_access_m(f"csrw {csr}, x{old1_reg} # restore", mode),
                f"#endif // UDB_{csr.upper()}_IMPLEMENTED",
            ]
        )

    ######################################
    coverpoint = "cp_csr_unimplemented"
    ######################################
    # Same file as cp_csr_access_global, so a hart with every optional trigger CSR gets no empty test. SdtrigSm only:
    # from S-mode the access would trap whether or not the CSR exists.
    if mode == "Sm":
        lines.append(
            comment_banner(
                coverpoint,
                "Read and write each optional trigger CSR that the hart does not implement (UDB_<CSR>_IMPLEMENTED\n"
                "undefined) from M-mode: illegal instruction",
            )
        )
        for csr in ("tdata2", "tdata3", "tcontrol", "mcontext", "scontext", "hcontext"):
            lines.extend(
                [
                    f"\n#ifndef UDB_{csr.upper()}_IMPLEMENTED",
                    _add_tc(test_data, f"{csr}_read", coverpoint, covergroup),
                    f"csrr x{data_reg}, {csr} # not implemented: illegal instruction",
                    _add_tc(test_data, f"{csr}_write", coverpoint, covergroup),
                    f"csrw {csr}, x0 # not implemented: illegal instruction",
                    f"#endif // UDB_{csr.upper()}_IMPLEMENTED",
                ]
            )

    ######################################
    coverpoint = "cp_csr_access_local"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "For each trigger, write all 0s and all 1s to tdata1, tinfo and each implemented tdata2/tdata3 from\n"
            "M-mode, with the trigger disabled first. A disabled trigger takes tdata2 = tdata3 = 0; tinfo ignores\n"
            "the writes; the all-1s results are WARL and not checked",
        )
    )
    lines.append(f"LI(x{ones_reg}, -1) # all 1s")
    for trig_num in TRIGGERS:
        lines.extend([f"\n{_num_guard(trig_num)}", *_write_tselect(temp_reg, trig_num, mode)])
        for csr in (*TDATA_CSRS, "tinfo"):
            optional = csr in ("tdata2", "tdata3")
            lines.extend(
                [
                    *([f"#ifdef UDB_{csr.upper()}_IMPLEMENTED"] if optional else []),
                    _add_tc(test_data, f"trig_num_{trig_num}_{csr}", coverpoint, covergroup),
                    *_clear_tdata(mode),
                    _csr_access(f"csrr x{old1_reg}, tinfo", mode),
                    _csr_access(f"csrw {csr}, x0 # write all 0s", mode),
                ]
            )
            if optional:
                lines.extend(
                    [
                        _csr_access(f"csrr x{data_reg}, {csr} # 0 is legal for every type", mode),
                        write_sigupd(data_reg, test_data),
                    ]
                )
            if csr == "tdata2":  # a disabled trigger takes any tdata2 its types support (norm:Sdtrig_tdata2_disabled)
                lines.extend(
                    [
                        f"#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}",
                        f"LA(x{temp_reg}, scratch) # an address, which mcontrol6 supports",
                        _csr_access(f"csrw tdata2, x{temp_reg} # trigger still disabled (tdata1 = 0)", mode),
                        _csr_access(f"csrr x{data_reg}, tdata2", mode),
                        f"xor x{data_reg}, x{data_reg}, x{temp_reg} # 0 if tdata2 holds the address",
                        write_sigupd(data_reg, test_data),
                        "#endif",
                    ]
                )
            lines.append(_csr_access(f"csrw {csr}, x{ones_reg} # write all 1s", mode))
            if csr == "tinfo":
                lines.extend(
                    [
                        _csr_access(f"csrr x{data_reg}, tinfo", mode),
                        f"xor x{data_reg}, x{data_reg}, x{old1_reg} # 0 if tinfo unchanged",
                        write_sigupd(data_reg, test_data),
                    ]
                )
            if optional:
                lines.append("#endif")
        lines.extend([*_clear_tdata(mode), "#endif // UDB_SDTRIG_NUM_TRIGGERS"])

    ######################################
    coverpoint = "cp_tdata_write"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "With the trigger disabled (tdata1.type = 15), write all 0s and then all 1s to one tdata\n"
            "register; the other implemented ones must not change (each before ^ after is recorded and must be 0).\n"
            "Then write each tdata register of trigger 1 the same way; trigger 0's tdata1/2/3 must not change",
        )
    )
    lines.append(f"LI(x{ones_reg}, -1) # all 1s")
    for trig_num in TRIGGERS:
        lines.extend([f"\n{_num_guard(trig_num)}", *_write_tselect(temp_reg, trig_num, mode)])
        for csr in TDATA_CSRS:
            others = list(zip([c for c in TDATA_CSRS if c != csr], (old1_reg, old2_reg)))
            body = [
                _add_tc(test_data, f"trig_num_{trig_num}_{csr}", coverpoint, covergroup),
                *_clear_tdata(mode),
                *_li_xlen(temp_reg, TDATA1_TYPE_DISABLED << 60, TDATA1_TYPE_DISABLED << 28, "tdata1.type = 15"),
                _csr_access(f"csrw tdata1, x{temp_reg} # disabled: tdata2/3 take any supported value", mode),
            ]
            for other, reg in others:
                body.extend(_if_implemented(other, _csr_access(f"csrr x{reg}, {other} # before", mode)))
            body.extend(
                [
                    _csr_access(f"csrw {csr}, x0 # write all 0s", mode),
                    _csr_access(f"csrw {csr}, x{ones_reg} # write all 1s", mode),
                ]
            )
            for other, reg in others:
                check = [
                    _csr_access(f"csrr x{data_reg}, {other} # after", mode),
                    f"xor x{data_reg}, x{data_reg}, x{reg} # 0 if {other} unchanged",
                    write_sigupd(data_reg, test_data),
                ]
                body.extend(
                    [f"#ifdef UDB_{other.upper()}_IMPLEMENTED", *check, "#endif"] if other != "tdata1" else check
                )
            if csr == "tdata1":
                lines.extend(body)
            else:
                lines.extend([f"#ifdef UDB_{csr.upper()}_IMPLEMENTED", *body, "#endif"])
        lines.extend([*_clear_tdata(mode), "#endif // UDB_SDTRIG_NUM_TRIGGERS"])
    # Nor does it change any trigger besides the selected one: trigger 0 is disabled with tdata2 set (to scratch,
    # an address mcontrol6 supports), then each implemented tdata register of trigger 1 is written all 0s and all 1s
    (old3_reg,) = test_data.int_regs.get_registers(1, exclude_regs=[10, 11])
    lines.extend(
        [
            f"\n{_num_guard(1)}",
            *_write_tselect(temp_reg, 0, mode),
            *_clear_tdata(mode),
            *_li_xlen(temp_reg, TDATA1_TYPE_DISABLED << 60, TDATA1_TYPE_DISABLED << 28, "tdata1.type = 15"),
            _csr_access(f"csrw tdata1, x{temp_reg} # trigger 0 disabled", mode),
            "#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_0",
            f"LA(x{temp_reg}, scratch)",
            *_if_implemented("tdata2", _csr_access(f"csrw tdata2, x{temp_reg} # trigger 0 tdata2 = scratch", mode)),
            "#endif",
        ]
    )
    before_regs = tuple(zip(TDATA_CSRS, (old1_reg, old2_reg, old3_reg), strict=True))
    for csr in TDATA_CSRS:
        body = [
            _add_tc(test_data, f"trig_num_1_{csr}_trig_num_0", coverpoint, covergroup),
            *_write_tselect(temp_reg, 0, mode),
        ]
        for other, before_reg in before_regs:
            body.extend(_if_implemented(other, _csr_access(f"csrr x{before_reg}, {other} # trigger 0 before", mode)))
        body.extend(
            [
                *_write_tselect(temp_reg, 1, mode),
                *_clear_tdata(mode),
                *_li_xlen(temp_reg, TDATA1_TYPE_DISABLED << 60, TDATA1_TYPE_DISABLED << 28, "tdata1.type = 15"),
                _csr_access(f"csrw tdata1, x{temp_reg} # trigger 1 disabled", mode),
                _csr_access(f"csrw {csr}, x0 # trigger 1: write all 0s", mode),
                _csr_access(f"csrw {csr}, x{ones_reg} # trigger 1: write all 1s", mode),
                *_write_tselect(temp_reg, 0, mode),
            ]
        )
        for other, before_reg in before_regs:
            check = [
                _csr_access(f"csrr x{data_reg}, {other} # trigger 0 after", mode),
                f"xor x{data_reg}, x{data_reg}, x{before_reg} # 0 if trigger 0's {other} unchanged",
                write_sigupd(data_reg, test_data),
            ]
            body.extend([f"#ifdef UDB_{other.upper()}_IMPLEMENTED", *check, "#endif"] if other != "tdata1" else check)
        lines.extend(body if csr == "tdata1" else [f"#ifdef UDB_{csr.upper()}_IMPLEMENTED", *body, "#endif"])
    lines.extend(
        [
            *_clear_tdata(mode),
            *_write_tselect(temp_reg, 1, mode),
            *_clear_tdata(mode),
            "#endif // UDB_SDTRIG_NUM_TRIGGERS",
        ]
    )
    test_data.int_regs.return_registers([old3_reg])

    ######################################
    coverpoint = "cp_tdata1_mode_hardwired"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "Write an mcontrol6 tdata1 with m/s/u/vs/vu all set (no execute/store/load, so it never fires) and\n"
            "read it back. Recorded: type, each writable mode bit (UDB_SDTRIG_<MODE>_WRITABLE), which keeps the 1,\n"
            "and the bits of modes the hart lacks, which the Debug spec hard-wires to 0",
        )
    )
    # A bit of an implemented mode that is not writable is also read-only 0, but Sail cannot model it, so it is not
    # recorded: its value would differ from the reference.
    recorded = [
        ("M", "", MCONTROL6_M, "m"),
        ("S", "S_SUPPORTED", MCONTROL6_S, "s"),
        ("U", "U_SUPPORTED", MCONTROL6_U, "u"),
        ("VS", "H_SUPPORTED", MCONTROL6_VS, "vs"),
        ("VU", "H_SUPPORTED", MCONTROL6_VU, "vu"),
    ]
    lines.extend(_li_xlen(ones_reg, 0xF << 60, 0xF << 28, "type"))
    for letter, mode_define, bit, name in recorded:
        cond = f"defined(UDB_SDTRIG_{letter}_WRITABLE)" + (f" || !defined({mode_define})" if mode_define else "")
        lines.extend(
            [
                f"#if {cond}",
                f"LI(x{temp_reg}, 0x{bit:x})",
                f"or x{ones_reg}, x{ones_reg}, x{temp_reg} # {name}: writable, or hard-wired to 0",
                "#endif",
            ]
        )
    for trig_num in TRIGGERS:
        lines.extend(
            [
                f"\n#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}",
                _add_tc(test_data, f"trig_num_{trig_num}", coverpoint, covergroup),
                *_write_tselect(temp_reg, trig_num, mode),
                *_clear_tdata(mode),
                *_li_xlen(
                    data_reg,
                    (MCONTROL6_TYPE << 60) | MCONTROL6_ALL_PRIV,
                    (MCONTROL6_TYPE << 28) | MCONTROL6_ALL_PRIV,
                    "mcontrol6, m/s/u/vs/vu = 1",
                ),
                _csr_access(f"csrw tdata1, x{data_reg} # all mode bits set", mode),
                _csr_access(f"csrr x{data_reg}, tdata1", mode),
                f"and x{data_reg}, x{data_reg}, x{ones_reg} # recorded fields",
                write_sigupd(data_reg, test_data),
                _csr_access("csrw tdata1, x0 # disable trigger", mode),
                f"#endif // UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}",
            ]
        )

    ######################################
    coverpoint = "cp_tdata1_dmode"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "Write tdata1 with dmode = 1 and a type the trigger supports (mcontrol6 with no execute/store/load,\n"
            "icount with m = 0, so neither fires) from M-mode. dmode is writable only from Debug Mode, so it\n"
            "reads back 0; only dmode is recorded",
        )
    )
    dmode_types = (  # the mcontrol6 case writes m = 1, so it also needs the m bit
        (
            "mcontrol6",
            MCONTROL6_TYPE,
            MCONTROL6_M,
            ["UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}", "UDB_SDTRIG_M_WRITABLE"],
        ),
        ("icount", TRIG_TYPE_ICOUNT, 1 << 10, ["UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}"]),  # count = 1
    )
    for trig_num in TRIGGERS:
        for type_name, trig_type, lowfields, guards in dmode_types:
            gates = [f"#ifdef {g.format(trig_num=trig_num)}" for g in guards]
            gates[0] = "\n" + gates[0]
            lines.extend(
                [
                    *gates,
                    _add_tc(test_data, f"trig_num_{trig_num}_{type_name}", coverpoint, covergroup),
                    *_write_tselect(temp_reg, trig_num, mode),
                    *_clear_tdata(mode),
                    *_li_xlen(
                        data_reg,
                        (trig_type << 60) | (1 << 59) | lowfields,
                        (trig_type << 28) | (1 << 27) | lowfields,
                        f"{type_name}, dmode = 1",
                    ),
                    _csr_access(f"csrw tdata1, x{data_reg} # dmode is not writable from M-mode", mode),
                    _csr_access(f"csrr x{data_reg}, tdata1", mode),
                    "#if __riscv_xlen == 64",
                    f"srli x{data_reg}, x{data_reg}, 59",
                    "#else",
                    f"srli x{data_reg}, x{data_reg}, 27",
                    "#endif",
                    f"andi x{data_reg}, x{data_reg}, 1 # dmode",
                    write_sigupd(data_reg, test_data),
                    _csr_access("csrw tdata1, x0 # disable trigger", mode),
                    *_close_gates(gates),
                ]
            )

    ######################################
    coverpoint = "cp_tinfo_read_only"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "Write all 0s and all 1s to tinfo; it is read-only, so before ^ after is recorded and must be 0",
        )
    )
    lines.append(f"LI(x{ones_reg}, -1) # all 1s")
    for trig_num in TRIGGERS:
        lines.extend(
            [
                f"\n{_num_guard(trig_num)}",
                _add_tc(test_data, f"trig_num_{trig_num}", coverpoint, covergroup),
                *_write_tselect(temp_reg, trig_num, mode),
                _csr_access(f"csrr x{old1_reg}, tinfo # before", mode),
                _csr_access("csrw tinfo, x0 # write all 0s", mode),
                _csr_access(f"csrw tinfo, x{ones_reg} # write all 1s", mode),
                _csr_access(f"csrr x{data_reg}, tinfo # after", mode),
                f"xor x{data_reg}, x{data_reg}, x{old1_reg} # 0 if tinfo unchanged",
                write_sigupd(data_reg, test_data),
                "#endif // UDB_SDTRIG_NUM_TRIGGERS",
            ]
        )
    lines.append(_csr_access("csrw tselect, x0 # restore tselect", mode))

    test_data.int_regs.return_registers([data_reg, temp_reg, ones_reg, old1_reg, old2_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


_TCONTROL_MTE = 0x8
_TCONTROL_MPTE = 0x80


def _generate_tcontrol_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate tcontrol tests (SdtrigSm; harts with TCONTROL_IMPLEMENTED).

    cp_tcontrol_enable (harts that use tcontrol for reentrancy) arms an M-mode mcontrol6 execute trigger and runs its
    instruction with tcontrol.mte = 0 and 1.
    cp_tcontrol_mtrap and cp_tcontrol_mret set mte and mpte, then take an illegal-instruction trap (and return with
    mret) or execute mret, and record tcontrol: a trap copies mte to mpte and clears mte, and mret copies mpte to mte.
    """
    covergroup = f"Sdtrig{mode}_tcontrol_cg"
    chunks: list[TestChunk] = []
    cfg_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        3, exclude_regs=[2, 10, 11], reg_range=list(range(8, 16))
    )

    ######################################
    coverpoint = "cp_tcontrol_enable"
    ######################################
    lines = test_data.new_test_chunk(chunks, "tcontrol").code
    lines.append(
        comment_banner(
            coverpoint,
            "tcontrol.mte gates M-mode triggers with action = 0: an execute trigger on add x0, x1, x2 fires\n"
            "only with mte = 1. rvtest_trap_count is signed after each case",
        )
    )
    # mte gates M-mode triggers on harts that use it for reentrancy; others may implement tcontrol without that
    lines.extend(["#ifdef UDB_SDTRIG_BREAKPOINT_REENTRANCY_USE_TCONTROL", *_global_ie(mode, True)])
    for trig_num in TRIGGERS:
        gates = [*_mcontrol6_gates(trig_num, mode), *_xsl_ifdefs(0b100)]
        lines.extend([*gates, *_select_trigger(cfg_reg, trig_num, mode)])
        for mte in (0, 1):
            label = f"tcontrol_enable_trig_num_{trig_num}_mte_{mte}"
            lines.extend(
                [
                    _add_tc(test_data, f"trig_num_{trig_num}_mte_{mte}", coverpoint, covergroup),
                    *_config_mcontrol6(cfg_reg, trig_num, label, mode, xsl=0b100, select=0),
                    f"{'csrsi' if mte else 'csrci'} tcontrol, 0x{_TCONTROL_MTE:x} # mte = {mte}",
                    "nop # mte is set before the matched instruction",
                    f"{label}:",
                    f"add x0, x1, x2 # PC == tdata2: fires iff mte = {mte} is 1",
                    "nop # spacer",
                    *_disable_trigger(mode),
                    *_sign_trap_count(data_reg, test_data),
                ]
            )
        lines.extend(_close_gates(gates))
    lines.extend([*_global_ie(mode, False), "#endif // UDB_SDTRIG_BREAKPOINT_REENTRANCY_USE_TCONTROL"])

    ######################################
    coverpoint = "cp_tcontrol_mtrap"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "A trap into M-mode sets mpte = mte and mte = 0; the handler's mret then sets mte = mpte, so tcontrol\n"
            "read after the trap holds the old mte in both fields",
        )
    )
    lines.append("#ifdef UDB_TCONTROL_IMPLEMENTED")
    for mte in (0, 1):
        for mpte in (0, 1):
            value = (_TCONTROL_MPTE if mpte else 0) | (_TCONTROL_MTE if mte else 0)
            lines.extend(
                [
                    _add_tc(test_data, f"mte_{mte}_mpte_{mpte}", coverpoint, covergroup),
                    f"LI(x{temp_reg}, 0x{value:x})",
                    f"csrw tcontrol, x{temp_reg} # mte = {mte}, mpte = {mpte}",
                    ".4byte 0xf1101073 # csrrw x0, mvendorid, x0: illegal instruction trap into M",
                    f"csrr x{data_reg}, tcontrol",
                    f"andi x{data_reg}, x{data_reg}, 0x{_TCONTROL_MPTE | _TCONTROL_MTE:x} # mpte, mte",
                    write_sigupd(data_reg, test_data),
                ]
            )
    lines.append("#endif // UDB_TCONTROL_IMPLEMENTED")

    ######################################
    coverpoint = "cp_tcontrol_mret"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "mret (to M-mode, MPP = M) sets mte = mpte and leaves mpte unchanged",
        )
    )
    lines.append("#ifdef UDB_TCONTROL_IMPLEMENTED")
    for mte in (0, 1):
        for mpte in (0, 1):
            value = (_TCONTROL_MPTE if mpte else 0) | (_TCONTROL_MTE if mte else 0)
            label = f"tcontrol_mret_mte_{mte}_mpte_{mpte}"
            lines.extend(
                [
                    _add_tc(test_data, f"mte_{mte}_mpte_{mpte}", coverpoint, covergroup),
                    f"LA(x{temp_reg}, {label})",
                    f"csrw mepc, x{temp_reg}",
                    f"LI(x{temp_reg}, {hex(_MSTATUS_MPP_MASK)})",
                    f"csrs mstatus, x{temp_reg} # MPP = M",
                    f"LI(x{temp_reg}, 0x{value:x})",
                    f"csrw tcontrol, x{temp_reg} # mte = {mte}, mpte = {mpte}",
                    "mret # mte = mpte",
                    f"{label}:",
                    f"csrr x{data_reg}, tcontrol",
                    f"andi x{data_reg}, x{data_reg}, 0x{_TCONTROL_MPTE | _TCONTROL_MTE:x} # mpte, mte",
                    write_sigupd(data_reg, test_data),
                ]
            )
    lines.extend(["csrwi tcontrol, 0 # mte = mpte = 0", "#endif // UDB_TCONTROL_IMPLEMENTED"])

    test_data.int_regs.return_registers([cfg_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _generate_mcontrol6_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate mcontrol6 address/data match trigger tests."""
    covergroup = f"Sdtrig{mode}_mcontrol6_cg"
    seed(reproducible_hash(covergroup))
    chunks: list[TestChunk] = []

    # setup registers
    sp_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        4, exclude_regs=[2], reg_range=list(range(8, 16))
    )

    ######################################
    coverpoint = "cp_mcontrol6_priv_mode"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires on a sw when the privilege bit corresponding to mode is enabled,\n"
            "and not when only the other modes' m/s/u bits are set",
        )
    )
    # m/s/u without the current mode's bit. A bit for a mode the hart lacks is hard-wired to 0, which leaves
    # the trigger enabled in no mode: no fire either way, so this case needs no guard.
    others = (MODE_PRIVBIT["Sm"] | MODE_PRIVBIT["S"] | MODE_PRIVBIT["U"]) & ~MODE_PRIVBIT[mode]
    # in SdtrigS/U these cases fill cp_mcontrol6_priv_bits_s/u
    label_cp = coverpoint if mode == "Sm" else f"cp_mcontrol6_priv_bits_{mode.lower()}"
    for trig_num in TRIGGERS:
        lines.append(f"\n#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")
        lines.extend(_xsl_ifdefs(0b010))
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for priv in (0, MODE_PRIVBIT[mode]):
            if priv != 0:
                lines.append(f"\n#ifdef {_mode_writable(mode)}")

            binname = f"trig_num_{trig_num}_priv_{priv:05b}"
            lines.extend(
                [
                    _add_tc(test_data, binname, label_cp, covergroup),
                    *_config_mcontrol6(temp_reg, trig_num, "scratch", mode, privbits=priv, xsl=0b010, select=0),
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{data_reg}, {random_int(32, signed=False)})",
                    f"sw x{data_reg}, 0(x{addr_reg}) # fire trigger if applicable",
                    "nop # spacer (an address match may fire after the store)",
                    *_disable_trigger(mode),
                ]
            )

            if priv != 0:
                lines.append(f"#endif // {_mode_writable(mode)}")
        # fixed data so that the random values of the later sections stay as they were
        lines.extend(
            [
                _add_tc(test_data, f"trig_num_{trig_num}_priv_{others:05b}", label_cp, covergroup),
                *_config_mcontrol6(temp_reg, trig_num, "scratch", mode, privbits=others, xsl=0b010, select=0),
                f"LA(x{addr_reg}, scratch)",
                f"LI(x{data_reg}, 0x5A5A5A5A)",
                f"sw x{data_reg}, 0(x{addr_reg}) # must not fire: the current mode's bit is clear",
                "nop # spacer",
                *_disable_trigger(mode),
            ]
        )
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b010)))
        lines.append(f"#endif // UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")

    ######################################
    coverpoint = "cp_mcontrol6_execute_adr"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when PC == tdata2",
        )
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for perm in range(8):  # perm_xsl
            lines.extend(_xsl_ifdefs(perm))
            label = f"exec_adr_trig_num_{trig_num}_xls_{perm:03b}"
            binname = f"trig_num_{trig_num}_exec_adr_perm_{perm:03b}"
            lines.extend(
                [
                    _add_tc(test_data, binname, coverpoint, covergroup),
                    *_config_mcontrol6(temp_reg, trig_num, label, mode, xsl=perm, select=0),
                    f"{label}:",
                    "add x0, x1, x2 # execute here; PC == tdata2",
                    *_disable_trigger(mode),
                ]
            )
            binname = f"trig_num_{trig_num}_exec_adr_nofire_perm_{perm:03b}"
            lines.extend(
                [
                    _add_tc(test_data, binname, coverpoint, covergroup),
                    *_config_mcontrol6(temp_reg, trig_num, 0, mode, xsl=perm, select=0),
                    "add x0, x1, x2 # execute here; PC == tdata2",
                    *_disable_trigger(mode),
                ]
            )
            lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(perm)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_load_store_adr"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when access address == tdata2 (select=address)",
        )
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for tdata2_name, tdata2 in (("scratch", "scratch"), ("scratch_plus_8", "scratch+8"), ("0", 0)):
            for perm in range(8):  # perm_xsl
                lines.extend(_xsl_ifdefs(perm))
                for offset in (0, 8):
                    binname = f"trig_num_{trig_num}_td2_{tdata2_name}_offset_{offset}_perm_{perm:03b}"
                    lines.extend(
                        [
                            _add_tc(test_data, binname, coverpoint, covergroup),
                            *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=perm, select=0),
                            f"LA(x{addr_reg}, scratch) # x{addr_reg} = &scratch",
                            f"LI(x{data_reg}, {random_int(32, signed=False)})",
                            f"sw x{data_reg}, {offset}(x{addr_reg}) # store: breakpoint iff addr==tdata2 and xsl has store bit",
                            "nop # spacer",
                            f"lw x{data_reg}, {offset}(x{addr_reg}) # fire iff addr==tdata2 and xsl has load bit",
                            "nop # spacer",
                            *_disable_trigger(mode),
                        ]
                    )
                lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(perm)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_execute_data"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when instruction encoding == tdata2 (select=data)\n"
            "size=0 with a 32-bit instruction on RV64: relies on the zero-extension in norm:Sdtrig_mcontrol6_select_data",
        )
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode, select=1)
        lines.extend(gates)
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for tdata2 in (ADDI_HINT, TDATA2_NOFIRE):
            for perm in range(8):  # perm_xsl
                lines.extend(_xsl_ifdefs(perm))
                binname = f"trig_num_{trig_num}_exec_data_td2_{tdata2}_perm_{perm:03b}"
                lines.extend(
                    [
                        _add_tc(test_data, binname, coverpoint, covergroup),
                        *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=perm, select=1),
                        "addi x0, x1, 0 # fire trigger when opcode==tdata2",
                        "nop # spacer (does not match tdata2)",
                        "nop # spacer (does not match tdata2)",
                        *_disable_trigger(mode),
                    ]
                )
                lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(perm)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_load_store_data"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 fires when load/store data == tdata2 (select=data)",
        )
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode, select=1)
        lines.extend(gates)
        match_val = _xlen_value(random_int(32, signed=False))
        # no-fire values differ in bit 0 (RV32) or only in the upper half (RV64), so the whole register is compared
        nofire_val = (match_val[0] ^ 1, match_val[1] ^ (1 << 32))
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for case, tdata2 in [("Fire", match_val), ("NoFire", nofire_val)]:
            for perm in range(8):  # perm_xsl
                lines.extend(_xsl_ifdefs(perm))
                binname = f"trig_num_{trig_num}_{case}_perm_{perm:03b}"
                lines.extend(
                    [
                        _add_tc(test_data, binname, coverpoint, covergroup),
                        *_config_mcontrol6(temp_reg, trig_num, _xlen_li(temp_reg, *tdata2), mode, xsl=perm, select=1),
                        f"LA(x{addr_reg}, scratch) # x{addr_reg} = &scratch",
                        *_xlen_li(data_reg, *match_val),
                        f"SREG x{data_reg}, 0(x{addr_reg}) # XLEN-wide store: breakpoint iff data==tdata2 and xsl has store bit",
                        "nop # spacer (data match fires after)",
                        f"LREG x{data_reg}, 0(x{addr_reg}) # XLEN-wide load: fire iff data==tdata2 and xsl has load bit",
                        "nop # spacer (data match fires after)",
                        *_disable_trigger(mode),
                    ]
                )
                lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(perm)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_execute_size"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 execute match across access sizes\n"
            "size=0 with c.nop, or addi on RV64: relies on the zero-extension in norm:Sdtrig_mcontrol6_select_data",
        )
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode, select=1)
        lines.extend(gates)
        lines.extend(_xsl_ifdefs(0b111))
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for tdata2 in (ADDI_HINT, C_NOP):  # tdata2 sizes: 32-bit and 16-bit targets
            for size in range(7):
                lines.append(f"\n# Size = {size}")
                if size > 0:
                    lines.extend(_size_open(size))
                bin1 = f"trig_num_{trig_num}_td2_{tdata2}_insn_addi_size_{size}"
                bin2 = f"trig_num_{trig_num}_td2_{tdata2}_insn_c.nop_size_{size}"
                lines.extend(
                    [
                        _add_tc(test_data, bin1, coverpoint, covergroup),
                        *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b111, select=1, size=size),
                        "addi x0, x1, 0 # 32-bit target; fires iff tdata2 matches",
                        # "nop # spacer (does not match tdata2)",
                        *_disable_trigger(mode),
                    ]
                )
                lines.extend(
                    [
                        "#ifdef ZCA_SUPPORTED",
                        _add_tc(test_data, bin2, coverpoint, covergroup),
                        *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b111, select=1, size=size),
                        *_arch_guard("c.nop", ["zca"]),
                        "nop # spacer (does not match tdata2)",
                        *_disable_trigger(mode),
                        "#endif",
                    ]
                )
                if size > 0:
                    lines.extend(_size_close(size))
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b111)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_execute_adr_size"
    ######################################
    # A select = 0 execute trigger with size = N matches only the execution of N-bit instructions. Sail 0.16 fires one
    # with size = 2 or 3 on an instruction of either width (sail-riscv#2033), so only the cases where it agrees with
    # the Debug spec are generated: size 2 on c.nop and size 3 on addi fire, and sizes 1, 4 and 5 fire on neither.
    # Add size 2 on addi and size 3 on c.nop once Sail honors size (ACT #2921). A c.nop target sits at an address
    # that is 2 mod 4 and an addi target at 0 mod 4, which the coverage uses to tell them apart when a breakpoint
    # replaces the target.
    lines = test_data.new_test_chunk(chunks, "mcontrol6_execute_adr_size").code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 execute address (select=0) match with size = N: fires only on an N-bit instruction at tdata2\n"
            "(size 2 on c.nop and size 3 on addi fire; sizes 1, 4 and 5 fire on neither)",
        )
    )
    exec_adr_size_cases = ((1, "addi"), (1, "c.nop"), (2, "c.nop"), (3, "addi"), (4, "addi"), (4, "c.nop"))
    exec_adr_size_cases += ((5, "addi"), (5, "c.nop"))
    for trig_num in TRIGGERS:
        gates = [*_mcontrol6_gates(trig_num, mode), *_xsl_ifdefs(0b100)]
        lines.extend([*gates, *_select_trigger(temp_reg, trig_num, mode)])
        for size, insn in exec_adr_size_cases:
            label = f"exec_adr_size_trig_num_{trig_num}_size_{size}_{insn.replace('.', '_')}"
            compressed = insn == "c.nop"
            lines.extend(_size_open(size))
            if compressed:
                lines.append("#ifdef ZCA_SUPPORTED")
            lines.extend(
                [
                    _add_tc(test_data, f"trig_num_{trig_num}_size_{size}_insn_{insn}", coverpoint, covergroup),
                    *_config_mcontrol6(temp_reg, trig_num, label, mode, xsl=0b100, select=0, size=size),
                    ".p2align 2",
                ]
            )
            if compressed:
                lines.extend(
                    [
                        *_arch_guard("c.nop # filler: the target is at an address that is 2 mod 4", ["zca"]),
                        f"{label}:",
                        *_arch_guard(f"c.nop # PC == tdata2: fires iff size = {size} is 2 (16 bits)", ["zca"]),
                    ]
                )
            else:
                lines.extend([f"{label}:", f"addi x0, x1, 0 # PC == tdata2: fires iff size = {size} is 3 (32 bits)"])
            lines.extend(["nop # spacer", *_disable_trigger(mode)])
            if compressed:
                lines.append("#endif // ZCA_SUPPORTED")
            lines.extend(_size_close(size))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_load_store_size"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 load/store match across access sizes",
        )
    )

    lines.extend(
        [
            f"LI(x{temp_reg}, 0x6000)",
            _csr_access(
                f"csrs mstatus, x{temp_reg} # enable mstatus.FS (bits 14:13) so the fp loads/stores below don't trap as illegal instructions",
                mode,
            ),
        ]
    )

    instr_asm = {
        "sb": [f"sb x{data_reg}, 0(x{addr_reg})", []],
        "sh": [f"sh x{data_reg}, 0(x{addr_reg})", []],
        "sw": [f"sw x{data_reg}, 0(x{addr_reg})", []],
        "lb": [f"lb x{data_reg}, 0(x{addr_reg})", []],
        "lbu": [f"lbu x{data_reg}, 0(x{addr_reg})", []],
        "lh": [f"lh x{data_reg}, 0(x{addr_reg})", []],
        "lhu": [f"lhu x{data_reg}, 0(x{addr_reg})", []],
        "lw": [f"lw x{data_reg}, 0(x{addr_reg})", []],
        "sd": [f"sd x{data_reg}, 0(x{addr_reg})", []],
        "lwu": [f"lwu x{data_reg}, 0(x{addr_reg})", []],
        "ld": [f"ld x{data_reg}, 0(x{addr_reg})", []],
        "fsw": [f"fsw f{data_reg}, 0(x{addr_reg})", ["f"]],
        "flw": [f"flw f{data_reg}, 0(x{addr_reg})", ["f"]],
        "fsd": [f"fsd f{data_reg}, 0(x{addr_reg})", ["d"]],
        "fld": [f"fld f{data_reg}, 0(x{addr_reg})", ["d"]],
        "fsh": [f"fsh f{data_reg}, 0(x{addr_reg})", ["zfh"]],
        "flh": [f"flh f{data_reg}, 0(x{addr_reg})", ["zfh"]],
        "fsq": [f"fsq f{data_reg}, 0(x{addr_reg})", ["q"]],
        "flq": [f"flq f{data_reg}, 0(x{addr_reg})", ["q"]],
        "c.sw": [f"c.sw x{data_reg}, 0(x{addr_reg})", ["zca"]],
        "c.lw": [f"c.lw x{data_reg}, 0(x{addr_reg})", ["zca"]],
        "c.swsp": [f"c.swsp x{data_reg}, 0(sp)", ["zca"]],
        "c.lwsp": [f"c.lwsp x{data_reg}, 0(sp)", ["zca"]],
        "c.sd": [f"c.sd x{data_reg}, 0(x{addr_reg})", ["zca"]],
        "c.ld": [f"c.ld x{data_reg}, 0(x{addr_reg})", ["zca"]],
        "c.sdsp": [f"c.sdsp x{data_reg}, 0(sp)", ["zca"]],
        "c.ldsp": [f"c.ldsp x{data_reg}, 0(sp)", ["zca"]],
        "c.sb": [f"c.sb x{data_reg}, 0(x{addr_reg})", ["zcb"]],
        "c.sh": [f"c.sh x{data_reg}, 0(x{addr_reg})", ["zcb"]],
        "c.lbu": [f"c.lbu x{data_reg}, 0(x{addr_reg})", ["zcb"]],
        "c.lh": [f"c.lh x{data_reg}, 0(x{addr_reg})", ["zcb"]],
        "c.lhu": [f"c.lhu x{data_reg}, 0(x{addr_reg})", ["zcb"]],
        "c.fsw": [f"c.fsw f{data_reg}, 0(x{addr_reg})", ["zcf"]],
        "c.flw": [f"c.flw f{data_reg}, 0(x{addr_reg})", ["zcf"]],
        "c.fswsp": [f"c.fswsp f{data_reg}, 0(sp)", ["zcf"]],
        "c.flwsp": [f"c.flwsp f{data_reg}, 0(sp)", ["zcf"]],
        "c.fsd": [f"c.fsd f{data_reg}, 0(x{addr_reg})", ["zcd"]],
        "c.fld": [f"c.fld f{data_reg}, 0(x{addr_reg})", ["zcd"]],
        "c.fsdsp": [f"c.fsdsp f{data_reg}, 0(sp)", ["zcd"]],
        "c.fldsp": [f"c.fldsp f{data_reg}, 0(sp)", ["zcd"]],
    }
    sp_setup_asm = [f"mv x{sp_reg}, sp", "LA(sp, scratch)"]
    sp_teardown_asm = [f"mv sp, x{sp_reg}"]

    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode)
        lines.extend(gates)
        lines.extend(_xsl_ifdefs(0b011))
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for tdata2 in ("scratch", 0):
            for size in (0, 1, 2, 3, 5):
                lines.append(f"\n# Size = {size}")
                if size > 0:
                    lines.extend(_size_open(size))
                lines.extend(
                    [
                        *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b011, select=0, size=size),
                        f"LA(x{addr_reg}, scratch) # load/store address",
                        f"LI(x{data_reg}, {random_int(32, signed=False)}) # random load/store value",
                        "#ifdef F_SUPPORTED",
                        *_arch_guard(f"fmv.w.x f{data_reg}, x{data_reg}", ["f"]),
                        "#endif",
                    ]
                )
                for instr in instr_asm:
                    binname = f"trig_num_{trig_num}_td2_{tdata2}_size_{size}_instr_{instr}"
                    lines.extend(
                        [
                            _add_tc(test_data, binname, coverpoint, covergroup),
                            *_ifdef_guard(instr),
                            *(sp_setup_asm if instr.endswith("sp") else []),
                            *_arch_guard(instr_asm[instr][0], instr_asm[instr][1]),
                            "nop # spacer",
                            *(sp_teardown_asm if instr.endswith("sp") else []),
                            *_ifdef_guard(instr, closing=True),
                        ]
                    )
                lines.extend(_disable_trigger(mode))
                if size > 0:
                    lines.extend(_size_close(size))
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b011)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_match"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 match types equal / ge / lt / not-equal",
        )
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode, select=1)
        lines.extend(gates)
        lines.extend(_xsl_ifdefs(0b010))
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for match in (0, 2, 3, 8):
            lines.append(f"\n# Match = {match}")
            if match > 0:
                lines.append(f"#ifdef {_match_legal(match)}")
            lines.append("#if __riscv_xlen == 32")
            for data in (0x00000000, 0x12345677, 0x12345678, 0x12345679, 0xFFFFFFFF):
                tdata2 = 0x12345678
                binname = f"RV32_trig_num_{trig_num}_match_{match}_tdata2_{tdata2:x}_data_{data:x}"
                lines.extend(
                    [
                        _add_tc(test_data, binname, coverpoint, covergroup),
                        *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b010, match=match, select=1),
                        f"LA(x{addr_reg}, scratch) # store address",
                        f"LI(x{data_reg}, {data}) # store data value",
                        f"sw x{data_reg}, 0(x{addr_reg})",
                        "nop # spacer (data match fires after)",
                        *_disable_trigger(mode),
                    ]
                )
            lines.append("#else // XLEN == 64")
            for data in (
                0x0000000000000000,
                0x123456789ABCDEEF,
                0x123456789ABCDEF0,
                0x123456789ABCDEF1,
                0xFFFFFFFFFFFFFFFF,
            ):
                tdata2 = 0x123456789ABCDEF0
                binname = f"RV64_trig_num_{trig_num}_match_{match}_tdata2_{tdata2:x}_data_{data:x}"
                lines.extend(
                    [
                        _add_tc(test_data, binname, coverpoint, covergroup),
                        *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b010, match=match, select=1),
                        f"LA(x{addr_reg}, scratch)",
                        f"LI(x{data_reg}, {data})",
                        f"sd x{data_reg}, 0(x{addr_reg})",
                        "nop # spacer (data match fires after)",
                        *_disable_trigger(mode),
                    ]
                )
            lines.append("#endif // __riscv_xlen")
            if match > 0:
                lines.append(f"#endif // {_match_legal(match)}")
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b010)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_match_napot"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 NAPOT and not-NAPOT match types",
        )
    )

    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode, select=1)
        lines.extend(gates)
        lines.extend(_xsl_ifdefs(0b010))
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for match in (1, 9):
            lines.append(f"\n# Match = {match}")
            lines.append(f"#ifdef {_match_legal(match)}")
            for xlen, store, store_values in (
                (32, "sw", (0x00000000, 0x12345678, 0xFFFFFFFF)),
                (64, "sd", (0x0000000000000000, 0x123456789ABCDEF0, 0xFFFFFFFFFFFFFFFF)),
            ):
                lines.append(f"#if __riscv_xlen == {xlen}")
                # tdata2 is all ones except bit zero_bit, a NAPOT range of 2^(zero_bit+1) bytes; every range from 2^1
                # to 2^maskmax6 is supported (norm:Sdtrig_mcontrol6_napot_range), and M > 0 needs zero_bit < XLEN-1
                for zero_bit in range(xlen - 1):
                    tdata2 = ((1 << xlen) - 1) & ~(1 << zero_bit)
                    lines.extend(
                        [
                            f"\n#if UDB_SDTRIG_MCONTROL6_MASKMAX6 > {zero_bit}",
                            *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b010, match=match, select=1),
                            f"LA(x{addr_reg}, scratch)",
                        ]
                    )
                    for data in store_values:
                        binname = f"RV{xlen}_trig_num_{trig_num}_match_{match}_zero_bit_{zero_bit}_data_{data:x}"
                        lines.extend(
                            [
                                _add_tc(test_data, binname, coverpoint, covergroup),
                                f"LI(x{data_reg}, 0x{data:x})",
                                f"{store} x{data_reg}, 0(x{addr_reg})",
                                "nop # spacer (data match fires after)",
                            ]
                        )
                    lines.extend([*_disable_trigger(mode), "#endif // UDB_SDTRIG_MCONTROL6_MASKMAX6"])
                lines.append("#endif // __riscv_xlen")
            lines.append(f"#endif // {_match_legal(match)}")
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b010)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_napot_allones"
    ######################################
    # SdtrigSm only: tdata2 legalization does not depend on the mode the trigger CSRs are written from. Its own file,
    # so a DUT that keeps the all-ones value can exclude just this group. The arm writes tdata1 = 0, tdata2 = 0, then
    # tdata1 with the match type, as the Debug spec's maskmax6 discovery sequence does; xsl = 000, so it never fires.
    if mode == "Sm":
        lines = test_data.new_test_chunk(chunks, "mcontrol6_napot_allones").code
        lines.append(
            comment_banner(
                coverpoint,
                "Write all ones to tdata2 of an mcontrol6 trigger with match = 1 (NAPOT) or 9 (not NAPOT) and read\n"
                "it back: bit maskmax6-1 reads 0 (norm:Sdtrig_mcontrol6_match_napot_mask). Bits maskmax6-2:0 are\n"
                "UNSPECIFIED and the bits above are WARL, so only bit maskmax6-1 is signed",
            )
        )
        lines.append("#if defined(UDB_TDATA2_IMPLEMENTED) && UDB_SDTRIG_MCONTROL6_MASKMAX6 < __riscv_xlen")
        for trig_num in TRIGGERS:
            lines.append(f"\n#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")
            lines.extend(_select_trigger(temp_reg, trig_num, mode))
            for match in (1, 9):
                lines.extend(
                    [
                        f"#ifdef {_match_legal(match)}",
                        _add_tc(test_data, f"trig_num_{trig_num}_match_{match}", coverpoint, covergroup),
                        *_config_mcontrol6(temp_reg, trig_num, 0, mode, privbits=0, xsl=0b000, match=match),
                        f"LI(x{data_reg}, -1)",
                        _csr_access(f"csrw tdata2, x{data_reg} # bits maskmax6-1:0 written with all ones", mode),
                        _csr_access(f"csrr x{data_reg}, tdata2", mode),
                        f"srli x{data_reg}, x{data_reg}, UDB_SDTRIG_MCONTROL6_MASKMAX6 - 1",
                        f"andi x{data_reg}, x{data_reg}, 1 # bit maskmax6-1, which must read 0",
                        write_sigupd(data_reg, test_data),
                        *_disable_trigger(mode),
                        f"#endif // {_match_legal(match)}",
                    ]
                )
            lines.append(f"#endif // UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}")
        lines.append("#endif // UDB_TDATA2_IMPLEMENTED && maskmax6 < XLEN")

    ######################################
    coverpoint = "cp_mcontrol6_match_mask"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "mcontrol6 mask-low / mask-high match types",
        )
    )
    # Mask cases for the current RV length, with the correct length store operation, and test case values.
    mask_cases = (
        (
            32,
            "sw",
            0xF0F0_A0B0,
            (0x0000_0000, 0xF0F0_A0B0, 0xFFFF_FFFF)
            + (0x0000_A0B0, 0x0000_A1B2, 0x0000_F0F0, 0x0001_A0B0)
            + (0xA0B0_0000, 0xA1B2_0000, 0xF0F0_0000, 0xA0B0_0001),
        ),
        (
            64,
            "sd",
            0xF0F0F0F0_A0B0C0D0,
            (0x00000000_00000000, 0xF0F0F0F0_A0B0C0D0, 0xFFFFFFFF_FFFFFFFF)
            + (0x00000000_A0B0C0D0, 0x00000000_A1B2C3D4, 0x00000000_F0F0F0F0, 0x00000001_A0B0C0D0)
            + (0xA0B0C0D0_00000000, 0xA1B2C3D4_00000000, 0xF0F0F0F0_00000000, 0xA0B0C0D0_00000001),
        ),
    )
    for trig_num in TRIGGERS:
        gates = _mcontrol6_gates(trig_num, mode, select=1)
        lines.extend(gates)
        lines.extend(_xsl_ifdefs(0b010))
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for match in (4, 5, 12, 13):  # 4: mask low, 5: mask high, 12: not mask low, 13: not mask high
            lines.append(f"\n# Match = {match}")
            lines.append(f"#ifdef {_match_legal(match)}")
            for xlen, store, tdata2, store_values in mask_cases:
                lines.extend(
                    [
                        f"#if __riscv_xlen == {xlen}",
                        *_config_mcontrol6(temp_reg, trig_num, tdata2, mode, xsl=0b010, match=match, select=1),
                        f"LA(x{addr_reg}, scratch)",
                    ]
                )
                for data in store_values:
                    binname = f"RV{xlen}_trig_num_{trig_num}_match_{match}_data_{data:x}"
                    lines.extend(
                        [
                            _add_tc(test_data, binname, coverpoint, covergroup),
                            f"LI(x{data_reg}, 0x{data:x})",
                            f"{store} x{data_reg}, 0(x{addr_reg})",
                            "nop # spacer (data match fires after)",
                        ]
                    )
                lines.extend([*_disable_trigger(mode), "#endif // __riscv_xlen"])
            lines.append(f"#endif // {_match_legal(match)}")
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b010)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_chain_adr"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "chained mcontrol6 triggers fire only when both match the same\n"
            "instruction (trigN chain=1 address, trigN+1 chain=0 data)",
        )
    )
    match_val = _xlen_value(random_int(32, signed=False))

    for trig_num in range(SDTRIG_MAX_TRIGGERS - 1):
        gates = [  # trigger trig_num + 1 is the select=1 one
            *_mcontrol6_gates(trig_num, mode, select=1),
            f"#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num + 1}",
            "#if UDB_SDTRIG_MAX_CHAIN_LENGTH >= 2",
        ]
        lines.extend(gates)
        lines.extend(_xsl_ifdefs(0b010))
        lines.extend(
            [
                *_select_trigger(temp_reg, trig_num + 1, mode),
                *_select_trigger(temp_reg, trig_num, mode),
                *_config_mcontrol6(temp_reg, trig_num, "scratch", mode, xsl=0b010, select=0, chain=1),
                *_write_tselect(temp_reg, trig_num + 1, mode),
                *_config_mcontrol6(
                    temp_reg, trig_num + 1, _xlen_li(temp_reg, *match_val), mode, xsl=0b010, select=1, chain=0
                ),
                f"LA(x{addr_reg}, scratch)",
            ]
        )
        # sweep data-match x addr-match; only both-match fires the chained pair
        for data_case, data in [("Fire", match_val), ("NoFire", (0, 0))]:
            for adr_case, offset in [("Fire", 0), ("NoFire", 8)]:
                binname = f"trig_nums_{trig_num}_{trig_num + 1}_data_{data_case}_adr_{adr_case}"
                lines.extend(
                    [
                        _add_tc(test_data, binname, coverpoint, covergroup),
                        *_xlen_li(data_reg, *data),
                        f"SREG x{data_reg}, {offset}(x{addr_reg}) # XLEN-wide store: fire when both triggers match",
                        "nop # spacer (data match fires after)",
                    ]
                )
        lines.extend([*_disable_trigger(mode), *_write_tselect(temp_reg, trig_num, mode), *_disable_trigger(mode)])
        lines.extend(["#endif // UDB_SDTRIG_MCONTROL6_XSL_WRITABLE"] * len(_xsl_ifdefs(0b010)))
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_chain_long"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "A chain of 3 to UDB_SDTRIG_MAX_CHAIN_LENGTH mcontrol6 store-address triggers starting at trigger 0\n"
            "(chain = 1 on all but the last) fires on a store to scratch only when every trigger in it matches:\n"
            "all watch scratch, or one watches scratch+8. rvtest_trap_count is signed after each case",
        )
    )
    lines.append(f"LA(x{addr_reg}, scratch)")
    for length in range(3, SDTRIG_MAX_TRIGGERS + 1):
        gates = [
            f"\n#if UDB_SDTRIG_MAX_CHAIN_LENGTH >= {length}",
            *[f"#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{t}" for t in range(length)],
            f"#ifdef {_mode_writable(mode)}",
            "#ifdef UDB_SDTRIG_MCONTROL6_STORE_WRITABLE",
        ]
        lines.extend(gates)
        for t in range(length):
            lines.extend(_select_trigger(temp_reg, t, mode))
        for case, miss in [("all_match", None), *[(f"trig_{t}_misses", t) for t in range(length)]]:
            lines.append(_add_tc(test_data, f"length_{length}_{case}", coverpoint, covergroup))
            for t in range(length):
                tdata2 = "scratch+8" if t == miss else "scratch"
                lines.extend(
                    [
                        *_write_tselect(temp_reg, t, mode),
                        *_config_mcontrol6(temp_reg, t, tdata2, mode, xsl=0b010, select=0, chain=int(t < length - 1)),
                    ]
                )
            lines.extend(
                [
                    f"SREG x0, 0(x{addr_reg}) # fires iff every trigger in the chain matches",
                    "nop # spacer (an address match may fire after the store)",
                    *[
                        line
                        for t in range(length)
                        for line in (*_write_tselect(temp_reg, t, mode), *_disable_trigger(mode))
                    ],
                    *_sign_trap_count(data_reg, test_data),
                ]
            )
        lines.extend(_close_gates(gates))

    ######################################
    coverpoint = "cp_mcontrol6_size_data"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "A select = data store trigger with size = N compares only the N bits the store writes\n"
            "(norm:Sdtrig_mcontrol6_comparisons): it fires on a store of that width whose low N bits equal\n"
            "tdata2 even when the register's other bits are set, and not when the low bits differ or the\n"
            "store has another width. rvtest_trap_count is signed after each case",
        )
    )
    # (size, store of that width, store of another width, N-bit value); tdata2 holds the value zero-extended,
    # because Sail 0.16 compares the zero-extended access data with all of tdata2
    size_cases = (
        (1, "sb", "sh", 0x5A),
        (2, "sh", "sw", 0xA55A),
        (3, "sw", "sb", 0x1234A55A),
        (5, "sd", "sw", 0x0123456789ABCDEF),
    )
    for trig_num in TRIGGERS:
        gates = [*_mcontrol6_gates(trig_num, mode, select=1), *_xsl_ifdefs(0b010)]
        lines.extend([*gates, *_select_trigger(temp_reg, trig_num, mode)])
        for size, store, other_store, value in size_cases:
            bits = _SIZE_BITS[size]
            lines.extend(_size_open(size))
            lines.extend(
                [
                    *_config_mcontrol6(temp_reg, trig_num, value, mode, xsl=0b010, select=1, size=size),
                    f"LA(x{addr_reg}, scratch)",
                ]
            )
            upper32 = ~((1 << bits) - 1) & 0xFFFFFFFF if bits < 32 else 0
            upper64 = ~((1 << bits) - 1) & 0xFFFFFFFFFFFFFFFF if bits < 64 else 0
            for case, insn, low in (
                ("match", store, value),
                ("low_differs", store, value ^ 1),
                ("other_width", other_store, value),
            ):
                lines.extend(
                    [
                        _add_tc(test_data, f"trig_num_{trig_num}_size_{size}_{case}", coverpoint, covergroup),
                        *_xlen_li(data_reg, (upper32 | low) & 0xFFFFFFFF, upper64 | low),
                        f"{insn} x{data_reg}, 0(x{addr_reg}) # fires iff {store} and the low {bits} bits equal tdata2",
                        "nop # spacer (data match fires after)",
                        *_sign_trap_count(data_reg, test_data),
                    ]
                )
            # The next wider store of the value with no other bits set writes tdata2 zero-extended, so only the size
            # keeps the trigger from firing (a hart that ignores size on data matches fires here)
            wider = {1: "sh", 2: "sw", 3: "sd"}.get(size)
            if wider:
                lines.extend(
                    [
                        *(["#if __riscv_xlen == 64"] if wider == "sd" else []),
                        _add_tc(test_data, f"trig_num_{trig_num}_size_{size}_wider_same_value", coverpoint, covergroup),
                        f"LI(x{data_reg}, 0x{value:x}) # no bits above the low {bits}",
                        f"{wider} x{data_reg}, 0(x{addr_reg}) # writes tdata2 zero-extended: must not fire (size = {bits} bits)",
                        "nop # spacer (data match fires after)",
                        *_sign_trap_count(data_reg, test_data),
                        *(["#endif"] if wider == "sd" else []),
                    ]
                )
            # The next narrower store, with tdata2 a value that fits in it: the size-N store of that value fires, and
            # the narrower store of it, which writes tdata2 zero-extended, must not
            narrower = {2: ("sb", 0x5A), 3: ("sh", 0xA55A), 5: ("sw", 0x1234A55A)}.get(size)
            lines.extend(_disable_trigger(mode))
            if narrower:
                narrow_store, small = narrower
                lines.extend(_config_mcontrol6(temp_reg, trig_num, small, mode, xsl=0b010, select=1, size=size))
                for case, insn in (("small_value", store), ("narrower_same_value", narrow_store)):
                    lines.extend(
                        [
                            _add_tc(test_data, f"trig_num_{trig_num}_size_{size}_{case}", coverpoint, covergroup),
                            f"LI(x{data_reg}, 0x{small:x}) # tdata2, no other bits set",
                            f"{insn} x{data_reg}, 0(x{addr_reg}) # writes tdata2 zero-extended: fires iff {store}",
                            "nop # spacer (data match fires after)",
                            *_sign_trap_count(data_reg, test_data),
                        ]
                    )
                lines.extend(_disable_trigger(mode))
            lines.extend(_size_close(size))
        lines.extend(_close_gates(gates))

    test_data.int_regs.return_registers([sp_reg, addr_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    for chunk in chunks:  # each section is its own file and enables MIE/SIE at its start
        chunk.code.extend(_global_ie(mode, False))
    return chunks


######################################
# cp_mcontrol6_match_size_{store,load,execute}: every legal match crossed with every legal size on select = 1
######################################
# A case is (label, value, width): the access of `width` bits whose compare value is `value` (the data stored or
# loaded, or the instruction encoding). A group is one tdata2 with the cases run against it: (tdata2, fire, nofire).
# Each group has cases that fire and narrow cases that don't, each chosen to fire if size or match were misread:
#   - a stored register or the loaded word has bits set above N (and tdata2 too, see _MS_TDATA2_ABOVE), so a hart
#     that compares more than the low N bits misses the cases that should fire (norm:Sdtrig_mcontrol6_comparisons);
#   - the data values have bit N-1 set and loads sign-extend, so an XLEN-wide or signed compare goes wrong;
#   - equal/not-equal miss by one bit (the lowest and the top compared bits), ge/lt miss by one step and by a
#     value that a signed compare would order the other way, NAPOT misses by the lowest compared bit and the top
#     bit, and the mask matches miss by one masked bit while an unmasked difference still fires;
#   - accesses of another width, with a tdata2 their own value would match, never fire (only accesses of size N
#     can), as they would on a hart that ignored size or matched the access's own width.
# The mask matches (4, 5, 12, 13) and NAPOT (1, 9) follow the XLEN-half reading of riscv-isa-manual#3461 that
# Sail 0.16, Whisper and ImperasDV implement; the other matches compare the low N bits of the value and tdata2.

_MS_MATCHES = (0, 1, 2, 3, 4, 5, 8, 9, 12, 13)
_MS_SIZE_CODE = {8: 1, 16: 2, 32: 3, 64: 5}
_MS_DATA = {8: 0xB6, 16: 0xB65A, 32: 0xB65A3C96, 64: 0xB65A3C960F1E2D4B}  # bit N-1 set
# TODO: set to 0xA5A5A5A5A5A5A5A5 once ACT moves to a Sail release that compares only the low N bits of tdata2
# (sail-riscv#2038). Sail 0.16 compares all of tdata2, so its expected signatures would fail a correct DUT
_MS_TDATA2_ABOVE = 0  # tdata2 bits above N
_MS_DATA_ABOVE = 0x5A5A5A5A5A5A5A5A  # stored register / loaded word bits above N
_MS_STORE = {8: "sb", 16: "sh", 32: "sw", 64: "sd"}
_MS_LOAD = {8: "lb", 16: "lh", 32: "lw", 64: "ld"}  # sign-extending, so the register differs from the compare value
# Execute targets. A select = 1 execute trigger in M-mode also sees the csrw tdata1, x0 that disarms it, which the
# trap handler would skip if it fired, so every 32-bit group keeps that instruction from matching
_MS_DISARM = 0x7A101073  # csrrw x0, tdata1, x0
_MS_ADDI = 0xB5A00013  # addi x0, x0, -0x4a6: rs1 and imm vary freely (bits 31:15), rd = x0 keeps it a hint
_MS_ADDI_LT = 0x7A000013  # addi x0, x0, 0x7a0: below the disarm, for less-than
_MS_ADDI_SMALL = 0x00008013  # addi x0, x1, 0
_MS_ADDI_STEP = 1 << 15  # rs1 field LSB
_MS_CNOP = 0x1059  # c.nop 0x36 (a hint): nzimm[5] (bit 12) and nzimm[4:0] (bits 6:2) vary freely
_MS_CNOP_STEP = 1 << 2


def _ms_mask(bits: int) -> int:
    return (1 << bits) - 1


def _ms_fires(match: int, n: int, xlen: int, tdata2: int, value: int) -> bool:
    """Whether a select = 1, size = N trigger fires on an N-bit access with compare value ``value``."""
    if match in (4, 5, 12, 13):  # XLEN halves of tdata2 and of the zero-extended value
        half = xlen // 2
        part = value if match in (4, 12) else value >> half
        hit = (part & _ms_mask(half) & (tdata2 >> half)) == tdata2 & _ms_mask(half)
    else:  # the low N bits of each
        t, v = tdata2 & _ms_mask(n), value & _ms_mask(n)
        if match in (1, 9):
            zero = next(i for i in range(n) if not t >> i & 1)
            hit = v >> (zero + 1) == t >> (zero + 1)
        else:
            hit = {0: v == t, 8: v == t, 2: v >= t, 3: v < t}[match]
    return hit != (match in (8, 9, 12, 13))


def _ms_swap(groups: list[tuple[int, list, list]], match: int) -> list[tuple[int, list, list]]:
    """The not-equal / not-NAPOT / not-mask match fires exactly where its positive match does not."""
    return [(t, nofire, fire) for t, fire, nofire in groups] if match in (8, 9, 12, 13) else groups


def _ms_data_groups(match: int, n: int, xlen: int) -> list[tuple[int, list, list]]:
    """Groups for an N-bit load or store."""
    d, top, half = _MS_DATA[n], 1 << (n - 1), xlen // 2
    above = _MS_TDATA2_ABOVE & _ms_mask(xlen) & ~_ms_mask(n)
    base = match & 7 if match in (8, 9, 12, 13) else match
    if base == 0:  # equal
        groups = [(above | d, [("value", d)], [("bit0", d ^ 1), ("topbit", d ^ top)])]
    elif base == 2:  # ge: d - 1 misses by one, and 1 would be greater than d in a signed compare
        groups = [(above | d, [("value", d)], [("below", d - 1), ("one", 1)])]
    elif base == 3:  # lt
        groups = [(above | d, [("below", d - 1), ("one", 1)], [("value", d)])]
    elif base == 1:  # NAPOT over bits 3:0
        lo = d & ~0xF
        groups = [
            (above | lo | 0x7, [("range_lo", lo), ("range_hi", lo | 0xF)], [("bit4", lo ^ 0x10), ("topbit", lo ^ top)])
        ]
    elif base == 4:  # mask low: bit 0 compared, bit 1 masked off
        mask = _ms_mask(half) & ~0b10
        groups = [((mask << half) | (d & mask), [("value", d), ("unmasked_bit1", d ^ 2)], [("masked_bit0", d ^ 1)])]
    elif n > half:  # mask high: bit XLEN/2 compared, bit XLEN/2+1 masked off
        mask = _ms_mask(half) & ~0b10
        groups = [
            (
                (mask << half) | (d >> half & mask),
                [("value", d), ("unmasked", d ^ (2 << half))],
                [("masked", d ^ (1 << half))],
            )
        ]
    else:  # mask high on a value no wider than XLEN/2: its high half is 0. The second group would fire if the
        # value were compared as the high half
        groups = [
            (_ms_mask(half) << half, [("value_zero_high", d)], []),
            ((_ms_mask(half) << half) | (d & _ms_mask(half)), [], [("value_as_high", d)]),
        ]
    return _ms_swap(groups, match)


def _ms_exec_groups(match: int, n: int, xlen: int, rd: int) -> list[tuple[int, list, list]]:
    """Groups for an N-bit instruction (16 or 32). The 32-bit groups never match the disarming csrw; those that must
    fire on almost every instruction (not-equal, not-NAPOT, not-mask) are built around it, with targets that are
    other harmless writes of tdata1 (csrrw x{rd}, tdata1, x0 and csrrwi x0, tdata1, 0)."""
    half = xlen // 2
    # tdata2 bits above 32 stay clear for 32-bit instructions: a hart (or Sail 0.16, sail-riscv#2038) that compared
    # them would see the disarming csrw match ge/lt/not-equal and skip it. The load and store groups test those bits
    above = _MS_TDATA2_ABOVE & _ms_mask(xlen) & ~_ms_mask(n) if n == 16 else 0
    if n == 16:
        d, step = _MS_CNOP, _MS_CNOP_STEP
        groups = {
            0: [(above | d, [("value", d)], [("imm0", d ^ step), ("bit12", d ^ (1 << 12))])],
            2: [(above | d, [("value", d)], [("below", d - step), ("c_nop", 0x0001)])],
            3: [(above | d, [("below", d - step), ("c_nop", 0x0001)], [("value", d)])],
            1: [(above | d | 0x3, [("bit2_0", d), ("bit2_1", d | 0x4)], [("bit3", d ^ 0x8), ("bit12", d ^ (1 << 12))])],
            4: [
                (
                    ((_ms_mask(half) & ~0x8) << half) | (d & ~0x8),
                    [("value", d), ("unmasked_bit3", d ^ 0x8)],
                    [("masked_bit2", d ^ 0x4)],
                )
            ],
            5: [
                (_ms_mask(half) << half, [("value_zero_high", d)], []),
                ((_ms_mask(half) << half) | d, [], [("value_as_high", d)]),
            ],
        }
    else:
        d, step, disarm = _MS_ADDI, _MS_ADDI_STEP, _MS_DISARM
        rd_write, imm_write = disarm | rd << 7, disarm | 1 << 14  # csrrw x{rd}, tdata1, x0 / csrrwi x0, tdata1, 0
        groups = {
            0: [(above | d, [("value", d)], [("rs1_bit0", d ^ step), ("bit31", d ^ (1 << 31))])],
            2: [(above | d, [("value", d)], [("below", d - step), ("addi_x1", _MS_ADDI_SMALL)])],
            3: [
                (
                    above | _MS_ADDI_LT,
                    [("below", _MS_ADDI_LT - step), ("addi_x1", _MS_ADDI_SMALL)],
                    [("value", _MS_ADDI_LT), ("signed_below", d)],
                )
            ],
            1: [
                (
                    above | d | 0xFFFF,
                    [("rs1_0", d), ("rs1_3", d | 0x18000)],
                    [("bit17", d ^ (1 << 17)), ("bit31", d ^ (1 << 31))],
                )
            ],
            # not-equal: everything but the disarming csrw fires
            8: [(above | disarm, [("rd", rd_write), ("bit14", imm_write)], [("value", disarm)])],
            # not-NAPOT over bits 13:0, which holds the disarming csrw and the rd variant
            9: [(above | (disarm & ~0x3FFF) | 0x1FFF, [("bit14", imm_write)], [("value", disarm), ("rd", rd_write)])],
            # mask low, addi: bit 15 compared, bit 13 (funct3: addi -> slti) masked off
            4: [
                (
                    ((_ms_mask(half) & ~(1 << 13)) << half) | (d & _ms_mask(half) & ~(1 << 13)),
                    [("value", d), ("unmasked_bit13", d ^ (1 << 13))],
                    [("masked_bit15", d ^ (1 << 15))],
                )
            ],
            # not-mask-low, csrw: bit 14 compared, rd (bits 11:7) masked off
            12: [
                (
                    ((_ms_mask(half) & ~(0x1F << 7)) << half) | (disarm & _ms_mask(half) & ~(0x1F << 7)),
                    [("bit14", imm_write)],
                    [("value", disarm), ("unmasked_rd", rd_write)],
                )
            ],
        }
        if n > half:  # RV32: compare bit 16 (rs1 bit 1) of the high half; mask high masks off bit 17
            mask = _ms_mask(half) & ~0b10
            groups[5] = [
                (
                    (mask << half) | (d >> half & mask),
                    [("value", d), ("unmasked_bit17", d ^ (1 << 17))],
                    [("masked_bit16", d ^ (1 << 16))],
                )
            ]
            # not-mask-high compares only bit 16, where the disarming csrw and addi x0, x0 hold 0
            groups[13] = [((1 << half), [("bit16", d ^ (1 << 16))], [("value", d), ("disarm", disarm)])]
        else:  # RV64: the high half of a 32-bit instruction is 0; only the groups that never fire are safe
            groups[5] = [((_ms_mask(half) << half) | d, [], [("value_as_high", d)])]
            groups[13] = [(_ms_mask(half) << half, [], [("value_zero_high", d)])]
        return groups[match]
    return _ms_swap(groups[match & 7 if match in (8, 9, 12, 13) else match], match)


def _ms_check(match: int, n: int, xlen: int, groups: list[tuple[int, list, list]], disarm: bool) -> None:
    """Fail generation if a case would not behave as its group says, or the disarming csrw would fire."""
    for tdata2, fire, nofire in groups:
        for label, value in fire:
            assert _ms_fires(match, n, xlen, tdata2, value), (match, n, xlen, label)
        for label, value in nofire:
            assert not _ms_fires(match, n, xlen, tdata2, value), (match, n, xlen, label)
        # the disarming csrw must not match whether the low N or all XLEN bits of tdata2 are compared
        assert not (disarm and any(_ms_fires(match, w, xlen, tdata2, _MS_DISARM) for w in (n, xlen))), (match, n, xlen)


def _ms_sizes(xlen: int, kind: str) -> list[int]:
    if kind == "execute":
        return [16, 32]
    return [n for n in (8, 16, 32, 64) if n <= xlen]


def _ms_groups(kind: str, match: int, n: int, xlen: int, rd: int) -> list[tuple[int, list, list]]:
    if kind == "execute":
        groups = _ms_exec_groups(match, n, xlen, rd)
        _ms_check(match, n, xlen, groups, disarm=(n == 32))
    else:
        groups = _ms_data_groups(match, n, xlen)
        _ms_check(match, n, xlen, groups, disarm=False)
    return groups


def _generate_match_size_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate the mcontrol6 match x size tests (select = 1) for stores, loads and, in M-mode, execution."""
    covergroup = f"Sdtrig{mode}_mcontrol6_cg"
    seed(reproducible_hash(covergroup + "_match_size"))
    chunks: list[TestChunk] = []
    addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(3, reg_range=[8, 9, 12, 13, 14, 15])

    def config(trig_num: int, tdata2: int, xsl: int, match: int, n: int) -> tuple[list[str], list[str]]:
        """(write tselect and tdata2 with the trigger disabled, write tdata1 to arm it)"""
        lines = _config_mcontrol6(
            temp_reg, trig_num, tdata2, mode, xsl=xsl, select=1, size=_MS_SIZE_CODE[n], match=match
        )
        split = next(i for i, line in enumerate(lines) if line.startswith("# tdata1:"))
        return lines[:split], lines[split:]

    def data_case(kind: str, arm: list[str], xlen: int, value: int, width: int, note: str) -> list[str]:
        word = (_MS_DATA_ABOVE & _ms_mask(xlen) & ~_ms_mask(width)) | value
        insn = _MS_STORE[width] if kind == "store" else _MS_LOAD[width]
        setup = [f"LI(x{data_reg}, 0x{word:x}) # low {width} bits 0x{value:x}, other bits set"]
        if kind == "load":
            setup.append(f"SREG x{data_reg}, 0(x{addr_reg}) # the loaded word, written before the trigger is armed")
        return [
            *setup,
            *arm,
            f"{insn} x{data_reg}, 0(x{addr_reg}) # {note}",
            "nop # spacer (data match fires after)",
            _csr_access("csrw tdata1, x0 # disarm before the signature is written", mode),
            *_sign_trap_count(data_reg, test_data),
        ]

    def exec_case(arm: list[str], value: int, width: int, note: str) -> list[str]:
        target = f".4byte 0x{value:08x}" if width == 32 else f".2byte 0x{value:04x}"
        return [
            *arm,
            f"{target} # {note}",
            "csrw tdata1, x0 # disarm: never matches this group's tdata2",
            *_sign_trap_count(data_reg, test_data),
        ]

    kinds = ["store", "load", *(["execute"] if mode == "Sm" else [])]
    for kind in kinds:
        coverpoint = f"cp_mcontrol6_match_size_{kind}"
        lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
        lines.extend(_global_ie(mode, True))
        lines.append(
            comment_banner(
                coverpoint,
                f"Each legal match crossed with each legal size on a select = 1 {kind} trigger: accesses of size N\n"
                "that fire, narrowly different ones that don't, and accesses of another width that don't.\n"
                "rvtest_trap_count is signed after each case",
            )
        )
        xsl = {"store": 0b010, "load": 0b001, "execute": 0b100}[kind]
        for trig_num in TRIGGERS:
            gates = [*_mcontrol6_gates(trig_num, mode, select=1), *_xsl_ifdefs(xsl)]
            lines.extend(gates)
            if kind != "execute":
                lines.append(f"LA(x{addr_reg}, scratch)")
            for xlen in (32, 64):
                lines.append(f"#if __riscv_xlen == {xlen}")
                for match in _MS_MATCHES:
                    if match:
                        lines.append(f"#ifdef {_match_legal(match)}")
                    for n in _ms_sizes(xlen, kind):
                        size = _MS_SIZE_CODE[n]
                        lines.append(f"\n# match = {match}, size = {size} ({n} bits)")
                        lines.extend(_size_open(size))
                        cases: list[tuple[int, str, int, int, str]] = []  # (tdata2, label, value, width, note)
                        groups = _ms_groups(kind, match, n, xlen, temp_reg)
                        for tdata2, fire, nofire in groups:
                            cases += [(tdata2, label, v, n, "fires") for label, v in fire]
                            cases += [(tdata2, label, v, n, "must not fire") for label, v in nofire]
                        # accesses of another width W, with the tdata2 their own W-bit groups fire on
                        others = [w for w in (n // 2, n * 2) if w in _ms_sizes(xlen, kind) and w != n]
                        if kind == "execute":
                            others = [16 if n == 32 else 32]
                        for w in others:
                            for tdata2, fire, _ in _ms_groups(kind, match, w, xlen, temp_reg):
                                if (
                                    kind == "execute"
                                    and n == 32
                                    and any(_ms_fires(match, b, xlen, tdata2, _MS_DISARM) for b in (n, xlen))
                                ):
                                    continue  # the disarming csrw would match this tdata2 at size 32
                                cases += [
                                    (tdata2, f"other{w}_{label}", v, w, f"{w}-bit: must not fire (size {n})")
                                    for label, v in fire
                                ]
                        if kind != "execute" and n < xlen:  # an XLEN-wide access that equals tdata2 above N too
                            tdata2, fire, _ = groups[0]
                            for label, v in fire[:1]:
                                full = (tdata2 & ~_ms_mask(n)) | v
                                cases.append(
                                    (tdata2, f"xlen_{label}", full, xlen, f"XLEN-wide: must not fire (size {n})")
                                )
                        last_tdata2 = None
                        for i, (tdata2, label, value, width, note) in enumerate(cases):
                            setup, arm = config(trig_num, tdata2, xsl, match, n)
                            if tdata2 != last_tdata2:  # tselect and tdata2 once per group
                                lines.extend(setup)
                                last_tdata2 = tdata2
                            binname = f"RV{xlen}_trig_{trig_num}_match_{match}_size_{size}_{label}_{i}"
                            zca = kind == "execute" and 16 in (n, width)
                            if zca:
                                lines.append("#ifdef ZCA_SUPPORTED")
                            # a 32-bit instruction on a size = 2 trigger has a cross of its own
                            cp = f"{coverpoint}_other" if kind == "execute" and (n, width) == (16, 32) else coverpoint
                            lines.append(_add_tc(test_data, binname, cp, covergroup))
                            if kind == "execute":
                                lines.extend(exec_case(arm, value, width, note))
                            else:
                                lines.extend(data_case(kind, arm, xlen, value, width, note))
                            if zca:
                                lines.append("#endif")
                        lines.extend(_size_close(size))
                    if match:
                        lines.append(f"#endif // {_match_legal(match)}")
                lines.append(f"#endif // __riscv_xlen == {xlen}")
            lines.extend(_close_gates(gates))

    test_data.int_regs.return_registers([addr_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    for chunk in chunks:  # each section is its own file and enables MIE/SIE at its start
        chunk.code.extend(_global_ie(mode, False))
    return chunks


def _icount_gates(trig_num: int, mode: str) -> list[str]:
    """``#ifdef``s for an icount arm on ``trig_num`` from ``mode``: the trigger supports icount and the mode's bit is
    writable (a case that leaves the bit clear still writes it as 1 in the matching case)."""
    return [f"#ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}", f"#ifdef {_mode_writable(mode)}"]


def _generate_icount_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate icount instruction-count trigger tests.

    Each case signs a marker sum (which instructions ran), the tdata1 readback without hit, which is optional,
    and rvtest_trap_count, so a fire or missing fire is reported at that case.
    """
    covergroup = f"Sdtrig{mode}_icount_cg"
    seed(reproducible_hash(covergroup))
    chunks: list[TestChunk] = []

    # setup registers
    sp_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        4, exclude_regs=[2], reg_range=list(range(8, 16))
    )  # exclude a0, a1 because they are used in SBI

    ######################################
    coverpoint = "cp_icount_hardwired"
    ######################################
    # Shares the icount_instr file: a DUT gets exactly one of hardwired and instr, so neither file is ever empty.
    lines = test_data.new_test_chunk(chunks, "icount_instr").code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "icount priv/action hard-wired field behavior",
        )
    )

    lines.append("#ifdef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")
    for trig_num in TRIGGERS:
        lines.extend([*_icount_gates(trig_num, mode), *_select_trigger(temp_reg, trig_num, mode)])
        binname = f"trig_num_{trig_num}"
        lines.extend(
            [
                _add_tc(test_data, binname, coverpoint, covergroup),
                *_config_icount(temp_reg, trig_num, 1, mode, privbits=0b11111),
                "nop # decrement count, pending becomes set",
                "nop # fire trigger",
                "nop # landing pad",
                _csr_access(f"csrr x{data_reg}, tdata1 # firing clears m/s/u/vs/vu when count is hard-wired", mode),
                *_sigupd_masked(data_reg, temp_reg, 0x1000000, test_data, "hit (bit 24) is optional: not signed"),
                *_disable_trigger(mode),
                *_sign_trap_count(data_reg, test_data),
            ]
        )
        lines.extend(_close_gates(_icount_gates(trig_num, mode)))
    lines.append("#endif // UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")

    ######################################
    coverpoint = "cp_icount_instr"
    ######################################
    lines = test_data.new_test_chunk(chunks, "icount_instr").code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "icount fires after count instructions",
        )
    )
    lines.append("#ifndef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")
    for trig_num in TRIGGERS:
        lines.extend([*_icount_gates(trig_num, mode), *_select_trigger(temp_reg, trig_num, mode)])
        for priv_en in (0, 1):  # test enabled/not enabled in current mode
            privbits = MODE_PRIVBIT[mode] if priv_en else 0
            binname = f"trig_num_{trig_num}_priv_{priv_en}"
            lines.extend(
                [
                    _add_tc(test_data, binname, coverpoint, covergroup),
                    f"LI(x{addr_reg}, 0) # marker sum",
                    *_config_icount(temp_reg, trig_num, 9, mode, privbits=privbits),
                    *[
                        f"addi x{addr_reg}, x{addr_reg}, 0x{i:x} # marker {i}" for i in range(1, 12)
                    ],  # has extra markers that act as spacers
                    write_sigupd(addr_reg, test_data),
                    _csr_access(f"csrr x{data_reg}, tdata1 # read back count/pending after firing", mode),
                    *_sigupd_masked(data_reg, temp_reg, 0x1000000, test_data, "hit (bit 24) is optional: not signed"),
                    *_disable_trigger(mode),
                    *_sign_trap_count(data_reg, test_data),
                ]
            )
        lines.extend(_close_gates(_icount_gates(trig_num, mode)))
    lines.append("#endif // !UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")

    ######################################
    coverpoint = "cp_icount_trap"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "icount count decrement across a trap",
        )
    )
    for trig_num in TRIGGERS:
        lines.extend([*_icount_gates(trig_num, mode), *_select_trigger(temp_reg, trig_num, mode)])
        for priv_en in (0, 1):  # trigger disabled/enabled in the current mode
            privbits = MODE_PRIVBIT[mode] if priv_en else 0
            binname = f"trig_num_{trig_num}_priv_{priv_en}"
            lines.extend(
                [
                    _add_tc(test_data, binname, coverpoint, covergroup),
                    f"LI(x{addr_reg}, 0) # marker sum",
                    *_config_icount(temp_reg, trig_num, 1, mode, privbits=privbits),
                    f".4byte 0xf1101073 # csrrw x0, mvendorid, x0 is illegal from {mode}: the trap matches",
                    *[f"addi x{addr_reg}, x{addr_reg}, {i} # marker {i}" for i in (1, 2, 4)],
                    write_sigupd(addr_reg, test_data),  # 7 = no fire, 6 = fired after the trap, 5 = trap not counted
                    _csr_access(f"csrr x{data_reg}, tdata1 # count and pending after the trap", mode),
                    *_sigupd_masked(data_reg, temp_reg, 0x1000000, test_data, "hit (bit 24) is optional: not signed"),
                    *_disable_trigger(mode),
                    *_sign_trap_count(data_reg, test_data),
                ]
            )
        lines.extend(_close_gates(_icount_gates(trig_num, mode)))

    ######################################
    coverpoint = "cp_icount_eq0"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.extend(_global_ie(mode, True))
    lines.append(
        comment_banner(
            coverpoint,
            "icount pending bit when count reaches 0",
        )
    )
    lines.append("#ifndef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")
    for trig_num in TRIGGERS:
        lines.extend([*_icount_gates(trig_num, mode), *_select_trigger(temp_reg, trig_num, mode)])
        for pending in (0, 1):  # tdata1[8]
            binname = f"trig_num_{trig_num}_pending_{pending}"
            lines.extend(
                [
                    _add_tc(test_data, binname, coverpoint, covergroup),
                    f"LI(x{addr_reg}, 0) # marker sum",
                    *_config_icount(temp_reg, trig_num, 0, mode, pending=pending),
                    *[f"addi x{addr_reg}, x{addr_reg}, {i} # marker {i}" for i in (1, 2, 4)],
                    write_sigupd(addr_reg, test_data),  # 7 = no fire, 6 = pending fired first, 5 = fired late
                    *["nop # count stays 0, so nothing matches again"] * 8,
                    _csr_access(f"csrr x{data_reg}, tdata1 # count still 0, pending cleared", mode),
                    *_sigupd_masked(data_reg, temp_reg, 0x1000000, test_data, "hit (bit 24) is optional: not signed"),
                    *_disable_trigger(mode),
                    *_sign_trap_count(data_reg, test_data),
                ]
            )
        lines.extend(_close_gates(_icount_gates(trig_num, mode)))
    lines.append("#endif // !UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")

    ######################################
    coverpoint = "cp_icount_self_write"
    ######################################
    # SdtrigSm only: from S and U, the tdata1 write goes through T-SBI, so the instruction the trigger matches is the
    # ecall, not the write. With a hard-wired count the rewritten trigger keeps matching, so the case is left out.
    if mode == "Sm":
        lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
        lines.extend(_global_ie(mode, True))
        lines.append(
            comment_banner(
                coverpoint,
                "An icount trigger with count = 1 matches a csrw that rewrites its own tdata1 (count = 100).\n"
                "Afterwards count holds the new value; pending becomes set, and the trigger fires, only with\n"
                "SDTRIG_ICOUNT_SELF_WRITE_SETS_PENDING (norm:Sdtrig_icount_exception). rvtest_trap_count is signed",
            )
        )
        self_write = (TRIG_TYPE_ICOUNT, (100 << 10) | (1 << 9))  # count = 100, m = 1
        lines.append("#ifndef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")
        for trig_num in TRIGGERS:
            gates = _icount_gates(trig_num, mode)
            lines.extend(
                [
                    *gates,
                    *_select_trigger(temp_reg, trig_num, mode),
                    _add_tc(test_data, f"trig_num_{trig_num}", coverpoint, covergroup),
                    *_li_xlen(
                        data_reg,
                        (self_write[0] << 60) | self_write[1],
                        (self_write[0] << 28) | self_write[1],
                        "icount, count = 100, m = 1",
                    ),
                    *_config_icount(temp_reg, trig_num, 1, mode),
                    f"csrw tdata1, x{data_reg} # matched with count = 1: pending set iff SELF_WRITE_SETS_PENDING",
                    "nop # spacer: the breakpoint is taken here if pending was set",
                    # count holds the new value, less the few instructions since: 1 if it is still above 1
                    f"csrr x{data_reg}, tdata1",
                    f"srli x{data_reg}, x{data_reg}, 10",
                    f"andi x{data_reg}, x{data_reg}, 0x3ff # count[9:0]: 100 less the instructions since the write",
                    f"sltiu x{data_reg}, x{data_reg}, 2",
                    f"xori x{data_reg}, x{data_reg}, 1 # 1 if count > 1",
                    write_sigupd(data_reg, test_data),
                    *_disable_trigger(mode),
                    *_sign_trap_count(data_reg, test_data),
                    *_close_gates(gates),
                ]
            )
        lines.append("#endif // !UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1")

    test_data.int_regs.return_registers([sp_reg, addr_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    for chunk in chunks:  # each section is its own file and enables MIE/SIE at its start
        chunk.code.extend(_global_ie(mode, False))
    return chunks


INTERRUPT_CODES = (1, 3, 5, 7, 9, 11, 13)  # SSI, MSI, STI, MTI, SEI, MEI, LCOFI
LOWER_MODE_INTERRUPT_CODES = (1, 5, 9, 13)
TIMER_INTERRUPT_CODE = 7


def _set_itrigger_delegation(code: int, delegate: int, reg: int) -> list[str]:
    return [
        f"LI(x{reg}, 0x{1 << code:x})",
        f"{'csrs' if delegate else 'csrc'} mideleg, x{reg}",
    ]


def _goto_itrigger_origin(origin: str) -> list[str]:
    if origin == "Sm":
        return []
    return [f"RVTEST_TSBI_GOTO_{origin}MODE"]


# Gates for the textra context matches: the hart matches on that context and implements value bits to compare
_MCONTEXT_MATCH_GATE = "#if defined(UDB_SDTRIG_TEXTRA_MHSELECT_MCONTEXT_MATCH) && UDB_SDTRIG_TEXTRA_MHVALUE_LEN > 0"
_SCONTEXT_MATCH_GATE = "#if defined(UDB_SDTRIG_TEXTRA_SSELECT_SCONTEXT_MATCH) && UDB_SDTRIG_TEXTRA_SVALUE_LEN > 0"


def _trap_textra_blocks(
    reg: int, temp_reg: int
) -> list[tuple[str, str, list[str], list[str], list[tuple[str, list[str]]]]]:
    """(context, gate, context-set lines, context-clear lines, [(case, tdata3 load into x{reg})]) for the
    itrigger/etrigger textra cases: mhselect=4 with mhvalue equal to or different from mcontext, and sselect=1 with
    svalue equal to or different from scontext. Each block runs under its gate (an #if closed by #endif)."""
    mh = {name: (v32, v64) for name, v32, v64 in _TEXTRA_MCONTEXT_CASES}
    return [
        (
            "mcontext",
            _MCONTEXT_MATCH_GATE,
            [
                *_xlen_li_expr(temp_reg, _mhvalue(_MCONTEXT_TEST_VALUE_RV32), _mhvalue(_MCONTEXT_TEST_VALUE_RV64)),
                f"csrw mcontext, x{temp_reg}",
            ],
            ["csrw mcontext, x0 # clear the test context"],
            [
                (
                    f"mhvalue_{name}",
                    _xlen_li_expr(
                        reg,
                        _textra_expr(32, mhselect=4, mhvalue=_mhvalue(mh[name][0])),
                        _textra_expr(64, mhselect=4, mhvalue=_mhvalue(mh[name][1])),
                    ),
                )
                for name in ("match", "other")
            ],
        ),
        (
            "scontext",
            _SCONTEXT_MATCH_GATE,
            [
                *_xlen_li_expr(temp_reg, _svalue(_SCONTEXT_TEST_VALUE_RV32), _svalue(_SCONTEXT_TEST_VALUE_RV64)),
                f"csrw scontext, x{temp_reg}",
            ],
            ["csrw scontext, x0 # clear the test context"],
            [
                (
                    f"svalue_{name}",
                    _xlen_li_expr(
                        reg,
                        _textra_expr(32, sselect=1, svalue=_svalue(sv32)),
                        _textra_expr(64, sselect=1, svalue=_svalue(sv64)),
                    ),
                )
                for name, sv32, sv64 in (
                    ("match", _SCONTEXT_TEST_VALUE_RV32, _SCONTEXT_TEST_VALUE_RV64),
                    ("zero", 0, 0),
                )
            ],
        ),
    ]


def _generate_itrigger_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate itrigger interrupt trigger tests."""

    covergroup = f"Sdtrig{mode}_itrigger_cg"
    chunks: list[TestChunk] = []

    # setup registers
    t1, t2 = test_data.int_regs.get_registers(2, exclude_regs=[2], reg_range=list(range(8, 16)))

    ######################################
    coverpoint = "cp_itrigger"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "itrigger with tdata2 selecting one interrupt code and the origin mode's priv bit set or\n"
            "clear; that interrupt, then a different one, is taken. In SdtrigSm, with the priv bit\n"
            "set, the selected interrupt taken from S/U and delegated to S fires it into M; one\n"
            "handled in M never does. In SdtrigS/U whether it fires depends on the hart's\n"
            "re-entrancy option",
        )
    )
    origins = ("Sm", "S", "U") if mode == "Sm" else (mode,)
    for origin in origins:
        gated = mode == "Sm" and origin != "Sm"
        if gated:
            lines.append("#ifdef S_SUPPORTED")
        codes = INTERRUPT_CODES if origin == "Sm" else LOWER_MODE_INTERRUPT_CODES
        delegations = (0,) if origin == "Sm" else (1,)
        for trig_num in TRIGGERS:
            trig_gates = [
                f"#ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_{trig_num}",
                f"#ifdef {_mode_writable(origin)}",
            ]
            lines.extend([*trig_gates, *_select_trigger(t1, trig_num, mode)])
            for code in codes:
                for delegate in delegations:
                    code_guard = guard_symbol(_INT_TYPE[code])
                    lines.append(f"#ifdef {code_guard}")
                    lines.append(f"#ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_{code}")
                    for priv in (0, MODE_PRIVBIT[origin]):
                        binname = f"trig_num_{trig_num}_{origin.lower()}_code_{code}_deleg_{delegate}_priv_{priv:05b}"
                        label_cp = f"{coverpoint}_{MODE_UDB_LETTER[origin].lower()}"
                        lines.append(_add_tc(test_data, binname, label_cp, covergroup))
                        # negative case: a different interrupt is taken; from S/U pick a delegated S-level timer
                        # so the trap is handled in S, where no re-entrancy option suppresses a wrong cause mask
                        other = TIMER_INTERRUPT_CODE if origin == "Sm" else (5 if code != 5 else 1)
                        for cause in (code,) if code == other else (code, other):
                            paired_cause_guard = None
                            if cause != code:
                                paired_cause_guard = guard_symbol(_INT_TYPE[cause])
                                lines.append(f"#ifdef {paired_cause_guard}")
                            cause_gated = mode == "Sm" and origin == "Sm" and cause in LOWER_MODE_INTERRUPT_CODES
                            if cause_gated:
                                lines.append("#ifdef S_SUPPORTED")
                            lines.extend(_global_ie(mode, enable=False))
                            # The M-level sources reach mip only eventually. They are raised only with origin Sm,
                            # so the wait runs in M-mode and polls mip instead of idling for the whole latency.
                            wait = (
                                [
                                    f"RVTEST_WAIT_MIP_PENDING_M(x{t1}, x{t2}, {cause}) # until interrupt {cause} is pending"
                                ]
                                if cause in (3, 7, 11)
                                else []
                            )
                            if mode == "Sm":
                                lines.append("csrci mstatus, 0x2 # SIE=0 while the source is prepared")
                                if gated:
                                    lines.extend(_set_itrigger_delegation(cause, delegate, t1))
                            lines.extend(
                                [
                                    *_config_itrigger(
                                        t1,
                                        trig_num,
                                        1 << code,
                                        mode,
                                        privbits=priv,
                                    ),
                                    *(
                                        [
                                            _load_reg(t1, 1 << cause),
                                            _csr_access(f"csrs mie, x{t1} # enable the non-matching interrupt", mode),
                                        ]
                                        if cause != code
                                        else []
                                    ),
                                    *_cause_interrupt(cause, mode, t1),
                                    *wait,
                                    *_goto_itrigger_origin(origin),
                                    *_global_ie(origin, enable=True),
                                    "nop # allow the pending interrupt to be taken",
                                    *_global_ie(origin, enable=False),
                                ]
                            )
                            if gated:
                                lines.append("RVTEST_TSBI_GOTO_MMODE")
                            lines.extend(
                                [
                                    *_clear_interrupt(cause, mode),
                                    *_sign_trap_count(t2, test_data),
                                    *_disable_trigger(mode),
                                ]
                            )
                            if mode == "Sm" and gated:
                                lines.extend(_set_itrigger_delegation(cause, 0, t1))
                            if cause_gated:
                                lines.append("#endif // S_SUPPORTED")
                            if paired_cause_guard is not None:
                                lines.append(f"#endif // {paired_cause_guard}")

                    lines.append(f"#endif // UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_{code}")
                    lines.append(f"#endif // {code_guard}")
            lines.extend(_close_gates(trig_gates))
        if gated:
            lines.append("#endif  // S_SUPPORTED")

    ######################################
    coverpoint = "cp_textra_itrigger"
    ######################################
    # SdtrigSm only: the S-handled interrupts of cp_itrigger_s fire the trigger into M (medeleg[3]=0), so a
    # textra condition decides whether it fires. The supervisor software interrupt stands in for every code.
    if mode == "Sm":
        lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
        lines.append(
            comment_banner(
                coverpoint,
                "itrigger with tdata1.s = 1 on the supervisor software interrupt, taken from S and delegated\n"
                "to S, with textra mhselect=4 or sselect=1: it fires into M only when the context matches",
            )
        )
        lines.extend(
            [
                "#ifdef S_SUPPORTED",
                "#ifdef UDB_SDTRIG_S_WRITABLE",
                f"#ifdef {guard_symbol(_INT_TYPE[1])}",
                "#ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_1",
            ]
        )
        for ctx, gate, set_ctx, clear_ctx, cases in _trap_textra_blocks(t1, t2):
            lines.extend([f"\n{gate}", *set_ctx])
            for trig_num in TRIGGERS:
                lines.append(f"#ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_{trig_num}")
                lines.extend(_select_trigger(t1, trig_num, mode))
                for case, tdata3 in cases:
                    lines.extend(
                        [
                            _add_tc(
                                test_data,
                                f"trig_num_{trig_num}_{ctx}_{case}",
                                f"{coverpoint}_{ctx}",
                                f"Sdtrig{mode}_textra_cg",
                            ),
                            *_global_ie(mode, enable=False),
                            "csrci mstatus, 0x2 # SIE=0 while the source is prepared",
                            *_set_itrigger_delegation(1, 1, t1),
                            *_config_itrigger(t1, trig_num, 1 << 1, mode, privbits=MODE_PRIVBIT["S"], tdata3=tdata3),
                            *_cause_interrupt(1, mode, t1),
                            "RVTEST_TSBI_GOTO_SMODE",
                            *_global_ie("S", enable=True),
                            "nop # allow the pending interrupt to be taken",
                            *_global_ie("S", enable=False),
                            "RVTEST_TSBI_GOTO_MMODE",
                            *_clear_interrupt(1, mode),
                            *_sign_trap_count(t2, test_data),
                            *_disable_trigger(mode),
                            *_set_itrigger_delegation(1, 0, t1),
                        ]
                    )
                lines.append(f"#endif // UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_{trig_num}")
            lines.extend([*clear_ctx, f"#endif // {ctx} textra match"])
        lines.extend(
            [
                "#endif // UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_1",
                f"#endif // {guard_symbol(_INT_TYPE[1])}",
                "#endif // UDB_SDTRIG_S_WRITABLE",
                "#endif // S_SUPPORTED",
            ]
        )

    test_data.int_regs.return_registers([t1, t2])

    chunks.append(test_data.end_test_chunk())
    return chunks


def _generate_etrigger_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate etrigger exception trigger tests."""
    covergroup = f"Sdtrig{mode}_etrigger_cg"
    chunks: list[TestChunk] = []

    cfg_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        3, exclude_regs=[2, 10, 11], reg_range=list(range(8, 16))
    )

    ######################################
    coverpoint = f"cp_etrigger_{ {'Sm': 'm', 'S': 's', 'U': 'u'}[mode] }"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint,
            "etrigger with tdata2 selecting one exception code and tdata1.priv set or clear; that\n"
            "exception or an illegal instruction is raised. An exception handled in M never fires\n"
            "it, and whether one handled in S fires depends on the hart's re-entrancy option, so\n"
            "bins name the exception raised. SdtrigSm_etrigger_cross_priv_s/u check firing",
        )
    )

    # Exception codes under test
    codes_to_test = _etrigger_codes_to_test(mode)

    if any(code in _PAGE_FAULT_CODES for code in codes_to_test):
        lines.extend(pf_data_section())

    for trig_num in TRIGGERS:
        lines.extend([f"\n#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}", f"#ifdef {_mode_writable(mode)}"])
        lines.extend(_select_trigger(temp_reg, trig_num, mode))
        for code, raisable in codes_to_test.items():
            name = ETRIGGER_EXCODE_NAMES[code]
            lines.append(f"\n#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_{code} // {name}")
            raised_codes = (code, 2) if raisable and code != 2 else (2,)
            for priv_en in (0, 1):
                privbits = MODE_PRIVBIT[mode] if priv_en else 0
                for raised_code in raised_codes:
                    raised = ETRIGGER_EXCODE_NAMES[raised_code]
                    binname = f"trig_num_{trig_num}_code_{name}_priv{priv_en}_raise_{raised}"
                    is_pf = raised_code in _PAGE_FAULT_CODES

                    label_cp = coverpoint if raised_code == code else f"{coverpoint}_other"

                    if is_pf:
                        lines.append(_PAGING_GUARD)
                    lines.extend(
                        [
                            _add_tc(test_data, binname, label_cp, covergroup),
                            *_config_etrigger(cfg_reg, trig_num, 1 << code, mode, privbits=privbits),
                        ]
                    )
                    if is_pf:
                        lines.extend(pf_mode_arm(mode))
                    lines.extend(
                        [
                            *_cause_exception(
                                raised_code,
                                mode,
                                data_reg,
                                temp_reg,
                                mprv_scratch_reg=cfg_reg if (is_pf and mode == "Sm") else None,
                            ),
                        ]
                    )
                    if is_pf:
                        lines.extend(pf_mode_disarm(mode))
                    lines.extend([*_sign_trap_count(data_reg, test_data), *_disable_trigger(mode)])
                    if is_pf:
                        lines.append("#endif // paging")
            lines.append(f"#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_{code}")
        lines.extend(
            [f"#endif // {_mode_writable(mode)}", f"#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}"]
        )

    test_data.int_regs.return_registers([cfg_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def etrigger_cross_priv_delegate_test(test_data: TestData, target_mode: str) -> list[TestChunk]:
    """Etrigger cross-privilege delegation tests."""
    if target_mode not in ("S", "U"):
        raise ValueError(f"etrigger_cross_priv_delegate_test: target_mode must be 'S' or 'U', got {target_mode!r}")

    covergroup = "SdtrigSm_etrigger_cg"
    chunks: list[TestChunk] = []
    lines = test_data.new_test_chunk(chunks, f"etrigger_cross_priv_{target_mode.lower()}").code
    lines.append("#ifdef S_SUPPORTED")

    cfg_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        3, exclude_regs=[2, 10, 11], reg_range=list(range(8, 16))
    )

    ######################################
    coverpoint = f"cp_etrigger_{target_mode.lower()}"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            f"etrigger configured in M, exception raised in {target_mode}-mode with medeleg[cause]\n"
            f"set or clear and medeleg[3]=0. It fires into M when tdata2 selects the raised\n"
            f"code, tdata1.priv is set and the exception is delegated to S; one handled in M\n"
            f"never fires it. The trap record checks the breakpoint's mtval",
        )
    )

    codes_to_test = _etrigger_codes_to_test(target_mode, cross_priv=True)
    goto_target = "RVTEST_TSBI_GOTO_SMODE" if target_mode == "S" else "RVTEST_TSBI_GOTO_UMODE"

    if any(code in _PAGE_FAULT_CODES for code in codes_to_test):
        lines.extend(pf_data_section())

    for trig_num in TRIGGERS:
        lines.extend(
            [
                f"\n#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}",
                f"#ifdef {_mode_writable(target_mode)}",
                *_select_trigger(temp_reg, trig_num, "Sm"),
            ]
        )
        for code, raisable in codes_to_test.items():
            name = ETRIGGER_EXCODE_NAMES[code]
            lines.append(f"\n#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_{code} // {name}")
            raised_codes = (code, 2) if raisable and code != 2 else (2,)

            for priv_en in (0, 1):
                privbits = MODE_PRIVBIT[target_mode] if priv_en else 0
                for medeleg_en in (0,) if code in _ETRIGGER_NOT_DELEGATABLE else (0, 1):
                    if code == 2 and priv_en and medeleg_en:
                        # T-SBI clears medeleg[2], so a DUT that emulates the time CSR forwards the
                        # illegal instruction to S in software and the etrigger does not fire, while the
                        # reference delegates in hardware and fires.
                        continue
                    for raised_code in raised_codes:
                        if (
                            medeleg_en
                            and code == _ETRIGGER_ECALL_CODE[target_mode]
                            and (target_mode == "S" or raised_code != code)
                        ):
                            # RVTEST_TSBI_GOTO_MMODE returns to M with an ecall from the target mode.
                            # With that ecall delegated it is itself a matching exception: from U it
                            # fires the trigger (so a case raising another code would fire), and from S the
                            # S-mode T-SBI forwards it with another ecall that is delegated again (no way back).
                            continue
                        is_pf = raised_code in _PAGE_FAULT_CODES
                        binname = (
                            f"trig_num_{trig_num}_{target_mode.lower()}_code_{name}"
                            f"_priv{priv_en}_medeleg{medeleg_en}_raise_{ETRIGGER_EXCODE_NAMES[raised_code]}"
                        )

                        if raised_code != code:
                            label_cp = f"{coverpoint}_other"
                        else:
                            label_cp = f"{coverpoint}_deleg" if medeleg_en else coverpoint

                        if is_pf:
                            lines.append(_PAGING_GUARD)
                        lines.extend(
                            [
                                _add_tc(test_data, binname, label_cp, covergroup),
                                *_config_etrigger(cfg_reg, trig_num, 1 << code, "Sm", privbits=privbits),
                                *_set_medeleg(temp_reg, code, bool(medeleg_en)),
                                *_set_medeleg(temp_reg, 3, False),  # Trigger -> Breakpoint handled in M-mode
                                goto_target,
                            ]
                        )
                        if is_pf:
                            lines.extend(pf_mode_arm(target_mode))
                        lines.extend(_cause_exception(raised_code, target_mode, data_reg, temp_reg))
                        if is_pf:
                            lines.extend(pf_mode_disarm(target_mode))
                        lines.extend(
                            [
                                "RVTEST_TSBI_GOTO_MMODE",
                                *_set_medeleg(temp_reg, code, False),
                            ]
                        )
                        lines.extend([*_sign_trap_count(data_reg, test_data), *_disable_trigger("Sm")])
                        if is_pf:
                            lines.append("#endif // paging")
            lines.append(f"#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_{code}")
        lines.extend(
            [f"#endif // {_mode_writable(target_mode)}", f"#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}"]
        )
    lines.append("#endif // S_SUPPORTED")

    ######################################
    coverpoint = "cp_textra_etrigger"
    ######################################
    # The S-handled exceptions of cp_etrigger_s_deleg fire the trigger into M (medeleg[3]=0), so a textra
    # condition decides whether it fires. A delegated load access fault stands in for every code.
    if target_mode == "S":
        lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
        lines.append(
            comment_banner(
                coverpoint,
                "etrigger with tdata1.s = 1 on a load access fault raised in S and delegated to S, with\n"
                "textra mhselect=4 or sselect=1: it fires into M only when the context matches",
            )
        )
        lines.extend(
            ["#ifdef S_SUPPORTED", "#ifdef UDB_SDTRIG_S_WRITABLE", "#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_5"]
        )
        for ctx, gate, set_ctx, clear_ctx, cases in _trap_textra_blocks(cfg_reg, temp_reg):
            lines.extend([f"\n{gate}", *set_ctx])
            for trig_num in TRIGGERS:
                lines.append(f"#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}")
                lines.extend(_select_trigger(cfg_reg, trig_num, "Sm"))
                for case, tdata3 in cases:
                    lines.extend(
                        [
                            _add_tc(
                                test_data,
                                f"trig_num_{trig_num}_{ctx}_{case}",
                                f"{coverpoint}_{ctx}",
                                "SdtrigSm_textra_cg",
                            ),
                            *_config_etrigger(
                                cfg_reg, trig_num, 1 << 5, "Sm", privbits=MODE_PRIVBIT["S"], tdata3=tdata3
                            ),
                            *_set_medeleg(temp_reg, 5, True),
                            *_set_medeleg(temp_reg, 3, False),  # Trigger -> Breakpoint handled in M-mode
                            "RVTEST_TSBI_GOTO_SMODE",
                            *_cause_exception(5, "S", data_reg, temp_reg),
                            "RVTEST_TSBI_GOTO_MMODE",
                            *_set_medeleg(temp_reg, 5, False),
                            *_sign_trap_count(data_reg, test_data),
                            *_disable_trigger("Sm"),
                        ]
                    )
                lines.append(f"#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}")
            lines.extend([*clear_ctx, f"#endif // {ctx} textra match"])
        lines.extend(
            [
                "#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_5",
                "#endif // UDB_SDTRIG_S_WRITABLE",
                "#endif // S_SUPPORTED",
            ]
        )

    test_data.int_regs.return_registers([cfg_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _generate_textra_tests(test_data: TestData, mode: str) -> list[TestChunk]:
    """Generate textra32/64 (tdata3) context-matching tests, one test chunk per coverpoint.

    Each case arms an icount (count=1) or mcontrol6 (store-data) trigger whose tdata3 selects a context match,
    performs the triggering action, disarms it, and signs rvtest_trap_count, so a case that fires when it
    should not (or the reverse) is reported at that case. Every section needs TDATA3_IMPLEMENTED and the match
    parameter of the context it selects (SDTRIG_TEXTRA_MHSELECT_MCONTEXT_MATCH, SSELECT_SCONTEXT_MATCH,
    SSELECT_ASID_MATCH); the context and textra values are limited to the implemented mhvalue and svalue bits.
    itrigger/etrigger are omitted here: with action=0 they cannot fire in these cases, because every interrupt and
    exception is taken with xIE=0 (into M, or into S with medeleg[3]=1). cp_textra_itrigger and cp_textra_etrigger
    test them on S-handled traps instead.
    """
    covergroup = f"Sdtrig{mode}_textra_cg"
    chunks: list[TestChunk] = []
    trig_types = ("icount", "mcontrol6")
    cfg_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(
        4, exclude_regs=[2, 10, 11], reg_range=list(range(8, 16))
    )

    def case(binname: str, cp: str, trig_num: int, trig_type: str, tdata3_lines: list[str]) -> list[str]:
        return [
            _add_tc(test_data, binname, cp, covergroup),
            *_config_textra(cfg_reg, trig_num, trig_type, tdata3_lines, mode),
            *_fire_textra_trigger(trig_type, mode, cfg_reg, addr_reg, data_reg),
            *_disable_trigger(mode),
            *_sign_trap_count(temp_reg, test_data),
        ]

    def per_type(trig_num: int, trig_type: str, body: list[str]) -> list[str]:
        guards = [
            g.format(trig_num=trig_num, mode_letter=MODE_UDB_LETTER[mode]) for g in _TEXTRA_TYPE_GUARDS[trig_type]
        ]
        return [
            f"\n# trig_num {trig_num}, {trig_type}",
            *guards,
            *_select_trigger(cfg_reg, trig_num, mode),
            *body,
            *(["#endif"] * len(guards)),
        ]

    def context_access(csr: str, instr: str) -> list[str]:
        if mode == "S" and csr in ("scontext", "hcontext"):
            # set up through T-SBI: mstateen0.CONTEXT may make scontext/hcontext illegal below M-mode
            return [tsbi_call(instr)]
        return [_csr_access(instr, mode)]

    def set_context(csr: str, expr32: str, expr64: str) -> list[str]:
        return [
            *_xlen_li_expr(temp_reg, expr32, expr64),
            *context_access(csr, f"csrw {csr}, x{temp_reg} # live context tag"),
        ]

    ######################################
    coverpoint = "cp_textra_mcontext"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(comment_banner(coverpoint, "textra mhselect=4: the trigger fires only when mhvalue equals mcontext"))
    lines.append(_MCONTEXT_MATCH_GATE)
    lines.extend(_global_ie(mode, True))
    lines.extend(set_context("mcontext", _mhvalue(_MCONTEXT_TEST_VALUE_RV32), _mhvalue(_MCONTEXT_TEST_VALUE_RV64)))
    for trig_num in TRIGGERS:
        for trig_type in trig_types:
            body: list[str] = []
            for case_name, mhv32, mhv64 in _TEXTRA_MCONTEXT_CASES:
                tdata3 = _xlen_li_expr(
                    cfg_reg,
                    _textra_expr(32, mhselect=4, mhvalue=_mhvalue(mhv32)),
                    _textra_expr(64, mhselect=4, mhvalue=_mhvalue(mhv64)),
                )
                body += case(
                    f"trig_num_{trig_num}_type_{trig_type}_mhvalue_{case_name}", coverpoint, trig_num, trig_type, tdata3
                )
            lines.extend(per_type(trig_num, trig_type, body))
    lines.append(_csr_access("csrw mcontext, x0 # clear the test context", mode))
    lines.extend(_global_ie(mode, False))
    lines.append("#endif // mcontext textra match")

    ######################################
    coverpoint = "cp_textra_scontext"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(comment_banner(coverpoint, "textra sselect=1: svalue compared with scontext, sbytemask bytes ignored"))
    lines.append(_SCONTEXT_MATCH_GATE)
    lines.extend(_global_ie(mode, True))
    lines.extend(set_context("scontext", _svalue(_SCONTEXT_TEST_VALUE_RV32), _svalue(_SCONTEXT_TEST_VALUE_RV64)))
    for trig_num in TRIGGERS:
        for trig_type in trig_types:
            body = ["#if __riscv_xlen == 64"]
            for sv, m in _TEXTRA_SCONTEXT_RV64:
                tdata3 = [f"LI(x{cfg_reg}, {_textra_expr(64, sselect=1, svalue=_svalue(sv), sbytemask=m)})"]
                body += case(
                    f"trig_num_{trig_num}_type_{trig_type}_svalue_{sv:08x}_mask_{m:04b}",
                    coverpoint,
                    trig_num,
                    trig_type,
                    tdata3,
                )
            body.append("#else")
            for sv, m in _TEXTRA_SCONTEXT_RV32:
                tdata3 = [f"LI(x{cfg_reg}, {_textra_expr(32, sselect=1, svalue=_svalue(sv), sbytemask=m)})"]
                body += case(
                    f"trig_num_{trig_num}_type_{trig_type}_svalue_{sv:04x}_mask_{m:02b}",
                    coverpoint,
                    trig_num,
                    trig_type,
                    tdata3,
                )
            body.append("#endif")
            lines.extend(per_type(trig_num, trig_type, body))
    lines.extend(context_access("scontext", "csrw scontext, x0 # clear the test context"))
    lines.extend(_global_ie(mode, False))
    lines.append("#endif // UDB_SCONTEXT_AVAILABLE")

    ######################################
    coverpoint = "cp_textra_double_context"
    ######################################
    lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
    lines.append(
        comment_banner(
            coverpoint, "mhselect/mhvalue and sselect/svalue together: fires only when every enabled context matches"
        )
    )
    lines.append(_MCONTEXT_MATCH_GATE)
    lines.append(_SCONTEXT_MATCH_GATE)
    lines.extend(_global_ie(mode, True))
    lines.extend(set_context("mcontext", *(_mhvalue(v) for v in _DOUBLE_MCONTEXT)))
    lines.extend(set_context("scontext", *(_svalue(v) for v in _DOUBLE_SCONTEXT)))
    for trig_num in TRIGGERS:
        for trig_type in trig_types:
            body = []
            for mhsel in (0, 4):
                for ssel in (0, 1):
                    for mh_name, mh_on in (("mismatch", False), ("match", True)):
                        for sv_name, sv_on in (("mismatch", False), ("match", True)):
                            fields = {
                                xl: {
                                    "mhselect": mhsel,
                                    "mhvalue": _mhvalue(_DOUBLE_MCONTEXT[i] if mh_on else 0),
                                    "sselect": ssel,
                                    "svalue": _svalue(_DOUBLE_SCONTEXT[i] if sv_on else 0),
                                }
                                for i, xl in ((0, 32), (1, 64))
                            }
                            tdata3 = _xlen_li_expr(
                                cfg_reg, _textra_expr(32, **fields[32]), _textra_expr(64, **fields[64])
                            )
                            name = f"trig_num_{trig_num}_type_{trig_type}_mhsel{mhsel}_mhvalue_{mh_name}_ssel{ssel}_svalue_{sv_name}"
                            body += case(name, coverpoint, trig_num, trig_type, tdata3)
            lines.extend(per_type(trig_num, trig_type, body))
    lines.append(_csr_access("csrw mcontext, x0 # clear the test context", mode))
    lines.extend(context_access("scontext", "csrw scontext, x0 # clear the test context"))
    lines.extend(_global_ie(mode, False))
    lines.append("#endif // UDB_SCONTEXT_AVAILABLE")
    lines.append("#endif // UDB_MCONTEXT_AVAILABLE")

    ######################################
    coverpoint = "cp_textra_asid"
    ######################################
    # satp.MODE=Bare with a nonzero ASID is UNSPECIFIED, so satp selects a paging mode with ASID X. M-mode is
    # not translated, so SdtrigSm needs no mapping; SdtrigS runs the accesses and its trap handler in S-mode
    # through the boot identity map in the root table. SdtrigU would need user mappings of its code and data.
    if mode in ("Sm", "S"):
        lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
        lines.append(
            comment_banner(
                coverpoint,
                "textra sselect=2: the low ASIDMAX bits of svalue compared with satp.ASID; sbytemask is ignored",
            )
        )
        lines.append(
            "#if defined(S_SUPPORTED) && defined(UDB_SDTRIG_TEXTRA_SSELECT_ASID_MATCH) && UDB_ASID_WIDTH >= 2 "
            "&& UDB_SDTRIG_TEXTRA_SVALUE_LEN >= UDB_ASID_WIDTH"
        )
        lines.append(
            "#if (__riscv_xlen == 64 && defined(SV39_SUPPORTED)) || (__riscv_xlen == 32 && defined(SV32_SUPPORTED))"
        )
        lines.extend(_global_ie(mode, True))
        lines.extend(
            [
                f"LA(x{temp_reg}, rvtest_Sroot_pg_tbl)",
                f"srli x{temp_reg}, x{temp_reg}, 12 # root PPN",
                "#if __riscv_xlen == 64",
                f"LI(x{data_reg}, (SATP_MODE_SV39 << 60) | ({_ASID_X} << 44))",
                "#else",
                f"LI(x{data_reg}, SATP32_MODE | ({_ASID_X} << 22))",
                "#endif",
                f"or x{temp_reg}, x{temp_reg}, x{data_reg}",
                f"csrw satp, x{temp_reg} # satp.ASID = X",
                *(["sfence.vma"] if mode == "S" else []),
            ]
        )
        for trig_num in TRIGGERS:
            for trig_type in trig_types:
                body = []
                for case_name, sv, masked in _TEXTRA_ASID_CASES:
                    sv64 = sv.replace("ASIDMAX", "16").replace("X", _ASID_X)
                    sv32 = sv.replace("ASIDMAX", "9").replace("X", _ASID_X)
                    mask64 = 0xF if masked else 0
                    mask32 = 0x3 if masked else 0
                    tdata3 = _xlen_li_expr(
                        cfg_reg,
                        _textra_expr(32, sselect=2, svalue=_svalue(sv32), sbytemask=mask32),
                        _textra_expr(64, sselect=2, svalue=_svalue(sv64), sbytemask=mask64),
                    )
                    body += case(
                        f"trig_num_{trig_num}_type_{trig_type}_svalue_{case_name}",
                        coverpoint,
                        trig_num,
                        trig_type,
                        tdata3,
                    )
                lines.extend(per_type(trig_num, trig_type, body))
        lines.extend(["csrw satp, x0 # back to Bare", "sfence.vma"])
        lines.extend(_global_ie(mode, False))
        lines.append("#endif // SV39_SUPPORTED / SV32_SUPPORTED")
        lines.append("#endif // S_SUPPORTED && UDB_SDTRIG_TEXTRA_SSELECT_ASID_MATCH")

    ######################################
    coverpoint = "cp_textra_mhselect_no_h"
    ######################################
    # tdata3 is written through T-SBI in SdtrigS, so the writes run in M-mode as in SdtrigSm
    if mode in ("Sm", "S"):
        lines = test_data.new_test_chunk(chunks, coverpoint.removeprefix("cp_")).code
        lines.append(
            comment_banner(
                coverpoint,
                "Without H, write tdata3.mhselect = 1, 2, 3, 5, 6, 7 on an armed trigger that never fires (icount with\n"
                "m = 0, mcontrol6 with no execute/store/load). Only 0 and 4 are legal, so 1 is recorded when\n"
                "mhselect reads back 0 or 4; which of the two is the hart's choice",
            )
        )
        lines.append("#if !defined(H_SUPPORTED) && defined(UDB_TDATA3_IMPLEMENTED)")
        for trig_num in TRIGGERS:
            for trig_type in trig_types:
                if trig_type == "icount":
                    arm = _config_icount(cfg_reg, trig_num, 1, mode, privbits=0)
                else:
                    arm = _config_mcontrol6(cfg_reg, trig_num, 0x12345678, mode, xsl=0b000, select=1)
                body = [*_select_trigger(cfg_reg, trig_num, mode), *arm]
                for mhsel in (1, 2, 3, 5, 6, 7):
                    body += [
                        _add_tc(
                            test_data, f"trig_num_{trig_num}_type_{trig_type}_mhselect_{mhsel}", coverpoint, covergroup
                        ),
                        *_xlen_li(temp_reg, _textra3(32, mhselect=mhsel), _textra3(64, mhselect=mhsel)),
                        _csr_access(f"csrw tdata3, x{temp_reg} # mhselect = {mhsel}", mode),
                        _csr_access(f"csrr x{data_reg}, tdata3", mode),
                        "#if __riscv_xlen == 64",
                        f"srli x{data_reg}, x{data_reg}, 48",
                        "#else",
                        f"srli x{data_reg}, x{data_reg}, 23",
                        "#endif",
                        f"andi x{data_reg}, x{data_reg}, 3 # mhselect[1:0]",
                        f"seqz x{data_reg}, x{data_reg} # 1 if mhselect is 0 or 4",
                        write_sigupd(data_reg, test_data),
                    ]
                body += _disable_trigger(mode)
                # the mcontrol6 arm writes select = 1, and neither arm needs the mode bits
                guards = [f"UDB_SDTRIG_{trig_type.upper()}_SUPPORTED_TRIGGERS_{trig_num}"]
                if trig_type == "mcontrol6":
                    guards.append("UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE")
                gates = [f"#ifdef {g}" for g in guards]
                lines.extend([f"\n# trig_num {trig_num}, {trig_type}", *gates, *body, *_close_gates(gates)])
        lines.append("#endif // !H_SUPPORTED && UDB_TDATA3_IMPLEMENTED")

    # cp_smode_fields_hardwired is not generated: svalue/sselect "should" be tied to 0 without S-mode
    # (Sdtrig_textra32_svalue_no_s, Sdtrig_textra32_sselect_no_s), so a hart that implements them is legal.

    test_data.int_regs.return_registers([cfg_reg, addr_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def register_sdtrig_textra(mode: str, required_extensions: list[str | list[str]], extra_defines: list[str]) -> None:
    """Register the textra (tdata3 context-match) section for ``mode`` as its own generator of suite ``Sdtrig{mode}``."""

    @add_priv_test_generator(
        f"Sdtrig{mode}", required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_textra(test_data: TestData) -> list[TestChunk]:
        """textra context-match tests."""
        return _with_trap_counts(_generate_textra_tests(test_data, mode))


def _with_trap_counts(chunks: list[TestChunk]) -> list[TestChunk]:
    """Size each chunk's trap signature region: up to 6 traps per testcase (an exception or interrupt, a second
    one, and the breakpoints they fire) plus one per T-SBI call. With up to SDTRIG_MAX_TRIGGERS triggers a file can
    take more traps than the default PRIV_TRAP_SIGUPD_COUNT."""
    for chunk in chunks:
        tsbi_calls = sum(line.count("RVTEST_TSBI") for line in chunk.code)
        chunk.trap_sigupd_count = trap_sigupd_count(6 * chunk.num_testcases + tsbi_calls + 16)
    return chunks


# ── Suite registration ─────────────────────────────────────────────────────


def register_sdtrig_suite(mode: str, required_extensions: list[str | list[str]], extra_defines: list[str]) -> None:
    """Register each Sdtrig section for ``mode`` ("Sm"/"S"/"U") as its own generator of suite ``Sdtrig{mode}``."""
    suite = f"Sdtrig{mode}"

    @add_priv_test_generator(
        suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_access(test_data: TestData) -> list[TestChunk]:
        """Access tests."""
        return _with_trap_counts(_generate_access_tests(test_data, mode))

    if mode in ("Sm", "S"):
        # The trigger module registers are M-mode only: SdtrigS accesses them through T-SBI, so these tests and
        # the crosses that sample them run in M-mode in both suites.

        @add_priv_test_generator(
            suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
        )
        def make_sdtrig_csr(test_data: TestData) -> list[TestChunk]:
            """Trigger-module register tests."""
            return _with_trap_counts(_generate_csr_tests(test_data, mode))

        @add_priv_test_generator(
            suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
        )
        def make_sdtrig_tcontrol(test_data: TestData) -> list[TestChunk]:
            """tcontrol tests."""
            return _with_trap_counts(_generate_tcontrol_tests(test_data, mode))

        @add_priv_test_generator(
            suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
        )
        def make_sdtrig_address_matches(test_data: TestData) -> list[TestChunk]:
            """tdata2 address storage and translated execute-trigger tests."""
            return _with_trap_counts(_generate_address_matches_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_mcontrol6(test_data: TestData) -> list[TestChunk]:
        """mcontrol6 tests."""
        return _with_trap_counts(_generate_mcontrol6_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_match_size(test_data: TestData) -> list[TestChunk]:
        """mcontrol6 match x size tests (select = 1)."""
        return _with_trap_counts(_generate_match_size_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=[*required_extensions, "Zvl32b"], march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_vector(test_data: TestData) -> list[TestChunk]:
        """vector load/store tests."""
        return _with_trap_counts(_generate_vector_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=[*required_extensions, "Zicbom"], march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_zicbom(test_data: TestData) -> list[TestChunk]:
        """cbo.clean/flush/inval tests."""
        return _with_trap_counts(_generate_zicbom_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=[*required_extensions, "Zicboz"], march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_zicboz(test_data: TestData) -> list[TestChunk]:
        """cbo.zero tests."""
        return _with_trap_counts(_generate_zicboz_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=[*required_extensions, "Zicbop"], march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_zicbop(test_data: TestData) -> list[TestChunk]:
        """prefetch tests."""
        return _with_trap_counts(_generate_zicbop_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_icount(test_data: TestData) -> list[TestChunk]:
        """icount tests."""
        return _with_trap_counts(_generate_icount_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=[*required_extensions, "Zalrsc"], march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_zalrsc(test_data: TestData) -> list[TestChunk]:
        """lr/sc tests."""
        return _with_trap_counts(_generate_zalrsc_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=[*required_extensions, "Zaamo"], march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_zaamo(test_data: TestData) -> list[TestChunk]:
        """AMO tests."""
        return _with_trap_counts(_generate_zaamo_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_itrigger(test_data: TestData) -> list[TestChunk]:
        """itrigger tests."""
        return _with_trap_counts(_generate_itrigger_tests(test_data, mode))

    @add_priv_test_generator(
        suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
    )
    def make_sdtrig_etrigger(test_data: TestData) -> list[TestChunk]:
        """etrigger tests."""
        return _with_trap_counts(_generate_etrigger_tests(test_data, mode))

    if mode == "Sm":

        @add_priv_test_generator(
            suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
        )
        def make_sdtrig_etrigger_cross_priv_s(test_data: TestData) -> list[TestChunk]:
            """etrigger configured in M, exceptions raised in S."""
            return _with_trap_counts(etrigger_cross_priv_delegate_test(test_data, "S"))

        @add_priv_test_generator(
            suite, required_extensions=required_extensions, march_extensions=[], extra_defines=extra_defines
        )
        def make_sdtrig_etrigger_cross_priv_u(test_data: TestData) -> list[TestChunk]:
            """etrigger configured in M, exceptions raised in U."""
            return _with_trap_counts(etrigger_cross_priv_delegate_test(test_data, "U"))

    if mode != "Sm":
        # medeleg exists only with S-mode

        @add_priv_test_generator(
            suite,
            required_extensions=required_extensions if mode == "S" else [*required_extensions, "S"],
            march_extensions=[],
            extra_defines=extra_defines,
        )
        def make_sdtrig_native_triggers(test_data: TestData) -> list[TestChunk]:
            """Breakpoint delegation tests."""
            return _with_trap_counts(_generate_native_triggers_tests(test_data, mode))

    register_sdtrig_textra(mode, required_extensions, extra_defines)

    # Disabled section and its extra required extension:
    #   _generate_zcmp_tests: Zcmp; waits for Zcmp in the Sail reference model (riscv/sail-riscv#730)
