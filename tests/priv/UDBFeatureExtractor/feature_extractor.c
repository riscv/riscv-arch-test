// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International

// C version of FeatureExtractor.
// Detects whether M is supported by executing encoded DIV.

#include <stdint.h>

extern int printf(const char *fmt, ...);

/* Defined by the ACT trap-signature setup. */
extern uint32_t read_trap_count_asm(void);

static inline uint32_t read_trap_count(void)
{
    return read_trap_count_asm();
}

/*
 * Probe M by executing:
 *     div a2, a0, a1
 *
 * Raw encoding:
 *     div a2, a0, a1 = 0x02b54633
 *
 * Returns:
 *     1 if DIV trapped
 *     0 if DIV executed successfully
 */
 
static int probe_m_extension(void)
{
    uint32_t before = read_trap_count();

    __asm__ volatile (
        "li      a0, 10\n"
        "li      a1, 2\n"
        ".option push\n"
        ".option norvc\n"
        ".word   0x02b54633\n"   // div a2, a0, a1
        ".option pop\n"
        :
        :
        : "memory", "a0", "a1", "a2", "t0", "t1"
    );

    uint32_t after = read_trap_count();

    return after != before;
}

int main(void)
{
    int div_trapped = probe_m_extension();

    printf("implemented_extensions:\n");
    printf("  - { name: I, version: '= 2.1' }\n");

    if (!div_trapped) {
        printf("  - { name: M, version: '= 2.0' }\n");
    }

    return 0;
}