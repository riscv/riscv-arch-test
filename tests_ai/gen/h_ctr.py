# SPDX-License-Identifier: Apache-2.0
"""H suite: hcounteren and the counter virtual-instruction rules, and htimedelta."""

from __future__ import annotations

from typing import TYPE_CHECKING

import hlib
from aigen import X
from h_virt import new
from hlib import HYP, ILLEGAL, READS, enc_csr, hs_read, m_bits

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import TestFile

    Ctr = tuple[str, int, int, str]  # (name, CSR number, counteren bit, condition)

MUT = hlib.MUT
ZICNTR = "defined(ZICNTR_SUPPORTED)"
ZIHPM = "defined(ZIHPM_SUPPORTED)"

MUTANTS = {
    "hctr_ignored": "hcounteren=0 does not stop VS/VU counter reads",
    "hctr_illegal": "a counter read denied by hcounteren raises illegal- instead of virtual-instruction",
    "mctr_virtual": "a counter read denied by mcounteren raises virtual-instruction in VS/VU",
    "hctr_affects_hs": "hcounteren gates counter reads in HS-mode",
    "hctr_affects_u": "hcounteren gates counter reads in U-mode (V=0)",
    "vu_ignores_scounteren": "VU-mode counter reads ignore scounteren",
    "vs_uses_scounteren": "VS-mode counter reads are gated by scounteren",
    "high_illegal": "RV32 high-half counter reads denied by hcounteren raise illegal-instruction",
    "hcounteren_64bit": "hcounteren bits 63:32 are writable on RV64",
    "htimedelta_ignored": "time read in VS/VU-mode does not add htimedelta",
    "htimedelta_in_hs": "time read in HS-mode adds htimedelta",
    "htimedelta_carry_lost": "RV32: the carry from time + htimedelta low halves does not reach timeh",
    "htimedelta_partial": "htimedelta is not a full 64-bit read/write register",
}


def ctrs() -> list[tuple[str, int, int, str]]:
    """(name, CSR number, counteren bit, condition) for every non-high counter."""
    out = [("cycle", 0xC00, 0, ZICNTR), ("time", 0xC01, 1, ZICNTR), ("instret", 0xC02, 2, ZICNTR)]
    out += [(f"hpmcounter{n}", 0xC00 + n, n, ZIHPM) for n in range(3, 32)]
    return out


SUBSET = ["cycle", "time", "instret", "hpmcounter3", "hpmcounter17", "hpmcounter31"]


def ctr_by(name: str) -> tuple[str, int, int, str]:
    return next(c for c in ctrs() if c[0] == name)


def high(c: tuple[str, int, int, str]) -> tuple[str, int, int, str]:
    return (c[0] + "h", c[1] + 0x80, c[2], c[3])


def expect(mode: str, m: int, h: int, s: int) -> str:
    """Outcome of a counter read with mcounteren/hcounteren/scounteren bits m, h, s."""
    if MUT == "hctr_ignored":
        h = 1
    if MUT == "vu_ignores_scounteren" and mode == "VU":
        s = 1
    if mode == "S":
        return "virtual" if (MUT == "hctr_affects_hs" and m and not h) else ("ok" if m else "illegal")
    if mode == "U":
        if MUT == "hctr_affects_u" and m and s and not h:
            return "illegal"
        return "ok" if m and s else "illegal"
    if not m:
        return "virtual" if MUT == "mctr_virtual" else "illegal"
    need = h and (s or (mode == "VS" and MUT != "vs_uses_scounteren"))
    if need:
        return "ok"
    return "illegal" if MUT == "hctr_illegal" else "virtual"


def ctr_read(
    t: TestFile, mode: str, c: tuple[str, int, int, str], i: int, exp: str, desc: str, is_high: bool = False
) -> str:
    name, num, _, _ = c
    form = READS[i % 2]
    asm, f3, rd, rs1, kind, _ = form
    if is_high and exp == "virtual" and MUT == "high_illegal":
        exp = "illegal"
    cause = hlib.CAUSE[exp]
    tval = None if exp == "ok" else [0, enc_csr(num, f3, rd, rs1)]
    return t.window(mode, [asm.format(c=hex(num)) + f"  // {name}"], cause, f"{kind} of {name} ({desc})", tval)


def set_bit(t: TestFile, reg: str, b: int, on: bool) -> None:
    """Set or clear bit b of mcounteren (T-SBI), hcounteren or scounteren."""
    if reg == "m":
        m_bits(t, "mcounteren", 1 << b, on, f"M-mode: mcounteren[{b}] = {int(on)}")
    else:
        hlib.hs_bits(t, f"{reg}counteren", 1 << b, on, f"{reg}counteren[{b}] = {int(on)}")


def probe(t: TestFile, reg: str, b: int, dst: str) -> None:
    """dst = bit b of mcounteren/hcounteren/scounteren as read back (0 or 1)."""
    if reg == "m":
        t.tsbi_csr("READ", "MCOUNTEREN")
        t.emit(f"srli {dst}, a0, {b}")
    else:
        hs_read(t, dst, f"{reg}counteren")
        t.emit(f"srli {dst}, {dst}, {b}")
    t.emit(f"andi {dst}, {dst}, 1")


