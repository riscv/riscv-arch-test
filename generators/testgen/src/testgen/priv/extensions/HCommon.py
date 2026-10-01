##################################
# priv/extensions/HCommon.py
#
# Shared H test-generation infrastructure
# wutianze@ict.ac.cn Sep 2026
# Assisted by the MLVP AI framework
# SPDX-License-Identifier: Apache-2.0
##################################
"""Shared H test-generation infrastructure.

The H CSR inventory and the per-case emission
scaffolding (mode entry, M trap recovery, signature updates) shared by the
H test generators. Each chunk owns its setup, M trap recovery and data.
Public guest trap/save-area services are intentionally not consumed. The
framework supplies the outer test, PMP setup, signature implementation and
final M-mode termination.
"""

from dataclasses import dataclass

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

CG = "H_cg"
M_CSRS = ("mtval2", "mtinst")
H_CSRS = (
    "hstatus",
    "hedeleg",
    "hideleg",
    "hie",
    "hcounteren",
    "hgeie",
    "henvcfg",
    "htval",
    "hip",
    "hvip",
    "htinst",
    "hgatp",
    "hgeip",
)
S_CSRS = ("sstatus", "sie", "stval", "sip", "stvec", "sscratch", "sepc", "scause", "satp")
VS_CSRS = ("vsstatus", "vsie", "vstval", "vsip", "vstvec", "vsscratch", "vsepc", "vscause", "vsatp")
MODE = {"m": (3, 0), "hs": (1, 0), "u": (0, 0), "vs": (1, 1), "vu": (0, 1)}
OPS = ("write_zero", "write_ones", "set", "clear", "read")


@dataclass(frozen=True)
class CSR:
    name: str
    guard: str | None = None
    access_bits: int | None = None  # None follows XLEN.


def csr_inventory(machine: bool = False, supervisor: bool = False) -> list[CSR]:
    names = (M_CSRS if machine else ()) + H_CSRS + VS_CSRS + (S_CSRS if supervisor else ())
    return [CSR(name) for name in names] + [
        CSR("htimedelta", "defined(ZICNTR_SUPPORTED)"),
        CSR("vstimecmp", "defined(SSTC_SUPPORTED)"),
        CSR("hedelegh", "__riscv_xlen == 32", access_bits=32),
        CSR("henvcfgh", "__riscv_xlen == 32", access_bits=32),
        CSR("htimedeltah", "__riscv_xlen == 32 && defined(ZICNTR_SUPPORTED)", access_bits=32),
        CSR("vstimecmph", "__riscv_xlen == 32 && defined(SSTC_SUPPORTED)", access_bits=32),
    ]


