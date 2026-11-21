#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Sdtrig: one test per normative rule of the Sdtrig (debug trigger) extension that is observable
without Debug Mode.

Rules are norm: tags in Sdtrig.adoc and xml/hwbp_registers.xml of the RISC-V Debug spec (riscv-debug-spec PR 1220,
afd3901; upstream main has no tags yet). Tests boot to S-mode and program the M-level trigger CSRs through T-SBI;
breakpoints (action = 0) are taken in U, S, VS or VU and land in the S/HS handler (medeleg[3] = 1, hedeleg = 0) or
in M on harts that hard-wire medeleg[3] to 0. M-mode parts (M-mode triggers, tcontrol, optional trigger CSRs that may
trap, etrigger/itrigger on traps delegated to S) are _Sm files. Every trigger feature is probed at run time (WARL
write and read-back of tdata1/tdata2); a test passes vacuously on a hart without the feature.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import sdtriglib as sd
from aigen import POOL_TRAP, X
from sdtriglib import EXEC, LOAD, MC6, SELECT, STORE, Acc, SdFile, set_t2

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, TestFile

SUITE = "Sdtrig"
SRC = "riscv-debug-spec Sdtrig.adoc"
XML = "riscv-debug-spec xml/hwbp_registers.xml"
MARCH = "rv${XLEN}i_zicsr_zifencei"
H = sd.H
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    "action0_epc_always_next": "xepc of an action=0 breakpoint always points past the matching instruction",
    "exec_fires_on_load": "an execute trigger also fires on a load from the instruction's address",
    "load_fires_on_store": "a load address trigger also fires on a store to that address",
    "store_fires_on_load": "a store address trigger also fires on a load from that address",
    "load_ignores_size_any": "a size=0 (any) load trigger does not fire on a byte load",
}

DATA = "sd_data"


def mut(name: str) -> bool:
    assert name in MUTANTS, name
    return name == MUT


def new(rule: str, *, sm: bool = False, vector: bool = False, march: str = MARCH, req: list | None = None) -> SdFile:
    required = ["I", "Sm", "Sdtrig"] if sm else ["I", "S", "Sdtrig"]
    required += req or []
    t = SdFile(
        SUITE,
        rule,
        required=required,
        march=march,
        boot="M" if sm else "S",
        pool=POOL_TRAP,
        suffix="_Sm" if sm else "",
        vector=vector,
    )
    t.extra_data += [".p2align 6", f"{DATA}:", "  .fill 32, 4, 0x5a5aa5a5"]
    if sm:
        sd.m_prologue(t)
    else:
        sd.s_prologue(t)
    return t


def modes(t: TestFile, body: Callable[[str], object], ms: tuple[str, ...] = ("U", "S", "VS", "VU")) -> None:
    """Call body(mode) for each mode, VS/VU under H (U-mode needs U, which every S-boot config has)."""
    for m in ms:
        if m in ("VS", "VU"):
            with t.only_if(H):
                body(m)
        else:
            body(m)


def with_trigger(
    t: TestFile, acc: Acc, low: int, t2: str | list[str] | int, body: Callable[[], object], typ: int = MC6
) -> None:
    """Probe for a trigger accepting (typ, low) with tdata2 = t2; when one exists, arm it, run body, disarm it."""
    sd.probe(t, acc, [(typ, low)], [t2])

    def run() -> None:
        sd.arm(t, acc, typ, low, t2)
        body()
        sd.disarm(t, acc)

    sd.either(t, "x1", run)


TVAL_RULE = (
    "mcontrol6 breakpoints write xtval = 0 or the faulting virtual address, the address accessed "
    "(norm:Sdtrig_mcontrol6_breakpoint, norm:Sdtrig_mcontrol6_faulting_address)."
)
TIMING = (
    "mcontrol6 has no timing bit: a trigger may fire before the matching instruction retires (xepc = that "
    "instruction), just after it (xepc = the next one) or later (xepc = a later one), so xepc is accepted anywhere "
    "in the window and the handler resumes at the window's end (rvtest_trap_resume)."
)


# ---------------------------------------------------------------- tests
def t_action0() -> SdFile:
    t = new("Sdtrig_action0")
    acc = Acc(t)
    t.describe(
        source=SRC,
        rule_text="Raise a breakpoint exception. (Used when software wants to use the trigger module without an external "
        "debugger attached.) `xepc` must contain the virtual address of the next instruction that must be executed "
        "to preserve the program flow.",
        context=TIMING + " The window's first instruction is addi x7, x7, 1 with x7 = 0, so 'the next instruction "
        "that must be executed' is that addi when x7 is still 0 and a later instruction when the addi retired.",
        plan="For each of U, S, VS and VU (VS/VU with H): find a trigger that accepts an mcontrol6 execute-address "
        "trigger (match=0, action=0) enabled only in that mode, arm it on the window's first instruction, run the "
        "window and check:\n"
        "1. exactly one breakpoint (cause 3) from that mode, xtval = 0 or the instruction's address;\n"
        "2. xepc = the addi exactly when the addi did not execute (x7 = 0), and xepc is past it when x7 = 1.",
    )

    def per(mode: str) -> None:
        lab = t.label(f"pc_{mode}")
        low = EXEC | sd.MODEBITS6[mode]

        def body() -> None:
            t.li("x7", 0)
            # lab is the first instruction of the window (fire() emits it); point tdata2 at it via its own label
            at, _ = fire_at(
                t,
                mode,
                lab,
                ["addi x7, x7, 1  // matched instruction", "nop", "nop"],
                True,
                "execute trigger on addi",
                tval=[0, lab],
                off="x9",
            )
            t.comment("x15 = (xepc == first) == (x7 == 0)")
            t.emit("seqz x15, x9")
            t.emit("seqz x13, x7")
            t.emit("xor x15, x15, x13")
            t.emit("seqz x15, x15")
            if mut("action0_epc_always_next"):
                t.emit("snez x15, x9")
            t.check_bool("x15", at, f"execute trigger in {mode}-mode: xepc is the addi iff the addi did not retire")

        with_trigger(t, acc, low, lab, body)

    modes(t, per)
    return t


def fire_at(
    t: TestFile, mode: str, lab: str, body: list[str], expect: bool | None, desc: str, **kw: object
) -> tuple[str, str]:
    """sd.fire with the window's first instruction also labelled lab (for a tdata2 set before the window)."""
    return sd.fire(t, mode, [f"{lab}:", *body], expect, desc, **kw)  # type: ignore[arg-type]


def t_execute() -> SdFile:
    t = new("Sdtrig_mcontrol6_execute")
    acc = Acc(t)
    t.describe(
        source=XML,
        rule_text="When set, the trigger fires on the virtual address or opcode of an instruction that is executed.",
        context=TIMING + " " + TVAL_RULE,
        plan="For each of U, S, VS and VU (VS/VU with H), with an mcontrol6 execute-address trigger (match=0, "
        "select=0, size=0) enabled only in that mode on address B:\n"
        "1. a window executing other instructions (not B) takes no trap;\n"
        "2. a window whose first instruction is at B takes one breakpoint from that mode, xtval = 0 or B;\n"
        "3. a load from B (the instruction's address used as data) takes no trap: execute does not match loads.",
    )

    def per(mode: str) -> None:
        b = t.label(f"B_{mode}")
        low = EXEC | sd.MODEBITS6[mode]

        def body() -> None:
            sd.fire(t, mode, ["addi x7, x0, 1", "nop"], False, "execute trigger on B, other instructions run")
            fire_at(t, mode, b, ["addi x7, x0, 2", "nop", "nop"], True, "execute trigger on B, B runs", tval=[0, b])
            t.la("x8", b)
            sd.fire(
                t,
                mode,
                ["lw x7, 0(x8)  // load from B", "nop"],
                mut("exec_fires_on_load"),
                "execute trigger on B, load from B",
            )

        with_trigger(t, acc, low, b, body)

    modes(t, per)
    return t


def t_loadstore(load: bool) -> SdFile:
    rule = "Sdtrig_mcontrol6_load" if load else "Sdtrig_mcontrol6_store"
    t = new(rule)
    acc = Acc(t)
    kind = "load" if load else "store"
    t.describe(
        source=XML,
        rule_text=f"When set, the trigger fires on the virtual address or data of any {kind}.",
        context=TIMING + " " + TVAL_RULE + " With select=0 a compare value is the lowest address of the access; "
        "size=0 matches accesses of any size (norm:Sdtrig_mcontrol6_size_any).",
        plan=f"For each of U, S, VS and VU (VS/VU with H), with an mcontrol6 {kind}-address trigger (match=0, "
        f"select=0, size=0) enabled only in that mode on address A = {DATA}+8:\n"
        f"1. a word {kind} at A takes one breakpoint from that mode, xtval = 0 or A;\n"
        f"2. a byte {kind} at A takes one breakpoint (size any), and on RV64 a doubleword {kind};\n"
        f"3. a word {'store to' if load else 'load from'} A takes no trap (the other access kind does not match);\n"
        f"4. a word {kind} at A+8 takes no trap.",
    )
    same_w, same_b, same_d = (
        ("lw x7, 0(x8)", "lb x7, 0(x8)", "ld x7, 0(x8)") if load else ("sw x7, 0(x8)", "sb x7, 0(x8)", "sd x7, 0(x8)")
    )
    other = "sw x7, 0(x8)" if load else "lw x7, 0(x8)"
    other_fires = mut("load_fires_on_store") if load else mut("store_fires_on_load")

    def per(mode: str) -> None:
        low = (LOAD if load else STORE) | sd.MODEBITS6[mode]

        def body() -> None:
            t.la("x8", f"{DATA}+8")
            sd.fire(
                t, mode, [same_w, "nop", "nop"], True, f"{kind} trigger on A, word {kind} at A", tval=[0, f"{DATA}+8"]
            )
            sd.fire(
                t,
                mode,
                [same_b, "nop", "nop"],
                not mut("load_ignores_size_any") if load else True,
                f"{kind} trigger on A, byte {kind} at A",
                tval=[0, f"{DATA}+8"],
            )
            with t.rv64_only():
                sd.fire(
                    t,
                    mode,
                    [same_d, "nop", "nop"],
                    True,
                    f"{kind} trigger on A, doubleword {kind} at A",
                    tval=[0, f"{DATA}+8"],
                )
            sd.fire(
                t,
                mode,
                [other, "nop"],
                other_fires,
                f"{kind} trigger on A, {'store' if load else 'load'} at A",
            )
            t.la("x8", f"{DATA}+16")
            sd.fire(t, mode, [same_w, "nop"], False, f"{kind} trigger on A, word {kind} at A+8")

        with_trigger(t, acc, low, f"{DATA}+8", body)

    modes(t, per)
    return t


A = f"{DATA}+32"  # 64-byte aligned + 32: an 8-byte-aligned address inside the data block


def lines_lohalf_mask(addr: str, mask_lo: int) -> list[str]:
    """x8 = (mask << XLEN/2) | (addr's low half): tdata2 for match=4 (mask_low); mask_lo is a small negative mask."""
    return [
        f"LA(x8, {addr})",
        "slli x8, x8, (__riscv_xlen/2)",
        "srli x8, x8, (__riscv_xlen/2)  // the low half of the address",
        f"li x5, {mask_lo}",
        "slli x5, x5, (__riscv_xlen/2)  // the mask in the high half",
        "or x8, x8, x5",
    ]


def lines_hihalf_mask(addr: str, mask_lo: int, flip: int = 0, clear: int = 0) -> list[str]:
    """x8 = (mask << XLEN/2) | value, value = ((addr's high half) ^ flip) & ~clear: tdata2 for match=5 (mask_high)."""
    out = [
        f"LA(x8, {addr})",
        "srli x8, x8, (__riscv_xlen/2)  // the high half of the address",
    ]
    if flip:
        out.append(f"xori x8, x8, {flip}")
    if clear:
        out.append(f"andi x8, x8, {~clear}")
    out += [f"li x5, {mask_lo}", "slli x5, x5, (__riscv_xlen/2)  // the mask in the high half", "or x8, x8, x5"]
    return out


def t2_kept(t: TestFile, acc: Acc, t2: str | list[str] | int, flag: str = "x6") -> None:
    """flag = 1 when the selected trigger's tdata2 reads back as t2 (a WARL legalization would change the range)."""
    acc.r("x7", "tdata2")
    sd.set_t2(t, t2)
    t.emit(f"sub {flag}, x7, x8")
    t.emit(f"seqz {flag}, {flag}")


# (rule, match value, rule text, plan description, armings: list of (tdata2, [(insn, offset from A, fires)]))
MATCHES = [
    (
        "Sdtrig_mcontrol6_match_equal",
        0,
        "Matches when any compare value equals {csr-tdata2}.",
        "tdata2 = A",
        [(A, [("lb", 0, True), ("lw", 0, True), ("lb", 1, False), ("lb", -1, False), ("lw", -4, False)])],
    ),
    (
        "Sdtrig_mcontrol6_match_napot",
        1,
        (
            "Matches when the top `M` bits of any compare value match the top `M` bits of {csr-tdata2}. `M` is "
            "`XLEN-1` minus the index of the least-significant bit containing 0 in {csr-tdata2}."
        ),
        (
            "tdata2 = A | 3 (an 8-byte range A..A+7; tdata2 must read back unchanged, otherwise the range is not "
            "supported and the case is skipped), then tdata2 = A (bit 0 = 0: the 2-byte range A..A+1, which every "
            "hart with NAPOT supports, norm:Sdtrig_mcontrol6_napot_range)"
        ),
        [
            (
                [f"LA(x8, {A})", "ori x8, x8, 3"],
                [("lb", 0, True), ("lb", 7, True), ("lw", 4, True), ("lb", 8, False), ("lb", -1, False)],
            ),
            ([f"LA(x8, {A})"], [("lb", 1, True), ("lb", 2, False)]),
        ],
    ),
    (
        "Sdtrig_mcontrol6_match_ge",
        2,
        "Matches when any compare value is greater than (unsigned) or equal to {csr-tdata2}.",
        "tdata2 = A",
        [(A, [("lb", 0, True), ("lb", 9, True), ("lw", 16, True), ("lb", -1, False), ("lw", -4, False)])],
    ),
    (
        "Sdtrig_mcontrol6_match_lt",
        3,
        "Matches when any compare value is less than (unsigned) {csr-tdata2}.",
        "tdata2 = A",
        [(A, [("lb", -1, True), ("lw", -4, True), ("lb", 0, False), ("lw", 0, False), ("lb", 9, False)])],
    ),
    (
        "Sdtrig_mcontrol6_match_mask_low",
        4,
        (
            "Matches when XLEN/2-1:0 of any compare value equals XLEN/2-1:0 of {csr-tdata2} after XLEN/2-1:0 of the "
            "compare value is ANDed with XLEN-1:XLEN/2 of {csr-tdata2}."
        ),
        (
            "tdata2 = (~7 << XLEN/2) | (low half of A): the low half of the address with bits 2:0 masked off must equal "
            "the low half of A"
        ),
        [(lines_lohalf_mask(A, -8), [("lb", 0, True), ("lb", 7, True), ("lb", 8, False), ("lb", -8, False)])],
    ),
    (
        "Sdtrig_mcontrol6_match_mask_high",
        5,
        (
            "Matches when XLEN-1:XLEN/2 of any compare value equals XLEN/2-1:0 of {csr-tdata2} after XLEN-1:XLEN/2 of "
            "the compare value is ANDed with XLEN-1:XLEN/2 of {csr-tdata2}."
        ),
        (
            "three armings: (a) mask all ones, value = high half of A; (b) mask all ones, value = (high half of A) ^ 1; "
            "(c) mask = ~1, value = (high half of A) & ~1"
        ),
        [
            (lines_hihalf_mask(A, -1), [("lb", 0, True), ("lb", 9, True)]),
            (lines_hihalf_mask(A, -1, flip=1), [("lb", 0, False)]),
            (lines_hihalf_mask(A, -2, clear=1), [("lb", 0, True)]),
        ],
    ),
    (
        "Sdtrig_mcontrol6_match_not_equal",
        8,
        "Matches when {mcontrol6-match} `=0` would not match.",
        "tdata2 = A",
        [(A, [("lb", 0, False), ("lw", 0, False), ("lb", 1, True), ("lw", -4, True)])],
    ),
    (
        "Sdtrig_mcontrol6_match_not_napot",
        9,
        "Matches when {mcontrol6-match} `=1` would not match.",
        "tdata2 = A | 3 (8-byte range A..A+7, skipped unless tdata2 reads back unchanged)",
        [([f"LA(x8, {A})", "ori x8, x8, 3"], [("lb", 0, False), ("lb", 7, False), ("lb", 8, True), ("lb", -1, True)])],
    ),
    (
        "Sdtrig_mcontrol6_match_not_mask_low",
        12,
        "Matches when {mcontrol6-match} `=4` would not match.",
        "tdata2 = (~7 << XLEN/2) | (low half of A)",
        [(lines_lohalf_mask(A, -8), [("lb", 0, False), ("lb", 7, False), ("lb", 8, True)])],
    ),
    (
        "Sdtrig_mcontrol6_match_not_mask_high",
        13,
        "Matches when {mcontrol6-match} `=5` would not match.",
        "two armings: (a) mask all ones, value = high half of A; (b) mask all ones, value = (high half of A) ^ 1",
        [
            (lines_hihalf_mask(A, -1), [("lb", 0, False)]),
            (lines_hihalf_mask(A, -1, flip=1), [("lb", 0, True), ("lb", 9, True)]),
        ],
    ),
]

MATCH_MUT = {
    "napot_one_byte_short": ("Sdtrig_mcontrol6_match_napot", "lb", 7),
    "ge_strict": ("Sdtrig_mcontrol6_match_ge", "lb", 0),
    "lt_inclusive": ("Sdtrig_mcontrol6_match_lt", "lb", 0),
    "mask_low_ignores_mask": ("Sdtrig_mcontrol6_match_mask_low", "lb", 7),
    "mask_high_ignores_mask": ("Sdtrig_mcontrol6_match_mask_high", "lb", 0),
    "not_equal_is_equal": ("Sdtrig_mcontrol6_match_not_equal", "lb", 1),
}
MUTANTS.update(
    {
        "napot_one_byte_short": "a NAPOT range of 2^n bytes covers only 2^n - 1 bytes (A+7 does not match)",
        "ge_strict": "match=2 compares greater-than instead of greater-or-equal",
        "lt_inclusive": "match=3 compares less-or-equal instead of less-than",
        "mask_low_ignores_mask": "match=4 ignores the mask (A+7 does not match)",
        "mask_high_ignores_mask": "match=5 compares the low half of the address",
        "not_equal_is_equal": "match=8 behaves as match=0",
    }
)


def t_match(rule: str, mval: int, text: str, t2desc: str, armings: list) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    checked = t2desc.startswith("tdata2 = A | 3") or "mask" in t2desc
    t.describe(
        source=XML,
        rule_text=text,
        context=TIMING + " Compare values are the lowest address of each load (select=0); only byte loads and "
        "aligned word loads are used, so the result does not depend on whether a hart also compares the other "
        "addresses an access touches. Range-style matches would also match the test's own loads in S-mode, so "
        "the trigger is enabled only in U (and VU with H). A = sd_data+32 (8-byte aligned).",
        plan=f"With an mcontrol6 load-address trigger, match={mval}, enabled in U (then VU with H), {t2desc}, each "
        "load below runs alone in a U-mode window:\n"
        + "\n".join(
            f"- {insn} at A{off:+d}: {'one breakpoint' if f else 'no trap'}" for _, cs in armings for insn, off, f in cs
        ),
    )

    def per(mode: str) -> None:
        low = LOAD | sd.MODEBITS6[mode] | sd.MATCH(mval)
        for t2, cases in armings:
            sd.probe(t, acc, [(MC6, low)], [t2])

            def run(t2: str | list[str] = t2, cases: list = cases) -> None:
                sd.arm(t, acc, MC6, low, t2)
                if checked:
                    t2_kept(t, acc, t2)
                else:
                    t.emit("li x6, 1")

                def go() -> None:
                    for insn, off, fires in cases:
                        mm = [k for k, v in MATCH_MUT.items() if v == (rule, insn, off)]
                        if mm and mut(mm[0]):
                            fires = not fires
                        t.la("x8", f"{A}{off:+d}")
                        nb = {"lb": 1, "lh": 2, "lw": 4, "ld": 8}[insn]
                        tv = ([0, f"{A}{off:+d}"] if nb == 1 or mval == 0 else (f"{A}{off:+d}", nb)) if fires else None
                        sd.fire(
                            t,
                            mode,
                            [f"{insn} x7, 0(x8)", "nop", "nop"],
                            fires,
                            f"match={mval}: {insn} at A{off:+d}",
                            tval=tv,
                        )

                sd.either(t, "x6", go)
                sd.disarm(t, acc)

            sd.either(t, "x1", run)

    modes(t, per, ("U", "VU"))
    return t


SIZES = [
    ("Sdtrig_mcontrol6_size_8bit", 1, "The trigger will only match against 8-bit memory accesses.", "lb"),
    (
        "Sdtrig_mcontrol6_size_16bit",
        2,
        "The trigger will only match against 16-bit memory accesses or execution of 16-bit instructions.",
        "lh",
    ),
    (
        "Sdtrig_mcontrol6_size_32bit",
        3,
        "The trigger will only match against 32-bit memory accesses or execution of 32-bit instructions.",
        "lw",
    ),
    (
        "Sdtrig_mcontrol6_size_64bit",
        5,
        "The trigger will only match against 64-bit memory accesses or execution of 64-bit instructions.",
        "ld",
    ),
]
MUTANTS["size_ignored"] = "a sized load trigger matches accesses of every size"
MUTANTS["size_exec_ignored"] = "a size=3 execute trigger does not match a 32-bit instruction"