PROBE_REG = {"m": "x1", "h": "x8", "s": "x9"}


def case(
    t: TestFile,
    c: tuple[str, int, int, str],
    want: dict[str, int],
    body: Callable[[dict[str, int]], object],
    collapse: bool = False,
) -> None:
    """Set the counter-enable bits to `want` (keys m, h, s), probe the ones requested as 1 (they may be
    read-only zero), and call body(actual) on each run-time branch with the values actually held. With
    collapse, only the branch where every requested bit is held runs body; otherwise the case is skipped."""
    b = c[2]
    for k in ("m", "h", "s"):
        set_bit(t, k, b, bool(want[k]))
    probes = [k for k in ("m", "h", "s") if want[k]]
    for k in probes:
        probe(t, k, b, PROBE_REG[k])
    if collapse and len(probes) > 1:
        for k in probes[1:]:
            t.emit(f"and x1, x1, {PROBE_REG[k]}" if PROBE_REG[probes[0]] == "x1" else "")
        t.either("x1", lambda: body(dict(want)), lambda: t.comment("an enable bit is read-only zero: skipped"))
        return

    def branch(rest: list[str], actual: dict[str, int]) -> None:
        if not rest:
            body(actual)
            return
        k = rest[0]
        t.either(PROBE_REG[k], lambda: branch(rest[1:], {**actual, k: 1}), lambda: branch(rest[1:], {**actual, k: 0}))

    branch(probes, dict(want))


def restore(t: TestFile) -> None:
    t.comment("restore all counter enables")
    t.tsbi_csr("SET", "MCOUNTEREN", imm=-1)
    t.emit("li x7, -1")
    t.emit(f"csrw {hex(hlib.csr_num('hcounteren'))}, x7")
    t.emit(f"csrw {hex(hlib.csr_num('scounteren'))}, x7")


def guarded(t: TestFile, c: Ctr, fn: Callable[[], object]) -> None:
    with t.only_if(c[3]):
        fn()


def desc(a: dict[str, int]) -> str:
    return f"mcounteren={a['m']}, hcounteren={a['h']}, scounteren={a['s']}"


ISSUE_HSQ = (
    "HS-qualified (hypervisor.adoc, Virtual Instruction): a counter read is valid in HS-mode when the "
    "mcounteren bit is 1, so with mcounteren=1 a denial below HS is a virtual-instruction exception and with "
    "mcounteren=0 an illegal-instruction exception."
)
ISSUE_WARL = (
    "Counter-enable bits in mcounteren, hcounteren and scounteren may be read-only zero; each case sets the "
    "requested bits, reads them back and expects the outcome for the values actually held."
)