class Case:
    """One counted testcase with register allocation and explicit recovery."""

    def __init__(
        self,
        td: TestData,
        cp: str,
        mode: str,
        name: str,
        changed: tuple[str, ...] = (),
        guard: str | None = None,
        virtual: bool = False,
        destination: str | None = None,
        chunk: TestChunk | None = None,
    ) -> None:
        self.td = td
        self.cp = cp
        self.mode = mode
        self.guard = guard
        self.virtual = virtual or MODE[mode][1] == 1
        assert chunk is not None
        self.tc = chunk
        self.tc.section_header = comment_banner(cp, name)
        self.regs = td.int_regs.get_registers(6)
        self.p, self.t, self.r, self.c, self.a, self.b = self.regs
        self.label = td.add_testcase(name, cp, CG).rstrip(":")
        self.base = self.label + "_state"
        # Accesses to RV32 high-half CSRs are illegal-instruction tests on RV64.
        suffix = f"_{destination}" if destination else ""
        self.profile = f"{cp.removeprefix('cp_')}_{mode}{suffix}"
        xlens = (64,) if cp in ("cp_vs_high_half", "cp_u_high_half", "cp_vu_high_half") else (32, 64)
        identifiers = [f"rv{xlen}_{self.profile}" for xlen in xlens]
        resource_mode = "two_stage" if cp in ("cp_hlv", "cp_hlvx", "cp_hsv") else "bare_or_csr_only"
        self.emit("# H_VM_PROFILE " + " ".join(identifiers))
        self.emit(f"# H_RESOURCE_MODE {resource_mode}")
        if guard:
            self.emit(f"#if {guard}")
        self.emit(".option push", ".option norvc")
        core = ("mstatus", "mtvec", "medeleg", "mie", "mepc", "mcause", "mtval")
        if mode != "m" or self.virtual:
            core += ("satp",)
        if self.virtual:
            core += ("hstatus", "vsstatus", "vsatp", "hgatp", "mtval2", "mtinst")
        self.saved = list(dict.fromkeys(core + changed))
        self.saved = [csr for csr in self.saved if csr != "hgeip"]
        self.timer_access = False
        self.stateen_access = False
        self.guest_envcfg = False
        self.tc.raw_data += [".balign 8", f"{self.base}:", f".zero {8 * (len(self.saved) + 12)}"]
        self.emit(f"LA(x{self.p}, {self.base})")
        for index, csr in enumerate(self.saved):
            self.read(self.t, csr)
            self.emit(f"SREG x{self.t}, {index * 8}(x{self.p}) # save {csr}")
        self.emit("#if __riscv_xlen == 32")
        self.read(self.t, "mstatush")
        self.store_slot(self.t, 0)
        self.emit("#endif")
        self.field("mstatus", (1 << 3) | (1 << 17) | (1 << 19) | (1 << 20) | (1 << 22), 0)
        self.write("mie", "zero")
        self.write("medeleg", "zero")
        if "satp" in self.saved:
            self.write("satp", "zero")
            self.emit("sfence.vma zero, zero", "nop")
        if self.virtual:
            self.write("vsatp", "zero")
            self.write("hgatp", "zero")
            self.emit("hfence.vvma zero, zero", "nop", "hfence.gvma zero, zero", "nop")
            self.field("hstatus", (1 << 20) | (1 << 21) | (1 << 22) | (1 << 7), 0)
        self.emit(f"LA(x{self.t}, {self.label}_trap)")
        self.write("mtvec", self.t)
        self.emit(f"LI(x{self.r}, 0)", f"LI(x{self.c}, 0)")

    def emit(self, *lines: str) -> None:
        self.tc.code.extend(lines)

    def read(self, reg: int, csr: str) -> None:
        # Signature CSR macros combine the access and observation. State saves
        # and lower-mode stimuli must instead defer observation until M recovery.
        self.emit(f"csrr x{reg}, {csr}", "nop")

    def write(self, csr: str, reg: int | str) -> None:
        operand = f"x{reg}" if isinstance(reg, int) else reg
        self.emit(f"csrw {csr}, {operand}", "nop")

    def field(self, csr: str, mask: int | str, value: int | str) -> None:
        """Preserve old bits outside mask; value never aliases the saved old CSR."""
        self.read(self.t, csr)
        self.emit(
            f"LI(x{self.a}, {mask})",
            f"not x{self.a}, x{self.a}",
            f"and x{self.t}, x{self.t}, x{self.a}",
            f"LI(x{self.a}, ({value}) & ({mask}))",
            f"or x{self.t}, x{self.t}, x{self.a}",
        )
        self.write(csr, self.t)

    def slot(self, index: int) -> int:
        return (len(self.saved) + index) * 8

    def store_slot(self, reg: int, index: int) -> None:
        self.emit(f"LA(x{self.p}, {self.base})", f"SREG x{reg}, {self.slot(index)}(x{self.p})")

    def load_slot(self, reg: int, index: int) -> None:
        self.emit(f"LA(x{self.p}, {self.base})", f"LREG x{reg}, {self.slot(index)}(x{self.p})")

    def enter(self) -> None:
        if self.mode == "m":
            return
        privilege, virt = MODE[self.mode]
        self.field("mstatus", (3 << 11) | (1 << 7), privilege << 11)
        self.mpv(virt)
        self.emit(f"LA(x{self.t}, {self.label}_entry)")
        self.write("mepc", self.t)
        self.emit("mret", "nop", f"{self.label}_entry:")

    def mpv(self, value: int) -> None:
        self.emit("#if __riscv_xlen == 64")
        self.field("mstatus", "(1 << 39)", f"({value} << 39)")
        self.emit("#else")
        self.field("mstatush", 1 << 7, value << 7)
        self.emit("#endif")

    def instruction(self, instruction: str) -> None:
        self.emit(f"{self.label}:", instruction, "nop")

    def recover(self, expected: int, completed_mode: str | None = None) -> None:
        """Recover once; an exception at an unrelated PC is never accepted."""
        mode = completed_mode or self.mode
        ecall_cause = {"m": 11, "hs": 9, "u": 8, "vs": 10, "vu": 8}[mode]
        if self.mode == "m" and completed_mode is None:
            self.emit(f"j {self.label}_resume")
        self.emit(f"{self.label}_complete:", "ecall", "nop", ".p2align 2", f"{self.label}_trap:")
        self.read(self.c, "mcause")
        self.read(self.t, "mepc")
        self.store_slot(self.t, 1)
        self.read(self.t, "mstatus")
        self.store_slot(self.t, 2)
        self.emit("#if __riscv_xlen == 32")
        self.read(self.t, "mstatush")
        self.store_slot(self.t, 3)
        self.emit("#endif")
        self.read(self.t, "mtval")
        self.store_slot(self.t, 4)
        self.load_slot(self.t, 1)
        self.emit(
            f"LA(x{self.p}, {self.label}_complete)",
            f"bne x{self.t}, x{self.p}, {self.label}_target_trap",
            f"LI(x{self.t}, {ecall_cause})",
            f"bne x{self.c}, x{self.t}, {self.label}_bad_trap",
            f"LI(x{self.c}, 0)",
            f"j {self.label}_to_m",
            f"{self.label}_target_trap:",
            f"LA(x{self.p}, {self.label})",
            f"beq x{self.t}, x{self.p}, {self.label}_to_m",
            f"{self.label}_bad_trap:",
            f"LI(x{self.t}, 0x1000)",
            f"or x{self.c}, x{self.c}, x{self.t}",
            f"{self.label}_to_m:",
        )
        self.field("mstatus", (3 << 11) | (1 << 17) | (1 << 7), 3 << 11)
        self.mpv(0)
        self.emit(f"LA(x{self.t}, {self.label}_resume)")
        self.write("mepc", self.t)
        self.emit("mret", "nop", f"{self.label}_resume:")
        self.expect(self.c, expected)
        self.emit(write_sigupd(self.c, self.td))

    def expect(self, reg: int, value: int | str) -> None:
        self.emit(
            f"LI(x{self.t}, {value})",
            f"beq x{reg}, x{self.t}, 1f",
            f"LA(x{self.t}, rvmodel_halt_fail)",
            f"jalr zero, 0(x{self.t})",
            "1:",
        )

    def signature(self, reg: int) -> None:
        self.emit(write_sigupd(reg, self.td))

    def enable_stateen(self, csr: str) -> None:
        """Enable only permissions directly consumed by this CSR stimulus."""
        self.stateen_access = True
        self.guest_envcfg = self.mode == "vs" and csr == "senvcfg"
        mask = 1 << (56 if csr == "hedelegh" else 62)
        self.emit("#ifdef SMSTATEEN_SUPPORTED")
        self.read(self.t, "mstateen0")
        self.store_slot(self.t, 6)
        self.emit("#if __riscv_xlen == 32")
        self.read(self.t, "mstateen0h")
        self.store_slot(self.t, 7)
        self.field("mstateen0h", mask >> 32, mask >> 32)
        self.emit("#else")
        self.field("mstateen0", mask, mask)
        self.emit("#endif", "#endif")
        if self.guest_envcfg:
            self.emit("#if defined(SMSTATEEN_SUPPORTED) || defined(SSSTATEEN_SUPPORTED)")
            self.read(self.t, "hstateen0")
            self.store_slot(self.t, 8)
            self.emit("#if __riscv_xlen == 32")
            self.read(self.t, "hstateen0h")
            self.store_slot(self.t, 9)
            self.field("hstateen0h", 1 << 30, 1 << 30)
            self.emit("#else")
            self.field("hstateen0", 1 << 62, 1 << 62)
            self.emit("#endif", "#endif")

    def finish(self) -> TestChunk:
        if self.virtual:
            self.write("vsatp", "zero")
            self.emit("hfence.vvma zero, zero", "nop")
            self.write("hgatp", "zero")
            self.emit("hfence.gvma zero, zero", "nop")
        if self.timer_access:
            self.emit("#if __riscv_xlen == 32")
            self.load_slot(self.t, 5)
            self.write("menvcfgh", self.t)
            self.emit("#endif")
        self.emit(f"LA(x{self.p}, {self.base})")
        # Restore status/interrupt/vector state last. EPC is no longer needed.
        order = [s for s in self.saved if s not in ("mstatus", "mtvec", "mie")]
        order += [s for s in ("mtvec", "mie", "mstatus") if s in self.saved]
        for csr in order:
            self.emit(f"LREG x{self.t}, {self.saved.index(csr) * 8}(x{self.p}) # restore {csr}")
            self.write(csr, self.t)
        if self.stateen_access:
            if self.guest_envcfg:
                self.emit("#if defined(SMSTATEEN_SUPPORTED) || defined(SSSTATEEN_SUPPORTED)")
                self.load_slot(self.t, 8)
                self.write("hstateen0", self.t)
                self.emit("#if __riscv_xlen == 32")
                self.load_slot(self.t, 9)
                self.write("hstateen0h", self.t)
                self.emit("#endif", "#endif")
            self.emit("#ifdef SMSTATEEN_SUPPORTED")
            self.load_slot(self.t, 6)
            self.write("mstateen0", self.t)
            self.emit("#if __riscv_xlen == 32")
            self.load_slot(self.t, 7)
            self.write("mstateen0h", self.t)
            self.emit("#endif", "#endif")
        self.emit("#if __riscv_xlen == 32")
        self.load_slot(self.t, 0)
        self.write("mstatush", self.t)
        self.emit("#endif")
        if "satp" in self.saved:
            self.emit("sfence.vma zero, zero", "nop")
        if self.virtual:
            self.emit("hfence.vvma zero, zero", "nop", "hfence.gvma zero, zero", "nop")
        self.emit(".option pop")
        if self.guard:
            self.emit("#endif")
        self.td.int_regs.return_registers(self.regs)
        return self.tc


def new_case(
    td: TestData,
    cp: str,
    mode: str,
    name: str,
    changed: tuple[str, ...] = (),
    guard: str | None = None,
    virtual: bool = False,
    destination: str | None = None,
) -> Case:
    chunk = td.begin_test_chunk(cp.removeprefix("cp_"))
    return Case(td, cp, mode, name, changed, guard, virtual, destination, chunk)


def finish_case(case: Case) -> TestChunk:
    case.finish()
    return case.td.end_test_chunk()