def t_size(rule: str, sval: int, text: str, insn: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    others = [i for i in ("lb", "lh", "lw", "ld") if i != insn]
    t.describe(
        source=XML,
        rule_text=text,
        context=TIMING + " Size values other than 0 are optional (norm:Sdtrig_mcontrol6_size_support), so each "
        "configuration is probed first and the test passes vacuously without it. 48-, 80-, 96-, 112- and 128-bit "
        "accesses and instructions do not exist in the tested ISA.",
        plan=f"For U and S (and VU/VS with H), with an mcontrol6 load-address trigger (match=0, select=0, "
        f"size={sval}) on A = sd_data+32 enabled only in that mode: {insn} at A takes one breakpoint"
        + (" (RV64)" if insn == "ld" else "")
        + f"; {', '.join(others)} at A take no trap (ld on RV64 only)."
        + (" Then an execute trigger with size=3 on a 32-bit instruction fires." if sval == 3 else ""),
    )

    def per(mode: str) -> None:
        low = LOAD | sd.MODEBITS6[mode] | sd.SIZE(sval)

        def body() -> None:
            t.la("x8", A)
            for i in ("lb", "lh", "lw", "ld"):
                fires = i == insn or mut("size_ignored")

                def one(i: str = i, fires: bool = fires) -> None:
                    sd.fire(
                        t,
                        mode,
                        [f"{i} x7, 0(x8)", "nop", "nop"],
                        fires,
                        f"size={sval} load trigger: {i} at A",
                        tval=[0, A] if fires else None,
                    )

                if i == "ld":
                    with t.rv64_only():
                        one()
                else:
                    one()

        with_trigger(t, acc, low, A, body)
        if sval == 3:
            b = t.label(f"B_{mode}")

            def body2() -> None:
                fire_at(
                    t,
                    mode,
                    b,
                    ["addi x7, x0, 3", "nop", "nop"],
                    not mut("size_exec_ignored"),
                    "size=3 execute trigger on a 32-bit instruction",
                    tval=[0, b],
                )

            with_trigger(t, acc, EXEC | sd.MODEBITS6[mode] | sd.SIZE(3), b, body2)

    if insn == "ld":
        with t.rv64_only():
            modes(t, per)
    else:
        modes(t, per)
    return t


MUTANTS["mode_bits_ignored"] = "an mcontrol6 trigger fires in every mode, whatever its m/s/u/vs/vu bits"
MUTANTS["vu_uses_u_bit"] = "the u bit enables an mcontrol6 trigger in VU-mode too"


def t_modebit(mode_bit: str) -> SdFile:
    rule = f"Sdtrig_mcontrol6_{mode_bit.lower()}"
    t = new(rule)
    acc = Acc(t)
    names = {"S": "S/HS-mode", "U": "U-mode", "VS": "VS-mode", "VU": "VU-mode"}
    text = f"When set, enable this trigger in {names[mode_bit]}."
    text += {
        "S": " This bit is hard-wired to 0 if the hart does not support S-mode.",
        "U": " This bit is hard-wired to 0 if the hart does not support U-mode.",
        "VS": " This bit is hard-wired to 0 if the hart does not support virtualization mode.",
        "VU": " This bit is hard-wired to 0 if the hart does not support virtualization mode.",
    }[mode_bit]
    t.describe(
        source=XML,
        rule_text=text,
        context=TIMING + " The trigger is a store-address trigger on A = sd_data+32 (match=0), which no framework "
        "code uses.",
        plan=f"1. With only {mode_bit}={1} set: a sw to A in {mode_bit}-mode takes one breakpoint from {mode_bit}; "
        "in each other mode (U, S, VU, VS that exist) no trap.\n"
        f"2. With every mode bit except {mode_bit} that the hart keeps: a sw to A in {mode_bit}-mode takes no trap."
        + ("\n3. Without H, tdata1.vs/vu read 0 after writing 1 (hard-wired)." if mode_bit in ("VS", "VU") else ""),
    )
    allm = ["U", "S", "VS", "VU"]

    def run_all(only: str | None, bits: int) -> None:
        def body() -> None:
            t.la("x8", A)
            for m in allm:
                fires = (
                    (m == only)
                    or (mut("mode_bits_ignored") and m != only)
                    or (mut("vu_uses_u_bit") and m == "VU" and only == "U")
                )
                if only is None:
                    fires = mut("mode_bits_ignored")

                def one(m: str = m, fires: bool = fires) -> None:
                    sd.fire(
                        t,
                        m,
                        ["sw x7, 0(x8)", "nop", "nop"],
                        fires,
                        f"store trigger with {'only ' + only if only else 'all modes but ' + mode_bit}",
                        tval=[0, A] if fires else None,
                    )

                if only is None and m != mode_bit:
                    continue
                if m in ("VS", "VU"):
                    with t.only_if(H):
                        one()
                else:
                    one()

        with_trigger(t, acc, STORE | bits, A, body)

    def main_part() -> None:
        run_all(mode_bit, sd.MODEBITS6[mode_bit])
        others = sum(v for k, v in sd.MODEBITS6.items() if k not in (mode_bit, "M"))
        # the "all others" trigger: probe with the base bits that every S-boot hart keeps, then add VS/VU under H
        base = sum(sd.MODEBITS6[k] for k in ("U", "S") if k != mode_bit)
        with t.only_if(H):
            run_all(None, others)
        with t.only_if(f"!{H}"):
            run_all(None, base)

    if mode_bit in ("VS", "VU"):
        with t.only_if(H):
            main_part()
        with t.only_if(f"!{H}"):
            t.comment(f"without H, {mode_bit} is hard-wired to 0")
            sd.probe(t, acc, [(MC6, STORE | sd.U)], [A])

            def hw() -> None:
                t.emit(f"{rule}_hw:", 0)
                sd.select(t, acc)
                acc.w0("tdata1")
                sd.mk(t, "x8", MC6, STORE | sd.U | sd.MODEBITS6[mode_bit])
                acc.w("tdata1", "x8")
                acc.r("x7", "tdata1")
                acc.w0("tdata1")
                t.li("x5", sd.MODEBITS6[mode_bit])
                t.emit("and x7, x7, x5")
                t.check("x7", 0, f"{rule}_hw", f"tdata1.{mode_bit.lower()} reads 0 without H")

            sd.either(t, "x1", hw)
    else:
        main_part()
    return t


# ---------------------------------------------------------------- chains
MUTANTS.update(
    {
        "chain_ignored": "chain=1 is ignored: the second trigger of a chain fires on its own",
        "chain_first_action": "the action of a non-final chained trigger is taken when it matches alone",
        "chain_diff_insns": "a chain fires when its triggers match different instructions",
        "chain_tval_tdata2": "a chained breakpoint reports the load trigger's tdata2, not 0 or an accessed address",
    }
)
CHAIN_RULES = {
    "Sdtrig_mcontrol6_chain_enabled": (
        "While this trigger does not match, it prevents the trigger with the next index from matching.",
        (
            "T0 (chain=1) is a load-address trigger on A and T1 (chain=0) a load-address trigger on A+8: a load from "
            "A+8 matches only T1 and takes no trap."
        ),
    ),
    "Sdtrig_mcontrol6_chain_start": (
        (
            "A trigger chain starts on the first trigger with `chain`=1 after a trigger with `chain`=0, or simply on the "
            "first trigger if that has `chain`=1. It ends on the first trigger after that which has `chain`=0. This "
            "final trigger is part of the chain. The action on all but the final trigger is ignored. The action on that "
            "final trigger will be taken if and only if all the triggers in the chain match at the same time."
        ),
        (
            "T0 (chain=1) on A, T1 (chain=0) on A+8 (both load address): a load from A matches only T0, whose action is "
            "ignored (no trap); a load from A+8 matches only T1 (no trap); with T1 also on A, a load from A matches both and "
            "takes one breakpoint."
        ),
    ),
    "Sdtrig_mcontrol6_chain": (
        "A chain of triggers must only fire if every trigger in the chain was matched by the same instruction.",
        (
            "T0 (chain=1) is an execute trigger on instruction X, T1 (chain=0) a load trigger on A: running X (a nop) "
            "followed by a load from A takes no trap; running X = the load from A may take one breakpoint (whether an "
            "execute and a load match of one instruction are 'at the same time' is not settled). T0 (chain=1) and T1 "
            "load triggers on A: lw A takes one breakpoint; with T1 on A+8, lw A followed by lw A+8 takes none."
        ),
    ),
    "Sdtrig_mcontrol6_chained_faulting": (
        (
            "If multiple mcontrol6 triggers are chained then the faulting virtual address is the address which caused "
            "any of the chained triggers to fire."
        ),
        (
            "T0 (chain=1) execute trigger on X, T1 (chain=0) load trigger on A, X = lw from A: no breakpoint, or one "
            "with xtval 0, X or A (whether an execute match and a load match of one instruction are 'at the same time' "
            "is not settled, so both outcomes are accepted). With T0 and T1 both load-address triggers, match=2 (>=) on "
            "A: lw from A+4 takes one breakpoint with xtval 0 or one of A+4..A+7 (not tdata2)."
        ),
    ),
    "Sdtrig_mcontrol6_chain_disabled": (
        "When this trigger matches, the configured action is taken.",
        (
            "T0 (chain=0) load trigger on A and T1 (chain=0) load trigger on A+8: a load from A takes one breakpoint "
            "(T0 alone), and so does a load from A+8 (T1 alone)."
        ),
    ),
}


def t_chain(rule: str) -> SdFile:
    text, plan = CHAIN_RULES[rule]
    t = new(rule)
    acc = Acc(t)
    t.describe(
        source=XML,
        rule_text=text,
        context=TIMING + " Chains are optional: the test looks for two consecutive triggers that keep chain=1 in "
        "the first and passes vacuously without them. Triggers are enabled in U-mode only.",
        plan=plan + " The check runs in U-mode (and VU-mode with H).",
    )
    a8 = f"{A}+8"

    def per(mode: str) -> None:
        mb = sd.MODEBITS6[mode]
        ld = LOAD | mb
        ch = sd.CHAIN if not mut("chain_ignored") else 0
        xl = t.label(f"X_{mode}")
        if rule == "Sdtrig_mcontrol6_chain_disabled":
            sd.probe(t, acc, [(MC6, ld), (MC6, ld)], [A, a8])
        elif rule in ("Sdtrig_mcontrol6_chain", "Sdtrig_mcontrol6_chained_faulting"):
            sd.probe(t, acc, [(MC6, EXEC | mb | sd.CHAIN), (MC6, ld)], [xl, A])
        else:
            sd.probe(t, acc, [(MC6, ld | sd.CHAIN), (MC6, ld)], [A, a8])

        def run() -> None:
            if rule == "Sdtrig_mcontrol6_chain_enabled":
                sd.arm(t, acc, MC6, ld | ch, A)
                sd.arm(t, acc, MC6, ld, a8, k=1)
                t.la("x8", a8)
                sd.fire(
                    t, mode, ["lw x7, 0(x8)", "nop", "nop"], mut("chain_ignored"), "chain T0 on A, T1 on A+8: lw A+8"
                )
            elif rule == "Sdtrig_mcontrol6_chain_start":
                sd.arm(t, acc, MC6, ld | sd.CHAIN, A)
                sd.arm(t, acc, MC6, ld, a8, k=1)
                t.la("x8", A)
                sd.fire(
                    t,
                    mode,
                    ["lw x7, 0(x8)", "nop", "nop"],
                    mut("chain_first_action"),
                    "chain T0 on A, T1 on A+8: lw A (only T0 matches)",
                )
                t.la("x8", f"{A}+8")
                sd.fire(
                    t,
                    mode,
                    ["lw x7, 0(x8)", "nop", "nop"],
                    mut("chain_ignored"),
                    "chain T0 on A, T1 on A+8: lw A+8 (only T1 matches)",
                )
                sd.arm(t, acc, MC6, ld, A, k=1)
                t.la("x8", A)
                sd.fire(t, mode, ["lw x7, 0(x8)", "nop", "nop"], True, "chain T0 on A, T1 on A: lw A", tval=[0, A])
            elif rule == "Sdtrig_mcontrol6_chain_disabled":
                sd.arm(t, acc, MC6, ld, A)
                sd.arm(t, acc, MC6, ld, a8, k=1)
                t.la("x8", A)
                sd.fire(
                    t, mode, ["lw x7, 0(x8)", "nop", "nop"], True, "T0 on A, T1 on A+8 (no chain): lw A", tval=[0, A]
                )
                t.la("x8", a8)
                sd.fire(
                    t, mode, ["lw x7, 0(x8)", "nop", "nop"], True, "T0 on A, T1 on A+8 (no chain): lw A+8", tval=[0, a8]
                )
            elif rule == "Sdtrig_mcontrol6_chain":
                y = t.label(f"Y_{mode}")
                sd.arm(t, acc, MC6, EXEC | mb | ch, y)
                sd.arm(t, acc, MC6, ld, A, k=1)
                t.la("x8", A)
                fire_at(
                    t,
                    mode,
                    y,
                    ["nop  // X", "lw x7, 0(x8)", "nop", "nop"],
                    mut("chain_diff_insns") or mut("chain_ignored"),
                    "chain X (execute) + A (load): X = nop, then lw A",
                )
                sd.arm(t, acc, MC6, EXEC | mb | ch, xl)
                t.la("x8", A)
                fire_at(
                    t,
                    mode,
                    xl,
                    ["lw x7, 0(x8)  // X", "nop", "nop"],
                    None,
                    "chain X (execute) + A (load): X = lw A (may fire)",
                    tval=[0, xl, A],
                )
                sd.arm(t, acc, MC6, ld | sd.CHAIN, A)
                sd.arm(t, acc, MC6, ld | sd.SIZE(0), A, k=1)
                t.la("x8", A)
                sd.fire(t, mode, ["lw x7, 0(x8)", "nop", "nop"], True, "chain A (load) + A (load): lw A", tval=[0, A])
                t.la("x8", f"{A}+8")
                sd.arm(t, acc, MC6, ld, f"{A}+8", k=1)
                t.la("x8", A)
                sd.fire(
                    t,
                    mode,
                    ["lw x7, 0(x8)", "lw x7, 8(x8)", "nop", "nop"],
                    mut("chain_diff_insns"),
                    "chain A (load) + A+8 (load): lw A then lw A+8",
                )
            else:
                sd.arm(t, acc, MC6, EXEC | mb | sd.CHAIN, xl)
                sd.arm(t, acc, MC6, ld, A, k=1)
                t.la("x8", A)
                fire_at(
                    t,
                    mode,
                    xl,
                    ["lw x7, 0(x8)  // X", "nop", "nop"],
                    None,
                    "chain X (execute) + A (load): X = lw A (may fire)",
                    tval=[0, xl, A],
                )
                sd.arm(t, acc, MC6, ld | sd.CHAIN | sd.MATCH(2), A)
                sd.arm(t, acc, MC6, ld | sd.MATCH(2), A, k=1)
                t.la("x8", f"{A}+4")
                sd.fire(
                    t,
                    mode,
                    ["lw x7, 0(x8)", "nop", "nop"],
                    True,
                    "chain >= A (load) + >= A (load): lw A+4",
                    tval=[A] if mut("chain_tval_tdata2") else (f"{A}+4", 4),
                )
            sd.disarm(t, acc, k=1)
            sd.disarm(t, acc)

        sd.either(t, "x1", run)

    modes(t, per, ("U", "VU"))
    return t


# ---------------------------------------------------------------- hit bits
MUTANTS.update(
    {
        "hit_set_on_other": "a trigger that did not fire has its hit field set",
        "hit_sticky_once": "the hit field is set only on the first firing after reset",
        "hit_before_means_next": "hit = 1 (before) goes with xepc = the next instruction",
        "multiple_one_hit": "when two triggers fire on one instruction, only the first one's hit field is set",
    }
)
HIT_RULES = {
    "Sdtrig_mcontrol6_hit0": "If they are implemented, {mcontrol6-hit1} (MSB) and {mcontrol6-hit0} (LSB) combine "
    "into a single 2-bit field. The TM updates this field when the trigger fires.",
    "Sdtrig_mcontrol6_hit0_1": "`xepc` or {csr-dpc} (depending on {mcontrol6-action}) must be set to the virtual "
    "address of the instruction that matched. (hit = 1, before)",
    "Sdtrig_mcontrol6_hit0_2": "`xepc` or {csr-dpc} (depending on {mcontrol6-action}) must be set to the virtual "
    "address of the next instruction that must be executed to preserve the program flow. (hit = 2, after)",
    "Sdtrig_mcontrol6_hit0_3": "`xepc` or {csr-dpc} (depending on {mcontrol6-action}) must be set to the virtual "
    "address of the next instruction that must be executed to preserve the program flow. (hit = 3, immediately "
    "after)",
    "Sdtrig_multiple_fires": "When multiple triggers in the same priority fire at once, {mcontrol-hit} (if "
    "implemented) is set for all of them.",
}
SAVE = f"{DATA}+120"  # spill slots at the end of the data block
SAVE2 = f"{DATA}+112"


def save(t: TestFile, reg: str, slot: str) -> None:
    t.la("x5", slot)
    t.emit(f"SREG {reg}, 0(x5)")


def restore(t: TestFile, reg: str, slot: str) -> None:
    t.la("x5", slot)
    t.emit(f"LREG {reg}, 0(x5)")


def t_hit(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    multi = rule == "Sdtrig_multiple_fires"
    hit0 = rule == "Sdtrig_mcontrol6_hit0"
    want = {"Sdtrig_mcontrol6_hit0_1": 1, "Sdtrig_mcontrol6_hit0_2": 2, "Sdtrig_mcontrol6_hit0_3": 3}.get(rule)
    ctx = (
        TIMING + " The hit field is optional and software writes of 1 may be legalized to 0, so whether it is "
        "implemented is seen only from a trigger firing: a hit field that becomes nonzero when a trigger fires alone "
        "is implemented. Values: 0 = did not fire, 1 = before (xepc = the matching instruction), 2 = after (xepc "
        "past the instruction after it), 3 = immediately after (xepc = the next instruction)."
    )
    if multi:
        plan = (
            "In U, S, VS and VU (VS/VU with H), with two load-address triggers T0 and T1 (same priority):\n"
            "1. T0 on A, T1 on an unused address: lw A fires T0 alone; record whether T0's hit field became nonzero;\n"
            "2. T0 on the unused address, T1 on A: lw A fires T1 alone; record T1's hit field the same way;\n"
            "3. both on A: lw A takes one breakpoint, and each trigger whose hit field became nonzero alone has a "
            "nonzero hit field again."
        )
    elif hit0:
        plan = (
            "In U, S, VS and VU (VS/VU with H), T0 is a load-address trigger on A and T1 one on an unused address:\n"
            "1. lw A fires T0; T1's hit field stays 0 (it did not fire);\n"
            "2. tdata1 of T0 is rewritten with hit = 0 and a load from another address runs: T0's hit field stays "
            "0;\n"
            "3. lw A fires T0 again: its hit field is nonzero after the second firing exactly when it was after the "
            "first (the TM updates it at every firing)."
        )
    else:
        plan = (
            f"In U, S, VS and VU (VS/VU with H), an execute trigger on the window's first instruction and a "
            f"load-address trigger on A (lw A first in its window) each fire once; when the trigger's hit field "
            f"then reads {want}, xepc must be "
            + {
                0: "",
                1: "the matching instruction.",
                2: "beyond the instruction after the matching one.",
                3: "the instruction after the matching one.",
            }[want or 0]
        )
    t.describe(source=SRC if multi else XML, rule_text=HIT_RULES[rule], context=ctx, plan=plan)
    other = f"{DATA}+96"

    def per(mode: str) -> None:
        mb = sd.MODEBITS6[mode]
        kinds: list[tuple[str, int, str | None, list[str]]] = [("load", LOAD | mb, A, ["lw x7, 0(x8)", "nop", "nop"])]
        if want:
            kinds.insert(0, ("execute", EXEC | mb, None, ["addi x7, x0, 1", "nop", "nop"]))
        for kind, low, t2, body in kinds:
            lab = t.label(f"I_{mode}")
            t2v = t2 or lab
            tv = [0, lab] if kind == "execute" else [0, A]

            def shot(desc: str, at: str | None = None, body: list = body, tv: list = tv) -> None:
                t.la("x8", A)
                if at:
                    fire_at(t, mode, at, body, True, desc, off="x9", tval=tv)
                else:
                    sd.fire(t, mode, body, True, desc, off="x9", tval=tv)
                restore(t, "x1", SAVE)

            def hitof(dst: str, k: int = 0) -> None:
                sd.read_tdata1(t, acc, "x7", k=k)
                sd.hit6(t, dst, "x7")

            if want:

                def run1(low: int = low, t2v: str = t2v, lab: str = lab, kind: str = kind) -> None:
                    save(t, "x1", SAVE)
                    sd.arm(t, acc, MC6, low, t2v)
                    shot(f"{kind} trigger", at=lab)
                    hitof("x6")
                    t.comment(f"only hit = {want} is checked against xepc here")
                    t.emit(f"addi x13, x6, -{want}")
                    t.emit("seqz x13, x13")
                    t.emit("neg x13, x13  // all ones when hit == want")
                    t.emit(f"and x6, x6, x13  // hit, or 0 when hit != {want}")
                    sd.hit_epc_ok(t, "x6", "x9")
                    if mut("hit_before_means_next") and want == 1:
                        t.emit("addi x13, x9, -4")
                        t.emit("seqz x13, x13")
                        t.emit("seqz x14, x6")
                        t.emit("or x15, x13, x14")
                    t.check_bool("x15", lab, f"{kind} trigger in {mode}-mode: hit = {want} agrees with xepc")
                    sd.disarm(t, acc)

                with_probe(t, acc, [(MC6, low)], [t2v], run1)
            elif hit0:

                def run2(low: int = low, lab: str = lab) -> None:
                    save(t, "x1", SAVE)
                    sd.arm(t, acc, MC6, low, A)
                    sd.arm(t, acc, MC6, low, other, k=1)
                    shot("load trigger T0 (T1 on an unused address)", at=lab)
                    hitof("x6")
                    save(t, "x6", SAVE2)
                    hitof("x6", k=1)
                    if mut("hit_set_on_other"):
                        t.emit("ori x6, x6, 1")
                    t.check("x6", 0, lab, f"load trigger in {mode}-mode: T1, which did not fire, has hit = 0")
                    sd.arm(t, acc, MC6, low, A)
                    t.la("x8", other)
                    sd.fire(t, mode, ["lw x7, 4(x8)", "nop"], False, "T0 rearmed with hit = 0, unrelated load")
                    restore(t, "x1", SAVE)
                    hitof("x6")
                    t.check("x6", 0, lab, f"load trigger in {mode}-mode: T0's hit stays 0 without firing")
                    shot("load trigger T0 fires again")
                    hitof("x6")
                    if mut("hit_sticky_once"):
                        t.emit("li x6, 0")
                    restore(t, "x7", SAVE2)
                    t.emit("snez x6, x6")
                    t.emit("snez x7, x7")
                    t.emit("sub x6, x6, x7")
                    t.check(
                        "x6",
                        0,
                        lab,
                        f"load trigger in {mode}-mode: hit nonzero after the "
                        "second firing iff after the first (difference)",
                    )
                    sd.disarm(t, acc, k=1)
                    sd.disarm(t, acc)

                with_probe(t, acc, [(MC6, low), (MC6, low)], [A, other], run2)
            else:

                def run3(low: int = low, lab: str = lab) -> None:
                    save(t, "x1", SAVE)
                    sd.arm(t, acc, MC6, low, A)
                    sd.arm(t, acc, MC6, low, other, k=1)
                    shot("T0 on A alone", at=lab)
                    hitof("x6")
                    t.emit("snez x6, x6")
                    save(t, "x6", SAVE2)
                    sd.arm(t, acc, MC6, low, other)
                    sd.arm(t, acc, MC6, low, A, k=1)
                    shot("T1 on A alone")
                    hitof("x6", k=1)
                    t.emit("snez x6, x6")
                    save(t, "x6", f"{DATA}+104")
                    sd.arm(t, acc, MC6, low, A)
                    sd.arm(t, acc, MC6, low, A, k=1)
                    shot("T0 and T1 both on A")
                    for k, slot in ((0, SAVE2), (1, f"{DATA}+104")):
                        hitof("x6", k=k)
                        if mut("multiple_one_hit") and k == 1:
                            t.emit("li x6, 0")
                        restore(t, "x7", slot)
                        t.emit("snez x6, x6")
                        t.emit("xori x7, x7, 1")
                        t.emit("or x15, x6, x7  // hit set, or no hit when firing alone")
                        t.check_bool(
                            "x15",
                            lab,
                            f"lw A in {mode}-mode with T0 and T1 on A: T{k}'s hit field is set when it is implemented",
                        )
                    sd.disarm(t, acc, k=1)
                    sd.disarm(t, acc)

                with_probe(t, acc, [(MC6, low), (MC6, low)], [A, other], run3)

    modes(t, per)
    return t


def with_probe(t: TestFile, acc: Acc, cfgs: list, t2s: list, run: Callable[[], object]) -> None:
    sd.probe(t, acc, cfgs, t2s)
    sd.either(t, "x1", run)


# ---------------------------------------------------------------- xtval
MUTANTS["tval_is_tdata2"] = "the breakpoint's xtval is tdata2 instead of the address accessed"


def t_faulting() -> SdFile:
    t = new("Sdtrig_mcontrol6_faulting_address")
    acc = Acc(t)
    t.describe(
        source=XML,
        rule_text="The faulting virtual address for an mcontrol6 trigger with {mcontrol6-action}=0 is the address "
        "being accessed and which caused that trigger to fire.",
        context=TIMING + " The Privileged Spec allows xtval = 0 for breakpoints (norm:Sdtrig_mcontrol6_breakpoint). "
        "For a multi-byte access, any accessed byte that satisfies the match is an address that caused the trigger "
        "to fire (riscv-debug-spec#1132).",
        issues="https://github.com/riscv/riscv-debug-spec/issues/1132 (which address a range trigger reports for an "
        "access that crosses the boundary): any address accessed that satisfies the match.",
        plan="In U-mode (and VU with H), so tdata2 differs from the address accessed:\n"
        "1. load trigger, match=2 (>=) on A: lb at A+5 reports xtval 0 or A+5; lw at A+16 reports 0 or one of "
        "A+16..A+19;\n"
        "2. store trigger, match=1 (NAPOT 8 bytes at A): sb at A+6 reports 0 or A+6;\n"
        "3. execute trigger, match=1 (NAPOT, tdata2 = X|1: the 4 bytes at X) on the window's first instruction X: "
        "xtval 0 or X.",
    )

    def per(mode: str) -> None:
        mb = sd.MODEBITS6[mode]

        def ge() -> None:
            for insn, off, nb in (("lb", 5, 1), ("lw", 16, 4)):
                t.la("x8", f"{A}+{off}")
                tv = [0, f"{A}+{off}"] if nb == 1 else (f"{A}+{off}", nb)
                if mut("tval_is_tdata2"):
                    tv = [A]
                sd.fire(
                    t, mode, [f"{insn} x7, 0(x8)", "nop", "nop"], True, f"load trigger >= A: {insn} A+{off}", tval=tv
                )

        with_trigger(t, acc, LOAD | mb | sd.MATCH(2), A, ge)
        nap = [f"LA(x8, {A})", "ori x8, x8, 3"]
        sd.probe(t, acc, [(MC6, STORE | mb | sd.MATCH(1))], [nap])

        def napot() -> None:
            sd.arm(t, acc, MC6, STORE | mb | sd.MATCH(1), nap)
            t2_kept(t, acc, nap)

            def go() -> None:
                t.la("x8", f"{A}+6")
                sd.fire(
                    t,
                    mode,
                    ["sb x7, 0(x8)", "nop", "nop"],
                    True,
                    "store trigger NAPOT A..A+7: sb A+6",
                    tval=[A] if mut("tval_is_tdata2") else [0, f"{A}+6"],
                )

            sd.either(t, "x6", go)
            sd.disarm(t, acc)

        sd.either(t, "x1", napot)
        x = t.label(f"X_{mode}")
        xn = [f"LA(x8, {x})", "ori x8, x8, 1  // NAPOT: the 4 bytes X..X+3"]
        sd.probe(t, acc, [(MC6, EXEC | mb | sd.MATCH(1))], [xn])

        def ex() -> None:
            sd.arm(t, acc, MC6, EXEC | mb | sd.MATCH(1), xn)
            t2_kept(t, acc, xn)

            def go() -> None:
                fire_at(
                    t,
                    mode,
                    x,
                    ["addi x7, x0, 7", "nop", "nop"],
                    True,
                    "execute trigger NAPOT X..X+3: X runs",
                    tval=[x, "0x1"] if mut("tval_is_tdata2") else [0, x],
                )

            sd.either(t, "x6", go)
            sd.disarm(t, acc)

        sd.either(t, "x1", ex)

    modes(t, per, ("U", "VU"))
    return t


# ---------------------------------------------------------------- priority
MUTANTS.update(
    {
        "illegal_before_exec_bp": "an illegal instruction takes priority over an execute-address breakpoint",
        "misaligned_before_load_bp": "a load-address-misaligned exception takes priority over a load-address "
        "breakpoint",
        "load_bp_before_exec_bp": "a load-address breakpoint takes priority over an execute-address breakpoint on the "
        "same instruction",
    }
)


def t_priority() -> SdFile:
    t = new("Sdtrig_priority")
    acc = Acc(t)
    t.describe(
        source=SRC,
        rule_text="Priorities in the table are separated by horizontal lines, so e.g. etrigger and itrigger have the "
        "same priority. If this table contradicts the table in the Privileged Spec, then the latter takes "
        "precedence.",
        context="Synchronous exception priority (highest first): etrigger/icount/itrigger/after-triggers; execute "
        "address before; instruction page/access faults; execute data before; illegal, virtual, misaligned "
        "instruction, ecall, ebreak and load/store address before; load/store misaligned (optionally) and faults; "
        "load data before. The table applies only to precise triggers (norm:Sdtrig_non_precise_priority), so each "
        "case first measures the trigger's timing on a harmless instruction: when it fires before that instruction "
        "(xepc = the instruction), the priority is checked; otherwise cases 1-2 are skipped and case 3 accepts either "
        "trigger's xtval (equal-priority 'after' triggers: which sets xtval is UNSPECIFIED, norm:Sdtrig_tval).",
        plan="In U-mode (and VU with H):\n"
        "1. execute-address trigger on an instruction that is illegal in U (csrr mstatus): one breakpoint (cause 3), "
        "xepc = the instruction, not an illegal-instruction trap;\n"
        "2. load-address trigger on A+1 and lw from A+1 (misaligned): one breakpoint, not a misaligned or access "
        "fault (a hart without misaligned support must still report the breakpoint);\n"
        "3. execute trigger on X = lw A and load trigger on A: one breakpoint; when the execute trigger alone fires "
        "before its instruction, xtval is 0 or X (the execute trigger) and the load trigger's hit field stays 0, "
        "otherwise xtval is 0, X or A.",
    )

    def per(mode: str) -> None:
        mb = sd.MODEBITS6[mode]
        p = t.label(f"P_{mode}")
        q = t.label(f"Q_{mode}")

        def c1() -> None:
            sd.arm(t, acc, MC6, EXEC | mb, p)
            fire_at(
                t, mode, p, ["addi x7, x0, 1", "nop", "nop"], True, "execute trigger on addi (timing probe)", off="x9"
            )
            t.emit("seqz x9, x9  // 1: fires before the instruction")
            sd.arm(t, acc, MC6, EXEC | mb, q)

            def precise() -> None:
                lab, _ = sd.fire(
                    t,
                    mode,
                    [f"{q}:", "csrr x7, mstatus  // illegal in U", "nop", "nop"],
                    True,
                    "execute trigger on an illegal instruction",
                    epc=None,
                )
                del lab
                t.emit("AI_LOG(x15, TRAPLOG_CAUSE)", 10)
                t.check(
                    "x15",
                    2 if mut("illegal_before_exec_bp") else 3,
                    q,
                    f"execute trigger on an illegal instruction in {mode}-mode: breakpoint (3) wins over illegal",
                )
                t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
                t.check("x15", q, q, f"execute trigger on an illegal instruction in {mode}-mode: xepc")

            def imprecise() -> None:
                t.comment("imprecise execute triggers: not checked")

            sd.either(t, "x9", precise, imprecise)

        with_trigger(t, acc, EXEC | mb, p, c1)

        a1 = f"{A}+1"

        def c2() -> None:
            sd.arm(t, acc, MC6, LOAD | mb, A)
            t.la("x8", A)
            sd.fire(t, mode, ["lw x7, 0(x8)", "nop", "nop"], True, "load trigger on A (timing probe)", off="x9")
            t.emit("seqz x9, x9")
            sd.arm(t, acc, MC6, LOAD | mb, a1)

            def precise() -> None:
                t.la("x8", a1)
                r = t.label(f"R_{mode}")
                sd.resume(t, r)
                t.allow(1)
                if mode != t.cur:
                    t.enter(mode)
                lab = t.label(f"mis_{mode}")
                t.emit(f"{lab}:", 0)
                t.emit("lw x7, 0(x8)  // misaligned")
                t.emit("nop")
                t.emit(f"{r}:", 0)
                if mode != t.cur:
                    t.leave()
                sd.clear_resume(t)
                t.emit("AI_OUTCOME", 20)
                t.check("x13", 1, lab, f"misaligned lw A+1 with a load trigger on A+1 in {mode}-mode: one trap")
                t.check(
                    "x14",
                    4 if mut("misaligned_before_load_bp") else 3,
                    lab,
                    f"misaligned lw A+1 with a load trigger on A+1 in {mode}-mode: breakpoint (3) wins",
                )

            sd.either(t, "x9", precise)

        with_trigger(t, acc, LOAD | mb, A, c2)

        x = t.label(f"X_{mode}")
        sd.probe(t, acc, [(MC6, EXEC | mb), (MC6, LOAD | mb)], [x, A])

        def c3() -> None:
            save(t, "x1", SAVE)
            h = t.label(f"H_{mode}")
            sd.arm(t, acc, MC6, EXEC | mb, h)
            fire_at(
                t, mode, h, ["addi x7, x0, 1", "nop", "nop"], True, "execute trigger alone (timing probe)", off="x9"
            )
            t.emit("seqz x9, x9  // 1: the execute trigger fires before its instruction")
            save(t, "x9", SAVE2)
            restore(t, "x1", SAVE)
            sd.arm(t, acc, MC6, EXEC | mb, x)
            sd.arm(t, acc, MC6, LOAD | mb, A, k=1)
            t.la("x8", A)
            fire_at(t, mode, x, ["lw x7, 0(x8)", "nop", "nop"], True, "execute trigger on X = lw A, load trigger on A")
            t.emit("AI_LOG(x6, TRAPLOG_TVAL)", 10)
            restore(t, "x9", SAVE2)

            def before() -> None:
                t.check(
                    "x6",
                    [A] if mut("load_bp_before_exec_bp") else [0, x],
                    x,
                    f"execute (before) + load trigger on one lw in {mode}-mode: xtval is the execute trigger's",
                )
                restore(t, "x1", SAVE)
                sd.read_tdata1(t, acc, "x7", k=1)
                sd.hit6(t, "x7", "x7")
                t.check("x7", 0, x, f"execute + load trigger on one lw in {mode}-mode: the load trigger did not fire")

            def after() -> None:
                t.check(
                    "x6",
                    [0, x, A],
                    x,
                    f"execute (after) + load trigger on one lw in {mode}-mode: xtval is 0, X "
                    "or A (either trigger may be reported)",
                )

            sd.either(t, "x9", before, after)
            restore(t, "x1", SAVE)
            sd.disarm(t, acc, k=1)
            sd.disarm(t, acc)

        sd.either(t, "x1", c3)

    modes(t, per, ("U", "VU"))
    return t


# ---------------------------------------------------------------- tdata CSR semantics (T-SBI, M-mode accesses)
MUTANTS.update(
    {
        "write0_keeps_type": "writing 0 to tdata1 leaves the trigger's configuration in place",
        "write0_still_fires": "writing 0 to tdata1 does not disable the trigger",
        "disabled_tdata2_masked": "a disabled trigger's tdata2 drops the low 2 bits of an address",
        "tdata2_truncated": "tdata2 keeps only 32 bits of an address on RV64 (or drops bit 0)",
        "tdata_write_crosses": "writing tdata2 of one trigger changes the selected trigger's tdata1",
        "dmode_writable": "M-mode can set tdata1.dmode",
        "action1_kept": "tdata1 keeps action=1 with dmode=0",
        "type0_keeps_data": "a type-0 tdata1 keeps the written data bits",
        "reserved_type_kept": "a reserved tdata1.type (8..14) reads back as written",
        "size0_dropped": "mcontrol6 size=0 is not supported",
        "napot_allones_kept": "an all-ones NAPOT tdata2 reads back unchanged",
        "napot_range_short": "a supported NAPOT range of 2^j bytes does not include its last byte",
        "select_data_sext": "a byte load data trigger compares the sign-extended value loaded",
        "comparisons_full_tdata2": "a size=8 data trigger compares all of tdata2",
    }
)


def tdata1_type(t: TestFile, reg: str, dst: str) -> None:
    t.emit(f"srli {dst}, {reg}, {sd.TYPE_SHIFT}  // type")


def t_write0() -> SdFile:
    t = new("Sdtrig_tdata1_write0")
    acc = Acc(t)
    t.describe(
        source=XML,
        rule_text="Writing 0 to this register must result in a trigger that is disabled.",
        context="A disabled trigger reads type 0 (no trigger) or 15 (disabled); a trigger that supports several types "
        "should use 15 (norm:Sdtrig_tdata1_multiple_types, a recommendation). A trigger whose type is not writable "
        "(norm:Sdtrig_tinfo_optional) may keep its type with every enable bit cleared, which also disables it.",
        plan="For an mcontrol6 execute trigger on X enabled in U, and (when supported) an icount trigger with count=1 "
        "enabled in U: arm it, write tdata1 = 0, then\n1. tdata1.type reads 0 or 15, or the same type with all mode and "
        "execute/load/store bits clear;\n2. a U-mode window "
        "that starts at X (and retires several instructions) takes no trap.",
    )
    x = t.label("X")

    def disabled_ok(typ: int, enables: int, desc: str) -> None:
        """x7 = tdata1 after writing 0: type 0 or 15, or the same type with every enable bit clear."""
        if mut("write0_keeps_type"):
            sd.mk(t, "x7", typ, enables)
        t.emit(f"srli x6, x7, {sd.TYPE_SHIFT}")
        t.emit("seqz x15, x6  // type 0")
        t.emit("addi x13, x6, -15")
        t.emit("seqz x13, x13")
        t.emit("or x15, x15, x13  // or 15")
        t.emit(f"addi x13, x6, -{typ}")
        t.emit("seqz x13, x13  // or the same type ...")
        t.li("x14", enables)
        t.emit("and x14, x14, x7")
        t.emit("seqz x14, x14  // ... with every enable bit clear")
        t.emit("and x13, x13, x14")
        t.emit("or x15, x15, x13")
        t.check_bool("x15", x, f"{desc}: tdata1 after writing 0 is a disabled trigger")

    def body() -> None:
        acc.w0("tdata1")
        if mut("write0_still_fires"):
            sd.mk(t, "x8", MC6, EXEC | sd.U)
            acc.w("tdata1", "x8")
        acc.r("x7", "tdata1")
        disabled_ok(MC6, sd.M | sd.S | sd.U | sd.VS | sd.VU | EXEC | LOAD | STORE, "mcontrol6")
        fire_at(t, "U", x, ["addi x7, x0, 1", "nop", "nop"], mut("write0_still_fires"), "disabled execute trigger on X")

    with_trigger(t, acc, EXEC | sd.U, x, body)
    sd.probe(t, acc, [(sd.IC, sd.IC_U | sd.COUNT(1))])

    def ic() -> None:
        sd.arm(t, acc, sd.IC, sd.IC_U | sd.COUNT(1))
        acc.w0("tdata1")
        acc.r("x7", "tdata1")
        disabled_ok(sd.IC, sd.IC_M | sd.IC_S | sd.IC_U | sd.IC_VS | sd.IC_VU, "icount")
        sd.fire(t, "U", ["nop", "nop", "nop", "nop"], False, "disabled icount trigger")

    sd.either(t, "x1", ic)
    return t


def t_tdata2_disabled(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    text = {
        "Sdtrig_disable_trig": "To help with this situation, it is guaranteed that writing 0 to {csr-tdata1} disables "
        "the trigger, and leaves it in a state where {csr-tdata2} and {csr-tdata3} can be written with any value that "
        "makes sense for any trigger type supported by this trigger.",
        "Sdtrig_tdata2_disabled": "If the trigger is disabled, then this register can be written with any value "
        "supported by any of the trigger types supported by this trigger.",
        "Sdtrig_tdata2_addr_sz1": "For address matches without a mask, {csr-tdata2} must be able to hold all valid "
        "addresses in all supported translation modes. That means that after writing any of these valid addresses, "
        "the exact same value XLEN-wide value is read back, including any high bits.",
    }[rule]
    armed = rule == "Sdtrig_tdata2_addr_sz1"
    t.describe(
        source=SRC,
        rule_text=text,
        context="Addresses of the test's own code and data are valid physical (and, with satp = bare, virtual) "
        "addresses, which an mcontrol6 address trigger (match=0) supports. tdata3 is optional, so only tdata2 is "
        "checked.",
        plan=(
            "With an mcontrol6 load trigger (match=0) armed"
            if armed
            else "After tdata1 = 0 on a trigger that supports mcontrol6"
        )
        + ", write tdata2 = each of: a code address, A, A+1, A+3, A+7 and the trap log "
        "address; each reads back exactly. "
        + (
            "Then a lw from the last address written (A+4-aligned data) still fires."
            if armed
            else "Then tdata1 = mcontrol6 load trigger on the last value: tdata2 is unchanged."
        ),
    )
    vals = [t.label("code"), A, f"{A}+1", f"{A}+3", f"{A}+7", "rvtest_trap_log"]

    def body() -> None:
        if not armed:
            acc.w0("tdata1")
        for v in vals:
            t.la("x6", v)
            acc.w("tdata2", "x6")
            acc.r("x7", "tdata2")
            if mut("disabled_tdata2_masked") and not armed:
                t.emit("andi x6, x6, -4")
            if mut("tdata2_truncated") and armed:
                t.emit("andi x6, x6, -2")
            t.emit("sub x7, x7, x6")
            t.check("x7", 0, vals[0], f"tdata2 = {v} reads back exactly (difference)")
        if armed:
            sd.select(t, acc)
            t.la("x6", A)
            acc.w("tdata2", "x6")
            t.la("x8", A)
            sd.fire(t, "U", ["lw x7, 0(x8)", "nop", "nop"], True, "load trigger on A after the writes", tval=[0, A])
        else:
            sd.mk(t, "x8", MC6, LOAD | sd.U)
            acc.w("tdata1", "x8")
            acc.r("x7", "tdata2")
            t.la("x6", vals[-1])
            t.emit("sub x7, x7, x6")
            t.check("x7", 0, vals[0], "tdata2 unchanged by writing tdata1 (difference)")

    t.emit(f"{vals[0]}:", 0)
    with_trigger(t, acc, LOAD | sd.U, A, body)
    return t


def t_tdata_write() -> SdFile:
    t = new("Sdtrig_tdata_write")
    acc = Acc(t)
    t.describe(
        source=SRC,
        rule_text="Writes to one `tdata` register must not modify the contents of other `tdata` registers, nor the "
        "configuration of any trigger besides the one that is currently selected.",
        plan="T0 and T1 are consecutive triggers that support mcontrol6. T0 = load trigger on A (U), T1 = load "
        "trigger on A+8 (U). Read T0's tdata1 and T1's tdata1.\n"
        "1. With T1 selected, write its tdata2 = A+16: T1's tdata1 is unchanged.\n"
        "2. Write T1's tdata1 = store trigger on A+16: T1's tdata2 is still A+16.\n"
        "3. Write T1's tdata1 = 0. Select T0: its tdata1 and tdata2 are unchanged, and lw A in U fires.",
    )
    lab = t.label("tw")

    def run() -> None:
        save(t, "x1", SAVE)
        sd.arm(t, acc, MC6, LOAD | sd.U, A)
        sd.arm(t, acc, MC6, LOAD | sd.U, f"{A}+8", k=1)
        sd.read_tdata1(t, acc, "x9")
        save(t, "x9", SAVE2)
        sd.select(t, acc, k=1)
        acc.r("x9", "tdata1")
        t.la("x6", f"{A}+16")
        acc.w("tdata2", "x6")
        acc.r("x7", "tdata1")
        if mut("tdata_write_crosses"):
            t.emit("addi x7, x7, 1")
        t.emit("sub x7, x7, x9")
        t.emit(f"{lab}:", 0)
        t.check("x7", 0, lab, "T1.tdata1 unchanged by writing T1.tdata2 (difference)")
        sd.mk(t, "x8", MC6, STORE | sd.U)
        acc.w("tdata1", "x8")
        acc.r("x7", "tdata2")
        t.la("x6", f"{A}+16")
        t.emit("sub x7, x7, x6")
        t.check("x7", 0, lab, "T1.tdata2 unchanged by writing T1.tdata1 (difference)")
        acc.w0("tdata1")
        sd.read_tdata1(t, acc, "x7")
        restore(t, "x9", SAVE2)
        t.emit("sub x7, x7, x9")
        t.check("x7", 0, lab, "T0.tdata1 unchanged by writes to T1 (difference)")
        acc.r("x7", "tdata2")
        t.la("x6", A)
        t.emit("sub x7, x7, x6")
        t.check("x7", 0, lab, "T0.tdata2 unchanged by writes to T1 (difference)")
        t.la("x8", A)
        sd.fire(t, "U", ["lw x7, 0(x8)", "nop", "nop"], True, "T0 still fires on lw A", tval=[0, A])
        restore(t, "x1", SAVE)
        sd.disarm(t, acc)

    with_probe(t, acc, [(MC6, LOAD | sd.U), (MC6, LOAD | sd.U)], [A, f"{A}+8"], run)
    return t


def t_dmode(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    text = {
        "Sdtrig_tdata1_dmode_writable": "This bit is only writable from Debug Mode.",
        "Sdtrig_tdata1_dmode_0": "Both Debug and M-mode can write the `tdata` registers at the selected {csr-tselect}.",
        "Sdtrig_action1": "Enter Debug Mode. {csr-dpc} must contain the virtual address of the next instruction that "
        "must be executed to preserve the program flow. This action is only legal when the trigger's dmode is 1. "
        "Since {csr-tdata1} is WARL, hardware must prevent it from containing {tdata1-dmode}=0 and action=1. This "
        "action can only be supported if `Sdext` is implemented on the hart.",
    }[rule]
    t.describe(
        source=SRC if rule == "Sdtrig_action1" else XML,
        rule_text=text,
        context="The tests run without a debugger: T-SBI performs the CSR accesses in M-mode, never Debug Mode.",
        plan={
            "Sdtrig_tdata1_dmode_writable": "For each trigger type the hart accepts among mcontrol6 (load, U) and "
            "icount (count=1, U): write tdata1 = that configuration with dmode = 1; tdata1.dmode reads 0. Then a "
            "write of tdata2 from M-mode still takes effect (the trigger is not locked to Debug Mode).",
            "Sdtrig_tdata1_dmode_0": "With dmode = 0, M-mode writes take effect: tdata1 = mcontrol6 load trigger "
            "(U) reads back with the configured bits, tdata2 = A then A+8 read back, and the trigger fires on lw A+8.",
            "Sdtrig_action1": "Write tdata1 = mcontrol6 load trigger (U) with action = 1 and dmode = 0, and the same "
            "for icount (count=1, U): tdata1 never reads dmode = 0 with action = 1.",
        }[rule],
    )
    lab = t.label("dm")
    t.emit(f"{lab}:", 0)
    if rule == "Sdtrig_tdata1_dmode_0":

        def run() -> None:
            sd.arm(t, acc, MC6, LOAD | sd.U, A)
            acc.r("x7", "tdata1")
            t.check_masked(
                "x7",
                X(sd.MC6_MASK | (0xF << 28), sd.MC6_MASK | (0xF << 60)),
                sd.tdata1(MC6, LOAD | sd.U),
                lab,
                "tdata1 written from M-mode (dmode=0)",
            )
            t.la("x6", f"{A}+8")
            acc.w("tdata2", "x6")
            acc.r("x7", "tdata2")
            t.emit("sub x7, x7, x6")
            t.check("x7", 0, lab, "tdata2 written from M-mode (difference)")
            t.la("x8", f"{A}+8")
            sd.fire(t, "U", ["lw x7, 0(x8)", "nop", "nop"], True, "load trigger rewritten to A+8", tval=[0, f"{A}+8"])
            sd.disarm(t, acc)

        with_probe(t, acc, [(MC6, LOAD | sd.U)], [A], run)
        return t
    for typ, low, t2 in ((MC6, LOAD | sd.U, A), (sd.IC, sd.IC_U | sd.COUNT(1), None)):
        name = "mcontrol6" if typ == MC6 else "icount"

        def run2(typ: int = typ, low: int = low, t2: str | None = t2, name: str = name) -> None:
            sd.select(t, acc)
            acc.w0("tdata1")
            if t2:
                set_t2(t, t2)
                acc.w("tdata2", "x8")
            if rule == "Sdtrig_action1":
                act = sd.ACTION(1) if typ == MC6 else 1
                sd.mk(t, "x8", typ, low | act)
                acc.w("tdata1", "x8")
                acc.r("x7", "tdata1")
                acc.w0("tdata1")
                t.comment(f"x15 = !(type == {typ} && dmode == 0 && action == 1)")
                t.emit(f"srli x6, x7, {'12' if typ == MC6 else '0'}")
                t.emit(f"andi x6, x6, {15 if typ == MC6 else 63}")
                t.emit("addi x6, x6, -1")
                t.emit("snez x6, x6  // action != 1")
                t.emit("srli x5, x7, (__riscv_xlen-5)")
                t.emit("andi x5, x5, 1  // dmode")
                t.emit("or x15, x6, x5")
                t.emit(f"srli x5, x7, {sd.TYPE_SHIFT}")
                t.emit(f"addi x5, x5, -{typ}")
                t.emit("snez x5, x5  // legalized to another type (e.g. 15, disabled): no action field")
                t.emit("or x15, x15, x5")
                if mut("action1_kept"):
                    t.emit("li x15, 0")
                t.check_bool("x15", lab, f"{name}: tdata1 never holds dmode=0 with action=1")
            else:
                sd.mk(t, "x8", typ, low, hi=sd.DMODE)
                acc.w("tdata1", "x8")
                acc.r("x7", "tdata1")
                t.check_masked(
                    "x7",
                    sd.DMODE,
                    sd.DMODE if mut("dmode_writable") else 0,
                    lab,
                    f"{name}: tdata1.dmode after an M-mode write of 1",
                )
                t.la("x6", f"{A}+16")
                acc.w("tdata2", "x6")
                acc.r("x7", "tdata2")
                acc.w0("tdata1")

        sd.probe(t, acc, [(typ, low)], [t2])
        sd.either(t, "x1", run2)
    return t


def t_type0(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    text = {
        "Sdtrig_tdata1_data": "If {tdata1-type} is 0, then this field is hard-wired to 0.",
        "Sdtrig_tdata1_dmode_type_0": "If {tdata1-type} is 0, then this bit is hard-wired to 0.",
        "Sdtrig_tdata1_type_rsv": "Other values are reserved for future use.",
    }[rule]
    rsv = rule == "Sdtrig_tdata1_type_rsv"
    t.describe(
        source=XML,
        rule_text=text,
        context="tdata1 is WARL. Type values 8-14 are reserved, so no write may leave them in tdata1."
        if rsv
        else "tdata1 is WARL: a write of type 0 may be legalized to another type (e.g. 15, disabled); the rule "
        "constrains only a tdata1 that reads type 0.",
        plan=(
            "For tselect = 0..3 (while tselect reads back): write tdata1 = 0, then tdata1 = type t with all data bits "
            "set for t = 8, 11 and 14: tdata1.type never reads 8..14."
            if rsv
            else "For tselect = 0..3 (while tselect reads back): write tdata1 = type 0 with dmode = 1 and every data "
            "bit set: when tdata1 then reads type 0, it reads 0 (dmode and data hard-wired to 0)."
        ),
    )
    lab = t.label("t0")
    t.emit(f"{lab}:", 0)
    done = t.label("done")
    for i in range(sd.NPROBE):
        t.li("x6", i)
        acc.w("tselect", "x6")
        acc.r("x7", "tselect")
        nx = t.label("nx")
        t.emit(f"beq x7, x6, {nx}")
        t.code += [f"  AI_SKIP({(sd.NPROBE - i) * (3 if rsv else 1)})"]
        t.emit(f"j {done}")
        t.emit(f"{nx}:", 0)
        acc.w0("tdata1")
        for ty in (8, 11, 14) if rsv else (0,):
            t.li("x8", 0x7FFFFFF)
            t.emit(f"li x5, {ty}")
            t.emit(f"slli x5, x5, {sd.TYPE_SHIFT}")
            t.emit("or x8, x8, x5")
            t.emit("li x5, 1")
            t.emit("slli x5, x5, (__riscv_xlen-5)")
            t.emit("or x8, x8, x5  // dmode")
            acc.w("tdata1", "x8")
            acc.r("x7", "tdata1")
            acc.w0("tdata1")
            tdata1_type(t, "x7", "x6")
            if rsv:
                t.emit("addi x6, x6, -8")
                t.emit("sltiu x15, x6, 7  // 1: type in 8..14")
                t.emit("xori x15, x15, 1")
                if mut("reserved_type_kept"):
                    t.emit("li x15, 0")
                t.check_bool("x15", lab, f"tselect={i}: tdata1.type is not reserved after writing type {ty}")
            else:
                t.emit("snez x6, x6  // type != 0")
                t.emit("seqz x15, x7  // tdata1 == 0")
                t.emit("or x15, x15, x6")
                if mut("type0_keeps_data"):
                    t.emit("seqz x15, x6")
                t.check_bool("x15", lab, f"tselect={i}: a type-0 tdata1 reads 0")
    t.emit(f"{done}:", 0)
    return t


def t_size_support() -> SdFile:
    t = new("Sdtrig_mcontrol6_size_support")
    acc = Acc(t)
    t.describe(
        source=XML,
        rule_text="An implementation must support the value of 0, but all other values are optional.",
        plan="For each trigger that accepts an mcontrol6 load trigger of size 1, 2 or 3 (probed), writing the same "
        "configuration with size = 0 reads back size = 0 (and type 6). Execute and store triggers likewise.",
    )
    lab = t.label("sz")
    t.emit(f"{lab}:", 0)
    for kind in (LOAD, STORE, EXEC):
        for sz in (1, 3):
            low = kind | sd.U | sd.SIZE(sz)

            def run(kind: int = kind, sz: int = sz) -> None:
                sd.select(t, acc)
                acc.w0("tdata1")
                set_t2(t, A)
                acc.w("tdata2", "x8")
                sd.mk(t, "x8", MC6, kind | sd.U | sd.SIZE(0))
                acc.w("tdata1", "x8")
                acc.r("x7", "tdata1")
                acc.w0("tdata1")
                t.check_masked(
                    "x7",
                    X((0xF << 28) | (7 << 16), (0xF << 60) | (7 << 16)),
                    sd.tdata1(MC6, sd.SIZE(1) if mut("size0_dropped") else 0),
                    lab,
                    f"type and size after writing size=0 (kind {kind}) to a trigger that takes size={sz}",
                )

            with_probe(t, acc, [(MC6, low)], [A], run)
    return t


def t_napot() -> list[SdFile]:
    return [
        t_napot_one(r)
        for r in (
            "Sdtrig_mcontrol6_match_napot_mask",
            "Sdtrig_mcontrol6_match_napot_legal",
            "Sdtrig_mcontrol6_napot_range",
        )
    ]


def t_napot_one(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    text = {
        "Sdtrig_mcontrol6_match_napot_mask": "if bits `maskmax6-1:0` are written with all ones then bit "
        "`maskmax6-1` will be set to 0 while the values of bits `maskmax6-2:0` are UNSPECIFIED.",
        "Sdtrig_mcontrol6_match_napot_legal": "Legal values for {csr-tdata2} require M + `maskmax6` >= `XLEN` and "
        "`M` > 0. See above for how to determine maskmax6.",
        "Sdtrig_mcontrol6_napot_range": "All NAPOT ranges between 2^1 and 2^maskmax6 are supported where "
        "maskmax6 >= 1.",
    }[rule]
    t.describe(
        source=XML,
        rule_text=text,
        context="maskmax6 is found as the spec describes: tdata1 = 0, tdata2 = 0, tdata1 = mcontrol6 with match=1 "
        "(skipped when match does not read 1), tdata2 = all ones, read tdata2: maskmax6 = 1 + the index of its "
        "most significant 0. M = XLEN-1 - (index of the least significant 0 of tdata2).",
        plan={
            "Sdtrig_mcontrol6_match_napot_mask": "After writing all ones, tdata2 is not all ones and its most "
            "significant bit is still 1 (it lies above maskmax6-1, as maskmax6 < XLEN).",
            "Sdtrig_mcontrol6_match_napot_legal": "The value read after writing all ones is legal: M > 0 (bits "
            "XLEN-2:0 are not all ones) and M + maskmax6 >= XLEN (the most significant 0 is at or above the least "
            "significant 0, true for any value with a 0 below XLEN-1). Then tdata2 = A|3 (M = XLEN-3, legal when "
            "maskmax6 >= 3) reads back unchanged.",
            "Sdtrig_mcontrol6_napot_range": "For j = 1, 3 and 5 with j <= maskmax6: tdata2 = A | (2^(j-1) - 1) "
            "reads back unchanged, a U-mode lb at A + 2^j - 1 fires and one at A + 2^j does not.",
        }[rule],
    )
    lab = t.label("np")
    t.emit(f"{lab}:", 0)
    low = LOAD | sd.U | sd.MATCH(1)

    def run(rule: str = rule, lab: str = lab, low: int = low) -> None:
        save(t, "x1", SAVE)
        sd.arm(t, acc, MC6, low, 0)
        t.li("x6", -1)
        acc.w("tdata2", "x6")
        acc.r("x9", "tdata2")
        if mut("napot_allones_kept"):
            t.li("x9", -1)
        save(t, "x9", SAVE2)
        if rule == "Sdtrig_mcontrol6_match_napot_mask":
            t.emit("not x7, x9")
            t.emit("snez x7, x7")
            t.check("x7", 1, lab, "tdata2 after writing all ones is not all ones (bit maskmax6-1 cleared)")
            t.emit("srli x7, x9, (__riscv_xlen-1)")
            t.check("x7", 1, lab, "tdata2 after writing all ones keeps its most significant bit")
        elif rule == "Sdtrig_mcontrol6_match_napot_legal":
            t.emit("slli x7, x9, 1")
            t.emit("ori x7, x7, 1")
            t.emit("not x7, x7")
            t.emit("snez x7, x7  // a 0 in bits XLEN-2:0, so M > 0")
            t.check("x7", 1, lab, "tdata2 after writing all ones is legal (M > 0)")
            t.emit("not x7, x9")
            t.emit("srli x7, x7, 2  // a 0 at bit >= 2: maskmax6 >= 3")

            def m3() -> None:
                t2 = [f"LA(x8, {A})", "ori x8, x8, 3"]
                restore(t, "x1", SAVE)
                sd.select(t, acc)
                set_t2(t, t2)
                acc.w("tdata2", "x8")
                acc.r("x7", "tdata2")
                set_t2(t, t2)
                t.emit("sub x7, x7, x8")
                t.check("x7", 0, lab, "tdata2 = A|3 (8-byte range, legal) reads back unchanged (difference)")

            sd.either(t, "x7", m3)
        else:
            for j in (1, 3, 5):
                restore(t, "x9", SAVE2)
                t.emit("not x7, x9")
                t.emit(f"srli x7, x7, {j - 1}  // nonzero: maskmax6 >= {j}")
                t2 = [f"LA(x8, {A})"] + ([f"ori x8, x8, {(1 << (j - 1)) - 1}"] if j > 1 else [])

                def rng(j: int = j, t2: list = t2) -> None:
                    restore(t, "x1", SAVE)
                    sd.select(t, acc)
                    set_t2(t, t2)
                    acc.w("tdata2", "x8")
                    acc.r("x7", "tdata2")
                    set_t2(t, t2)
                    t.emit("sub x7, x7, x8")
                    t.check("x7", 0, lab, f"tdata2 for a 2^{j}-byte range reads back unchanged (difference)")
                    last = (1 << j) - 1
                    t.la("x8", f"{A}+{last}")
                    sd.fire(
                        t,
                        "U",
                        ["lb x7, 0(x8)", "nop", "nop"],
                        not mut("napot_range_short"),
                        f"2^{j}-byte NAPOT: lb A+{last}",
                        tval=[0, f"{A}+{last}"],
                    )
                    t.la("x8", f"{A}+{1 << j}")
                    sd.fire(t, "U", ["lb x7, 0(x8)", "nop", "nop"], False, f"2^{j}-byte NAPOT: lb A+{1 << j}")

                sd.either(t, "x7", rng)
        restore(t, "x1", SAVE)
        sd.disarm(t, acc)

    with_probe(t, acc, [(MC6, low)], [0], run)
    return t


def t_select_data(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    sel = rule == "Sdtrig_mcontrol6_select_data"
    t.describe(
        source=XML,
        rule_text="There is exactly one compare value and it contains the data value loaded or stored, or the "
        "instruction executed. Any bits beyond the size of the data access will contain 0."
        if sel
        else "All comparisons only look at the lower XLEN (in the current mode) bits of the compare values and of "
        "{csr-tdata2}. When {mcontrol-select}=1 and access size is N, this is further reduced, and comparisons only "
        "look at the lower N bits of the compare values and of {csr-tdata2}.",
        context=TIMING + " Data triggers (select=1) with size=1 (8-bit) are optional and probed. Load data "
        "triggers typically fire after the load (rd written).",
        issues=""
        if sel
        else "https://github.com/riscv/sail-riscv/issues/2038 (Sail compares all of tdata2 for "
        "sized data triggers); open.",
        plan=(
            "In U-mode, A holds byte 0x80:\n1. load data trigger, size=1, tdata2 = 0x80: lb from A (which sign-extends "
            "rd to all ones) fires, and so does lbu; with tdata2 = 0x81 lb does not fire;\n"
            "2. store data trigger, size=1, tdata2 = 0x80: sb of a register holding -128 fires;\n"
            "3. execute data trigger (select=1, size=3) with tdata2 = the encoding of addi x7, x7, 0x5a3: executing "
            "that instruction fires, executing addi x7, x7, 0x5a4 does not."
            if sel
            else "In U-mode: store data trigger, size=1, tdata2 = 0x5a80 (bits above the byte nonzero): sb of 0x80 "
            "fires (only tdata2[7:0] is compared), sb of 0x81 does not; load data trigger likewise with lb from A "
            "(byte 0x80)."
        ),
    )
    t.li("x6", 0x80)
    t.la("x7", A)
    t.emit("sb x6, 0(x7)  // A holds byte 0x80")
    if sel:
        low = LOAD | sd.U | SELECT | sd.SIZE(1)

        def ld() -> None:
            t.la("x8", A)
            sd.fire(
                t,
                "U",
                ["lb x7, 0(x8)", "nop", "nop"],
                not mut("select_data_sext"),
                "load data trigger 0x80 (8-bit): lb A",
                tval=[0, A],
            )
            sd.fire(t, "U", ["lbu x7, 0(x8)", "nop", "nop"], True, "load data trigger 0x80 (8-bit): lbu A", tval=[0, A])
            sd.arm(t, acc, MC6, low, 0x81)
            t.la("x8", A)
            sd.fire(t, "U", ["lb x7, 0(x8)", "nop", "nop"], False, "load data trigger 0x81 (8-bit): lb A")

        with_trigger(t, acc, low, 0x80, ld)
        slow = STORE | sd.U | SELECT | sd.SIZE(1)

        def st() -> None:
            t.la("x8", A)
            t.li("x6", -128)
            sd.fire(t, "U", ["sb x6, 0(x8)", "nop", "nop"], True, "store data trigger 0x80: sb of -128", tval=[0, A])

        with_trigger(t, acc, slow, 0x80, st)
        enc = (0x5A3 << 20) | (7 << 15) | (7 << 7) | 0x13
        elow = EXEC | sd.U | SELECT | sd.SIZE(3)

        def ex() -> None:
            sd.fire(t, "U", ["addi x7, x7, 0x5a4", "nop"], False, "execute data trigger: another addi")
            sd.fire(t, "U", ["addi x7, x7, 0x5a3", "nop", "nop"], True, "execute data trigger: addi x7, x7, 0x5a3")

        with_trigger(t, acc, elow, enc, ex)
    else:
        for kind in (STORE, LOAD):
            low = kind | sd.U | SELECT | sd.SIZE(1)

            def run(kind: int = kind) -> None:
                t.la("x8", A)
                if kind == STORE:
                    t.li("x6", 0x80)
                    sd.fire(
                        t,
                        "U",
                        ["sb x6, 0(x8)", "nop", "nop"],
                        not mut("comparisons_full_tdata2"),
                        "store data trigger 0x5a80 (8-bit): sb 0x80",
                        tval=[0, A],
                    )
                    t.li("x6", 0x81)
                    sd.fire(t, "U", ["sb x6, 0(x8)", "nop", "nop"], False, "store data trigger 0x5a80 (8-bit): sb 0x81")
                    t.li("x6", 0x80)
                    t.la("x7", A)
                    t.emit("sb x6, 0(x7)  // restore byte 0x80")
                else:
                    sd.fire(
                        t,
                        "U",
                        ["lb x7, 0(x8)", "nop", "nop"],
                        True,
                        "load data trigger 0x5a80 (8-bit): lb A",
                        tval=[0, A],
                    )

            with_trigger(t, acc, low, 0x5A80, run)
    return t


# ---------------------------------------------------------------- CSR access from lower modes
MUTANTS.update(
    {
        "trigger_csr_virtual": "a VS/VU-mode access to a trigger CSR raises virtual instruction",
        "scontext_u_ok": "U-mode may access scontext",
        "hcontext_vs_illegal": "a VS-mode access to hcontext raises illegal instead of virtual instruction",
        "hcontext_not_alias": "hcontext is a separate register from mcontext",
        "scontext_stateen_ignored": "mstateen0[57] does not gate scontext",
    }
)


def csr_enc(csr: int, rd: int = 7) -> int:
    return (csr << 20) | (2 << 12) | (rd << 7) | 0x73  # csrrs rd, csr, x0


def t_trigger_modes() -> SdFile:
    t = new("Sdtrig_trigger_modes")
    t.describe(
        source=XML,
        rule_text="The Trigger Module registers, except {csr-mscontext}, {csr-scontext}, and {csr-hcontext}, are only "
        "accessible in machine and Debug Mode to prevent untrusted user code from causing entry into Debug Mode "
        "without the OS's permission.",
        context="tselect, tdata1-3, tinfo, tcontrol and mcontext are M-level CSRs (0x7a0-0x7a8), so a read from S, U, "
        "VS or VU raises illegal instruction (not virtual instruction: they are not hypervisor or supervisor CSRs). "
        "xtval is 0 or the instruction bits. An optional CSR that is not implemented raises illegal instruction too.",
        plan="Read each of tselect, tdata1, tdata2, tdata3, tinfo, tcontrol and mcontext with csrrs x7, csr, x0 in S, "
        "U, VS and VU (VS/VU with H): illegal instruction (cause 2) every time, and rd is unchanged. Then write "
        "tselect and tdata1 (csrrw x0, csr, x6 with x6 = 1) in each mode: illegal instruction, and tselect (read "
        "through T-SBI) is unchanged.",
    )
    for name, num in (
        ("tselect", 0x7A0),
        ("tdata1", 0x7A1),
        ("tdata2", 0x7A2),
        ("tdata3", 0x7A3),
        ("tinfo", 0x7A4),
        ("tcontrol", 0x7A5),
        ("mcontext", 0x7A8),
    ):
        e = csr_enc(num)

        def per(mode: str, e: int = e, name: str = name) -> None:
            t.li("x7", 0x77)
            exp = 22 if (mut("trigger_csr_virtual") and mode in ("VS", "VU")) else 2
            lab = t.window(mode, [f".word {e:#x}  // csrrs x7, {name}, x0"], exp, f"read {name}", tval=[0, e])
            t.check("x7", 0x77, lab, f"read {name} in {mode}-mode: rd unchanged")

        modes(t, per, ("S", "U", "VS", "VU"))
    acc = Acc(t)
    t.comment("writes: csrrw x0, tselect/tdata1, x6 must trap and leave the trigger CSRs unchanged")
    acc.r("x9", "tselect")
    for name, num in (("tselect", 0x7A0), ("tdata1", 0x7A1)):
        e = (num << 20) | (6 << 15) | (1 << 12) | 0x73  # csrrw x0, csr, x6

        def wr(mode: str, e: int = e, name: str = name) -> None:
            t.li("x6", 1)
            lab = t.window(mode, [f".word {e:#x}  // csrrw x0, {name}, x6"], 2, f"write {name}", tval=[0, e])
            acc.r("x7", "tselect")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab, f"write {name} in {mode}-mode: tselect unchanged (difference)")

        modes(t, wr, ("S", "U", "VS", "VU"))
    return t


def t_scontext(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    del acc
    stateen = rule == "Sdtrig_scontext_accessibility"
    text = {
        "Sdtrig_scontext_access": "This optional register is only accessible in S/HS-mode, VS-mode, M-mode and Debug "
        "Mode.",
        "Sdtrig_scontext_accessibility": "Accessibility of this CSR is controlled by `mstateenzero[57]` and "
        "`hstateenzero[57]` in the Smstateen extension.",
    }[rule]
    t.describe(
        source=XML,
        rule_text=text,
        context="scontext (0x5a8) is optional: the test first reads it in S-mode and passes vacuously when that "
        "raises illegal instruction. The framework boots with mstateen0[57] and hstateen0[57] set. From VU-mode an "
        "S-level CSR that VS-mode may access raises virtual instruction; from U-mode, illegal instruction.",
        plan=(
            "With Smstateen: clear mstateen0[57] (mstateen0h bit 25 on RV32) through T-SBI: an S-mode read of "
            "scontext raises illegal instruction; set it again: the read succeeds. With H also: clear hstateen0[57] "
            "(hstateen0h bit 25): a VS-mode read raises virtual instruction; set it again: it succeeds."
            if stateen
            else "S-mode and VS-mode reads succeed; U-mode raises illegal instruction (2); VU-mode raises virtual "
            "instruction (22)."
        ),
    )
    e = csr_enc(0x5A8)
    sd.has_csr(t, "scontext", "x1")

    def run() -> None:
        if not stateen:
            for m, exp in (("S", "ok"), ("U", 2), ("VS", "ok"), ("VU", 22)):
                if mut("scontext_u_ok") and m == "U":
                    exp = "ok"
                ctx = t.only_if(H) if m in ("VS", "VU") else None
                if ctx:
                    with ctx:
                        t.window(
                            m,
                            [f".word {e:#x}  // csrr x7, scontext"],
                            exp,
                            "read scontext",
                            tval=[0, e] if exp != "ok" else None,
                        )
                else:
                    t.window(
                        m,
                        [f".word {e:#x}  // csrr x7, scontext"],
                        exp,
                        "read scontext",
                        tval=[0, e] if exp != "ok" else None,
                    )
            return
        with t.only_if("defined(SMSTATEEN_SUPPORTED)"):
            for op in ("CLEAR", "SET"):
                with t.rv64_only():
                    t.emit("li a1, 1")
                    t.emit("slli a1, a1, 57")
                    t.tsbi_csr(op, "MSTATEEN0", "a1")
                with t.rv32_only():
                    t.li("a1", 1 << 25)
                    t.tsbi_csr(op, "MSTATEEN0H", "a1")
                exp = 2 if op == "CLEAR" and not mut("scontext_stateen_ignored") else "ok"
                t.window(
                    "S",
                    [f".word {e:#x}  // csrr x7, scontext"],
                    exp,
                    f"read scontext with mstateen0[57] = {int(op == 'SET')}",
                    tval=[0, e] if exp != "ok" else None,
                )
            with t.only_if(H):
                for op, csrop in (("CLEAR", "csrc"), ("SET", "csrs")):
                    with t.rv64_only():
                        t.emit("li x6, 1")
                        t.emit("slli x6, x6, 57")
                        t.emit(f"{csrop} CSR_HSTATEEN0, x6")
                    with t.rv32_only():
                        t.li("x6", 1 << 25)
                        t.emit(f"{csrop} CSR_HSTATEEN0H, x6")
                    exp = 22 if op == "CLEAR" else "ok"
                    t.window(
                        "VS",
                        [f".word {e:#x}  // csrr x7, scontext"],
                        exp,
                        f"read scontext with hstateen0[57] = {int(op == 'SET')}",
                        tval=[0, e] if exp != "ok" else None,
                    )

    sd.either(t, "x1", run)
    return t


def t_hcontext(rule: str) -> SdFile:
    t = new(rule, req=["H"])
    acc = Acc(t)
    text = {
        "Sdtrig_hcontext": "This register is an alias of the {csr-mcontext} register, providing access to the "
        "{mcontext-hcontext} field from HS-Mode.",
        "Sdtrig_hcontext_access": "This register is only accessible in HS-Mode, M-mode and Debug Mode.",
        "Sdtrig_hcontext_implemented": "This optional register may be implemented only if the H extension is "
        "implemented. If it is implemented, {csr-mcontext} must also be implemented.",
        "Sdtrig_hcontext_smstateen": "If Smstateen is implemented, then accessibility of in HS-Mode is controlled by "
        "`mstateenzero[57]`.",
    }[rule]
    t.describe(
        source=XML,
        rule_text=text,
        context="hcontext (0x6a8) is optional: the test reads it in HS-mode and passes vacuously when that raises "
        "illegal instruction. mcontext is read through T-SBI (M-mode); a T-SBI access to an unimplemented mcontext "
        "traps in M-mode and fails the test. From VS/VU-mode an HS-level CSR raises virtual instruction; from U-mode "
        "illegal instruction.",
        plan={
            "Sdtrig_hcontext": "Write hcontext = 5 in HS-mode and read it back as h; mcontext (T-SBI) reads h. Write "
            "mcontext = 3 (T-SBI); hcontext reads what mcontext reads.",
            "Sdtrig_hcontext_access": "HS-mode reads succeed; VS and VU raise virtual instruction (22); U raises "
            "illegal instruction (2).",
            "Sdtrig_hcontext_implemented": "When hcontext reads without a trap in HS-mode, mcontext reads through "
            "T-SBI (no trap) and equals hcontext.",
            "Sdtrig_hcontext_smstateen": "With Smstateen: clear mstateen0[57] (mstateen0h bit 25 on RV32): an HS-mode "
            "read of hcontext raises illegal instruction; set it again: the read succeeds.",
        }[rule],
    )
    e = csr_enc(0x6A8)
    sd.has_csr(t, "hcontext", "x1")

    def run() -> None:
        lab = t.label("hc")
        t.emit(f"{lab}:", 0)
        if rule == "Sdtrig_hcontext":
            t.li("x6", 5)
            t.emit("csrw 0x6a8, x6")
            t.emit("csrr x9, 0x6a8")
            acc.r("x7", "mcontext")
            if mut("hcontext_not_alias"):
                t.emit("addi x7, x7, 1")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab, "mcontext reads the value written through hcontext (difference)")
            t.li("x6", 3)
            acc.w("mcontext", "x6")
            acc.r("x9", "mcontext")
            t.emit("csrr x7, 0x6a8")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab, "hcontext reads the value written through mcontext (difference)")
            t.emit("csrw 0x6a8, x0")
        elif rule == "Sdtrig_hcontext_implemented":
            t.emit("csrr x9, 0x6a8")
            acc.r("x7", "mcontext")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab, "mcontext exists and equals hcontext (difference)")
        elif rule == "Sdtrig_hcontext_access":
            for m in ("VS", "VU", "U"):
                exp = 22 if m != "U" else 2
                if mut("hcontext_vs_illegal") and m == "VS":
                    exp = 2
                t.window(m, [f".word {e:#x}  // csrr x7, hcontext"], exp, "read hcontext", tval=[0, e])
        else:
            with t.only_if("defined(SMSTATEEN_SUPPORTED)"):
                for op in ("CLEAR", "SET"):
                    with t.rv64_only():
                        t.emit("li a1, 1")
                        t.emit("slli a1, a1, 57")
                        t.tsbi_csr(op, "MSTATEEN0", "a1")
                    with t.rv32_only():
                        t.li("a1", 1 << 25)
                        t.tsbi_csr(op, "MSTATEEN0H", "a1")
                    exp = 2 if op == "CLEAR" else "ok"
                    t.window(
                        "S",
                        [f".word {e:#x}  // csrr x7, hcontext"],
                        exp,
                        f"read hcontext with mstateen0[57] = {int(op == 'SET')}",
                        tval=[0, e] if exp != "ok" else None,
                    )

    sd.either(t, "x1", run)
    return t


# ---------------------------------------------------------------- icount
MUTANTS.update(
    {
        "icount_off_by_one": "icount fires one instruction late (count+1 instructions retire first)",
        "icount_tval_pc": "an icount breakpoint writes the PC to xtval",
        "icount_trap_not_counted": "a trap does not decrement icount",
        "icount_trap_counted_twice": "a trapping instruction decrements icount twice (trap and retirement)",
        "icount_counts_ecall_twice": "the ecall that leaves U-mode is not counted",
        "icount_no_pending": "icount.pending is not set when count reaches 0 in a mode where it cannot fire",
        "icount_pending_kept": "icount.pending stays set after the trigger fires",
        "icount_zero_fires": "an icount trigger with count=0 fires",
        "icount_ret_not_counted": "an sret is not counted by icount",
        "icount_mode_ignored": "icount counts instructions in modes whose bit is clear",
        "icount_hit_sticky": "icount.hit is set only on the first firing",
    }
)
COUNTF = X(0x3FFF << 10, 0x3FFF << 10)
PEND = sd.IC_PENDING


def ic_state(t: TestFile, acc: Acc, lab: str, count: list[int], pending: int, desc: str) -> None:
    """Read the icount trigger's tdata1 (found in x1) and check count and pending."""
    sd.read_tdata1(t, acc, "x7")
    t.check_masked("x7", COUNTF, [sd.COUNT(c) for c in count], lab, f"{desc}: icount.count")
    t.check_masked("x7", PEND, pending, lab, f"{desc}: icount.pending")


def raw(t: TestFile, mode: str, body: list[str], n: int, lab: str | None = None) -> tuple[str, str]:
    """A window permitting n traps; with n = 1 the trap resumes at the end of body, with n = 2 each trap returns
    past its instruction (body must leave room). Returns (first label, end label)."""
    lab = lab or t.label(f"at_{mode}")
    end = t.label("end")
    if mode == "S" and t.cur == "S":
        t.emit("csrsi sstatus, 2")
    if n == 1:
        sd.resume(t, end)  # with two traps, the first must return normally (resume is used by the next trap)
    t.allow(n)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    for ln in body:
        t.emit(ln)
    t.emit(f"{end}:", 0)
    if mode != t.cur:
        t.leave()
    sd.clear_resume(t)
    t.emit("AI_OUTCOME", 20)
    return lab, end


def bp_log(t: TestFile, lab: str, epc: str, mode: str, desc: str, tval: Expect = 0) -> None:
    """The last logged trap is a breakpoint from `mode` at epc with xtval tval."""
    t.emit("AI_LOG(x15, TRAPLOG_CAUSE)", 10)
    t.check("x15", 3, lab, f"{desc}: cause breakpoint")
    t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
    t.check("x15", epc, lab, f"{desc}: xepc")
    t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
    t.check("x15", [lab] if mut("icount_tval_pc") else tval, lab, f"{desc}: xtval")
    t.emit("AI_ORIGIN", 25)
    t.check("x15", sd.ORIGIN[mode], lab, f"{desc}: came from {mode}-mode")


def ic_low(mode: str, n: int) -> int:
    return sd.MODEBITS_IC[mode] | sd.COUNT(n)


IC_CTX = (
    "icount (type 3) is optional and probed: a test looks for a trigger that keeps type 3 with the count it needs "
    "(a count hard-wired to 1 makes larger counts unavailable). A U/VU-mode window is entered with sret from S "
    "(an S instruction) and left with T-SBI (li a0, op; ecall: one retired instruction and one trap in the window's "
    "mode). When a window takes only the icount breakpoint, the handler resumes at the end of the window; when it "
    "also takes the instruction's own trap, each trap returns past its instruction."
)


def t_icount(rule: str) -> SdFile:
    t = new(rule)
    acc = Acc(t)
    lab0 = t.label("ic")
    t.emit(f"{lab0}:", 0)
    texts = {
        "Sdtrig_icount_match1": "An instruction retires after having been fetched in a privilege mode where the "
        "trigger is enabled. This explicitly includes all RET instructions from various modes.",
        "Sdtrig_icount_match_gt1": "When {icount-count} is greater than 1 and the trigger matches, then {icount-count} "
        "is decremented by 1.",
        "Sdtrig_icount_match_eq1": "When {icount-count} is 1 and the trigger matches, then {icount-pending} becomes "
        "set. In addition {icount-count} will become 0 unless it is hard-wired to 1.",
        "Sdtrig_icount_pending_set": "This bit becomes set when {icount-count} is decremented from 1 to 0. It is "
        "cleared when the trigger fires, which will happen just before executing the next instruction in one of the "
        "enabled modes.",
        "Sdtrig_icount_pending": "When {icount-pending} is set, the trigger fires just before any further instructions "
        "are executed in a mode where the trigger is enabled. As the trigger fires, {icount-pending} is cleared. In "
        "addition, if {icount-count} is hard-wired to 1 then {icount-m}, {icount-s}, {icount-u}, {icount-vs}, and "
        "{icount-vu} are all cleared.",
        "Sdtrig_icount_count_zero": "When {icount-count} is 0 it stays at 0 until explicitly written.",
        "Sdtrig_icount_match2": "A trap is taken from a privilege mode where the trigger is enabled. This explicitly "
        "includes traps taken due to interrupts.",
        "Sdtrig_icount_case": "The intent of {icount-pending} is to cleanly handle the case where {icount-action} is "
        "0, {icount-m} is 0, {icount-u} is 1, {icount-count} is 1, and the U-mode instruction being executed causes a "
        "trap into M-mode. In that case we want the entire M-mode handler to be executed, and the debug trap to be "
        "taken before the next U-mode instruction.",
        "Sdtrig_icount_all_traps_match": "the rule is simply that all traps match.",
        "Sdtrig_icount_multiple_match": "If more than one of the above events occur during a single instruction "
        "execution, the trigger still only matches once for that instruction.",
        "Sdtrig_icount_action0": "If the trigger fires with {icount-action}=0 then zero is written to the `tval` CSR "
        "on the breakpoint trap.",
        "Sdtrig_icount_u": "When set, enable this trigger in U-mode. This bit is hard-wired to 0 if the hart does not "
        "support U-mode.",
        "Sdtrig_icount_s": "When set, enable this trigger in S/HS-mode. This bit is hard-wired to 0 if the hart does "
        "not support S-mode.",
        "Sdtrig_icount_vs": "When set, enable this trigger in VS-mode. This bit is hard-wired to 0 if the hart does "
        "not support virtualization mode.",
        "Sdtrig_icount_vu": "When set, enable this trigger in VU-mode. This bit is hard-wired to 0 if the hart does "
        "not support virtualization mode.",
        "Sdtrig_icount_hit": "If this bit is implemented, the hardware sets it when this trigger fires. The trigger's "
        "user can set or clear it at any time. It is used to determine which trigger(s) fires. If the bit is not "
        "implemented, it is always 0 and writing it has no effect.",
    }
    plans = {
        "Sdtrig_icount_match1": "1. count=3, u=1: a U window of nops takes one breakpoint with xepc = the 4th nop "
        "(3 retired).\n2. With H: count=2, vs=1, vsepc = a VU label and vsstatus.SPP = 0 set beforehand: a VS window "
        "runs nop; sret (to VU, where the trigger is disabled). The sret is counted: back in HS, count = 0 and pending "
        "= 1 (with the sret not counted, count would be 1).",
        "Sdtrig_icount_match_gt1": "count=20, u=1: a U window of 5 nops plus the T-SBI exit (li: 1 retired, ecall: 1 "
        "trap) takes no trap and leaves count = 13, pending = 0. With H the same in VU (vu=1).",
        "Sdtrig_icount_match_eq1": "count=7, u=1: 5 nops + li + ecall bring count to 0 at the ecall trap; back in S "
        "(not enabled) tdata1 reads count = 0 and pending = 1.",
        "Sdtrig_icount_pending_set": "As for match_eq1 (pending = 1 after count reaches 0 in a trap to S), then a U "
        "window: the trigger fires before its first instruction (xepc = that instruction), and afterwards pending "
        "= 0.",
        "Sdtrig_icount_pending": "count=7, u=1, the count reaches 0 at the U exit's ecall; S-mode code (not enabled) "
        "runs without a breakpoint; the next U window takes the breakpoint before its first instruction (xepc = it, "
        "xtval = 0); tdata1 then reads pending = 0.",
        "Sdtrig_icount_count_zero": "count=0, u=1: a U window of 4 nops (plus the exit) takes no trap; count and "
        "pending read 0.",
        "Sdtrig_icount_match2": "1. count=1, u=1: a U-mode illegal instruction traps to S (counted: pending); the "
        "handler returns and the breakpoint is taken before the next U instruction (xepc = it, xtval = 0).\n2. "
        "Interrupt: with sstatus.SIE = 0, sie.SSIE = 1 and sip.SSIP = 1, count=1, u=1: entering U takes the supervisor "
        "software interrupt at the first U instruction (counted), and after the handler returns the breakpoint is "
        "taken before that instruction (xepc = it).",
        "Sdtrig_icount_case": "count=1, u=1, s=0 (and m=0): a U-mode illegal instruction (csrr mstatus) traps into S; "
        "the whole handler runs (logged, returns past the instruction) and the breakpoint is taken before the next "
        "U instruction (xepc = it, xtval = 0): two traps, cause 2 then 3.",
        "Sdtrig_icount_all_traps_match": "count=1, u=1: an ebreak in U traps to S (a breakpoint exception, counted); "
        "after the handler, the icount breakpoint is taken before the next U instruction.",
        "Sdtrig_icount_multiple_match": "count=2, u=1: a U-mode illegal instruction (traps, does not retire) counts "
        "once, the following nop once: the breakpoint is taken before the instruction after the nop (xepc = first "
        "+ 8), not before the nop.",
        "Sdtrig_icount_action0": "count=1 in U (u=1) and in S (s=1, armed through T-SBI so the first S instruction "
        "after the return is counted), and VS/VU with H: the breakpoint writes xtval = 0, xepc = the second "
        "instruction.",
        "Sdtrig_icount_u": "1. count=1, u=1: the breakpoint is taken in U before the second U instruction.\n2. count=2, "
        "s=1 only (u=0): a U window of nops takes no trap, and the trigger has not counted U instructions.",
        "Sdtrig_icount_s": "1. count=1, s=1 (armed through T-SBI): the breakpoint is taken in S before the second S instruction after "
        "the return (no breakpoint is accepted only when tdata1.s did not stick).\n2. count=20, u=1 only: S-mode instructions do not decrement count.",
        "Sdtrig_icount_vs": "count=1, vs=1: the breakpoint is taken in VS before the second VS instruction; with u=1 "
        "and s=1 only (count=1000), a VS window of nops takes no trap.",
        "Sdtrig_icount_vu": "count=1, vu=1: the breakpoint is taken in VU before the second VU instruction; with u=1 "
        "and s=1 only (count=1000), a VU window of nops takes no trap.",
        "Sdtrig_icount_hit": "count=1, u=1 fires in U; tdata1 is rewritten with hit = 0 and no mode bits and a U window "
        "runs (no firing: hit stays 0); count=1 again fires again: hit is nonzero after the second firing exactly "
        "when it was after the first (when it is implemented, the hardware sets it at every firing).",
    }
    if rule in ("Sdtrig_icount_vs", "Sdtrig_icount_vu"):
        t.required.append("H")
    t.describe(source=XML, rule_text=texts[rule], context=IC_CTX, plan=plans[rule])
    off = 1 if mut("icount_off_by_one") else 0

    def probe_ic(low: int, run: Callable[[], object]) -> None:
        with_probe(t, acc, [(sd.IC, low)], [None], run)

    def u_fire(mode: str, n: int, desc: str) -> None:
        """Arm count=n in mode (enabled there only), run nops in mode, expect a breakpoint before nop n+1."""

        def run() -> None:
            sd.arm(t, acc, sd.IC, ic_low(mode, n))
            lab = t.label(f"icu_{mode}")
            raw(t, mode, ["nop"] * (n + 4), 1, lab)
            t.check("x13", 1, lab, f"{desc}: one trap")
            bp_log(t, lab, f"{lab}+{4 * (n + off)}", mode, desc)
            sd.disarm(t, acc)

        probe_ic(ic_low(mode, n), run)

    def s_fire(desc: str) -> None:
        """count=1, s=1 armed through T-SBI: the first S instruction after the return retires, then the breakpoint."""

        def run() -> None:
            save(t, "x1", SAVE)
            sd.select(t, acc)
            acc.w0("tdata1")
            sd.mk(t, "x8", sd.IC, ic_low("S", 1))
            lab, end = t.label("ics"), t.label("ics_end")
            t.emit("csrsi sstatus, 2")
            sd.resume(t, end)
            t.allow(1)
            acc.w("tdata1", "x8")
            t.emit(f"{lab}:", 0)
            for _ in range(5):
                t.emit("nop")
            t.emit(f"{end}:", 0)
            sd.clear_resume(t)
            t.emit("AI_OUTCOME", 20)
            t.check("x13", [0, 1], lab, f"{desc}: at most one trap")

            def trapped() -> None:
                bp_log(t, lab, f"{lab}+{4 * (1 + off)}", "S", desc)

            def none() -> None:
                restore(t, "x1", SAVE)
                sd.read_tdata1(t, acc, "x7")
                t.check_masked("x7", sd.IC_S, 0, lab, f"{desc}: no breakpoint, so icount.s was not kept (WARL)")

            sd.either(t, "x13", trapped, none)
            restore(t, "x1", SAVE)
            sd.disarm(t, acc)

        # An s=1 icount cannot be probed through T-SBI: it would count the probe's own S-mode instructions (and a
        # count hard-wired to 1 fires at once). Probe u=1 instead, and arm s=1 inside the window: no breakpoint is
        # legal only when tdata1.s did not stick.
        probe_ic(ic_low("U", 1), run)

    if rule == "Sdtrig_icount_match1":
        u_fire("U", 3, "count=3 in U")
        with t.only_if(H):

            def run() -> None:
                sd.arm(t, acc, sd.IC, ic_low("VS", 2))
                vu = t.label("vu")
                t.la("x6", vu)
                t.emit("csrw CSR_VSEPC, x6")
                t.li("x6", 0x100)
                t.emit("csrc CSR_VSSTATUS, x6  // vsstatus.SPP = 0: VS sret goes to VU")
                sd.fire(t, "VS", ["nop", "sret", f"{vu}:", "nop", "nop"], False, "VS nop; sret to VU")
                ic_state(
                    t,
                    acc,
                    lab0,
                    [1] if mut("icount_ret_not_counted") else [0],
                    0 if mut("icount_ret_not_counted") else PEND,
                    "after VS nop + sret with count=2",
                )
                sd.disarm(t, acc)

            probe_ic(ic_low("VS", 2), run)
    elif rule == "Sdtrig_icount_match_gt1":
        for m in ("U", "VU"):
            ctx = t.only_if(H) if m == "VU" else None

            def one(m: str = m) -> None:
                def run() -> None:
                    sd.arm(t, acc, sd.IC, ic_low(m, 20))
                    sd.fire(t, m, ["nop"] * 5, False, "count=20, 5 nops + exit")
                    left = 13 + (1 if mut("icount_counts_ecall_twice") else 0)
                    ic_state(t, acc, lab0, [left], 0, f"count=20 after 5 {m} nops, li and ecall")
                    sd.disarm(t, acc)

                probe_ic(ic_low(m, 20), run)

            if ctx:
                with ctx:
                    one()
            else:
                one()
    elif rule in ("Sdtrig_icount_match_eq1", "Sdtrig_icount_pending_set", "Sdtrig_icount_pending"):

        def run() -> None:
            sd.arm(t, acc, sd.IC, ic_low("U", 7))
            sd.fire(t, "U", ["nop"] * 5, False, "count=7, 5 nops + exit")
            if rule != "Sdtrig_icount_pending":
                ic_state(t, acc, lab0, [0], 0 if mut("icount_no_pending") else PEND, "count reached 0 at the U exit")
            if rule != "Sdtrig_icount_match_eq1":
                t.emit("nop")
                t.emit("nop  // S-mode instructions: the trigger is not enabled here")
                lab = t.label("pend")
                raw(t, "U", ["nop", "nop", "nop"], 1, lab)
                t.check("x13", 1, lab, "pending icount: one trap in the next U window")
                bp_log(t, lab, lab, "U", "pending icount fires before the first U instruction")
                ic_state(t, acc, lab0, [0], PEND if mut("icount_pending_kept") else 0, "after the pending icount fired")
            sd.disarm(t, acc)

        probe_ic(ic_low("U", 7), run)
    elif rule == "Sdtrig_icount_count_zero":

        def run() -> None:
            sd.arm(t, acc, sd.IC, ic_low("U", 0))
            sd.fire(t, "U", ["nop"] * 4, mut("icount_zero_fires"), "count=0, 4 nops", epc=None, tval=None)
            ic_state(t, acc, lab0, [0], 0, "count=0 after U instructions")
            sd.disarm(t, acc)

        probe_ic(ic_low("U", 0), run)
    elif rule in (
        "Sdtrig_icount_case",
        "Sdtrig_icount_all_traps_match",
        "Sdtrig_icount_multiple_match",
        "Sdtrig_icount_match2",
    ):
        n = 2 if rule == "Sdtrig_icount_multiple_match" else 1
        insn = "ebreak" if rule == "Sdtrig_icount_all_traps_match" else "csrr x7, mstatus  // illegal in U"
        cause = 3 if rule == "Sdtrig_icount_all_traps_match" else 2

        def run() -> None:
            sd.arm(t, acc, sd.IC, ic_low("U", n))
            lab = t.label("ict")
            raw(t, "U", [insn, "nop", "nop", "nop"], 2, lab)
            if mut("icount_trap_not_counted"):
                nxt = 4 * (n + 1)
            elif mut("icount_trap_counted_twice"):
                nxt = 0 if n == 1 else 4
            else:
                nxt = 4 * n
            t.check("x13", 2, lab, "trap in U with icount armed: two traps (the instruction's, then the breakpoint)")
            sd.log(t, "x15", "CAUSE", back=1)
            t.check("x15", cause, lab, "first trap: the instruction's own exception")
            sd.log(t, "x15", "EPC", back=1)
            t.check("x15", lab, lab, "first trap: xepc")
            bp_log(t, lab, f"{lab}+{nxt}", "U", f"icount count={n} after a trapping instruction")
            sd.disarm(t, acc)

        probe_ic(ic_low("U", n), run)
        if rule == "Sdtrig_icount_match2":

            def run2() -> None:
                t.emit("csrci sstatus, 2  // SIE = 0: the interrupt is taken only in U")
                t.li("x6", 2)
                t.emit("csrs sie, x6  // SSIE")
                t.emit("csrs sip, x6  // SSIP pending")
                sd.arm(t, acc, sd.IC, ic_low("U", 1))
                lab = t.label("ici")
                raw(t, "U", ["nop", "nop", "nop"], 2, lab)
                t.emit("csrw sie, x0")
                t.li("x6", 2)
                t.emit("csrc sip, x6")
                t.check("x13", 2, lab, "SSI taken from U with icount armed: two traps")
                sd.log(t, "x15", "CAUSE", back=1)
                t.check("x15", X((1 << 31) | 1, (1 << 63) | 1), lab, "first trap: supervisor software interrupt")
                bp_log(
                    t,
                    lab,
                    f"{lab}+4" if mut("icount_trap_not_counted") else lab,
                    "U",
                    "icount count=1 after an interrupt from U",
                )
                sd.disarm(t, acc)

            probe_ic(ic_low("U", 1), run2)
    elif rule == "Sdtrig_icount_action0":
        u_fire("U", 1, "count=1 in U")
        s_fire("count=1 in S")
        with t.only_if(H):
            u_fire("VS", 1, "count=1 in VS")
            u_fire("VU", 1, "count=1 in VU")
    elif rule in ("Sdtrig_icount_u", "Sdtrig_icount_vs", "Sdtrig_icount_vu"):
        m = {"Sdtrig_icount_u": "U", "Sdtrig_icount_vs": "VS", "Sdtrig_icount_vu": "VU"}[rule]
        u_fire(m, 1, f"count=1 in {m}")
        others = (ic_low("U", 1000) | sd.IC_S) if m != "U" else ic_low("S", 1000)

        def run() -> None:
            sd.arm(t, acc, sd.IC, others)
            sd.fire(t, m, ["nop"] * 4, mut("icount_mode_ignored"), f"icount enabled in other modes, {m} nops", epc=None)
            if m == "U":
                t.emit("nop  // (S-mode instructions would count here)")
            sd.disarm(t, acc)

        t.comment("an S-enabled icount is probed only when count is writable (u-only probe with count=1000 first)")
        with_probe(t, acc, [(sd.IC, ic_low("U", 1000))], [None], lambda: probe_ic(others, run))
    elif rule == "Sdtrig_icount_s":
        s_fire("count=1 in S")

        def run() -> None:
            sd.arm(t, acc, sd.IC, ic_low("U", 20))
            for _ in range(6):
                t.emit("nop  // S-mode")
            ic_state(t, acc, lab0, [19] if mut("icount_mode_ignored") else [20], 0, "u-only icount after S-mode code")
            sd.disarm(t, acc)

        probe_ic(ic_low("U", 20), run)
    elif rule == "Sdtrig_icount_hit":

        def run() -> None:
            save(t, "x1", SAVE)
            sd.arm(t, acc, sd.IC, ic_low("U", 1))
            lab = t.label("ich")
            raw(t, "U", ["nop"] * 4, 1, lab)
            t.check("x13", 1, lab, "first firing: one trap")
            restore(t, "x1", SAVE)
            sd.read_tdata1(t, acc, "x7")
            t.emit("srli x7, x7, 24")
            t.emit("andi x7, x7, 1")
            save(t, "x7", SAVE2)
            sd.arm(t, acc, sd.IC, sd.COUNT(1))
            sd.fire(t, "U", ["nop"] * 3, False, "icount with no mode bits (hit cleared)")
            restore(t, "x1", SAVE)
            sd.read_tdata1(t, acc, "x7")
            t.check_masked("x7", sd.IC_HIT, 0, lab, "icount.hit stays 0 without firing")
            sd.arm(t, acc, sd.IC, ic_low("U", 1))
            raw(t, "U", ["nop"] * 4, 1)
            restore(t, "x1", SAVE)
            sd.read_tdata1(t, acc, "x7")
            t.emit("srli x7, x7, 24")
            t.emit("andi x7, x7, 1")
            if mut("icount_hit_sticky"):
                t.li("x7", 0)
            restore(t, "x6", SAVE2)
            t.emit("sub x7, x7, x6")
            t.check("x7", 0, lab, "icount.hit after the second firing equals that after the first (difference)")
            sd.disarm(t, acc)

        probe_ic(ic_low("U", 1), run)
    return t


ICOUNT_RULES = [
    "Sdtrig_icount_match1",
    "Sdtrig_icount_match_gt1",
    "Sdtrig_icount_match_eq1",
    "Sdtrig_icount_pending_set",
    "Sdtrig_icount_pending",
    "Sdtrig_icount_count_zero",
    "Sdtrig_icount_match2",
    "Sdtrig_icount_case",
    "Sdtrig_icount_all_traps_match",
    "Sdtrig_icount_multiple_match",
    "Sdtrig_icount_action0",
    "Sdtrig_icount_u",
    "Sdtrig_icount_s",
    "Sdtrig_icount_vs",
    "Sdtrig_icount_vu",
    "Sdtrig_icount_hit",
]


# ---------------------------------------------------------------- M-mode (_Sm) tests
MUTANTS.update(
    {
        "tselect_gap": "the set of triggers has a gap (an index above a missing one exists)",
        "tinfo_says_missing": "tinfo.info reads 1 (no trigger) for an implemented trigger",
        "tinfo_bit_off_by_one": "tinfo.info bit N+1 marks support for type N",
        "tinfo_version0": "a hart with mcontrol6 reports tinfo.version 0",
        "tdata2_traps_for_icount": "tdata2 cannot be accessed while the selected trigger is an icount trigger",
        "tselect_warl_unstable": "a legal tselect value read back changes when written again",
        "num_trigs_zero": "a hart with Sdtrig has no trigger 0",
        "mpte_not_saved": "a trap into M-mode does not copy tcontrol.MTE to MPTE",
        "mret_ignores_mpte": "mret does not restore tcontrol.MTE from MPTE",
        "mte0_fires": "an M-mode trigger fires with tcontrol.MTE = 0",
        "m_bit_ignored": "mcontrol6.m does not enable the trigger in M-mode",
        "icount_m_not_counted": "icount.m does not count M-mode instructions",
        "bp_never_delegated": "breakpoints are taken in M-mode even with medeleg[3] = 1",
        "etrigger_tval_nonzero": "an etrigger breakpoint writes the original exception's xtval",
        "etrigger_epc_faulting": "an etrigger breakpoint's xepc is the instruction that raised the exception",
        "etrigger_wrong_cause": "an etrigger fires on an exception code whose tdata2 bit is clear",
        "etrigger_u_ignored": "an etrigger with u=1 does not fire for exceptions taken from U",
        "itrigger_tval_nonzero": "an itrigger breakpoint writes a nonzero xtval",
        "itrigger_wrong_cause": "an itrigger fires on an interrupt whose tdata2 bit is clear",
        "itrigger_epc_interrupted": "an itrigger breakpoint's xepc is the interrupted instruction",
        "textra_mcontext_ignored": "mhselect=4 does not restrict the trigger to mcontext = mhvalue",
        "textra_scontext_ignored": "sselect=1 does not restrict the trigger to scontext = svalue",
        "sbytemask_ignored": "sbytemask does not mask scontext bytes from the comparison",
        "textra_m_exempt": "textra filtering does not apply in M-mode",
    }
)


def li_x(t: TestFile, reg: str, v: X) -> None:
    """reg = a per-XLEN constant, without table entries."""
    with t.rv64_only():
        t.emit(f"LI({reg}, {v.v64:#x})", 2)
    with t.rv32_only():
        t.emit(f"LI({reg}, {v.v32:#x})", 2)


def sm(rule: str, vector: bool = False, req: list | None = None) -> SdFile:
    return new(rule, sm=True, vector=vector, req=req)


def exists(t: TestFile, i: int, flag: str, has_tinfo: str) -> None:
    """flag = 1 when trigger i exists: tselect reads back i and (tinfo implemented ? tinfo.info != 1 : a written type
    sticks). Leaves tselect = i (when it reads back). M-mode only; uses x5, x7, x8."""
    t.li("x7", i)
    t.emit("csrw CSR_TSELECT, x7")
    t.emit("csrr x8, CSR_TSELECT")
    t.emit("sub x8, x8, x7")
    t.emit(f"seqz {flag}, x8  // tselect reads back {i}")
    no, done = t.label("noinfo"), t.label("exdone")
    t.emit(f"beqz {flag}, {done}")
    t.emit(f"beqz {has_tinfo}, {no}")
    t.emit("csrr x8, CSR_TINFO")
    t.emit("slli x8, x8, (__riscv_xlen-16)")
    t.emit("srli x8, x8, (__riscv_xlen-16)  // info")
    t.emit("addi x8, x8, -1")
    t.emit(f"snez {flag}, x8  // info != 1")
    t.emit(f"j {done}")
    t.emit(f"{no}:", 0)
    t.emit("csrr x8, CSR_TDATA1")
    t.emit(f"srli x8, x8, {sd.TYPE_SHIFT}")
    t.emit(f"snez {flag}, x8  // type != 0")
    t.emit(f"{done}:", 0)


MIN_CFG = {2: LOAD | sd.U, 3: sd.IC_U | sd.COUNT(1), 4: sd.IE_U, 5: sd.IE_U, 6: LOAD | sd.U, 7: 0}


def sticks(t: TestFile, typ: int, flag: str) -> None:
    """flag = 1 when the selected trigger keeps tdata1.type = typ after writing a minimal configuration (enabled in
    U only, so nothing fires in M). Leaves it disabled. Uses x5, x8."""
    t.emit("csrw CSR_TDATA1, x0")
    t.emit("csrw CSR_TDATA2, x0")
    sd.mk(t, "x8", typ, MIN_CFG[typ])
    t.emit("csrw CSR_TDATA1, x8")
    t.emit("csrr x8, CSR_TDATA1")
    t.emit("csrw CSR_TDATA1, x0")
    t.emit(f"srli x8, x8, {sd.TYPE_SHIFT}")
    t.emit(f"addi x8, x8, -{typ}")
    t.emit(f"seqz {flag}, x8")


def t_enum(rule: str) -> SdFile:
    t = sm(rule)
    texts = {
        "Sdtrig_num_trigs_ge1": (
            "If Sdtrig is implemented, the Trigger Module must support at least one trigger.",
            SRC,
        ),
        "Sdtrig_tselect_access": ("The set of accessible triggers must start at 0, and be contiguous.", XML),
        "Sdtrig_tselect_warl": ("This register is *WARL*.", XML),
        "Sdtrig_tinfo_no_trigger": ("If the currently selected trigger doesn't exist, this field contains 1.", XML),
        "Sdtrig_tinfo_support": (
            (
                "One bit for each possible {tdata1-type} enumerated in {csr-tdata1}. Bit N "
                "corresponds to type N. If the bit is set, then that type is supported by the "
                "currently selected trigger."
            ),
            XML,
        ),
        "Sdtrig_mcontrol6_dependence": (
            (
                "Implementing this trigger as described here requires that {tinfo-version} is "
                "1 or higher, which in turn means {csr-tinfo} must be implemented."
            ),
            XML,
        ),
        "Sdtrig_csr_mode": (
            (
                "M-Mode and Debug Mode accesses to trigger CSRs that are used by any of the implemented "
                "triggers must succeed, regardless of the current type of the currently selected trigger."
            ),
            SRC,
        ),
    }
    plans = {
        "Sdtrig_num_trigs_ge1": "tselect = 0 reads back 0, and trigger 0 exists: tinfo.info != 1 when tinfo is "
        "implemented, otherwise one of the types 2-7 sticks in tdata1.",
        "Sdtrig_tselect_access": "For i = 0..7, trigger i exists when tselect reads back i and tinfo.info != 1 (or, "
        "without tinfo, some type 2-7 sticks): no index exists above one that does not.",
        "Sdtrig_tselect_warl": "Write tselect = all ones, 0x55..., 0xaa..., 1, 3 and a random value: each read value r, "
        "written back, reads back r.",
        "Sdtrig_tinfo_no_trigger": "With tinfo implemented, for each i = 0..7 that tselect reads back: tinfo.info = 1 "
        "exactly when no type 2-7 sticks in tdata1 (a missing trigger can take no configuration).",
        "Sdtrig_tinfo_support": "With tinfo implemented, for each existing trigger i < 4 and each type N in 2..7: when "
        "a minimal configuration of type N sticks in tdata1, tinfo.info bit N is set. (The converse is not checked: a "
        "supported type may legalize this configuration to a disabled trigger, norm:Sdtrig_tdata_warl.)",
        "Sdtrig_mcontrol6_dependence": "When some trigger i < 4 keeps type 6, tinfo is implemented (a read in a trap "
        "window does not trap) and tinfo.version >= 1.",
        "Sdtrig_csr_mode": "With trigger i < 4 holding each of: disabled (tdata1 = 0), an mcontrol6 and an icount "
        "configuration (when it takes them): reads of tselect, tdata1 and tinfo (when implemented at all), and of "
        "tdata2 (when any of the first 4 triggers takes mcontrol6, which uses it), do not trap.",
    }
    text, src = texts[rule]
    t.describe(
        source=src,
        rule_text=text,
        context="Run in M-mode, where the trigger CSRs are accessible. tinfo is "
        "optional (it may trap). Types are probed with a minimal configuration enabled only in U (2, 6: "
        "load trigger; 3: icount count=1; 4, 5: u=1; 7: no inputs), so nothing fires in M.",
        plan=plans[rule],
    )
    lab = t.label("en")
    t.emit(f"{lab}:", 0)
    t.emit("csrw CSR_TSELECT, x0")
    sd.has_csr(t, "tinfo", "x9")
    if rule == "Sdtrig_num_trigs_ge1":
        exists(t, 0, "x6", "x9")
        if mut("num_trigs_zero"):
            t.emit("li x6, 0")
        t.check("x6", 1, lab, "trigger 0 exists")
    elif rule == "Sdtrig_tselect_access":
        t.li("x1", 1)
        t.li("x15", 1)
        for i in range(8):
            exists(t, i, "x6", "x9")
            if mut("tselect_gap") and i == 7:
                t.li("x6", 1)
            t.emit("seqz x7, x1  // previous missing")
            t.emit("and x7, x7, x6  // ... and this one exists")
            t.emit("seqz x7, x7")
            t.emit("and x15, x15, x7")
            t.emit("mv x1, x6")
        t.check_bool("x15", lab, "triggers 0..7 that exist are contiguous from 0")
    elif rule == "Sdtrig_tselect_warl":
        vals = [
            X(-1, -1),
            X(0x55555555, 0x5555555555555555),
            X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA),
            X(1, 1),
            X(3, 3),
            t.rand_x(),
        ]
        for v in vals:
            li_x(t, "x6", v)
            t.emit("csrw CSR_TSELECT, x6")
            t.emit("csrr x7, CSR_TSELECT")
            t.emit("csrw CSR_TSELECT, x7")
            t.emit("csrr x8, CSR_TSELECT")
            if mut("tselect_warl_unstable"):
                t.emit("addi x8, x8, 1")
            t.emit("sub x8, x8, x7")
            t.check("x8", 0, lab, f"tselect keeps a legal value read back after writing {v} (difference)")
    elif rule in ("Sdtrig_tinfo_no_trigger", "Sdtrig_tinfo_support", "Sdtrig_csr_mode", "Sdtrig_mcontrol6_dependence"):

        def body() -> None:
            n = 8 if rule == "Sdtrig_tinfo_no_trigger" else 4
            if rule == "Sdtrig_csr_mode":
                t.li("x1", 0)
                for i in range(4):
                    t.li("x7", i)
                    t.emit("csrw CSR_TSELECT, x7")
                    sticks(t, 6, "x6")
                    t.emit("or x1, x1, x6  // some trigger takes mcontrol6: tdata2 is used")
            for i in range(n):
                skipl = t.label("skip")
                t.li("x7", i)
                t.emit("csrw CSR_TSELECT, x7")
                t.emit("csrr x8, CSR_TSELECT")
                if rule == "Sdtrig_tinfo_no_trigger":
                    t.emit(f"beq x8, x7, {skipl}_in")
                    t.code.append("  AI_SKIP(1)")
                    t.emit(f"j {skipl}")
                    t.emit(f"{skipl}_in:", 0)
                    t.li("x15", 0)
                    for ty in range(2, 8):
                        sticks(t, ty, "x6")
                        t.emit("or x15, x15, x6")
                    t.emit("csrr x8, CSR_TINFO")
                    t.emit("slli x8, x8, (__riscv_xlen-16)")
                    t.emit("srli x8, x8, (__riscv_xlen-16)")
                    t.emit("addi x8, x8, -1")
                    t.emit("seqz x8, x8  // info == 1")
                    if mut("tinfo_says_missing"):
                        t.emit("li x8, 1")
                    t.emit("xor x15, x15, x8  // exactly one of: some type sticks, info == 1")
                    t.check_bool("x15", lab, f"tselect={i}: tinfo.info == 1 iff the trigger takes no type")
                    t.emit(f"{skipl}:", 0)
                elif rule == "Sdtrig_tinfo_support":
                    t.emit(f"beq x8, x7, {skipl}_in")
                    t.code.append("  AI_SKIP(6)")
                    t.emit(f"j {skipl}")
                    t.emit(f"{skipl}_in:", 0)
                    t.emit("csrr x9, CSR_TINFO")
                    for ty in range(2, 8):
                        sticks(t, ty, "x6")
                        sh = ty + 1 if mut("tinfo_bit_off_by_one") else ty
                        t.emit(f"srli x7, x9, {sh}")
                        t.emit("andi x7, x7, 1")
                        t.emit("xori x6, x6, 1")
                        t.emit("or x7, x7, x6  // bit set, or the type did not stick")
                        t.check("x7", 1, lab, f"tselect={i}: type {ty} sticks only when tinfo.info bit {ty} is set")
                    t.emit(f"{skipl}:", 0)
                elif rule == "Sdtrig_mcontrol6_dependence":
                    t.emit(f"bne x8, x7, {skipl}")
                    sticks(t, 6, "x6")
                    t.emit(f"beqz x6, {skipl}")
                    t.emit("csrr x7, CSR_TINFO")
                    t.emit("srli x7, x7, 24")
                    t.emit("andi x7, x7, 0xff")
                    if mut("tinfo_version0"):
                        t.li("x7", 0)
                    t.emit("snez x7, x7")
                    t.emit(f"j {skipl}_c")
                    t.emit(f"{skipl}:", 0)
                    t.li("x7", 1)
                    t.emit(f"{skipl}_c:", 0)
                    t.check("x7", 1, lab, f"tselect={i}: a trigger that takes mcontrol6 reports tinfo.version >= 1")
                else:
                    t.emit(f"beq x8, x7, {skipl}_in")
                    t.code.append("  AI_SKIP(24)")
                    t.emit(f"j {skipl}")
                    t.emit(f"{skipl}_in:", 0)
                    for state, typ, low, t2 in (
                        ("disabled", None, 0, None),
                        ("mcontrol6", MC6, LOAD | sd.U, A),
                        ("icount", sd.IC, sd.IC_U | sd.COUNT(1), None),
                    ):
                        t.emit("csrw CSR_TDATA1, x0")
                        if typ:
                            if t2:
                                t.la("x8", t2)
                                t.emit("csrw CSR_TDATA2, x8")
                            sd.mk(t, "x8", typ, low)
                            t.emit("csrw CSR_TDATA1, x8")
                        for csr, cond in (("tselect", None), ("tdata1", None), ("tdata2", "x1"), ("tinfo", "x9")):
                            w = t.label("w")
                            if cond:
                                t.emit(f"seqz x6, {cond}")
                            else:
                                t.li("x6", 0)
                            t.allow(1)
                            t.emit(f"bnez x6, {w}_s")
                            t.emit(f"{w}:", 0)
                            if mut("tdata2_traps_for_icount") and csr == "tdata2" and typ == sd.IC:
                                t.emit(".word 0xf1101073  // csrw mvendorid, x0: illegal")
                            else:
                                t.emit(f"csrr x7, {sd.CSR[csr]}")
                            t.emit(f"{w}_s:", 0)
                            t.outcome("ok", w, f"tselect={i}, {state}: read {csr}")
                        t.emit("csrw CSR_TDATA1, x0")
                    t.emit(f"{skipl}:", 0)

        if rule == "Sdtrig_csr_mode":
            body()
        else:
            sd.either(t, "x9", body)
    t.emit("csrw CSR_TSELECT, x0")
    return t


def tcontrol_enable(t: TestFile) -> None:
    """When tcontrol is implemented, set MTE (M-mode triggers armed on harts using tcontrol). Uses a trap window."""
    sd.has_csr(t, "tcontrol", "x9")
    sk = t.label("notc")
    t.emit(f"beqz x9, {sk}")
    t.emit("csrsi CSR_TCONTROL, 8  // MTE")
    t.emit(f"{sk}:", 0)


def t_tcontrol(rule: str) -> SdFile:
    t = sm(rule)
    texts = {
        "Sdtrig_tcontrol_mpte": "When any trap into M-mode is taken, {tcontrol-mpte} is set to the value of "
        "{tcontrol-mte}.",
        "Sdtrig_tcontrol_mte_mret": "When `mret` is executed, {tcontrol-mte} is set to the value of {tcontrol-mpte}.",
        "Sdtrig_tcontrol_mte_disabled": "Triggers with action=0 do not match/fire while the hart is in M-mode.",
        "Sdtrig_tcontrol_mte_enabled": "Triggers do match/fire while the hart is in M-mode.",
    }
    plans = {
        "Sdtrig_tcontrol_mpte": "When tcontrol is implemented and MTE/MPTE are writable: (a) MTE=1, MPTE=0, an "
        "illegal instruction in M (trap into M, then the handler's mret): MPTE reads 1; (b) MTE=0, MPTE=1, same "
        "trap: MPTE reads 0.",
        "Sdtrig_tcontrol_mte_mret": "When tcontrol is implemented and writable: (a) MTE=0, MPTE=1, mret to the next "
        "instruction (MPP=M, MPIE=1): MTE reads 1; (b) MTE=1, MPTE=0, mret: MTE reads 0.",
        "Sdtrig_tcontrol_mte_disabled": "When tcontrol is implemented and MTE is writable: MTE=0 with mstatus.MIE=1: an "
        "M-mode execute trigger (m=1) on the window's first instruction does not fire.",
        "Sdtrig_tcontrol_mte_enabled": "When tcontrol is implemented and MTE is writable: MTE=1 with mstatus.MIE=1: an "
        "M-mode execute trigger (m=1) on the window's first instruction fires (one breakpoint from M).",
    }
    t.describe(
        source=XML,
        rule_text=texts[rule],
        context="tcontrol (0x7a5) is optional; it is read in a trap window "
        "first and the test passes vacuously without it or when MTE/MPTE do not keep a written 1. mstatus.MIE = 1 "
        "with mie = 0 throughout, for harts that also gate M-mode triggers with MIE. The framework's M handler "
        "ends with mret.",
        plan=plans[rule],
    )
    lab = t.label("tc")
    t.emit(f"{lab}:", 0)
    sd.has_csr(t, "tcontrol", "x1")

    def run() -> None:
        t.li("x6", 0x88)
        t.emit("csrw CSR_TCONTROL, x6")
        t.emit("csrr x6, CSR_TCONTROL")
        t.emit("andi x6, x6, 0x88")
        t.emit("addi x6, x6, -0x88")
        t.emit("seqz x6, x6  // MTE and MPTE writable")

        def go() -> None:
            if rule == "Sdtrig_tcontrol_mpte":
                for mte, mpte in ((1, 0), (0, 1)):
                    t.li("x7", mte * 8 + mpte * 0x80)
                    t.emit("csrw CSR_TCONTROL, x7")
                    t.window(
                        "M",
                        [".word 0xf1101073  // csrw mvendorid, x0: illegal"],
                        2,
                        f"trap with MTE={mte}, MPTE={mpte}",
                    )
                    t.emit("csrr x7, CSR_TCONTROL")
                    t.emit("srli x7, x7, 7")
                    t.emit("andi x7, x7, 1")
                    exp = mpte if mut("mpte_not_saved") else mte
                    t.check("x7", exp, lab, f"tcontrol.MPTE after a trap into M with MTE={mte}")
            elif rule == "Sdtrig_tcontrol_mte_mret":
                for mte, mpte in ((0, 1), (1, 0)):
                    nx = t.label("after_mret")
                    t.li("x7", mte * 8 + mpte * 0x80)
                    t.emit("csrw CSR_TCONTROL, x7")
                    t.la("x7", nx)
                    t.emit("csrw mepc, x7")
                    t.li("x7", 0x1880)
                    t.emit("csrs mstatus, x7  // MPP = M, MPIE = 1")
                    t.emit("mret")
                    t.emit(f"{nx}:", 0)
                    t.emit("csrr x7, CSR_TCONTROL")
                    t.emit("srli x7, x7, 3")
                    t.emit("andi x7, x7, 1")
                    t.check(
                        "x7",
                        mte if mut("mret_ignores_mpte") else mpte,
                        lab,
                        f"tcontrol.MTE after mret with MTE={mte}, MPTE={mpte}",
                    )
            else:
                on = rule == "Sdtrig_tcontrol_mte_enabled"
                x = t.label("X")
                t.emit(f"csrwi CSR_TCONTROL, {8 if on else 0}")
                t.emit("csrsi mstatus, 8")
                sd.probe(t, Acc(t), [(MC6, EXEC | sd.M)], [x], found="x9")

                def arm() -> None:
                    acc = Acc(t)
                    sd.arm(t, acc, MC6, EXEC | sd.M, x, found="x9")
                    fire_at(
                        t,
                        "M",
                        x,
                        ["addi x7, x0, 1", "nop", "nop"],
                        on or mut("mte0_fires"),
                        f"M-mode execute trigger with MTE={int(on)}",
                        tval=[0, x] if on else None,
                    )
                    sd.disarm(t, acc, found="x9")

                sd.either(t, "x9", arm)
            t.emit("csrwi CSR_TCONTROL, 0")

        sd.either(t, "x6", go)

    sd.either(t, "x1", run)
    return t


def t_m_triggers(rule: str) -> SdFile:
    t = sm(rule)
    acc = Acc(t)
    if rule == "Sdtrig_mcontrol6_m":
        t.describe(
            source=XML,
            rule_text="When set, enable this trigger in M-mode.",
            context=TIMING + " M-mode code runs with mstatus.MIE = 1 (mie = 0) and, when tcontrol exists, MTE = 1, so "
            "neither reentrancy mechanism suppresses action=0 triggers in M.",
            plan="1. m=1: an execute trigger on X fires when X runs in M; a load trigger on A fires on lw A in M "
            "(xtval 0 or A); a store trigger on A fires on sw A in M.\n2. Only u=1 (and s=1 with S): lw A in M takes "
            "no trap.",
        )
        tcontrol_enable(t)
        x = t.label("X")
        mb = sd.M if not mut("m_bit_ignored") else sd.U

        def ex() -> None:
            fire_at(t, "M", x, ["addi x7, x0, 1", "nop", "nop"], True, "execute trigger m=1 on X", tval=[0, x])

        with_trigger(t, acc, EXEC | sd.M, x, ex)
        for kind, insn in ((LOAD, "lw"), (STORE, "sw")):

            def ld(insn: str = insn) -> None:
                t.la("x8", A)
                sd.fire(t, "M", [f"{insn} x7, 0(x8)", "nop", "nop"], True, f"m=1 trigger: {insn} A", tval=[0, A])

            with_trigger(t, acc, kind | sd.M, A, ld)

        def neg() -> None:
            t.la("x8", A)
            sd.fire(t, "M", ["lw x7, 0(x8)", "nop", "nop"], mb == sd.U, "u=1 trigger: lw A in M")

        with_trigger(t, acc, LOAD | sd.U, A, neg)
    else:
        t.describe(
            source=XML,
            rule_text="When set, enable this trigger in M-mode."
            if rule == "Sdtrig_icount_m"
            else "The only exception to the above is when the instruction the trigger matched on is a write to the icount "
            "trigger. In that case {icount-pending} might or might not become set if {icount-count} was 1. Afterwards "
            "{icount-count} contains the newly written value.",
            context=IC_CTX
            + " In M-mode (MIE = 1, MTE = 1 when tcontrol exists), the csrw that arms the trigger may or "
            "may not itself be counted (norm:Sdtrig_icount_exception).",
            plan="icount m=1, count=1, written by csrw tdata1 in M: the breakpoint is taken from M before the first or "
            "the second instruction after the csrw (xepc one of the two, xtval 0)."
            if rule == "Sdtrig_icount_m"
            else "icount m=0, u=1, count=5, then the M-mode csrw writes count=9 (m=0, u=1): tdata1 reads count=9 and "
            "pending=0 (the write is not an M-mode match because m=0, and the written value is what remains).",
        )
        tcontrol_enable(t)
        sd.probe(t, acc, [(sd.IC, sd.IC_U | sd.COUNT(5))])

        def run() -> None:
            lab = t.label("icm")
            if rule == "Sdtrig_icount_m":
                sd.select(t, acc)
                t.emit("csrw CSR_TDATA1, x0")
                sd.mk(t, "x8", sd.IC, sd.IC_M | sd.COUNT(1))
                end = t.label("icm_end")
                sd.resume(t, end)
                t.allow(1)
                t.emit("csrw CSR_TDATA1, x8")
                t.emit(f"{lab}:", 0)
                for _ in range(6):
                    t.emit("nop")
                t.emit(f"{end}:", 0)
                sd.clear_resume(t)
                t.emit("AI_OUTCOME", 20)
                t.emit("csrw CSR_TDATA1, x0")
                t.check("x13", 0 if mut("icount_m_not_counted") else 1, lab, "icount m=1 in M: one breakpoint")
                t.check("x14", 3, lab, "icount m=1 in M: cause")
                t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
                t.check("x15", [lab, f"{lab}+4"], lab, "icount m=1 in M: xepc (the csrw may or may not count)")
                t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
                t.check("x15", 0, lab, "icount m=1 in M: xtval")
            else:
                sd.arm(t, acc, sd.IC, sd.IC_U | sd.COUNT(5))
                sd.mk(t, "x8", sd.IC, sd.IC_U | sd.COUNT(9))
                t.emit(f"{lab}:", 0)
                t.emit("csrw CSR_TDATA1, x8")
                ic_state(t, acc, lab, [9], 0, "after writing count=9")
                sd.disarm(t, acc)

        sd.either(t, "x1", run)
    return t


def t_deleg() -> SdFile:
    t = sm("Sdtrig_breakpoint_delegated", req=["S"])
    acc = Acc(t)
    t.describe(
        source=SRC,
        rule_text="That breakpoint exception can either be taken in M-mode or it can be delegated to a less privileged "
        "mode. However, it is possible for triggers to fire in the same mode that the resulting exception will be "
        "handled in.",
        context=TIMING + " medeleg[3] may be read-only 0 (harts using tcontrol for reentrancy hard-wire it); it is "
        "written and read back. Breakpoints delegated to S are suppressed in S while sstatus.SIE = 0 on harts that "
        "use the interrupt enables for reentrancy, so S-mode windows run with SIE = 1 and sie = 0.",
        plan="1. medeleg[3] = 0: a U-mode load trigger fires on lw A in U; the breakpoint is handled in M.\n"
        "2. medeleg[3] = 1 (when it reads back 1): the same breakpoint is handled in S; and an S-mode load trigger "
        "fires on lw A in S and is handled in S (the same mode).",
    )
    t.emit("csrw sie, x0")

    def body() -> None:
        lab = t.label("dl")
        t.emit(f"{lab}:", 0)
        t.emit("csrci medeleg, 8")
        sd.arm(t, acc, MC6, LOAD | sd.U, A)
        t.la("x8", A)
        sd.fire(t, "U", ["lw x7, 0(x8)", "nop", "nop"], True, "medeleg[3]=0", tval=[0, A])
        sd.handler(t, "x15")
        t.check("x15", 3, lab, "medeleg[3]=0: breakpoint from U handled in M")
        t.emit("csrsi medeleg, 8")
        t.emit("csrr x6, medeleg")
        t.emit("andi x6, x6, 8")

        def dl() -> None:
            sd.arm(t, acc, MC6, LOAD | sd.U, A)
            t.la("x8", A)
            sd.fire(t, "U", ["lw x7, 0(x8)", "nop", "nop"], True, "medeleg[3]=1", tval=[0, A])
            sd.handler(t, "x15")
            t.check("x15", 3 if mut("bp_never_delegated") else 1, lab, "medeleg[3]=1: breakpoint from U handled in S")
            sd.arm(t, acc, MC6, LOAD | sd.S, A)
            t.la("x8", A)
            t.li("x7", 2)
            t.emit("csrs mstatus, x7  // sstatus.SIE = 1 (sie = 0)")
            sd.fire(t, "S", ["lw x7, 0(x8)", "nop", "nop"], True, "medeleg[3]=1, S trigger", tval=[0, A])
            sd.handler(t, "x15")
            t.check("x15", 3 if mut("bp_never_delegated") else 1, lab, "medeleg[3]=1: breakpoint from S handled in S")

        sd.either(t, "x6", dl)
        t.emit("csrci medeleg, 8")
        sd.disarm(t, acc)

    sd.probe(t, acc, [(MC6, LOAD | sd.U | sd.S)], [A])
    sd.either(t, "x1", body)
    return t


ET_RULES = {
    "Sdtrig_etrigger_fire": "This trigger may fire on up to XLEN of the Exception Codes defined in `mcause` (described "
    "in the Privileged Spec, with Interrupt=0).",
    "Sdtrig_etrigger_config": "Those causes are configured by writing the corresponding bit in {csr-tdata2}.",
    "Sdtrig_etrigger_timing": "When the trigger matches, it fires after the trap occurs, just before the first "
    "instruction of the trap handler is executed.",
    "Sdtrig_etrigger_action0": "If {etrigger-action}=0, the standard CSRs are updated for taking the breakpoint trap, "
    "and zero is written to the relevant `tval` CSR.",
    "Sdtrig_etrigger_u": "When set, enable this trigger for exceptions that are taken from U mode. This bit is "
    "hard-wired to 0 if the hart does not support U-mode.",
    "Sdtrig_etrigger_s": "When set, enable this trigger for exceptions that are taken from S/HS mode. This bit is "
    "hard-wired to 0 if the hart does not support S-mode.",
    "Sdtrig_itrigger_fire": "This trigger can fire when an interrupt trap is taken.",
    "Sdtrig_itrigger_enable_num": "It can be enabled for individual interrupt numbers by setting the bit corresponding "
    "to the interrupt number in {csr-tdata2}. The interrupt number is interpreted in the mode that the trap handler "
    "executes in.",
    "Sdtrig_itrigger_timing": "When the trigger matches, it fires after the trap occurs, just before the first "
    "instruction of the trap handler is executed.",
    "Sdtrig_itrigger_action0": "If {itrigger-action}=0, the standard CSRs are updated for taking the breakpoint trap, "
    "and zero is written to the relevant `tval` CSR.",
    "Sdtrig_itrigger_u": "When set, enable this trigger for interrupts that are taken from U mode. This bit is "
    "hard-wired to 0 if the hart does not support U-mode.",
    "Sdtrig_itrigger_s": "When set, enable this trigger for interrupts that are taken from S/HS mode. This bit is "
    "hard-wired to 0 if the hart does not support S-mode.",
}
ET_CTX = (
    "Run from M-mode. The trap is delegated to S (medeleg[2] = 1 for an illegal instruction; mideleg[1] = 1 for the "
    "supervisor software interrupt) and breakpoints are not (medeleg[3] = 0), so the breakpoint, taken in S just before "
    "the S handler's first instruction, goes to M. Both reentrancy mechanisms (MIE/SIE, tcontrol) only suppress "
    "triggers whose breakpoint is taken in the mode they fire in, so this is the configuration where every hart must "
    "fire. The M handler returns to the S trap vector without advancing (SDTRIG_XEPC_IN_VECTOR), so the S handler then "
    "handles the original trap: the log holds the breakpoint (M handler) followed by the original trap (S handler). "
    "The type and its mode bit are probed in tdata1, and tdata2 is read back after every write: a hart may "
    "support only some codes, and the expected outcome follows the bit it kept."
)


def t_et(rule: str) -> SdFile:
    t = sm(rule, vector=True, req=["S"])
    acc = Acc(t)
    itr = "itrigger" in rule
    typ = sd.IT if itr else sd.ET
    code = 1 if itr else 2
    modes_ = ("S",) if rule.endswith("_s") else ("U",)
    plans = {
        "fire": "the selected trap from U (illegal instruction / SSI) is followed by one breakpoint",
        "config": "with tdata2 selecting only code 2 (illegal instruction), an illegal instruction from U fires; with "
        "tdata2 selecting only code 5, it does not",
        "enable_num": "with tdata2 selecting only interrupt 1 (SSI), an SSI from U fires; with only interrupt 5 (STI) "
        "selected, it does not",
        "timing": "the breakpoint's mepc is the S handler's entry (stvec BASE for an exception, BASE + 4 for "
        "interrupt 1 when stvec is vectored), and it is logged before the original trap",
        "action0": "the breakpoint writes mtval = 0",
        "u": "with u=1 the breakpoint follows a trap from U; with only s=1, a trap from U is not followed by one",
        "s": "with s=1 the breakpoint follows a trap taken from S (the window runs in S); with only u=1, it does not",
    }
    key = rule.split("_", 2)[2]
    t.describe(
        source=XML,
        rule_text=ET_RULES[rule],
        context=ET_CTX
        + " "
        + (
            "itrigger is probed with tdata2 bit 1 (SSI); the interrupt is made pending with mip.SSIP and enabled with "
            "sie.SSIE, with sstatus.SIE = 0 so it is taken in the lower-mode window."
            if itr
            else "etrigger is probed with tdata2 bit 2 (illegal instruction, csrr mstatus outside M)."
        ),
        plan=f"{'itrigger' if itr else 'etrigger'}: " + plans[key] + ". Every breakpoint is checked: mcause 3 "
        "from S, mepc = the S handler entry, mtval = 0; the original trap is then handled in S with its own cause "
        "and from the original mode.",
    )
    mode = modes_[0]
    mbit = sd.MODEBITS_IE[mode]
    lab0 = t.label("et")
    t.emit(f"{lab0}:", 0)
    sel = 1 << code
    t.li("x6", 1 << 2)
    t.emit("csrw medeleg, x6  // illegal instruction to S, breakpoints to M")
    t.li("x6", 2)
    t.emit("csrw mideleg, x6  // SSI to S")
    t.emit("csrci mstatus, 2  // sstatus.SIE = 0")

    def window(fires: bool, desc: str) -> None:
        lab = t.label(f"etw_{mode}")
        if itr:
            if mode == "S":
                t.emit("csrsi mstatus, 2  // sstatus.SIE = 1: the SSI is taken in S")
            t.li("x6", 2)
            t.emit("csrs mie, x6  // sie.SSIE")
            t.emit("csrs mip, x6  // SSIP pending")
            body = ["nop", "nop", "nop"]
        else:
            body = ["csrr x7, mstatus  // illegal outside M", "nop"]
        t.li("x6", 1 << 2)
        t.emit("csrw medeleg, x6  // again: the framework's GOTO_MMODE restores medeleg[2] from its own saved copy")
        raw(t, mode, body, 2, lab)
        t.emit("csrci mstatus, 2")
        t.emit("csrw mie, x0")
        t.li("x6", 2)
        t.emit("csrc mip, x6")
        t.check("x13", 2 if fires else 1, lab, f"{desc}: number of traps")
        cause = X((1 << 31) | 1, (1 << 63) | 1) if itr else 2
        t.emit("AI_LOG(x15, TRAPLOG_CAUSE)", 10)
        t.check("x15", cause, lab, f"{desc}: the original trap, handled in S")
        sd.handler(t, "x15")
        t.check("x15", 1, lab, f"{desc}: the original trap was handled in S")
        t.emit("AI_ORIGIN", 25)
        t.check("x15", sd.ORIGIN[mode], lab, f"{desc}: the original trap came from {mode}")
        if not itr:
            t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
            t.check("x15", lab, lab, f"{desc}: sepc of the original trap")
        if fires:
            sd.log(t, "x15", "CAUSE", back=1)
            t.check("x15", 3, lab, f"{desc}: breakpoint first")
            sd.handler(t, "x15", back=1)
            t.check("x15", 3, lab, f"{desc}: breakpoint handled in M")
            sd.log(t, "x15", "TVAL", back=1)
            mt = "itrigger_tval_nonzero" if itr else "etrigger_tval_nonzero"
            t.check("x15", [1] if mut(mt) else 0, lab, f"{desc}: breakpoint mtval = 0")
            sd.log(t, "x15", "EPC", back=1)
            t.emit("csrr x14, stvec")
            t.emit("andi x13, x14, 1  // vectored")
            t.emit("andi x14, x14, -4  // BASE")
            if itr:
                t.emit("slli x13, x13, 2  // + 4 * cause 1 when vectored")
                t.emit("add x14, x14, x13")
            if mut("etrigger_epc_faulting") or mut("itrigger_epc_interrupted"):
                t.la("x14", lab)
            t.emit("sub x15, x15, x14")
            t.check("x15", 0, lab, f"{desc}: breakpoint mepc = the S handler entry (difference)")
            sd.origin(t, back=1)
            t.check("x15", 1, lab, f"{desc}: breakpoint taken from S")

    def run() -> None:
        def gated(bits: int, t2: int, fires: bool, desc: str) -> None:
            """Arm with tdata2 = t2 and read tdata2 back: a hart may support only some codes (the spec tells
            debuggers to read tdata2 back), so the outcome follows whether the selected code's bit is kept."""
            sd.arm(t, acc, typ, bits, t2)
            t.emit("csrr x6, CSR_TDATA2")
            t.emit(f"andi x6, x6, {sel}")
            if t2 & sel:
                sd.either(t, "x6", lambda: window(fires, desc))
            else:
                sd.either(
                    t,
                    "x6",
                    lambda: window(True, desc + " (tdata2 kept the selected code anyway)"),
                    lambda: window(fires, desc),
                )

        wrong = mut("etrigger_wrong_cause") or mut("itrigger_wrong_cause")
        if key in ("fire", "timing", "action0"):
            gated(mbit, sel, True, f"{'itrigger' if itr else 'etrigger'} on code {code}, trap from {mode}")
        elif key in ("config", "enable_num"):
            gated(mbit, sel, True, f"tdata2 selects code {code}")
            gated(mbit, 1 << 5, wrong, "tdata2 selects only code 5")
        else:
            other = sd.IE_S if mode == "U" else sd.IE_U
            gated(mbit, sel, not (mut("etrigger_u_ignored") and not itr and mode == "U"), f"{mode} bit set")
            gated(other, sel, False, "only the other mode's bit set")
        sd.disarm(t, acc)

    sd.probe(t, acc, [(typ, mbit)], [sel])
    sd.either(t, "x1", run)
    t.emit("csrw medeleg, x0")
    t.emit("csrw mideleg, x0")
    return t


def textra_v(mh: int | None = None, mhsel: int = 0, sval: int | None = None, ssel: int = 0, mask: int = 0) -> X:
    v32 = v64 = 0
    if mh is not None:
        v32 |= (mh << 26) | (mhsel << 23)
        v64 |= (mh << 51) | (mhsel << 48)
    if sval is not None:
        v32 |= ((sval & 0xFFFF) << 2) | ssel | ((mask & 3) << 18)
        v64 |= (sval << 2) | ssel | (mask << 36)
    return X(v32, v64)


def t_textra(rule: str) -> SdFile:
    rv64 = rule == "Sdtrig_textra64_sbytemask"
    t = sm(rule, req=["S"])
    t.rv64 = rv64
    if rv64:
        t.code.insert(0, "#if __riscv_xlen == 64")
        t._conds.append("__riscv_xlen == 64")
    acc = Acc(t)
    texts = {
        "Sdtrig_mcontrol6_textra": "If {csr-textra32} or {csr-textra64} are implemented for this trigger, it only "
        "matches when the conditions set there are satisfied.",
        "Sdtrig_textra32_mhselect_mcontext": "This trigger will only match or fire if the low bits of "
        "{csr-mcontext}/{csr-hcontext} equal {textra32-mhvalue}.",
        "Sdtrig_textra32_sselect_scontext": "This trigger will only match or fire if the low bits of {csr-scontext} "
        "equal {textra32-svalue}.",
        "Sdtrig_textra32_sbytemask": "When the least significant bit of this field is 1, it causes bits 7:0 in the "
        "comparison to be ignored, when {textra32-sselect}=1. When the next most significant bit of this field is 1, "
        "it causes bits 15:8 to be ignored in the comparison, when {textra32-sselect}=1.",
        "Sdtrig_textra64_sbytemask": "When the least significant bit of this field is 1, it causes bits 7:0 in the "
        "comparison to be ignored, when {textra64-sselect}=1. Likewise, the second bit controls the comparison of bits "
        "15:8, third bit controls the comparison of bits 23:16, and fourth bit controls the comparison of bits 31:24.",
        "Sdtrig_textra32_filter_modes": "Note that sselect and mhselect filtering apply in all modes, including M-mode "
        "and S-mode.",
        "Sdtrig_mscontext": "This optional register is an alias for {csr-scontext}.",
    }
    plans = {
        "Sdtrig_mcontrol6_textra": "A U-mode load trigger on A with tdata3 = mhselect 4, mhvalue 5 (kept when written): "
        "fires on lw A with mcontext = 5, not with mcontext = 4. With tdata3 = sselect 1, svalue 0x34: fires with "
        "scontext = 0x34, not with 0x35.",
        "Sdtrig_textra32_mhselect_mcontext": "mhselect = 4, mhvalue = 5 on a U-mode load trigger: mcontext = 5 fires, "
        "mcontext = 7 and 0x25 do not (the low bits must equal mhvalue).",
        "Sdtrig_textra32_sselect_scontext": "sselect = 1, svalue = 0x1234 on a U-mode load trigger: scontext = 0x1234 "
        "fires; 0x1235 and 0x1334 do not.",
        "Sdtrig_textra32_sbytemask": "sselect = 1, svalue = 0x12ff, sbytemask = 1: scontext = 0x1234 fires (bits 7:0 "
        "ignored), 0x1334 does not; sbytemask = 2, svalue = 0xff34: 0x1234 fires, 0x1235 does not.",
        "Sdtrig_textra64_sbytemask": "sselect = 1, svalue = 0x12345678 with sbytemask = 4 and svalue byte 2 changed: "
        "scontext = 0x12345678 fires; sbytemask = 8 with byte 3 changed: fires; byte 0 changed with sbytemask = 4: "
        "does not.",
        "Sdtrig_textra32_filter_modes": "An M-mode load trigger (m=1) on A with mhselect = 4, mhvalue = 5: lw A in M "
        "fires with mcontext = 5 and not with mcontext = 6. (mstatus.MIE = 1, MTE = 1 when tcontrol exists.)",
        "Sdtrig_mscontext": "When both scontext and mscontext read without a trap in M: writing scontext = 0x5a is "
        "read through mscontext, and writing mscontext = 0x3c through scontext.",
    }
    t.describe(
        source=XML,
        rule_text=texts[rule],
        context="tdata3 (textra), mcontext and scontext are optional: each is "
        "read in a trap window first, and a textra configuration is used only when tdata3 reads it back. "
        "textra64 (RV64): mhvalue 63:51, mhselect 50:48, sbytemask 39:36, svalue 33:2, sselect 1:0; textra32 "
        "(RV32): mhvalue 31:26, mhselect 25:23, sbytemask 19:18, svalue 17:2, sselect 1:0. Context values "
        "are small, inside the implemented widths when the configuration is kept." + TIMING,
        plan=plans[rule],
    )
    lab0 = t.label("tx")
    t.emit(f"{lab0}:", 0)
    if rule == "Sdtrig_mscontext":
        sd.has_csr(t, "scontext", "x1")
        sd.has_csr(t, "mscontext", "x9")
        t.emit("and x1, x1, x9")

        def ms() -> None:
            t.li("x6", 0x5A)
            t.emit("csrw CSR_SCONTEXT, x6")
            t.emit("csrr x9, CSR_SCONTEXT")
            t.emit("csrr x7, CSR_MSCONTEXT")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab0, "mscontext reads scontext (difference)")
            t.li("x6", 0x3C)
            t.emit("csrw CSR_MSCONTEXT, x6")
            t.emit("csrr x9, CSR_MSCONTEXT")
            t.emit("csrr x7, CSR_SCONTEXT")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab0, "scontext reads mscontext (difference)")
            t.emit("csrw CSR_SCONTEXT, x0")

        sd.either(t, "x1", ms)
        return t
    mctx = (
        rule in ("Sdtrig_textra32_mhselect_mcontext", "Sdtrig_textra32_filter_modes")
        or rule == "Sdtrig_mcontrol6_textra"
    )
    sctx = (
        rule in ("Sdtrig_textra32_sselect_scontext", "Sdtrig_textra32_sbytemask", "Sdtrig_textra64_sbytemask")
        or rule == "Sdtrig_mcontrol6_textra"
    )
    mmode = rule == "Sdtrig_textra32_filter_modes"
    if mmode:
        tcontrol_enable(t)
    mode = "M" if mmode else "U"
    low = LOAD | (sd.M if mmode else sd.U)

    def case(tx: X, ctxreg: str, ctxval: int, fires: bool, desc: str) -> None:
        """Arm with tdata3 = tx (skipped unless kept), set the context CSR, run lw A in mode."""
        sd.select(t, acc)
        t.emit("csrw CSR_TDATA1, x0")
        set_t2(t, A)
        t.emit("csrw CSR_TDATA2, x8")
        li_x(t, "x7", tx)
        t.emit("csrw CSR_TDATA3, x7")
        t.emit("csrr x6, CSR_TDATA3")
        t.emit("sub x6, x6, x7")
        t.emit("seqz x6, x6  // textra configuration kept")
        sd.mk(t, "x8", MC6, low)
        t.emit("csrw CSR_TDATA1, x8")

        def go() -> None:
            t.li("x7", ctxval)
            t.emit(f"csrw {ctxreg}, x7")
            t.la("x8", A)
            sd.fire(t, mode, ["lw x7, 0(x8)", "nop", "nop"], fires, desc, tval=[0, A] if fires else None)
            t.emit(f"csrw {ctxreg}, x0")

        sd.either(t, "x6", go)
        t.emit("csrw CSR_TDATA1, x0")
        t.emit("csrw CSR_TDATA3, x0")

    def run() -> None:
        mi = mut("textra_mcontext_ignored") or (mut("textra_m_exempt") and mmode)
        si = mut("textra_scontext_ignored")
        if mctx:
            sd.has_csr(t, "mcontext", "x7")

            def mc() -> None:
                case(textra_v(mh=5, mhsel=4), "CSR_MCONTEXT", 5, True, "mhselect=4 mhvalue=5, mcontext=5")
                for v in (6,) if mmode else (4, 7, 0x25) if rule != "Sdtrig_mcontrol6_textra" else (4,):
                    case(textra_v(mh=5, mhsel=4), "CSR_MCONTEXT", v, mi, f"mhselect=4 mhvalue=5, mcontext={v:#x}")

            sd.either(t, "x7", mc)
        if sctx:
            sd.has_csr(t, "scontext", "x7")

            def sc() -> None:
                if rule == "Sdtrig_textra64_sbytemask":
                    case(
                        textra_v(sval=0x12AB5678, ssel=1, mask=4),
                        "CSR_SCONTEXT",
                        0x12345678,
                        True,
                        "svalue byte 2 differs, sbytemask=4",
                    )
                    case(
                        textra_v(sval=0xAB345678, ssel=1, mask=8),
                        "CSR_SCONTEXT",
                        0x12345678,
                        True,
                        "svalue byte 3 differs, sbytemask=8",
                    )
                    case(
                        textra_v(sval=0x123456AB, ssel=1, mask=4),
                        "CSR_SCONTEXT",
                        0x12345678,
                        mut("sbytemask_ignored") and False or si,
                        "svalue byte 0 differs, sbytemask=4",
                    )
                    if mut("sbytemask_ignored"):
                        case(
                            textra_v(sval=0x12AB5678, ssel=1, mask=0),
                            "CSR_SCONTEXT",
                            0x12345678,
                            True,
                            "(mutant) byte 2 differs, no mask",
                        )
                elif rule == "Sdtrig_textra32_sbytemask":
                    case(
                        textra_v(sval=0x12FF, ssel=1, mask=1),
                        "CSR_SCONTEXT",
                        0x1234,
                        not mut("sbytemask_ignored"),
                        "svalue 0x12ff, sbytemask=1",
                    )
                    case(
                        textra_v(sval=0x12FF, ssel=1, mask=1),
                        "CSR_SCONTEXT",
                        0x1334,
                        si,
                        "svalue 0x12ff, sbytemask=1, scontext=0x1334",
                    )
                    case(
                        textra_v(sval=0xFF34, ssel=1, mask=2),
                        "CSR_SCONTEXT",
                        0x1234,
                        not mut("sbytemask_ignored"),
                        "svalue 0xff34, sbytemask=2",
                    )
                    case(
                        textra_v(sval=0xFF34, ssel=1, mask=2),
                        "CSR_SCONTEXT",
                        0x1235,
                        si,
                        "svalue 0xff34, sbytemask=2, scontext=0x1235",
                    )
                else:
                    sv = 0x34 if rule == "Sdtrig_mcontrol6_textra" else 0x1234
                    case(
                        textra_v(sval=sv, ssel=1), "CSR_SCONTEXT", sv, True, f"sselect=1 svalue={sv:#x}, scontext equal"
                    )
                    for v in (sv + 1,) if rule == "Sdtrig_mcontrol6_textra" else (sv + 1, sv + 0x100):
                        case(
                            textra_v(sval=sv, ssel=1),
                            "CSR_SCONTEXT",
                            v,
                            si,
                            f"sselect=1 svalue={sv:#x}, scontext={v:#x}",
                        )

            sd.either(t, "x7", sc)

    sd.probe(t, acc, [(MC6, low)], [A])
    t.comment("tdata3 may not exist at all (illegal instruction); per-trigger support is checked by read-back")
    sd.has_csr(t, "tdata3", "x9")
    sd.either(t, "x1", lambda: sd.either(t, "x9", run))
    return t


def gen() -> list[SdFile]:
    out = [t_action0(), t_execute(), t_loadstore(True), t_loadstore(False)]
    out += [t_match(*m) for m in MATCHES]
    out += [t_size(*s) for s in SIZES]
    out += [t_modebit(m) for m in ("U", "S", "VS", "VU")]
    out += [t_chain(r) for r in CHAIN_RULES]
    out += [t_hit(r) for r in HIT_RULES]
    out += [t_faulting(), t_priority()]
    out += [t_write0(), t_tdata_write(), t_size_support()]
    out += [t_tdata2_disabled(r) for r in ("Sdtrig_disable_trig", "Sdtrig_tdata2_disabled", "Sdtrig_tdata2_addr_sz1")]
    out += [t_dmode(r) for r in ("Sdtrig_tdata1_dmode_writable", "Sdtrig_tdata1_dmode_0", "Sdtrig_action1")]
    out += [t_type0(r) for r in ("Sdtrig_tdata1_data", "Sdtrig_tdata1_dmode_type_0", "Sdtrig_tdata1_type_rsv")]
    out += t_napot()
    out += [t_select_data(r) for r in ("Sdtrig_mcontrol6_select_data", "Sdtrig_mcontrol6_comparisons")]
    out += [t_trigger_modes()]
    out += [t_scontext(r) for r in ("Sdtrig_scontext_access", "Sdtrig_scontext_accessibility")]
    out += [
        t_hcontext(r)
        for r in (
            "Sdtrig_hcontext",
            "Sdtrig_hcontext_access",
            "Sdtrig_hcontext_implemented",
            "Sdtrig_hcontext_smstateen",
        )
    ]
    out += [t_icount(r) for r in ICOUNT_RULES]
    out += [
        t_enum(r)
        for r in (
            "Sdtrig_num_trigs_ge1",
            "Sdtrig_tselect_access",
            "Sdtrig_tselect_warl",
            "Sdtrig_tinfo_no_trigger",
            "Sdtrig_tinfo_support",
            "Sdtrig_mcontrol6_dependence",
            "Sdtrig_csr_mode",
        )
    ]
    out += [
        t_tcontrol(r)
        for r in (
            "Sdtrig_tcontrol_mpte",
            "Sdtrig_tcontrol_mte_mret",
            "Sdtrig_tcontrol_mte_disabled",
            "Sdtrig_tcontrol_mte_enabled",
        )
    ]
    out += [t_m_triggers(r) for r in ("Sdtrig_mcontrol6_m", "Sdtrig_icount_m", "Sdtrig_icount_exception")]
    out += [t_deleg()]
    out += [t_et(r) for r in ET_RULES]
    out += [
        t_textra(r)
        for r in (
            "Sdtrig_mcontrol6_textra",
            "Sdtrig_textra32_mhselect_mcontext",
            "Sdtrig_textra32_sselect_scontext",
            "Sdtrig_textra32_sbytemask",
            "Sdtrig_textra64_sbytemask",
            "Sdtrig_textra32_filter_modes",
            "Sdtrig_mscontext",
        )
    ]
    return out


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(Path(__file__).resolve().parents[1])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