def gen() -> list[TestFile]:
    tests: list[TestFile] = []

    # ---- H_virtinst_vs_nonhighctr_h0_m1 ----
    t = new("H_virtinst_vs_nonhighctr_h0_m1")
    t.describe(
        source=HYP,
        rule_text="in VS-mode, attempts to access a non-high-half counter CSR when the corresponding bit in "
        "hcounteren is 0 and the same bit in mcounteren is 1;",
        context="One of the cases that raise a virtual-instruction exception. Counters: cycle, time, instret "
        "(Zicntr) and hpmcounter3-31 (Zihpm). " + ISSUE_WARL,
        issues=ISSUE_HSQ,
        plan="1. For every counter: mcounteren=1, hcounteren=0: a VS-mode read (csrrs rs1=x0 or csrrsi uimm=0) "
        "raises virtual-instruction with xtval 0 or the bits (illegal-instruction if the mcounteren bit is "
        "read-only zero).\n"
        "2. For cycle, time, instret, hpmcounter3, 17, 31: mcounteren=1, hcounteren=1 succeeds; mcounteren=0, "
        "hcounteren=0 raises illegal-instruction.",
    )
    for i, c in enumerate(ctrs()):

        def vs_fn(c: Ctr = c, i: int = i) -> None:
            case(
                t,
                c,
                {"m": 1, "h": 0, "s": 1},
                lambda a: ctr_read(t, "VS", c, i, expect("VS", a["m"], 0, a["s"]), desc(a)),
            )
            if c[0] in SUBSET:
                case(
                    t,
                    c,
                    {"m": 1, "h": 1, "s": 1},
                    lambda a: ctr_read(t, "VS", c, i + 1, expect("VS", a["m"], a["h"], a["s"]), desc(a)),
                )
                case(
                    t,
                    c,
                    {"m": 0, "h": 0, "s": 1},
                    lambda a: ctr_read(t, "VS", c, i, expect("VS", 0, 0, a["s"]), desc(a)),
                )

        guarded(t, c, vs_fn)
    restore(t)
    tests.append(t)

    # ---- H_virtinst_vs32_highctr_h0_m1 ----
    t = new("H_virtinst_vs32_highctr_h0_m1")
    t.describe(
        source=HYP,
        rule_text="in VS-mode, if XLEN=32, attempts to access a high-half counter CSR when the corresponding bit "
        "in hcounteren is 0 and the same bit in mcounteren is 1;",
        context="High halves: cycleh, timeh, instreth (Zicntr), hpmcounter3h-31h (Zihpm), gated by the same "
        "counter-enable bits as their low halves. On RV64 the high-half addresses are not CSRs: an access is "
        "not valid in HS-mode either, so VS-mode raises illegal-instruction. " + ISSUE_WARL,
        issues=ISSUE_HSQ,
        plan="1. RV32, every high-half counter: mcounteren=1, hcounteren=0 raises virtual-instruction in VS-mode "
        "(xtval 0 or the bits).\n"
        "2. RV32, cycleh, timeh, instreth, hpmcounter3h, 17h, 31h: mcounteren=1, hcounteren=1 succeeds; "
        "mcounteren=0 raises illegal-instruction.\n"
        "3. RV64: VS-mode reads of cycleh, timeh and hpmcounter3h raise illegal-instruction with every enable "
        "set.",
    )
    with t.rv32_only():
        for i, c in enumerate(ctrs()):
            hc = high(c)

            def vs32_fn(c: Ctr = c, hc: Ctr = hc, i: int = i) -> None:
                case(
                    t,
                    c,
                    {"m": 1, "h": 0, "s": 1},
                    lambda a: ctr_read(t, "VS", hc, i, expect("VS", a["m"], 0, 1), desc(a), True),
                )
                if c[0] in SUBSET:
                    case(
                        t,
                        c,
                        {"m": 1, "h": 1, "s": 1},
                        lambda a: ctr_read(t, "VS", hc, i, expect("VS", a["m"], a["h"], 1), desc(a), True),
                    )
                    case(
                        t,
                        c,
                        {"m": 0, "h": 1, "s": 1},
                        lambda a: ctr_read(t, "VS", hc, i, expect("VS", 0, a["h"], 1), desc(a), True),
                    )

            guarded(t, c, vs32_fn)
    with t.rv64_only():
        for nm in ("cycle", "time", "hpmcounter3"):
            c = ctr_by(nm)
            guarded(t, c, lambda c=c: ctr_read(t, "VS", high(c), 0, "illegal", "RV64: not a CSR"))
    restore(t)
    tests.append(t)

    # ---- VU rules ----
    for rule, is_high in (("H_virtinst_vu_nonhighctr_h0_s0_m1", False), ("H_virtinst_vu32_highctr_h0_s0_m1", True)):
        t = new(rule)
        hi = "high-half " if is_high else "non-high-half "
        t.describe(
            source=HYP,
            rule_text=f"in VU-mode, {'if XLEN=32, ' if is_high else ''}attempts to access a {hi}counter CSR when "
            "the corresponding bit in either hcounteren or scounteren is 0 and the same bit in mcounteren is 1;",
            context="One of the cases that raise a virtual-instruction exception. VU-mode needs the bit in all "
            "three registers. " + ISSUE_WARL + (" On RV64 the file has nothing to test." if is_high else ""),
            issues=ISSUE_HSQ,
            plan="1. For cycle, time, instret, hpmcounter3, 17, 31"
            + (" (high halves, RV32)" if is_high else "")
            + ", with mcounteren=1: (hcounteren, scounteren) = (0,1), (1,0), (0,0) raise virtual-instruction in "
            "VU-mode (xtval 0 or the bits), and (1,1) succeeds.\n"
            "2. mcounteren=0 with hcounteren=scounteren=1 raises illegal-instruction.",
        )

        def body(t: TestFile = t, is_high: bool = is_high) -> None:
            for i, nm in enumerate(SUBSET):
                c = ctr_by(nm)
                rc = high(c) if is_high else c

                def vu_fn(c: Ctr = c, rc: Ctr = rc, i: int = i) -> None:
                    for h, s in ((0, 1), (1, 0), (0, 0), (1, 1)):
                        case(
                            t,
                            c,
                            {"m": 1, "h": h, "s": s},
                            lambda a, h=h: ctr_read(
                                t, "VU", rc, i + h, expect("VU", a["m"], a["h"], a["s"]), desc(a), is_high
                            ),
                        )
                    case(
                        t,
                        c,
                        {"m": 0, "h": 1, "s": 1},
                        lambda a: ctr_read(t, "VU", rc, i, expect("VU", 0, a["h"], a["s"]), desc(a), is_high),
                    )

                guarded(t, c, vu_fn)
            restore(t)

        if is_high:
            with t.rv32_only():
                body()
        else:
            body()
        tests.append(t)

    # ---- hcounteren_op ----
    t = new("hcounteren_op")
    t.describe(
        source=HYP,
        rule_text="When the CY, TM, IR, or HPMn bit in the hcounteren register is clear, attempts to read the "
        "cycle, time, instret, or hpmcountern register while V=1 will cause a virtual-instruction exception if "
        "the same bit in mcounteren is 1.",
        context="hcounteren matters only when V=1 and only when mcounteren permits the access: with mcounteren=0 "
        "the read raises illegal-instruction whatever hcounteren holds. HS-mode and U-mode (V=0) are governed "
        "by mcounteren and scounteren only. " + ISSUE_WARL,
        issues=ISSUE_HSQ,
        plan="1. For cycle, time, instret, hpmcounter3, 17, 31 with hcounteren=0, mcounteren=1, scounteren=1: "
        "VS-mode and VU-mode reads raise virtual-instruction; HS-mode and U-mode reads succeed.\n"
        "2. mcounteren=0: VS-mode reads raise illegal-instruction with hcounteren=0 and with hcounteren=1.",
    )
    for i, nm in enumerate(SUBSET):
        c = ctr_by(nm)

        def op_fn(c: Ctr = c, i: int = i) -> None:
            def b1(a: dict[str, int]) -> None:
                for mode in ("VS", "VU", "S", "U"):
                    ctr_read(t, mode, c, i, expect(mode, a["m"], 0, a["s"]), desc(a))

            case(t, c, {"m": 1, "h": 0, "s": 1}, b1)
            for h in (0, 1):
                case(
                    t,
                    c,
                    {"m": 0, "h": h, "s": 1},
                    lambda a: ctr_read(t, "VS", c, i, expect("VS", 0, a["h"], 1), desc(a)),
                )

        guarded(t, c, op_fn)
    restore(t)
    tests.append(t)

    # ---- hcounteren_set_op ----
    t = new("hcounteren_set_op")
    t.describe(
        source=HYP,
        rule_text="When one of these bits is set, access to the corresponding register is permitted when V=1, "
        "unless prevented for some other reason.",
        context="Other reasons: mcounteren=0 (illegal-instruction), scounteren=0 in VU-mode "
        "(virtual-instruction), and writes, since the counters are read-only (illegal-instruction). " + ISSUE_WARL,
        issues=ISSUE_HSQ,
        plan="1. For every counter with mcounteren, hcounteren and scounteren set: VS-mode and VU-mode reads "
        "succeed.\n"
        "2. For cycle, time, instret, hpmcounter3: with hcounteren=1, a VU-mode read with scounteren=0 raises "
        "virtual-instruction, a VS-mode read with mcounteren=0 raises illegal-instruction, and a VS-mode write "
        "(csrrw) raises illegal-instruction.",
    )
    for i, c in enumerate(ctrs()):

        def set_fn(c: Ctr = c, i: int = i) -> None:
            case(
                t,
                c,
                {"m": 1, "h": 1, "s": 1},
                lambda a: [
                    ctr_read(t, mode, c, i, expect(mode, a["m"], a["h"], a["s"]), desc(a)) for mode in ("VS", "VU")
                ],
                collapse=True,
            )
            if c[0] in SUBSET[:4]:
                case(
                    t,
                    c,
                    {"m": 1, "h": 1, "s": 0},
                    lambda a: ctr_read(t, "VU", c, i, expect("VU", a["m"], a["h"], 0), desc(a)),
                )
                case(
                    t,
                    c,
                    {"m": 0, "h": 1, "s": 1},
                    lambda a: ctr_read(t, "VS", c, i, expect("VS", 0, a["h"], 1), desc(a)),
                )
                set_bit(t, "m", c[2], True)
                t.emit("li x6, 0")
                t.window(
                    "VS",
                    [f"csrrw x7, {hex(c[1])}, x6  // {c[0]}"],
                    ILLEGAL,
                    f"write of read-only {c[0]} (hcounteren=1)",
                    [0, enc_csr(c[1], 1, 7, 6)],
                )

        guarded(t, c, set_fn)
    restore(t)
    tests.append(t)

    # ---- hcounteren_scounteren_vu_op ----
    t = new("hcounteren_scounteren_vu_op")
    t.describe(
        source=HYP,
        rule_text="In VU-mode, a counter is not readable unless the applicable bits are set in both hcounteren "
        "and scounteren.",
        context="scounteren does not gate VS-mode (it gates the mode below VS), and hcounteren does not gate "
        "U-mode (V=0). " + ISSUE_WARL,
        issues=ISSUE_HSQ,
        plan="1. For cycle, time, instret, hpmcounter3, 17, 31 with mcounteren=1, every (hcounteren, "
        "scounteren) pair: VU-mode reads succeed only for (1,1), otherwise raise virtual-instruction.\n"
        "2. (hcounteren, scounteren) = (1,0): a VS-mode read succeeds.\n"
        "3. (0,1): a U-mode read succeeds.",
    )
    for i, nm in enumerate(SUBSET):
        c = ctr_by(nm)

        def vu_op_fn(c: Ctr = c, i: int = i) -> None:
            for h, s in ((0, 0), (0, 1), (1, 0), (1, 1)):

                def b(a: dict[str, int], h: int = h, s: int = s) -> None:
                    ctr_read(t, "VU", c, i, expect("VU", a["m"], a["h"], a["s"]), desc(a))
                    if (h, s) == (1, 0):
                        ctr_read(t, "VS", c, i + 1, expect("VS", a["m"], a["h"], 0), desc(a))
                    if (h, s) == (0, 1):
                        ctr_read(t, "U", c, i + 1, expect("U", a["m"], 0, a["s"]), desc(a))

                case(t, c, {"m": 1, "h": h, "s": s}, b)

        guarded(t, c, vu_op_fn)
    restore(t)
    tests.append(t)

    # ---- hcounteren_sz ----
    t = new("hcounteren_sz")
    t.describe(
        source=HYP,
        rule_text="The counter-enable register hcounteren is a 32-bit register that controls the availability of "
        "the hardware performance monitoring counters to the guest virtual machine.",
        context="On RV64 the CSR reads as XLEN bits, so bits 63:32 read zero.",
        plan="1. HS-mode writes all ones to hcounteren: on RV64 bits 63:32 read 0.\n"
        "2. HS-mode writes zero: hcounteren reads 0.\n"
        "3. All eight CSR instruction forms on hcounteren execute in HS-mode.",
    )
    num = hex(hlib.csr_num("hcounteren"))
    lab = t.label("sz")
    t.emit("li x7, -1")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrw {num}, x7")
    t.emit(f"csrr x7, {num}")
    with t.rv64_only():
        t.check_masked(
            "x7",
            X(0, 0xFFFFFFFF00000000),
            X(0, 0xFFFFFFFF00000000 if MUT == "hcounteren_64bit" else 0),
            lab,
            "hcounteren bits 63:32 read 0 after writing all ones",
        )
    t.emit(f"csrw {num}, x0")
    t.emit(f"csrr x7, {num}")
    t.check("x7", 0, lab, "hcounteren reads 0 after writing 0")
    for form in hlib.FORMS:
        t.emit("li x6, -1")
        hlib.csr_window(t, "S", "hcounteren", form, "ok", "HS-mode")
    restore(t)
    tests.append(t)

    # ---- hcounteren_warl ----
    t = new("hcounteren_warl")
    t.describe(
        source=HYP,
        rule_text="hcounteren must be implemented. However, any of the bits may be read-only zero, indicating "
        "reads to the corresponding counter will cause an exception when V=1. Hence, they are effectively WARL "
        "fields.",
        context="A read-only-zero bit must behave as a cleared bit: with mcounteren set, the VS-mode read raises "
        "virtual-instruction. A writable bit holds what is written.",
        plan="1. HS-mode reads and writes hcounteren without a trap.\n"
        "2. W = hcounteren after writing all ones. Writing 0 reads 0; writing each of bits 0, 1, 2, 3, 17, 31 "
        "alone reads that bit if it is in W, else 0; writing ~W reads 0.\n"
        "3. For cycle, time, instret, hpmcounter3, 17, 31 with mcounteren set: if the hcounteren bit is "
        "read-only zero, a VS-mode read raises virtual-instruction; if writable and set, it succeeds.",
    )
    t.emit("li x7, -1")
    t.emit(f"csrw {num}, x7")
    t.emit(f"csrr x1, {num}  // W")
    for b in (0, 1, 2, 3, 17, 31):
        lab = t.label("bit")
        t.li("x6", 1 << b)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {num}, x6")
        t.emit(f"csrr x7, {num}")
        t.emit("and x6, x6, x1")
        t.emit("xor x5, x7, x6")
        t.emit("seqz x5, x5")
        t.check_bool("x5", lab, f"writing hcounteren = bit {b} alone reads bit {b} & W")
    lab = t.label("notw")
    t.emit(f"{lab}:", 0)
    t.emit("not x6, x1")
    t.emit(f"csrw {num}, x6")
    t.emit(f"csrr x7, {num}")
    t.check("x7", 0, lab, "writing ~W to hcounteren reads 0")
    for i, nm in enumerate(SUBSET):
        c = ctr_by(nm)

        def warl_fn(c: Ctr = c, i: int = i) -> None:
            set_bit(t, "m", c[2], True)
            probe(t, "m", c[2], "x1")
            set_bit(t, "h", c[2], True)
            probe(t, "h", c[2], "x8")

            def m_on() -> None:
                t.either(
                    "x8",
                    lambda: ctr_read(t, "VS", c, i, "ok", "hcounteren bit writable and set"),
                    lambda: ctr_read(
                        t,
                        "VS",
                        c,
                        i,
                        "ok" if MUT == "hcounteren_ro0_enables" else expect("VS", 1, 0, 1),
                        "hcounteren bit read-only zero",
                    ),
                )

            t.either("x1", m_on, lambda: t.comment("mcounteren bit read-only zero"))

        guarded(t, c, warl_fn)
    restore(t)
    tests.append(t)

    # ---- H_cause_virtual_instruction_high ----
    t = new("H_cause_virtual_instruction_high")
    t.describe(
        source=HYP,
        rule_text="A special rule applies for CSR instructions that access 32-bit high-half CSRs such as cycleh "
        "and htimedeltah. When V=1 and XLEN=32, an invalid attempt to access a high-half CSR raises a "
        "virtual-instruction exception instead of an illegal-instruction exception if the same CSR instruction "
        "for the corresponding low-half CSR (e.g.cycle or htimedelta) is HS-qualified.",
        context="RV32 only (the file passes trivially on RV64). The rule compares with the same instruction on "
        "the low half: a read of cycleh is HS-qualified when mcounteren.CY=1, a write of cycleh never is "
        "(cycle is read-only), htimedeltah and hedelegh accesses are (htimedelta and hedeleg are HS CSRs), and "
        "mstatush is not (mstatus is M-level). " + ISSUE_WARL,
        plan="1. RV32, VS-mode and VU-mode: htimedeltah and hedelegh reads and writes raise "
        "virtual-instruction.\n"
        "2. cycleh and instreth (Zicntr): with mcounteren=1, hcounteren=0 a read raises virtual-instruction; "
        "with mcounteren=0 it raises illegal-instruction; a write (csrrw, all enables set) raises "
        "illegal-instruction.\n"
        "3. mstatush read in VS-mode raises illegal-instruction.",
    )
    with t.rv32_only():
        hlib.CSRS.setdefault("mstatush", (0x310, "M", None))
        for nm in ("htimedeltah", "hedelegh"):
            for mode in ("VS", "VU"):
                hlib.csr_window(
                    t, mode, nm, hlib.FORMS[0], "illegal" if MUT == "high_illegal" else "virtual", "RV32 high half"
                )
                hs_read(t, "x6", nm)
                hlib.csr_window(
                    t, mode, nm, hlib.FORMS[1], "illegal" if MUT == "high_illegal" else "virtual", "RV32 high half"
                )
        for i, nm in enumerate(("cycle", "instret")):
            c = ctr_by(nm)
            hc = high(c)

            def high_fn(c: Ctr = c, hc: Ctr = hc, i: int = i) -> None:
                case(
                    t,
                    c,
                    {"m": 1, "h": 0, "s": 1},
                    lambda a: ctr_read(t, "VS", hc, i, expect("VS", a["m"], 0, 1), desc(a), True),
                )
                case(
                    t,
                    c,
                    {"m": 0, "h": 1, "s": 1},
                    lambda a: ctr_read(t, "VS", hc, i, expect("VS", 0, a["h"], 1), desc(a), True),
                )
                case(t, c, {"m": 1, "h": 1, "s": 1}, lambda a: None)
                t.emit("li x6, 0")
                t.window(
                    "VS",
                    [f"csrrw x7, {hex(hc[1])}, x6  // {hc[0]}"],
                    ILLEGAL,
                    f"write of read-only {hc[0]}",
                    [0, enc_csr(hc[1], 1, 7, 6)],
                )

            guarded(t, c, high_fn)
        hlib.csr_window(t, "VS", "mstatush", hlib.FORMS[0], "illegal", "M-level high half")
    restore(t)
    tests.append(t)

    tests += gen_htimedelta()
    return tests


