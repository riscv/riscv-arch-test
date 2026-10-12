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
#define CAUSE_INSTRUCTION_MISALIGNED 0
#define CAUSE_INSTRUCTION_ACCESS_FAULT 1
#define CAUSE_ILLEGAL_INSTRUCTION 2
#define CAUSE_BREAKPOINT 3
#define CAUSE_LOAD_MISALIGNED 4
#define CAUSE_LOAD_ACCESS_FAULT 5
#define CAUSE_STORE_MISALIGNED 6
#define CAUSE_STORE_ACCESS_FAULT 7
#define CAUSE_ECALL_U 8
#define CAUSE_ECALL_S 9
#define CAUSE_ECALL_M 11

#define STR_(x) #x
#define STR(x) STR_(x)

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

#endif
