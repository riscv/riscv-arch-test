/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Compiler runtime helpers for bare-metal builds.
 *
 * The bare-metal build uses -nostdlib -nodefaultlibs, so GCC's libgcc
 * routines are not linked automatically. Symbols required by the compiler
 * (e.g., 64-bit division for printf %llu) are provided here.
 */

#include "types.h"

/* ===================================================================
 * 64-bit integer division helpers
 * =================================================================== */

static void udivmod64(unsigned long long n, unsigned long long d,
                      unsigned long long *q, unsigned long long *r)
{
    unsigned long long quot = 0;
    unsigned long long rem = 0;

    /* Division by zero is undefined behavior. In a bare-metal environment
     * without hardware traps for this case, silently continuing would
     * produce a bogus result. Return zeroes as a safe fallback. */
    if (d == 0) {
        *q = 0;
        *r = 0;
        return;
    }

    for (int i = 63; i >= 0; i--) {
        rem = (rem << 1) | ((n >> i) & 1ULL);
        if (rem >= d) {
            rem -= d;
            quot |= (1ULL << i);
        }
    }

    *q = quot;
    *r = rem;
}

unsigned long long __udivdi3(unsigned long long n, unsigned long long d)
{
    unsigned long long q, r;
    udivmod64(n, d, &q, &r);
    return q;
}

unsigned long long __umoddi3(unsigned long long n, unsigned long long d)
{
    unsigned long long q, r;
    udivmod64(n, d, &q, &r);
    return r;
}
