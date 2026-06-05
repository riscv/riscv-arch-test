// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2025 RISC-V International

// Minimal printf support for bare-metal FeatureExtractorC.
// Only supports plain strings, %s, %c, and %% which is enough for YAML output and avoids libgcc division helpers.

#include <stdarg.h>

extern void arch_write_str_asm(const char *s);

static void put_char(char c)
{
    char buf[2];

    buf[0] = c;
    buf[1] = '\0';

    arch_write_str_asm(buf);
}

static void put_str(const char *s)
{
    if (s == 0) {
        s = "(null)";
    }

    while (*s != '\0') {
        put_char(*s++);
    }
}

int printf(const char *fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);

    while (*fmt != '\0') {
        if (*fmt != '%') {
            put_char(*fmt++);
            continue;
        }

        fmt++;

        if (*fmt == 's') {
            const char *s = va_arg(ap, const char *);
            put_str(s);
        } else if (*fmt == 'c') {
            char c = (char)va_arg(ap, int);
            put_char(c);
        } else if (*fmt == '%') {
            put_char('%');
        } else {
            // Unsupported format: print it literally.
            put_char('%');
            put_char(*fmt);
        }

        if (*fmt != '\0') {
            fmt++;
        }
    }

    va_end(ap);
    return 0;
}

int puts(const char *s)
{
    put_str(s);
    put_char('\n');
    return 0;
}