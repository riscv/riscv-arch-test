/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Minimal libc replacements for bare-metal environment.
 *
 * GCC typically inlines small struct assignments and array copies, so
 * these functions are rarely called. Clang, however, emits explicit
 * calls to memcpy/memset for such operations. Since the framework is
 * built with -nostdlib -nodefaultlibs, no libc is linked automatically.
 *
 * These implementations provide the minimal subset required by the
 * compiler's code generation. They are intentionally simple (byte-level)
 * to ensure correctness on all architectures without alignment concerns.
 */

#include "types.h"

void *memcpy(void *dst, const void *src, size_t n)
{
    char *d = (char *)dst;
    const char *s = (const char *)src;
    while (n--) {
        *d++ = *s++;
    }
    return dst;
}

void *memset(void *dst, int c, size_t n)
{
    char *d = (char *)dst;
    while (n--) {
        *d++ = (char)c;
    }
    return dst;
}

void *memmove(void *dst, const void *src, size_t n)
{
    char *d = (char *)dst;
    const char *s = (const char *)src;
    if (d < s) {
        while (n--) {
            *d++ = *s++;
        }
    } else if (d > s) {
        d += n;
        s += n;
        while (n--) {
            *--d = *--s;
        }
    }
    return dst;
}
