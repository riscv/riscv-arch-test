// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International

// C version of FeatureExtractor.
// Detects whether M is supported by executing encoded DIV.

#include <stdint.h>
#include <stdbool.h>

extern int printf(const char *fmt, ...);

/* Defined by the ACT trap-signature setup. */
extern volatile uint32_t c_trap_flag;
extern volatile uint32_t c_unexpected_trap;

static inline uint32_t read_trap_flag(void)
{
    return c_trap_flag;
}

static inline void reset_trap_flag(void)
{
    c_trap_flag = 0;
}

static inline uint32_t read_unexpected_trap(void)
{
    return c_unexpected_trap;
}


/*
 * check_i_supported() - probe for the I (base integer) extension.
 *
 * I supports 32 general-purpose registers (x0-x31).
 * E only supports 16 (x0-x15); accessing x16-x31 is illegal on E.
 *
 * Probe: addi x16, x16, 0  (no-op using an upper register)
 *     trap   -> E only
 *     no trap -> I is supported
 *
 * Returns:
 *     true  if I is supported
 *     false if only E is supported
 */
static bool check_i_supported(void)
{
    reset_trap_flag();

    __asm__ volatile (
        ".option push\n"
        ".option norvc\n"
        "addi x16, x16, 0\n"
        ".option pop\n"
        :
        :
        : "memory", "a6", "t0", "t1"
    );

    return !read_trap_flag();
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
    reset_trap_flag();
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

    return !read_trap_flag();
}

int main(void)
{
    bool i_supported = check_i_supported();
    bool m_supported = check_m_supported();

    if (read_unexpected_trap() != 0) {
        printf("error: unexpected trap occurred\n");
        return 1;
    }

    printf("implemented_extensions:\n");

    if (i_supported) {
        printf("  - { name: I, version: '= 2.1' }\n");
    } else {
        printf("  - { name: E, version: '= 2.0' }\n");
    }

    if (m_supported) {
        printf("  - { name: M, version: '= 2.0' }\n");
    }

    return 0;
}
