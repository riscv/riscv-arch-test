// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International

// C version of FeatureExtractor.
// Detects whether M is supported by executing encoded DIV.

#include <stdint.h>
#include <stdbool.h>

extern int printf(const char *fmt, ...);

/* Defined by the ACT trap-signature setup. */
extern uint32_t read_trap_count_asm(void);
extern uint32_t read_unexpected_trap_asm(void);

static inline uint32_t read_trap_count(void)
{
    return read_trap_count_asm();
}

/*
 * Probe M by executing:
 *     div a2, a0, a1
 *
* Returns:
 *     true  if DIV executed successfully (M is supported)
 *     false if DIV trapped (M is not supported)
 */
static bool check_m_supported(void)
{
    uint32_t before = read_trap_count();

    /*
    * The inline assembly executes one candidate instruction and then C checks
    * whether the local trap counter changed.
    *
    * "memory" prevents the compiler from reordering memory accesses across the
    * probe, which matters because the trap counter is updated asynchronously by
    * the trap handler.
    *
    * a0/a1/a2 are clobbered by the probe operands/result.
    *
    * t0/t1 are listed because the local trap handler uses them when the probe
    * traps. From the C compiler's point of view, the inline assembly may return
    * after a trap path that modified those temporaries.
    */
    __asm__ volatile (
        "li      a0, 10\n"
        "li      a1, 2\n"
        ".option push\n"
        ".option arch, +m\n"
        ".option norvc\n"
        "div     a2, a0, a1\n"
        ".option pop\n"
        :
        :
        : "memory", "a0", "a1", "a2", "t0", "t1"
    );

    uint32_t after = read_trap_count();

    return after == before;
}

int main(void)
{
    bool m_supported = check_m_supported();

    if (read_unexpected_trap_asm() != 0) {
        printf("error: unexpected trap occurred\n");
        return 1;
    }

    printf("implemented_extensions:\n");
    printf("  - { name: I, version: '= 2.1' }\n");

    if (m_supported) {
        printf("  - { name: M, version: '= 2.0' }\n");
    }

    return 0;
}
