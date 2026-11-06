// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// probe.h: the trap-safe probe macros shared by the extension and parameter extractors.
//
// Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
// with assistance from Claude.
//
// A probe stores the address to resume at in probe_resume, executes its instructions, and clears
// probe_resume.  If an instruction traps, the handler in start.S records mcause, mtval and mepc,
// clears probe_resume and returns to the resume address, so the probe never needs to know the
// length of the instruction that trapped.  Label 1 is the resume address and label 2 the exit,
// aligned to 4 bytes because a 16-bit probe instruction leaves the code after it 2-byte aligned
// and a hart without C cannot resume at such an address (mepc[1] reads as zero).

#ifndef PROBE_H
#define PROBE_H

#include <stdbool.h>

#include "encoding.h"

#if __riscv_xlen == 64
#define SREG "sd"
#else
#define SREG "sw"
#endif

// Shared with start.S
extern volatile unsigned long probe_resume;   // while nonzero, a trap resumes here instead of failing
extern volatile unsigned long probe_cause;    // mcause of the most recent probe trap
extern volatile unsigned long probe_tval;     // mtval of the most recent probe trap
extern volatile unsigned long probe_epc;      // mepc of the most recent probe trap
#define PROBE_SCRATCH_SIZE 16384       // a G-stage root page table needs 16 KiB, 16 KiB aligned
extern unsigned char probe_scratch[PROBE_SCRATCH_SIZE];

#define CAUSE_NONE (~0ul)

// A probe the watchdog ended: the machine-timer interrupt
#define CAUSE_TIMEOUT ((1ul << (__riscv_xlen - 1)) | 7)

// The watchdog (feature_extractor.c).  On a DUT with a machine timer that interrupts, a probe run
// between watchdog_arm() and watchdog_disarm() that does not finish within the timeout ends with
// probe_cause = CAUSE_TIMEOUT; both are no-ops when there is no usable timer.
extern unsigned long watchdog_ticks;   // the timeout in mtime ticks, 0 without a watchdog
void watchdog_arm(unsigned long ticks);
void watchdog_disarm(void);
bool timed_wait(bool wrs, unsigned long ticks, unsigned long *elapsed, unsigned long *cycles);

#define STR_(x) #x
#define STR(x) STR_(x)
#define COUNT(a) (sizeof(a) / sizeof((a)[0]))

// Register convention inside a probe's instructions: a1 points at probe_scratch (aligned to
// PROBE_SCRATCH_SIZE); t1, t2, a2, a3, s0, s1, ft0-ft4, fs0 and every vector register may be
// written; %[in] is the input of PROBE_VALUE_IN.  t0 holds the resume address.  Floating-point
// and vector registers need no clobbers because the compiled code never keeps values in them.
// Every probe first sets probe_cause to CAUSE_NONE, so PROBE_OK() says afterwards whether it
// trapped even when its value is PROBE_TRAPPED (all ones is a legitimate CSR read-back).
#define PROBE_OK() (probe_cause == CAUSE_NONE)
#define PROBE_ASM(arch, insn, on_ok, on_trap, outputs, inputs)                             \
    probe_cause = CAUSE_NONE;                                                               \
    __asm__ volatile(                                                                       \
        "la    t0, 1f\n\t"                                                                  \
        SREG " t0, %[resume]\n\t"                                                           \
        "la    a1, probe_scratch\n\t"                                                       \
        ".option push\n\t"                                                                  \
        ".option arch, +" arch "\n\t"                                                       \
        insn "\n\t"                                                                         \
        ".option pop\n\t"                                                                   \
        on_ok "\n\t"                                                                        \
        "j     2f\n\t"                                                                      \
        ".balign 4\n"                                                                       \
        "1:\n\t"                                                                            \
        on_trap "\n"                                                                        \
        "2:\n\t"                                                                            \
        SREG " zero, %[resume]\n\t"                                                         \
        : outputs, [resume] "=m"(probe_resume)                                              \
        : inputs                                                                            \
        : "memory", "t0", "t1", "t2", "a1", "a2", "a3", "s0", "s1")

// Execute insn; true if it retired without trapping
#define PROBE(arch, insn) ({                                                                \
    unsigned long probe_ok_;                                                                \
    PROBE_ASM(arch, insn, "li %[ok], 1", "li %[ok], 0", [ok] "=&r"(probe_ok_), );           \
    (bool)probe_ok_;                                                                        \
})

