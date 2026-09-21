// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// console.c: a printf for the feature extractor's YAML output, on top of the DUT's string writer.
// Supports %s, %c, %d (long), %x (unsigned long, hexadecimal) and %%.  Division is done by hand
// so no libgcc helper is needed and the code runs without M.
//
// Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
// with assistance from Claude.

#include <stdarg.h>

#include "console.h"

extern void console_write(const char *s);

static void put_char(char c)
{
    char buf[2] = { c, '\0' };
    console_write(buf);
}

// Print an unsigned value in the given base without using a divide instruction
static void put_unsigned(unsigned long v, unsigned base)
{
    char digits[2 * sizeof(v) * 8 / 3 + 2];
    int len = 0;
    do {
        // v / base and v % base by binary long division
        unsigned long q = 0, r = 0;
        for (int bit = 8 * sizeof(v) - 1; bit >= 0; bit--) {
            r = (r << 1) | ((v >> bit) & 1);
            q <<= 1;
            if (r >= base) { r -= base; q |= 1; }
        }
        digits[len++] = "0123456789abcdef"[r];
        v = q;
    } while (v);
    while (len)
        put_char(digits[--len]);
}

int printf(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    for (; *fmt; fmt++) {
        if (*fmt != '%') {
            put_char(*fmt);
            continue;
        }
        fmt++;
        switch (*fmt) {
        case 's': {
            const char *s = va_arg(ap, const char *);
            console_write(s ? s : "(null)");
            break;
        }
        case 'c':
            put_char((char)va_arg(ap, int));
            break;
        case 'd': {
            long v = va_arg(ap, long);
            if (v < 0) { put_char('-'); v = -v; }
            put_unsigned((unsigned long)v, 10);
            break;
        }
        case 'x':
            put_unsigned(va_arg(ap, unsigned long), 16);
            break;
        case '%':
            put_char('%');
            break;
        case '\0':
            va_end(ap);
            return 0;
        default:            // unknown conversion: print it literally
            put_char('%');
            put_char(*fmt);
        }
    }
    va_end(ap);
    return 0;
}