# ---------------------------------------------------------------- htimedelta
HTD, HTDH = hlib.csr_num("htimedelta"), hlib.csr_num("htimedeltah")


def wr_htd(t: TestFile, v: int) -> None:
    with t.rv64_only():
        t.load("x7", v, "htimedelta")
        t.emit(f"csrw {hex(HTD)}, x7  // htimedelta")
    with t.rv32_only():
        t.load("x7", v >> 32, "htimedeltah")
        t.emit(f"csrw {hex(HTDH)}, x7  // htimedeltah")
        t.load("x7", v & 0xFFFFFFFF, "htimedelta low")
        t.emit(f"csrw {hex(HTD)}, x7  // htimedelta")


def time_enabled(t: TestFile, body: Callable[[], object]) -> None:
    """Run body when mcounteren.TM, hcounteren.TM and scounteren.TM all read 1 (else nothing to test)."""
    case(
        t,
        ("time", 0xC01, 1, ZICNTR),
        {"m": 1, "h": 1, "s": 1},
        lambda a: body() if a["m"] and a["h"] and a["s"] else t.comment("time not readable below M-mode"),
    )


def gen_htimedelta() -> list[TestFile]:
    tests = []
    m64 = (1 << 64) - 1

    t = new("htimedelta_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="The htimedelta CSR is a 64-bit read/write register that contains the delta between the value "
        "of the time CSR and the value returned in VS-mode or VU-mode. That is, reading the time CSR in VS or VU "
        "mode returns the sum of the contents of htimedelta and the actual value of time.",
        context="time keeps running, so the test brackets each VS/VU read with HS-mode reads t0 (before entering) "
        "and t1 (after leaving) and requires t0 <= read - htimedelta <= t1 (unsigned, mod 2^64). On RV32 the "
        "check uses the low word (timeh with carries is htimedeltah_sz_acc_op). time must be readable below "
        "M-mode (mcounteren.TM, hcounteren.TM, scounteren.TM set); if a bit is read-only zero the time checks "
        "are skipped.",
        plan="1. HS-mode writes htimedelta (and htimedeltah on RV32) with 0, all ones, 2^63, 2^40 + 5 and random "
        "values and reads them back exactly.\n"
        "2. For htimedelta = 0, 2^40, -2^40 and all ones: a time read in VS-mode and in VU-mode returns time + "
        "htimedelta.\n"
        "3. HS-mode and U-mode (V=0) time reads are not offset: with htimedelta = 2^40 they lie between "
        "bracketing HS-mode reads.",
    )
    with t.only_if(ZICNTR):
        vals = [0, m64, 1 << 63, (1 << 40) + 5, t.rand(64), t.rand(64)]
        for v in vals:
            exp = v & 0xFFFFFFFF if MUT == "htimedelta_partial" else v
            wr_htd(t, v)
            lab = t.label("rt")
            t.emit(f"{lab}:", 0)
            with t.rv64_only():
                t.emit(f"csrr x7, {hex(HTD)}")
                t.check("x7", exp, lab, f"htimedelta reads back {hex(v)}")
            with t.rv32_only():
                t.emit(f"csrr x7, {hex(HTD)}")
                t.check("x7", exp & 0xFFFFFFFF, lab, f"htimedelta reads back the low half of {hex(v)}")
                t.emit(f"csrr x7, {hex(HTDH)}")
                t.check("x7", exp >> 32, lab, f"htimedeltah reads back the high half of {hex(v)}")

        def offsets() -> None:
            for v, nm in ((0, "0"), (1 << 40, "2^40"), ((1 << 64) - (1 << 40), "-2^40"), (m64, "all ones")):
                wr_htd(t, v)
                for mode in ("VS", "VU", "S", "U"):
                    eff = v if mode in ("VS", "VU") else 0
                    if MUT == "htimedelta_ignored" and mode in ("VS", "VU"):
                        eff = 0
                    if MUT == "htimedelta_in_hs" and mode in ("S", "U"):
                        eff = v
                    if mode in ("S", "U") and v != 1 << 40:
                        continue
                    t.emit("csrr x8, time  // t0")
                    lab = t.window(mode, ["csrr x7, time"], "ok", f"time read, htimedelta={nm}")
                    t.emit("csrr x9, time  // t1")
                    t.load("x6", X(eff & 0xFFFFFFFF, eff), "expected offset")
                    t.emit("sub x7, x7, x6")
                    t.emit("sub x7, x7, x8")  # read - delta - t0
                    t.emit("sub x9, x9, x8")  # t1 - t0
                    t.emit("sltu x7, x9, x7")
                    t.emit("xori x7, x7, 1")
                    t.check_bool(
                        "x7",
                        lab,
                        f"time read in {mode}-mode = time + {'htimedelta' if mode[0] == 'V' else '0'}"
                        f" (htimedelta={nm}), between bracketing HS-mode reads",
                    )
            wr_htd(t, 0)

        time_enabled(t, offsets)
        wr_htd(t, 0)
        restore(t)
    tests.append(t)

    t = new("htimedeltah_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="When XLEN=32, htimedeltah is a 32-bit read/write register that aliases bits 63:32 of "
        "htimedelta. Register htimedeltah does not exist when XLEN=64.",
        context="The sum time + htimedelta is 64-bit, so on RV32 a carry out of the low halves must reach timeh "
        "as read in VS/VU-mode. The test sets the low half of htimedelta to 2^32 - t0_lo, where t0_lo "
        "is the low half of time just read, so the low-half sum carries; timeh read in VS/VU must then be "
        "time_hi + htimedeltah + 1 (or + 2 if time_hi itself advanced). On RV64, htimedeltah (0x615) is not a "
        "CSR: HS-mode access raises illegal-instruction.",
        plan="1. RV32: writes of htimedeltah do not change htimedelta (low half) and vice versa; all eight forms "
        "on htimedeltah execute in HS-mode with exact results.\n"
        "2. RV32, with carry: timeh read in VS-mode and in VU-mode equals time_hi + htimedeltah + 1 (bracketed); "
        "the low half read is time_lo + htimedelta_lo, within the bracket.\n"
        "3. RV32, no carry (htimedelta low half 0x10 and htimedeltah 5): timeh read in VS-mode is time_hi + 5 "
        "(bracketed).\n"
        "4. RV64: HS-mode read of htimedeltah raises illegal-instruction.",
    )
    with t.rv32_only():
        lab = t.label("alias")
        t.emit(f"{lab}:", 0)
        t.load("x7", 0x13579BDF, "low")
        t.emit(f"csrw {hex(HTD)}, x7")
        t.load("x7", 0x2468ACE0, "high")
        t.emit(f"csrw {hex(HTDH)}, x7")
        t.emit(f"csrr x7, {hex(HTD)}")
        t.check("x7", 0x13579BDF, lab, "writing htimedeltah leaves the low half of htimedelta")
        t.load("x7", 0x0F0F0F0F, "low")
        t.emit(f"csrw {hex(HTD)}, x7")
        t.emit(f"csrr x7, {hex(HTDH)}")
        t.check("x7", 0x2468ACE0, lab, "writing htimedelta (low) leaves htimedeltah")
        old = 0x2468ACE0
        for form in hlib.FORMS:
            src = t.rand(32)
            t.load("x7", old, "old htimedeltah")
            t.emit(f"csrw {hex(HTDH)}, x7")
            t.load("x6", src, "source")
            lab = hlib.csr_window(t, "S", "htimedeltah", form, "ok", "HS-mode")
            _, newv = hlib.form_value(form, old, src, 32)
            if form[2]:
                t.check("x7", old, lab, f"{form[4]} of htimedeltah returns the old value")
            hs_read(t, "x7", "htimedeltah")
            t.check("x7", newv, lab, f"{form[4]} of htimedeltah writes {hex(newv)}")
            old = newv

        def carry_cases() -> None:
            for mode in ("VS", "VU"):
                for carry in (1, 0):
                    dh = 5
                    t.load("x7", dh, "htimedeltah")
                    t.emit(f"csrw {hex(HTDH)}, x7")
                    t.emit("csrr x8, timeh  // h0")
                    if carry:
                        t.emit("csrr x7, time")
                        t.emit("neg x7, x7  // low = 2^32 - t0_lo: time_lo + low carries for time_lo >= t0_lo > 0")
                    else:
                        t.li("x7", 0x10)
                    t.emit(f"csrw {hex(HTD)}, x7")
                    lab = t.window(
                        mode,
                        ["csrr x7, timeh", "csrr x6, time"],
                        "ok",
                        f"timeh read, {'carry' if carry else 'no carry'} from the low halves",
                    )
                    t.emit("csrr x9, timeh  // h1")
                    inc = carry and MUT != "htimedelta_carry_lost"
                    t.emit(f"addi x7, x7, -{dh + (1 if inc else 0)}")
                    t.emit("sub x7, x7, x8  // read_hi - dh - carry - h0")
                    t.emit("sub x9, x9, x8  // h1 - h0")
                    t.emit("sltu x7, x9, x7")
                    t.emit("xori x7, x7, 1")
                    t.check_bool(
                        "x7",
                        lab,
                        f"timeh in {mode}-mode = time_hi + htimedeltah"
                        f"{' + 1 (carry from the low half)' if carry else ''}",
                    )
                    if carry:
                        t.li("x7", 0x01000000)
                        t.emit("sltu x6, x6, x7")
                        t.check_bool(
                            "x6",
                            lab,
                            f"time (low) in {mode}-mode = time_lo + htimedelta_lo "
                            "(the ticks elapsed since t0, below 2^24)",
                        )
            wr_htd(t, 0)

        with t.only_if(ZICNTR):
            time_enabled(t, carry_cases)
        wr_htd(t, 0)
        restore(t)
    with t.rv64_only():
        hlib.csr_window(t, "S", "htimedeltah", hlib.FORMS[0], "illegal", "RV64: not a CSR")
    tests.append(t)

    t = new("time_htimedelta_req")
    t.describe(
        source=HYP,
        rule_text="If the time CSR is implemented, htimedelta (and htimedeltah for XLEN=32) must be implemented.",
        context='Zicntr implements time. "Implemented" means the CSR exists in HS-mode and is a full '
        "read/write register (htimedelta_sz_acc_op): every bit holds what is written.",
        plan="1. Zicntr: all eight CSR instruction forms on htimedelta in HS-mode, with random old and source "
        "values, return the old value and leave the exact new value.\n"
        "2. RV32: the same reads and writes of htimedeltah succeed.",
    )
    with t.only_if(ZICNTR):
        old = X(t.rand(32), t.rand(64))
        for form in hlib.FORMS:
            src = X(t.rand(32), t.rand(64))
            t.load("x7", old, "old htimedelta")
            t.emit(f"csrw {hex(HTD)}, x7")
            t.load("x6", src, "source")
            lab = hlib.csr_window(t, "S", "htimedelta", form, "ok", "HS-mode")
            n32 = hlib.form_value(form, old.num(32), src.num(32), 32)[1]
            n64 = hlib.form_value(form, old.num(64), src.num(64), 64)[1]
            if MUT == "htimedelta_partial":
                n64 &= 0xFFFFFFFF
            if form[2]:
                t.check("x7", old, lab, f"{form[4]} of htimedelta returns the old value")
            hs_read(t, "x7", "htimedelta")
            t.check("x7", X(n32, n64), lab, f"{form[4]} of htimedelta writes the expected value")
            old = X(n32 | 0x15, n64 | 0x15)
        with t.rv32_only():
            for form in (hlib.FORMS[0], hlib.FORMS[2]):
                t.load("x6", 0x7ACE, "source")
                lab = hlib.csr_window(t, "S", "htimedeltah", form, "ok", "HS-mode")
            hs_read(t, "x7", "htimedeltah")
            t.check("x7", 0x7ACE, lab, "htimedeltah holds the written value")
        wr_htd(t, 0)
    tests.append(t)
    return tests