// Execute insn; the value it left in a3, or PROBE_TRAPPED if it trapped
#define PROBE_TRAPPED (~0ul)
#define PROBE_VALUE(arch, insn) ({                                                          \
    unsigned long probe_value_;                                                             \
    PROBE_ASM(arch, insn, "mv %[value], a3", "li %[value], -1", [value] "=&r"(probe_value_), ); \
    probe_value_;                                                                           \
})

// Like PROBE_VALUE, with one input that insn refers to as %[in]
#define PROBE_VALUE_IN(arch, insn, input) ({                                                \
    unsigned long probe_value_;                                                             \
    PROBE_ASM(arch, insn, "mv %[value], a3", "li %[value], -1",                             \
              [value] "=&r"(probe_value_), [in] "r"(input));                                \
    probe_value_;                                                                           \
})

// Write a CSR, read it back and restore it; PROBE_TRAPPED if the CSR does not exist
#define DEFINE_CSR_WRITE_READ(name, csr)                                                    \
    static unsigned long name(unsigned long value)                                          \
    {                                                                                       \
        return PROBE_VALUE_IN("zicsr", "csrrw t2, " #csr ", %[in]\n\tcsrr a3, " #csr "\n\t" \
                                       "csrw " #csr ", t2", value);                         \
    }

// Read a CSR; PROBE_TRAPPED if it does not exist
#define DEFINE_CSR_READ(name, csr)                                                          \
    static unsigned long name(void) { return PROBE_VALUE("zicsr", "csrr a3, " #csr); }

// The CSRs both extractors write and read back
DEFINE_CSR_WRITE_READ(satp_wr, satp)
DEFINE_CSR_WRITE_READ(hgatp_wr, hgatp)
DEFINE_CSR_WRITE_READ(vsatp_wr, vsatp)
DEFINE_CSR_WRITE_READ(mcounteren_wr, mcounteren)
DEFINE_CSR_WRITE_READ(scounteren_wr, scounteren)
DEFINE_CSR_WRITE_READ(hcounteren_wr, hcounteren)

// Write a translation mode to satp/hgatp/vsatp, then Bare, and report whether Bare stuck
#define DEFINE_BARE_AFTER(name, csr)                                                        \
    static bool name(unsigned long mode)                                                    \
    {                                                                                       \
        unsigned long v = PROBE_VALUE_IN("zicsr", "csrw " #csr ", %[in]\n\tcsrw " #csr ", zero\n\t" \
                                                  "csrr a3, " #csr "\n\tseqz a3, a3", mode); \
        return v != PROBE_TRAPPED && v != 0;                                                \
    }
DEFINE_BARE_AFTER(satp_bare_after, satp)
DEFINE_BARE_AFTER(hgatp_bare_after, hgatp)
DEFINE_BARE_AFTER(vsatp_bare_after, vsatp)

// Address translation modes: satp.MODE values; hgatp uses the same values for the x4 modes
#if __riscv_xlen == 64
#define ATP_MODE(m) ((unsigned long)(m) << 60)
#define SATP_ASID SATP64_ASID
#define HGATP_VMID HGATP64_VMID
static const struct { const char *name; unsigned long mode; } atp_modes[] =
    { { "Sv39", SATP_MODE_SV39 }, { "Sv48", SATP_MODE_SV48 }, { "Sv57", SATP_MODE_SV57 } };
#else
#define ATP_MODE(m) ((unsigned long)(m) << 31)
#define SATP_ASID SATP32_ASID
#define HGATP_VMID HGATP32_VMID
static const struct { const char *name; unsigned long mode; } atp_modes[] = { { "Sv32", SATP_MODE_SV32 } };
#endif

// The atp_modes a translation CSR accepts, bit i for atp_modes[i]; *last is the last one accepted
// (0 if none), the mode to try Bare after
static unsigned atp_accepted(unsigned long (*wr)(unsigned long), unsigned long *last)
{
    unsigned modes = 0;
    *last = 0;
    for (unsigned i = 0; i < COUNT(atp_modes); i++) {
        unsigned long m = ATP_MODE(atp_modes[i].mode);
        if (wr(m) == m) {
            modes |= 1u << i;
            *last = m;
        }
    }
    return modes;
}

#endif
